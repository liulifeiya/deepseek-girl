# deploy/verify-autostart.ps1 — 检查「重启后是否无需人工登录即可自启」
#
#   .\deploy\verify-autostart.ps1
#
# 检查项：自动登录注册表、任务触发器/运行账户、boot.log 最近一次开机记录。
# 退出码 0 = 全过；非 0 = 有问题项数。

[CmdletBinding()]
param()

$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$fail = 0
function Check($name, [bool]$ok, $detail = '') {
  if ($ok) { Write-Host ("PASS  {0,-26} {1}" -f $name, $detail) -ForegroundColor Green }
  else     { Write-Host ("FAIL  {0,-26} {1}" -f $name, $detail) -ForegroundColor Red; $script:fail++ }
}
function Info($name, $detail) { Write-Host ("INFO  {0,-26} {1}" -f $name, $detail) }

Write-Host "`n== 自动登录"
$wg = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
$v = Get-ItemProperty $wg
$auto = "$($v.AutoAdminLogon)"
Check 'AutoAdminLogon=1' ($auto -eq '1') "当前=$auto"
Check 'DefaultUserName' ([bool]$v.DefaultUserName) "当前=$($v.DefaultUserName)"
$hasPwd = [bool](Get-ItemProperty $wg -Name DefaultPassword -ErrorAction SilentlyContinue).DefaultPassword
Info 'DefaultPassword' $(if ($hasPwd) { '存在（注册表明文）' } else { '无（可能由 LSA 托管，正常）' })
Info 'AutoLogonCount' "$($v.AutoLogonCount)"

Write-Host "`n== 计划任务"
$tasks = Get-ScheduledTask -TaskName 'DshBot-*' -ErrorAction SilentlyContinue
foreach ($t in $tasks) {
  $trigger = ($t.Triggers | ForEach-Object { $_.CimClass.CimClassName -replace 'MSFT_Task','' }) -join ','
  $who = $t.Principal.UserId
  $logon = $t.Principal.LogonType
  Write-Host ("      {0,-24} trigger={1,-14} user={2,-22} logonType={3}" -f $t.TaskName, $trigger, $who, $logon)
}

$atStartup = @($tasks | Where-Object { $_.Triggers | Where-Object { $_.CimClass.CimClassName -match 'BootTrigger' } })
$atLogon = @($tasks | Where-Object { $_.Triggers | Where-Object { $_.CimClass.CimClassName -match 'LogonTrigger' } })
Check '存在开机任务' ($atStartup.Count -ge 1) "共 $($atStartup.Count) 个（应含 DshBot-BootCheck）"
Check '存在登录任务' ($atLogon.Count -ge 1) "共 $($atLogon.Count) 个（DSH/Workers/Agent/NapCat）"

Write-Host "`n== 上次开机自检"
$bootLog = 'C:\Users\Administrator\qq-dsh-bot\boot.log'
if (Test-Path $bootLog) {
  $last = Get-Content $bootLog | Where-Object { $_ -match 'boot-check start' } | Select-Object -Last 1
  Info 'boot.log 最近记录' $last
  $since = Get-Content $bootLog | Select-Object -Last 40
  $port = ($since | Where-Object { $_ -match 'port 3081 listening=True' } | Select-Object -Last 1)
  $qqp = ($since | Where-Object { $_ -match 'QQ processes=([1-9]\d*)' } | Select-Object -Last 1)
  Check 'boot.log 显示后端已起' ([bool]$port) $(if ($port) { $port.Trim() } else { '未找到 port 3081 listening=True' })
  Check 'boot.log 显示 QQ 进程' ([bool]$qqp) $(if ($qqp) { $qqp.Trim() } else { '未找到 QQ 进程记录' })
} else {
  Check 'boot.log 存在' $false '还没经历过一次开机自检'
}

Write-Host ''
if ($fail -eq 0) { Write-Host '自启检查通过' -ForegroundColor Green; exit 0 }
Write-Host "自启检查失败 $fail 项" -ForegroundColor Red
exit $fail
