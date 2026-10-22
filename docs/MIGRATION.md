# 迁移手册

把一台机器上的 QQ 机器人整套搬到另一台，包括：dsh + 插件 + 补丁、NapCat/QQ、运行脚本、人设与记忆、常挂 agent、定时任务。

## 0. 这套系统由什么组成

| 层 | 位置 | 内容 | 能否自动装 |
|---|---|---|---|
| dsh 运行时 | `~/.local/node`、`~/.local/share/pnpm` | Node 24、pnpm、dsh（版本锁死） | ✅ |
| 插件 | `~/.dsh-user/profiles/web` | dsh-onebot-qq、persona、proactive、cron 等 | ✅ |
| 本地补丁 | 插件 `lib/` | 引用回复、分段、群聊插话、睡眠时段、人格锁定 | ✅（`patches/apply-onebot-patches.py`） |
| 机器人脚本 | `~/qq-dsh-bot` | guard / keepalive / watchdog / 主动搭话 / 二维码 | ✅ |
| QQ 客户端 | `~/Napcat` | QQ + NapCat 注入 | ✅ 安装，❌ 登录要扫码 |
| Python | `~/tts-venv`、`~/tts-out` | 语音、音乐、表情包 | ✅（依赖 PyPI） |
| 常挂 agent | `~/agent` | 任务队列、立项/实施/验收 | ✅ |
| 服务 | `~/.config/systemd/user` | 12 个 unit + timer | ✅（需要 linger） |
| 数据 | `.dsh-user/`、`~/agent/projects` 等 | 会话、人设、记忆、白名单 | 用迁移包导入 |

## 1. 迁移前须知

- **目标机**：Ubuntu 22.04 / 24.04，x86_64，建议 2 核 2G 以上、20G 磁盘（QQ 客户端约 700M）。
- **用户名/家目录**：建议保持 `ubuntu` / `/home/ubuntu`。换用户名能装，但 dsh 的会话目录名由工作目录算出来（`--home-ubuntu--`），老会话不会自动接上；`/new` 之后的新会话不受影响。
- **QQ 登录无法自动化**：新机器第一次必须扫码，可能还会触发新设备验证。老机器先别删，万一新机器登不上还能退回去。
- **NapCat 版本会变**：安装脚本拉的是 latest，dsh 插件补丁锚点可能对不上。`install.sh` 会在补丁打不上时明确报错，不会静默失败。
- **密钥不随 git 走**：`deploy/deploy.conf`、`onebot-token.txt`、`dsh-web.env` 都在 `.gitignore` 里。迁移包默认也不含密钥，要带得显式加 `--with-secrets`。

## 2. 老机器：导出

```bash
cd ~/deepseek-girl

# 不含密钥（可走网盘/微信传）
./deploy/migrate-export.sh

# 建议：带密钥 + 带会话，一步到位
./deploy/migrate-export.sh --with-secrets
```

产出：`~/qqbot-migrate-YYYYmmdd-HHMM.tar.gz` 和同名 `.sha256`。

- 默认包含：配置、人设、记忆、白名单、agent 项目、会话（`--no-sessions` 可去掉）。
- `--with-media` 会带上收发的图片，通常没必要。
- `--stop` 会先停服务再打包，保证会话文件一致；打完自动拉起。
- `--with-qq-login` 会带上 QQ 登录态（约 1MB），可能省掉扫码；但换设备/IP 常触发验证，失败就正常扫码。
- 带密钥的包是**明文**，传完就删。

## 3. 新机器：装环境

```bash
# 1) 基础工具
sudo apt-get update && sudo apt-get install -y git curl

# 2) 拉仓库（公开仓库，不需要登录）
git clone https://github.com/liulifeiya/deepseek-girl.git ~/deepseek-girl
cd ~/deepseek-girl

# 3) 体检
./deploy/preflight.sh

# 4) 配置
cp deploy/deploy.conf.example deploy/deploy.conf
chmod 600 deploy/deploy.conf
$EDITOR deploy/deploy.conf
```

`deploy.conf` 里至少填：

```ini
BOT_QQ=你的机器人QQ
ADMIN_QQ=你的管理员QQ
ONEBOT_TOKEN=$(openssl rand -hex 32)   # 先生成，粘进去
DEEPSEEK_API_KEY=sk-...
GROUP_ALLOW="群号1 群号2"               # 不要群聊就留空
```

然后：

