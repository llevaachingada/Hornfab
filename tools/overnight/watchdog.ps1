# Overnight GPU watchdog (no Claude usage needed). Runs beside a queue script:
#  - keeps Windows awake while the queue runs;
#  - if a GPU job holds runs\.gpu.lock but nothing under runs\ was written for $StallMin minutes,
#    kills the innermost stalled `search` process tree (else the lock holder's tree), so the queue
#    (or the campaign) records a failure and continues; the queue runs gpu-clean between steps;
#  - logs every action to runs\overnight\watchdog.log; exits when the queue process is gone.
param([int]$QueuePid, [int]$StallMin = 30, [int]$PollSec = 120)
Set-Location C:\Users\hunte\Hrns\hornlab-search
$log = "runs\overnight\watchdog.log"
function Log($m) { "$(Get-Date -Format s) $m" | Out-File -Append -Encoding utf8 $log }
Add-Type -Namespace W -Name P -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
Log "watchdog start: queue pid $QueuePid, stall $StallMin min"
while (Get-Process -Id $QueuePid -ErrorAction SilentlyContinue) {
  [W.P]::SetThreadExecutionState([uint32]"0x80000001") | Out-Null   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
  Start-Sleep $PollSec
  if (-not (Test-Path runs\.gpu.lock)) { continue }
  $newest = Get-ChildItem runs -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -ne ".gpu.lock" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $idle = ((Get-Date) - $newest.LastWriteTime).TotalMinutes
  if ($idle -lt $StallMin) { continue }
  $lock = Get-Content runs\.gpu.lock -Raw | ConvertFrom-Json
  $procs = Get-CimInstance Win32_Process
  $kids = @($lock.pid); $all = @()
  while ($kids.Count) { $all += $kids; $kids = @($procs | Where-Object { $kids -contains $_.ParentProcessId } | ForEach-Object { $_.ProcessId }) }
  $search = $procs | Where-Object { ($all -contains $_.ProcessId) -and $_.ProcessId -ne $lock.pid -and $_.CommandLine -match "hornlab.search.* search " } |
            Select-Object -Last 1
  $target = if ($search) { $search.ProcessId } else { $lock.pid }
  Log ("STALL: nothing written for {0:N0} min (newest {1}); killing tree of pid {2} (lock: {3})" -f $idle, $newest.FullName, $target, $lock.command)
  taskkill /PID $target /T /F 2>&1 | ForEach-Object { Log "  $_" }
  Start-Sleep 60
}
[W.P]::SetThreadExecutionState([uint32]"0x80000000") | Out-Null
Log "watchdog exit: queue finished"
