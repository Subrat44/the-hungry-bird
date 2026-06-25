from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_restaurants_by_text():
    response = client.get("/api/restaurants", params={"q": "ramen"})
    payload = response.json()
    assert response.status_code == 200
    assert payload["count"] == 1
    assert payload["restaurants"][0]["name"] == "Miso Sun"


def test_filter_open_now_and_price():
    response = client.get("/api/restaurants", params={"open_now": "true", "price": "$"})
    payload = response.json()
    assert response.status_code == 200
    assert payload["count"] == 1
    assert payload["restaurants"][0]["name"] == "Slice Society"


def test_unknown_restaurant_404():
    response = client.get("/api/restaurants/unknown")
    assert response.status_code == 404


def test_google_source_without_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    response = client.get("/api/restaurants", params={"source": "google", "q": "dosa"})
    payload = response.json()
    assert response.status_code == 200
    assert payload["configured"] is False
    assert payload["restaurants"] == []
