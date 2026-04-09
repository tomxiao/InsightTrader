from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ta_service.api.deps import get_current_user, get_report_service
from ta_service.models.auth import MobileUser
from ta_service.models.report import ReportDetailResponse
from ta_service.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{report_id}/detail", response_model=ReportDetailResponse)
def get_report_detail(
    report_id: str,
    current_user: MobileUser = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
) -> ReportDetailResponse:
    report = report_service.get_report(user_id=current_user.id, report_id=report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report
