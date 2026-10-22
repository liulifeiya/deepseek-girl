[Unit]
Description=Timer: monthly memory consolidation on the 1st at 05:00

[Timer]
OnCalendar=*-*-01 05:00:00
Persistent=true

[Install]
WantedBy=timers.target
