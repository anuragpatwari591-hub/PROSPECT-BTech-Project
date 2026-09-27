# 13 — Deployment

## A. Local (Docker Compose) — recommended for demos
```bash
git clone <your-repo-url> prospect && cd prospect
cp .env.example .env
# edit .env: set GITHUB_TOKEN, POSTGRES_PASSWORD, AUTHOR_HASH_SALT
docker compose up --build
# UI:        http://localhost:8080
# API docs:  http://localhost:8080/docs   (also http://localhost:8000/docs)
docker compose down          # stop (data kept in volume pgdata)
docker compose down -v       # stop and delete data
```
The backend container runs `alembic upgrade head` before starting uvicorn. Health check: `GET /api/health`.

## B. Local without Docker
```bash
# PostgreSQL running locally with a database "prospect"
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://prospect:<pw>@localhost:5432/prospect GITHUB_TOKEN=<token>
alembic upgrade head && uvicorn app.main:app --reload       # :8000
cd ../frontend && npm ci && npm run dev                       # :5173, proxies /api to :8000
```

## C. Cloud: Render Blueprint (verified available Sep 2026)
Render supports Infrastructure-as-Code "Blueprints" defined in `render.yaml`, including a managed PostgreSQL instance whose connection string can be injected into a service with `fromDatabase`. `render.yaml` in this repository declares: `prospect-db` (PostgreSQL), `prospect-api` (Docker web service from `backend/`, health check `/api/health`), `prospect-web` (static site from `frontend/`).

1. Push the repository to GitHub.
2. Render dashboard → New → Blueprint → select the repository → review plans (free-tier limits change; historically the free PostgreSQL instance expires after a limited period — check Render's current pricing page) → Apply.
3. Set secrets in the dashboard: `GITHUB_TOKEN` on prospect-api; `CORS_ORIGINS=https://<prospect-web>.onrender.com`; on prospect-web `VITE_API_BASE_URL=https://<prospect-api>.onrender.com`, then redeploy the static site (Vite reads it at build time).
4. Verify: `curl https://<prospect-api>.onrender.com/api/health` → `{"status":"ok",...,"github_token_configured":true}`.

The backend normalises `postgres://`/`postgresql://` URLs to the psycopg driver automatically.

**Alternatives** (not configured here; verify current offerings before choosing): Railway or Fly.io for the backend with managed/attached Postgres; Vercel or Netlify for the static frontend; Neon or Supabase for PostgreSQL.

## Production checklist
- [ ] `ENVIRONMENT=production` (enables HSTS)
- [ ] Strong `POSTGRES_PASSWORD` and `AUTHOR_HASH_SALT`, never committed
- [ ] Fine-grained read-only `GITHUB_TOKEN`
- [ ] `CORS_ORIGINS` set to the exact frontend origin
- [ ] Access restricted (no authentication in v1.0)
- [ ] Database backups enabled on the provider
- [ ] CI green before deploying; no auto-deploy until the above are verified

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| `GITHUB_RATE_LIMITED` | No/invalid token or quota used; set `GITHUB_TOKEN`, wait for `reset_at` |
| UI says "Cannot reach the PROSPECT server" | Backend down or wrong `VITE_API_BASE_URL`; check `/api/health` |
| CORS error in browser console | Add the frontend origin to `CORS_ORIGINS` |
| `DATABASE_UNAVAILABLE` / backend exits on start | Wrong `DATABASE_URL`, DB not ready; check `docker compose logs db` |
| Analysis stuck in RUNNING | Server restarted mid-run; start a new analysis (stale runs are marked FAILED after 15 min) |
| "Some data was truncated" | Large repository; raise `MAX_PAGES_PER_ENDPOINT` (costs more API calls) |
| Alembic "Target database is not up to date" | Run `alembic upgrade head` |
