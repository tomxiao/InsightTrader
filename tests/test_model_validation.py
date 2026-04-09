import unittest
import warnings
from unittest.mock import MagicMock, patch

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.llm_clients.anthropic_client import AnthropicClient
from tradingagents.llm_clients.base_client import BaseLLMClient
from tradingagents.llm_clients.factory import create_llm_client
from tradingagents.llm_clients.model_catalog import get_known_models
from tradingagents.llm_clients.openai_client import OpenAIClient
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

    def test_factory_routes_deepseek_to_openai_client(self):
        client = create_llm_client("deepseek", "deepseek-chat")
        self.assertIsInstance(client, OpenAIClient)
        self.assertEqual(client.provider, "deepseek")

    def test_deepseek_uses_dedicated_base_url_and_api_key(self):
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-deepseek-key"}, clear=False):
            with patch("tradingagents.llm_clients.openai_client.NormalizedChatOpenAI") as chat_cls:
                client = OpenAIClient(
                    "deepseek-chat",
                    base_url="https://unused.example.com/v1",
                    provider="deepseek",
                    timeout=123,
                    max_retries=4,
                )
                client.get_llm()

        kwargs = chat_cls.call_args.kwargs
        self.assertEqual(kwargs["model"], "deepseek-chat")
        self.assertEqual(kwargs["base_url"], "https://api.deepseek.com/v1")
        self.assertEqual(kwargs["api_key"], "test-deepseek-key")
        self.assertEqual(kwargs["timeout"], 123)
        self.assertEqual(kwargs["max_retries"], 4)
        self.assertNotIn("use_responses_api", kwargs)

    def test_minimax_filters_anthropic_only_kwargs(self):
        with patch.dict("os.environ", {"MINIMAX_API_KEY": "test-minimax-key"}, clear=False):
            with patch(
                "tradingagents.llm_clients.anthropic_client.NormalizedChatAnthropic"
            ) as chat_cls:
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

    def test_trading_graph_forwards_timeout_and_retry_kwargs_to_llm_clients(self):
        client = MagicMock()
        client.get_llm.return_value = object()

        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "minimax"
        config["llm_timeout"] = 321
        config["llm_max_retries"] = 7

        with patch(
            "tradingagents.graph.trading_graph.create_llm_client", return_value=client
        ) as create_client:
            with patch("tradingagents.graph.trading_graph.FinancialSituationMemory"):
                with patch("tradingagents.graph.trading_graph.GraphSetup") as graph_setup_cls:
                    with patch("tradingagents.graph.trading_graph.Reflector"):
                        with patch("tradingagents.graph.trading_graph.SignalProcessor"):
                            with patch.object(
                                TradingAgentsGraph, "_create_tool_nodes", return_value={}
                            ):
                                graph_setup_cls.return_value.setup_graph.return_value = object()
                                TradingAgentsGraph(selected_analysts=["market"], config=config)

        self.assertEqual(create_client.call_count, 2)
        for call in create_client.call_args_list:
            self.assertEqual(call.kwargs["timeout"], 321)
            self.assertEqual(call.kwargs["max_retries"], 7)

    def test_default_config_uses_deepseek_chat(self):
        self.assertEqual(DEFAULT_CONFIG["llm_provider"], "deepseek")
        self.assertEqual(DEFAULT_CONFIG["backend_url"], "https://api.deepseek.com/v1")
        self.assertEqual(DEFAULT_CONFIG["deep_think_llm"], "deepseek-chat")
        self.assertEqual(DEFAULT_CONFIG["quick_think_llm"], "deepseek-chat")
