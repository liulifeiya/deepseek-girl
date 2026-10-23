# Wait for the next NapCat QR refresh, copy it into the workspace with a unique
# name (browser cache busting), and print the decode URL from the log.
param([int]$TimeoutSec = 150)

$qr  = 'C:\Users\Administrator\Napcat\cache\qrcode.png'
$log = 'C:\Users\Administrator\qq-dsh-bot\napcat.log'
$ws  = 'C:\Users\Administrator\Documents\deepseek-harness\default-workspace'

$last = (Get-Item $qr -ErrorAction SilentlyContinue).LastWriteTime
$deadline = (Get-Date).AddSeconds($TimeoutSec)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 1
  $cur = (Get-Item $qr -ErrorAction SilentlyContinue).LastWriteTime
  if ($cur -and $cur -gt $last) { break }
}

$stamp = Get-Date -Format 'HHmmss'
$name  = "qq-login-qr-$stamp.png"
Copy-Item $qr (Join-Path $ws $name) -Force

# Latest decode URL (fallback if the image will not scan).
$url = (Select-String -Path $log -Pattern 'https://txz\.qq\.com/p\?[^\s]+' -AllMatches |
        Select-Object -Last 1).Matches.Value

"FILE=$name"
"MTIME=$((Get-Item $qr).LastWriteTime.ToString('HH:mm:ss'))"
"URL=$url"
