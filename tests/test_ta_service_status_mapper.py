import unittest
from datetime import datetime, timedelta, timezone

from ta_service.runtime.status_mapper import build_task_status_response


class TaskStatusMapperTests(unittest.TestCase):
    def test_running_task_uses_created_at_to_compute_elapsed_and_remaining(self):
        created_at = (datetime.now(timezone.utc) - timedelta(seconds=45)).isoformat()
        response = build_task_status_response(
            {
                "taskId": "task-1",
                "status": "running",
                "symbol": "AAPL",
                "stageId": "analysts.market",
                "createdAt": created_at,
            }
        )

        self.assertEqual(response.taskId, "task-1")
        self.assertEqual(response.status, "running")
        self.assertGreaterEqual(response.elapsedTime or 0, 40)
        self.assertLessEqual(response.elapsedTime or 0, 60)
        self.assertEqual(response.currentStep, "正在获取市场与技术数据")
        self.assertIsNotNone(response.remainingTime)
        self.assertGreaterEqual(response.remainingTime or 0, 0)

    def test_completed_task_preserves_explicit_elapsed_time(self):
        response = build_task_status_response(
            {
                "taskId": "task-2",
                "status": "completed",
                "symbol": "700",
                "currentStep": "分析已完成",
                "message": "分析已完成",
                "elapsedTime": 321,
                "remainingTime": 0,
                "reportId": "report-1",
            }
        )

        self.assertEqual(response.status, "completed")
        self.assertEqual(response.elapsedTime, 321)
        self.assertEqual(response.remainingTime, 0)
        self.assertEqual(response.reportId, "report-1")


if __name__ == "__main__":
    unittest.main()
