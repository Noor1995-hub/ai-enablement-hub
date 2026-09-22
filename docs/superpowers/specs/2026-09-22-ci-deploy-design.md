# CI-driven deploy — manual button, pre-deploy migration job, `BUILD_SHA` in health

**Date:** 2026-09-22
**Status:** draft for review
**Source:** `docs/reviews/2026-09-17/WAY-OF-WORKING-COMPARISON-2026-09-17.md` §5 Tier 1 items 1.1, 1.2, 1.3
**Decisions taken 2026-09-22 (Matthias):** deploy is a **manual button**, not on-merge; **both admins**
may press it (no GitHub environment / required reviewer); the app container **stops** running
migrations on start — the pre-deploy job is the only place migrations run; no dev database for now.
**Reference:** `bta-agents-portal` `.github/workflows/ci.yml` `rollout` job and `infra/50-cicd.ps1`
(study notes in `docs/reviews/2026-09-17/reference-bta-agents-portal.md` §4).

## 1. Goal

Replace "run `deploy.ps1` from a fresh worktree on a laptop" with a deploy that

- is started from GitHub's Actions tab by an admin, always from `main`, and builds the image from the
  **merged commit** on a clean runner — nobody's disk state can reach production;
- applies the database migration **before** rolling the app, in a separate Container Apps Job, and
  **fails closed**: if the job does not succeed, the app is not touched;
- rolls the app, then **polls until the live revision reports the expected image and `Running`**,
  and finally reads `/api/health` back and asserts it reports the deployed SHA;
- stamps `BUILD_SHA` and `BUILD_TIME` on the running app so "what is live?" is answered by the
  app itself, not by a hand-edited paragraph in `CLAUDE.md`;
- can **redeploy a previous image** (rollback lever) without a rebuild.

## 2. Non-goals

Deploy on merge (decided against). A staging environment or GitHub environment approvals. Key Vault
(the app keeps Container App secrets). Changing the nightly backup/restore jobs. Frontend tests,
Claude review, dev DB (other Tier 1/2 items). Schema rollback — migrations stay one-directional and
expand-first (PR template rule); rollback of code is re-pointing the image.

## 3. Design

### 3.1 One-time Azure setup (run with Matthias watching — ask-first rule)

Matthias is **Owner** on RG `imaginemore-playground` (verified 2026-09-22), so no ticket is needed.

1. **User-assigned identity** `ai-hub-cicd` in the RG.
2. **Federated credential** on it: issuer `https://token.actions.githubusercontent.com`, subject
   `repo:DLW-INT-BTA-BELUX/ai-enablement-hub:ref:refs/heads/main`, audience
   `api://AzureADTokenExchange`. A `workflow_dispatch` run on `main` presents exactly that subject;
   any other ref fails at login.
3. **Role assignments** (same shape as `bta-portal-cicd`): `AcrPush` on registry `ca530fc7463eacr`;
   `Contributor` on container app `ai-enablement-hub`; `Contributor` on the new job
   `ai-enablement-hub-migrate`. Nothing at RG scope.
4. **Migration job** `ai-enablement-hub-migrate` (Container Apps Job, environment
   `imaginemore-playground-cae`): trigger **Manual**, `replicaTimeout 600`, `replicaRetryLimit 0`,
   parallelism 1, cpu 0.25 / 0.5Gi; image = the **app image** (it already contains `alembic/`,
   `alembic.ini`, `src/` and the venv); registry auth via the ACR admin credential secret (same
   pattern as the backup job); one secret `alembic-database-url` copied from the app's secret of
   the same name; env `ALEMBIC_DATABASE_URL` → that secret. Command is set by the workflow on every
   run (`--command python --args migrate.py`) so the entry point is declared from git, not from
   portal state.
5. **GitHub repository variables** (not secrets — identifiers): `AZURE_CLIENT_ID` (identity client
   id), `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`. No Azure secret is stored in GitHub.

Recorded as an idempotent script `infra/50-cicd.ps1` (create-if-missing for each step, prints
what it did) plus the `gh variable set` lines, so the setup is reproducible.

### 3.2 Backend changes

- **New `backend/migrate.py`** — the job's entry point: Alembic Python API `upgrade(cfg, "head")`,
  prints the head before/after, exits non-zero on any exception. ~20 lines, copied from today's
  `startup.py` logic.
- **`backend/startup.py`** — drops the `command.upgrade` call; runs uvicorn only. Docstring: "Migrations
  run in the `ai-enablement-hub-migrate` job before each deploy (see `.github/workflows/deploy.yml`);
  the container never migrates." The Dockerfile already `COPY`s `startup.py`; add `migrate.py` to the
  same `COPY` line.
