from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalEvidence:
    scenario_type: str | None = None
    direction_bias: str | None = None
    trend_integrity: str | None = None
    catalyst_state: str | None = None
    extension_state: str | None = None
    risk_state: str | None = None
    entry_posture: str | None = None

    def is_complete(self) -> bool:
        return all(
            value is not None
            for value in (
                self.direction_bias,
                self.trend_integrity,
                self.catalyst_state,
                self.extension_state,
                self.risk_state,
                self.entry_posture,
            )
        )


_DIRECTION_MAP = {
    "看多": "bullish",
    "中性": "neutral",
    "看空": "bearish",
}

_SCENARIO_MAP = {
    "公司催化趋势型": "company_catalyst_trend",
    "催化后高波动整理型": "post_catalyst_high_volatility",
    "Beta情绪技术驱动型": "beta_technical_sentiment",
}

_TREND_MAP = {
    "完整": "complete",
    "边际走弱": "weakening",
    "已破坏": "broken",
}

_CATALYST_MAP = {
    "支撑中": "supportive",
    "消化中": "digesting",
    "缺位": "absent",
}

_EXTENSION_MAP = {
    "正常": "normal",
    "延展": "extended",
    "过热": "overstretched",
}

_RISK_MAP = {
    "低": "low",
    "中": "medium",
    "高": "high",
    "风险未主导": "low",
    "风险与机会拉锯": "medium",
    "风险主导": "high",
}

_ENTRY_POSTURE_MAP = {
    "可直接参与": "immediate",
    "等待回调": "wait_pullback",
    "等待确认": "wait_confirmation",
    "暂不参与": "no_entry",
}

_ACTION_TO_TREND = {
    "buy_now": "趋势延续",
    "buy_on_pullback": "趋势延续",
    "hold": "震荡等待确认",
    "sell": "风险主导",
}


def normalize_signal_evidence(evidence: SignalEvidence) -> SignalEvidence:
    return SignalEvidence(
        scenario_type=_SCENARIO_MAP.get((evidence.scenario_type or "").strip()),
        direction_bias=_DIRECTION_MAP.get((evidence.direction_bias or "").strip()),
        trend_integrity=_TREND_MAP.get((evidence.trend_integrity or "").strip()),
        catalyst_state=_CATALYST_MAP.get((evidence.catalyst_state or "").strip()),
        extension_state=_EXTENSION_MAP.get((evidence.extension_state or "").strip()),
        risk_state=_RISK_MAP.get((evidence.risk_state or "").strip()),
        entry_posture=_ENTRY_POSTURE_MAP.get((evidence.entry_posture or "").strip()),
    )


def derive_action_from_evidence(evidence: SignalEvidence) -> str | None:
    normalized = normalize_signal_evidence(evidence)
    if not normalized.is_complete():
        return None

    def can_buy_pullback_with_direction_bias() -> bool:
        if normalized.direction_bias == "bullish":
            if normalized.entry_posture != "wait_pullback":
                return False
            if normalized.trend_integrity not in {"complete", "weakening"}:
                return False
            if normalized.catalyst_state not in {"supportive", "digesting"}:
                return False
            # 高波动催化股在首轮消化阶段，仍可能属于“等待更好位置参与”而不是应当直接观望。
            return normalized.risk_state in {"low", "medium", "high"}

        if normalized.direction_bias == "neutral":
            if normalized.entry_posture == "wait_pullback":
                # 只放宽“中性但仍允许等待回调参与”的组合，避免把 wait_confirmation / no_entry 一并推回买入。
                return (
                    normalized.trend_integrity in {"complete", "weakening"}
                    and normalized.catalyst_state in {"digesting", "absent"}
                    and normalized.extension_state in {"normal", "extended", "overstretched"}
                )

            if normalized.entry_posture == "no_entry":
                # round27 之后剩余的主要坏样本集中在“中性 + 暂不参与”，但其中一部分其实仍属于高波动消化期里的等待型偏多。
                if (
                    normalized.trend_integrity == "complete"
                    and normalized.catalyst_state == "digesting"
                    and normalized.extension_state == "extended"
                    and normalized.risk_state in {"medium", "high"}
                ):
                    return True

                # round29 之后剩余的保守残差进一步收敛到一小批“催化后高波动整理型 + 边际走弱 + 高风险”样本。
                # 对这类样本，当前规则若仍停留在 no_entry -> hold，往往会系统性错过高 beta 反弹。
                return (
                    normalized.scenario_type == "post_catalyst_high_volatility"
                    and normalized.trend_integrity == "weakening"
                    and normalized.catalyst_state in {"digesting", "absent"}
                    and normalized.extension_state in {"normal", "extended"}
                    and normalized.risk_state == "high"
                )

            if normalized.entry_posture == "wait_confirmation":
                # round28 之后剩余的主要 hold bad_case 进一步收敛到“中性 + 等待确认 + 催化后高波动整理型”。
                # 对这类样本，若趋势未破坏、催化仍处于消化期，观望往往过于保守。
                return (
                    normalized.scenario_type == "post_catalyst_high_volatility"
                    and normalized.trend_integrity in {"complete", "weakening"}
                    and normalized.catalyst_state == "digesting"
                    and normalized.extension_state in {"normal", "extended"}
                    and normalized.risk_state in {"medium", "high"}
                )

        return False

    if normalized.direction_bias == "bearish":
        if normalized.trend_integrity == "broken" or normalized.risk_state in {"medium", "high"}:
            return "sell"
        return "hold"

    if normalized.direction_bias == "neutral":
        if can_buy_pullback_with_direction_bias():
            return "buy_on_pullback"
        return "hold"

    if normalized.direction_bias != "bullish":
        return None

    if normalized.trend_integrity == "broken" or normalized.risk_state == "high":
        if can_buy_pullback_with_direction_bias():
            return "buy_on_pullback"
        return "hold"

    if normalized.entry_posture == "immediate":
        if normalized.trend_integrity == "complete" and normalized.extension_state != "overstretched":
            return "buy_now"
        return "hold"

    if normalized.entry_posture == "wait_pullback":
        if can_buy_pullback_with_direction_bias():
            return "buy_on_pullback"
        return "hold"

    if normalized.entry_posture in {"wait_confirmation", "no_entry"}:
        return "hold"

    return None


def derive_trend_judgment_from_action(action: str | None) -> str | None:
    if action is None:
        return None
    return _ACTION_TO_TREND.get(action)
