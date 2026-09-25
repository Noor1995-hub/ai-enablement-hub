# One-time (idempotent) create of the app health alerts - way-of-working 2.9, issue #48.
#
# Three metric alerts on the ai-enablement-hub Container App, all mailing the
# `ai-hub-app-alerts` action group (Matthias only - his call, 2026-09-25). The nightly-backup
# alerts keep their own `ai-hub-backup-alerts` group (Matthias + Aaron); this script never
# touches that group, it only moves app rules off it:
#   ai-hub-app-5xx       Sev2  >= 3 responses with status 5xx in 15 min
#   ai-hub-app-restarts  Sev2  any container restart in 15 min (crash, OOM kill)
#   ai-hub-app-down      Sev1  no running replica for 15 min (min=max=1, so 0 = outage)
# Unlike the backup JOB (whose Executions metric reads 0 - see docs/db-backup-restore.md), the
# APP's metrics are real: Requests/statusCodeCategory, RestartCount and Replicas all report.
# Traffic is ~200 requests/day, so the 5xx rule counts errors instead of using a rate.
#
# Azure-MUTATING: run only when a human has approved it. Re-running is safe: the action group is
# created only if missing, a missing rule is created, and an existing rule is left as is except
# that it is re-pointed from the old shared group to ai-hub-app-alerts (to change a condition,
# delete the rule in the portal first). Traps this follows
# (docs/superpowers/lessons.md): old az off PATH, PYTHONIOENCODING, never redirect az's stderr
# under PS 5.1, no probe variable that shadows a constant, ASCII only.

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$AZ = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'
$RESOURCE_GROUP = 'imaginemore-playground'
$APP_NAME = 'ai-enablement-hub'
$ACTION_GROUP = 'ai-hub-app-alerts'
$ACTION_GROUP_SHORT = 'hubapp'
$ALERT_EMAIL = 'matthias.danneel@delaware.pro'
$OLD_ACTION_GROUP = 'ai-hub-backup-alerts'
$RUNBOOK = 'Runbook: docs/app-alerts.md in the ai-enablement-hub repo'

$appResourceId = & $AZ containerapp show -n $APP_NAME -g $RESOURCE_GROUP --query id -o tsv
if (-not $appResourceId) { throw 'app not found - nothing created' }

$existingGroups = @(& $AZ monitor action-group list -g $RESOURCE_GROUP --query '[].name' -o tsv)
if ($existingGroups -notcontains $ACTION_GROUP) {
    & $AZ monitor action-group create -n $ACTION_GROUP -g $RESOURCE_GROUP `
        --short-name $ACTION_GROUP_SHORT --action email matthias $ALERT_EMAIL --query name -o tsv
    if ($LASTEXITCODE -ne 0) { throw "action group create failed: $ACTION_GROUP" }
    Write-Host "created action group: $ACTION_GROUP ($ALERT_EMAIL)"
}
$actionGroupId = & $AZ monitor action-group show -n $ACTION_GROUP -g $RESOURCE_GROUP --query id -o tsv
if (-not $actionGroupId) { throw 'action group not found after create - nothing changed' }
$oldActionGroupId = $null
if ($existingGroups -contains $OLD_ACTION_GROUP) {
    $oldActionGroupId = & $AZ monitor action-group show -n $OLD_ACTION_GROUP -g $RESOURCE_GROUP --query id -o tsv
}

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
        # Compare ids case-insensitively: Azure does not keep resource-id casing stable.
        $ruleGroups = @(& $AZ monitor metrics alert show -n $rule.Name -g $RESOURCE_GROUP `
            --query 'actions[].actionGroupId' -o tsv)
        $onNewGroup = @($ruleGroups | Where-Object { $_ -ieq $actionGroupId }).Count -gt 0
        $onOldGroup = $oldActionGroupId -and (@($ruleGroups | Where-Object { $_ -ieq $oldActionGroupId }).Count -gt 0)
        if ($onNewGroup -and -not $onOldGroup) {
            Write-Host "exists, left as is: $($rule.Name)"
            continue
        }
        $updateArgs = @('monitor', 'metrics', 'alert', 'update', '-n', $rule.Name, '-g', $RESOURCE_GROUP)
        if (-not $onNewGroup) { $updateArgs += @('--add-action', $actionGroupId) }
        if ($onOldGroup) { $updateArgs += @('--remove-action', $oldActionGroupId) }
        & $AZ @updateArgs --query name -o tsv
        if ($LASTEXITCODE -ne 0) { throw "re-point failed: $($rule.Name)" }
        Write-Host "re-pointed to $($ACTION_GROUP): $($rule.Name)"
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
& $AZ monitor action-group show -n $ACTION_GROUP -g $RESOURCE_GROUP --query 'emailReceivers[].emailAddress' -o tsv
