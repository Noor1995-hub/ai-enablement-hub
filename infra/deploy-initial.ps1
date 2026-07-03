# One-time creation of the ai-enablement-hub Container App.
# Prereqs: image already pushed (deploy.ps1 or `az acr build`), backend\.env present.
# Redeploys afterwards use ..\deploy.ps1 — never this script (it would need the
# secrets again; `az containerapp update` preserves them).
param(
    [Parameter(Mandatory = $true)][string]$Tag
)
$ErrorActionPreference = "Stop"
$az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
$root = Split-Path $PSScriptRoot -Parent

& $az account set --subscription e2b785b0-d93d-4c19-9537-4f752f759cb1

$acrPwd = (& $az acr credential show -n ca530fc7463eacr --query "passwords[0].value" -o tsv)
if (-not $acrPwd) { throw "could not read ACR credential" }

# DB secrets come from backend\.env (the same live Azure PG credentials dev uses)
$envLines = Get-Content (Join-Path $root "backend\.env")
$dbPwd = ($envLines | Where-Object { $_ -match "^DATABASE__PASSWORD=" }) -replace "^DATABASE__PASSWORD=", ""
$alembicUrl = ($envLines | Where-Object { $_ -match "^ALEMBIC_DATABASE_URL=" }) -replace "^ALEMBIC_DATABASE_URL=", ""
if (-not $dbPwd -or -not $alembicUrl) { throw "backend\.env is missing DATABASE__PASSWORD or ALEMBIC_DATABASE_URL" }

# Fresh prod JWT secret — deliberately NOT the dev one (rotating it later kills
# all sessions but breaks nothing else).
$bytes = New-Object byte[] 48
[Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes($bytes)
$jwt = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')

$yaml = [IO.File]::ReadAllText((Join-Path $PSScriptRoot "containerapp.yaml"), [Text.UTF8Encoding]::new($false))
$yaml = $yaml.Replace("__ACR_PASSWORD__", $acrPwd)
$yaml = $yaml.Replace("__DB_PASSWORD__", $dbPwd)
$yaml = $yaml.Replace("__ALEMBIC_DATABASE_URL__", $alembicUrl)
$yaml = $yaml.Replace("__JWT_SECRET__", $jwt)
$yaml = $yaml.Replace("__TAG__", $Tag)

# az parses the yaml with the system codepage on Windows - keep it pure ASCII.
$nonAscii = ($yaml.ToCharArray() | Where-Object { [int]$_ -gt 127 }).Count
if ($nonAscii -gt 0) { throw "yaml contains $nonAscii non-ASCII character(s) after substitution - az would misparse it" }

# The temp file briefly holds secrets - removed in finally.
$tmp = Join-Path $env:TEMP "ca-ai-enablement-hub.yaml"
try {
    [IO.File]::WriteAllText($tmp, $yaml, [Text.ASCIIEncoding]::new())
    & $az containerapp create -n ai-enablement-hub -g imaginemore-playground --yaml $tmp
    if ($LASTEXITCODE -ne 0) { throw "containerapp create failed" }
}
finally {
    Remove-Item $tmp -Force -Confirm:$false -ErrorAction SilentlyContinue
}

Write-Host "Created. URL: https://ai-enablement-hub.kindcoast-3b1fe056.swedencentral.azurecontainerapps.io"
