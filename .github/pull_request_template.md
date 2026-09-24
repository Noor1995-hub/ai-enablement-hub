## What & why

<!-- One or two sentences: what changes for a learner, an admin, or an operator, and why. -->

## Checklist

- [ ] Backend checks pass locally (in `backend/`): `uv run poe format-check && uv run poe lint-src && uv run poe ty-src && uv run poe test`
- [ ] Frontend checks pass locally (in `frontend/`): `npm run typecheck && npm run lint && npm run build`
- [ ] No secret is committed — real values live only in the git-ignored `backend/.env` / `db/.env`
- [ ] **Migration** (if this adds one under `backend/alembic/versions/`): additive / expand-first, fast on the live tables, safe to run twice — it runs unattended on container start against the production database
- [ ] **Learner-facing change** (if any): verified with production-shaped fixtures and a stubbed `fetch`, never by creating users, surveys or progress (see CLAUDE.md → "Verifying without touching live data")
- [ ] **Prompt change** (`backend/prompts/**`): treated as a production change; confirmed no DB override on the admin System Prompts page masks it
- [ ] `CLAUDE.md` / `docs/` updated where this changes how the app is run or operated
- [ ] Verified with evidence, not assumed

## Linked issue

Closes #

<!--
Merging: `main` is protected. Both CI checks must be green (no bypass, admins included) and the
PR needs one approving review unless a repo admin merges it. Squash merge only:
`gh pr merge --squash --delete-branch`. Flow and policy: CONTRIBUTING.md.
-->
