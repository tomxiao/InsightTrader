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

    def test_running_task_ignores_snapshot_elapsed_and_uses_created_at(self):
        """运行中任务即使有 elapsedTime 快照值，也应动态计算 now-createdAt，不返回快照。"""
        created_at = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
        response = build_task_status_response(
            {
                "taskId": "task-3",
                "status": "running",
                "symbol": "TSLA",
                "stageId": "research.debate",
                "createdAt": created_at,
                "elapsedTime": 30,  # stage 开始时写入的快照值，应被忽略
            }
        )

        self.assertEqual(response.status, "running")
        # 动态计算结果应约为 90s，远大于快照值 30s
        self.assertGreaterEqual(response.elapsedTime or 0, 80)
        self.assertLessEqual(response.elapsedTime or 0, 110)

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
            }
        )

        self.assertEqual(response.status, "completed")
        self.assertEqual(response.elapsedTime, 321)
        self.assertEqual(response.remainingTime, 0)


if __name__ == "__main__":
    unittest.main()
