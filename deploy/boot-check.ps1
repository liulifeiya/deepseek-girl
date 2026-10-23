# deploy/boot-check.ps1 — 开机自检（AtStartup / SYSTEM 运行）
#
# 目的：重启后无论有没有人登录，先把「机器起来了、各服务什么状态」记一笔，
# 方便事后判断自启链路是否按预期工作。
#
# 输出：%USERPROFILE%\qq-dsh-bot\boot.log（SYSTEM 下写的是 Administrator 的路径）

$ErrorActionPreference = 'SilentlyContinue'
$log = 'C:\Users\Administrator\qq-dsh-bot\boot.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log -Parent) | Out-Null

function Line($text) {
  $ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  [System.IO.File]::AppendAllText($log, "$ts  $text`r`n", [System.Text.UTF8Encoding]::new($false))
}

Line '=== boot-check start ==='
Line ("os=" + [System.Environment]::OSVersion.VersionString + " uptime(min)=" + [math]::Round(((Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime).TotalMinutes, 1))

foreach ($p in 3001, 3081) {
  $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  Line ("port $p listening=" + [bool]$c)
}

Line ("QQ processes=" + (Get-Process QQ -ErrorAction SilentlyContinue | Measure-Object).Count)
Line ("node dsh/worker processes=" + (Get-Process node -ErrorAction SilentlyContinue | Measure-Object).Count)

$sessions = query session 2>$null
Line ("sessions: " + (($sessions | Select-Object -Skip 1 | ForEach-Object { ($_ -split '\s+')[0..2] -join ' ' }) -join ' | '))

$tasks = Get-ScheduledTask -TaskName 'DshBot-*' -ErrorAction SilentlyContinue
foreach ($t in $tasks) {
  Line ("task " + $t.TaskName + " state=" + $t.State)
}

Line '=== boot-check end ==='
