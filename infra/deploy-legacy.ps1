# infra/deploy-legacy.ps1 - BREAK-GLASS ONLY. The normal deploy is the GitHub Actions "Deploy"
# button (.github/workflows/deploy.yml). Use this only if GitHub Actions is unavailable.
#
# It builds the WORKING DIRECTORY in ACR and rolls the app. The guard below still requires a
# clean tree at origin/main.
# It does NOT run migrations by itself. Break-glass sequence (PowerShell, repo root, tree clean at origin/main):
#   1. $t = Get-Date -Format yyyyMMdd-HHmmss;  .\infra\deploy-legacy.ps1 -BuildOnly -Tag $t      # build+push only
#   2. & 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd' containerapp job update -g imaginemore-playground -n ai-enablement-hub-migrate --image ca530fc7463eacr.azurecr.io/ai-enablement-hub:$t --command python --args migrate.py
#      & 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd' containerapp job start  -g imaginemore-playground -n ai-enablement-hub-migrate     # wait until the execution shows Succeeded
#   3. .\infra\deploy-legacy.ps1 -Tag $t                                                    # same tag: rolls the app (rebuilds the identical tree)
# It does NOT stamp APP__BUILD_SHA/TIME: /api/health keeps reporting the previous button deploy until the next one.
# Usage: .\infra\deploy-legacy.ps1            (tag = timestamp)
#        .\infra\deploy-legacy.ps1 -BuildOnly (push the image but don't touch the app)
param(
    [string]$Tag = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [switch]$BuildOnly
)
$ErrorActionPreference = "Stop"
# Repo root: this script lives in infra/, the guard and the ACR build context need the parent.
$repoRoot = Split-Path $PSScriptRoot -Parent
# --- Interim guard (Tier 0, 2026-09-22): ship only the pushed origin/main. -------------------
# `az acr build` uploads this directory as-is, so an uncommitted edit or an un-pushed commit
# would go live untraceably (it has happened: 2026-07-22). Refuse both. Retired when the
# CI-driven deploy lands (Tier 1); no -Force switch on purpose.
$env:GIT_TERMINAL_PROMPT = "0"
& git -C $repoRoot fetch origin --quiet
if ($LASTEXITCODE -ne 0) { throw "deploy guard: 'git fetch origin' failed - are you online and authenticated?" }
$dirty = & git -C $repoRoot status --porcelain
if ($dirty) {
    throw "deploy guard: working tree is dirty - commit or stash first. deploy-legacy.ps1 ships the directory as-is.`n$($dirty -join "`n")"
}
$head = & git -C $repoRoot rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($head)) {
    throw "deploy guard: could not resolve HEAD - is $repoRoot a git repository?"
}
$originMain = & git -C $repoRoot rev-parse origin/main
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($originMain)) {
    throw "deploy guard: could not resolve origin/main - does this clone have a full refspec for origin (not a single-branch/narrow clone)?"
}
$head = $head.Trim()
$originMain = $originMain.Trim()
if ($head -ne $originMain) {
    throw "deploy guard: HEAD ($($head.Substring(0,7))) is not origin/main ($($originMain.Substring(0,7))). Merge the PR, then: git switch main; git pull; and deploy from there."
}
$subject = (& git -C $repoRoot log -1 --format=%s).Trim()
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
& $az acr build --no-wait --registry $registry --image $image --platform linux/amd64 --file (Join-Path $repoRoot "Dockerfile") $repoRoot | Out-Null
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
