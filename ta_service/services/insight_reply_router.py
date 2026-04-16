from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any


@dataclass(frozen=True)
class InsightReplyRouting:
    intent: str
    primary_section: str | None
    fallback_sections: list[str] = field(default_factory=list)
    reason: str = ""


_ROUTER_SYSTEM_PROMPT = """你是一个极轻量的 insight reply 路由器。

你的任务不是回答用户问题，而是基于当前用户问题和最近几轮对话，判断：
1. 这轮追问最像什么意图
2. 是否应该为正式回答阶段预读 1 个最相关章节

请遵守：
- 只输出 JSON，不要输出任何额外解释
- primary_section 只能是可用章节中的一个，或者 null
- fallback_sections 只能从可用章节中选择，最多 2 个
- 如果当前问题仅靠轻量摘要大概率就够答，或者你没有把握，就让 primary_section 为 null
- 如果用户这轮只是承接上一轮，比如“好”“继续”“想知道”，要结合历史对话理解真正意图

intent 可选值：
- conclusion
- action
- risk
- why
- market_level
- fundamental_reason
- general

输出格式：
{
  "intent": "general",
  "primary_section": null,
  "fallback_sections": [],
  "reason": "一句很短的话"
}
"""


class InsightReplyRouter:
    def route(
        self,
        *,
        llm: Any | None,
        question: str,
        conversation_history: list[dict[str, str]],
        available_sections: list[str],
    ) -> InsightReplyRouting:
        if llm is None or not available_sections:
            return InsightReplyRouting(
                intent="general",
                primary_section=None,
                fallback_sections=[],
                reason="router unavailable",
            )

        messages = [
            ("system", _ROUTER_SYSTEM_PROMPT),
            (
                "human",
                _build_router_input(
                    question=question,
                    conversation_history=conversation_history,
                    available_sections=available_sections,
                ),
            ),
        ]
        try:
            response = llm.invoke(messages)
            payload = _parse_router_payload(_extract_text(response))
        except Exception:
            return InsightReplyRouting(
                intent="general",
                primary_section=None,
                fallback_sections=[],
                reason="router failed",
            )
        return _coerce_routing(payload=payload, available_sections=available_sections)


def _build_router_input(
    *,
    question: str,
    conversation_history: list[dict[str, str]],
    available_sections: list[str],
) -> str:
    history_lines: list[str] = []
    for turn in conversation_history[-4:]:
        role = "用户" if turn.get("role") == "user" else "助手"
        history_lines.append(f"{role}：{turn.get('content', '')}")
    history_text = "\n".join(history_lines) if history_lines else "（无）"
    sections_text = ", ".join(available_sections) if available_sections else "（无）"
    return (
        f"最近对话：\n{history_text}\n\n"
        f"当前用户问题：{question}\n"
        f"可用章节：{sections_text}\n"
    )


def _parse_router_payload(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("empty router response")
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def _coerce_routing(
    *, payload: dict[str, Any], available_sections: list[str]
) -> InsightReplyRouting:
    intent = str(payload.get("intent") or "general").strip() or "general"
    raw_primary = payload.get("primary_section")
    primary_section = raw_primary if raw_primary in available_sections else None

    raw_fallbacks = payload.get("fallback_sections")
    fallback_sections: list[str] = []
    if isinstance(raw_fallbacks, list):
        for item in raw_fallbacks:
            if item in available_sections and item != primary_section and item not in fallback_sections:
                fallback_sections.append(item)
            if len(fallback_sections) >= 2:
                break

    return InsightReplyRouting(
        intent=intent,
        primary_section=primary_section,
        fallback_sections=fallback_sections,
        reason=str(payload.get("reason") or "").strip(),
    )


def _extract_text(response: Any) -> str:
    content = getattr(response, "content", "") if response else ""
    if isinstance(content, list):
        content = "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item) for item in content
        )
    return content.strip() if isinstance(content, str) else ""