- **`AppSettings`** gains `build_sha: str = "dev"` and `build_time: str = ""` (env `APP__BUILD_SHA`,
  `APP__BUILD_TIME`, set by the workflow). **`/api/health`** returns
  `{"status": "ok", "build_sha": ..., "build_time": ...}` via a `HealthOut` schema. A unit test asserts
  the fields. This is a wire-contract change → `npm run gen:api` regenerates `schema.d.ts`.
- **Startup probe budget:** with no migration on start the app binds in seconds. The
  `infra/containerapp.yaml` comment and `failureThreshold` (48 → 12) are updated in the template;
  the **live** probe is left as-is (changing it is an `az containerapp update --yaml` with a full
  template — not worth the risk; note it as an optional later tidy-up).

### 3.3 Frontend change

Admin **Setup** page (`admin2/SetupPage.tsx`) gets a small "Deployment" card: `Build <short sha>`
linking to `https://github.com/DLW-INT-BTA-BELUX/ai-enablement-hub/commit/<sha>`, and "deployed
<relative time>" from `build_time`. Data via a new `useHealth()` hook in `admin2/api.ts`
(openapi-fetch, `GET /api/health`, no auth needed). Shows "dev build" when `build_sha === "dev"`.

### 3.4 The workflow — `.github/workflows/deploy.yml`

```yaml
name: Deploy
on:
  workflow_dispatch:
    inputs:
      image_sha:
        description: "Redeploy an existing image by full commit SHA (rollback). Leave empty to build and deploy main HEAD."
        required: false
        default: ""
permissions:
  contents: read
  id-token: write
concurrency:
  group: deploy-production     # never two deploys at once; never cancel a running one
  cancel-in-progress: false
env:
  RESOURCE_GROUP: imaginemore-playground
  APP_NAME: ai-enablement-hub
  JOB_NAME: ai-enablement-hub-migrate
  ACR_NAME: ca530fc7463eacr
  IMAGE_REPO: ai-enablement-hub
  AZURE_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}
  AZURE_TENANT_ID: ${{ vars.AZURE_TENANT_ID }}
  AZURE_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}
  IMAGE_SHA_INPUT: ${{ inputs.image_sha }}
jobs:
  deploy:
    name: build, migrate, roll, verify
    if: github.ref == 'refs/heads/main'      # the federated credential is bound to main
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps: …
```

Steps (all shell, inputs only via `env:`, `set -euo pipefail`):

1. **Checkout** `main` at `github.sha` (`actions/checkout@v4`).
2. **Resolve SHA.** `SHA = IMAGE_SHA_INPUT or github.sha`. If an input was given: assert it is a
   full 40-hex SHA and `git merge-base --is-ancestor $SHA HEAD` (no side-branch or unknown images),
   and assert the tag exists in ACR (`az acr repository show-tags`). Otherwise build.
3. **Azure login** `azure/login@v2` with the three ids (OIDC). `az acr login --name $ACR_NAME`.
4. **Build + push** (skipped when `image_sha` given): `docker build -t $ACR/$REPO:$SHA .` from the
   repo root (the real Docker daemon honours `.dockerignore` correctly, unlike the old az CLI), push
   `:$SHA`. No `:latest` tag — the SHA is the only identity.
5. **Migrate, fail-closed:** `az containerapp job update -n $JOB --image $ACR/$REPO:$SHA --command python --args migrate.py`; `exec=$(az containerapp job start … --query name -o tsv)`; poll
   `az containerapp job execution show` every 15 s up to 5 min; `Succeeded` → continue; `Failed |
   Degraded | Stopped | timeout` → `::error::` and exit 1 **before** the app is touched. Print the
   job's log tail on failure (`az containerapp job logs show … --container … --execution $exec`).
6. **Roll:** `BUILD_TIME=$(date -u +%FT%TZ)`; `az containerapp update -n $APP --image $ACR/$REPO:$SHA --set-env-vars APP__BUILD_SHA=$SHA APP__BUILD_TIME=$BUILD_TIME` (`--set-env-vars` is additive; all
   other env/secret refs are preserved).
7. **Poll until healthy:** every 15 s up to 10 min: `latestRevisionName` → `revision show` → image
   equals expected **and** `runningState in {Running, RunningAtMaxScale}` **and**
   `provisioningState == Provisioned`. Timeout → `::error::` exit 1 (the previous revision is still
   serving in Single mode until the new one is ready, so a failed roll is not an outage).
8. **Read-back:** `curl -fsS https://<app fqdn>/api/health` (fqdn read from `az containerapp show
   --query properties.configuration.ingress.fqdn`) and assert `.build_sha == $SHA`. Write a step
   summary: SHA, subject, image, revision, migration execution name, BUILD_TIME, health JSON.

