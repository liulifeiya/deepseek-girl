[Unit]
Description=DSH Web (QQ bot backend)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=@BOT_HOME@
Environment=DSH_HOME=@DSH_HOME@
Environment=PATH=@BOT_HOME@/.local/node/bin:@BOT_HOME@/.local/share/pnpm:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=@DSH_HOME@/dsh-web.env
ExecStart=@BOT_HOME@/.local/share/pnpm/dsh web --host 127.0.0.1 --port @DSH_PORT@ --no-open
ExecStartPost=/bin/sh -c '@BOT_HOME@/qq-dsh-bot/patches/bind-private-persona.sh >/dev/null 2>&1 &'
Restart=always
RestartSec=5
StandardOutput=append:@BOT_HOME@/qq-dsh-bot/dsh-web.log
StandardError=append:@BOT_HOME@/qq-dsh-bot/dsh-web.log

[Install]
WantedBy=default.target
