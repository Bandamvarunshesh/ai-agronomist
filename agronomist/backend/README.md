# AI Agronomist Backend

FastAPI backend for the farming platform.

## Stack

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- `pgvector`
- Gemini APIs

## Local Setup

```bash
cd backend
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload
```

Docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Production Notes

- `DATABASE_URL` is normalized for SQLAlchemy and supports Supabase-style URLs.
- Supabase hosts automatically get `sslmode=require` when it is missing.
- production startup validates database, storage, and `pgvector`.
- wildcard CORS is rejected in production.
- local storage is abstracted behind a storage service and is ready to be replaced with cloud object storage later.

## Health Endpoints

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `GET /api/v1/health`
- `GET /api/v1/health/rag`
- `GET /api/v1/health/embeddings`

## Environment

See `.env.example` for the full backend configuration surface.

Important variables:

- `ENVIRONMENT`
- `DATABASE_URL`
- `DATABASE_SSL_MODE`
- `SECRET_KEY`
- `GEMINI_API_KEY`
- `CORS_ORIGINS`
- `UPLOAD_DIR`
- `KNOWLEDGE_STORAGE_DIR`

## Deployment

Use the root-level [DEPLOYMENT.md](../DEPLOYMENT.md) and [render.yaml](../render.yaml) for production deployment on Supabase and Render.
