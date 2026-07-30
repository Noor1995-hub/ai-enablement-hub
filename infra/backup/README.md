# Database backup & restore jobs

Two Azure Container Apps Jobs, one image, in RG `imaginemore-playground`:

| Job | Trigger | Entrypoint | What it does |
|---|---|---|---|
| `ai-enablement-hub-db-backup` | schedule `30 2 * * *` (UTC) | `backup.py` | dump → verify → upload to `db-backups` → prune >30 d |
| `ai-enablement-hub-db-restore` | manual | `restore.py` | download a dump → `pg_restore` into a target database |

**Operations (freshness check, restoring, the drill) live in
[`docs/db-backup-restore.md`](../../docs/db-backup-restore.md).** This file is
only about the code and the image.

## Layout

- `dumpcheck.py` — pure logic (verification, blob naming, prune selection). Unit-tested.
- `backup.py` / `restore.py` — thin I/O shells around it; these two run in the container.
- `Dockerfile` — `postgres:18` + python3 + `azure-identity`/`azure-storage-blob`.

These run *locally* via `uv run` (no Postgres client needed, PEP 723 deps inline):

- `verify_restore.py` — compares a restored database to live, table by table.
- `drill_db.py` — `--check` / `--create` / `--drop` the scratch database.
- `copy_lesson.py` — copy one lesson's `content_blocks` restored → live (dry run by default).

Deliberately separate from the app image: an app deploy can't change the
backup's `pg_dump`, and a backup change can't break the app build.

## Tests

```powershell
uv run --no-project --with pytest pytest infra/backup/test_dumpcheck.py -v
```

## Rebuild and roll the jobs (after changing any .py here)

```powershell
$env:PYTHONIOENCODING='utf-8'
$az  = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'
$tag = "ai-enablement-hub-db-backup:" + (Get-Date -Format 'yyyyMMdd-HHmmss')
& $az acr build --registry ca530fc7463eacr --image $tag --platform linux/amd64 `
    --file infra/backup/Dockerfile infra/backup
& $az containerapp job update -n ai-enablement-hub-db-backup  -g imaginemore-playground --image "ca530fc7463eacr.azurecr.io/$tag"
& $az containerapp job update -n ai-enablement-hub-db-restore -g imaginemore-playground --image "ca530fc7463eacr.azurecr.io/$tag"
```

Both jobs always run the same tag — roll them together.
