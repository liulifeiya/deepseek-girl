# Restart only the bot backend (profile qq) and wait until 3081 is listening.
# Kept in its own file so a caller's command line never contains the process
# matching strings (which would make the caller kill itself).
$ErrorActionPreference = 'SilentlyContinue'

Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
  Where-Object { $_.CommandLine -like '*dsh/lib/bin.js*' -and $_.CommandLine -like '*--profile qq*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Start-Sleep -Seconds 4
schtasks /Run /TN 'DshBot-DSH' | Out-Null

for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 2
  $c = Get-NetTCPConnection -LocalPort 3081 -State Listen -ErrorAction SilentlyContinue
  if ($c) { Write-Host "3081 listening (pid=$($c[0].OwningProcess))"; exit 0 }
}
Write-Host '3081 not listening yet'
exit 1
