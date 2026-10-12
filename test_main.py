# Тесты API без базы: живой PostgreSQL не вызываем и ничего не записываем.
from datetime import date
from unittest.mock import MagicMock, patch

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


def test_expenses_by_category_uses_placeholder():
    """Фильтр ?category=еда не открывает базу home и не склеивает SQL."""
    # Одна фейковая строка: id, сегодняшняя дата, сумма, категория.
    fake_row = (1, date.today(), 10, "еда")
    cursor = MagicMock()
    cursor.fetchall.return_value = [fake_row]
    # В main.py строки читаются циклом for, поэтому курсор отдаёт то же, что fetchall.
    cursor.__iter__.side_effect = lambda: iter(cursor.fetchall())
    # with не должен прятать ошибки.
    cursor.__exit__.return_value = False

    # with psycopg.connect(...) as conn / with conn.cursor() as cur
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    connection.cursor.return_value.__enter__.return_value = cursor
    connection.cursor.return_value.__exit__.return_value = False

    with patch("main.psycopg.connect", return_value=connection) as connect:
        response = client.get("/expenses", params={"category": "еда"})

    # До живой базы запрос не дошёл: вызван только подменённый connect.
    connect.assert_called_once_with("dbname=home")
    assert response.status_code == 200
    assert response.json()[0]["category"] == "еда"

    query, params = cursor.execute.call_args[0]
    assert "%s" in query
    assert params == ("еда",)
    # Категория передана параметром, а не вставлена в текст запроса.
    assert "еда" not in query


def test_totals_without_database():
    """GET /totals берёт фейковые суммы и не открывает базу home."""
    # Две пары: категория и сумма.
    fake_rows = [("еда", 100), ("транспорт", 40)]
    cursor = MagicMock()
    cursor.fetchall.return_value = fake_rows
    # В main.py строки читаются циклом for, поэтому курсор отдаёт то же, что fetchall.
    cursor.__iter__.side_effect = lambda: iter(cursor.fetchall())
    cursor.__exit__.return_value = False

    # with psycopg.connect(...) as conn / with conn.cursor() as cur
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    connection.cursor.return_value.__enter__.return_value = cursor
    connection.cursor.return_value.__exit__.return_value = False

    with patch("main.psycopg.connect", return_value=connection) as connect:
        response = client.get("/totals")

    # До живой базы запрос не дошёл: вызван только подменённый connect.
    connect.assert_called_once_with("dbname=home")
    assert response.status_code == 200
    food = next(item for item in response.json() if item["category"] == "еда")
    assert food["total"] == 100
    assert isinstance(food["total"], (int, float))
