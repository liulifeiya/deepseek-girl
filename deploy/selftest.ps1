# deploy/selftest.ps1 — 部署后自检（模块行为 + 接口 + shell 执行）
#
#   .\deploy\selftest.ps1              # 全套
#   .\deploy\selftest.ps1 -NoShell     # 跳过 headless shell 测试（不花模型额度）
#
# 退出码 0 = 全过；非 0 = 失败项数。

[CmdletBinding()]
param(
  [switch]$NoShell
)

$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$env:BOT_HOME = $env:USERPROFILE
$env:DSH_HOME = Join-Path $env:USERPROFILE '.dsh-qq'
$env:BOT_DSH_API = 'http://127.0.0.1:3081'

$fail = 0

Write-Host "`n== 模块 / 接口自检" -ForegroundColor Cyan
& node (Join-Path $Repo 'scripts\selftest.mjs')
if ($LASTEXITCODE -ne 0) { $fail += [int]$LASTEXITCODE }

if (-not $NoShell) {
  Write-Host "`n== Agent shell 执行（headless，同 profile 权限配置）" -ForegroundColor Cyan
  $sth = Join-Path $env:USERPROFILE '.dsh-selftest'
  $prof = Join-Path $sth 'profiles\selftest'
  New-Item -ItemType Directory -Force -Path $prof | Out-Null
  @{
    name = 'dsh-profile-selftest'
    private = $true
    dependencies = @{}
    dsh = @{ profile = @{ bundles = @('@deepseek-ai/dsh-base', '@deepseek-ai/dsh-headless') } }
  } | ConvertTo-Json -Depth 8 | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $prof 'package.json'), $_, [System.Text.UTF8Encoding]::new($false))
  }
  $yml = @'
- id: permission
  name: "@deepseek-ai/dsh-permission-presets"
  config:
    presets:
      read-only: { sandbox: read-only, approval: ask }
      workspace-write: { sandbox: workspace-write, approval: ask }
      danger-full-access: { sandbox: danger-full-access, approval: never }
    defaultPreset: danger-full-access
'@
  [System.IO.File]::WriteAllText((Join-Path $prof 'cordis.patch.yml'), $yml, [System.Text.UTF8Encoding]::new($false))

  $envFile = Join-Path $env:DSH_HOME 'dsh-web.env'
  if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
      if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { Set-Item -Path "env:$($matches[1])" -Value $matches[2].Trim() }
    }
  }

  $savedHome = $env:DSH_HOME
  $env:DSH_HOME = $sth
  Push-Location $env:USERPROFILE
  try {
    $out = & dsh --profile selftest headless "用 shell 工具执行 echo selftest-shell-ok，把 stdout 原样告诉我，只做这一件事。" 2>&1 | Out-String
  } finally {
    Pop-Location
    $env:DSH_HOME = $savedHome
  }
  if ($out -match 'selftest-shell-ok') {
    Write-Host 'PASS  shell-exec          headless 实跑 echo 成功'
  } else {
    Write-Host 'FAIL  shell-exec          未拿到预期输出' -ForegroundColor Red
    Write-Host ($out.Substring(0, [Math]::Min(400, $out.Length)))
    $fail++
  }
}

Write-Host ''
if ($fail -eq 0) { Write-Host '自检全部通过' -ForegroundColor Green; exit 0 }
Write-Host "自检失败 $fail 项" -ForegroundColor Red
exit $fail
