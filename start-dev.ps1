$ErrorActionPreference = 'Stop'

$workspaceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pwshExe = (Get-Command pwsh).Source

function Test-ManagedProcessRunning {
  param(
    [string]$PidFile
  )

  if (-not (Test-Path -LiteralPath $PidFile)) {
    return $false
  }

  $pidValue = (Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
  if (-not $pidValue) {
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    return $false
  }

  $process = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
  if (-not $process) {
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    return $false
  }

  return $true
}

$backendPidFile = Join-Path (Join-Path $workspaceRoot 'logs') 'ta_service.dev.pid'
$frontendPidFile = Join-Path (Join-Path $workspaceRoot 'logs') 'mobile_h5.dev.pid'
$backendScript = Join-Path $workspaceRoot 'start-backend.ps1'
$frontendScript = Join-Path $workspaceRoot 'start-frontend.ps1'

if (Test-ManagedProcessRunning -PidFile $backendPidFile) {
  throw "Backend is already running. Stop it first with .\stop-dev.ps1"
}

if (Test-ManagedProcessRunning -PidFile $frontendPidFile) {
  throw "Frontend is already running. Stop it first with .\stop-dev.ps1"
}

if (-not (Test-Path -LiteralPath $backendScript)) {
  throw "Backend starter not found: $backendScript"
}

if (-not (Test-Path -LiteralPath $frontendScript)) {
  throw "Frontend starter not found: $frontendScript"
}

Start-Process `
  -FilePath $pwshExe `
  -ArgumentList @('-NoExit', '-ExecutionPolicy', 'Bypass', '-File', $backendScript) `
  -WorkingDirectory $workspaceRoot | Out-Null

Start-Process `
  -FilePath $pwshExe `
  -ArgumentList @('-NoExit', '-ExecutionPolicy', 'Bypass', '-File', $frontendScript) `
  -WorkingDirectory $workspaceRoot | Out-Null

Write-Host "InsightTrader launchers opened in two terminal windows."
Write-Host "Backend terminal : start-backend.ps1"
Write-Host "Frontend terminal: start-frontend.ps1"
Write-Host "Frontend URL     : http://localhost:3100"
Write-Host "Backend URL      : http://localhost:8100"
Write-Host "Backend Docs URL : http://localhost:8100/docs"
