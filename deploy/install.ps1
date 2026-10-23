# deploy/install.ps1 — Windows 一键部署（替代原来的 install.sh）
#
#   .\deploy\install.ps1 -DryRun          # 只看计划
#   .\deploy\install.ps1                  # 真装
#   .\deploy\install.ps1 -SkipTasks       # 不注册计划任务
#
# 参数（都有默认值；也可以先改 deploy\windows\env.ps1）：
#   -BotQQ 2836148023 -AdminQQ 2812108776
#   -OneBotToken <32字节hex>   # 不给就自动生成
#   -DshPort 3081 -NapcatWsPort 3001
#
# 步骤与旧 install.sh 对应：
#   10-base     依赖检查（Node / pnpm / Python / dsh）
#   20-dsh      profile 与 6 个插件
#   30-plugins  cordis 覆盖 + onebot 补丁
#   40-botfiles 运行目录、人设、token
#   50-tts      venv 与脚本
#   60-agent    常挂智能体
#   70-napcat   NapCat 配置
#   80-services 计划任务

[CmdletBinding()]
param(
  [string]$BotQQ = '2836148023',
  [string]$AdminQQ = '2812108776',
  [string]$OneBotToken = '',
  [int]$DshPort = 3081,
  [int]$NapcatWsPort = 3001,
  [switch]$DryRun,
  [switch]$SkipTasks,
  [switch]$SkipStart
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$Repo    = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Win     = $PSScriptRoot
$Home_   = $env:USERPROFILE
$BotHome = $Home_
$BotDir  = Join-Path $Home_ 'qq-dsh-bot'
$DshHome = Join-Path $Home_ '.dsh-qq'
$Profile = Join-Path $DshHome 'profiles\qq'
$Napcat  = Join-Path $Home_ 'Napcat'

function Step($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }
function Run($cmd, $args_) {
  if ($DryRun) { Write-Host "  would run: $cmd $args_" -ForegroundColor DarkGray; return }
  & $cmd @args_
  if ($LASTEXITCODE -ne 0) { throw "failed: $cmd $args_" }
}

Write-Host "repo    : $Repo"
Write-Host "BOT_HOME: $BotHome"
Write-Host "DSH_HOME: $DshHome"
if ($DryRun) { Write-Host "mode    : DRY RUN" -ForegroundColor Yellow }

# ---------------------------------------------------------------- 10-base
Step '10-base 依赖检查'
$node = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $node) { throw 'Node 24 未安装' }
$nodeMajor = [int]((& node -v).TrimStart('v').Split('.')[0])
if ($nodeMajor -lt 22) { throw "Node 版本过低: $(& node -v)" }
Write-Host "  node $( & node -v )"

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) { throw 'pnpm 未安装（corepack enable --install-directory %APPDATA%\npm pnpm）' }
Write-Host "  pnpm $(pnpm -v)"

$py = 'C:\Program Files\Python312\python.exe'
if (-not (Test-Path $py)) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw 'Python 3.12 未安装' }
Write-Host "  python $(& $py --version)"

if (-not (Get-Command dsh -ErrorAction SilentlyContinue)) { throw 'dsh 未安装（pnpm add -g @deepseek-ai/dsh）' }
Write-Host "  dsh $(dsh --version)"

# ---------------------------------------------------------------- 20-dsh
Step '20-dsh profile 与插件'
New-Item -ItemType Directory -Force -Path $Profile | Out-Null
if ($DryRun) {
  Write-Host "  would copy web/{package.json,pnpm-workspace.yaml,pnpm-lock.yaml} -> $Profile"
} else {
  Copy-Item (Join-Path $Repo 'web\package.json')        $Profile -Force
  Copy-Item (Join-Path $Repo 'web\pnpm-workspace.yaml') $Profile -Force
  Copy-Item (Join-Path $Repo 'web\pnpm-lock.yaml')      $Profile -Force
  # pnpm 12 需要 allowBuilds；旧版 pnpm 只认 onlyBuiltDependencies，两个都写
  $ws = Get-Content (Join-Path $Repo 'web\pnpm-workspace.yaml') -Raw
  if ($ws -notmatch 'allowBuilds') {
    $key = '"@momojie-s/dsh-archive-retention@https://codeload.github.com/Momojie-S/dsh-archive-retention/tar.gz/2cdd2def3e4fea4781d4f3497175929aa224a3bb"'
    $ws += "allowBuilds:`n  ${key}: true`n"
    [System.IO.File]::WriteAllText((Join-Path $Profile 'pnpm-workspace.yaml'), $ws, [System.Text.UTF8Encoding]::new($false))
  }
  Push-Location $Profile
  try { Run pnpm @('install', '--frozen-lockfile') } finally { Pop-Location }
}

