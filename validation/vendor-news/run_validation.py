import argparse
import importlib
import sys
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parents[1]
for path in (REPO_ROOT, SCRIPT_ROOT):
    text = str(path)
    if text in sys.path:
        sys.path.remove(text)
    sys.path.insert(0, text)

vendor_news_lab = importlib.import_module("vendor_news_lab")
NewsValidationRunner = vendor_news_lab.NewsValidationRunner
load_news_cases = vendor_news_lab.load_news_cases
load_vendor_configs = vendor_news_lab.load_vendor_configs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate stock news vendors and keyword expansion."
    )
    parser.add_argument(
        "--cases",
        default="validation/vendor-news-lab/cases/market_news_cases.json",
        help="Path to the case manifest JSON.",
    )
    parser.add_argument(
        "--vendors",
        default="validation/vendor-news-lab/configs/vendors.json",
        help="Path to the vendor config JSON.",
    )
    parser.add_argument(
        "--output-root",
        default="validation/vendor-news-lab/outputs",
        help="Directory where validation outputs will be written.",
    )
    parser.add_argument(
        "--mode",
        choices=["all", "vendor-comparison", "keyword-expansion"],
        default="all",
        help="Validation mode to run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = REPO_ROOT
    load_dotenv(repo_root / ".env")

    cases = load_news_cases(repo_root / args.cases)
    vendors = load_vendor_configs(repo_root / args.vendors)
    runner = NewsValidationRunner(repo_root / args.output_root)
    modes = ("vendor-comparison", "keyword-expansion") if args.mode == "all" else (args.mode,)
    run_dir, results = runner.run(cases=cases, vendors=vendors, modes=modes)

    print(f"validation_run_dir={run_dir}")
    print(f"total_calls={len(results)}")
    print(f"ok_calls={sum(1 for item in results if item.outcome == 'ok')}")
    print(f"empty_calls={sum(1 for item in results if item.outcome == 'empty')}")
    print(f"error_calls={sum(1 for item in results if item.outcome == 'error')}")
    print(f"unsupported_calls={sum(1 for item in results if item.outcome == 'unsupported')}")


if __name__ == "__main__":
    main()
