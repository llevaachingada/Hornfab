# NOTES FOR SENIOR - resolved blocks

Rotated from NOTES_FOR_SENIOR.md on 2026-10-30 (owner-authorized); the blocks below are unchanged.

## 2026-10-12  task-06  RESOLVED HERE, please confirm: "-6 dB" is implemented as HALF PRESSURE (-6.0206 dB), not -6.0000 dB
What I was doing: beamwidth_deg against contract tests 1 and 2 (cardioid reads 180.0, dipole reads 120.0, both to 0.05 deg).
What happened: the orchestrator addendum suggested an epsilon of 1e-3 dB around a strict -6.0 dB threshold. That cannot work: (1+cos t)/2 is 20*log10(0.5) = -6.0206 dB at +-90 deg, which is 0.0206 dB below -6.0, i.e. 20x outside a 1e-3 dB epsilon. A strict -6.0 reads the cardioid 179.73 and the dipole 119.83 (both fail the 0.05 tolerance).
What I did: polar._threshold_db maps the conventional labels to their exact amplitude ratios: drop_db=6.0 -> 20*log10(0.5) (half pressure), drop_db=3.0 -> 10*log10(0.5) (half power); any other value is taken literally. No tolerance was loosened, the result is continuous in the pattern (no snapping), and every contract case is exact on any grid. A near-threshold epsilon of ~0.025 dB with snapping was the alternative; I rejected it because it is discontinuous and grid dependent (the piston cases at a 2.5 deg grid would see up to 0.12 deg snap error).
What I need decided: confirm 01_CONTRACTS section 10 "-6 dB" means p = 0.5 (it must, for its own cardioid/dipole numbers). Every later beamwidth in the project inherits this.

