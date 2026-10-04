# DEPLOY.md — Raat ka plan 🌙

## Pehle se tayyar (ho gaya ✅)
- `render.yaml` — Render Blueprint: 1 Postgres DB (free) + backend API + frontend static site
- Backend: Postgres-ready (`psycopg2-binary`), gunicorn + uvicorn workers, prod security headers (HSTS on)
- Frontend: API URL env-based (`VITE_API_URL`) — deploy par backend se connect hoga
- CORS: production origins env se

## Raat ko steps (lagbhag 20–30 min)

### 1. GitHub account (5 min)
- github.com par free account banao (agar nahi hai)
- New repository → naam `creatorgrowth` → Public

### 2. Code push (Muse karega)
- Main browser se repo mein `creator-growth-platform/` ka code push kar dunga
- Tumhe sirf GitHub login confirm karna hoga

### 3. Render account + Blueprint (10 min)
- render.com par GitHub se sign up (free)
- Dashboard → **New → Blueprint** → `creatorgrowth` repo select
- `render.yaml` auto-detect hoga → **Apply**
- Render khud banayega: database + `creatorgrowth-api` + `creatorgrowth-web`

### 4. Verify (5 min)
- `https://creatorgrowth-api.onrender.com/health` → `{"status":"ok"}`
- `https://creatorgrowth-web.onrender.com` kholo → register karo → dashboard
- Pehla AI post generate + schedule kar ke test karo

## Zaroori notes
- **Free tier sota hai**: 15 min inactivity ke baad service sleep hoti hai, pehla request ~30–60 sec lega. Normal hai.
- **ENCRYPTION_KEY / JWT_SECRET**: Render khud generate karega (`generateValue: true`) — kahin note karne ki zaroorat nahi.
- **CORS**: agar frontend ka URL kuch aur bana (naam change hua), to API service ke `CORS_ORIGINS` env mein woh URL dal dena.
- **Database**: free Postgres 90 din tak rehta hai, phir expire — tab tak data ka backup le lena ya paid plan.
- Custom domain baad mein laga sakte hain (Render free mein deta hai).
