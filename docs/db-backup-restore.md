# Database backups & restore runbook

**What protects the `ai-enablement-hub` database**

| Layer | Covers | Window | Granularity |
|---|---|---|---|
| Azure PITR (server-level, untouched by us) | server/infrastructure loss, "restore to 14:32 yesterday" | 7 days | whole server → a NEW server |
| Nightly logical dumps (this runbook) | bad edits, bad migrations, bad scripts, older mistakes | 30 days | one table, one row, or the whole DB |

Design: [`docs/superpowers/specs/2026-07-29-database-backups-design.md`](superpowers/specs/2026-07-29-database-backups-design.md).
Code: [`infra/backup/`](../infra/backup/README.md).

**The moving parts** (all in RG `imaginemore-playground`, subscription
`e2b785b0-d93d-4c19-9537-4f752f759cb1`):

| Thing | Name |
|---|---|
| Nightly job | `ai-enablement-hub-db-backup` — cron `30 2 * * *` UTC |
| Manual restore job | `ai-enablement-hub-db-restore` |
| Image (both jobs) | `ca530fc7463eacr.azurecr.io/ai-enablement-hub-db-backup:<tag>` |
| Blob container | `db-backups` (private) on `aienablementhubmedia` |
| Alert rules | `ai-hub-db-backup-failed` (Sev1), `ai-hub-db-backup-missing` (Sev2) |
| Action group | `ai-hub-backup-alerts` → matthias.danneel@delaware.pro |
| Log Analytics workspace | `workspaceimaginemoreplayground897c` (customerId `b588bbe8-2fa8-4da0-9ee9-bdd4438fd8bc`) |

Both jobs authenticate to Blob Storage with their **own system-assigned managed
identity**, each scoped to the `db-backups` container only (backup =
`Storage Blob Data Contributor`, restore = `Storage Blob Data Reader`). No storage
keys live in either job. The database credential is the job secret
`backup-database-url` / `restore-target-url` (the `ai_hub_owner` DSN).

## Prerequisites on your machine

There is **no `psql`, no `pg_restore`, no `pg_dump` and no Docker** on the dev
machine (checked 2026-07-29). Everything below therefore runs either **inside
Azure** (the jobs) or through **`uv run` scripts using asyncpg** — nothing here
needs a Postgres client install. Do not rewrite these steps to assume one.

Every snippet assumes:

```powershell
$env:PYTHONIOENCODING='utf-8'
$az = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'    # not on PATH
```

## Is the backup healthy?

```powershell
$key = & $az storage account keys list -n aienablementhubmedia -g imaginemore-playground --query "[0].value" -o tsv
& $az storage blob list -c db-backups --account-name aienablementhubmedia --account-key $key `
    --prefix ai-enablement-hub/ --query "[].{name:name, bytes:properties.contentLength}" -o table
```

The newest entry should be dated **today or yesterday** (the job runs 02:30 UTC).
Typical size as of 2026-07-30: **775,806 bytes** for the dump covering **25
tables**, plus a **5,678-byte** `globals-*.sql`.

You should not normally need this check — a failed run emails you within ~15
minutes (`ai-hub-db-backup-failed`), and a job that stops running at all emails
you within an hour of the 48-hour mark (`ai-hub-db-backup-missing`).

### Reading a job's log output

`az containerapp job logs show` and `az monitor log-analytics query` both require
az CLI **extensions that are not installed**, and the install prompt fails with
`EOF when reading a line` in a non-interactive shell. Use the built-in
`az rest` against the Log Analytics API instead:

```powershell
$q = '{"query":"ContainerAppConsoleLogs_CL | where ContainerGroupName_s startswith ''ai-enablement-hub-db-backup'' | order by TimeGenerated desc | take 30 | project TimeGenerated, Stream_s, Log_s"}'
$body = Join-Path $env:TEMP 'la-query.json'; Set-Content -Path $body -Value $q -Encoding utf8
$resp = & $az rest --method post --url "https://api.loganalytics.io/v1/workspaces/b588bbe8-2fa8-4da0-9ee9-bdd4438fd8bc/query" `
    --resource "https://api.loganalytics.io" --body "@$body" -o json | ConvertFrom-Json
$resp.tables[0].rows | ForEach-Object { "[$($_[1])] $($_[2])" }
```

