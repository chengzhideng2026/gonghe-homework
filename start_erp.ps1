$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Join-Path $PSScriptRoot 'erpnext')
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$dockerPath = if ($dockerCommand) { $dockerCommand.Source } else { 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' }
& $dockerPath compose config --quiet
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $dockerPath compose up -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $dockerPath compose logs --tail 40 restore-site
Write-Host 'Wait for Restore complete., then open http://localhost:8080'
