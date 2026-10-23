# Register Windows scheduled tasks that replace the systemd user units.
# Run once:  powershell -ExecutionPolicy Bypass -File install-tasks.ps1
$bot = 'C:\Users\Administrator\qq-dsh-bot'
$ps  = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$user = "$env:USERDOMAIN\$env:USERNAME"

function New-Task($name, $script, $trigger) {
  $action = New-ScheduledTaskAction -Execute $ps `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$bot\$script`""
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 0)
  $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
  Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null
  Write-Host "registered: $name"
}

$logon = New-ScheduledTaskTrigger -AtLogOn -User $user

New-Task 'DshBot-DSH'     'start-dsh.ps1'    $logon
New-Task 'DshBot-Workers' 'start-workers.ps1' $logon
New-Task 'DshBot-Agent'   'start-agent.ps1'  $logon
New-Task 'DshBot-NapCat'  'start-napcat.ps1' $logon

New-Task 'DshBot-DailyRestart' 'restart-dsh.ps1' (New-ScheduledTaskTrigger -Daily -At 05:00)
New-Task 'DshBot-Monthly'      'run-monthly.ps1' (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 05:00 -WeeksInterval 4)

# 会话→人设绑定是进程内状态，重启会丢；每分钟兜底一次（对应 Linux 的 dsh-persona-bind.timer）
$everyMinute = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
  -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)
New-Task 'DshBot-PersonaBind' 'patches\bind-private-persona.ps1' $everyMinute

New-Task 'DshBot-Proactive-1030' 'run-proactive.ps1' (New-ScheduledTaskTrigger -Daily -At 10:30)
New-Task 'DshBot-Proactive-1530' 'run-proactive.ps1' (New-ScheduledTaskTrigger -Daily -At 15:30)
New-Task 'DshBot-Proactive-2030' 'run-proactive.ps1' (New-ScheduledTaskTrigger -Daily -At 20:30)

Get-ScheduledTask -TaskName 'DshBot-*' | Select-Object TaskName, State | Format-Table -AutoSize
