import csv
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .loader import ProviderConfig, ValidationCase
from .providers import build_validation_llm, invoke_validation_case


@dataclass
class ValidationResult:
    case_id: str
    case_label: str
    source_path: str
    stage_id: str
    node_id: str
    input_type: str
    prompt_chars: int
    provider: str
    provider_key: str
    client_type: str
    model: str
    started_at: str
    duration_ms: int
    success: bool
    error_type: str | None
    error_message: str | None
    response_text: str
    response_chars: int
    usage_prompt_tokens: int | None
    usage_completion_tokens: int | None
    usage_total_tokens: int | None
    raw_metadata: dict[str, Any]

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


class ValidationRunner:
    def __init__(
        self,
        output_root: str | Path,
        llm_factory: Callable[[ProviderConfig], Any] = build_validation_llm,
    ) -> None:
        self.output_root = Path(output_root)
        self.llm_factory = llm_factory

    def run(
        self,
        *,
        cases: list[ValidationCase],
        providers: list[ProviderConfig],
    ) -> tuple[Path, list[ValidationResult]]:
        run_dir = self.output_root / datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        results: list[ValidationResult] = []

        for provider in providers:
            llm = None
            provider_init_error: Exception | None = None
            try:
                llm = self.llm_factory(provider)
            except Exception as exc:
                provider_init_error = exc

            for case in cases:
                results.append(self._run_single_case(case, provider, llm, provider_init_error))

        self._write_outputs(run_dir, results)
        return run_dir, results

    def _run_single_case(
        self,
        case: ValidationCase,
        provider: ProviderConfig,
        llm: Any,
        provider_init_error: Exception | None = None,
    ) -> ValidationResult:
        started_at = datetime.now().isoformat()
        start = time.monotonic()
        if provider_init_error is not None:
            return ValidationResult(
                case_id=case.case_id,
                case_label=case.label,
                source_path=case.source_path,
                stage_id=case.stage_id,
                node_id=case.node_id,
                input_type=case.input_type,
                prompt_chars=case.prompt_chars,
                provider=provider.display_name,
                provider_key=provider.provider_key,
                client_type=provider.client_type,
                model=provider.model,
                started_at=started_at,
                duration_ms=0,
                success=False,
                error_type=provider_init_error.__class__.__name__,
                error_message=str(provider_init_error),
                response_text="",
                response_chars=0,
                usage_prompt_tokens=None,
                usage_completion_tokens=None,
                usage_total_tokens=None,
                raw_metadata={},
            )

        try:
            response = invoke_validation_case(llm, case.prompt)
        except Exception as exc:
            return ValidationResult(
                case_id=case.case_id,
                case_label=case.label,
                source_path=case.source_path,
                stage_id=case.stage_id,
                node_id=case.node_id,
                input_type=case.input_type,
                prompt_chars=case.prompt_chars,
                provider=provider.display_name,
                provider_key=provider.provider_key,
                client_type=provider.client_type,
                model=provider.model,
                started_at=started_at,
                duration_ms=int((time.monotonic() - start) * 1000),
                success=False,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
                response_text="",
                response_chars=0,
                usage_prompt_tokens=None,
                usage_completion_tokens=None,
                usage_total_tokens=None,
                raw_metadata={},
            )

        return ValidationResult(
            case_id=case.case_id,
            case_label=case.label,
            source_path=case.source_path,
            stage_id=case.stage_id,
            node_id=case.node_id,
            input_type=case.input_type,
            prompt_chars=case.prompt_chars,
            provider=provider.display_name,
            provider_key=provider.provider_key,
            client_type=provider.client_type,
            model=provider.model,
            started_at=started_at,
            duration_ms=int((time.monotonic() - start) * 1000),
            success=True,
            error_type=None,
            error_message=None,
            response_text=response.content,
            response_chars=len(response.content),
            usage_prompt_tokens=response.usage["usage_prompt_tokens"],
            usage_completion_tokens=response.usage["usage_completion_tokens"],
            usage_total_tokens=response.usage["usage_total_tokens"],
            raw_metadata=response.metadata,
        )

    def _write_outputs(self, run_dir: Path, results: list[ValidationResult]) -> None:
        self._write_results_jsonl(run_dir / "results.jsonl", results)
        self._write_summary_csv(run_dir / "summary.csv", results)
        self._write_summary_md(run_dir / "summary.md", results)
        self._write_responses(run_dir / "responses", results)

    def _write_results_jsonl(self, path: Path, results: list[ValidationResult]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for result in results:
                handle.write(json.dumps(result.to_record(), ensure_ascii=False, default=str) + "\n")

    def _write_summary_csv(self, path: Path, results: list[ValidationResult]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {
                "case_id": result.case_id,
                "case_label": result.case_label,
                "provider": result.provider,
                "provider_key": result.provider_key,
                "model": result.model,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "prompt_chars": result.prompt_chars,
                "response_chars": result.response_chars,
                "usage_prompt_tokens": result.usage_prompt_tokens,
                "usage_completion_tokens": result.usage_completion_tokens,
                "usage_total_tokens": result.usage_total_tokens,
                "error_type": result.error_type,
                "error_message": result.error_message,
            }
            for result in results
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
            if rows:
                writer.writeheader()
                writer.writerows(rows)

    def _write_summary_md(self, path: Path, results: list[ValidationResult]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Validation Summary",
            "",
            f"- total_calls: {len(results)}",
            f"- successful_calls: {sum(1 for item in results if item.success)}",
            f"- failed_calls: {sum(1 for item in results if not item.success)}",
            "",
            "| Case | Provider | Model | Success | Duration(ms) | Prompt Tokens | Completion Tokens | Total Tokens |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
        for result in results:
            lines.append(
                "| {case} | {provider} | {model} | {success} | {duration} | {pt} | {ct} | {tt} |".format(
                    case=result.case_id,
                    provider=result.provider,
                    model=result.model,
                    success="yes" if result.success else "no",
                    duration=result.duration_ms,
                    pt=result.usage_prompt_tokens if result.usage_prompt_tokens is not None else "",
                    ct=result.usage_completion_tokens if result.usage_completion_tokens is not None else "",
                    tt=result.usage_total_tokens if result.usage_total_tokens is not None else "",
                )
            )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_responses(self, base_dir: Path, results: list[ValidationResult]) -> None:
        for result in results:
            target = base_dir / result.case_id / f"{result.provider_key}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            lines = [
                f"# {result.case_label} / {result.provider}",
                "",
                f"- model: `{result.model}`",
                f"- success: `{result.success}`",
                f"- duration_ms: `{result.duration_ms}`",
                f"- usage_total_tokens: `{result.usage_total_tokens}`",
                "",
            ]
            if result.success:
                lines.append(result.response_text)
            else:
                lines.extend(
                    [
                        "## Error",
                        "",
                        f"- error_type: `{result.error_type}`",
                        f"- error_message: `{result.error_message}`",
                    ]
                )
            target.write_text("\n".join(lines) + "\n", encoding="utf-8")
