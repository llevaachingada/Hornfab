# Driver source correction

Checked 2026-11-15: FaitalPRO's [HF1440 product page](https://faitalpro.com/en/products/HF_Drivers/product_details/index.php?id=502020185) and [manufacturer datasheet](https://faitalpro.com/en/products/HF_Drivers/product_details/datasheet.php?id=502020185), printed 2026-11-04.

The manufacturer specifies a 35.8 mm throat diameter, a radial phase plug and **Combined Exit**. Footnote5 places the exit at the phase-plug end without an adaptation throat. It does not specify a2-degree conical exit. The stated700 Hz minimum crossover is qualified by a12 dB/octave or steeper high-pass filter; published curves use the LTH142 horn.

The repository brief instead specifies radius18 mm and angle2 degrees. Preserve these as the **historical modeling interface**, not newly verified manufacturer geometry. The0.2 mm diameter difference may be a modeling approximation; no manufacturing failure follows from that arithmetic alone. The exit field, physical local tangent/curvature and interface to the owner's actual unit remain unresolved. A smooth uniform source cap and a round mating outline do not reconstruct the phase-plug field. Matching a generated wall to2 degrees proves a model-interface property only. Any corrected driver/source configuration needs a new identity; do not mutate or silently relabel existing recipes, responses or cohorts.

This correction adds a source-validation gate for every family. It does not prescribe a substitute angle or authorize solves.
