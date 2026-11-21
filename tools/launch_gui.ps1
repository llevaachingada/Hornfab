# Kill any running hornlab-search GUI server, then start a fresh one and open the browser.
# Only processes whose command line is a hornlab-search GUI server are stopped; searches, campaigns
# and solver hosts are never touched.
#
# The match must cover every shape the server is actually started in (fixed 2026-11-20):
#   ...\Scripts\hornlab-search.exe gui            console script used below
#   ...\Scripts\hornlab-search.exe" gui           same, quoted path
#   python -m hornlab_search.gui --port 8765      documented module form (spawns twice: the .venv
#                                                 python.exe is a launcher trampoline + its child)
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$port = 8765
$guiPattern = 'hornlab[-_]search(\.exe)?"?\s+gui\b|hornlab[-_]search\.gui\b|hornlab[-_]search\.cli\s+gui\b'

function Stop-OldGui {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -in @('python.exe', 'pythonw.exe', 'py.exe', 'hornlab-search.exe') -and
            $_.CommandLine -match $guiPattern
        } |
        ForEach-Object {
            Write-Host "Stopping old GUI process $($_.ProcessId)"
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

function Test-PortFree {
    -not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

# Wait (up to 10 s) for the port to actually free up; a half-dead old server is what makes a fresh
# one fail to bind or leaves the browser talking to a stale process.
function Wait-PortFree([int]$seconds = 10) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortFree) { return $true }
        Start-Sleep -Milliseconds 300
    }
    Test-PortFree
}

Stop-OldGui
if (-not (Wait-PortFree)) {
    $held = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
    $owner = Get-CimInstance Win32_Process -Filter "ProcessId=$($held[0].OwningProcess)" -ErrorAction SilentlyContinue
    if ($owner -and $owner.CommandLine -match 'hornlab[-_]search') {
        # Ours, but in an invocation shape the pattern above does not know yet (a new entry point).
        # The port is what we need, so stop it instead of telling the owner to do it by hand.
        Write-Host "Port $port is held by a HornLab process the launcher did not recognise; stopping PID $($owner.ProcessId): $($owner.CommandLine)"
        Stop-Process -Id $owner.ProcessId -Force -ErrorAction SilentlyContinue
    }
    if (-not (Wait-PortFree 5)) {
        $held = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId=$($held[0].OwningProcess)" -ErrorAction SilentlyContinue
        Write-Host "Port $port is still held by PID $($held[0].OwningProcess) ($($owner.Name)): $($owner.CommandLine)" -ForegroundColor Red
        Write-Host "That is not a hornlab-search GUI, so it was left alone. Close it, or run:  hornlab-search gui --port 8766" -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit 1
    }
}

Write-Host "Starting hornlab-search GUI (close this window to stop it)..."
Write-Host "The browser opens once the run index is warm (a few seconds; first load after a restart is the slow one)."
& "$repo\.venv\Scripts\hornlab-search.exe" gui
$rc = $LASTEXITCODE
if ($rc -ne 0) {
    # Never let a startup failure vanish with the window.
    Write-Host "GUI exited with code $rc" -ForegroundColor Red
    Read-Host "Press Enter to close"
}
exit $rc
