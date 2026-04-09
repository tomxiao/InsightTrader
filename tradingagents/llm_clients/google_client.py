import time
from typing import Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI

from tradingagents.observability import emit_llm_event

from .base_client import BaseLLMClient, normalize_content
from .validators import validate_model


class NormalizedChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
    """ChatGoogleGenerativeAI with normalized content output.

    Gemini 3 models return content as list of typed blocks.
    This normalizes to string for consistent downstream handling.
    """

    def invoke(self, input, config=None, **kwargs):
        started_at = time.monotonic()
        provider = getattr(self, "_tradingagents_provider", "google")
        model = getattr(self, "_tradingagents_model", getattr(self, "model", None))
        emit_llm_event(
            "llm.started",
            llm_input=input,
            provider=provider,
            model=model,
        )
        try:
            response = super().invoke(input, config, **kwargs)
        except Exception as exc:
            emit_llm_event(
                "llm.failed",
                llm_input=input,
                duration_ms=int((time.monotonic() - started_at) * 1000),
                provider=provider,
                model=model,
                error=exc,
            )
            raise

        emit_llm_event(
            "llm.completed",
            duration_ms=int((time.monotonic() - started_at) * 1000),
            provider=provider,
            model=model,
        )
        return normalize_content(response)


class GoogleClient(BaseLLMClient):
    """Client for Google Gemini models."""

    def __init__(self, model: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(model, base_url, **kwargs)

    def get_llm(self) -> Any:
        """Return configured ChatGoogleGenerativeAI instance."""
        self.warn_if_unknown_model()
        llm_kwargs = {"model": self.model}

        if self.base_url:
            llm_kwargs["base_url"] = self.base_url

        for key in ("timeout", "max_retries", "callbacks", "http_client", "http_async_client"):
            if key in self.kwargs:
                llm_kwargs[key] = self.kwargs[key]

        # Unified api_key maps to provider-specific google_api_key
        google_api_key = self.kwargs.get("api_key") or self.kwargs.get("google_api_key")
        if google_api_key:
            llm_kwargs["google_api_key"] = google_api_key

        # Map thinking_level to appropriate API param based on model
        # Gemini 3 Pro: low, high
        # Gemini 3 Flash: minimal, low, medium, high
        # Gemini 2.5: thinking_budget (0=disable, -1=dynamic)
        thinking_level = self.kwargs.get("thinking_level")
        if thinking_level:
            model_lower = self.model.lower()
            if "gemini-3" in model_lower:
                # Gemini 3 Pro doesn't support "minimal", use "low" instead
                if "pro" in model_lower and thinking_level == "minimal":
                    thinking_level = "low"
                llm_kwargs["thinking_level"] = thinking_level
            else:
                # Gemini 2.5: map to thinking_budget
                llm_kwargs["thinking_budget"] = -1 if thinking_level == "high" else 0

        llm = NormalizedChatGoogleGenerativeAI(**llm_kwargs)
        llm._tradingagents_provider = "google"
        llm._tradingagents_model = self.model
        return llm

    def validate_model(self) -> bool:
        """Validate model for Google."""
        return validate_model("google", self.model)
