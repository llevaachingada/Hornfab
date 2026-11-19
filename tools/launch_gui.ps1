# Kill any running hornlab-search GUI server, then start a fresh one and open the browser.
# Only processes whose command line is "hornlab-search ... gui" are stopped; searches, campaigns
# and solver hosts are never touched.
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$port = 8765

Get-CimInstance Win32_Process |
    Where-Object { $_.Name -in @('python.exe', 'hornlab-search.exe') -and $_.CommandLine -match 'hornlab[-_]search(\.exe"?|\.cli)?\s.*\bgui\b' } |
    ForEach-Object {
        Write-Host "Stopping old GUI process $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

# Wait (up to 10 s) for the port to actually free up; a half-dead old server is what makes a fresh
# one fail to bind or leaves the browser talking to a stale process.
$deadline = (Get-Date).AddSeconds(10)
while ((Get-Date) -lt $deadline) {
    $held = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $held) { break }
    Start-Sleep -Milliseconds 300
}
$held = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($held) {
    $owner = Get-CimInstance Win32_Process -Filter "ProcessId=$($held[0].OwningProcess)" -ErrorAction SilentlyContinue
    Write-Host "Port $port is still held by PID $($held[0].OwningProcess) ($($owner.Name)): $($owner.CommandLine)" -ForegroundColor Red
    Write-Host "That is not a hornlab-search GUI, so it was left alone. Close it, or run:  hornlab-search gui --port 8766" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
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
