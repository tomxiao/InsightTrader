$ErrorActionPreference = 'Stop'

$workspaceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$logsDir = Join-Path $workspaceRoot 'logs'
$pythonExe = Join-Path $workspaceRoot '.venv\Scripts\python.exe'
$backendPidFile = Join-Path $logsDir 'ta_service.dev.pid'

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

if (-not (Test-Path -LiteralPath $pythonExe)) {
  throw "Python not found: $pythonExe"
}

New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

if (Test-ManagedProcessRunning -PidFile $backendPidFile) {
  throw "Backend is already running. Stop it first with .\stop-dev.ps1"
}

$currentPid = $PID
Set-Content -LiteralPath $backendPidFile -Value $currentPid

try {
  Write-Host "Starting backend in this terminal..."
  Write-Host "Backend URL: http://localhost:8100"
  Write-Host "Backend Docs URL: http://localhost:8100/docs"
  & $pythonExe -m ta_service.main
}
finally {
  Remove-Item -LiteralPath $backendPidFile -Force -ErrorAction SilentlyContinue
}
