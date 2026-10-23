# deploy/run-learn-queue.ps1 — 处理「看不懂的表情包」学习队列
#
#   .\deploy\run-learn-queue.ps1
#   .\deploy\run-learn-queue.ps1 -Max 1 -DryRun
#
# 从 knowledge\_queue.jsonl 取 pending 项，逐条用 headless 看图+搜索+写笔记，
# 成功记 done，失败记 failed。队列为空时直接退出，不启动 dsh。

param(
  [int]$Max = 2,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$home_ = $env:USERPROFILE
$kb = Join-Path $home_ 'knowledge'
$bot = Join-Path $home_ 'qq-dsh-bot'
$py = 'C:\Program Files\Python312\python.exe'
$dshCmd = Join-Path $home_ 'AppData\Roaming\npm\dsh.cmd'
$promptFile = Join-Path $bot 'meme-prompt.txt'
$log = Join-Path $kb 'learn-queue.log'
$env:KB_HOME = $kb

New-Item -ItemType Directory -Force -Path $kb | Out-Null

$pendingJson = & $py (Join-Path $bot 'kb-queue.py') list --json 2>&1
if ($LASTEXITCODE -ne 0) { Add-Content $log "queue list failed: $pendingJson" -Encoding utf8; exit 1 }
$items = @()
try {
  $parsed = @(($pendingJson -join "`n") | ConvertFrom-Json)
  # ConvertFrom-Json 对空数组会返回 $null，@($null) 会变成 1 个空元素，必须过滤
  $items = @($parsed | Where-Object { $_ -and $_.id -and $_.image })
} catch { $items = @() }
if ($items.Count -eq 0) {
  Add-Content -Path $log -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') queue empty" -Encoding utf8
  exit 0
}

$env:DSH_HOME = Join-Path $home_ '.dsh-qq'
$envFile = Join-Path $env:DSH_HOME 'dsh-web.env'
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { Set-Item -Path "env:$($matches[1])" -Value $matches[2].Trim() }
  }
}
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

$basePrompt = Get-Content $promptFile -Raw
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Add-Content -Path $log -Value "`r`n===== $stamp learn-queue ($($items.Count) pending, max $Max) =====" -Encoding utf8

$processed = 0
foreach ($it in $items) {
  if ($processed -ge $Max) { break }
  $processed++

  $job = [ordered]@{ hash = $it.hash; image = $it.image; context = $it.context }
  $prompt = $basePrompt + "`r`n## 本条任务数据`r`n" + ($job | ConvertTo-Json -Compress)
  $tmp = Join-Path $env:TEMP ("meme-" + $it.id + ".txt")
  [System.IO.File]::WriteAllText($tmp, $prompt, [System.Text.UTF8Encoding]::new($false))

  if ($DryRun) {
    Add-Content -Path $log -Value "would learn: $($it.id) $($it.image)" -Encoding utf8
    continue
  }

  $out = Join-Path $env:TEMP ("meme-" + $it.id + ".out")
  Push-Location $home_
  try {
    $line = '"' + $dshCmd + '" headless - < "' + $tmp + '" > "' + $out + '" 2>&1'
    cmd.exe /c $line
    $code = $LASTEXITCODE
  } finally {
    Pop-Location
  }

  $text = Get-Content $out -Raw -Encoding utf8 -ErrorAction SilentlyContinue
  $learned = ([regex]::Matches($text, '(?m)^LEARNED .+') | Select-Object -Last 1).Value
  $failed = ([regex]::Matches($text, '(?m)^(FAILED|SKIP) .+') | Select-Object -Last 1).Value

  if ($code -eq 0 -and $learned) {
    & $py (Join-Path $bot 'kb-queue.py') done --id $it.id --result $learned | Out-Null
    Add-Content -Path $log -Value "OK   $($it.id)  $learned" -Encoding utf8
  } elseif ($failed) {
    & $py (Join-Path $bot 'kb-queue.py') done --id $it.id --result $failed | Out-Null
    Add-Content -Path $log -Value "SKIP $($it.id)  $failed" -Encoding utf8
  } else {
    $tail = if ($text.Length -gt 300) { $text.Substring($text.Length - 300) } else { $text }
    & $py (Join-Path $bot 'kb-queue.py') fail --id $it.id --reason "exit=$code" | Out-Null
    Add-Content -Path $log -Value "FAIL $($it.id) exit=$code`r`n$tail" -Encoding utf8
  }
  Remove-Item $tmp, $out -Force -ErrorAction SilentlyContinue
}
Add-Content -Path $log -Value "----- processed=$processed -----" -Encoding utf8

# 有新笔记就同步到知识库仓库
if ($processed -gt 0 -and -not $DryRun) {
  $sync = Join-Path $bot 'sync-knowledge.ps1'
  if (Test-Path $sync) {
    try {
      $syncOut = & powershell -NoProfile -ExecutionPolicy Bypass -File $sync -Message "knowledge: 表情包补习（$processed 条）" 2>&1 | Out-String
      Add-Content -Path $log -Value $syncOut -Encoding utf8
    } catch {
      Add-Content -Path $log -Value "sync failed: $($_.Exception.Message)" -Encoding utf8
    }
  }
}
