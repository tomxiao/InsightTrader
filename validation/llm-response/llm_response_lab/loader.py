import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ValidationCase:
    case_id: str
    label: str
    source_path: str
    stage_id: str
    node_id: str
    input_type: str
    prompt: Any
    prompt_chars: int
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ProviderConfig:
    provider_key: str
    display_name: str
    client_type: str
    base_url: str
    model: str
    api_key_env: str
    timeout: int = 240
    max_retries: int = 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _count_prompt_chars(prompt: Any) -> int:
    if prompt is None:
        return 0
    if isinstance(prompt, str):
        return len(prompt)
    return len(json.dumps(prompt, ensure_ascii=False))


def load_cases(manifest_path: str | Path, repo_root: str | Path) -> list[ValidationCase]:
    manifest = _read_json(Path(manifest_path))
    repo_root = Path(repo_root)
    cases: list[ValidationCase] = []
    for item in manifest:
        source_path = repo_root / item["source_path"]
        source_payload = _read_json(source_path)
        source_field = item.get("source_field", "input")
        prompt = source_payload[source_field]
        cases.append(
            ValidationCase(
                case_id=item["case_id"],
                label=item["label"],
                source_path=item["source_path"],
                stage_id=source_payload.get("stage_id", ""),
                node_id=source_payload.get("node_id", ""),
                input_type=source_payload.get("input_type", "string"),
                prompt=prompt,
                prompt_chars=_count_prompt_chars(prompt),
                metadata={
                    "run_id": source_payload.get("run_id"),
                    "captured_at": source_payload.get("captured_at"),
                    "provider": source_payload.get("provider"),
                    "model": source_payload.get("model"),
                },
            )
        )
    return cases


def load_provider_configs(config_path: str | Path) -> list[ProviderConfig]:
    config_payload = _read_json(Path(config_path))
    return [ProviderConfig(**item) for item in config_payload]