# ---------------------------------------------------------------- 30-plugins
Step '30-plugins cordis 覆盖 + onebot 补丁'
if (-not $OneBotToken) {
  $bytes = New-Object byte[] 32
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  $rng.GetBytes($bytes)
  $rng.Dispose()
  $OneBotToken = ($bytes | ForEach-Object { $_.ToString('x2') }) -join ''
}
if ($DryRun) {
  Write-Host "  would render cordis.patch.yml (bot=$BotQQ admin=$AdminQQ ws=$NapcatWsPort)"
} else {
  $yml = @"
# 用户 patch 层：dsh-onebot-qq 配置覆盖（Windows）
- id: system-prompt
  config:
    includeHarnessIdentity: false
    personaPrefix: ""
- id: persona-dafeiyu
  config:
    suffix: ""
- id: dsh-onebot
  config:
    mode: forward
    url: ws://127.0.0.1:$NapcatWsPort
    accessToken: "$OneBotToken"
    botQQ: "$BotQQ"
    adminUsers: ["$AdminQQ"]
    requireMention: true
    groupPolicy: allowlist
    groupAllowFrom: ["1003871222", "877935643"]
    dmPolicy: open
    workspacePath: '$BotHome'
    logLevel: info
    interimMessages: false
# openwolf 默认会把解剖表注入 AGENTS.md（家目录扫出 20KB 无用路径，每轮烧 token），
# 关掉注入并排除无关大目录。
- id: openwolf
  name: dsh-openwolf
  config:
    injectAgentsMd: false
    ignore:
      - node_modules
      - .git
      - AppData
      - Documents
      - Downloads
      - Desktop
      - Napcat
      - tts-venv
      - .dsh
      - .dsh-qq
      - .dshwolf
      - agent/projects
      - agent/work
      - agent/logs
      - "*.log"
# Windows 上 workspace 是整个家目录时，ACL 沙箱的临时目录会落在 workspace 里，
# 报 "Windows ACL temp root must be outside the workspace"，导致所有 shell 调用失败。
# 机器人要跑 tts-out / qq-dsh-bot 下的固定脚本，这里用 danger-full-access。
- id: permission
  name: "@deepseek-ai/dsh-permission-presets"
  config:
    presets:
      read-only:
        sandbox: read-only
        approval: ask
      workspace-write:
        sandbox: workspace-write
        approval: ask
      danger-full-access:
        sandbox: danger-full-access
        approval: never
    defaultPreset: danger-full-access
"@
  [System.IO.File]::WriteAllText((Join-Path $Profile 'cordis.patch.yml'), $yml, [System.Text.UTF8Encoding]::new($false))
  New-Item -ItemType Directory -Force -Path $BotDir | Out-Null
  [System.IO.File]::WriteAllText((Join-Path $BotDir 'onebot-token.txt'), "$OneBotToken`n", [System.Text.UTF8Encoding]::new($false))
  $lib = Join-Path $Profile 'node_modules\dsh-onebot-qq\lib'
  # Windows 上杀软/索引器偶尔会短暂锁住刚解压的文件（写时报 Errno 22），重试即可
  $patched = $false
  for ($i = 1; $i -le 3 -and -not $patched; $i++) {
    & $py (Join-Path $Repo 'patches\apply-onebot-patches.py') $lib
    if ($LASTEXITCODE -eq 0) { $patched = $true } else { Start-Sleep -Seconds 3 }
  }
  if (-not $patched) { throw 'apply-onebot-patches.py failed after 3 attempts' }

  # archive-retention 补丁：文件名兼容 / dryRun / 清单 / cron 校验 / 状态持久化 / 跨进程锁
  & $py (Join-Path $Repo 'patches\patch-archive-retention.py')
  if ($LASTEXITCODE -ne 0) { throw 'patch-archive-retention.py failed' }
  # v2：回收站 / 容量上限 / 机器人本地归档名单
  & $py (Join-Path $Repo 'patches\patch-archive-retention-2.py')
  if ($LASTEXITCODE -ne 0) { throw 'patch-archive-retention-2.py failed' }
}

