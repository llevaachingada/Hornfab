# 25 x 2 solve queue for the two look cells (2026-11-15).
# Refuses to start while another live process holds runs/.gpu.lock.
# Run from the repo root: powershell -ExecutionPolicy Bypass -File runs\2026-11-15_25x2\run_25x2.ps1
$ErrorActionPreference = "Stop"
$root = "C:\Users\hunte\Hrns\hornlab-search"
Set-Location $root
$lock = Join-Path $root "runs\.gpu.lock"
if (Test-Path -LiteralPath $lock) {
    $info = Get-Content -LiteralPath $lock -Raw | ConvertFrom-Json
    $holder = Get-Process -Id ([int]$info.pid) -ErrorAction SilentlyContinue
    if ($holder) {
        Write-Output "GPU lock is held by pid $($info.pid) ($($info.command)); refusing to start."
        exit 3
    }
    Write-Output "GPU lock is stale (pid $($info.pid) is gone); gpu-clean will clear it."
}
$env:OMP_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"
$env:VECLIB_MAXIMUM_THREADS = "1"
$env:HORNLAB_BEAT_WORKER_DIR = "C:\Users\hunte\Hrns\hornlab-search\runs\lanes\gpu\workers"
$logdir = Join-Path $root "runs\2026-11-15_25x2"
New-Item -ItemType Directory -Force -Path $logdir | Out-Null
$cells = @(
    @{ id = "section_home_s1234"; seed = 1234; config = "examples\typologies\rolled_family_2026-11-15\rf__section_axial_home_v7.yaml" },
    @{ id = "section_home_s5678"; seed = 5678; config = "examples\typologies\rolled_family_2026-11-15\rf__section_axial_home_v7.yaml" },
    @{ id = "squarex_s1234"; seed = 1234; config = "examples\typologies\home_landscape_2026-11-15\hl__crowe_x_square_v7.yaml" },
    @{ id = "squarex_s5678"; seed = 5678; config = "examples\typologies\home_landscape_2026-11-15\hl__crowe_x_square_v7.yaml" }
)
foreach ($c in $cells) {
    .venv\Scripts\python.exe -m hornlab_search.cli gpu-clean --lane gpu 2>&1 |
        Tee-Object -FilePath (Join-Path $logdir ("pre_" + $c.id + ".log"))
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    .venv\Scripts\python.exe -m hornlab_search.cli search `
        --config $c.config --mode screen --budget 25 --cma-seed $c.seed `
        --cache-dir scratch\2026-11-15_25x2\cache `
        --dataset-dir scratch\2026-11-15_25x2\dataset 2>&1 |
        Tee-Object -FilePath (Join-Path $logdir ($c.id + ".log"))
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
.venv\Scripts\python.exe -m hornlab_search.cli gpu-clean --lane gpu 2>&1 |
    Tee-Object -FilePath (Join-Path $logdir "post_clean.log")
Write-Output "25x2 queue complete; see $logdir"
