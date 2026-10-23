# Monthly memory consolidation (replaces dsh-monthly.timer).
. "$PSScriptRoot\env.ps1"
Set-Location 'C:\Users\Administrator'
$prompt = Get-Content (Join-Path $PSScriptRoot 'monthly-prompt.txt') -Raw
& dsh headless $prompt *>> (Join-Path $PSScriptRoot 'monthly.log')
