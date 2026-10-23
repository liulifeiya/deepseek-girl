# Proactive QQ greeting, one run = at most one message (replaces qq-proactive.timer).
. "$PSScriptRoot\env.ps1"
$py = 'C:\Program Files\Python312\python.exe'
& $py (Join-Path $PSScriptRoot 'proactive.py') --send *>> (Join-Path $PSScriptRoot 'proactive.log')
