# Nightly logical backups of the `ai-enablement-hub` database

**Date:** 2026-07-29
**Branch:** `main`
**Status:** design approved, ready for implementation plan

## Goal

Make the production database **restorable** — selectively and beyond Azure's 7-day
window — with the least infrastructure and cost that honestly achieves that.

Concretely, after this work these three situations are recoverable:

1. "A content pass three weeks ago wrecked a lesson" → restore one table from a
   dated dump and copy the rows back, without touching anything else.
2. "A migration or script destroyed data and nobody noticed for 10 days" → the dump
   from before it exists (30-day retention beats the 7-day PITR window).
3. "The server/database is gone" → recreate it from a dump plus the role globals.

## Scope

**In scope:** restorable backups (disaster recovery).

**Explicitly out of scope** (asked and answered 2026-07-29 — the user selected DR only):

- Content version history / diff / rollback as a product feature.
- An audit trail of who changed what.
- Refreshing dev/test from a prod copy.
- Backups of the **lesson media blobs** (see §8 — flagged, not solved here).

## Context (what exists today)

- **Server:** `imaginemore-playground-pg` (PG **18**, Burstable `Standard_B2s`, 32 GB,
  Sweden Central, RG `imaginemore-playground`). Databases: `ai-enablement-hub` (prod)
  and `ai-enablement-hub-test` (backend integration tests).
- **Azure backup state (read 2026-07-29):** automatic PITR **on**, retention
  **7 days**, `geoRedundantBackup: Disabled`, `highAvailability: Disabled`,
  `autoGrow: Disabled`, earliest restore `2026-07-22T15:30Z`.
- **Two hard constraints this design works around:**
  - Azure PITR restores the **whole server to a new server**. There is no
    single-database, single-table or single-row restore. Recovering one bad content
    edit today means provisioning a restore server and hand-copying rows out.
  - `geoRedundantBackup` **cannot be enabled after server creation** on PG Flexible
    Server, and the retention knob is **server-wide** — the playground server is
    shared with other apps (bta-portal, dellie), so we do not touch it.
- **Schema is versioned** (Alembic, prod head `c6d7e8f9a0b1`). **Data is not.**
  Admin-UI edits (`PATCH /api/admin/lessons/{id}`) overwrite `content_blocks` in place
  with no history. [`db/baseline/data/lessons.json`](../../../db/baseline/data/lessons.json)
  is git-tracked but is a **frozen 2026-07-03 snapshot** that only advances when
  someone manually runs
  [`sync_baseline.py`](../../../db/content_tools/sync_baseline.py) after a *scripted*
  edit pass — it does not observe admin-UI edits and is not a backup.
- **Storage accounts in the RG:** `aienablementhubmedia` (StorageV2, **LRS**, holds
  lesson media, key already wired into the app) and `imaginemoreplaygroundsa`
  (StorageV2, RA-GRS, shared playground account).
- **Already-available building blocks:** ACR `ca530fc7463eacr`, Container Apps
  environment `imaginemore-playground-cae`, deploy tooling
  [`deploy.ps1`](../../../deploy.ps1), ACS email for notifications.

## Design

### 1. Azure PITR stays exactly as-is

No change to the server's backup retention, replication or HA. PITR keeps covering
fine-grained recent recovery ("restore to 14:32 yesterday"); the dumps below cover
selective and older recovery. The two are complementary, and leaving the shared
server's settings alone avoids affecting the sibling apps.

### 2. One scheduled Container Apps Job

A single Azure Container Apps **Job** in the existing `imaginemore-playground-cae`
environment:

| Setting | Value |
|---|---|
| Name | `ai-enablement-hub-db-backup` |
| Trigger | Schedule, cron `30 2 * * *` (**02:30 UTC** ≈ 04:30 local CEST) |
| Parallelism / completions | 1 / 1 |
| Replica timeout | 900 s |
| Retry limit | 1 |
| Resources | 0.25 CPU / 0.5 Gi |
| Identity | **system-assigned managed identity** |
| Image | `ca530fc7463eacr.azurecr.io/ai-enablement-hub-db-backup:<date-tag>` |

### 3. Its own small image — not the app image

`infra/backup/Dockerfile`:

```dockerfile
FROM postgres:18-bookworm          # guarantees pg_dump 18 == server major version
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3-minimal python3-pip \
 && pip install --no-cache-dir --break-system-packages azure-identity azure-storage-blob \
 && apt-get purge -y python3-pip && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*
COPY backup.py /usr/local/bin/backup.py
ENTRYPOINT ["python3", "/usr/local/bin/backup.py"]
```

