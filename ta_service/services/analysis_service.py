from __future__ import annotations

from fastapi import HTTPException, status

from ta_service.config.settings import Settings
from ta_service.contracts.analysis import build_analysis_status
from ta_service.models.analysis import AnalysisTaskStatusResponse, CreateAnalysisTaskRequest
from ta_service.repos.analysis_tasks import AnalysisTaskRepository
from ta_service.repos.reports import ReportRepository
from ta_service.workers.launcher import spawn_analysis_task_runner
from ta_service.workers.queue import AnalysisJobQueue


class AnalysisService:
    def __init__(
        self,
        *,
        task_repo: AnalysisTaskRepository,
        report_repo: ReportRepository,
        queue: AnalysisJobQueue,
        settings: Settings,
    ):
        self.task_repo = task_repo
        self.report_repo = report_repo
        self.queue = queue
        self.settings = settings

    def get_task_status(self, *, task_id: str, user_id: str) -> AnalysisTaskStatusResponse | None:
        document = self.task_repo.get_for_user(task_id=task_id, user_id=user_id)
        if not document:
            return None
        return build_analysis_status(document)

    def create_task(
        self,
        *,
        user_id: str,
        payload: CreateAnalysisTaskRequest,
    ) -> AnalysisTaskStatusResponse:
        active_task = self.task_repo.get_active_for_user(user_id)
        if active_task:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A task is already running for this user",
            )

        if not self.queue.acquire_user_lock(user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unable to acquire analysis lock for this user",
            )

        document = self.task_repo.create(
            user_id=user_id,
            conversation_id=payload.conversationId,
            ticker=payload.ticker,
            trade_date=payload.tradeDate,
            prompt=payload.prompt,
            selected_analysts=payload.selectedAnalysts,
        )

        try:
            spawn_analysis_task_runner(document["taskId"])
            self.task_repo.update_status(
                document["taskId"],
                status="pending",
                currentStep="任务已启动",
                message="任务已启动",
            )
            document["status"] = "pending"
            document["currentStep"] = "任务已启动"
            document["message"] = "任务已启动"
        except Exception as exc:
            self.queue.release_user_lock(user_id)
            self.task_repo.update_status(
                document["taskId"],
                status="failed",
                currentStep="任务启动失败",
                message=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to launch analysis task runner",
            ) from exc
        return build_analysis_status(document)
