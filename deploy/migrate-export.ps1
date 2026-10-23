# deploy/migrate-export.ps1 — 导出机器人数据（替代 migrate-export.sh）
#
#   .\deploy\migrate-export.ps1                     # 不含密钥，可安全传输
#   .\deploy\migrate-export.ps1 -WithSecrets        # 含 API key / OneBot token
#   .\deploy\migrate-export.ps1 -Out D:\qqbot.zip
#
# 导出内容：qq-dsh-bot（不含日志）、.dsh-qq（profiles 只带配置、sessions、
# storages、proactive、group-wake/sleep-window）、agent（不含 projects/work）、
# tts-out 脚本、AGENTS.md。

[CmdletBinding()]
param(
  [string]$Out = (Join-Path $env:USERPROFILE ("qqbot-migrate-" + (Get-Date -Format 'yyyyMMdd-HHmm') + ".zip")),
  [switch]$WithSecrets
)

$ErrorActionPreference = 'Stop'
$Home_ = $env:USERPROFILE
$staging = Join-Path $env:TEMP ("qqbot-export-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $staging | Out-Null

function Copy-Rel($src, $rel) {
  if (-not (Test-Path $src)) { return }
  $dst = Join-Path $staging $rel
  New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent) | Out-Null
  Copy-Item $src $dst -Recurse -Force -ErrorAction SilentlyContinue
}

# 运行目录（排除日志与运行期状态）
$botDst = Join-Path $staging 'qq-dsh-bot'
New-Item -ItemType Directory -Force -Path $botDst | Out-Null
Get-ChildItem (Join-Path $Home_ 'qq-dsh-bot') -Force |
  Where-Object { $_.Name -notmatch '\.(log|pid)$' -and $_.Name -notin @('guard-state.json','image-lib','session-archive') } |
  ForEach-Object { Copy-Item $_.FullName (Join-Path $botDst $_.Name) -Recurse -Force -ErrorAction SilentlyContinue }

# DSH_HOME：配置 + 会话 + 存储
foreach ($rel in 'profiles\qq\package.json','profiles\qq\pnpm-workspace.yaml','profiles\qq\cordis.patch.yml',
                 'sessions','storages','proactive','group-wake.json','sleep-window.json') {
  Copy-Rel (Join-Path $Home_ ".dsh-qq\$rel") ".dsh-qq\$rel"
}

# agent（只带代码和少量状态）
foreach ($rel in 'worker.py','project.py','bin','GOAL.md','MEMORY.md','WORKLOG.md','state') {
  Copy-Rel (Join-Path $Home_ "agent\$rel") "agent\$rel"
}

# TTS 脚本与素材
Copy-Rel (Join-Path $Home_ 'tts-out\*.py') 'tts-out'
Copy-Rel (Join-Path $Home_ 'AGENTS.md') 'AGENTS.md'

# 密钥（显式开关）
if ($WithSecrets) {
  Copy-Rel (Join-Path $Home_ '.dsh-qq\dsh-web.env') '.dsh-qq\dsh-web.env'
  Copy-Rel (Join-Path $Home_ 'qq-dsh-bot\onebot-token.txt') 'qq-dsh-bot\onebot-token.txt'
  Write-Host '包含密钥：dsh-web.env / onebot-token.txt（注意保管）' -ForegroundColor Yellow
}

if (Test-Path $Out) { Remove-Item $Out -Force }
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $Out -CompressionLevel Optimal
Remove-Item $staging -Recurse -Force
Write-Host "导出完成: $Out ($([math]::Round((Get-Item $Out).Length / 1KB, 1)) KB)"
Write-Host '新机器上先跑 deploy\install.ps1，再跑 deploy\migrate-import.ps1 -Zip <文件>'
