# API: проверка, что сервер жив, и список трат из PostgreSQL (база home).
import psycopg
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    """Короткий ответ: сервер отвечает."""
    return {"ok": True}


@app.get("/expenses")
def expenses():
    """Все траты: id, дата, сумма, категория."""
    # Подключаемся к базе home.
    # Пользователь — текущий системный, пароль в файле не храним.
    # with закроет соединение сам.
    with psycopg.connect("dbname=home") as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, spent_on, amount, category FROM expenses ORDER BY id"
            )
            rows = []
            for expense_id, spent_on, amount, category in cur:
                # Дата и Decimal сами в JSON не превращаются.
                rows.append(
                    {
                        "id": expense_id,
                        "spent_on": str(spent_on),
                        "amount": float(amount),
                        "category": category,
                    }
                )
            return rows
