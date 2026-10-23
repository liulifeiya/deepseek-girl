# deploy/archive-session.ps1 — 维护机器人自己的「待归档会话」名单
#
# 机器人没有 GUI，archive-retention 的 GUI 归档集合没有数据源；
# 这里用 %USERPROFILE%\.dsh-qq\archive-list.json 作为补充名单，
# 插件会把它和 GUI 的 archivedSessionIds 合并处理。
#
#   .\deploy\archive-session.ps1 list
#   .\deploy\archive-session.ps1 add onebot-group-1003871222
#   .\deploy\archive-session.ps1 remove onebot-group-1003871222
#
# 注意：只影响「超过保留期后是否物理清理」，不影响当前会话能否继续使用。

[CmdletBinding()]
param(
  [ValidateSet('list', 'add', 'remove')][string]$Action = 'list',
  [string]$SessionId
)

$ErrorActionPreference = 'Stop'
$file = Join-Path $env:USERPROFILE '.dsh-qq\archive-list.json'

$ids = @()
if (Test-Path $file) {
  try {
    $raw = Get-Content $file -Raw
    $ids = @($raw | ConvertFrom-Json | ForEach-Object { [string]$_ })
  } catch {
    Write-Host "archive-list.json 解析失败，按空名单处理：$($_.Exception.Message)" -ForegroundColor Yellow
    $ids = @()
  }
}

switch ($Action) {
  'list' {
    if ($ids.Count -eq 0) { Write-Host "（空）$file" }
    else { $ids | ForEach-Object { $_ } }
  }
  'add' {
    if (-not $SessionId) { throw 'add 需要 -SessionId' }
    if ($ids -contains $SessionId) { Write-Host "已存在：$SessionId"; break }
    $ids += $SessionId
    [System.IO.File]::WriteAllText($file, (ConvertTo-Json -InputObject @($ids) -Compress), [System.Text.UTF8Encoding]::new($false))
    Write-Host "已加入：$SessionId（共 $($ids.Count) 条）"
  }
  'remove' {
    if (-not $SessionId) { throw 'remove 需要 -SessionId' }
    $ids = @($ids | Where-Object { $_ -ne $SessionId })
    [System.IO.File]::WriteAllText($file, (ConvertTo-Json -InputObject @($ids) -Compress), [System.Text.UTF8Encoding]::new($false))
    Write-Host "已移除：$SessionId（剩 $($ids.Count) 条）"
  }
}
