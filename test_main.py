# Тесты API без базы: живой PostgreSQL не вызываем и ничего не записываем.
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root_ok():
    """GET / отвечает, что сервер жив."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_zero_amount():
    """Нулевая сумма — ошибка про число, до подключения к базе."""
    response = client.post("/expenses", json={"amount": 0, "category": "еда"})
    assert response.status_code == 400
    assert "число" in response.json()["error"]


def test_empty_category():
    """Пустая категория — ошибка про категорию, до подключения к базе."""
    response = client.post("/expenses", json={"amount": 10, "category": ""})
    assert response.status_code == 400
    assert "категори" in response.json()["error"]
