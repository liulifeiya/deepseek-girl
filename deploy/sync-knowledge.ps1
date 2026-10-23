# deploy/sync-knowledge.ps1 — 把 knowledge\ 同步到独立的知识库仓库
#
#   .\deploy\sync-knowledge.ps1
#   .\deploy\sync-knowledge.ps1 -Message "knowledge: 今天学到 X"
#   .\deploy\sync-knowledge.ps1 -DryRun
#
# Token 来自 %USERPROFILE%\.dsh-qq\kb-sync.env（KB_SYNC_TOKEN），
# 不传就按 kb-sync.py 的默认仓库 liulifeiya/deepseek-girl-knowledge 同步。

[CmdletBinding()]
param(
  [string]$Message = '',
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$py = 'C:\Program Files\Python312\python.exe'
$script = Join-Path $env:USERPROFILE 'qq-dsh-bot\kb-sync.py'
$env:KB_HOME = Join-Path $env:USERPROFILE 'knowledge'
# Python 输出统一 UTF-8，避免中文路径写进日志变乱码
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

if (-not (Test-Path $script)) { throw "kb-sync.py missing: $script" }

$args_ = @($script)
if ($Message) { $args_ += @('--message', $Message) }
if ($DryRun) { $args_ += '--dry-run' }

& $py @args_
exit $LASTEXITCODE
