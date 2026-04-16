from __future__ import annotations

import argparse
import logging
import os
import time

from ta_service.adapters.tradingagents_runner import RunnerRequest, TradingAgentsRunner
from ta_service.config.settings import get_settings
from ta_service.db.mongo import create_mongo_client, get_database
from ta_service.db.redis import create_redis_client
from ta_service.models.message_types import MessageType
from ta_service.repos.analysis_tasks import AnalysisTaskRepository
from ta_service.repos.conversations import ConversationRepository
from ta_service.repos.messages import MessageRepository
from ta_service.repos.task_events import TaskEventRepository
from ta_service.runtime.status_mapper import resolve_node_message, resolve_stage_message
from ta_service.services.conversation_state_machine import ConversationStateMachine
from ta_service.teams import get_team_spec, normalize_team_id
from ta_service.workers.queue import AnalysisJobQueue

LOGGER = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _merge_stage_timeline(
    stage_timeline: dict[str, dict] | None,
    stage_snapshot: dict[str, str] | None,
) -> dict[str, dict]:
    timeline = {key: dict(value) for key, value in (stage_timeline or {}).items()}
    now = _utc_now_iso()
    for stage_id, status in (stage_snapshot or {}).items():
        item = timeline.setdefault(stage_id, {})
        previous_status = item.get("status")
        item["status"] = status
        if status in {"in_progress", "stalled", "completed", "failed"} and not item.get("startedAt"):
            item["startedAt"] = now
        if status in {"completed", "failed"} and previous_status != status and not item.get("completedAt"):
            item["completedAt"] = now
    return timeline


def _finalize_failed_stage_snapshot(
    stage_snapshot: dict[str, str] | None,
    failed_stage_id: str | None,
) -> dict[str, str]:
    snapshot = dict(stage_snapshot or {})
    if failed_stage_id:
        if failed_stage_id not in snapshot:
            snapshot[failed_stage_id] = "failed"
        for stage_id, status in list(snapshot.items()):
            if stage_id == failed_stage_id:
                snapshot[stage_id] = "failed"
            elif status == "in_progress":
                snapshot[stage_id] = "pending"
    return snapshot


