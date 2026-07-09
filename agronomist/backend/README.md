# AI Agronomist MVP - Backend

FastAPI-based backend for the AI Agronomist MVP.

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI app entry point
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py       # Environment configuration
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── health.py   # Health check endpoints
│   │       └── router.py   # API router aggregation
│   └── db/
│       ├── __init__.py
│       ├── base.py         # SQLAlchemy base for models
│       └── session.py      # Database session management
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose for local development
├── .env.example            # Environment variables template
└── README.md              # This file
```

## Tech Stack

- **FastAPI** - Modern web framework
- **SQLAlchemy** - ORM
- **PostgreSQL** - Database
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **Docker** - Containerization

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ (or Docker)
- Docker & Docker Compose (recommended)

## Quick Start (Docker - Recommended)

### 1. Setup environment
```bash
cd backend
cp .env.example .env
```

### 2. Start services
```bash
docker-compose up -d
```

This will:
- Start PostgreSQL container on port 5432
- Build and start FastAPI container on port 8000
- Enable hot-reload for development

### 3. Verify health
```bash
curl http://localhost:8000/api/v1/health
```

### 4. View API docs
```
http://localhost:8000/docs
```

## Local Development (Without Docker)

### 1. Setup environment
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure database
Update `.env` with your PostgreSQL connection details:
```
DATABASE_URL=postgresql://user:password@localhost:5432/agronomist
```

### 3. Start the server
```bash
python -m uvicorn app.main:app --reload
```

Server runs on `http://localhost:8000`

## API Endpoints

### Health Check
```bash
GET /api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Root
```bash
GET /
```

Response:
```json
{
  "app": "AI Agronomist MVP",
  "version": "0.1.0",
  "status": "running"
}
```

## Testing

### Test health endpoint
```bash
curl -X GET http://localhost:8000/api/v1/health
```

### Interactive API docs
Visit `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/redoc` (ReDoc)

## Database Management

### Connect to database (Docker)
```bash
docker exec -it agronomist_db psql -U agronomist -d agronomist
```

### View logs
```bash
docker-compose logs -f api
docker-compose logs -f db
```

## Stopping Services

```bash
docker-compose down
```

To remove database volume:
```bash
docker-compose down -v
```

## Next Steps (Phase 2)

- [ ] Setup Alembic for database migrations
- [ ] Implement authentication (JWT)
- [ ] Create core data models (Farm, Field, Crop, etc.)
- [ ] Implement farm management APIs
- [ ] Add request/response schemas

## Troubleshooting

### Database connection times out
- Ensure PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Verify network connectivity if using remote database

### Port already in use
- PostgreSQL: `lsof -i :5432` and kill process
- FastAPI: `lsof -i :8000` and kill process

### Docker issues
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `DEBUG` - Enable debug mode
- `HOST` - Server host
- `PORT` - Server port

## Phase 14.1: RAG And News Ingestion Verification

### Required Services

- PostgreSQL with the `pgvector` extension available.
- A valid `GEMINI_API_KEY` for live embedding generation.
- Real, approved external news/advisory/research/market feed URLs configured in the database or loaded from a source config file.

This project does not seed mock knowledge documents or mock news feeds. The sample source config at `config/intelligence_sources.example.json` is a template with an empty `sources` list.

### Environment

Copy `.env.example` to `.env` and configure:

```bash
GEMINI_API_KEY=your-gemini-key
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSIONS=768
GEMINI_REQUEST_TIMEOUT_SECONDS=20
KNOWLEDGE_STORAGE_DIR=knowledge_uploads
INTELLIGENCE_SOURCE_CONFIG_PATH=config/intelligence_sources.example.json
INTELLIGENCE_SYNC_ENABLED=false
```

Run migrations before ingestion:

```bash
alembic upgrade head
```

### Health Verification

Check RAG storage and embedding configuration:

```bash
curl http://localhost:8000/api/v1/health/rag
```

Run a live Gemini embedding check when network access is available:

```bash
curl "http://localhost:8000/api/v1/health/embeddings?live_check=true"
```

If the network is unavailable or the key is missing, the endpoint returns a safe `not_configured` or `unavailable` status with a clear error message. It never returns the API key.

### Document Ingestion Dry Run

Admins can validate document parsing, checksums, duplicate detection, and chunk counts without writing document rows or embeddings:

```bash
curl -X POST "http://localhost:8000/api/v1/admin/knowledge/documents" \
  -H "Authorization: Bearer <admin-token>" \
  -F "file=@/path/to/approved-guide.pdf" \
  -F "dry_run=true"
```

Folder dry run:

```bash
curl -X POST "http://localhost:8000/api/v1/admin/knowledge/documents" \
  -H "Authorization: Bearer <admin-token>" \
  -F "folder_path=/path/to/approved-folder" \
  -F "recursive=true" \
  -F "dry_run=true"
```

Set `dry_run=false` only after reviewing the response.

### Semantic Search Verification

After ingesting real documents, verify retrieval:

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/search" \
  -H "Authorization: Bearer <user-token>" \
  -H "Content-Type: application/json" \
  -d '{"query":"rice irrigation during flowering","limit":5,"use_hybrid":true}'
```

When `GEMINI_API_KEY` is configured, the search uses Gemini embeddings plus PostgreSQL full-text ranking. Without the key, it safely falls back to lexical search.

### External News Source Configuration

Create a real source config file from the template and set `INTELLIGENCE_SOURCE_CONFIG_PATH`. Validate it without writing rows:

```bash
curl -X POST "http://localhost:8000/api/v1/admin/intelligence/sources/load-config?dry_run=true" \
  -H "Authorization: Bearer <admin-token>"
```

Persist validated sources:

```bash
curl -X POST "http://localhost:8000/api/v1/admin/intelligence/sources/load-config?dry_run=false" \
  -H "Authorization: Bearer <admin-token>"
```

Verify external source fetch/parse behavior without saving articles:

```bash
curl -X POST "http://localhost:8000/api/v1/admin/intelligence/sources/sync?dry_run=true" \
  -H "Authorization: Bearer <admin-token>"
```

If a source is unreachable, malformed, or blocked by network policy, the dry-run report returns `status: failed` and a clear per-source error.