# ---------------------------------------------------------------- 40-botfiles
Step '40-botfiles 运行目录 / 人设 / 配置'
$dirs = @($BotDir, (Join-Path $BotDir 'patches'), (Join-Path $BotDir 'image-lib'), (Join-Path $BotDir 'session-archive'), $DshHome)
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
if ($DryRun) {
  Write-Host "  would copy runtime/, scripts/, patches/, personas/ into $BotDir"
} else {
  Copy-Item (Join-Path $Repo 'runtime\*') $BotDir -Force
  Copy-Item (Join-Path $Repo 'scripts\*') $BotDir -Force
  Copy-Item (Join-Path $Repo 'patches\*') (Join-Path $BotDir 'patches') -Force -Recurse
  Copy-Item (Join-Path $Repo 'personas\persona-*.md') $BotDir -Force
  Copy-Item (Join-Path $Repo 'config\group-wake.json') $DshHome -Force
  Copy-Item (Join-Path $Repo 'config\sleep-window.json') $DshHome -Force
  Copy-Item (Join-Path $Repo 'config\AGENTS.md') (Join-Path $BotHome 'AGENTS.md') -Force
  if (-not (Test-Path (Join-Path $BotDir 'proactive-targets.txt'))) {
    [System.IO.File]::WriteAllText((Join-Path $BotDir 'proactive-targets.txt'), "# 主动搭话白名单：QQ号 昵称 [group:群号] [dm]`n", [System.Text.UTF8Encoding]::new($false))
  }
  # 人设卡导入插件 store
  Run $py @((Join-Path $BotDir 'import-personas.py'), $Repo)
}

# ---------------------------------------------------------------- 50-tts
Step '50-tts venv 与脚本'
$venv = Join-Path $Home_ 'tts-venv'
$out  = Join-Path $Home_ 'tts-out'
New-Item -ItemType Directory -Force -Path $out | Out-Null
if ($DryRun) {
  Write-Host "  would create venv $venv and install pillow/aiohttp/tabulate"
} else {
  if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) { Run $py @('-m', 'venv', $venv) }
  Copy-Item (Join-Path $Repo 'tts\*.py') $out -Force
  $vpy = Join-Path $venv 'Scripts\python.exe'
  Run $vpy @('-m', 'pip', 'install', '-q', '--disable-pip-version-check',
             '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple', 'pillow', 'aiohttp', 'tabulate')
}

# ---------------------------------------------------------------- 60-agent
Step '60-agent 常挂智能体'
$agent = Join-Path $Home_ 'agent'
foreach ($d in @('', 'bin', 'inbox', 'done', 'failed', 'state', 'logs', 'work', 'projects', 'hooks')) {
  New-Item -ItemType Directory -Force -Path (Join-Path $agent $d) | Out-Null
}
if (-not $DryRun) {
  Copy-Item (Join-Path $Repo 'agent\worker.py')  $agent -Force
  Copy-Item (Join-Path $Repo 'agent\project.py') $agent -Force
  Copy-Item (Join-Path $Repo 'agent\bin\*') (Join-Path $agent 'bin') -Force
}

# ---------------------------------------------------------------- 70-napcat
Step '70-napcat 配置'
if ($DryRun) {
  Write-Host "  would render NapCat configs into $Napcat\config"
} else {
  Run $py @((Join-Path $Win 'render-napcat-config.py'))
}

# ---------------------------------------------------------------- 80-services
Step '80-services 计划任务'
if ($SkipTasks) {
  Write-Host '  skipped (-SkipTasks)'
} elseif ($DryRun) {
  Write-Host '  would register DshBot-* scheduled tasks'
} else {
  PowerShell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Win 'install-tasks.ps1')
}

Step '完成'
if (-not $DryRun) {
  Write-Host @"

下一步：
  1) 首次登录 QQ（NapCat 不能自动登录）：
       powershell -File "$Win\show-qr.ps1"
  2) 启动后端与保活：
       schtasks /Run /TN DshBot-DSH
       schtasks /Run /TN DshBot-Workers
  3) 看日志：
       Get-Content "$BotDir\dsh-web.log" -Tail 30 -Wait
"@
  if (-not $SkipStart) {
    Write-Host '  启动 NapCat 与后端 ...'
    Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',"$Win\start-napcat.ps1"
    schtasks /Run /TN 'DshBot-DSH' | Out-Null
    schtasks /Run /TN 'DshBot-Workers' | Out-Null
  }
}
