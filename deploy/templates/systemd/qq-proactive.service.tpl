[Unit]
Description=QQ proactive greeting (one message per run)

[Service]
Type=oneshot
Environment=BOT_HOME=@BOT_HOME@
EnvironmentFile=@DSH_HOME@/dsh-web.env
ExecStart=/usr/bin/python3 @BOT_HOME@/qq-dsh-bot/proactive.py --send
