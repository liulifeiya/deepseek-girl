[Unit]
Description=Hourly napcat.log rotation check

[Timer]
OnBootSec=10min
OnUnitActiveSec=1h
AccuracySec=1min

[Install]
WantedBy=timers.target
