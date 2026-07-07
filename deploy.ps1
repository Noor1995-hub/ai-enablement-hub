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
