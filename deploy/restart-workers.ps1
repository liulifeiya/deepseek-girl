# Restart the three keepalive workers (guard / keepalive / watchdog).
# Kept in its own file so a caller's command line never contains the match
# pattern or the script paths (which would make the caller kill itself).
$ErrorActionPreference = 'SilentlyContinue'

Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
  Where-Object { $_.CommandLine -match 'qq-dsh-bot\\(guard|keepalive|watchdog)\.mjs' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Start-Sleep -Seconds 2
schtasks /Run /TN 'DshBot-Workers' | Out-Null
Start-Sleep -Seconds 6
Get-Content (Join-Path $PSScriptRoot 'guard.log') -Tail 2
