# FastAPI и PostgreSQL

FastAPI ходит в PostgreSQL, база `home`. Пароля в файлах нет: подключение идёт от текущего системного пользователя.

## Запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Адреса

- `GET /` — сервер отвечает
- `GET /expenses` — все траты
- `GET /expenses?category=еда` — траты одной категории
- `GET /totals` — сумма по категориям
- `POST /expenses` — записать трату
- `/docs` — страница с описанием адресов

## Тесты

Тесты не ходят в живую базу `home`.

```bash
cd ~/projects/api
source .venv/bin/activate
python -m pytest -q
```

Ожидание: `5 passed`. Warning про `httpx` не ломает тесты.
