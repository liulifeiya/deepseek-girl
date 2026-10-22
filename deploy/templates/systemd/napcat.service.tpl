[Unit]
Description=NapCat QQ + OneBot 11 (WS 127.0.0.1:@NAPCAT_WS_PORT@)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=@BOT_HOME@/Napcat/opt/QQ
ExecStart=/usr/bin/xvfb-run -a ./qq --no-sandbox --disable-dev-shm-usage --disable-gpu -q @BOT_QQ@
Restart=always
RestartSec=10
KillMode=mixed
StandardOutput=append:@BOT_HOME@/napcat-setup/napcat.log
StandardError=append:@BOT_HOME@/napcat-setup/napcat.log

[Install]
WantedBy=default.target
