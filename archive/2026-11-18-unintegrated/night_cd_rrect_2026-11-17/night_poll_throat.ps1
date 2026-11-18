# HornLab throat watcher: 15-minute scheduled task (HornLabThroatPhase1Poll).
# Tracks Phase 1 (7 runs, already complete) and Phase 2 (2 epw8 runs). Read-only status;
# writes markers PHASE1/PHASE2_DONE.txt and appends to poll_throat.log.
$Repo = 'C:\Users\hunte\Hrns\hornlab-search'
$Night = 'cd_rrect_2026-11-17'
$NightDir = Join-Path $Repo "runs\nights\$Night"
$Log = Join-Path $NightDir 'poll_throat.log'
$Ids1 = @('throat_hv_run_B_ctl','throat_hv_run_B_o00','throat_hv_run_B_o25',
          'throat_hv_run_B_o50','throat_hv_run_B_o75','throat_hv_run_A_r15',
          'throat_hv_run_A_r20')
$Ids2 = @('throat_hv_p2_B_o50_epw8','throat_hv_p2_B_o00_epw8')

$now = Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'
$lines = @("== $now poll")

$statePath = Join-Path $NightDir 'queue_state.json'
if (Test-Path $statePath) {
    try {
        $s = Get-Content $statePath -Raw | ConvertFrom-Json
        $lines += ("queue_state: state={0} running={1} done={2} pending={3}" -f $s.state, $s.running, $s.done.Count, $s.pending.Count)
    } catch { $lines += "queue_state: unreadable" }
} else { $lines += "queue_state: MISSING" }

$summaryPath = Join-Path $NightDir 'summary.jsonl'
$rows = @()
if (Test-Path $summaryPath) {
    foreach ($ln in Get-Content $summaryPath) {
        if (-not $ln.Trim()) { continue }
        try { $r = $ln | ConvertFrom-Json } catch { continue }
        $rows += $r
    }
}
function Report-Ids($ids, $tag) {
    $present = 0
    foreach ($id in $ids) {
        $hit = $null
        foreach ($row in $rows) { if ($row.id -eq $id) { $hit = $row } }
        if ($hit) {
            $present++
            $script:lines += ("{0}: exit={1} status={2} bestJ={3} evals={4}" -f $id, $hit.exit_code, $hit.status, $hit.best_J, $hit.evals_ndjson)
        } else {
            $script:lines += ("{0}: pending" -f $id)
        }
    }
    $script:lines += ("{0}: {1}/{2} summaries" -f $tag, $present, $ids.Count)
    return $present
}
$p1 = Report-Ids $Ids1 'phase1'
$p2 = Report-Ids $Ids2 'phase2'
$lines += ("runner_like_processes: {0}" -f ((Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'run_campaign_night|queue\.ps1' } | Measure-Object).Count))
$lines | Add-Content -Path $Log -Encoding UTF8

if ($p1 -ge 7 -and -not (Test-Path (Join-Path $NightDir 'THROAT_PHASE1_DONE.txt'))) {
    @("THROAT PHASE 1 COMPLETE $now - all 7 throat_hv_run_* jobs have summary rows.") +
      $lines | Set-Content -Path (Join-Path $NightDir 'THROAT_PHASE1_DONE.txt') -Encoding UTF8
}
if ($p2 -ge 2 -and -not (Test-Path (Join-Path $NightDir 'THROAT_PHASE2_DONE.txt'))) {
    @("THROAT PHASE 2 COMPLETE $now - both epw8 runs have summary rows.",
      "GATE: Phase 3 runs only if (5.9484 - best_B) > max |dJ| of the two epw8 pairs.",
      "best_B Phase 1 = B_o50 J 5.69735 (improvement over B_ctl = 0.25104).",
      "Job line if the gate passes: see docs/evidence/throat_hv_2026-11-18/LOCAL_RESULTS_2026-11-18_part3.md") +
      $lines | Set-Content -Path (Join-Path $NightDir 'THROAT_PHASE2_DONE.txt') -Encoding UTF8
}