### 3.5 Retiring the laptop path

- `deploy.ps1` → `infra/deploy-legacy.ps1`, header rewritten: "**Break-glass only** (GitHub Actions
  unavailable). Ships the working directory; the guard still requires a clean tree at
  `origin/main`. Does NOT run migrations — run the migrate job first with `az containerapp job
  start -n ai-enablement-hub-migrate` after updating its image." The `.claude/settings.json` ask
  patterns `*deploy.ps1*` already cover the new path (glob), add `*deploy-legacy.ps1*` explicitly.
- `CLAUDE.md` "Deployment & operations": deploy procedure = "Actions → Deploy → Run workflow (on
  `main`)"; rollback = same with `image_sha`; what is live = `/api/health`; the "record deploy in
  CLAUDE.md" habit is retired; `startup.py` no longer migrates; `deploy.ps1` gotchas move under a
  "legacy" heading.
- `CONTRIBUTING.md` "Deploying" section rewritten to the button, with the rule "deploy only what a
  merged PR put on `main`; if you need something live urgently, merge first".
- `README.md` Deploy line updated.

## 4. Rollout sequence

1. PR A (code): `migrate.py`, `startup.py`, `AppSettings` + `/api/health` + test, Dockerfile COPY,
   `gen:api`, Setup page card, `containerapp.yaml` template edit, `deploy.yml`, `infra/50-cicd.ps1`,
   `infra/deploy-legacy.ps1` move, docs. CI green, admin-merge. **At this point prod still runs the
   old image; nothing changed live.** Note: the *current live image* still migrates on start — fine.
2. **Azure one-time setup** (§3.1) — Matthias present, each command shown before it runs. Includes
   creating the job with the **current live image** and the copied secret, and setting the three
   GitHub variables.
3. **First button press** on `main` HEAD, both watching the Actions log. Expected: build ~4–6 min,
   migration job runs `alembic upgrade head` (no-op, prints the same head twice), roll, poll, health
   read-back shows the SHA. Live app now has `build_sha` and no longer migrates on start.
4. Verify §5. Then a follow-up docs PR records the run id + timings in `docs/superpowers/lessons.md`
   (created here if Tier 1.7 has not yet) and updates the memory note.

## 5. Verification

- `az containerapp show … --query properties.template.containers[0].image` equals `…:<SHA>`;
  `/api/health` returns that SHA and a fresh `build_time`; the admin Setup page shows the build card.
- `az containerapp job execution list -n ai-enablement-hub-migrate` shows one `Succeeded` execution
  whose end time precedes the new revision's creation time.
- `cd backend && uv run alembic current` unchanged (no-op migration).
- Negative test of fail-closed, **without touching prod data**: dispatch with an `image_sha` that is
  not an ancestor of `main` → step 2 fails; dispatch from a non-`main` ref → `if:` skips the job.
  (A genuinely failing migration is not rehearsed against the live DB — the portal's identical
  poll logic is the evidence, plus a code read.)
- Rollback drill: dispatch with `image_sha` = the previous SHA → no build, job runs (no-op), app
  rolls back, health shows the old SHA. Then roll forward again.
- Startup: container logs show uvicorn binding within seconds and **no** Alembic output.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Role assignment propagation delay → first `az acr login` fails | Wait 2–5 min after §3.1 before the first press; re-run is idempotent. |
| Federated subject mismatch | Subject string copied from the portal's working credential, only the repo name differs; failure is at login, before any change. |
| Job cannot pull the image | Same ACR admin-credential secret pattern as the backup job (proven); the workflow updates the image before starting. |
| Job secret drifts from the app's `alembic-database-url` after a password rotation | `db/README.md` rotation procedure gains one line: update the job secret too; `infra/50-cicd.ps1` documents the secret name. |
| Migration succeeds but roll fails | Expand-first rule means the old image keeps working on the new schema; re-press the button. |
| Roll succeeds but health read-back shows old SHA | Poll already asserted the image; a mismatch means the env var did not apply — step fails loudly, investigate before declaring done. |
| Runner Docker build slower than ACR Tasks | Portal's identical build runs ~4 min; acceptable for a manual button. |
| Someone still runs the legacy script | It is under `infra/`, guarded, documented as break-glass, and the hooks ask before it runs. |

## 7. Open points (do not block)

- Shrinking the live startup probe `failureThreshold` (template updated, live untouched).
- `:latest` tag deliberately not pushed; the backup job's "roll both jobs together" note is unrelated.
- Whether to add a Teams/email notification on deploy (later, with alerting in Tier 2.9).
