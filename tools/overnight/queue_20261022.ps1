# Overnight GPU queue 2026-10-22 -> 2026-10-23 ~17:00. One job at a time; gpu-clean between steps.
# No step STARTS after $cutoff, so the GPU is idle and clean by ~17:00.
$ErrorActionPreference = "Continue"
Set-Location C:\Users\hunte\Hrns\hornlab-search
$hs = ".\.venv\Scripts\hornlab-search.exe"
$log = "runs\overnight\queue_20261022.log"
$cutoff = Get-Date "2026-10-23 15:45"
function Step($name, [string[]]$a) {
  if ((Get-Date) -gt $cutoff) { "=== $(Get-Date -Format s) SKIP $name (past start cutoff)" | Tee-Object -Append $log; return }
  "=== $(Get-Date -Format s) START $name : $($a -join ' ')" | Tee-Object -Append $log
  & $hs gpu-clean 2>&1 | Tee-Object -Append $log
  & $hs @a 2>&1 | Where-Object { $_ -notmatch "Statistics on Transfer" } | Tee-Object -Append $log
  "=== $(Get-Date -Format s) END $name exit $LASTEXITCODE" | Tee-Object -Append $log
  & $hs gpu-clean 2>&1 | Tee-Object -Append $log
}
# phase 1: axi re-screen at epw 8, then compare tiers (item E)
Step "axi-screen-epw8" @("campaign","--brief","examples\briefs\axi_90x90_1in.yaml","--families","conical,exponential,hypex,tractrix,osse_axi,blend_osse_tractrix,blend_conical_exponential,perturbed_tractrix","--tier","screen")
Step "axi-compare" @("campaign","--brief","examples\briefs\axi_90x90_1in.yaml","--families","osse_axi,blend_osse_tractrix,hypex,exponential","--tier","compare")
Step "hifi-compare" @("campaign","--brief","examples\briefs\hifi_90x60_1in.yaml","--families","perturbed_osse_hv,hyb_osse_h_hypex_v,rosse_baseline","--tier","compare")
# phase 2: OSSE records for the surrogate gates, two fresh CMA seeds
Step "osse-topup-s1" @("search","--config","examples\osse_baseline.yaml","--cma-seed","4101","--budget","950")
Step "osse-topup-s2" @("search","--config","examples\osse_baseline.yaml","--cma-seed","4102","--budget","950")
# phase 3: FREEFORM data, 150-evaluation searches with fresh seeds until the cutoff
$seed = 5101
while ((Get-Date) -lt $cutoff) { Step "sculpt-$seed" @("search","--config","examples\freeform_sculpt.yaml","--cma-seed","$seed","--budget","150"); $seed++ }
"=== $(Get-Date -Format s) QUEUE DONE" | Tee-Object -Append $log
nvidia-smi --query-gpu=memory.used --format=csv | Tee-Object -Append $log
