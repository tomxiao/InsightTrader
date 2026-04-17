from __future__ import annotations


def test_get_analysis_task_status_returns_contract(api_client) -> None:
    response = api_client.get("/analysis/tasks/task-1/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["taskId"] == "task-1"
    assert payload["status"] == "queued"
    assert payload["symbol"] == "AAPL"


def test_get_analysis_task_status_returns_404_when_missing(api_client) -> None:
    response = api_client.get("/analysis/tasks/missing/status")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_create_analysis_task_returns_accepted_contract(api_client) -> None:
    response = api_client.post(
        "/analysis/tasks",
        json={
            "conversationId": "conv-1",
            "ticker": "TSLA",
            "tradeDate": "20260417",
            "prompt": "帮我分析",
            "teamId": "lite",
            "selectedAnalysts": ["market", "news"],
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["taskId"] == "task-1"
    assert payload["symbol"] == "TSLA"
    assert payload["teamId"] == "lite"

