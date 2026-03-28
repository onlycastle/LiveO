from starlette.testclient import TestClient


def test_ws_connect_disconnect(ws_client: TestClient):
    with ws_client.websocket_connect("/ws/events") as ws:
        # Just verify connection works
        pass  # disconnect happens on context exit


def test_candidate_created_event(ws_client: TestClient):
    """Creating a candidate should broadcast via WS."""
    with ws_client.websocket_connect("/ws/events") as ws:
        resp = ws_client.post("/api/shorts/candidates", json={
            "startTime": "0:10",
            "endTime": "0:25",
            "duration": "0:15",
            "title": "Test Candidate",
            "indicators": ["audio_spike"],
            "confidence": 85,
        })
        assert resp.status_code == 201

        data = ws.receive_json()
        assert data["type"] == "candidate_created"
        assert "id" in data["data"]


def test_candidate_updated_event(ws_client: TestClient):
    """Updating a candidate should broadcast via WS."""
    resp = ws_client.post("/api/shorts/candidates", json={
        "startTime": "0:10",
        "endTime": "0:25",
        "duration": "0:15",
        "title": "Test",
        "indicators": [],
        "confidence": 80,
    })
    assert resp.status_code == 201
    cid = resp.json()["id"]

    with ws_client.websocket_connect("/ws/events") as ws:
        ws_client.patch(f"/api/shorts/candidates/{cid}", json={
            "status": "confirmed",
        })

        data = ws.receive_json()
        assert data["type"] == "candidate_updated"
        assert data["data"]["status"] == "confirmed"
