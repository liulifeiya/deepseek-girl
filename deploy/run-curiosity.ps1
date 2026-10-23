# deploy/run-curiosity.ps1 — 自主好奇心循环（headless 跑一次）
#
#   .\deploy\run-curiosity.ps1
#   .\deploy\run-curiosity.ps1 -DryRun
#
# 用 headless profile 跑 curiosity-prompt.txt：上网查资料 → 写进 knowledge\。
# 提示词通过 cmd 的 stdin 重定向传入（PowerShell 管道 + 多行文本会被垫片吞掉）。
# 日志：knowledge\curiosity.log

param([switch]$DryRun)

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
exit $code
