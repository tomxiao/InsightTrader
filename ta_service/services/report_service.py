from __future__ import annotations

from ta_service.contracts.reports import build_report_detail
from ta_service.models.report import ReportDetailResponse
from ta_service.repos.reports import ReportRepository


class ReportService:
    def __init__(self, *, report_repo: ReportRepository):
        self.report_repo = report_repo

    def get_report(self, *, user_id: str, report_id: str) -> ReportDetailResponse | None:
        document = self.report_repo.get_for_user(report_id=report_id, user_id=user_id)
        if not document:
            return None
        return build_report_detail(document)
