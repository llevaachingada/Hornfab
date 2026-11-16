# BO GUI evidence â€” 2026-11-15

Read-only screenshots of the new BO study panels on the real `bo_s31001` study
(`runs/bo_vs_cma_2026-11-15/bo_s31001`, package `f269f257â€¦`, objective v7). The app was served
from the development worktree (`bogui-wt`) with the canonical `runs/` folder; no study was
started, changed, or re-solved for these images.

## Pages

- `execute-*` â€” Run budget, convergence (best recorded J vs solve index; BO line), and the
  comparison endpoint table. Trust region / Pareto are correctly absent while the policy is
  scalar.
- `explain-*` â€” predicted-vs-measured calibration (1 point; the old run predates per-proposal
  persistence), knob sensitivity (missing; hyperparameters were not recorded then), and the
  design-space PCA.
- `compare-*` â€” `#/analysis/compare-methods` from the declarative
  `tools/analysis/specs/bo_method_board_2026-11-15.yaml`; shows the BO arm and the completed CMA
  arm; the verdict is **incomplete** because the remaining arms/verify are still running.

## Screenshots

| File | Page | Width | Theme |
|---|---|---|---|
| `execute-desktop-light.png` | execute | 1440 | light |
| `execute-desktop-dark.png` | execute | 1440 | dark |
| `execute-phone-light.png` | execute | 500 | light |
| `execute-phone-dark.png` | execute | 500 | dark |
| `explain-desktop-light.png` | explain | 1440 | light |
| `explain-desktop-dark.png` | explain | 1440 | dark |
| `explain-phone-light.png` | explain | 500 | light |
| `explain-phone-dark.png` | explain | 500 | dark |
| `compare-desktop-light.png` | compare methods | 1440 | light |
| `compare-desktop-dark.png` | compare methods | 1440 | dark |
| `compare-phone-light.png` | compare methods | 500 | light |
| `compare-phone-dark.png` | compare methods | 500 | dark |

Chrome headless enforces a minimum layout width near 500 CSS px; the 500 px images are the
narrowest honest phone-width evidence this harness can produce (the 390 px capture crops the
500 px layout rather than reflowing it).

## Regenerate

The development server (read-only; canonical data, worktree code):

```python
# C:\Users\hunte\AppData\Local\Temp\opencode\bo_gui_dev_server.py
App(repo, runs=repo / "runs", study_service=StudyService(repo / "runs/bo_vs_cma_2026-11-15/bo_s31001"))
```

Screenshots (Chrome headless):

```powershell
chrome --headless=new --disable-gpu --no-sandbox --hide-scrollbars `
  --virtual-time-budget=15000 --window-size=1440,2400 `
  --screenshot=execute-desktop-light.png `
  "http://127.0.0.1:8811/?theme=light#/analysis/study/66ab47f9b47e45a68791dda68ef777b5/execute?root=c9d390ce"
```

`?theme=light|dark` is read by the app's boot script before the hash route. Same-environment
screenshots are regression evidence, not cross-machine truth.
