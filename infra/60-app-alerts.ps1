# One-time (idempotent) create of the app health alerts - way-of-working 2.9, issue #48.
#
# Three metric alerts on the ai-enablement-hub Container App, all mailing the existing
# `ai-hub-backup-alerts` action group (Matthias + Aaron):
#   ai-hub-app-5xx       Sev2  >= 3 responses with status 5xx in 15 min
#   ai-hub-app-restarts  Sev2  any container restart in 15 min (crash, OOM kill)
#   ai-hub-app-down      Sev1  no running replica for 15 min (min=max=1, so 0 = outage)
# Unlike the backup JOB (whose Executions metric reads 0 - see docs/db-backup-restore.md), the
# APP's metrics are real: Requests/statusCodeCategory, RestartCount and Replicas all report.
# Traffic is ~200 requests/day, so the 5xx rule counts errors instead of using a rate.
#
# Azure-MUTATING: run only when a human has approved it. Re-running is safe: an existing rule
# is left untouched (delete it in the portal first to change it). Traps this follows
# (docs/superpowers/lessons.md): old az off PATH, PYTHONIOENCODING, never redirect az's stderr
# under PS 5.1, no probe variable that shadows a constant, ASCII only.

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$AZ = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'
$RESOURCE_GROUP = 'imaginemore-playground'
$APP_NAME = 'ai-enablement-hub'
$ACTION_GROUP = 'ai-hub-backup-alerts'
$RUNBOOK = 'Runbook: docs/app-alerts.md in the ai-enablement-hub repo'

$appResourceId = & $AZ containerapp show -n $APP_NAME -g $RESOURCE_GROUP --query id -o tsv
$actionGroupId = & $AZ monitor action-group show -n $ACTION_GROUP -g $RESOURCE_GROUP --query id -o tsv
if (-not $appResourceId -or -not $actionGroupId) { throw 'app or action group not found - nothing created' }

$rules = @(
    @{ Name = 'ai-hub-app-5xx'; Severity = 2
       Condition = 'total Requests >= 3 where statusCodeCategory includes 5xx'
       Description = "AI Enablement Hub returned 3+ server errors (5xx) in 15 minutes. $RUNBOOK" },
    @{ Name = 'ai-hub-app-restarts'; Severity = 2
       Condition = 'total RestartCount > 0'
       Description = "AI Enablement Hub container restarted (crash or out-of-memory). $RUNBOOK" },
    @{ Name = 'ai-hub-app-down'; Severity = 1
       Condition = 'max Replicas < 1'
       Description = "AI Enablement Hub has had no running replica for 15 minutes - the app is down. $RUNBOOK" }
)

# Plain name list, filtered in PowerShell: az.cmd hands its arguments to cmd.exe, which mangles a
# JMESPath filter like [?name=='x'] ("-o was unexpected at this time", lessons.md 2026-09-24).
$existingRuleNames = @(& $AZ monitor metrics alert list -g $RESOURCE_GROUP --query '[].name' -o tsv)

foreach ($rule in $rules) {
    if ($existingRuleNames -contains $rule.Name) {
        Write-Host "exists, left as is: $($rule.Name)"
        continue
    }
    if (-not $rule.Name) { throw 'empty rule name' }
    & $AZ monitor metrics alert create -n $rule.Name -g $RESOURCE_GROUP `
        --scopes $appResourceId --action $actionGroupId --severity $rule.Severity `
        --window-size 15m --evaluation-frequency 5m `
        --condition $rule.Condition --description $rule.Description `
        --query name -o tsv
    if ($LASTEXITCODE -ne 0) { throw "create failed: $($rule.Name)" }
    Write-Host "created: $($rule.Name)"
}

& $AZ monitor metrics alert list -g $RESOURCE_GROUP --query '[].{name:name, sev:severity, enabled:enabled}' -o table
