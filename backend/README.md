# Backend local setup

Python 3.12 is required. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
python backend\scripts\export_openapi.py
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API documentation is at `http://localhost:8000/docs`. The first contract milestone exposes route schemas; verification still returns 503 until the database and worker are implemented. Copy `backend/.env.example` to an untracked `backend/.env` and enter credentials locally when the PostgreSQL project is available. Do not commit `.env` or apply migrations to Supabase automatically.
