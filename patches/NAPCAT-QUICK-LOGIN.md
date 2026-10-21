# NapCat 掉线自动快速登录补丁

日期：2026-10-21
目的：QQ 被服务端踢下线（KickedOffLine）后，NapCat 重启 Worker 时丢掉 `-q <uin>`，
退化成二维码登录，没人扫码就一直离线。此补丁让 Worker 重启也带上 `-q`，
并配置 WebUI 自动登录账号作为第二道保险。

## 改动

1. `NapCat/opt/QQ/resources/app/app_launcher/napcat/napcat.mjs`
   - 第 83517 行：`await Bg(!1)` → `await Bg(!0)`
   - 第 83530 行：`await Bg(!1, t, e)` → `await Bg(!0, t, e)`
   - 作用：`c2e()` 重启 Worker 时，从主进程 `process.argv` 里解析 `-q` 并传给新 Worker。

2. `NapCat/opt/QQ/resources/app/app_launcher/napcat/config/webui.json`
   - `"autoLoginAccount": ""` → `"autoLoginAccount": "2836148023"`
   - 作用：Worker 启动时若没拿到 `-q`，会走 WebUI 的自动快速登录分支。

## 备份

- `patches/napcat.mjs.bak-20261021213334`
- `patches/webui.json.bak-20261021213334`

恢复：把备份覆盖回原路径，`systemctl --user restart napcat`。

## 验证方式

重启后日志应出现：

```
正在快速登录  2836148023
```

而不是：

```
没有 -q 指令指定快速登录，将使用二维码登录方式
```

## 注意

- 快速登录依赖本地 token（NTQQ LocalLoginInfo）。账号被 **KickedOffLine** 后
  服务端会作废该 token，此时快速登录会报「你的用户身份已失效」，仍须扫码一次。
  扫码成功后 token 才会更新，之后进程重启/网络抖动可以自动登录。
- NapCat 升级会覆盖 `napcat.mjs`，升级后需重新打这两处补丁。
- 如需在 token 失效时也能自动登录，可再配 `NAPCAT_QUICK_PASSWORD`（明文密码）
  或 `NAPCAT_QUICK_PASSWORD_MD5`，但可能触发验证码/新设备验证，不建议。

## 验证记录

- 2026-10-21 21:36:42 扫码，21:36:49 OneBot WS Server Started，登录成功。
- 2026-10-21 21:38:17 重启 napcat 服务，1 秒内自动快速登录成功（未出二维码），
  3001 端口恢复监听，dsh-web 自动重连。
- 登录凭证备份：`qq-dsh-bot/qq-login-backup-20261021-213813/`（权限 700，约 1.1MB）。
  含 login.db + wal/shm、profile_info.db + wal/shm、Login 标记、mmkv、webui.json。
  恢复时把对应文件整套放回原路径（wal/shm 要一起），再重启 napcat。

## 恢复凭证步骤

1. 停服务：`systemctl --user stop napcat`
2. 按备份文件名前缀放回：
   - `global-login.db*` → `~/.config/QQ/global/nt_db/login.db*`
   - `account-profile_info.db*` → `~/.config/QQ/nt_qq_*/nt_db/profile_info.db*`
   - `Login/` → `~/.config/QQ/global/nt_data/Login/`
   - `global-mmkv/` → `~/.config/QQ/global/nt_data/mmkv/`
   - `account-mmkv/` → `~/.config/QQ/nt_qq_*/nt_data/mmkv/`
3. 启动：`systemctl --user start napcat`，观察是否直接快速登录。
