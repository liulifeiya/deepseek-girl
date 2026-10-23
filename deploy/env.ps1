# Shared environment for the QQ bot on Windows.
# Dot-source this from every start script:  . "$PSScriptRoot\env.ps1"

$env:DSH_HOME   = 'C:\Users\Administrator\.dsh-qq'
$env:BOT_HOME   = 'C:/Users/Administrator'
$env:BOT_QQ     = '2836148023'
$env:ADMIN_QQ   = '2812108776'
$env:PYTHONUTF8 = '1'

# Node + pnpm + dsh on PATH (same as the machine-wide install)
$nodeBin = 'C:\Program Files\nodejs'
$npmBin  = 'C:\Users\Administrator\AppData\Roaming\npm'
if ($env:Path -notlike "*$nodeBin*") { $env:Path = "$nodeBin;$npmBin;$env:Path" }

# Python used by the runtime scripts
$py = 'C:\Program Files\Python312\python.exe'
if (Test-Path $py) { $env:BOT_PYTHON = $py }

$env:NAPCAT_RESTART_CMD = 'C:\Windows\System32\cmd.exe /c C:\Users\Administrator\qq-dsh-bot\restart-napcat.cmd'
$env:NAPCAT_QR_PNG      = 'C:\Users\Administrator\Napcat\cache\qrcode.png'
