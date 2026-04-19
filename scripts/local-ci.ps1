Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  throw "Project virtualenv python not found: $venvPython"
}

function Invoke-Python {
  param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
  )

  & $venvPython @Args
}

function Invoke-Step {
  param(
    [Parameter(Mandatory = $true)][string]$Title,
    [Parameter(Mandatory = $true)][scriptblock]$Action
  )

  Write-Host ""
  Write-Host "==> $Title" -ForegroundColor Cyan
  & $Action
}

Invoke-Step -Title "Backend py_compile" -Action {
  Invoke-Python -m py_compile `
    ta_service/main.py `
    ta_service/app/factory.py `
    ta_service/api/routes/auth.py `
    ta_service/api/routes/admin_users.py `
    ta_service/api/routes/analysis.py `
    ta_service/api/routes/conversations.py `
    ta_service/api/routes/health.py `
    ta_service/models/message_types.py `
    tests/ta_service_api/conftest.py `
    tests/ta_service_api/test_auth_api.py `
    tests/ta_service_api/test_admin_users_api.py `
    tests/ta_service_api/test_analysis_api.py `
    tests/ta_service_api/test_conversations_api.py
}

Invoke-Step -Title "Backend app import" -Action {
  Invoke-Python -c "from ta_service.main import app; print('backend app import ok')"
}

Invoke-Step -Title "ta_service API contract tests" -Action {
  Invoke-Python -m pytest tests/ta_service_api -q
}

Invoke-Step -Title "Frontend type-check" -Action {
  npm --prefix mobile_h5 run type-check
}

Invoke-Step -Title "Frontend build" -Action {
  npm --prefix mobile_h5 run build
}

Write-Host ""
Write-Host "Local CI passed." -ForegroundColor Green
