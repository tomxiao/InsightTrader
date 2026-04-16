from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from tradingagents.agents import (
    create_decision_manager,
    create_fundamentals_analyst,
    create_market_analyst_fast,
    create_msg_delete,
    create_news_analyst,
)
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_utils import (
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_global_news,
    get_income_statement,
    get_indicators,
    get_news,
    get_stock_data,
)
from tradingagents.dataflows.config import get_runtime_context, set_config, set_runtime_context
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.graph.propagation import Propagator
from tradingagents.llm_clients import create_llm_client
from tradingagents.observability import NodeEventTracker, resolve_node_kind, resolve_stage_id_for_node


class LiteTradingGraph:
    _BRANCH_MESSAGE_KEYS = {
        "market": "market_messages",
        "news": "news_messages",
        "fundamentals": "fundamentals_messages",
    }

    def __init__(
        self,
        selected_analysts: Optional[List[str]] = None,
        debug: bool = False,
        config: Optional[Dict[str, Any]] = None,
        callbacks: Optional[List] = None,
    ):
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.callbacks = callbacks or []
        self.node_tracker = NodeEventTracker(
            config=self.config,
            runtime_context_getter=get_runtime_context,
            stall_threshold_s=float(self.config.get("node_stall_threshold_s", 60.0)),
            check_interval_s=float(self.config.get("node_check_interval_s", 5.0)),
        )
        self.node_tracker.start_watchdog()
        set_config(self.config)
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        llm_kwargs = self._get_provider_kwargs()
        if self.callbacks:
            llm_kwargs["callbacks"] = self.callbacks

        deep_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["deep_think_llm"],
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )
        quick_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["quick_think_llm"],
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )
        self.deep_thinking_llm = deep_client.get_llm()
        self.quick_thinking_llm = quick_client.get_llm()
        self.propagator = Propagator()
        self.conditional_logic = ConditionalLogic()
        self.tool_nodes = self._create_tool_nodes()
        self.ticker: Optional[str] = None
        self.curr_state = None
        self.graph = self._setup_graph(selected_analysts or ["market", "news", "fundamentals"])

    def _get_provider_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        provider = self.config.get("llm_provider", "").lower()
        timeout = self.config.get("llm_timeout")
        max_retries = self.config.get("llm_max_retries")
        if timeout is not None:
            kwargs["timeout"] = timeout
        if max_retries is not None:
            kwargs["max_retries"] = max_retries
        if provider == "google":
            thinking_level = self.config.get("google_thinking_level")
            if thinking_level:
                kwargs["thinking_level"] = thinking_level
        elif provider == "openai":
            reasoning_effort = self.config.get("openai_reasoning_effort")
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort
        elif provider == "anthropic":
            effort = self.config.get("anthropic_effort")
            if effort:
                kwargs["effort"] = effort
        return kwargs

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        return {
            "market": ToolNode([get_stock_data, get_indicators]),
            "news": ToolNode([get_news, get_global_news]),
            "fundamentals": ToolNode(
                [get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement]
            ),
        }

    def _invoke_node(self, node, *args, **kwargs):
        if hasattr(node, "invoke"):
            return node.invoke(*args, **kwargs)
        return node(*args, **kwargs)

    def _with_node_observability(self, node_name: str, node):
        stage_id = resolve_stage_id_for_node(node_name)
        node_kind = resolve_node_kind(node_name)

        def instrumented_node(*args, **kwargs):
            previous_context = get_runtime_context()
            self.node_tracker.mark_started(node_id=node_name, stage_id=stage_id, node_kind=node_kind)
            set_runtime_context(
                current_stage_id=stage_id,
                current_node_id=node_name,
                current_node_kind=node_kind,
            )
            try:
                result = self._invoke_node(node, *args, **kwargs)
            except Exception as exc:
                self.node_tracker.mark_failed(exc)
                raise
            else:
                self.node_tracker.mark_completed()
                return result
            finally:
                set_runtime_context(
                    current_stage_id=previous_context.get("current_stage_id"),
                    current_node_id=previous_context.get("current_node_id"),
                    current_node_kind=previous_context.get("current_node_kind"),
                )

        return instrumented_node

    def _get_branch_message_key(self, analyst_type: str) -> str:
        return self._BRANCH_MESSAGE_KEYS[analyst_type]

    def _build_branch_state(self, state: AgentState, analyst_type: str) -> Dict[str, Any]:
        branch_key = self._get_branch_message_key(analyst_type)
        branch_messages = state.get(branch_key) or state.get("messages", [])
        branch_state = dict(state)
        branch_state["messages"] = branch_messages
        return branch_state

    def _wrap_branch_node(self, analyst_type: str, node):
        branch_key = self._get_branch_message_key(analyst_type)

        def branch_node(state: AgentState) -> dict:
            result = self._invoke_node(node, self._build_branch_state(state, analyst_type))
            updates = {key: value for key, value in result.items() if key != "messages"}
            if "messages" in result:
                updates[branch_key] = add_messages(
                    state.get(branch_key) or state.get("messages", []),
                    result["messages"],
                )
            return updates

        return branch_node

    def _wrap_branch_condition(self, analyst_type: str):
        branch_condition = getattr(self.conditional_logic, f"should_continue_{analyst_type}")

        def condition(state: AgentState):
            return branch_condition(self._build_branch_state(state, analyst_type))

        return condition

    def _setup_graph(self, selected_analysts: List[str]):
        allowed = [item for item in selected_analysts if item in {"market", "news", "fundamentals"}]
        if not allowed:
            raise ValueError("LiteTradingGraph requires at least one of market/news/fundamentals")

        analyst_nodes = {
            "market": create_market_analyst_fast(self.quick_thinking_llm),
            "news": create_news_analyst(self.quick_thinking_llm),
            "fundamentals": create_fundamentals_analyst(self.quick_thinking_llm),
        }
        delete_node = create_msg_delete()
        decision_manager_node = create_decision_manager(self.deep_thinking_llm)

        workflow = StateGraph(AgentState)
        for analyst_type in allowed:
            analyst_node_name = f"{analyst_type.capitalize()} Analyst"
            clear_node_name = f"Msg Clear {analyst_type.capitalize()}"
            tool_node_name = f"tools_{analyst_type}"
            workflow.add_node(
                analyst_node_name,
                self._with_node_observability(
                    analyst_node_name,
                    self._wrap_branch_node(analyst_type, analyst_nodes[analyst_type]),
                ),
            )
            workflow.add_node(
                clear_node_name,
                self._with_node_observability(
                    clear_node_name,
                    self._wrap_branch_node(analyst_type, delete_node),
                ),
            )
            workflow.add_node(
                tool_node_name,
                self._with_node_observability(
                    tool_node_name,
                    self._wrap_branch_node(analyst_type, self.tool_nodes[analyst_type]),
                ),
            )

        workflow.add_node(
            "Decision Manager",
            self._with_node_observability("Decision Manager", decision_manager_node),
        )

        clear_nodes: list[str] = []
        for analyst_type in allowed:
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"
            clear_nodes.append(current_clear)
            workflow.add_edge(START, current_analyst)
            workflow.add_conditional_edges(
                current_analyst,
                self._wrap_branch_condition(analyst_type),
                [current_tools, current_clear],
            )
            workflow.add_edge(current_tools, current_analyst)

        workflow.add_edge(clear_nodes, "Decision Manager")

        workflow.add_edge("Decision Manager", END)
        return workflow.compile()

    def stop_observers(self):
        self.node_tracker.stop_watchdog()
