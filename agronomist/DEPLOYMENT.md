# Deployment Guide

This project is prepared for:

- Supabase for PostgreSQL and `pgvector`
- Render for the FastAPI backend
- Vercel for the React frontend

## 1. Supabase

Create a Supabase project and copy the direct PostgreSQL connection string into `DATABASE_URL`.

Recommended connection settings:

- use the direct Postgres connection string, not a local emulator
- keep `sslmode=require`
- run migrations against the same database used by Render

The backend automatically normalizes:

- `postgres://...` to `postgresql://...`
- Supabase hosts to `sslmode=require` when it is missing

### pgvector

The backend expects the `vector` extension to exist. The knowledge migration already runs:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Verify after migration:

```sql
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

## 2. Backend on Render

The repo includes [`render.yaml`](render.yaml).

### Render configuration summary

- runtime: Python
- root directory: `backend`
- health check: `/api/v1/health/ready`
- pre-deploy migration: `alembic upgrade head`
- persistent disk: mounted at `/var/data`

### Required backend environment variables

Set these in Render:

| Variable | Required | Notes |
| --- | --- | --- |
| `ENVIRONMENT` | yes | set to `production` |
| `DATABASE_URL` | yes | Supabase PostgreSQL connection string |
| `DATABASE_SSL_MODE` | recommended | `require` for Supabase |
| `SECRET_KEY` | yes | at least 32 characters |
| `GEMINI_API_KEY` | yes | required for diagnosis, chat, recommendations, embeddings |
| `CORS_ORIGINS` | yes | comma-separated or JSON list of Vercel origins |
| `UPLOAD_DIR` | yes | `/var/data/uploads` |
| `KNOWLEDGE_STORAGE_DIR` | yes | `/var/data/knowledge_uploads` |
| `WEATHER_CACHE_TTL_SECONDS` | recommended | `900` for 15-minute weather freshness |
| `WEATHER_STALE_TTL_SECONDS` | recommended | `3600` to serve stale weather during provider outages |
| `WEATHER_MAX_RETRIES` | recommended | `1` retry for transient weather provider failures |
| `WEATHER_PROVIDER_COOLDOWN_SECONDS` | recommended | `300` cooldown after repeated 429/5xx responses |
| `GEOCODING_PROVIDER` | recommended | `nominatim` for MVP/dev, replaceable with a hosted provider adapter later |
| `NOMINATIM_USER_AGENT` | recommended | identifiable User-Agent for Nominatim reverse geocoding requests |
| `GEOCODING_CACHE_TTL_SECONDS` | recommended | `86400` to avoid repeated reverse lookups for the same coordinates |
| `GEOCODING_MIN_INTERVAL_MS` | recommended | `1100` to rate limit public Nominatim requests |

Useful optional variables:

| Variable | Default |
| --- | --- |
| `LOG_LEVEL` | `INFO` |
| `LOG_FORMAT` | `json` |
| `LOG_ACCESS` | `true` |
| `DATABASE_POOL_SIZE` | `5` |
| `DATABASE_MAX_OVERFLOW` | `10` |
| `DATABASE_POOL_TIMEOUT_SECONDS` | `30` |
| `DATABASE_POOL_RECYCLE_SECONDS` | `1800` |
| `DATABASE_CONNECT_TIMEOUT_SECONDS` | `10` |
| `STARTUP_VALIDATE_DATABASE` | `true` |
| `STARTUP_VALIDATE_PGVECTOR` | `true` |
| `STARTUP_VALIDATE_STORAGE` | `true` |

### Backend deploy flow

1. Connect the Git repository in Render.
2. Use the existing `render.yaml`.
3. Fill the secret environment variables.
4. Confirm the persistent disk is enabled.
5. Deploy.

### Backend migration command

Render runs this before starting the app:

```bash
alembic upgrade head
```

If you need to run it manually in the Render shell:

```bash
cd backend
alembic upgrade head
```

## 3. Frontend on Vercel

The repo includes [`frontend/vercel.json`](frontend/vercel.json).

### Vercel project settings

- project root directory: `frontend`
- framework preset: Vite
- install command: `npm ci`
- build command: `npm run build`
- output directory: `dist`

### Required frontend environment variables

| Variable | Required | Notes |
| --- | --- | --- |
| `VITE_API_BASE_URL` | yes | full backend API URL, for example `https://<render-service>.onrender.com/api/v1` |
| `VITE_API_TIMEOUT_MS` | recommended | frontend API timeout in milliseconds |

