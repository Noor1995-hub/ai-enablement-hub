# App health alerts — runbook

Three Azure Monitor metric alerts watch the `ai-enablement-hub` Container App and mail the
`ai-hub-backup-alerts` action group (Matthias + Aaron). Created by `infra/60-app-alerts.ps1`
(idempotent; 2026-09-24, issue #48). Each alert also mails when it resolves. The nightly-backup
alerts are separate: `docs/db-backup-restore.md`.

| Alert | Fires when | Severity |
|---|---|---|
| `ai-hub-app-down` | no running replica for 15 min — the app is down | Sev 1 |
| `ai-hub-app-5xx` | 3 or more server errors (5xx) in 15 min | Sev 2 |
| `ai-hub-app-restarts` | the container restarted (crash, out-of-memory kill) | Sev 2 |

Normal traffic is ~200 requests a day with no 5xx and no restarts (measured 2026-09-17 → 24), so
any of these firing is worth a look.

## First checks (all read-only)

1. **Is it up, and which build?** `curl https://ai-enablement-hub.kindcoast-3b1fe056.swedencentral.azurecontainerapps.io/api/health`
   → `status` and `build_sha`. A just-pressed Deploy is the usual suspect: compare with the
   latest run under Actions → Deploy.
2. **Revision state:** `az containerapp revision list -n ai-enablement-hub -g imaginemore-playground --query "[].{name:name, active:properties.active, health:properties.healthState, running:properties.runningState, replicas:properties.replicas}" -o table`
   (the old az CLI is off PATH: `C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`, with
   `PYTHONIOENCODING=utf-8`).
3. **App logs:** the `az rest` Log Analytics recipe in `docs/db-backup-restore.md` → "Reading a
   job's log output", with the filter changed to the app:
   `ContainerAppConsoleLogs_CL | where ContainerAppName_s == 'ai-enablement-hub' | where TimeGenerated > ago(1h) | order by TimeGenerated desc | take 100 | project TimeGenerated, Stream_s, Log_s`.
   Python tracebacks are on `stderr`.

## What usually fixes it

- **After a deploy:** roll back — run Deploy again with `image_sha` = the previous commit on
  `main` (CONTRIBUTING.md → Deploying). Migrations are expand-first, so the old image runs on the
  new schema.
- **Out-of-memory restarts:** the app has 1 GiB; look for a request that loads something large.
  Scaling out is not an option (min = max = 1 replica is a design constraint, CLAUDE.md).
- **5xx from the AI features only:** the Anthropic API may be down or rate-limiting; the
  backend treats those as transient. Check status.anthropic.com before digging.

Any Azure-changing step (restart, scale, secret) is a deliberate operator action — agents ask
first.

## Changing or removing an alert

The script leaves an existing rule untouched. Change thresholds in the portal (Monitor → Alerts →
Alert rules) or delete the rule there and re-run the script after editing it — and update this
page in the same PR.
