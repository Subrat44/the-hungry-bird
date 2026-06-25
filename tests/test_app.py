from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"





def test_unknown_restaurant_404():
    response = client.get("/api/restaurants/unknown")
    assert response.status_code == 404


