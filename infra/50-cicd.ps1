#requires -Version 5.1
# infra/50-cicd.ps1 - one-time Azure setup for the GitHub Actions "Deploy" workflow.
# Idempotent: re-running creates only what is missing. Run as an RG Owner (Matthias) with the
# controller watching; every mutating command below is echoed before it runs.
#
# Creates:  identity ai-hub-cicd; federated credential github-ai-hub-main (subject bound to
#           refs/heads/main of DLW-INT-BTA-BELUX/ai-enablement-hub); roles AcrPush (registry),
#           Contributor (app), Contributor (migrate job); the Container Apps Job
#           ai-enablement-hub-migrate (manual trigger, app image, alembic-database-url secret).
# Then prints the three `gh variable set` commands for the repo.
param(
    [string]$Image = ""   # full image ref for the job's first creation; default = the app's current image
)
$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$az = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'

$SUB      = 'e2b785b0-d93d-4c19-9537-4f752f759cb1'
$RG       = 'imaginemore-playground'
$CAE      = 'imaginemore-playground-cae'
$IDENTITY = 'ai-hub-cicd'
$FIC      = 'github-ai-hub-main'
$REPO     = 'DLW-INT-BTA-BELUX/ai-enablement-hub'
$ACR      = 'ca530fc7463eacr'
$APP      = 'ai-enablement-hub'
$JOB      = 'ai-enablement-hub-migrate'

# Redacts the value following any --registry-password / --secrets flag before it is ever
# written to the console or into a thrown error message; $acrPwd/$alembicUrl themselves are
# never printed anywhere else in this script either.
function Get-RedactedArgs { param([string[]]$AzArgs)
    $out = New-Object System.Collections.Generic.List[string]
    $redactNext = $false
    foreach ($tok in $AzArgs) {
        if ($redactNext) { $out.Add('***'); $redactNext = $false }
        else { $out.Add($tok) }
        if ($tok -eq '--registry-password' -or $tok -eq '--secrets') { $redactNext = $true }
    }
    return ($out -join ' ')
}
# Note: --registry-password is briefly visible in the process list while az runs (accepted,
# same tradeoff as the nightly backup job).
function Invoke-Az { param([string[]]$AzArgs)
    $display = Get-RedactedArgs $AzArgs
    Write-Host ("az " + $display) -ForegroundColor DarkGray
    & $az @AzArgs
    if ($LASTEXITCODE -ne 0) { throw "az failed: $display" }
}

Invoke-Az @('account','set','--subscription',$SUB) | Out-Null
$acct = & $az account show -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $acct) { throw 'az account show failed - run az login first' }
Write-Host ("Signed in as {0} on {1}" -f $acct.user.name, $acct.name) -ForegroundColor Green

Write-Host '== 1/5 identity ==' -ForegroundColor Cyan
# A non-erroring list-and-filter probe: `identity show` on a missing resource would write to
# stderr and, under $ErrorActionPreference='Stop' in PS 5.1, that can surface as a terminating
# NativeCommandError instead of a clean not-found - `identity list` always exits 0.
$id = & $az identity list -g $RG --query "[?name=='$IDENTITY'] | [0]" -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'identity list probe failed' }
if (-not $id) { $id = Invoke-Az @('identity','create','-g',$RG,'-n',$IDENTITY,'-o','json') | ConvertFrom-Json; Write-Host 'created' } else { Write-Host 'exists' }
$CLIENT_ID = $id.clientId; $PRINCIPAL_ID = $id.principalId; $TENANT_ID = $id.tenantId

Write-Host '== 2/5 federated credential ==' -ForegroundColor Cyan
$fics = & $az identity federated-credential list -g $RG --identity-name $IDENTITY -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'federated-credential list failed' }
if (-not ($fics | Where-Object { $_.name -eq $FIC })) {
    Invoke-Az @('identity','federated-credential','create','--name',$FIC,'--identity-name',$IDENTITY,'-g',$RG,
        '--issuer','https://token.actions.githubusercontent.com',
        '--subject',"repo:$REPO`:ref:refs/heads/main",
        '--audiences','api://AzureADTokenExchange') | Out-Null
    Write-Host 'created'
} else { Write-Host 'exists' }