**Why a separate image rather than adding `postgresql-client` to the app
[`Dockerfile`](../../../Dockerfile):** it keeps the production app's build and deploy
path untouched. A backup-script change cannot break the app build, an app deploy
cannot change the backup's `pg_dump`, and the app image doesn't grow or gain a
build-time dependency on an external apt repo. Cost of the split: one extra
`az acr build` when `backup.py` changes (rare).

The official `postgres:18-bookworm` base is chosen over installing the PGDG apt repo
into a slim image: `pg_dump` **refuses to dump from a newer server** than itself, so
the client major version must track the server's, and the official image pins that
for free.

### 4. Credentials and authorization

- **Database:** job secret `backup-database-url` = the `ai_hub_owner` DSN
  (`sslmode=require`), exposed as `PGURL`. `ai_hub_owner` owns every table, so the
  dump is guaranteed complete; `ai_hub_app` only has DML grants and could silently
  miss objects.
- **Blob:** the job's **system-assigned managed identity** with
  `Storage Blob Data Contributor` **scoped to the `db-backups` container only**
  (not the account, not the RG). `DefaultAzureCredential` in `backup.py` picks it up.
  Nothing expires, and no storage account key is handed to the job — which also means
  the job cannot touch the lesson-media container.

### 5. What each run does

```
1. pg_dump -Fc -d $PGURL -f /tmp/ai-enablement-hub-<ts>.dump      # compressed custom format
2. pg_dumpall --globals-only --no-role-passwords -d $PGURL \
       -f /tmp/globals-<ts>.sql                                   # roles, for a from-scratch rebuild
3. VERIFY (all must hold, else exit non-zero and upload nothing):
     - both commands exited 0
     - dump file size >= MIN_DUMP_BYTES floor
     - `pg_restore --list` on the dump lists >= EXPECTED_TABLE_COUNT "TABLE DATA" entries
4. upload both to blob, passing a locally computed MD5 so Azure rejects a corrupted
   transfer server-side
5. PRUNE: list blobs under the prefix, delete those older than 30 days whose name
   matches the backup filename pattern
6. print a one-line summary (paths, bytes, table count, pruned count)
```

`--no-role-passwords` is required, not cosmetic: reading role password hashes needs
`pg_authid` access that `ai_hub_owner` does not have on Azure PG, and without the flag
`pg_dumpall` fails. Role passwords are not in the backup by design — they live in
`db/.env` and are re-settable with `db/provision_roles.py --rotate-passwords`. If
`pg_dumpall` turns out to need privileges `ai_hub_owner` lacks even with the flag, the
fallback is a documented manual globals capture (the roles are already described in
[`db/README.md`](../../../db/README.md)) — decided during implementation, not silently
dropped.

`EXPECTED_TABLE_COUNT` and `MIN_DUMP_BYTES` are env vars on the job. Defaults are
derived from the first successful run (observed table count and dump size), then set a
margin below it — high enough that a truncated or empty dump fails, low enough that
normal schema growth never does.

### 6. Storage layout and retention

Reuses the existing `aienablementhubmedia` account (user's call: least work, lowest
cost). New **private** container `db-backups` (no public access):

```
db-backups/ai-enablement-hub/YYYY/MM/DD/ai-enablement-hub-YYYYMMDDTHHMMSSZ.dump
db-backups/ai-enablement-hub/YYYY/MM/DD/globals-YYYYMMDDTHHMMSSZ.sql
```

Retention is **30 days**, pruned **by the script** (step 5 above) rather than by a
storage lifecycle-management policy. Reason: lifecycle policies are account-wide with
prefix filters, and a mistyped prefix on this account would delete **lesson media**.
Script-side pruning is scoped to one container, one prefix and one filename pattern,
and is testable.

**Accepted tradeoff:** `aienablementhubmedia` is **LRS**, so a Sweden Central regional
loss takes the app, the database and the backups together. This is reversible for
pennies later — `az storage account update --sku Standard_GRS` is non-disruptive — and
is recorded here as a known, accepted limitation rather than an oversight.

### 7. Failure visibility

A backup nobody watches isn't a backup. Two cheap layers:

