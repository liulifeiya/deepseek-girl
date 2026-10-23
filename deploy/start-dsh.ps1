# Start the bot's DSH web backend (profile: qq, port 3081).
. "$PSScriptRoot\env.ps1"

# Load DEEPSEEK_API_KEY and friends from dsh-web.env (same role as systemd EnvironmentFile).
$envFile = 'C:\Users\Administrator\.dsh-qq\dsh-web.env'
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
      Set-Item -Path "env:$($matches[1])" -Value $matches[2].Trim()
    }
  }
}

Set-Location 'C:\Users\Administrator'
$log = Join-Path $PSScriptRoot 'dsh-web.log'
& dsh --profile qq --port 3081 --no-open *>> $log
