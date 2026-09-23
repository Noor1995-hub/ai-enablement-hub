# AI Enablement Hub

Learning platform for delaware's AI enablement programme: maturity assessment → personalised
learning path (tracks / modules / lessons) → AI interviewer, with an admin panel for people,
assignments, content and AI features.

**Live (production):**
https://ai-enablement-hub.kindcoast-3b1fe056.swedencentral.azurecontainerapps.io

**Stack:** FastAPI (Python 3.13, uv) · React 18 + TypeScript (Vite) · Azure Database for
PostgreSQL · one Azure Container App serving API + SPA · Anthropic API for the AI features.

> ⚠️ **Dev and prod share one database.** There is no separate dev DB. Read the warning at the
> top of [CLAUDE.md](CLAUDE.md) before running migrations or writing any data.

## Quickstart

```powershell
# Backend (from backend/) — needs backend/.env, see backend/.env.local.example
uv run poe dev        # http://localhost:8000, Swagger at /docs
uv run poe format; uv run poe lint; uv run poe test   # checks

# Frontend (from frontend/)
npm install
npm run dev           # http://localhost:5173, proxies /api -> :8000
npm run typecheck; npm run lint; npm run build        # checks
```

Deploy: GitHub → Actions → **Deploy** → Run workflow (on `main`). See [CONTRIBUTING.md](CONTRIBUTING.md) → Deploying.

## Where to look

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — how to make a change: branch → PR → green CI → squash
  merge. `main` is protected. **Humans: read this first.**
- **[CLAUDE.md](CLAUDE.md)** — the operational guide (current state, conventions, feature
  index, locking semantics, deploy/ops). **AI agents: read this first.**
- **[python-be-architecture.md](python-be-architecture.md)** — mandatory backend conventions.
- **[docs/README.md](docs/README.md)** — map of the docs tree (feature specs/plans, reviews,
  content model, runbooks).
- **[db/README.md](db/README.md)** — database roles, credentials, procedures.
