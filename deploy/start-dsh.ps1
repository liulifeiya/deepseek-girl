# Start the bot's DSH web backend (profile: qq, port 3081).
. "$PSScriptRoot\env.ps1"

# 幂等：端口已在监听就说明后端活着（自动登录 + 手动 RDP 会触发两次）
$listening = Get-NetTCPConnection -LocalPort 3081 -State Listen -ErrorAction SilentlyContinue
if ($listening) {
  Write-Host 'dsh backend already listening on 3081, skip.'
  exit 0
}

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
