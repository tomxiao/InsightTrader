from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ta_service.services.report_insight_agent import _post_process_answer


@dataclass(frozen=True)
class ReplySample:
    question: str
    raw_answer: str


SAMPLES: list[ReplySample] = [
    ReplySample(
        question="主要风险是什么？",
        raw_answer="""回答：
核心风险：
主要是增长放缓、技术路线变化和资本开支压力。

- 增长放缓会放大高预期下的估值回撤。
- 技术路线变化如果落地，现有优势可能被削弱。
- 资本开支持续抬升，会压缩现金流和资金效率。
- 此外宏观波动也会影响短期情绪。
""",
    ),
    ReplySample(
        question="结论是什么？",
        raw_answer="""结论如下：
这份报告的整体判断偏谨慎，不是明确看空，但现阶段更像等待更好赔率，而不是马上重仓出手。

- 优势没有消失，但估值缓冲已经不多。
- 后续还要看盈利兑现和需求延续性。
- 如果市场预期继续抬升，回撤风险会更明显。
""",
    ),
    ReplySample(
        question="现在适合买入吗？",
        raw_answer="""回答：
现在不算特别好的买点，更偏向谨慎观察。

- 估值已经不便宜，安全边际有限。
- 盈利兑现节奏还需要继续验证。
- 资本开支和竞争变化都会影响后续表现。
""",
    ),
    ReplySample(
        question="为什么偏谨慎？",
        raw_answer="""分析要点：
主要是因为高预期已经先走在前面，但后续能不能持续兑现还不够确定。

1. 估值位置不低，容错率下降。
2. 需求、利润率和投入节奏都还有验证压力。
3. 一旦增速低于预期，市场重新定价会比较快。
""",
    ),
    ReplySample(
        question="最值得关注的一个风险是什么？",
        raw_answer="""关键风险：
如果只看一个，最值得盯的是增长放缓。

- 现在市场给它的预期并不低。
- 一旦收入或利润增速掉下来，估值和情绪会一起承压。
- 这类风险通常会先体现在股价弹性变差上。
""",
    ),
]


def evaluate_samples() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for sample in SAMPLES:
        final_answer = _post_process_answer(sample.raw_answer)
        rows.append(
            {
                "question": sample.question,
                "raw_answer": sample.raw_answer.strip(),
                "final_answer": final_answer,
                "char_count": len(final_answer),
                "bullet_count": final_answer.count("\n- "),
                "has_followup_hint": "如果你愿意" in final_answer,
                "is_single_screen": len(final_answer) <= 220,
            }
        )
    return rows


def main() -> None:
    print("Mobile chat reply sample check\n")
    for index, row in enumerate(evaluate_samples(), start=1):
        print(f"[{index}] {row['question']}")
        print("Raw:")
        print(row["raw_answer"])
        print("\nFinal:")
        print(row["final_answer"])
        print(
            f"\nMetrics: chars={row['char_count']}, bullets={row['bullet_count']}, "
            f"followup_hint={row['has_followup_hint']}, single_screen={row['is_single_screen']}"
        )
        print("\n" + "=" * 72 + "\n")


if __name__ == "__main__":
    main()
