# Night refresher loop: run the repair tool once, then every -EveryMinutes until the queue ends
# or the -Cutoff passes. Never touches a running job; the repair tool itself defers what it cannot
# do mechanically. Run DETACHED (launch_detached.ps1).
param(
    [string]$Night = "",
    [int]$EveryMinutes = 90,
    [string]$Cutoff = ""
)
$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$py = Join-Path $repo ".venv\Scripts\python.exe"
$tool = Join-Path $repo "tools\night_queue\refresh_watchdog.py"
$stamp = (Get-Date).ToString("yyyy-MM-dd")
$log = Join-Path $repo "runs\nights\queue_refresh_$stamp.log"

function Note($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss') $msg"
    Add-Content -Path $log -Value $line
}

$cut = $null
if ($Cutoff) { $hm = $Cutoff.Split(":"); $cut = Get-Date -Hour ([int]$hm[0]) -Minute ([int]$hm[1]) -Second 0 }

Note "refresh loop start (pid $PID): night=$Night every=${EveryMinutes}min cutoff=$Cutoff"
while ($true) {
    if ($cut -and (Get-Date) -ge $cut) { Note "cutoff reached; refresh loop ends"; break }
    # end when the night's queue is no longer live (controller gone and no job running)
    $runner = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match "run_campaign_night" }
    if (-not $runner) {
        Note "night runner not found; refresh loop ends"
        break
    }
    & $py $tool --night $Night 2>&1 | ForEach-Object { Note "repair: $_" }
    # lane-gate poll every 120 s until the next deep repair tick: pause our queue while a FOREIGN
    # holder is solving, resume when free (the gate writes/removes runs/nights/<night>/PAUSE).
    $ticks = [int]($EveryMinutes * 30)   # 120 s per gate tick
    for ($i = 0; $i -lt $ticks; $i++) {
        Start-Sleep -Seconds 120
        if ($cut -and (Get-Date) -ge $cut) { break }
        $r2 = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
            Where-Object { $_.CommandLine -match "run_campaign_night" }
        if (-not $r2) { break }
        & $py $tool --night $Night --gate 2>&1 | ForEach-Object { Note "gate: $_" }
    }
}
Note "refresh loop exit (pid $PID)"
