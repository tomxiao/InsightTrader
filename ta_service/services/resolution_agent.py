from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_core.tools import tool

from ta_service.models.resolution import AgentResolutionResult, ResolutionAgentContext
from ta_service.runtime.user_trace import append_runtime_user_trace
from ta_service.services.stock_lookup_gateway import StockLookupGateway
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.llm_clients.factory import create_llm_client

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 2

_TOOL_SYSTEM_PROMPT = """你是 InsightTrader Mobile 的 F3 Resolution Agent。

你的任务只有一个：识别并确认用户想分析的唯一股票标的。

工作规则：
1. 你负责理解自然语言、判断是否需要调用工具、以及产出最终结构化决策。
2. 你只处理一期单股票分析场景。
3. 当输入超出一期范围，例如行业、主题、多股票对比、指数、基金、加密货币或期货时，你需要收敛到 unsupported。
4. 当用户显式给出标准 ticker，且资料校验成功时，可以直接 resolved。
5. 当只有一个高置信候选但仍需要用户确认时，输出 need_confirm。
6. 当存在多个合理候选时，输出 need_disambiguation。
7. 当信息不足但仍可继续补充时，输出 collect_more。
8. 当工具返回 error 或无法可靠判断时，输出 failed。
9. 所有面向用户的文案必须使用简体中文，适合移动端消息流。

你可以使用两个工具：
- search_stock_candidates(query, market_hints?, limit?)
  · query 必须是干净的搜索词：提取出的 ticker、公司名或中文简称，不得包含用户句子中的动词、副词或无关汉字。
  · 例如：用户说"帮我看一下MU"→ query="MU"；用户说"分析一下英伟达"→ query="英伟达"；用户说"mu.us怎么样"→ query="MU"（去掉 .us/.US 后缀）。
  · market_hints 仅在能从上下文明确判断市场时传入，如 ["US"]、["HK"]、["CN"]。
- get_stock_profile(ticker)：查询单个 ticker 的标准资料，用于确认前校验。ticker 必须是标准格式（如 AAPL、00700.HK）。

只有在需要外部股票数据时才调用工具。
"""

_FINAL_OUTPUT_EXAMPLE = {
    "status": "need_confirm",
    "assistantReply": "你想分析的是 Apple Inc.（AAPL）吗？",
    "stock": {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "market": "US",
        "exchange": "NASDAQ",
        "aliases": [],
        "score": 1.0,
        "assetType": "stock",
        "isActive": True,
    },
    "candidates": [
        {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "market": "US",
            "exchange": "NASDAQ",
            "aliases": [],
            "score": 1.0,
            "assetType": "stock",
            "isActive": True,
        }
    ],
    "focusPoints": ["估值"],
    "shouldCreateAnalysisTask": False,
    "terminate": False,
}

_FINAL_OUTPUT_RESOLVED_EXAMPLE = {
    "status": "resolved",
    "assistantReply": "已确认标的是腾讯控股（0700.HK），现在开始为你准备分析。",
    "stock": {
        "ticker": "0700.HK",
        "name": "腾讯控股",
        "market": "HK",
        "exchange": "HKEX",
        "aliases": [],
        "score": 1.0,
        "assetType": "stock",
        "isActive": True,
    },
    "candidates": [],
    "focusPoints": [],
    "shouldCreateAnalysisTask": True,
    "terminate": True,
}

_FINAL_OUTPUT_FAILED_EXAMPLE = {
    "status": "failed",
    "assistantReply": "标的识别暂时失败，请稍后重试，或直接提供更标准的股票代码。",
    "stock": None,
    "candidates": [],
    "focusPoints": [],
    "shouldCreateAnalysisTask": False,
    "terminate": True,
}

_FINAL_OUTPUT_UNSUPPORTED_EXAMPLE = {
    "status": "unsupported",
    "assistantReply": "当前只支持单只股票分析，请直接提供一家公司名称或股票代码。",
    "stock": None,
    "candidates": [],
    "focusPoints": [],
    "shouldCreateAnalysisTask": False,
    "terminate": True,
}

