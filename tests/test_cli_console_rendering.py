import io
import unittest
from unittest.mock import patch

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text

import cli.main as cli_main


class _EncodedStringIO:
    def __init__(self, encoding: str):
        self.encoding = encoding
        self._buffer = io.StringIO()

    def write(self, text):
        return self._buffer.write(text)

    def flush(self):
        return self._buffer.flush()

    def isatty(self):
        return False


class CliConsoleRenderingTests(unittest.TestCase):
    def test_render_console_markdown_falls_back_to_text_on_gbk_console(self):
        console = Console(file=_EncodedStringIO("gbk"), force_terminal=False)

        renderable = cli_main._render_console_markdown("* item", console)

        self.assertIsInstance(renderable, Text)
        self.assertEqual(renderable.plain, "* item")

    def test_render_console_markdown_keeps_markdown_on_utf8_console(self):
        console = Console(file=_EncodedStringIO("utf-8"), force_terminal=False)

        renderable = cli_main._render_console_markdown("* item", console)

        self.assertIsInstance(renderable, Markdown)

    def test_coerce_console_safe_text_replaces_unencodable_glyphs(self):
        console = Console(file=_EncodedStringIO("gbk"), force_terminal=False)

        safe_text = cli_main._coerce_console_safe_text("Rating • Sell", console)

        self.assertEqual(safe_text, "Rating ? Sell")

    def test_display_complete_report_survives_gbk_console_with_markdown_lists(self):
        gbk_console = Console(file=_EncodedStringIO("gbk"), force_terminal=False)
        final_state = {
            "market_report": "* buy signal",
            "investment_debate_state": {"judge_decision": "* hold"},
            "trader_investment_plan": "* trade plan",
            "risk_debate_state": {
                "aggressive_history": "* aggressive",
                "conservative_history": "* conservative",
                "neutral_history": "* neutral",
                "judge_decision": "* sell",
            },
        }

        with patch.object(cli_main, "console", gbk_console):
            cli_main.display_complete_report(final_state)
