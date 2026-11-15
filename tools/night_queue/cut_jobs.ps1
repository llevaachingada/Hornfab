<#
Cut named jobs out of a night that is ALREADY RUNNING (the runner reads its night file once, so editing the file
does nothing). While the queue/runner process -WaitPid is alive, any process whose command line contains one of
-Match strings is killed (with its tree) as soon as it appears; the night runner records it as failed, runs its own
post-job GPU hygiene, and moves on to the next job. Launch detached (launch_detached.ps1). Log: -Log.

Example (2026-11-15: drop night D's Crowe jobs after the BoTorch arms):
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 `
    -Script tools\night_queue\cut_jobs.ps1 -ScriptArgs "-WaitPid 25164 -Match crowe_panel_cli.py -Log runs\nights\cut_d.log"
#>
param(
    [Parameter(Mandatory = $true)][int]$WaitPid,
    [Parameter(Mandatory = $true)][string[]]$Match,
    [string]$Log = "runs\nights\cut_jobs.log",
    [string]$Repo = "C:\Users\hunte\Hrns\hornlab-search"
)
Set-Location $Repo
function Note($m) { "$(Get-Date -Format s) $m" | Out-File -FilePath (Join-Path $Repo $Log) -Append -Encoding utf8 }
Note "cut_jobs start: wait pid $WaitPid; match $($Match -join ', ')"
while (Get-Process -Id $WaitPid -ErrorAction SilentlyContinue) {
    foreach ($p in Get-CimInstance Win32_Process -Filter "Name='python.exe'") {
        $cl = [string]$p.CommandLine
        foreach ($m in $Match) {
            if ($cl -like "*$m*" -and $p.ProcessId -ne $PID) {
                Note "killing pid $($p.ProcessId): $($cl.Substring(0, [Math]::Min(200, $cl.Length)))"
                taskkill /T /F /PID $p.ProcessId | Out-Null
            }
        }
    }
    Start-Sleep -Seconds 5
}
Note "cut_jobs end: pid $WaitPid exited"
