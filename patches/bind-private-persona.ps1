# bind-private-persona.ps1 — Windows 版 bind-private-persona.sh
#
# 作用（与 Linux 版一致）：
#   1. 把 dsh-persona-dafeiyu 切到 session 模式
#   2. 私聊管理员 2812108776 的所有会话固定人设 1（custom-mvi5y8pv 大肥鱼）
#   3. 群 877935643 的所有会话固定人设 3（custom-mvi6xf9s 鲸鱼娘）
#
# 用法：
#   powershell -NoProfile -ExecutionPolicy Bypass -File bind-private-persona.ps1
# 可选环境变量：BOT_DSH_PORT（默认 3081）、DSH_HOME、ADMIN_QQ

$ErrorActionPreference = 'SilentlyContinue'

$port    = if ($env:BOT_DSH_PORT) { $env:BOT_DSH_PORT } else { '3081' }
$dshHome = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh-qq' }
$admin   = if ($env:ADMIN_QQ) { $env:ADMIN_QQ } else { '2812108776' }
$group   = if ($env:GROUP_QQ) { $env:GROUP_QQ } else { '877935643' }

$api     = "http://127.0.0.1:$port/api/dsh-persona-dafeiyu"
$privatePid = 'custom-mvi5y8pv'
$groupPid   = 'custom-mvi6xf9s'

# 等 API 起来（最多约 60 秒）
for ($i = 0; $i -lt 30; $i++) {
  try { Invoke-RestMethod -Uri "$api/status" -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Seconds 2 }
}

Invoke-RestMethod -Method Post -Uri "$api/mutate" -ContentType 'application/json' `
  -Body '{"action":"set-mode","mode":"session"}' | Out-Null

$sessionsRoot = Join-Path $dshHome 'sessions'

function Bind-One([string]$sid, [string]$personaId) {
  $body = @{ action = 'set-session-persona'; sessionId = $sid; personaId = $personaId } | ConvertTo-Json -Compress
  try {
    Invoke-RestMethod -Method Post -Uri "$api/mutate" -ContentType 'application/json' -Body $body -TimeoutSec 5 | Out-Null
    Write-Host "bound $sid -> $personaId"
  } catch {
    Write-Host "skip $sid : $($_.Exception.Message)"
  }
}

# 主私聊会话（还没生成时也先占位）
Bind-One "onebot-private-$admin" $privatePid

if (-not (Test-Path $sessionsRoot)) {
  Write-Host "sessions dir not created yet: $sessionsRoot (只绑定了主私聊会话)"
  exit 0
}

function Bind-Sessions([string]$pattern, [string]$personaId) {
  $dirs = Get-ChildItem -Path $sessionsRoot -Directory -Recurse -Filter $pattern -ErrorAction SilentlyContinue
  foreach ($d in $dirs) {
    Bind-One $d.Name $personaId
  }
}

Bind-Sessions "onebot-private-$admin*" $privatePid
Bind-Sessions "onebot-group-$group*"   $groupPid
