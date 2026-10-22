[Unit]
Description=Timer: proactive QQ greeting at 10:30 / 15:30 / 20:30

[Timer]
OnCalendar=*-*-* 10:30:00
OnCalendar=*-*-* 15:30:00
OnCalendar=*-*-* 20:30:00
RandomizedDelaySec=900
Persistent=false

[Install]
WantedBy=timers.target
