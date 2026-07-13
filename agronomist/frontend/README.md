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
- `VITE_API_TIMEOUT_MS` controls frontend API request timeout; `VITE_API_REQUEST_TIMEOUT_MS` remains supported as a legacy alias
- production builds fail if `VITE_API_BASE_URL` is missing/invalid
- farm create/edit uses OpenStreetMap tiles through Leaflet; no Google Maps key or paid map API is required
- Vercel configuration is in `vercel.json`

Build verification:

```bash
npm run build
```