Useful optional variables:

| Variable | Default |
| --- | --- |
| `VITE_API_REQUEST_TIMEOUT_MS` | `20000` legacy alias for `VITE_API_TIMEOUT_MS` |
| `VITE_SOURCEMAP` | `false` |

Production builds fail fast if `VITE_API_BASE_URL` is missing or not an absolute URL.
Farm create/edit maps use OpenStreetMap tiles through Leaflet and do not require
Google Maps, billing, or browser map API keys.

## 4. CORS

Set backend `CORS_ORIGINS` to the exact Vercel origins that should call the API.

Examples:

```text
https://your-app.vercel.app
https://your-preview.vercel.app
```

Comma-separated:

```text
https://your-app.vercel.app,https://your-preview.vercel.app
```

JSON list:

```json
["https://your-app.vercel.app", "https://your-preview.vercel.app"]
```

Wildcard CORS is rejected in production.

## 5. Storage

The backend now uses a storage abstraction with a local backend implementation.

Current production mode:

- farm images stored under `UPLOAD_DIR`
- knowledge document files stored under `KNOWLEDGE_STORAGE_DIR`
- Render persistent disk keeps those files across restarts and deploys

Cloud object storage is not implemented yet, but the file-handling code is now centralized so that backend change is isolated.

## 6. Health Checks

Backend endpoints:

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `GET /api/v1/health`
- `GET /api/v1/health/rag`
- `GET /api/v1/health/embeddings`

`/health/ready` returns `503` when database, storage, or `pgvector` checks fail.

## 7. Production Verification Checklist

### Backend

- `alembic upgrade head` succeeds
- `/api/v1/health/live` returns `200`
- `/api/v1/health/ready` returns `200`
- `/api/v1/health/rag` reports healthy or degraded only because live embedding checks were skipped
- logs show startup validation success
- uploads directory is writable
- knowledge storage directory is writable

### Database

- Supabase connection succeeds from Render
- `vector` extension exists
- all Alembic tables exist
- knowledge chunk embedding column reports `vector(768)`

### Frontend

- `npm run build` succeeds in `frontend/`
- Vercel build receives `VITE_API_BASE_URL`
- app loads without client-side API base URL errors
- login, farm pages, chat, diagnosis, recommendations, and knowledge search all call the deployed backend

### Cross-system

- CORS allows the Vercel domain and blocks unlisted origins
- authenticated API calls succeed from the frontend
- file uploads persist across backend restarts
- a document can be ingested and later found by knowledge search

## 8. Manual Smoke Test Commands

Backend health:

```bash
curl https://<render-service>.onrender.com/api/v1/health/ready
curl https://<render-service>.onrender.com/api/v1/health/rag
```

Frontend build:

```bash
cd frontend
npm run build
```

Backend local production-style boot:

```bash
cd backend
ENVIRONMENT=production \
DEBUG=false \
DATABASE_URL='postgresql://...' \
SECRET_KEY='replace-with-a-real-secret' \
GEMINI_API_KEY='replace-with-a-real-key' \
CORS_ORIGINS='["https://your-app.vercel.app"]' \
UPLOAD_DIR='/tmp/agronomist/uploads' \
KNOWLEDGE_STORAGE_DIR='/tmp/agronomist/knowledge' \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
