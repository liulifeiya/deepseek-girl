[Unit]
Description=Rotate napcat.log when it grows past 10M

[Service]
Type=oneshot
ExecStart=/usr/sbin/logrotate -s @DSH_HOME@/logrotate.state @DSH_HOME@/logrotate-napcat.conf
