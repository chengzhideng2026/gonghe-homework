$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python agent.py
exit $LASTEXITCODE
