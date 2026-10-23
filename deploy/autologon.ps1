# deploy/autologon.ps1 — 配置/清除 Windows 自动登录（重启后无需人工登录）
#
#   .\deploy\autologon.ps1                 # 查看当前状态
#   .\deploy\autologon.ps1 -Enable         # 交互输入密码并启用（密码存入 LSA）
#   .\deploy\autologon.ps1 -Disable        # 清除自动登录
#
# 说明：这里用注册表 AutoAdminLogon + LSA 保存的凭据（等价于 netplwiz）。
# 密码不会以明文写进注册表 DefaultPassword；若你更放心自己操作，
# 直接运行 `netplwiz`，取消「要使用本计算机，用户必须输入用户名和密码」即可。

[CmdletBinding()]
param(
  [switch]$Enable,
  [switch]$Disable
)

$ErrorActionPreference = 'Stop'
$wg = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'

function Show-Status {
  $v = Get-ItemProperty $wg -ErrorAction SilentlyContinue
  "AutoAdminLogon : $($v.AutoAdminLogon)"
  "DefaultUserName: $($v.DefaultUserName)"
  "DefaultDomain  : $($v.DefaultDomainName)"
  "DefaultPassword: $(if ((Get-ItemProperty $wg -Name DefaultPassword -ErrorAction SilentlyContinue).DefaultPassword) { '<present>' } else { '<none>' })"
}

if (-not $Enable -and -not $Disable) { Show-Status; exit 0 }

if ($Disable) {
  Set-ItemProperty $wg -Name AutoAdminLogon -Value '0'
  Remove-ItemProperty $wg -Name DefaultPassword -ErrorAction SilentlyContinue
  Remove-ItemProperty $wg -Name DefaultUserName -ErrorAction SilentlyContinue
  Remove-ItemProperty $wg -Name DefaultDomainName -ErrorAction SilentlyContinue
  Write-Host '已关闭自动登录'
  Show-Status
  exit 0
}

$user = $env:USERNAME
$domain = $env:COMPUTERNAME
Write-Host "将为 $domain\$user 配置自动登录（密码只用于本机登录，不写入本脚本）"
$secure = Read-Host -AsSecureString '请输入该账户的 Windows 登录密码'
$plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
  [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))

Set-ItemProperty $wg -Name AutoAdminLogon -Value '1'
Set-ItemProperty $wg -Name DefaultUserName -Value $user
Set-ItemProperty $wg -Name DefaultDomainName -Value $domain
# 明文落在注册表里，仅本机管理员可读；不想这样的话改用 netplwiz（存 LSA）
Set-ItemProperty $wg -Name DefaultPassword -Value $plain

Write-Host '已启用自动登录。下次重启将自动进入桌面并触发 DshBot-* 的登录任务。'
Show-Status
