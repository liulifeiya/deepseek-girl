# deploy/preflight.ps1 — 装机前体检（对应旧 preflight.sh）
#   .\deploy\preflight.ps1
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$Repo    = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Home_   = $env:USERPROFILE
$BotDir  = Join-Path $Home_ 'qq-dsh-bot'
$DshHome = Join-Path $Home_ '.dsh-qq'
$fail = 0

function Check($name, [bool]$ok, $detail = '') {
  if ($ok) { Write-Host ("  OK   {0,-34} {1}" -f $name, $detail) -ForegroundColor Green }
  else     { Write-Host ("  FAIL {0,-34} {1}" -f $name, $detail) -ForegroundColor Red; $script:fail++ }
}
function Warn($name, $detail) { Write-Host ("  WARN {0,-34} {1}" -f $name, $detail) -ForegroundColor Yellow }

Write-Host "`n== 系统"
Check 'Windows' ($env:OS -eq 'Windows_NT') ([System.Environment]::OSVersion.VersionString)
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Check '管理员权限' $isAdmin 'NapCat 注入 QQ 需要'

Write-Host "`n== 运行环境"
$node = Get-Command node -ErrorAction SilentlyContinue
Check 'Node >= 22' ($node -and ([int]((& node -v).TrimStart('v').Split('.')[0]) -ge 22)) $(if ($node) { & node -v } else { 'missing' })
Check 'pnpm' ([bool](Get-Command pnpm -ErrorAction SilentlyContinue)) $(if (Get-Command pnpm -ErrorAction SilentlyContinue) { pnpm -v } else { 'missing' })
Check 'dsh' ([bool](Get-Command dsh -ErrorAction SilentlyContinue)) $(if (Get-Command dsh -ErrorAction SilentlyContinue) { dsh --version } else { 'missing' })
$py = 'C:\Program Files\Python312\python.exe'
Check 'Python 3.12' (Test-Path $py) $py

Write-Host "`n== 端口"
foreach ($p in 3001, 3080, 3081, 6099) {
  $used = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  if ($used) { Warn "端口 $p" ("被占用 pid=" + ($used | Select-Object -First 1).OwningProcess) }
  else { Check "端口 $p" $true 'free' }
}

Write-Host "`n== 已有安装"
foreach ($p in @($DshHome, $BotDir, (Join-Path $Home_ 'Napcat'), (Join-Path $Home_ 'tts-venv'))) {
  if (Test-Path $p) { Warn (Split-Path $p -Leaf) "已存在：$p（install.ps1 会覆盖配置，数据先备份）" }
  else { Check (Split-Path $p -Leaf) $true '不存在（将新建）' }
}

Write-Host "`n== QQ / NapCat"
$qq = 'C:\Program Files\Tencent\QQNT\QQ.exe'
Check 'QQ NT 已安装' (Test-Path $qq) $qq
Check 'NapCat 目录' (Test-Path (Join-Path $Home_ 'Napcat\NapCatWinBootMain.exe')) (Join-Path $Home_ 'Napcat')

Write-Host "`n== 密钥"
$envFile = Join-Path $DshHome 'dsh-web.env'
if (Test-Path $envFile) {
  $hasKey = (Get-Content $envFile -Raw) -match 'DEEPSEEK_API_KEY=\S+'
  Check 'DEEPSEEK_API_KEY' $hasKey $envFile
} else { Warn 'DEEPSEEK_API_KEY' "缺 $envFile" }

Write-Host ''
if ($fail -gt 0) { Write-Host "体检未通过：$fail 项 FAIL" -ForegroundColor Red; exit 1 }
Write-Host '体检通过，可以跑 .\deploy\install.ps1 -DryRun' -ForegroundColor Green