A healthy run ends with one line: `OK dump=… bytes=… tables=… kept=… pruned=…`.
A failed run prints `FATAL: …` on stderr (which *is* captured, `Stream_s='stderr'`).

## Restore path 1 — one table (the common case: undo a bad content edit)

1. Find the dump from before the damage (blob listing above).
2. Create the scratch database. **This needs the Entra admin**, because
   `ai_hub_owner` has `rolcreatedb=False`:

```powershell
$tok = & $az account get-access-token --resource https://ossrdbms-aad.database.windows.net --query accessToken -o tsv
$env:LIVE_DSN = "postgresql://danneelm%40delawareconsulting.com:$tok@imaginemore-playground-pg.postgres.database.azure.com/ai-enablement-hub?sslmode=require"
uv run infra/backup/drill_db.py --check     # confirms rolcreatedb=True for this connection
uv run infra/backup/drill_db.py --create    # creates it AND hands `public` to ai_hub_owner
```

   Both privilege steps matter. Owning the database is **not** enough on this
   server: the fresh database's `public` schema is not owned by
   `pg_database_owner`, so without the `ALTER SCHEMA public OWNER` that
   `--create` performs, the restore job dies on
   `permission denied for schema public`. (Learned the hard way 2026-07-30.)

3. Restore just the table you need into it:

```powershell
$dsnRestored = '<ai_hub_owner DSN with dbname=ai-enablement-hub-restoredrill>'
& $az containerapp job secret set -n ai-enablement-hub-db-restore -g imaginemore-playground `
    --secrets "restore-target-url=$dsnRestored"
& $az containerapp job update -n ai-enablement-hub-db-restore -g imaginemore-playground `
    --set-env-vars "SOURCE_BLOB=ai-enablement-hub/2026/07/10/ai-enablement-hub-20260710T023000Z.dump" "RESTORE_TABLE=lessons"
& $az containerapp job start -n ai-enablement-hub-db-restore -g imaginemore-playground
```

   Leave `SOURCE_BLOB` empty to take the newest dump. Watch it with the log
   snippet above (`ai-enablement-hub-db-restore`); success ends with
   `OK restored table lessons from …`.

4. Move the row back. Postgres cannot query across databases, so this is a
   two-connection script — dry run first, it writes nothing without `--apply`:

```powershell
$env:LIVE_DSN     = '<ai_hub_owner DSN, dbname=ai-enablement-hub>'
$env:RESTORED_DSN = '<same credentials, dbname=ai-enablement-hub-restoredrill>'
uv run infra/backup/copy_lesson.py --lesson-id <uuid>            # shows the diff
uv run infra/backup/copy_lesson.py --lesson-id <uuid> --apply     # writes to live
```

5. Check the lesson in the app, then clean up:

```powershell
& $az containerapp job update -n ai-enablement-hub-db-restore -g imaginemore-playground --set-env-vars "SOURCE_BLOB=" "RESTORE_TABLE="
& $az containerapp job secret set -n ai-enablement-hub-db-restore -g imaginemore-playground --secrets "restore-target-url=placeholder"
uv run infra/backup/drill_db.py --drop     # as the Entra admin again
```

   Resetting the secret to `placeholder` matters: it means a stray manual start
   cannot write into anything real.

## Restore path 2 — the whole database

Exactly path 1 without `RESTORE_TABLE`, into a freshly created empty database.
Then either repoint the app (its `database-password` / `alembic-database-url`
Container App secrets) or copy tables across. Restoring **over** the live
database is deliberately not supported by this job — create a new database and
switch to it.

## Restore path 3 — the server is gone

1. Create a new PG 18 flexible server (ask before provisioning).
2. Apply the matching `globals-*.sql` to recreate the roles. **Role passwords are
   NOT in it** (`pg_dumpall --no-role-passwords` is mandatory here — `ai_hub_owner`
   cannot read `pg_authid`): set them from `db/.env`, or rotate with
   `uv run db/provision_roles.py --rotate-passwords`.
