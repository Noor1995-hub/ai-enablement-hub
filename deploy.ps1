# Build the image in ACR (no local Docker needed) and roll the container app to it.
# Usage: .\deploy.ps1            (tag = timestamp)
#        .\deploy.ps1 -Tag v2   (explicit tag)
#        .\deploy.ps1 -BuildOnly (push the image but don't touch the app — used
#                                 before the one-time infra\deploy-initial.ps1)
param(
    [string]$Tag = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [switch]$BuildOnly
)
$ErrorActionPreference = "Stop"
# --- Interim guard (Tier 0, 2026-09-22): ship only the pushed origin/main. -------------------
# `az acr build` uploads this directory as-is, so an uncommitted edit or an un-pushed commit
# would go live untraceably (it has happened: 2026-07-22). Refuse both. Retired when the
# CI-driven deploy lands (Tier 1); no -Force switch on purpose.
$env:GIT_TERMINAL_PROMPT = "0"
& git -C $PSScriptRoot fetch origin --quiet
if ($LASTEXITCODE -ne 0) { throw "deploy guard: 'git fetch origin' failed - are you online and authenticated?" }
$dirty = & git -C $PSScriptRoot status --porcelain
if ($dirty) {
    throw "deploy guard: working tree is dirty - commit or stash first. deploy.ps1 ships the directory as-is.`n$($dirty -join "`n")"
}
$head = & git -C $PSScriptRoot rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($head)) {
    throw "deploy guard: could not resolve HEAD - is $PSScriptRoot a git repository?"
}
$originMain = & git -C $PSScriptRoot rev-parse origin/main
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($originMain)) {
    throw "deploy guard: could not resolve origin/main - does this clone have a full refspec for origin (not a single-branch/narrow clone)?"
}
$head = $head.Trim()
$originMain = $originMain.Trim()
if ($head -ne $originMain) {
    throw "deploy guard: HEAD ($($head.Substring(0,7))) is not origin/main ($($originMain.Substring(0,7))). Merge the PR, then: git switch main; git pull; and deploy from there."
}
$subject = (& git -C $PSScriptRoot log -1 --format=%s).Trim()
Write-Host "deploy guard: shipping $($head.Substring(0,7)) - $subject" -ForegroundColor Green
# ------------------------------------------------------------------------------------------
$env:PYTHONIOENCODING = "utf-8"
$az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
$registry = "ca530fc7463eacr"
$image = "ai-enablement-hub:$Tag"

& $az account set --subscription e2b785b0-d93d-4c19-9537-4f752f759cb1

# --no-wait + poll instead of letting az stream the remote build log: its local
# streamer can crash (colorama/cp1252) when Vite prints unicode checkmarks, and
# PYTHONIOENCODING=utf-8 doesn't reliably prevent that in a non-interactive
# session (confirmed 2026-07-07 — the remote build itself succeeds either way,
# only the local log display was crashing). Don't redirect its stderr (no 2>&1):
# under PowerShell 5.1 + $ErrorActionPreference=Stop that turns az's harmless
# stderr WARNING lines into terminating NativeCommandErrors, even on exit 0.
& $az acr build --no-wait --registry $registry --image $image --platform linux/amd64 --file (Join-Path $PSScriptRoot "Dockerfile") $PSScriptRoot | Out-Null
if ($LASTEXITCODE -ne 0) { throw "acr build queue failed" }

$run = & $az acr task list-runs --registry $registry --top 1 -o json | ConvertFrom-Json
if (-not $run) { throw "could not find the just-queued ACR build run" }
$runId = $run.runId
Write-Host "Queued ACR build $runId, waiting for it to finish..."

for ($i = 0; $i -lt 60 -and $run.status -in @("Queued", "Started", "Running"); $i++) {
    Start-Sleep -Seconds 10
    $run = & $az acr task list-runs --registry $registry --query "[?runId=='$runId'] | [0]" -o json | ConvertFrom-Json
}
if ($run.status -ne "Succeeded") { throw "ACR build $runId finished with status $($run.status)" }
Write-Host "ACR build $runId succeeded."

if ($BuildOnly) {
    Write-Host "Image pushed: $registry.azurecr.io/$image (app not updated)"
    return
}

& $az containerapp update -n ai-enablement-hub -g imaginemore-playground --image "$registry.azurecr.io/$image"
if ($LASTEXITCODE -ne 0) { throw "containerapp update failed" }

Write-Host "Deployed $registry.azurecr.io/$image"
Write-Host "URL: https://ai-enablement-hub.kindcoast-3b1fe056.swedencentral.azurecontainerapps.io"
