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


def test_delete_expense_removed():
    """DELETE удаляет строку: rowcount 1, ответ 200, база home не открывается."""
    expense_id = 7
    cursor = MagicMock()
    cursor.rowcount = 1
    cursor.__exit__.return_value = False

    # with psycopg.connect(...) as conn / with conn.cursor() as cur
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    connection.cursor.return_value.__enter__.return_value = cursor
    connection.cursor.return_value.__exit__.return_value = False

    with patch("main.psycopg.connect", return_value=connection) as connect:
        response = client.delete(f"/expenses/{expense_id}")

    # До живой базы запрос не дошёл: вызван только подменённый connect.
    connect.assert_called_once_with("dbname=home")
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    query, params = cursor.execute.call_args[0]
    assert "DELETE" in query
    assert "%s" in query
    assert params == (expense_id,)
    # id передан параметром, а не вставлен в текст запроса.
    assert str(expense_id) not in query


def test_delete_expense_missing():
    """DELETE без строки: rowcount 0, ответ 404, база home не открывается."""
    expense_id = 7
    cursor = MagicMock()
    cursor.rowcount = 0
    cursor.__exit__.return_value = False

    # with psycopg.connect(...) as conn / with conn.cursor() as cur
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    connection.cursor.return_value.__enter__.return_value = cursor
    connection.cursor.return_value.__exit__.return_value = False

    with patch("main.psycopg.connect", return_value=connection) as connect:
        response = client.delete(f"/expenses/{expense_id}")

    # До живой базы запрос не дошёл: вызван только подменённый connect.
    connect.assert_called_once_with("dbname=home")
    assert response.status_code == 404
    assert response.json() == {"error": "нет такой траты"}

    query, params = cursor.execute.call_args[0]
    assert "DELETE" in query
    assert "%s" in query
    assert params == (expense_id,)
    assert str(expense_id) not in query


def test_patch_zero_amount_skips_database():
    """Нулевая сумма на PATCH — 400, до базы не ходим."""
    with patch("main.psycopg.connect") as connect:
        response = client.patch("/expenses/7", json={"amount": 0})

    connect.assert_not_called()
    assert response.status_code == 400
    assert response.json() == {"error": "нужно число больше нуля"}


def test_patch_empty_body_skips_database():
    """Пустое тело PATCH — нечего менять, до базы не ходим."""
    with patch("main.psycopg.connect") as connect:
        response = client.patch("/expenses/7", json={})

    connect.assert_not_called()
    assert response.status_code == 400
    assert response.json() == {"error": "нечего менять"}


def test_patch_amount_updated():
    """PATCH суммы: rowcount 1, ответ 200, в UPDATE только amount и плейсхолдеры."""
    expense_id = 7
    cursor = MagicMock()
    cursor.rowcount = 1
    cursor.__exit__.return_value = False

    # with psycopg.connect(...) as conn / with conn.cursor() as cur
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    connection.cursor.return_value.__enter__.return_value = cursor
    connection.cursor.return_value.__exit__.return_value = False

    with patch("main.psycopg.connect", return_value=connection) as connect:
        response = client.patch(f"/expenses/{expense_id}", json={"amount": 15})

    # До живой базы запрос не дошёл: вызван только подменённый connect.
    connect.assert_called_once_with("dbname=home")
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    query, params = cursor.execute.call_args[0]
    assert "UPDATE" in query
    assert "amount = %s" in query
    assert "category" not in query
    assert "%s" in query
    assert params == (15, expense_id)
    # Сумма и id переданы параметрами, а не вставлены в текст запроса.
    assert "15" not in query
    assert str(expense_id) not in query


def test_patch_expense_missing():
    """PATCH без строки: rowcount 0, ответ 404, база home не открывается."""
    expense_id = 7
    cursor = MagicMock()
    cursor.rowcount = 0
    cursor.__exit__.return_value = False

    # with psycopg.connect(...) as conn / with conn.cursor() as cur
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    connection.cursor.return_value.__enter__.return_value = cursor
    connection.cursor.return_value.__exit__.return_value = False

    with patch("main.psycopg.connect", return_value=connection) as connect:
        response = client.patch(f"/expenses/{expense_id}", json={"amount": 15})

    # До живой базы запрос не дошёл: вызван только подменённый connect.
    connect.assert_called_once_with("dbname=home")
    assert response.status_code == 404
    assert response.json() == {"error": "нет такой траты"}

    query, params = cursor.execute.call_args[0]
    assert "UPDATE" in query
    assert "%s" in query
    assert params == (15, expense_id)