```bash
./deploy/install.sh --dry-run    # 先看它要干什么
./deploy/install.sh --no-start   # 装，但先不启动（等导入数据）
```

`--no-start` 很重要：先让文件就位，再导入老数据，最后启动，避免服务用空配置跑起来。

## 4. 新机器：导入数据

```bash
./deploy/migrate-import.sh ~/qqbot-migrate-YYYYmmdd-HHMM.tar.gz
```

会先校验 sha256 和包内路径，备份现有配置，再解压到 `$HOME`。

> 换过用户名的机器：导入后检查 `qq-dsh-bot/` 里的脚本路径是否还是 `/home/ubuntu`。
> `install.sh` 会按 `BOT_HOME` 重写脚本，所以正确顺序是「先 install，再 import」。

## 5. 启动与扫码

```bash
# 启动（NapCat 先起，dsh 再连）
./deploy/install.sh --only 80 --yes

# 看 NapCat 是否在等扫码
systemctl --user status napcat.service --no-pager
tail -f ~/napcat-setup/napcat.log
```

扫码两种方式：

```bash
# 终端里直接扫（推荐，SSH 里也能扫）
~/tts-venv/bin/python ~/qq-dsh-bot/qr-term.py

# 或者把二维码图片拉回本地看
scp ubuntu@新机器:~/Napcat/opt/QQ/resources/app/app_launcher/napcat/cache/qrcode.png .
```

登录成功后日志里会出现 `OneBot WS Server Started`，`ss -lnt | grep 3001` 能看到端口。

## 6. 验收清单

- [ ] `systemctl --user list-units 'dsh-*' 'qq-*' 'napcat*'` 全是 running
- [ ] `curl -s http://127.0.0.1:3080/` 有响应
- [ ] 私聊机器人发一句，能回；人设没串
- [ ] 群里 @ 它能回；不 @ 不说话
- [ ] `~/agent/bin/agent --status` 正常，之前的项目还在
- [ ] `systemctl --user list-timers` 里 daily-restart / persona-bind / monthly / logrotate 都在
- [ ] 重启机器后（`sudo reboot`）服务自己起来（linger 生效）

## 7. 迁移后还要手工做的事

1. **快速登录补丁**：`install.sh` 会自动打；NapCat 升级后要重打：
   `python3 patches/patch-napcat-quicklogin.py`
2. **NapCat WebUI token**：新生成，在 `~/Napcat/opt/QQ/resources/app/app_launcher/napcat/config/webui.json`。
3. **persona / 会话绑定**：`bind-private-persona.sh` 里写死了 persona id 和会话目录。
   如果新机器会话没接上，`/new` 一次让 timer 重新绑定即可。
4. **主动搭话白名单**：确认 `~/qq-dsh-bot/proactive-targets.txt` 是你想要的人。
5. **模型 key**：`~/.dsh-user/dsh-web.env` 里确认 `DEEPSEEK_API_KEY` 有效。

## 8. 回滚

老机器在确认新机器跑通之前不要停、不要释放。真出问题时：

1. 新机器 `systemctl --user stop 'dsh-*' 'qq-*' napcat.service`
2. 老机器 `systemctl --user start napcat.service dsh-web.service`
3. 注意同一个 QQ 不能两边同时在线，先停新机器再起老机器。

## 9. 常见问题

**`install.sh` 说 ONEBOT_TOKEN 是占位符**
`deploy.conf` 没填。`openssl rand -hex 32` 生成一个，NapCat 和 dsh 两端会自动用同一个。

**pnpm install 失败 / 卡住**
国内机器给 npm 配镜像：`pnpm config set registry https://registry.npmmirror.com`。
`dsh-archive-retention` 走的是 GitHub tarball，GitHub 不通时会失败，需要代理。

**补丁打不上：`plugin version changed`**
插件升级了，`patches/apply-onebot-patches.py` 的匹配串要对新版本改。
先 `pnpm list dsh-onebot-qq` 看版本，再对照 `patches/onebot-quote/*.orig`。

**QQ 一直二维码登录 / 被踢**
看 `patches/NAPCAT-QUICK-LOGIN.md`。被 KickedOffLine 后 token 会失效，必须再扫一次。

**服务重启后没了**
`loginctl show-user $USER -p Linger` 要是 `Linger=yes`，否则 SSH 一退 systemd 用户实例就没了。

**会话目录对不上**
老会话目录名带 `--home-ubuntu--`，换家目录就接不上。要么保持 `/home/ubuntu`，要么接受从新会话开始。
