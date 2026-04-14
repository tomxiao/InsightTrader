from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ta_service.api.deps import get_analysis_service, get_current_user
from ta_service.models.analysis import AnalysisTaskStatusResponse, CreateAnalysisTaskRequest
from ta_service.models.auth import MobileUser
from ta_service.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/tasks/{task_id}/status", response_model=AnalysisTaskStatusResponse)
def get_task_status(
    task_id: str,
    current_user: MobileUser = Depends(get_current_user),
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisTaskStatusResponse:
    response = analysis_service.get_task_status(task_id=task_id, user_id=current_user.id)
    if not response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return response


@router.post(
    "/tasks", response_model=AnalysisTaskStatusResponse, status_code=status.HTTP_202_ACCEPTED
)
def create_task(
    payload: CreateAnalysisTaskRequest,
    current_user: MobileUser = Depends(get_current_user),
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisTaskStatusResponse:
    return analysis_service.create_task(user_id=current_user.id, payload=payload)
