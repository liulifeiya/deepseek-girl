# vendor

`napcat-installer.sh` 是 NapCat 官方 rootless 安装脚本的本地副本（从
[NapNeko/NapCat-Installer](https://github.com/NapNeko/NapCat-Installer) 取得），
仅用于 `deploy/steps/70-napcat.sh` 在新机器上装 QQ + NapCat。

- 它自己会从 `github.com/NapNeko/NapCatQQ/releases/latest` 下载 NapCat.Shell.zip，
  从 `qqdl.gtimg.cn` 下载 Linux QQ，许可证归上游所有。
- 上游脚本会更新；要跟进就换掉这个文件，别改内容。
- 不想用这份副本：自己装好 NapCat 后把 `deploy.conf` 的 `WITH_NAPCAT` 设为 0，
  `70-napcat` 只写配置、不装客户端。
