# API: проверка, что сервер жив, список трат и новая трата (база home).
import psycopg
from datetime import date

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


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
    with psycopg.connect("dbname=home") as conn:
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
    with psycopg.connect("dbname=home") as conn:
        with conn.cursor() as cur:
            # Плейсхолдеры %s: значения передаём отдельно, не склеиваем запрос.
            cur.execute(
                "INSERT INTO expenses (spent_on, amount, category) VALUES (%s, %s, %s)",
                (spent_on, amount, category.strip()),
            )
    return {"ok": True}
