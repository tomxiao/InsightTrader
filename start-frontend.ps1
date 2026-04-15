$ErrorActionPreference = 'Stop'

$workspaceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendRoot = Join-Path $workspaceRoot 'mobile_h5'
$logsDir = Join-Path $workspaceRoot 'logs'
$viteCmd = Join-Path $workspaceRoot 'mobile_h5\node_modules\.bin\vite.cmd'
$frontendPidFile = Join-Path $logsDir 'mobile_h5.dev.pid'

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

if (-not (Test-Path -LiteralPath $viteCmd)) {
  throw "vite.cmd not found: $viteCmd. Run npm install in mobile_h5 first."
}

New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

if (Test-ManagedProcessRunning -PidFile $frontendPidFile) {
  throw "Frontend is already running. Stop it first with .\stop-dev.ps1"
}

$currentPid = $PID
Set-Content -LiteralPath $frontendPidFile -Value $currentPid

try {
  Write-Host "Starting frontend in this terminal..."
  Write-Host "Frontend URL: http://localhost:3100"
  Set-Location -LiteralPath $frontendRoot
  & $viteCmd --host 0.0.0.0 --port 3100 --strictPort
}
finally {
  Remove-Item -LiteralPath $frontendPidFile -Force -ErrorAction SilentlyContinue
}
