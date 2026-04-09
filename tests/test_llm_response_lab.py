import json
import sys
import tempfile
import unittest
from pathlib import Path


VALIDATION_ROOT = Path(__file__).resolve().parents[1] / "validation" / "llm-response-lab"
if str(VALIDATION_ROOT) not in sys.path:
    sys.path.insert(0, str(VALIDATION_ROOT))

from llm_response_lab.loader import ProviderConfig, load_cases, load_provider_configs
from llm_response_lab.providers import extract_usage
from llm_response_lab.runner import ValidationRunner


class FakeResponse:
    def __init__(self, content, usage_metadata=None, response_metadata=None):
        self.content = content
        self.usage_metadata = usage_metadata
        self.response_metadata = response_metadata or {}


class FakeLLM:
    def __init__(self, response):
        self.response = response

    def invoke(self, prompt):
        return self.response


class ValidationLabTests(unittest.TestCase):
    def test_load_cases_reads_prompt_from_source_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source_dir = repo_root / "results" / "sample"
            source_dir.mkdir(parents=True, exist_ok=True)
            source_path = source_dir / "case.json"
            source_path.write_text(
                json.dumps(
                    {
                        "stage_id": "research.debate",
                        "node_id": "Bull Researcher",
                        "input_type": "string",
                        "input": "prompt text",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            manifest_path = repo_root / "cases.json"
            manifest_path.write_text(
                json.dumps(
                    [
                        {
                            "case_id": "case-a",
                            "label": "Bull Researcher",
                            "source_path": "results/sample/case.json",
                            "source_field": "input",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            cases = load_cases(manifest_path, repo_root)

            self.assertEqual(len(cases), 1)
            self.assertEqual(cases[0].case_id, "case-a")
            self.assertEqual(cases[0].prompt, "prompt text")
            self.assertEqual(cases[0].prompt_chars, len("prompt text"))

    def test_load_provider_configs_reads_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "providers.json"
            config_path.write_text(
                json.dumps(
                    [
                        {
                            "provider_key": "deepseek",
                            "display_name": "DeepSeek",
                            "client_type": "openai_compatible",
                            "base_url": "https://api.deepseek.com/v1",
                            "model": "deepseek-chat",
                            "api_key_env": "DEEPSEEK_API_KEY",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            providers = load_provider_configs(config_path)

            self.assertEqual(len(providers), 1)
            self.assertEqual(providers[0].provider_key, "deepseek")
            self.assertEqual(providers[0].client_type, "openai_compatible")

    def test_extract_usage_supports_multiple_metadata_shapes(self):
        response = FakeResponse(
            "ok",
            usage_metadata={"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
        )
        usage = extract_usage(response)
        self.assertEqual(
            usage,
            {
                "usage_prompt_tokens": 11,
                "usage_completion_tokens": 7,
                "usage_total_tokens": 18,
            },
        )

        response = FakeResponse(
            "ok",
            response_metadata={"token_usage": {"prompt_tokens": 5, "completion_tokens": 9}},
        )
        usage = extract_usage(response)
        self.assertEqual(usage["usage_prompt_tokens"], 5)
        self.assertEqual(usage["usage_completion_tokens"], 9)
        self.assertEqual(usage["usage_total_tokens"], 14)

    def test_runner_writes_outputs_and_preserves_null_usage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source_dir = repo_root / "results" / "sample"
            source_dir.mkdir(parents=True, exist_ok=True)
            source_path = source_dir / "case.json"
            source_path.write_text(
                json.dumps(
                    {
                        "stage_id": "research.debate",
                        "node_id": "Research Manager",
                        "input_type": "string",
                        "input": "prompt text",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            manifest_path = repo_root / "cases.json"
            manifest_path.write_text(
                json.dumps(
                    [
                        {
                            "case_id": "case-a",
                            "label": "Research Manager",
                            "source_path": "results/sample/case.json",
                            "source_field": "input",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            cases = load_cases(manifest_path, repo_root)
            provider = ProviderConfig(
                provider_key="deepseek",
                display_name="DeepSeek",
                client_type="openai_compatible",
                base_url="https://api.deepseek.com/v1",
                model="deepseek-chat",
                api_key_env="DEEPSEEK_API_KEY",
            )

            def fake_factory(_provider):
                return FakeLLM(FakeResponse("response text"))

            runner = ValidationRunner(repo_root / "outputs", llm_factory=fake_factory)
            run_dir, results = runner.run(cases=cases, providers=[provider])

            self.assertEqual(len(results), 1)
            self.assertTrue(results[0].success)
            self.assertIsNone(results[0].usage_total_tokens)
            self.assertTrue((run_dir / "results.jsonl").exists())
            self.assertTrue((run_dir / "summary.csv").exists())
            self.assertTrue((run_dir / "summary.md").exists())
            self.assertTrue((run_dir / "responses" / "case-a" / "deepseek.md").exists())

            records = [
                json.loads(line)
                for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertIsNone(records[0]["usage_total_tokens"])


if __name__ == "__main__":
    unittest.main()