3. Create the `ai-enablement-hub` database, point the restore job's
   `restore-target-url` at it, and run the job.
4. Re-run `uv run db/provision_roles.py` for the default privileges that let
   `ai_hub_app` work without GRANTs in migrations.
5. Update the app's DB secrets and redeploy.

## Drill result — 2026-07-30 (passed)

Newest dump restored into `ai-enablement-hub-restoredrill` via the restore job,
then compared with `verify_restore.py`. **All 25 tables present and non-empty**;
`exit=0`. Lesson `f2faf741-d02e-417a-ac31-42adcd49ab80` ("Artifacts and
structured output"): 16 `content_blocks` on both sides, `identical=True`.

```
table                             restored      live     delta
alembic_version                          1         1        +0
auth_sessions                           72        73        -1
auth_tokens                             81        81        +0
calibration_notes                        0         0        +0
companies                                4         4        +0
conversations                            9         9        +0
curricula                                7         7        +0
feedback                                75        75        +0
lesson_content_proposals                 5         5        +0
lesson_progress                        294       295        -1
lessons                                121       121        +0
messages                                60        60        +0
module_prerequisites                    33        33        +0
modules                                 42        42        +0
project_ai_settings                     12        12        +0
project_component_settings              19        19        +0
project_email_templates                  4         4        +0
project_track_defaults                  18        18        +0
projects                                 8         8        +0
survey_responses                        46        46        +0
tracks                                  13        13        +0
user_lessons                          5316      5316        +0
user_modules                          1754      1754        +0
user_tracks                            479       479        +0
users                                  103       103        +0
```

The two `-1` deltas are `auth_sessions` and `lesson_progress` — live keeps moving
after a dump is taken. Deltas on those tables are expected, not a failure.

The scratch database was dropped afterwards and the restore job's target secret
reset to `placeholder`. **Re-run this drill after any change to `infra/backup/`
or to the storage layout.**

Also proven the same day: a forced verification failure
(`EXPECTED_TABLE_COUNT=9999`) logged
`FATAL: dump lists 25 TABLE DATA entries, expected >= 9999`, uploaded **nothing**
(blob count unchanged), the execution settled `Failed`, and
`ai-hub-db-backup-failed` fired Sev1 within ~1 minute.

## Gotchas worth knowing before you debug

- **The `Executions` metric is useless here.** Container Apps jobs expose
  `Executions` with a `state` dimension, but it reported `0.0` on every datapoint
  even during minutes when executions ran and succeeded. That is why alerting is
  log-based, not metric-based. Do not "simplify" it back to a metric alert.
- **Job execution status lags.** A finished execution can read `Running`, then
  `Unknown`, before settling on `Succeeded`/`Failed`. Trust the logs.
- **`--replica-retry-limit 1`** on the backup job means one bad night produces two
  failed attempts, not one.
- **PowerShell 5.1 mangles `$1`.** In a double-quoted PowerShell string, `$1`
  expands to *empty*, which silently corrupts any SQL with positional
  placeholders. That is why the operator steps are committed `uv run` scripts
  instead of inline one-liners — keep it that way.
- **`az acr build` crashes while streaming logs** (`'charmap' codec can't
  encode…`) even with `PYTHONIOENCODING=utf-8`. The build itself is fine; use
  `--no-wait` and poll `az acr task list-runs`.

## Known limitations (accepted)

- Backups live in `aienablementhubmedia`, which is **LRS** — a Sweden Central
  regional loss takes app, database and backups together. Reversible for pennies:
  `az storage account update -n aienablementhubmedia -g imaginemore-playground --sku Standard_GRS`.
- Up to ~24 h of learner progress could be lost if PITR is unavailable too.
- **Lesson media blobs are not backed up.** A deleted media blob is gone unless
  blob soft-delete gets enabled on the account.
- Role passwords are not in the globals dump (see path 3).
- The pending hosting move will require recreating both jobs, their identities,
  the role assignments and the alert rules in the new environment.
