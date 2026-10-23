# Restart the bot's DSH web process (used by the daily-restart task).
. "$PSScriptRoot\env.ps1"

# Only match the real dsh process: bin.js + profile qq (not the tool runner).
Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
  Where-Object { $_.CommandLine -like '*dsh/lib/bin.js*' -and $_.CommandLine -like '*--profile qq*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Start-Sleep -Seconds 3
Start-Process -FilePath 'powershell.exe' `
  -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',(Join-Path $PSScriptRoot 'start-dsh.ps1')