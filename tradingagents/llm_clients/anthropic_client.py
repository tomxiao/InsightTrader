import os
from typing import Any, Optional

from langchain_anthropic import ChatAnthropic

from .base_client import BaseLLMClient, normalize_content
from .validators import validate_model

_ANTHROPIC_PASSTHROUGH_KWARGS = (
    "timeout", "max_retries", "api_key", "max_tokens",
    "callbacks", "http_client", "http_async_client", "effort",
)

_MINIMAX_PASSTHROUGH_KWARGS = (
    "timeout", "max_retries", "api_key", "max_tokens",
    "callbacks", "http_client", "http_async_client",
)

_PROVIDER_PASSTHROUGH_KWARGS = {
    "anthropic": _ANTHROPIC_PASSTHROUGH_KWARGS,
    "minimax": _MINIMAX_PASSTHROUGH_KWARGS,
}

_PROVIDER_API_KEY_ENV = {
    "minimax": "MINIMAX_API_KEY",
}


class NormalizedChatAnthropic(ChatAnthropic):
    """ChatAnthropic with normalized content output.

    Claude models with extended thinking or tool use return content as a
    list of typed blocks. This normalizes to string for consistent
    downstream handling.
    """

    def invoke(self, input, config=None, **kwargs):
        return normalize_content(super().invoke(input, config, **kwargs))


class AnthropicClient(BaseLLMClient):
    """Client for Anthropic-compatible providers."""

    def __init__(
        self,
        model: str,
        base_url: Optional[str] = None,
        provider: str = "anthropic",
        **kwargs,
    ):
        super().__init__(model, base_url, **kwargs)
        self.provider = provider.lower()

    def get_llm(self) -> Any:
        """Return configured ChatAnthropic instance."""
        self.warn_if_unknown_model()
        llm_kwargs = {"model": self.model}

        if self.base_url:
            llm_kwargs["base_url"] = self.base_url

        if "api_key" not in self.kwargs:
            api_key_env = _PROVIDER_API_KEY_ENV.get(self.provider)
            if api_key_env:
                api_key = os.environ.get(api_key_env)
                if api_key:
                    llm_kwargs["api_key"] = api_key

        passthrough_kwargs = _PROVIDER_PASSTHROUGH_KWARGS.get(
            self.provider, _ANTHROPIC_PASSTHROUGH_KWARGS
        )
        for key in passthrough_kwargs:
            if key in self.kwargs:
                llm_kwargs[key] = self.kwargs[key]

        return NormalizedChatAnthropic(**llm_kwargs)

    def validate_model(self) -> bool:
        """Validate model for the configured Anthropic-compatible provider."""
        return validate_model(self.provider, self.model)
