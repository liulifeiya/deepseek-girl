# Start NapCat (injects into QQ and prints/updates the login QR).
. "$PSScriptRoot\env.ps1"

$n = 'C:\Users\Administrator\Napcat'
$qq = 'C:\Program Files\Tencent\QQNT\QQ.exe'

# 幂等：已经在跑就不要再起一份（自动登录 + 手动 RDP 会触发两次）
$qqProc  = Get-Process QQ -ErrorAction SilentlyContinue
$bootProc = Get-Process NapCatWinBootMain -ErrorAction SilentlyContinue
if ($qqProc -and $bootProc) {
  Write-Host 'NapCat/QQ already running, skip.'
  exit 0
}

# NapCatWinBootMain needs the VC runtime DLLs and QQ dir on PATH.
$env:Path = "$n;C:\Program Files\Tencent\QQNT;$env:Path"
$env:NAPCAT_PATCH_PACKAGE = "$n\qqnt.json"
$env:NAPCAT_LOAD_PATH     = "$n\loadNapCat.js"
$env:NAPCAT_INJECT_PATH   = "$n\NapCatWinBootHook.dll"
$env:NAPCAT_LAUNCHER_PATH = "$n\NapCatWinBootMain.exe"
$env:NAPCAT_MAIN_PATH     = "$n\napcat.mjs"

Set-Location $n
$log = Join-Path $PSScriptRoot 'napcat.log'
& "$n\NapCatWinBootMain.exe" $qq "$n\NapCatWinBootHook.dll" -q $env:BOT_QQ *>> $log
