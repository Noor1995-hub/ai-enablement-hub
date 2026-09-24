# Security

**The rule:** no secret value ever appears in this repo — not in a file, an issue, a PR
description, a commit message, a workflow log, or a Claude Code transcript. Real values live in
the git-ignored local `.env` files or in Azure Container App / Container Apps Job secrets.
`backend/.env.local.example` documents the shape with placeholders only. If you ever think
"I'll just paste the key for a second" — don't.

## Secrets this project uses

Inventory verified against Azure and GitHub on 2026-09-23 (names only; values were not read).

### Production — Container App `ai-enablement-hub` secrets

| Secret | Env var in the app | What it is |
|---|---|---|
| `database-password` | `DATABASE__PASSWORD` | Password of the `ai_hub_app` Postgres role (runtime DML only) |
| `alembic-database-url` | `ALEMBIC_DATABASE_URL` | Full DSN of the `ai_hub_owner` role (DDL, owns every table) |
| `jwt-secret` | `AUTH__JWT_SECRET` | Signs learner access/refresh tokens. **Differs from the dev value.** |
| `acs-connection-string` | `EMAIL__CONNECTION_STRING` | Azure Communication Services `imaginemore-playground-acs` — sends invite/reset email |
| `storage-connection-string` | `STORAGE__CONNECTION_STRING` | Account key of storage account `aienablementhubmedia` (lesson media) |
| `llm-api-key` | `LLM__API_KEY` | Anthropic API key for the AI features. Whether it is a spend-capped workspace key is **unverified** — see `docs/ai-agents-plan.md` §8b |
| `acr-password` | — (registry pull) | Admin password of registry `ca530fc7463eacr` |

### Production — Container Apps Job secrets

| Job | Secret | What it is |
|---|---|---|
| `ai-enablement-hub-migrate` | `alembic-database-url` | Same `ai_hub_owner` DSN as the app — **update both on a rotation** |
| `ai-enablement-hub-db-backup` | `backup-database-url` | `ai_hub_owner` DSN used by the nightly dump |
| `ai-enablement-hub-db-restore` | `restore-target-url` | Target DSN of a restore; parked at `placeholder` between drills (`docs/db-backup-restore.md`) |
| all three | `ca530fc7463eacrazurecrio-ca530fc7463eacr` | Registry pull password (same ACR admin credential as `acr-password`) |

### Local machine (git-ignored)

| File | Keys that are secret | Notes |
|---|---|---|
| `backend/.env` | `DATABASE__PASSWORD`, `ALEMBIC_DATABASE_URL`, `AUTH__JWT_SECRET`, `ENTRA__CLIENT_SECRET`, `EMAIL__CONNECTION_STRING`, `STORAGE__CONNECTION_STRING`, `LLM__API_KEY` | Points at the **live** database (the one-database rule). Email and storage keys reach the real shared resources. |
| `db/.env` | `AZURE_PG_OWNER_PASSWORD`, `AZURE_PG_OWNER_DSN`, `AZURE_PG_APP_PASSWORD`, `AZURE_PG_APP_DSN` | Written by `db/provision_roles.py`; source of the DB values above |

`ENTRA__CLIENT_SECRET` (app registration `ad61703c-…`, client secret `hub-oidc`, expires July
2028) exists only in `backend/.env` — production runs with Entra login dark.

### GitHub (`DLW-INT-BTA-BELUX/ai-enablement-hub`)

| Name | Kind | Notes |
|---|---|---|
| `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | Actions **variables**, not secrets | Identifiers for the OIDC login of identity `ai-hub-cicd`. Knowing them grants nothing: the federated credential only accepts tokens GitHub issues to this repo's `main`. |
| `ANTHROPIC_API_KEY` | Actions **repository secret** (added 2026-09-23) | Used only by `claude-code-review.yml`. Bills to **delaware's** Anthropic workspace; **not spend-capped** (believed) — a monthly limit on the key in the Anthropic Console is the cheap fix. Nobody can read it back from GitHub; admins can overwrite it. Anyone with write access (the repo admins) could add a workflow that prints it, which is one reason write access stays admin-only. The deploy itself stores no secret (OIDC). |

### Not secrets, but credentials all the same

- **Postgres Entra admin** of `imaginemore-playground-pg`: `danneelm` (short-lived AAD tokens,
  see `db/README.md`). A single person — a handover item.
- **Learner passwords, invite/reset tokens and refresh tokens** are stored hashed in the
  database and never logged.

## Who can read them

- **Container App and Job secrets:** anyone holding Contributor, Owner or Container Apps
  Contributor on resource group `imaginemore-playground` **or on the whole subscription**. On
  2026-09-23 that was about 35 people plus several service principals — far more than the hub
  team, because the playground is shared. Treat every secret above as readable by the wider
  delaware playground population. Check the current list with
  `az role assignment list -g imaginemore-playground --include-inherited -o table`. (This is the
  reason the hosting move to a dedicated environment is on the IT ticket.)
- **`backend/.env` / `db/.env`:** whoever has the file on their machine (today: Matthias).
- **The Deploy button:** repo admins (write access is required for `workflow_dispatch`). Seven
  admins on 2026-09-23, most inherited from the org; `gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/collaborators`.
- **The Anthropic keys:** the app's `llm-api-key` — anyone with access to the Anthropic Console
  workspace that issued it (Matthias, Aaron), plus everyone who can read Container App secrets.
  The review key `ANTHROPIC_API_KEY` — delaware's Anthropic workspace admins; on GitHub it is
  write-only.

## Rotations owed

| Secret | Why | Blast radius | Status |
|---|---|---|---|
| Dev `AUTH__JWT_SECRET` (`backend/.env`) | Leaked into a tool transcript 2026-07-06 | Dev only: prod uses a different value. A forged token works only against a locally running dev server — which does talk to the live DB. | Owed — #42 |
| `aienablementhubmedia` account key (`storage-connection-string` + `backend/.env`) | Leaked into a tool transcript 2026-07-30 | Read/write/delete on all lesson media in production | Owed — #43 |

How, when the time comes (everything except the dev JWT secret changes Azure — agents ask
first):

- **Dev JWT secret:** `python -c "import secrets; print(secrets.token_urlsafe(48))"` into
  `backend/.env`. Local sessions log out once; nothing on Azure changes.
- **Storage key:** the account has two keys. Point the app's `storage-connection-string` (and
  `backend/.env`) at the key that is **not** in use, restart the revision so it picks the secret
  up, check a lesson image loads, then regenerate the old key. No downtime.
- **DB role passwords:** `db/provision_roles.py --rotate-passwords`, then update the app's
  `database-password` + `alembic-database-url`, the migrate job's `alembic-database-url` and the
  backup job's `backup-database-url` (`db/README.md`).

## Rotate on handover

When the repo, the Azure resources, the Anthropic workspace, or an operator changes hands —
someone leaves the team, the app moves to new hosting, a laptop is decommissioned — rotate the
secrets that person or place could read. Rotating costs minutes; a stale, still-valid key in the
wrong hands does not. At the hosting move, rotate **everything** in the tables above: the
current values have lived in a shared playground.

## Reporting a concern

Internal delaware tool, no external users. Raise a security concern directly with the repo
admins (Matthias Danneel, Aaron Neuville) rather than in a GitHub issue or PR.
