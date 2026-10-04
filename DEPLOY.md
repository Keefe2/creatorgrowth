# DEPLOY.md — Vercel plan 🌙 (card-free, 100% free)

## Architecture
- **Backend**: FastAPI on Vercel serverless (`api/index.py` re-exports the app, mounted at `/api`)
- **Frontend**: same Vercel project serves `frontend/dist` as static (same-origin `/api` — no CORS issues)
- **Database**: Supabase free Postgres (no card)
- **Scheduler**: no background worker — due posts publish opportunistically inside API requests (max once/60s)

## Files that make it work
| File | Purpose |
|---|---|
| `api/index.py` | Vercel Python entrypoint — mounts backend under `/api` |
| `vercel.json` | build frontend, rewrites `/api/*` → function, SPA fallback |
| `requirements.txt` (root) | Python deps for the serverless function |
| `.python-version` | pins Python 3.12 |

## Deploy steps
1. **Vercel account**: vercel.com → Sign up with GitHub (free, no card)
2. **Supabase project**: supabase.com → New project → free tier → copy connection string
3. **Vercel → Add New Project → Import** `Keefe2/creatorgrowth`
   - Framework: Vite (auto) — build command & output dir come from `vercel.json`
   - Env vars: `DATABASE_URL` (Supabase), `JWT_SECRET` (random), `ENCRYPTION_KEY` (random Fernet key), `ENV=prod`
4. **Deploy** → open the URL → register → done

## Notes
- Serverless sleeps when idle: first request after idle takes a few seconds (normal on free tier)
- Scheduled posts publish when traffic arrives (opportunistic, ≤60s granularity)
- Never commit `.env` — secrets only in Vercel dashboard env vars