class AnalysisTaskRunner:
    def __init__(self):
        self.settings = get_settings()
        self.mongo_client = create_mongo_client(self.settings)
        self.mongo_db = get_database(self.mongo_client, self.settings)
        self.redis_client = create_redis_client(self.settings)
        self.queue = AnalysisJobQueue(self.redis_client, self.settings)
        self.task_repo = AnalysisTaskRepository(self.mongo_db)
        self.conversation_repo = ConversationRepository(self.mongo_db)
        self.message_repo = MessageRepository(self.mongo_db)
        self.task_event_repo = TaskEventRepository(self.mongo_db)
        self.state_machine = ConversationStateMachine(conversation_repo=self.conversation_repo)
        self.runner = TradingAgentsRunner(self.settings)

    def close(self) -> None:
        self.mongo_client.close()
        self.redis_client.close()

    def run_once(self, task_id: str) -> None:
        LOGGER.info("ta_service analysis task runner started task_id=%s", task_id)
        try:
            job = self.queue.get_task_job(self.task_repo, task_id)
            if not job:
                LOGGER.warning("task runner received unknown task_id=%s", task_id)
                return
            self._process_job(job)
        finally:
            self.close()

    def _process_job(self, job) -> None:
        started_at = time.time()

        def on_stage_change(stage_id: str) -> None:
            label = resolve_stage_message(stage_id) or stage_id
            elapsed = int(time.time() - started_at)
            self.task_repo.update_status(
                job.taskId,
                stageId=stage_id,
                nodeId=None,
                currentStep=label,
                message=label,
                elapsedTime=elapsed,
            )
            self.task_event_repo.create(
                task_id=job.taskId,
                event_type="stage.started",
                stage_id=stage_id,
                payload={"message": label, "elapsedTime": elapsed},
            )
            self.message_repo.create(
                conversation_id=job.conversationId,
                role="system",
                message_type=MessageType.TASK_STATUS,
                content={"text": label, "stageId": stage_id},
            )

        def on_node_change(node_id: str, stage_id: str) -> None:
            """Agent node 变化时更新 task 文档（仅影响 taskProgress，不写消息流）。"""
            label = resolve_node_message(node_id) or resolve_stage_message(stage_id) or node_id
            elapsed = int(time.time() - started_at)
            self.task_repo.update_status(
                job.taskId,
                stageId=stage_id,
                nodeId=node_id,
                currentStep=label,
                message=label,
                elapsedTime=elapsed,
            )
            self.task_event_repo.create(
                task_id=job.taskId,
                event_type="node.started",
                stage_id=stage_id,
                payload={"nodeId": node_id, "message": label, "elapsedTime": elapsed},
            )

        def on_stage_snapshot(stage_snapshot: dict[str, str]) -> None:
            existing_task_doc = self.task_repo.get_by_task_id(job.taskId) or {}
            self.task_repo.update_status(
                job.taskId,
                stageSnapshot=stage_snapshot,
                stageTimeline=_merge_stage_timeline(
                    existing_task_doc.get("stageTimeline"),
                    stage_snapshot,
                ),
            )

        team_spec = get_team_spec(job.teamId)
        runner_request = RunnerRequest(
            ticker=job.ticker,
            trade_date=job.tradeDate,
            selected_analysts=job.selectedAnalysts or list(team_spec.default_selected_analysts),
            team_id=normalize_team_id(job.teamId),
            on_stage_change=on_stage_change,
            on_node_change=on_node_change,
            on_stage_snapshot=on_stage_snapshot,
        )
        diagnostics = self.runner.build_runtime_diagnostics(runner_request)
        diagnostics["worker"] = {
            "pid": os.getpid(),
            "cwd": os.getcwd(),
        }
        LOGGER.info(
            "analysis job diagnostics task_id=%s diagnostics=%s",
            job.taskId,
            diagnostics,
        )
        self.task_repo.update_status(
            job.taskId,
            status="running",
            stageId="analysts.market",
            currentStep="正在启动 TradingAgents 分析",
            message="正在启动 TradingAgents 分析",
        )
        self.task_event_repo.create(
            task_id=job.taskId,
            event_type="task.started",
            stage_id="analysts.market",
            payload={"message": "analysis started"},
        )
        self.task_event_repo.create(
            task_id=job.taskId,
            event_type="task.config_snapshot",
            stage_id="analysts.market",
            payload=diagnostics,
        )
        self.message_repo.create(
            conversation_id=job.conversationId,
            role="system",
            message_type=MessageType.TASK_STATUS,
            content={"text": "投资团队已开始分析，正在为你整理关键信息", "stageId": None},
        )

        try:
            result = self.runner.run_analysis(runner_request)
            trace_dir_str = str(result.run_context.trace_dir)
            terminal_stage_id = team_spec.stage_contract.stages[-1].stage_id
            self.task_repo.update_status(
                job.taskId,
                status="completed",
                stageId=terminal_stage_id,
                currentStep="分析已完成",
                message="分析已完成",
                elapsedTime=int(time.time() - started_at),
                remainingTime=0,
                runId=result.run_context.run_id,
                traceDir=trace_dir_str,
            )
            self.task_event_repo.create(
                task_id=job.taskId,
                event_type="task.completed",
                stage_id=terminal_stage_id,
                payload={
                    "runId": result.run_context.run_id,
                    "traceDir": trace_dir_str,
                },
            )
            self.state_machine.transition_unchecked(
                conversation_id=job.conversationId,
                user_id=job.userId,
                to_status="report_ready",
                task_id=job.taskId,
            )
            self.message_repo.create(
                conversation_id=job.conversationId,
                role="assistant",
                message_type=MessageType.SUMMARY_CARD,
                content={"text": result.executive_summary or "分析已完成"},
            )
        except Exception as exc:
            LOGGER.exception("analysis job failed: %s", job.taskId)
            existing_task_doc = self.task_repo.get_by_task_id(job.taskId) or {}
            failed_stage_snapshot = _finalize_failed_stage_snapshot(
                existing_task_doc.get("stageSnapshot"),
                existing_task_doc.get("stageId"),
            )
            failed_stage_timeline = _merge_stage_timeline(
                existing_task_doc.get("stageTimeline"),
                failed_stage_snapshot,
            )
            self.task_repo.update_status(
                job.taskId,
                status="failed",
                currentStep="分析执行失败",
                message=str(exc),
                elapsedTime=int(time.time() - started_at),
                stageSnapshot=failed_stage_snapshot,
                stageTimeline=failed_stage_timeline,
            )
            self.task_event_repo.create(
                task_id=job.taskId,
                event_type="task.failed",
                payload={"error": str(exc)},
            )
            self.state_machine.transition_unchecked(
                conversation_id=job.conversationId,
                user_id=job.userId,
                to_status="failed",
                task_id=job.taskId,
            )
            self.message_repo.create(
                conversation_id=job.conversationId,
                role="system",
                message_type=MessageType.ERROR,
                content={"text": "分析未能完成，请稍后重新发起分析请求。"},
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one analysis task and exit.")
    parser.add_argument("--task-id", required=True, help="Analysis task id to process")
    args = parser.parse_args()
    from ta_service.config.logging_config import setup_logging

    setup_logging()
    LOGGER.info("worker process started task_id=%s", args.task_id)
    AnalysisTaskRunner().run_once(args.task_id)


if __name__ == "__main__":
    main()