Write-Host '== 3/5 roles ==' -ForegroundColor Cyan
$acrId = & $az acr show -n $ACR --query id -o tsv
if ($LASTEXITCODE -ne 0 -or -not $acrId) { throw 'could not resolve the ACR resource id' }
$appId = & $az containerapp show -g $RG -n $APP --query id -o tsv
if ($LASTEXITCODE -ne 0 -or -not $appId) { throw 'could not resolve the app resource id' }
function Ensure-Role { param([string]$Role,[string]$Scope)
    $have = & $az role assignment list --assignee $PRINCIPAL_ID --scope $Scope --query "[?roleDefinitionName=='$Role'] | length(@)" -o tsv
    if ($LASTEXITCODE -ne 0 -or $have -notmatch '^\d+$') { throw "role probe failed for $Role on $Scope" }
    if ($have -eq '0') { Invoke-Az @('role','assignment','create','--assignee-object-id',$PRINCIPAL_ID,'--assignee-principal-type','ServicePrincipal','--role',$Role,'--scope',$Scope) | Out-Null; Write-Host "  $Role on $(Split-Path $Scope -Leaf): created" } else { Write-Host "  $Role on $(Split-Path $Scope -Leaf): exists" }
}
Ensure-Role 'AcrPush' $acrId
# AcrDelete: the Deploy workflow untags the image of a FAILED migration so it can never become a rollback target.
Ensure-Role 'AcrDelete' $acrId
Ensure-Role 'Contributor' $appId

Write-Host '== 4/5 migration job ==' -ForegroundColor Cyan
# Same non-erroring list-and-filter probe as section 1/5 (`job show` on a missing job would
# otherwise risk throwing after the identity, credential and two roles above already exist).
# NB: the probe variable must NOT be called $job - PowerShell variable names are
# case-insensitive, so $job and $JOB are the SAME variable and an absent job would blank
# the job NAME, making the create below run with an empty -n (observed 2026-09-23).
$existingJob = & $az containerapp job list -g $RG --query "[?name=='$JOB'] | [0]" -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'containerapp job list probe failed' }
if (-not $JOB) { throw 'internal: the job name variable was clobbered' }
if (-not $existingJob) {
    if (-not $Image) {
        $Image = & $az containerapp show -g $RG -n $APP --query 'properties.template.containers[0].image' -o tsv
        if ($LASTEXITCODE -ne 0 -or -not $Image) { throw 'could not read the app image for the job' }
    }
    # If the ai_hub_owner password ever needs rotating, keep it free of spaces, double quotes
    # and `%`: PS 5.1's native-argument quoting mangles spaces/quotes when the value is passed
    # as an array element to `& $az ... @AzArgs` (as $alembicUrl is below), and `%` is separately
    # dangerous because $az is a .cmd wrapper - cmd.exe re-expands `%NAME%`/`%1` through it.
    $acrPwd     = & $az acr credential show -n $ACR --query 'passwords[0].value' -o tsv
    $alembicUrl = & $az containerapp secret show -g $RG -n $APP --secret-name alembic-database-url --query value -o tsv
    if (-not $acrPwd -or -not $alembicUrl) { throw 'could not read the ACR password or the app alembic-database-url secret' }
    if ($alembicUrl -match '[%\s"]') { throw 'alembic-database-url contains %, whitespace or a double quote: az.cmd (a batch wrapper) would corrupt it. Create the job secret with "az containerapp job secret set" from a shell that does not re-expand %, then re-run.' }
    Invoke-Az @('containerapp','job','create','-g',$RG,'-n',$JOB,'--environment',$CAE,
        '--trigger-type','Manual','--replica-timeout','600','--replica-retry-limit','0','--parallelism','1','--replica-completion-count','1',
        '--image',$Image,'--cpu','0.25','--memory','0.5Gi',
        '--registry-server',"$ACR.azurecr.io",'--registry-username',$ACR,'--registry-password',$acrPwd,
        '--secrets',"alembic-database-url=$alembicUrl",
        '--env-vars','ALEMBIC_DATABASE_URL=secretref:alembic-database-url',
        '--command','python','--args','migrate.py') | Out-Null
    Write-Host "created with image $Image"
} else { Write-Host 'exists' }
$jobId = & $az containerapp job show -g $RG -n $JOB --query id -o tsv
if ($LASTEXITCODE -ne 0 -or -not $jobId) { throw 'could not resolve the migrate job resource id' }
Ensure-Role 'Contributor' $jobId

Write-Host '== 5/5 GitHub repository variables (run these; not secrets, only identifiers) ==' -ForegroundColor Cyan
"gh variable set AZURE_CLIENT_ID       -R $REPO -b $CLIENT_ID"
"gh variable set AZURE_TENANT_ID       -R $REPO -b $TENANT_ID"
"gh variable set AZURE_SUBSCRIPTION_ID -R $REPO -b $SUB"
Write-Host 'Done. Role assignments can take a few minutes to propagate before the first Deploy run.' -ForegroundColor Green
