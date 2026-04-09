import os
from dataclasses import dataclass
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from tradingagents.llm_clients.base_client import normalize_content

from .loader import ProviderConfig


@dataclass
class ValidationResponse:
    content: str
    usage: dict[str, int | None]
    metadata: dict[str, Any]


def _extract_int(metadata: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, int):
            return value
    return None


def extract_usage(response: Any) -> dict[str, int | None]:
    usage_metadata = getattr(response, "usage_metadata", None)
    response_metadata = getattr(response, "response_metadata", None) or {}
    nested_candidates = []
    if isinstance(usage_metadata, dict):
        nested_candidates.append(usage_metadata)
    if isinstance(response_metadata.get("usage"), dict):
        nested_candidates.append(response_metadata["usage"])
    if isinstance(response_metadata.get("token_usage"), dict):
        nested_candidates.append(response_metadata["token_usage"])
    if isinstance(response_metadata, dict):
        nested_candidates.append(response_metadata)

    prompt_tokens = None
    completion_tokens = None
    total_tokens = None

    for candidate in nested_candidates:
        prompt_tokens = prompt_tokens or _extract_int(
            candidate,
            "input_tokens",
            "prompt_tokens",
            "prompt_token_count",
        )
        completion_tokens = completion_tokens or _extract_int(
            candidate,
            "output_tokens",
            "completion_tokens",
            "candidates_token_count",
        )
        total_tokens = total_tokens or _extract_int(
            candidate,
            "total_tokens",
            "total_token_count",
        )

    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "usage_prompt_tokens": prompt_tokens,
        "usage_completion_tokens": completion_tokens,
        "usage_total_tokens": total_tokens,
    }


def _build_openai_compatible_llm(config: ProviderConfig) -> ChatOpenAI:
    api_key = os.environ.get(config.api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing required environment variable: {config.api_key_env}")
    return ChatOpenAI(
        model=config.model,
        base_url=config.base_url,
        api_key=api_key,
        timeout=config.timeout,
        max_retries=config.max_retries,
        use_responses_api=False,
    )


def _build_anthropic_compatible_llm(config: ProviderConfig) -> ChatAnthropic:
    api_key = os.environ.get(config.api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing required environment variable: {config.api_key_env}")
    return ChatAnthropic(
        model=config.model,
        base_url=config.base_url,
        api_key=api_key,
        timeout=config.timeout,
        max_retries=config.max_retries,
    )


def build_validation_llm(config: ProviderConfig) -> Any:
    if config.client_type == "openai_compatible":
        return _build_openai_compatible_llm(config)
    if config.client_type == "anthropic_compatible":
        return _build_anthropic_compatible_llm(config)
    raise ValueError(f"Unsupported client_type: {config.client_type}")


def invoke_validation_case(llm: Any, prompt: Any) -> ValidationResponse:
    response = normalize_content(llm.invoke(prompt))
    response_metadata = getattr(response, "response_metadata", None) or {}
    return ValidationResponse(
        content=getattr(response, "content", ""),
        usage=extract_usage(response),
        metadata=response_metadata if isinstance(response_metadata, dict) else {},
    )
