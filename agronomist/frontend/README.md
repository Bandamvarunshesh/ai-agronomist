# AI Agronomist Frontend

React + TypeScript + Vite frontend for the farming platform.

## Local Setup

```bash
cd frontend
cp .env.example .env
npm ci
npm run dev
```

## Production

- `VITE_API_BASE_URL` must point to the deployed backend `/api/v1`
- production builds fail if `VITE_API_BASE_URL` is missing or invalid
- Vercel configuration is in `vercel.json`

Build verification:

```bash
npm run build
```
