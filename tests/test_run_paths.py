import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from tradingagents.run_paths import build_run_directory_name, resolve_results_run_dir


class RunPathTests(unittest.TestCase):
    def test_build_run_directory_name_uses_ticker_and_minute_precision_start_time(self):
        started_at = datetime(2026, 4, 9, 13, 17, 42)

        directory_name = build_run_directory_name("688679", started_at)

        self.assertEqual(directory_name, "688679_2026_0409_1317")

    def test_resolve_results_run_dir_appends_suffix_when_same_minute_directory_exists(self):
        started_at = datetime(2026, 4, 9, 13, 17, 42)

        with tempfile.TemporaryDirectory() as temp_dir:
            first_dir = resolve_results_run_dir(temp_dir, "688679", started_at)
            first_dir.mkdir()

            second_dir = resolve_results_run_dir(temp_dir, "688679", started_at)

            self.assertEqual(first_dir.name, "688679_2026_0409_1317")
            self.assertEqual(second_dir, Path(temp_dir) / "688679_2026_0409_1317_02")


if __name__ == "__main__":
    unittest.main()
