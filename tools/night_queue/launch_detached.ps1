<#
Start a PowerShell script DETACHED from the calling session, via WMI (Win32_Process.Create). The new process's
parent is WmiPrvSE, so it is outside the Claude Code tool's job object: closing the app or the session does not
kill it (2026-10-27: a night launched from a session shell died at 20:08 when that session ended).

Prints the new process id; check it with Get-CimInstance Win32_Process -Filter "ProcessId=<pid>".
Environment: the new process gets the USER-level environment, not the calling shell's - fine for this repo
(no solver environment variables are needed; checked 2026-10-28).

Example:
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 `
    -Script tools\night_queue\queue.ps1 -ScriptArgs "-Nights my_night -Cutoff 18:00"
#>
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [string]$ScriptArgs = "",
    [string]$Repo = "C:\Users\hunte\Hrns\hornlab-search"
)
$full = if ([System.IO.Path]::IsPathRooted($Script)) { $Script } else { Join-Path $Repo $Script }
if (-not (Test-Path $full)) { Write-Error "script not found: $full"; exit 2 }
$cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$full`" $ScriptArgs"
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cmd; CurrentDirectory = $Repo}
if ($r.ReturnValue -ne 0) { Write-Error "Win32_Process.Create failed: $($r.ReturnValue)"; exit 1 }
"launched pid $($r.ProcessId) at $(Get-Date -Format s): $cmd"
