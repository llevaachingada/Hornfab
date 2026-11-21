# 10-inch driver catalog re-verification (R15, 2026-11-21)

**Scope.** Risk R15: the 10-inch catalog YAML fields had not been re-verified against the live
vendor pages. Read-only web check; no file was edited, no solver was run. The committed catalog
values are compared field-by-field with the FaitalPRO product pages.

**Retrieval:** 2026-11-21 03:40:21 -05:00 (America/New_York), live pages fully rendered; no TLS
or prose-only block.

## Sources

- 10PR300 8 Ω: <https://faitalpro.com/en/products/LF_Loudspeakers/product_details/index.php?id=101040110>
- 10PR320 8 Ω: <https://faitalpro.com/en/products/LF_Loudspeakers/product_details/index.php?id=101040140>

## Result

Every numeric T/S and mechanical field in `examples/systems/driver_ts/faitalpro_10pr300.yaml`,
`faitalpro_10pr320.yaml` and the matching `driver_geometry/` files matches the live page:
Re 5.4/5.3 Ω, Le 0.6/0.57 mH, Bl 14.1/13.5 N/A, Sd 348/347 cm², Xmax 4.92/7.37 mm, P_AES 300 W,
Fs 60/48 Hz, Qms 5.8/4.6, Mms 28.2/35.0 g, Mmd 20.0/27.7 g, Cms 0.25/0.31 mm/N, Vas 42.2/52.7 L,
Rms 1.8/2.3 kg/s, cutout 232/230 mm, depth 115.3/110 mm, OD 261 mm, sensitivity 98/96 dB.
The notes-only fields also match: bolt circle 246 mm, flange/gasket 12.2/12 mm, net air volume
1.3 dm³, Xdamage 14/17 mm, Zmin 6.4 Ω, Qes 0.29/0.31, Qts 0.28/0.29, EBP 207/155 Hz, surround
M-Roll/Triple Roll.

Two **label** conventions are derived, not vendor wording, and are correct as recorded:

- `sens_db_2v83` is the vendor's "1 W/1 m" value re-expressed at 8 Ω (1 W = 2.83 V).
- `Vad` is the vendor's "NET Air Volume filled by loudspeaker" (1.3 dm³), not a vendor-printed
  symbol.

One separate prose defect was found outside the system YAMLs:
`examples/drivers/faital_10pr300.yaml` (C8 schema) says the 10PR300 surround is "triple roll";
the live 10PR300 page says **M-Roll** (Triple Roll belongs to the 10PR320). The numeric C8 values
match. This is a comment/prose fix for a later catalog pass; it is not part of the system screen
inputs, and changing it would not alter any screen hash.

## Conclusion

R15 is closed on the live pages: no catalog numeric value needs correction, and no YAML edit is
required. The derived labels are documented here; the C8 prose error is recorded for a future
comment-only fix. The system screen `input_sha256` values remain valid because no catalog file was
edited.