_FINAL_OUTPUT_PROMPT = """你现在需要基于已有对话和工具结果输出最终结构化结果。

输出要求：
1. 你必须只输出一个 JSON 对象，不要输出 markdown、代码块、解释、前后缀或任何额外文字。
2. 你的输出必须以字符 {{ 开始，并以字符 }} 结束。
3. 禁止输出数组作为根节点；禁止输出 null、true、false、字符串或数字作为完整回复。
4. 禁止输出 XML、HTML、标签片段、函数调用片段、tool call 残片、DSML 标记或类似 </...> 的内容。
5. JSON 字段必须严格符合 AgentResolutionResult schema。
6. 必须使用字段名 status，不要使用 state、resolution 或其他别名。
7. 必须使用字段名 assistantReply，不要使用 reply、assistant_message、message 或其他别名。
8. candidates 必须始终是数组；没有候选时输出 []，不要输出 null。
9. stock 字段仅在 need_confirm 或 resolved 时提供；其他状态输出 null。
10. shouldCreateAnalysisTask 仅在 resolved 时为 true。
11. terminate 在 resolved、unsupported、failed 时为 true。
12. 如果工具结果中出现 error，请优先输出 failed，并给出清晰中文提示。
13. 如果你无法完全确定正确状态，也必须输出一个合法 JSON 对象；默认输出合法的 failed 对象，绝不能输出非法 JSON。
14. focusPoints 仅保留真正与分析目标相关的关注点。

下面是 AgentResolutionResult 的 JSON Schema：
{schema_json}

下面是几个合法示例：

need_confirm 示例：
{need_confirm_example_json}

resolved 示例：
{resolved_example_json}

failed 示例：
{failed_example_json}

unsupported 示例：
{unsupported_example_json}

再次强调：
- 最终答案只能是一个 JSON 对象。
- 不要重复工具结果。
- 不要解释你的推理。
- 不要输出任何对象之外的字符。
"""

_FINAL_OUTPUT_PROMPT_PARTIALS = {
    "schema_json": json.dumps(
        AgentResolutionResult.model_json_schema(), ensure_ascii=False, indent=2
    ),
    "need_confirm_example_json": json.dumps(
        _FINAL_OUTPUT_EXAMPLE, ensure_ascii=False, indent=2
    ),
    "resolved_example_json": json.dumps(
        _FINAL_OUTPUT_RESOLVED_EXAMPLE, ensure_ascii=False, indent=2
    ),
    "failed_example_json": json.dumps(
        _FINAL_OUTPUT_FAILED_EXAMPLE, ensure_ascii=False, indent=2
    ),
    "unsupported_example_json": json.dumps(
        _FINAL_OUTPUT_UNSUPPORTED_EXAMPLE, ensure_ascii=False, indent=2
    ),
}


