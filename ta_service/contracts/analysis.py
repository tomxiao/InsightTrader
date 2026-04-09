from __future__ import annotations

from ta_service.models.analysis import AnalysisTaskStatusResponse
from ta_service.runtime.status_mapper import build_task_status_response


def build_analysis_status(document: dict) -> AnalysisTaskStatusResponse:
    return build_task_status_response(document)
