# deploy/migrate-import.ps1 — 还原机器人数据（替代 migrate-import.sh）
#
#   .\deploy\migrate-import.ps1 -Zip .\qqbot-migrate-20261024-0130.zip
#   .\deploy\migrate-import.ps1 -Zip .\qqbot-migrate.zip -DryRun
#
# 先跑 install.ps1（可用 -SkipStart），再跑这个，最后启动服务。

[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Zip,
  [switch]$DryRun,
  [switch]$Force
)

$ErrorActionPreference = 'Stop'
$Home_ = $env:USERPROFILE

if (-not (Test-Path $Zip)) { throw "找不到压缩包: $Zip" }
$staging = Join-Path $env:TEMP ("qqbot-import-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
Expand-Archive -Path $Zip -DestinationPath $staging -Force

$items = Get-ChildItem $staging -Force
Write-Host "将还原到 $Home_ ："
$items | ForEach-Object { Write-Host "  $($_.Name)" }

if ($DryRun) {
  Write-Host 'DRY RUN：未写入。' -ForegroundColor Yellow
  Remove-Item $staging -Recurse -Force
  return
}

# 目标已存在时默认不覆盖，除非 -Force
foreach ($item in $items) {
  $dst = Join-Path $Home_ $item.Name
  if ((Test-Path $dst) -and -not $Force) {
    Write-Host "跳过已存在: $($item.Name)（要覆盖加 -Force）" -ForegroundColor Yellow
    continue
  }
  Copy-Item $item.FullName $dst -Recurse -Force
  Write-Host "已还原: $($item.Name)"
}

Remove-Item $staging -Recurse -Force
Write-Host @'

还原完成，下一步：
  schtasks /Run /TN DshBot-DSH
  schtasks /Run /TN DshBot-Workers
  schtasks /Run /TN DshBot-PersonaBind
  Get-Content "$env:USERPROFILE\qq-dsh-bot\dsh-web.log" -Tail 30
'@