class ResolutionAgent:
    def __init__(self, *, stock_lookup_gateway: StockLookupGateway, llm: Any | None = None):
        self.stock_lookup_gateway = stock_lookup_gateway
        self._llm = llm

    def resolve(self, *, context: ResolutionAgentContext) -> AgentResolutionResult:
        llm = self._get_llm()
        if llm is None:
            result = _build_failed_result(
                "标的识别服务当前不可用，请稍后重试。",
            )
            logger.info(
                "resolution_agent_completed round=%s status=%s fallback=%s candidate_count=%s",
                context.currentRound,
                result.status,
                False,
                len(result.candidates),
            )
            return result

        try:
            result = self._run_llm_agent(context=context, llm=llm)
            logger.info(
                "resolution_agent_completed round=%s status=%s fallback=%s candidate_count=%s",
                context.currentRound,
                result.status,
                False,
                len(result.candidates),
            )
            return result
        except Exception as exc:  # pragma: no cover - network/provider dependent
            logger.warning("resolution_agent_llm_failed error=%s", exc)
            result = _build_failed_result(
                "标的识别暂时失败，请稍后重试，或直接提供更标准的股票代码。",
            )
            logger.info(
                "resolution_agent_completed round=%s status=%s fallback=%s candidate_count=%s",
                context.currentRound,
                result.status,
                False,
                len(result.candidates),
            )
            return result

    def _run_llm_agent(self, *, context: ResolutionAgentContext, llm: Any) -> AgentResolutionResult:
        tools = self._build_tools()
        tools_by_name: dict[str, BaseTool] = {tool_item.name: tool_item for tool_item in tools}

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _TOOL_SYSTEM_PROMPT),
                ("human", "{input_text}"),
            ]
        )
        history = prompt.format_messages(input_text=_build_agent_input(context))
        tool_llm = llm.bind_tools(tools)

        for _ in range(_MAX_TOOL_ROUNDS + 1):
            append_runtime_user_trace(
                phase="resolution",
                event="llm_input",
                inputPhase="tool_reasoning",
                inputPreview=_build_llm_input_preview(history),
            )
            ai_message = tool_llm.invoke(history)
            history.append(ai_message)
            append_runtime_user_trace(
                phase="resolution",
                event="llm_output",
                outputPhase="tool_reasoning",
                outputPreview=_extract_text(ai_message),
                toolCallCount=len(getattr(ai_message, "tool_calls", None) or []),
            )
            if not getattr(ai_message, "tool_calls", None):
                break
            for tool_call in ai_message.tool_calls[:2]:
                tool_result = _invoke_tool_call(
                    tools_by_name=tools_by_name,
                    tool_name=tool_call["name"],
                    args=tool_call.get("args", {}),
                )
                history.append(
                    ToolMessage(
                        content=json.dumps(tool_result, ensure_ascii=False),
                        tool_call_id=tool_call["id"],
                    )
                )

        final_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _FINAL_OUTPUT_PROMPT),
                MessagesPlaceholder(variable_name="history"),
            ]
        )
        final_prompt = final_prompt.partial(**_FINAL_OUTPUT_PROMPT_PARTIALS)
        final_messages = final_prompt.format_messages(history=history)
        append_runtime_user_trace(
            phase="resolution",
            event="llm_input",
            inputPhase="final_output",
            inputPreview=_build_llm_input_preview(final_messages, max_chars=1200),
        )
        final_llm = llm.bind(
            response_format={"type": "json_object"},
        )
        final_response = final_llm.invoke(final_messages)
        append_runtime_user_trace(
            phase="resolution",
            event="llm_output",
            outputPhase="final_output",
            outputPreview=_extract_text(final_response),
        )
        result = _parse_agent_resolution_result(final_response)
        return _normalize_agent_result(result)

    def _build_tools(self):
        gateway = self.stock_lookup_gateway

        @tool
        def search_stock_candidates(
            query: str, market_hints: list[str] | None = None, limit: int = 5
        ) -> dict:
            """根据干净的搜索词搜索股票候选。
            query 必须是提取后的 ticker、公司名或中文简称，不能包含原始用户句子中的动词或无关汉字。
            例如 "帮我看一下MU" → query="MU"；"分析英伟达" → query="英伟达"；"mu.us" → query="MU"。
            market_hints 可选，如 ["US"]、["HK"]、["CN"]。"""
            try:
                candidates = gateway.search_stock_candidates(
                    query=query,
                    market_hints=market_hints,
                    limit=limit,
                )
                return {"candidates": [candidate.model_dump() for candidate in candidates]}
            except Exception as exc:
                return {"error": str(exc), "candidates": []}

        @tool
        def get_stock_profile(ticker: str) -> dict:
            """查询单个股票的标准资料，用于确认前校验。"""
            try:
                candidate = gateway.get_stock_profile(ticker=ticker)
            except Exception as exc:
                return {"error": str(exc)}
            if candidate is None:
                return {"error": "Stock profile not found"}
            return candidate.model_dump()

        return [search_stock_candidates, get_stock_profile]

    def _get_llm(self) -> Any | None:
        if self._llm is not None:
            return self._llm

        provider = DEFAULT_CONFIG.get("llm_provider")
        model = DEFAULT_CONFIG.get("quick_think_llm")
        if not provider or not model:
            return None

        try:
            return create_llm_client(
                provider=provider,
                model=model,
                base_url=DEFAULT_CONFIG.get("backend_url"),
                timeout=DEFAULT_CONFIG.get("llm_timeout", 120),
                max_retries=DEFAULT_CONFIG.get("llm_max_retries", 1),
            ).get_llm()
        except Exception as exc:  # pragma: no cover - provider/runtime dependent
            logger.warning("resolution_agent_llm_init_failed error=%s", exc)
            return None


