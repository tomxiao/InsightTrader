from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

import requests


DEFAULT_BASE_URL = "http://127.0.0.1:8100"


@dataclass(frozen=True)
class EvalTurn:
    message: str


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    description: str
    turns: list[EvalTurn]
    expected_ticker: str
    expected_name: str | None = None


EVAL_CASES: list[EvalCase] = [
    EvalCase(
        case_id="case_1",
        description="中文简称识别苹果",
        turns=[EvalTurn("分析苹果，重点看估值")],
        expected_ticker="AAPL",
        expected_name="Apple Inc.",
    ),
    EvalCase(
        case_id="case_2",
        description="中文名称识别腾讯控股",
        turns=[EvalTurn("看看腾讯控股最新情况")],
        expected_ticker="0700.HK",
        expected_name="Tencent Holdings Limited",
    ),
    EvalCase(
        case_id="case_3",
        description="直接输入A股ticker",
        turns=[EvalTurn("分析 300750.SZ，重点关注未来两季催化")],
        expected_ticker="300750.SZ",
        expected_name="宁德时代新能源科技股份有限公司",
    ),
    EvalCase(
        case_id="case_4",
        description="中文别名识别英伟达",
        turns=[EvalTurn("帮我看看英伟达")],
        expected_ticker="NVDA",
        expected_name="NVIDIA Corporation",
    ),
    EvalCase(
        case_id="case_5",
        description="直接输入港股ticker",
        turns=[EvalTurn("我想看 0700.HK")],
        expected_ticker="0700.HK",
        expected_name="Tencent Holdings Limited",
    ),
    EvalCase(
        case_id="case_6",
        description="两轮补全标的",
        turns=[EvalTurn("重点看估值和护城河"), EvalTurn("苹果")],
        expected_ticker="AAPL",
        expected_name="Apple Inc.",
    ),
    EvalCase(
        case_id="case_7",
        description="北交所ticker处理",
        turns=[EvalTurn("分析 920964.BJ")],
        expected_ticker="920964.BJ",
        expected_name=None,
    ),
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate F3 conversational ticker resolution via HTTP API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="ta_service base URL")
    parser.add_argument("--username", default="test", help="login username")
    parser.add_argument("--password", default="test321", help="login password")
    parser.add_argument("--timeout", type=float, default=30.0, help="request timeout in seconds")
    parser.add_argument(
        "--case",
        action="append",
        dest="case_ids",
        default=[],
        help="optional case id(s) to run, e.g. --case case_1",
    )
    return parser.parse_args()


class EvalClient:
    def __init__(self, *, base_url: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def login(self, *, username: str, password: str) -> None:
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def create_conversation(self, *, title: str) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/conversations",
            json={"title": title},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def resolve(self, *, conversation_id: str, message: str) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/conversations/{conversation_id}/resolution",
            json={"message": message},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def confirm(self, *, conversation_id: str, resolution_id: str) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/conversations/{conversation_id}/resolution/confirm",
            json={"action": "confirm", "resolutionId": resolution_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def select(self, *, conversation_id: str, resolution_id: str, ticker: str) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/conversations/{conversation_id}/resolution/confirm",
            json={"action": "select", "resolutionId": resolution_id, "ticker": ticker},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


def _candidate_tickers(payload: dict[str, Any]) -> list[str]:
    return [item.get("ticker", "") for item in payload.get("candidates", [])]


def _candidate_summary(payload: dict[str, Any]) -> list[str]:
    result = []
    for item in payload.get("candidates", []):
        name = item.get("name", "")
        ticker = item.get("ticker", "")
        result.append(f"{name}({ticker})")
    return result


def _drive_case(client: EvalClient, case: EvalCase) -> dict[str, Any]:
    conversation = client.create_conversation(title=f"F3 Eval {case.case_id}")
    conversation_id = conversation["id"]
    trace: list[dict[str, Any]] = []
    latest: dict[str, Any] | None = None

    for turn in case.turns:
        latest = client.resolve(conversation_id=conversation_id, message=turn.message)
        trace.append(
            {
                "type": "resolve",
                "message": turn.message,
                "status": latest.get("status"),
                "ticker": latest.get("ticker"),
                "candidates": _candidate_summary(latest),
                "promptMessage": latest.get("promptMessage"),
            }
        )

    if latest is None:
        raise RuntimeError(f"No turns executed for {case.case_id}")

    if latest.get("status") == "need_confirm" and latest.get("resolutionId"):
        latest = client.confirm(
            conversation_id=conversation_id,
            resolution_id=latest["resolutionId"],
        )
        trace.append(
            {
                "type": "confirm",
                "status": latest.get("status"),
                "ticker": latest.get("ticker"),
                "candidates": _candidate_summary(latest),
                "promptMessage": latest.get("promptMessage"),
            }
        )
    elif latest.get("status") == "need_disambiguation" and latest.get("resolutionId"):
        candidate_tickers = _candidate_tickers(latest)
        if case.expected_ticker in candidate_tickers:
            latest = client.select(
                conversation_id=conversation_id,
                resolution_id=latest["resolutionId"],
                ticker=case.expected_ticker,
            )
            trace.append(
                {
                    "type": "select",
                    "status": latest.get("status"),
                    "ticker": latest.get("ticker"),
                    "candidates": _candidate_summary(latest),
                    "promptMessage": latest.get("promptMessage"),
                }
            )

    final_ticker = latest.get("ticker")
    final_candidates = _candidate_tickers(latest)
    passed = final_ticker == case.expected_ticker or case.expected_ticker in final_candidates

    return {
        "caseId": case.case_id,
        "description": case.description,
        "expectedTicker": case.expected_ticker,
        "expectedName": case.expected_name,
        "finalStatus": latest.get("status"),
        "finalTicker": final_ticker,
        "finalName": latest.get("name"),
        "finalCandidates": _candidate_summary(latest),
        "passed": passed,
        "trace": trace,
    }


def main() -> int:
    args = _parse_args()
    selected_cases = EVAL_CASES
    if args.case_ids:
        allowed = set(args.case_ids)
        selected_cases = [case for case in EVAL_CASES if case.case_id in allowed]

    if not selected_cases:
        raise SystemExit("No evaluation cases selected.")

    client = EvalClient(base_url=args.base_url, timeout=args.timeout)
    client.login(username=args.username, password=args.password)

    results = [_drive_case(client, case) for case in selected_cases]
    passed_count = sum(1 for item in results if item["passed"])

    print(f"F3 evaluation finished: {passed_count}/{len(results)} passed")
    for item in results:
        print(
            f"- {item['caseId']}: pass={item['passed']} "
            f"status={item['finalStatus']} expected={item['expectedTicker']} actual={item['finalTicker']}"
        )
        if item["finalCandidates"]:
            print(f"  candidates: {', '.join(item['finalCandidates'])}")
    print("\nJSON summary:")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if passed_count == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
