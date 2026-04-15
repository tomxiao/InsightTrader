$ErrorActionPreference = 'Stop'

$workspaceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$logsDir = Join-Path $workspaceRoot 'logs'

$backendPidFile = Join-Path $logsDir 'ta_service.dev.pid'
$frontendPidFile = Join-Path $logsDir 'mobile_h5.dev.pid'

function Stop-ProcessTree {
  param(
    [int]$ProcessId
  )

  $childProcesses = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
  foreach ($childProcess in $childProcesses) {
    Stop-ProcessTree -ProcessId $childProcess.ProcessId
  }

  $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
  if ($process) {
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
  }
}

function Stop-ManagedProcess {
  param(
    [string]$Name,
    [string]$PidFile
  )

  if (-not (Test-Path -LiteralPath $PidFile)) {
    Write-Host "$Name is not running."
    return
  }

  $pidValue = (Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
  if (-not $pidValue) {
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "$Name pid file was empty and has been cleaned up."
    return
  }

  $process = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
  if ($process) {
    Stop-ProcessTree -ProcessId $process.Id
    Write-Host "$Name stopped (PID $($process.Id))."
  } else {
    Write-Host "$Name was not running, cleaned up stale pid file."
  }

  Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}

Stop-ManagedProcess -Name 'Backend' -PidFile $backendPidFile
Stop-ManagedProcess -Name 'Frontend' -PidFile $frontendPidFile
