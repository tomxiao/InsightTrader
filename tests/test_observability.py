import json
import tempfile
import time
import unittest
from pathlib import Path

import pandas as pd

from tradingagents.dataflows.config import clear_runtime_context, set_runtime_context
from tradingagents.observability import (
    NODE_TRACE_FILENAME,
    RUN_TRACE_FILENAME,
    NodeEventTracker,
    StageEventTracker,
    emit_trace_event,
    persist_research_debate_llm_input,
)
from tradingagents.dataflows.indicator_utils import compute_indicator_report


class ObservabilityTests(unittest.TestCase):
    def tearDown(self):
        clear_runtime_context()

    def test_emit_trace_event_writes_target_file_and_run_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_context = {"trace_dir": temp_dir, "run_id": "run-test"}

            emit_trace_event(
                "route_events.jsonl",
                "route.decision",
                runtime_context=runtime_context,
                method="get_stock_data",
                vendor_chain=["tushare"],
            )

            route_event_path = Path(temp_dir) / "route_events.jsonl"
            run_trace_path = Path(temp_dir) / RUN_TRACE_FILENAME
            self.assertTrue(route_event_path.exists())
            self.assertTrue(run_trace_path.exists())

            route_event = json.loads(route_event_path.read_text(encoding="utf-8").strip())
            run_trace_event = json.loads(run_trace_path.read_text(encoding="utf-8").strip())
            self.assertEqual(route_event["event"], "route.decision")
            self.assertEqual(run_trace_event["event"], "route.decision")
            self.assertEqual(route_event["vendor_chain"], ["tushare"])

    def test_stage_event_tracker_emits_started_and_completed_for_pending_to_completed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = StageEventTracker(
                runtime_context={"trace_dir": temp_dir, "run_id": "run-stage"},
                stall_threshold_s=0,
            )

            tracker.sync(
                {"portfolio.decision": "completed"},
                {"portfolio.decision": {"agent_name": "Portfolio Manager"}},
            )

            stage_events = [
                json.loads(line)
                for line in (Path(temp_dir) / "stage_events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["event"] for event in stage_events], ["stage.started", "stage.completed"])
            self.assertEqual(stage_events[-1]["stage_id"], "portfolio.decision")

    def test_stage_event_tracker_emits_stalled_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = StageEventTracker(
                runtime_context={"trace_dir": temp_dir, "run_id": "run-stalled"},
                stall_threshold_s=0.02,
                check_interval_s=0.005,
            )
            tracker.start_watchdog()
            try:
                tracker.sync({"research.debate": "in_progress"})
                time.sleep(0.05)
            finally:
                tracker.stop_watchdog()

            stage_events = [
                json.loads(line)
                for line in (Path(temp_dir) / "stage_events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            event_names = [event["event"] for event in stage_events]
            self.assertIn("stage.started", event_names)
            self.assertIn("stage.stalled", event_names)

    def test_node_event_tracker_emits_started_and_completed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = NodeEventTracker(
                runtime_context={"trace_dir": temp_dir, "run_id": "run-node"},
                stall_threshold_s=0,
            )

            tracker.mark_started(
                node_id="Research Manager",
                stage_id="research.debate",
                node_kind="agent",
            )
            tracker.mark_completed()

            node_events = [
                json.loads(line)
                for line in (Path(temp_dir) / NODE_TRACE_FILENAME).read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["event"] for event in node_events], ["node.started", "node.completed"])
            self.assertEqual(node_events[-1]["node_id"], "Research Manager")
            self.assertEqual(node_events[-1]["stage_id"], "research.debate")
            self.assertGreaterEqual(node_events[-1]["duration_ms"], 0)

    def test_node_event_tracker_emits_stalled_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = NodeEventTracker(
                runtime_context={"trace_dir": temp_dir, "run_id": "run-node-stalled"},
                stall_threshold_s=0.02,
                check_interval_s=0.005,
            )
            tracker.start_watchdog()
            try:
                tracker.mark_started(
                    node_id="Research Manager",
                    stage_id="research.debate",
                    node_kind="agent",
                )
                time.sleep(0.05)
            finally:
                tracker.stop_watchdog()

            node_events = [
                json.loads(line)
                for line in (Path(temp_dir) / NODE_TRACE_FILENAME).read_text(encoding="utf-8").splitlines()
            ]
            event_names = [event["event"] for event in node_events]
            self.assertIn("node.started", event_names)
            self.assertIn("node.stalled", event_names)

    def test_persist_research_debate_llm_input_writes_prompt_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            set_runtime_context(
                trace_dir=temp_dir,
                run_id="run-research-input",
                current_stage_id="research.debate",
                current_node_id="Research Manager",
            )

            saved_path = persist_research_debate_llm_input(
                "debate prompt",
                provider="minimax",
                model="MiniMax-M2.5",
            )

            self.assertIsNotNone(saved_path)
            payload = json.loads(Path(saved_path).read_text(encoding="utf-8"))
            self.assertEqual(payload["stage_id"], "research.debate")
            self.assertEqual(payload["node_id"], "Research Manager")
            self.assertEqual(payload["input"], "debate prompt")

    def test_persist_research_debate_llm_input_skips_other_stages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            set_runtime_context(
                trace_dir=temp_dir,
                run_id="run-trader-input",
                current_stage_id="trader.plan",
                current_node_id="Trader",
            )

            saved_path = persist_research_debate_llm_input("trader prompt")

            self.assertIsNone(saved_path)
            self.assertFalse((Path(temp_dir) / "llm_inputs").exists())

    def test_compute_indicator_report_uses_stockstats_date_index_without_error(self):
        dataframe = pd.DataFrame(
            {
                "Date": pd.date_range("2026-03-01", periods=30, freq="D").strftime("%Y-%m-%d"),
                "Open": [100 + idx for idx in range(30)],
                "High": [101 + idx for idx in range(30)],
                "Low": [99 + idx for idx in range(30)],
                "Close": [100.5 + idx for idx in range(30)],
                "Volume": [1000 + idx * 10 for idx in range(30)],
            }
        )

        report = compute_indicator_report(dataframe, "vwma", "2026-03-30", 5)

        self.assertIn("## vwma values from 2026-03-25 to 2026-03-30:", report)
        self.assertIn("2026-03-30:", report)
        self.assertNotIn("Invalid number of return arguments", report)


if __name__ == "__main__":
    unittest.main()