- **Azure Monitor alert rule** on the job's **failed executions** (metric
  `JobExecutionCount`, dimension `Status = Failed`, threshold > 0, 24 h window) →
  action group emailing `matthias.danneel@delaware.pro`. This covers dump failure,
  verification failure, upload failure and image/auth breakage. If that metric or
  dimension turns out not to be queryable for jobs in this environment, fall back to an
  **activity-log alert** on the job resource's failed executions — the requirement is
  "a failed run emails Matthias", not a specific metric.
- **Freshness check in the runbook** — a documented 30-second command:
  `az storage blob list -c db-backups --prefix ai-enablement-hub/ --query "[-1].name"`.
  This is the manual guard against the one failure the metric alert can't see:
  the job never running at all.

### 8. Restore runbook + one real drill (the acceptance test)

New doc `docs/db-backup-restore.md`, covering three paths:

1. **One table** — download a dated dump, `pg_restore -t <table> --data-only` into a
   scratch database, then copy the wanted rows across to prod. (The everyday case:
   undo a bad content edit.)
2. **Whole database** — `pg_restore` into a freshly created database, then repoint or
   rename.
3. **Whole server lost** — create a new flexible server, apply `globals-*.sql`
   (roles), `pg_restore` the dump, re-run `db/provision_roles.py` for default
   privileges, update the Container App's DB secrets.

The doc also records: the SAS-free MI auth model, the freshness command, the LRS
limitation, and the fact that PITR remains the tool for sub-day recovery.

**The drill is part of the work, not a follow-up.** Once, for real: restore the newest
dump into a scratch database `ai-enablement-hub-restoredrill` on the same server,
verify row counts per table against live, spot-check one lesson's `content_blocks`,
then drop the scratch database. The work is not complete until this passes and the
observed numbers are written into the runbook.

## Acceptance criteria

- [ ] `infra/backup/Dockerfile` + `infra/backup/backup.py` committed; image built in ACR.
- [ ] Container Apps Job exists, schedule `30 2 * * *`, system-assigned MI, DB secret set.
- [ ] Private `db-backups` container exists; MI holds `Storage Blob Data Contributor`
      scoped to that container and nothing wider.
- [ ] A **manually triggered** run (`az containerapp job start`) succeeds end-to-end and
      leaves a `.dump` + `globals-*.sql` blob at the expected path.
- [ ] Negative check: with a deliberately broken DSN the run exits non-zero and uploads
      nothing (proves failures are loud, not silent).
- [ ] Prune logic verified against synthetic old blobs (deletes >30 d, keeps ≤30 d, and
      leaves non-matching names alone).
- [ ] Monitor alert rule + action group exist; alert fires to email on the failed run above.
- [ ] `docs/db-backup-restore.md` written, and the **restore drill executed** with row
      counts matching live; scratch DB dropped afterwards.
- [ ] `CLAUDE.md` gains a short "Backups" entry pointing at the runbook.

## Azure / DB mutations required (each confirmed at execution time)

Per the standing ask-first rule, every one of these is a separate confirmation, not
covered by approval of this spec:

1. `az acr build` of the backup image into `ca530fc7463eacr`.
2. `az storage container create -n db-backups` (private) on `aienablementhubmedia`.
3. `az containerapp job create` (+ its secret, + system-assigned identity).
4. `az role assignment create` — `Storage Blob Data Contributor`, container-scoped.
5. `az monitor action-group create` + `az monitor metrics alert create`.
6. `CREATE DATABASE "ai-enablement-hub-restoredrill"` for the drill, and `DROP` after.
7. One manual `az containerapp job start` to prove the pipeline.

## Optional extras — NOT in scope unless separately approved

Both are one command each and were flagged during design; neither is assumed:

- **Blob soft-delete** on `aienablementhubmedia` (e.g. 14 days). Protects the lesson
  media *and* these backups from accidental deletion. Recommended.
- **Resource lock** (`CanNotDelete`) on the PG flexible server, guarding against
  accidental deletion of the server itself.

## Known limitations, recorded deliberately

- **LRS**: backups share the region with everything else (§6). Reversible.
- **Media not backed up**: a deleted lesson-media blob is unrecoverable today unless
  soft-delete is enabled. Out of scope here; the extras above are the cheap mitigation.
- **Hosting move**: the pending delaware IT hosting move will require recreating the
  job, its identity and the role assignment in the new environment, and repointing the
  storage target. Because the whole thing is a Dockerfile, one script and ~5 CLI
  commands, that is a re-run of §"mutations", not a redesign.
- **Daily granularity**: up to ~24 h of learner progress could be lost if PITR is also
  unavailable. Accepted (chosen cadence); PITR covers the sub-day window for 7 days.
