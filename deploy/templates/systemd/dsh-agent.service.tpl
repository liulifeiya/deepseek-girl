[Unit]
Description=DSH 常挂智能体（任务队列 worker）
After=network-online.target

[Service]
Type=simple
WorkingDirectory=@BOT_HOME@/agent
Environment=AGENT_HOME=@BOT_HOME@/agent
Environment=DSH_HOME=@DSH_HOME@
Environment=PATH=@BOT_HOME@/.local/node/bin:@BOT_HOME@/.local/share/pnpm:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=@DSH_HOME@/dsh-web.env
ExecStart=/usr/bin/python3 @BOT_HOME@/agent/worker.py
Restart=always
RestartSec=5
StandardOutput=append:@BOT_HOME@/agent/logs/service.log
StandardError=append:@BOT_HOME@/agent/logs/service.log

[Install]
WantedBy=default.target
