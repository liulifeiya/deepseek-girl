[Unit]
Description=Monthly memory consolidation (dsh headless)

[Service]
Type=oneshot
WorkingDirectory=@BOT_HOME@
Environment=DSH_HOME=@DSH_HOME@
EnvironmentFile=@DSH_HOME@/dsh-web.env
ExecStart=/bin/bash -c '@BOT_HOME@/.local/share/pnpm/dsh headless "$(cat @BOT_HOME@/qq-dsh-bot/monthly-prompt.txt)" >> @BOT_HOME@/qq-dsh-bot/monthly.log 2>&1'
