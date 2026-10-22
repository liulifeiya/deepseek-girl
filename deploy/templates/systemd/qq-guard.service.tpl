[Unit]
Description=QQ guard (probe, heartbeat, auto-restart NapCat, recovery notice)
After=network-online.target napcat.service
Wants=napcat.service

[Service]
Type=simple
Environment=BOT_HOME=@BOT_HOME@
Environment=BOT_QQ=@BOT_QQ@
Environment=ADMIN_QQ=@ADMIN_QQ@
ExecStart=@BOT_HOME@/.local/node/bin/node @BOT_HOME@/qq-dsh-bot/guard.mjs
Restart=always
RestartSec=10
StandardOutput=append:@BOT_HOME@/qq-dsh-bot/guard.log
StandardError=append:@BOT_HOME@/qq-dsh-bot/guard.log

[Install]
WantedBy=default.target
