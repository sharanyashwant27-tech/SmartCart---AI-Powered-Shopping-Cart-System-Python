"""AI endpoint tests (heuristic mode without OpenAI key)."""


def test_ai_status(client):
    resp = client.get("/api/v1/ai/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert body["provider"] == "heuristic"


def test_ai_recommendations(client):
    resp = client.get("/api/v1/ai/recommendations", params={"query": "watch", "limit": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert "recommendations" in body
    assert body["provider"] == "heuristic"


def test_ai_chat(client):
    resp = client.post("/api/v1/ai/chat", json={"message": "looking for headphones"})
    assert resp.status_code == 200
    assert "reply" in resp.json()
