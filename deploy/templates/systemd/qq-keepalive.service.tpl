[Unit]
Description=QQ keepalive (online status ping every 5min)
After=network-online.target napcat.service

[Service]
Type=simple
Environment=BOT_HOME=@BOT_HOME@
Environment=BOT_QQ=@BOT_QQ@
ExecStart=@BOT_HOME@/.local/node/bin/node @BOT_HOME@/qq-dsh-bot/keepalive.mjs
Restart=always
RestartSec=10
StandardOutput=append:@BOT_HOME@/qq-dsh-bot/keepalive.log
StandardError=append:@BOT_HOME@/qq-dsh-bot/keepalive.log

[Install]
WantedBy=default.target
