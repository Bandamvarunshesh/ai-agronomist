# AI Agronomist

Production-oriented full-stack farming assistant built with:

- `backend/`: FastAPI, SQLAlchemy, Alembic, PostgreSQL, pgvector, Gemini
- `frontend/`: React, TypeScript, Vite
- `render.yaml`: Render service blueprint for the backend
- `DEPLOYMENT.md`: deployment guide for Supabase, Render, and Vercel

## Repository Layout

```text
agronomist/
├── backend/
├── frontend/
├── render.yaml
└── DEPLOYMENT.md
```

## Local Development

Backend:

```bash
cd backend
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
cp .env.example .env
npm ci
npm run dev
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for:

- Supabase database setup and `pgvector`
- Render backend deployment
- Vercel frontend deployment
- required environment variables
- migration commands
- production verification checklist
