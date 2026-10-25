# Kill any running hornlab-search GUI server, then start a fresh one and open the browser.
# Only processes whose command line is "hornlab-search ... gui" are stopped; searches, campaigns
# and solver hosts are never touched.
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
Get-CimInstance Win32_Process |
    Where-Object { $_.Name -in @('python.exe', 'hornlab-search.exe') -and $_.CommandLine -match 'hornlab[-_]search(\.exe"?|\.cli)?\s.*\bgui\b' } |
    ForEach-Object {
        Write-Host "Stopping old GUI process $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 1
Write-Host "Starting hornlab-search GUI (close this window to stop it)..."
& "$repo\.venv\Scripts\hornlab-search.exe" gui
