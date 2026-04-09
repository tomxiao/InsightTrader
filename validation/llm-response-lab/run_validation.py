import argparse
import importlib
import sys
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

llm_response_lab = importlib.import_module("llm_response_lab")
ValidationRunner = llm_response_lab.ValidationRunner
load_cases = llm_response_lab.load_cases
load_provider_configs = llm_response_lab.load_provider_configs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare responses across LLM providers.")
    parser.add_argument(
        "--cases",
        default="validation/llm-response-lab/cases/research_debate_cases.json",
        help="Path to the case manifest JSON.",
    )
    parser.add_argument(
        "--providers",
        default="validation/llm-response-lab/configs/providers.json",
        help="Path to the provider config JSON.",
    )
    parser.add_argument(
        "--output-root",
        default="validation/llm-response-lab/outputs",
        help="Directory where validation outputs will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")

    cases = load_cases(args.cases, repo_root)
    providers = load_provider_configs(args.providers)
    runner = ValidationRunner(repo_root / args.output_root)
    run_dir, results = runner.run(cases=cases, providers=providers)

    success_count = sum(1 for item in results if item.success)
    print(f"validation_run_dir={run_dir}")
    print(f"total_calls={len(results)}")
    print(f"successful_calls={success_count}")
    print(f"failed_calls={len(results) - success_count}")


if __name__ == "__main__":
    main()
