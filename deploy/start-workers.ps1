# Start keepalive / guard / watchdog workers (one process each, idempotent).
param([string]$Which = 'all')
. "$PSScriptRoot\env.ps1"
$node = 'C:\Program Files\nodejs\node.exe'

$jobs = @{
  guard     = @{ script = 'guard.mjs';     log = 'guard.log' }
  keepalive = @{ script = 'keepalive.mjs'; log = 'keepalive.log' }
  watchdog  = @{ script = 'watchdog.mjs';  log = 'watchdog.log' }
}

# 已运行的脚本不再重复拉起（自动登录 + 手动 RDP 会触发两次）
$running = Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
  Where-Object { $_.CommandLine -match 'qq-dsh-bot.(guard|keepalive|watchdog)\.mjs' } |
  ForEach-Object {
    if ($_.CommandLine -match 'guard\.mjs') { 'guard' }
    elseif ($_.CommandLine -match 'keepalive\.mjs') { 'keepalive' }
    elseif ($_.CommandLine -match 'watchdog\.mjs') { 'watchdog' }
  }

foreach ($name in $jobs.Keys) {
  if ($Which -ne 'all' -and $Which -ne $name) { continue }
  if ($running -contains $name) {
    Write-Host "$name already running, skip."
    continue
  }
  $j = $jobs[$name]
  Start-Process -FilePath $node -ArgumentList (Join-Path $PSScriptRoot $j.script) `
    -WorkingDirectory $PSScriptRoot -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $PSScriptRoot ($j.log + '.out')) `
    -RedirectStandardError  (Join-Path $PSScriptRoot ($j.log + '.err'))
}
