<#
Run several night files back to back, unattended. Launch it DETACHED with launch_detached.ps1 so closing the
Claude app (or its session) cannot kill it, and so Windows idle-sleep cannot stall it.

  - keeps Windows awake while it runs (SetThreadExecutionState ES_CONTINUOUS|ES_SYSTEM_REQUIRED; no setting
    is changed, the hold ends with the process);
  - optionally waits for a running runner first (-WaitPid + -WaitMatch on its command line, so a reused PID
    cannot fool it) - the next night's pre-hygiene KILLS julia.exe, so never start one while another runs;
  - runs tools\run_campaign_night.py on each night in order, each runner's stdout/stderr to
    runs\nights\<night>_runner_{stdout,stderr}.log;
  - starts NO new night after -Cutoff (HH:mm, today), so the queue ends near a known time;
  - never kills anything itself; the runner does hygiene and takes over a dead holder's GPU lock.

Example:
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 `
    -Script tools\night_queue\queue.ps1 `
    -ScriptArgs "-Nights v4_day_H2_hybrids_2026-10-28,v4_day_C_round_throat_2026-10-28 -Cutoff 17:30 -WaitPid 16212 -WaitMatch v4_day_H_hybrids -Log runs\nights\queue_2026-10-28.log"

To CHANGE a queued order: stop only this controller (taskkill /PID <controller>, never /T: its child runner
must keep going) and launch a new one that waits on the runner it left behind (-WaitPid <runner pid>).
A night file a runner already started is read once at start: appending jobs to it does nothing - put them
in a new night file.
#>
param(
    [Parameter(Mandatory = $true)][string]$Nights,      # comma list of night names (runs\nights\<name>.yaml)
    [string]$Cutoff = "",                                # HH:mm - no night starts after this (today)
    [int]$WaitPid = 0,                                   # optional: a runner to wait for first
    [string]$WaitMatch = "",                             # required with WaitPid: text in that process's command line
    [string]$Log = "runs\nights\queue.log",
    [string]$Repo = "C:\Users\hunte\Hrns\hornlab-search"
)
Set-Location $Repo
$logPath = Join-Path $Repo $Log
function Note($m) { "$(Get-Date -Format s) $m" | Out-File -FilePath $logPath -Append -Encoding utf8 }
Add-Type -Namespace W -Name P -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
function Awake { [W.P]::SetThreadExecutionState([uint32]"0x80000001") | Out-Null }
$cut = $null
if ($Cutoff) { $hm = $Cutoff.Split(":"); $cut = Get-Date -Hour ([int]$hm[0]) -Minute ([int]$hm[1]) -Second 0 }
$list = $Nights.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ }
foreach ($n in $list) {
    if (-not (Test-Path (Join-Path $Repo "runs\nights\$n.yaml"))) { Note "ABORT: runs\nights\$n.yaml not found"; exit 2 }
}
Awake
Note "queue start (pid $PID): $($list -join ' -> '); cutoff $Cutoff; wait pid $WaitPid"
if ($WaitPid -gt 0) {
    if (-not $WaitMatch) { Note "ABORT: -WaitPid needs -WaitMatch"; exit 2 }
    while ($true) {
        $p = Get-CimInstance Win32_Process -Filter "ProcessId=$WaitPid" -ErrorAction SilentlyContinue
        if (-not ($p -and $p.CommandLine -match [regex]::Escape($WaitMatch))) { break }
        Awake; Start-Sleep -Seconds 30
    }
    Note "waited-for runner $WaitPid finished"
}
$py = Join-Path $Repo ".venv\Scripts\python.exe"
foreach ($n in $list) {
    if ($cut -and (Get-Date) -ge $cut) { Note "cutoff $Cutoff reached; NOT starting $n or later nights"; break }
    Awake
    Note "starting $n"
    $r = Start-Process -FilePath $py -ArgumentList '-u', 'tools\run_campaign_night.py', '--night', "runs\nights\$n.yaml" `
         -WorkingDirectory $Repo -NoNewWindow -Wait -PassThru `
         -RedirectStandardOutput (Join-Path $Repo "runs\nights\${n}_runner_stdout.log") `
         -RedirectStandardError (Join-Path $Repo "runs\nights\${n}_runner_stderr.log")
    Note "finished $n (exit $($r.ExitCode))"
}
[W.P]::SetThreadExecutionState([uint32]"0x80000000") | Out-Null
Note "queue done; keep-awake released"
