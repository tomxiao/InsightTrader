import unittest
import warnings
from unittest.mock import patch

from tradingagents.llm_clients.base_client import BaseLLMClient
from tradingagents.llm_clients.anthropic_client import AnthropicClient
from tradingagents.llm_clients.factory import create_llm_client
from tradingagents.llm_clients.model_catalog import get_known_models
from tradingagents.llm_clients.validators import validate_model


class DummyLLMClient(BaseLLMClient):
    def __init__(self, provider: str, model: str):
        self.provider = provider
        super().__init__(model)

    def get_llm(self):
        self.warn_if_unknown_model()
        return object()

    def validate_model(self) -> bool:
        return validate_model(self.provider, self.model)


class ModelValidationTests(unittest.TestCase):
    def test_cli_catalog_models_are_all_validator_approved(self):
        for provider, models in get_known_models().items():
            if provider in ("ollama", "openrouter"):
                continue

            for model in models:
                with self.subTest(provider=provider, model=model):
                    self.assertTrue(validate_model(provider, model))

    def test_unknown_model_emits_warning_for_strict_provider(self):
        client = DummyLLMClient("openai", "not-a-real-openai-model")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            client.get_llm()

        self.assertEqual(len(caught), 1)
        self.assertIn("not-a-real-openai-model", str(caught[0].message))
        self.assertIn("openai", str(caught[0].message))

    def test_openrouter_and_ollama_accept_custom_models_without_warning(self):
        for provider in ("openrouter", "ollama"):
            client = DummyLLMClient(provider, "custom-model-name")

            with self.subTest(provider=provider):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    client.get_llm()

                self.assertEqual(caught, [])

    def test_factory_routes_minimax_to_anthropic_client(self):
        client = create_llm_client("minimax", "MiniMax-M2.7")
        self.assertIsInstance(client, AnthropicClient)
        self.assertEqual(client.provider, "minimax")

    def test_minimax_filters_anthropic_only_kwargs(self):
        with patch.dict("os.environ", {"MINIMAX_API_KEY": "test-minimax-key"}, clear=False):
            with patch("tradingagents.llm_clients.anthropic_client.NormalizedChatAnthropic") as chat_cls:
                client = AnthropicClient(
                    "MiniMax-M2.7",
                    base_url="https://api.minimaxi.com/anthropic",
                    provider="minimax",
                    effort="high",
                    max_tokens=256,
                )
                client.get_llm()

        kwargs = chat_cls.call_args.kwargs
        self.assertEqual(kwargs["model"], "MiniMax-M2.7")
        self.assertEqual(kwargs["base_url"], "https://api.minimaxi.com/anthropic")
        self.assertEqual(kwargs["api_key"], "test-minimax-key")
        self.assertEqual(kwargs["max_tokens"], 256)
        self.assertNotIn("effort", kwargs)
