# API: проверка, что сервер жив, список трат, новая трата и удаление (база home).
import os
import psycopg
from datetime import date

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


def database_url():
    """Адрес базы из DATABASE_URL. Если переменной нет — локальная база home."""
    # Пароль в файл не пишем и адрес в лог не печатаем.
    return os.environ.get("DATABASE_URL", "dbname=home")


@app.get("/")
def root():
    """Короткий ответ: сервер отвечает."""
    return {"ok": True}


@app.get("/expenses")
def expenses(category: str | None = None):
    """Все траты или только одна категория, если она передана в адресе."""
    # Подключаемся к базе home.
    # Пользователь — текущий системный, пароль в файле не храним.
    # with закроет соединение сам.
    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cur:
            # Без параметра — все строки. С ?category=... фильтр через %s.
            if category:
                cur.execute(
                    """
                    SELECT id, spent_on, amount, category
                    FROM expenses
                    WHERE category = %s
                    ORDER BY id
                    """,
                    (category,),
                )
            else:
                cur.execute(
                    "SELECT id, spent_on, amount, category FROM expenses ORDER BY id"
                )
            rows = []
            for expense_id, spent_on, amount, row_category in cur:
                # Дата и Decimal сами в JSON не превращаются.
                rows.append(
                    {
                        "id": expense_id,
                        "spent_on": str(spent_on),
                        "amount": float(amount),
                        "category": row_category,
                    }
                )
            return rows


@app.post("/expenses", status_code=201)
def add_expense(body: dict):
    """Записать трату за сегодня. Сумма больше нуля, категория не пустая."""
    amount = body.get("amount")
    category = body.get("category")

    # Не число или нуль и меньше — не записываем. bool в JSON — не сумма.
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
        return JSONResponse(
            status_code=400,
            content={"error": "нужно число больше нуля"},
        )

    # Пустая категория — не записываем.
    if not isinstance(category, str) or not category.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "нужна категория"},
        )

    # Сегодняшняя дата для колонки spent_on.
    spent_on = date.today()

    # Подключаемся к базе home.
    # Пользователь — текущий системный, пароль в файле не храним.
    # with закроет соединение и сохранит INSERT, если ошибок не было.
    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cur:
            # Плейсхолдеры %s: значения передаём отдельно, не склеиваем запрос.
            cur.execute(
                "INSERT INTO expenses (spent_on, amount, category) VALUES (%s, %s, %s)",
                (spent_on, amount, category.strip()),
            )
    return {"ok": True}


@app.get("/totals")
def totals():
    """Сумма трат по каждой категории, сначала самые большие."""
    # Подключаемся к базе home.
    # Пользователь — текущий системный, пароль в файле не храним.
    # with закроет соединение сам.
    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cur:
            # В запросе нет данных от пользователя — плейсхолдеры не нужны.
            cur.execute(
                """
                SELECT category, SUM(amount)
                FROM expenses
                GROUP BY category
                ORDER BY SUM(amount) DESC
                """
            )
            rows = []
            for category, total in cur:
                # SUM приходит как Decimal, в JSON нужен float.
                rows.append({"category": category, "total": float(total)})
            return rows


@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int):
    """Удалить одну трату по id. Нет такой строки — 404."""
    # Подключаемся к базе home.
    # Пользователь — текущий системный, пароль в файле не храним.
    # with закроет соединение и сохранит DELETE, если ошибок не было.
    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cur:
            # Плейсхолдер %s: id передаём отдельно, не склеиваем запрос.
            cur.execute(
                "DELETE FROM expenses WHERE id = %s",
                (expense_id,),
            )
            # 0 — такой строки не было. 1 — строка удалена.
            removed = cur.rowcount
    if removed == 0:
        return JSONResponse(
            status_code=404,
            content={"error": "нет такой траты"},
        )
    return {"ok": True}
