from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from tradingagents.graph.lite_trading_graph import LiteTradingGraph
from tradingagents.graph.trading_graph import TradingAgentsGraph

DEFAULT_TEAM_ID = "lite"


@dataclass(frozen=True)
class ReportSectionSpec:
    key: str
    relative_path: str
    label: str
    required: bool = False
    reply_visible: bool = True


@dataclass(frozen=True)
class ReportContract:
    sections: tuple[ReportSectionSpec, ...]
    primary_summary_key: str


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    label: str
    stage_group: str


@dataclass(frozen=True)
class StageContract:
    stages: tuple[StageSpec, ...]


@dataclass(frozen=True)
class ReplyAgentSpec:
    agent_id: str
    description: str


@dataclass(frozen=True)
class AnalysisTeamSpec:
    team_id: str
    display_name: str
    analysis_orchestrator_factory: Callable[..., object] | None
    analysis_agent_ids: tuple[str, ...]
    default_selected_analysts: tuple[str, ...]
    report_contract: ReportContract
    reply_agent_spec: ReplyAgentSpec
    stage_contract: StageContract


FULL_REPORT_CONTRACT = ReportContract(
    sections=(
        ReportSectionSpec("decision", "5_portfolio/decision.md", "最终投资决策", required=True),
        ReportSectionSpec("trading_plan", "3_trading/trader.md", "交易计划"),
        ReportSectionSpec("fundamentals", "1_analysts/fundamentals.md", "基本面分析"),
        ReportSectionSpec("market", "1_analysts/market.md", "市场与技术分析"),
        ReportSectionSpec("news", "1_analysts/news.md", "新闻事件分析"),
        ReportSectionSpec("sentiment", "1_analysts/sentiment.md", "社交情绪分析"),
        ReportSectionSpec("bull_research", "2_research/bull.md", "多方研究"),
        ReportSectionSpec("bear_research", "2_research/bear.md", "空方研究"),
        ReportSectionSpec("research_mgr", "2_research/manager.md", "研究经理结论"),
        ReportSectionSpec("risk_aggr", "4_risk/aggressive.md", "激进风险评估"),
        ReportSectionSpec("risk_cons", "4_risk/conservative.md", "保守风险评估"),
        ReportSectionSpec("risk_neutral", "4_risk/neutral.md", "中立风险评估"),
    ),
    primary_summary_key="decision",
)

LITE_REPORT_CONTRACT = ReportContract(
    sections=(
        ReportSectionSpec("decision", "2_decision/summary.md", "最终投资结论", required=True),
        ReportSectionSpec("fundamentals", "1_analysts/fundamentals.md", "基本面分析"),
        ReportSectionSpec("market", "1_analysts/market.md", "市场与技术分析"),
        ReportSectionSpec("news", "1_analysts/news.md", "新闻事件分析"),
    ),
    primary_summary_key="decision",
)

FULL_STAGE_CONTRACT = StageContract(
    stages=(
        StageSpec("analysts.market", "市场分析", "analysts"),
        StageSpec("analysts.social", "情绪分析", "analysts"),
        StageSpec("analysts.news", "新闻分析", "analysts"),
        StageSpec("analysts.fundamentals", "基本面分析", "analysts"),
        StageSpec("research.debate", "研究辩论", "research"),
        StageSpec("trader.plan", "交易计划", "trader"),
        StageSpec("risk.debate", "风险辩论", "risk"),
        StageSpec("portfolio.decision", "组合决策", "portfolio"),
    )
)

LITE_STAGE_CONTRACT = StageContract(
    stages=(
        StageSpec("analysts.market", "市场分析", "analysts"),
        StageSpec("analysts.news", "新闻分析", "analysts"),
        StageSpec("analysts.fundamentals", "基本面分析", "analysts"),
        StageSpec("decision.finalize", "投资结论", "decision"),
    )
)

FULL_TEAM_SPEC = AnalysisTeamSpec(
    team_id="full",
    display_name="Full Analysis Team",
    analysis_orchestrator_factory=TradingAgentsGraph,
    analysis_agent_ids=(
        "Market Analyst",
        "Social Analyst",
        "News Analyst",
        "Fundamentals Analyst",
        "Bull Researcher",
        "Bear Researcher",
        "Research Manager",
        "Trader",
        "Aggressive Analyst",
        "Conservative Analyst",
        "Neutral Analyst",
        "Portfolio Manager",
    ),
    default_selected_analysts=("market", "social", "news", "fundamentals"),
    report_contract=FULL_REPORT_CONTRACT,
    reply_agent_spec=ReplyAgentSpec(
        agent_id="full_reply_agent",
        description="解读 full team 的多阶段完整报告",
    ),
    stage_contract=FULL_STAGE_CONTRACT,
)

LITE_TEAM_SPEC = AnalysisTeamSpec(
    team_id="lite",
    display_name="Lite Analysis Team",
    analysis_orchestrator_factory=LiteTradingGraph,
    analysis_agent_ids=(
        "Market Analyst",
        "News Analyst",
        "Fundamentals Analyst",
        "Decision Manager",
    ),
    default_selected_analysts=("market", "news", "fundamentals"),
    report_contract=LITE_REPORT_CONTRACT,
    reply_agent_spec=ReplyAgentSpec(
        agent_id="lite_reply_agent",
        description="解读 lite team 的轻量报告",
    ),
    stage_contract=LITE_STAGE_CONTRACT,
)

TEAM_REGISTRY: dict[str, AnalysisTeamSpec] = {
    FULL_TEAM_SPEC.team_id: FULL_TEAM_SPEC,
    LITE_TEAM_SPEC.team_id: LITE_TEAM_SPEC,
}


def normalize_team_id(team_id: str | None) -> str:
    value = (team_id or "").strip().lower()
    return value or DEFAULT_TEAM_ID


def get_team_spec(team_id: str | None) -> AnalysisTeamSpec:
    normalized = normalize_team_id(team_id)
    try:
        return TEAM_REGISTRY[normalized]
    except KeyError as exc:
        raise ValueError(f"Unknown analysis team: {normalized}") from exc


def get_section_specs(team_id: str | None) -> tuple[ReportSectionSpec, ...]:
    return get_team_spec(team_id).report_contract.sections


def get_section_labels(team_id: str | None = None) -> dict[str, str]:
    labels: dict[str, str] = {}
    for spec in TEAM_REGISTRY.values():
        for section in spec.report_contract.sections:
            labels[section.key] = section.label
    if team_id is None:
        return labels
    return {section.key: section.label for section in get_section_specs(team_id)}
