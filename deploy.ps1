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
# az streams the remote build log; Vite prints unicode (checkmarks) that crashes
# the CLI under the default cp1252 console encoding.
$env:PYTHONIOENCODING = "utf-8"
$az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
$image = "ai-enablement-hub:$Tag"

& $az account set --subscription e2b785b0-d93d-4c19-9537-4f752f759cb1

& $az acr build --registry ca530fc7463eacr --image $image --platform linux/amd64 --file (Join-Path $PSScriptRoot "Dockerfile") $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw "acr build failed" }

if ($BuildOnly) {
    Write-Host "Image pushed: ca530fc7463eacr.azurecr.io/$image (app not updated)"
    return
}

& $az containerapp update -n ai-enablement-hub -g imaginemore-playground --image "ca530fc7463eacr.azurecr.io/$image"
if ($LASTEXITCODE -ne 0) { throw "containerapp update failed" }

Write-Host "Deployed ca530fc7463eacr.azurecr.io/$image"
Write-Host "URL: https://ai-enablement-hub.kindcoast-3b1fe056.swedencentral.azurecontainerapps.io"
