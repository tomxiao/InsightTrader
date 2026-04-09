from __future__ import annotations

import argparse
import logging
import os
import time

from ta_service.adapters.tradingagents_runner import RunnerRequest, TradingAgentsRunner
from ta_service.config.settings import get_settings
from ta_service.db.mongo import create_mongo_client, get_database
from ta_service.db.redis import create_redis_client
from ta_service.repos.analysis_tasks import AnalysisTaskRepository
from ta_service.repos.conversations import ConversationRepository
from ta_service.repos.messages import MessageRepository
from ta_service.repos.reports import ReportRepository
from ta_service.repos.task_events import TaskEventRepository
from ta_service.workers.queue import AnalysisJobQueue

LOGGER = logging.getLogger(__name__)


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
        self.report_repo = ReportRepository(self.mongo_db)
        self.task_event_repo = TaskEventRepository(self.mongo_db)
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
        runner_request = RunnerRequest(
            ticker=job.ticker,
            trade_date=job.tradeDate,
            selected_analysts=job.selectedAnalysts or ["market", "social", "news", "fundamentals"],
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
        self.conversation_repo.update_current_task(
            conversation_id=job.conversationId,
            user_id=job.userId,
            task_id=job.taskId,
            status="analyzing",
        )
        self.message_repo.create(
            conversation_id=job.conversationId,
            role="system",
            message_type="task_status",
            content={"text": "已开始执行分析任务"},
        )

        try:
            result = self.runner.run_analysis(runner_request)
            report = self.report_repo.create(
                task_id=job.taskId,
                conversation_id=job.conversationId,
                user_id=job.userId,
                stock_symbol=job.ticker,
                title=f"{job.ticker} 分析报告",
                summary=result.executive_summary,
                executive_summary=result.executive_summary,
                content_markdown=result.complete_report_markdown,
                trace_dir=str(result.run_context.trace_dir),
            )
            self.task_repo.update_status(
                job.taskId,
                status="completed",
                stageId="portfolio.decision",
                currentStep="分析已完成",
                message="分析已完成",
                elapsedTime=int(time.time() - started_at),
                remainingTime=0,
                reportId=report["id"],
                runId=result.run_context.run_id,
                traceDir=str(result.run_context.trace_dir),
            )
            self.task_event_repo.create(
                task_id=job.taskId,
                event_type="task.completed",
                stage_id="portfolio.decision",
                payload={
                    "reportId": report["id"],
                    "runId": result.run_context.run_id,
                    "traceDir": str(result.run_context.trace_dir),
                },
            )
            self.conversation_repo.update_current_task(
                conversation_id=job.conversationId,
                user_id=job.userId,
                task_id=job.taskId,
                status="report_ready",
                report_id=report["id"],
            )
            self.message_repo.create(
                conversation_id=job.conversationId,
                role="assistant",
                message_type="summary_card",
                content={"text": result.executive_summary or "分析已完成"},
            )
            self.message_repo.create(
                conversation_id=job.conversationId,
                role="assistant",
                message_type="report_card",
                content={"reportId": report["id"], "title": report["title"]},
            )
        except Exception as exc:
            LOGGER.exception("analysis job failed: %s", job.taskId)
            self.task_repo.update_status(
                job.taskId,
                status="failed",
                currentStep="分析执行失败",
                message=str(exc),
                elapsedTime=int(time.time() - started_at),
            )
            self.task_event_repo.create(
                task_id=job.taskId,
                event_type="task.failed",
                payload={"error": str(exc)},
            )
            self.conversation_repo.update_current_task(
                conversation_id=job.conversationId,
                user_id=job.userId,
                task_id=job.taskId,
                status="failed",
            )
            self.message_repo.create(
                conversation_id=job.conversationId,
                role="system",
                message_type="error",
                content={"text": str(exc)},
            )
        finally:
            self.queue.release_user_lock(job.userId)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one analysis task and exit.")
    parser.add_argument("--task-id", required=True, help="Analysis task id to process")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    AnalysisTaskRunner().run_once(args.task_id)


if __name__ == "__main__":
    main()
