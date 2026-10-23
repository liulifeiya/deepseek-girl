# deploy/run-curiosity.ps1 — 自主好奇心循环（headless 跑一次）
#
#   .\deploy\run-curiosity.ps1
#   .\deploy\run-curiosity.ps1 -DryRun
#
# 用 headless profile 跑 curiosity-prompt.txt：上网查资料 → 写进 knowledge\。
# 提示词通过 cmd 的 stdin 重定向传入（PowerShell 管道 + 多行文本会被垫片吞掉）。
# 日志：knowledge\curiosity.log

param([switch]$DryRun, [switch]$NoSync)

$ErrorActionPreference = 'Stop'
$home_ = $env:USERPROFILE
$kb = Join-Path $home_ 'knowledge'
$bot = Join-Path $home_ 'qq-dsh-bot'
$promptFile = Join-Path $bot 'curiosity-prompt.txt'
$log = Join-Path $kb 'curiosity.log'
$dshCmd = Join-Path $home_ 'AppData\Roaming\npm\dsh.cmd'

New-Item -ItemType Directory -Force -Path $kb, (Join-Path $kb 'notes') | Out-Null
if (-not (Test-Path $promptFile)) { throw "prompt missing: $promptFile" }
if (-not (Test-Path $dshCmd)) { throw "dsh not found: $dshCmd" }

$env:DSH_HOME = Join-Path $home_ '.dsh-qq'
$envFile = Join-Path $env:DSH_HOME 'dsh-web.env'
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { Set-Item -Path "env:$($matches[1])" -Value $matches[2].Trim() }
  }
}

$stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')

if ($DryRun) {
  Write-Host "would run: `"$dshCmd`" headless - < `"$promptFile`" >> `"$log`""
  exit 0
}

Add-Content -Path $log -Value "`r`n===== $stamp curiosity run =====" -Encoding utf8
Push-Location $home_
try {
  $line = '"' + $dshCmd + '" headless - < "' + $promptFile + '" >> "' + $log + '" 2>&1'
  cmd.exe /c $line
  $code = $LASTEXITCODE
} finally {
  Pop-Location
}
Add-Content -Path $log -Value "----- exit=$code -----" -Encoding utf8

# 学完就同步到独立的知识库仓库（失败不影响本轮结果）
if ($code -eq 0 -and -not $NoSync) {
  $sync = Join-Path $bot 'sync-knowledge.ps1'
  if (Test-Path $sync) {
    $learned = (Select-String -Path $log -Pattern '^LEARNED ' | Select-Object -Last 1).Line
    $msg = if ($learned) { 'knowledge: ' + $learned } else { '' }
    try {
      & powershell -NoProfile -ExecutionPolicy Bypass -File $sync -Message $msg *>> $log
    } catch {
      Add-Content -Path $log -Value "sync failed: $($_.Exception.Message)" -Encoding utf8
    }
  }
}

exit $code
