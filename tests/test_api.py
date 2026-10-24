"""Uçtan uca API testleri (lexicon NLP + mock veri + geçici SQLite)."""

API = "/api/v1"


def test_health(client):
    response = client.get(f"{API}/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert body["nlp_provider"] == "lexicon"
    assert body["sources"] == {"twitter": False, "reddit": False, "mock": True}


def test_analyze_persists_and_appears_in_history(client):
    response = client.post(f"{API}/analyze", json={"query": "#iPhone15", "platform": "twitter", "limit": 20})
    assert response.status_code == 201
    result = response.json()

    assert result["id"] is not None
    assert result["is_mock_data"] is True  # token yok -> mock'a düşmeli
    assert len(result["comments"]) == 20
    dist = result["distribution"]
    assert dist["positive"] + dist["negative"] + dist["neutral"] == 20
    assert abs(dist["positive_pct"] + dist["negative_pct"] + dist["neutral_pct"] - 100) < 0.1
    assert "iPhone15" in result["summary"]["overview"]

    history = client.get(f"{API}/history").json()
    assert history["total"] == 1
    assert history["items"][0]["id"] == result["id"]

    detail = client.get(f"{API}/history/{result['id']}").json()
    assert detail["distribution"] == dist
    assert len(detail["comments"]) == 20


def test_history_filter_and_pagination(client):
    for query in ("Tesla", "PlayStation 5", "Tesla Model Y"):
        client.post(f"{API}/analyze", json={"query": query, "platform": "mock", "limit": 5})

    filtered = client.get(f"{API}/history", params={"query": "tesla"}).json()
    assert filtered["total"] == 2

    page = client.get(f"{API}/history", params={"limit": 1, "offset": 1}).json()
    assert page["total"] == 3 and len(page["items"]) == 1


def test_delete_history_item(client):
    analysis_id = client.post(f"{API}/analyze", json={"query": "Samsung", "platform": "mock", "limit": 5}).json()["id"]
    assert client.delete(f"{API}/history/{analysis_id}").status_code == 204
    assert client.get(f"{API}/history/{analysis_id}").status_code == 404
    assert client.delete(f"{API}/history/{analysis_id}").status_code == 404


def test_validation_errors(client):
    assert client.post(f"{API}/analyze", json={"query": "#"}).status_code == 422
    assert client.post(f"{API}/analyze", json={"query": "ok", "platform": "facebook"}).status_code == 422
    assert client.post(f"{API}/analyze", json={"query": "valid", "limit": 1000}).status_code == 422
    assert client.get(f"{API}/history", params={"limit": 0}).status_code == 422
