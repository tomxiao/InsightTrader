from __future__ import annotations


def test_create_conversation_returns_summary(api_client) -> None:
    response = api_client.post("/conversations", json={"title": "苹果"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == "conv-1"
    assert payload["title"] == "苹果"
    assert payload["status"] == "idle"


def test_list_conversations_returns_items(api_client) -> None:
    response = api_client.get("/conversations")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload[0]["id"] == "conv-1"


def test_get_conversation_returns_404_when_missing(api_client) -> None:
    response = api_client.get("/conversations/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_post_message_returns_assistant_messages(api_client) -> None:
    response = api_client.post("/conversations/conv-1/messages", json={"message": "怎么看？"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["messages"][0]["messageType"] == "insight_reply"
    assert payload["messages"][0]["content"] == "这是回答"


def test_stream_post_message_returns_sse_events(api_client) -> None:
    with api_client.stream("POST", "/conversations/conv-1/messages/stream", json={"message": "怎么看？"}) as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: started" in body
    assert "event: delta" in body
    assert "event: completed" in body


def test_resolve_message_returns_resolution_contract(api_client) -> None:
    response = api_client.post("/conversations/conv-1/resolution", json={"message": "苹果"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["resolutionId"] == "res-1"
    assert payload["status"] == "need_confirm"
    assert payload["ticker"] == "AAPL"
    assert payload["messages"][1]["messageType"] == "ticker_resolution"


def test_stream_resolve_message_returns_sse_events(api_client) -> None:
    with api_client.stream("POST", "/conversations/conv-1/resolution/stream", json={"message": "苹果"}) as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: started" in body
    assert "event: progress" in body
    assert "event: delta" in body
    assert "event: completed" in body


def test_confirm_resolution_returns_resolved_contract(api_client) -> None:
    response = api_client.post(
        "/conversations/conv-1/resolution/confirm",
        json={"action": "confirm", "resolutionId": "res-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["status"] == "resolved"
    assert payload["conversationStatus"] == "analyzing"


def test_confirm_resolution_validates_select_payload(api_client) -> None:
    response = api_client.post(
        "/conversations/conv-1/resolution/confirm",
        json={"action": "select", "resolutionId": "res-1"},
    )

    assert response.status_code == 422
    assert "ticker is required when action is select" in response.text

