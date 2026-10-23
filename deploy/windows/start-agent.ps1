# Start the always-on agent worker.
. "$PSScriptRoot\env.ps1"
$env:AGENT_HOME = 'C:\Users\Administrator\agent'
$env:AGENT_WORKDIR = 'C:\Users\Administrator'
$env:AGENT_DSH_BIN = 'C:\Users\Administrator\AppData\Roaming\npm\dsh.cmd'
$py = 'C:\Program Files\Python312\python.exe'
$log = 'C:\Users\Administrator\agent\logs\service.log'
& $py 'C:\Users\Administrator\agent\worker.py' *>> $log
