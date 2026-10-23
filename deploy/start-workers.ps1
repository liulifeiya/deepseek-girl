# Start keepalive / guard / watchdog workers (one process each).
param([string]$Which = 'all')
. "$PSScriptRoot\env.ps1"
$node = 'C:\Program Files\nodejs\node.exe'

$jobs = @{
  guard     = @{ script = 'guard.mjs';     log = 'guard.log' }
  keepalive = @{ script = 'keepalive.mjs'; log = 'keepalive.log' }
  watchdog  = @{ script = 'watchdog.mjs';  log = 'watchdog.log' }
}

foreach ($name in $jobs.Keys) {
  if ($Which -ne 'all' -and $Which -ne $name) { continue }
  $j = $jobs[$name]
  Start-Process -FilePath $node -ArgumentList (Join-Path $PSScriptRoot $j.script) `
    -WorkingDirectory $PSScriptRoot -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $PSScriptRoot ($j.log + '.out')) `
    -RedirectStandardError  (Join-Path $PSScriptRoot ($j.log + '.err'))
}
