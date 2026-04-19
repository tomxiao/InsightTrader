from __future__ import annotations

from backtest.report_parser import parse_report_text


BUY_TEXT = """
1. **分析日期**：2026-02-23
3. **截面价格**：29.68美元。依据技术分析报告，此为2026-02-20收盘价。
4. **建议行动**：择机买入
9. **入场方式**：回调参与。明确等待价格回调至24.50-25.50美元关键支撑区间，并观察出现缩量企稳信号后，再进行分批建仓。
10. **失效条件**：
    * 股价放量跌破23.20美元支撑位，且短期内无法收回。
    * 公司明确表示出口许可问题将长期化。
"""

HOLD_TEXT = """
1. **分析日期**：2026-04-17
3. **截面价格**：81.78美元。依据市场报告中的分析基准信息。
4. **建议行动**：保持观望
9. **入场方式**：当前建议保持观望，暂不出手。
10. **失效条件**：
    * 股价放量突破并站稳82-83美元阻力区。
"""


def test_parse_report_text_extracts_buy_signal_fields() -> None:
    signal = parse_report_text(BUY_TEXT, ticker="AXTI")

    assert signal.ticker == "AXTI"
    assert signal.trade_date == "2026-02-23"
    assert signal.action == "buy_on_pullback"
    assert signal.reference_price == 29.68
    assert signal.entry_zone_low == 24.5
    assert signal.entry_zone_high == 25.5
    assert signal.invalidation_price == 23.2


def test_parse_report_text_extracts_hold_signal() -> None:
    signal = parse_report_text(HOLD_TEXT, ticker="AXTI")

    assert signal.action == "hold"
    assert signal.reference_price == 81.78
    assert signal.entry_zone_low is None
    assert signal.entry_zone_high is None


def test_parse_reference_price_prefers_value_with_dollar_unit_over_date() -> None:
    text = """
1. **分析日期**：2026-01-05
3. **截面价格**：核心参考价格为 2026-01-02 的收盘价 16.76 美元（技术报告明确给出）。
4. **建议行动**：择机买入
9. **入场方式**：回调参与，等待 15.00-15.60 美元。
10. **失效条件**：
    * 价格放量跌破14.70美元并无法快速收回。
"""

    signal = parse_report_text(text, ticker="AXTI")

    assert signal.reference_price == 16.76
    assert signal.invalidation_price == 14.7


def test_parse_invalidation_price_uses_price_not_moving_average_day_count() -> None:
    text = """
1. **分析日期**：2026-01-12
3. **截面价格**：22.99美元。
4. **建议行动**：择机买入
9. **入场方式**：回调参与，等待20.00-20.50美元。
10. **失效条件**：
    * 价格放量跌破50日移动平均线（当前约13.15美元，动态上移），中期上升趋势结构被破坏。
    * 2026年2月财报显示积压订单未如预期转化。
"""

    signal = parse_report_text(text, ticker="AXTI")

    assert signal.invalidation_price == 13.15


def test_parse_reference_price_accepts_leading_number_without_dollar_unit() -> None:
    text = """
1. **分析日期**：2026-03-18
3. **截面价格**：44.36。依据为技术分析报告明确给出的核心参考价格，即2026-03-17收盘价。
4. **建议行动**：择机买入
9. **入场方式**：回调参与，等待 38.50-42.00。
10. **失效条件**：
    * 股价日线收盘价有效跌破38.50。
"""

    signal = parse_report_text(text, ticker="AXTI")

    assert signal.reference_price == 44.36


def test_parse_report_text_accepts_bold_label_with_colon_inside_markup() -> None:
    text = """
**分析日期：** 2026-03-03
**截面价格：** 46.32 美元（核心参考技术报告中 2026-03-02 的收盘价）
**建议行动：** 保持观望
**入场方式：** （当前建议为“保持观望”）**暂不出手**。
**失效条件：**
1. **价格未经历显著回调便直接放量突破前高（47.03美元）。**
2. **地缘政治紧张局势突然且实质性缓和。**
**适合的场景：**
- 当前空仓，寻求清晰风险收益比的交易者。
"""

    signal = parse_report_text(text, ticker="AXTI")

    assert signal.trade_date == "2026-03-03"
    assert signal.action == "hold"
    assert signal.reference_price == 46.32