def _build_agent_input(context: ResolutionAgentContext) -> str:
    pending_json = (
        json.dumps(context.pendingResolution.model_dump(mode="json"), ensure_ascii=False)
        if context.pendingResolution
        else "null"
    )
    return (
        f"current_message: {context.currentMessage}\n"
        f"current_round: {context.currentRound}\n"
        f"analysis_prompt: {context.analysisPrompt or '无'}\n"
        f"prior_resolution_summary: {context.priorResolutionSummary or '无'}\n"
        f"pending_resolution: {pending_json}\n"
    )


def _invoke_tool_call(
    *,
    tools_by_name: dict[str, BaseTool],
    tool_name: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    tool_func = tools_by_name.get(tool_name)
    if tool_func is None:
        return {"error": f"Unknown tool: {tool_name}"}
    logger.info("resolution_agent_tool_call tool=%s args=%s", tool_name, args)
    result = tool_func.invoke(args)
    if not isinstance(result, dict):
        return {"error": f"Tool {tool_name} returned unsupported payload type"}
    logger.info(
        "resolution_agent_tool_result tool=%s has_error=%s candidate_count=%s",
        tool_name,
        "error" in result,
        len(result.get("candidates", [])),
    )
    return result


def _normalize_agent_result(result: AgentResolutionResult) -> AgentResolutionResult:
    if result.status == "resolved":
        result.shouldCreateAnalysisTask = True
        result.terminate = True
    elif result.status in {"unsupported", "failed"}:
        result.shouldCreateAnalysisTask = False
        result.terminate = True
    else:
        result.shouldCreateAnalysisTask = False
    if result.status == "need_confirm" and result.stock and not result.candidates:
        result.candidates = [result.stock]
    return result


def _parse_agent_resolution_result(response: Any) -> AgentResolutionResult:
    content = getattr(response, "content", "") if response else ""
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)
        content = "\n".join(part for part in text_parts if part)
    if not isinstance(content, str):
        raise ValueError("LLM returned non-text response for final structured output")

    payload_text = content.strip()
    if not payload_text:
        raise ValueError("LLM returned empty structured output")

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", payload_text, flags=re.S)
        if not match:
            logger.warning("resolution_agent_invalid_output raw_response=%s", payload_text)
            raise
        payload = json.loads(match.group(0))
    try:
        return AgentResolutionResult.model_validate(payload)
    except Exception:
        logger.warning(
            "resolution_agent_invalid_payload payload=%s", json.dumps(payload, ensure_ascii=False)
        )
        raise


def _build_failed_result(message: str) -> AgentResolutionResult:
    return AgentResolutionResult(
        status="failed",
        assistantReply=message,
        candidates=[],
        focusPoints=[],
        shouldCreateAnalysisTask=False,
        terminate=True,
    )


def _build_llm_input_preview(value: Any, max_chars: int = 800) -> str:
    text = _extract_text(value).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...[truncated]"


def _extract_text(response: Any) -> str:
    content = getattr(response, "content", "") if response else response
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)
            else:
                text_parts.append(str(item))
        return "\n".join(part for part in text_parts if part).strip()
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return str(content).strip()
