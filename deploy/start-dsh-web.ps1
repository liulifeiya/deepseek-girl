# Start the DSH Web GUI (port 3080) for interactive chat.
# Idempotent: skips when 3080 is already listening.

$ErrorActionPreference = 'Stop'
$log = 'C:\Users\Administrator\.dsh\logs\dsh-web-console.log'

$listening = Get-NetTCPConnection -LocalPort 3080 -State Listen -ErrorAction SilentlyContinue
if ($listening) {
  Write-Host 'DSH web GUI already listening on 3080, skip.'
  exit 0
}

New-Item -ItemType Directory -Force -Path (Split-Path $log -Parent) | Out-Null

# Keep the user's normal PATH (npm global contains dsh.cmd)
$env:Path = 'C:\Program Files\nodejs;C:\Users\Administrator\AppData\Roaming\npm;' + $env:Path

Set-Location 'C:\Users\Administrator'
& 'C:\Users\Administrator\AppData\Roaming\npm\dsh.cmd' web --host 127.0.0.1 --port 3080 --no-open *>> $log
