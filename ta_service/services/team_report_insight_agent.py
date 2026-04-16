from __future__ import annotations

from typing import Any, Iterator, Protocol

from ta_service.models.report_insight import ReportInsightContext, ReportInsightResult
from ta_service.services.report_context_loader import ReportContextLoader
from ta_service.services.report_insight_agent import ReportInsightAgent
from ta_service.teams import DEFAULT_TEAM_ID, normalize_team_id


class _ReplyAgent(Protocol):
    def answer(self, *, context: ReportInsightContext) -> ReportInsightResult: ...

    def answer_events(self, *, context: ReportInsightContext) -> Iterator[dict[str, Any]]: ...


class FullReportInsightAgent:
    def __init__(self, *, report_context_loader: ReportContextLoader, llm: Any | None = None):
        self._delegate = ReportInsightAgent(report_context_loader=report_context_loader, llm=llm)

    def answer(self, *, context: ReportInsightContext) -> ReportInsightResult:
        return self._delegate.answer(context=context.model_copy(update={"team_id": "full"}))

    def answer_events(self, *, context: ReportInsightContext) -> Iterator[dict[str, Any]]:
        return self._delegate.answer_events(
            context=context.model_copy(update={"team_id": "full"})
        )


class LiteReportInsightAgent:
    def __init__(self, *, report_context_loader: ReportContextLoader, llm: Any | None = None):
        self._delegate = ReportInsightAgent(report_context_loader=report_context_loader, llm=llm)

    def answer(self, *, context: ReportInsightContext) -> ReportInsightResult:
        return self._delegate.answer(context=context.model_copy(update={"team_id": "lite"}))

    def answer_events(self, *, context: ReportInsightContext) -> Iterator[dict[str, Any]]:
        return self._delegate.answer_events(
            context=context.model_copy(update={"team_id": "lite"})
        )


class TeamReportInsightAgent:
    def __init__(
        self,
        *,
        full_reply_agent: FullReportInsightAgent,
        lite_reply_agent: LiteReportInsightAgent,
    ):
        self._agents_by_team: dict[str, _ReplyAgent] = {
            "full": full_reply_agent,
            "lite": lite_reply_agent,
        }

    def answer(self, *, context: ReportInsightContext) -> ReportInsightResult:
        return self._resolve_agent(context.team_id).answer(context=context)

    def answer_events(self, *, context: ReportInsightContext) -> Iterator[dict[str, Any]]:
        return self._resolve_agent(context.team_id).answer_events(context=context)

    def _resolve_agent(self, team_id: str | None) -> _ReplyAgent:
        normalized = normalize_team_id(team_id)
        return self._agents_by_team.get(normalized, self._agents_by_team[DEFAULT_TEAM_ID])
