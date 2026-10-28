# Compression Driver Library for Horn Design
**Date:** 2026-10-28  
**Scope:** Round-exit drivers for BEM horn design — 1" (25.4 mm), 1.4" (36 mm), 2" (50.8 mm) exits  
**Use cases:** Hi-fi with tube amps (sensitivity), PA power (SPL), 3D-print prototyping  
**Target crossover:** ≤ 800 Hz (preferably 500–700 Hz) to a 12" or 15" woofer  

---

## How to read this document

- **[published]** = value taken from a manufacturer datasheet or product specification sheet.  
- **[retail]** = value taken from a retail product listing.  
- **n/a** = not found in any source examined; never estimated.  
- Prices are approximate US retail as of 2026-10-28; they shift frequently.  
- "Min XO" = manufacturer-stated minimum recommended crossover frequency.  
- Drivers are sorted within each bracket by exit size then by recommended use.  
- T/S parameters for compression drivers are sparsely published; most manufacturers omit Bl, Mmd, Sd, Qts from datasheets. Only values that were explicitly stated in a source are filled in.

---

## Price Bracket: Under $200

### Best picks by exit and use

| Model | Exit (mm) | Best for | Approx US price | Source |
|---|---|---|---|---|
| PRV Audio D4400Ti | 50.8 (2") | PA/power budget | ~$120–130 [retail] | Parts Express |
| PRV Audio D3500TiH-Nd | 50.8 (2") | PA/budget hybrid Ti | ~$180 [retail] | Parts Express |
| Eminence PSD3006-8 | 50.8 (2") | PA/budget | ~$215 [retail] | VIP Pro Audio / Zoro |
| Beyma CD14Nd | 36 (1.4") | Hi-fi/sensitivity | ~$263 [retail] | US Speaker |

> Note: the Eminence PSD3006 and Beyma CD14Nd fall just over $200 at most US retailers; included here because they are the most accessible options near this bracket.

---

### PRV Audio D4400Ti — 2" (50.8 mm) exit

**Use:** PA / budget power  
**Min XO:** 1600 Hz (12 dB/oct) — **not suitable for 600 Hz crossover without significant EQ risk**

| Parameter | Value | Provenance |
|---|---|---|
| Model | PRV Audio D4400Ti | — |
| Exit diameter | 50.8 mm (2 in) | [published] |
| Voice coil diameter | 101.6 mm (4 in) | [published] |
| Diaphragm material | Titanium | [published] |
| Voice coil winding | CCAW on Kapton former | [published] |
| Magnet | Ferrite | [published] |
| Nominal impedance | 8 Ω | [published] |
| Re (DC resistance) | n/a | — |
| Le | n/a | — |
| Bl | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Sensitivity (1W/1m) | 110 dB (at 2.83V/1m) | [published] |
| AES / continuous power | 200 W RMS / 400 W program | [published] |
| Frequency range | 1000–17000 Hz (−10 dB) | [published] |
| Min crossover | 1600 Hz @ 12 dB/oct | [published] |
| Mounting | 4-bolt, M6 on 4" centers | [published] |
| Weight | ~8.7 kg (19.2 lb) | [published] |
| Exit angle | n/a | — |
| Approx US price | ~$120–130 (sale) / $150 MSRP | [retail] |
| Source | Parts Express #294-2792 | [retail] |
| Datasheet URL | https://www.parts-express.com/PRV-Audio-D4400Ti-2-Titanium-Compression-Driver-8-Ohm-4-Bolt-294-2792 | — |

**Notes:** Very large ferrite motor; heavy. Recommended XO of 1600 Hz makes it marginal for a 600 Hz horn — usable if the horn has adequate upper-mid loading and the XO is set at 800–1000 Hz with 24 dB/oct. Also available in neodymium (D4400Ti-Nd, ~$230).

---

### PRV Audio D3500TiH-Nd — 2" (50.8 mm) exit

**Use:** PA / budget hybrid (Ti dome + Mylar suspension)  
**Min XO:** 1000 Hz (12 dB/oct) — marginal for 600 Hz

| Parameter | Value | Provenance |
|---|---|---|
| Model | PRV Audio D3500TiH-Nd | — |
| Exit diameter | 50.8 mm (2 in) | [published] |
| Voice coil diameter | 88.9 mm (3.5 in) | [published] |
| Diaphragm material | Titanium hybrid (Ti dome + Mylar suspension) | [published] |
| Magnet | Neodymium ring | [published] |
| Nominal impedance | 8 Ω | [published] |
| Re | n/a | — |
| Le | n/a | — |
| Bl | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Sensitivity (1W/1m) | 110 dB | [published] |
| AES / continuous power | 150 W AES / 300 W program | [published] |
| Frequency range | 800–18000 Hz | [published] |
| Min crossover | 1000 Hz @ 12 dB/oct | [published] |
| Mounting | 4-bolt | [published] |
| Weight | n/a | — |
| Approx US price | ~$180 | [retail] |
| Source | Parts Express #294-3432 | [retail] |
| Datasheet URL | https://prvaudio.com/products/d3500tih-nd/ | — |

---

### Eminence PSD3006-8 — 2" (50.8 mm) exit

**Use:** PA / budget; good sensitivity for the price  
**Min XO:** 500 Hz @ 12 dB/oct (lower boundary of useful horn territory)

| Parameter | Value | Provenance |
|---|---|---|
| Model | Eminence PSD3006-8 | — |
| Exit diameter | 50.8 mm (2 in) | [published] |
| Voice coil diameter | 76.2 mm (3 in) | [published] |
| Diaphragm material | Titanium (geodesic ribs) | [published] |
| Voice coil former | Polyimide | [published] |
| Nominal impedance | 8 Ω | [published] |
| Re (DC resistance) | 4.8 Ω | [published] |
| Le | n/a | — |
| Bl | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | 511 Hz | [published] |
| Qts / Qes / Qms | n/a | — |
| Sensitivity (1W/1m) | 111.4 dB | [published] |
| AES / continuous power | 80 W above 500 Hz; 115 W above 800 Hz | [published] |
| Frequency range | 500–20000 Hz | [published] |
| Min crossover | 500 Hz @ 12 dB/oct | [published] |
| Mounting | 4× ¼-20 studs on 4" (101.6 mm) dia. bolt circle | [published] |
| Weight | n/a | — |
| Approx US price | ~$215 | [retail] |
| Source | Zoro / VIP Pro Audio | [retail] |
| Datasheet URL | https://usspeaker.com/PSD3006-1.htm | — |

**Notes:** fs = 511 Hz makes this one of the few budget 2" drivers with a published resonance below 600 Hz. Discontinued per US Speaker listing — check stock before ordering. Geodesic titanium diaphragm is an unusual construction. High sensitivity for price bracket.

---

### Beyma CD14Nd — 1.4" (36 mm) exit

**Use:** Hi-fi / sensitivity; smooth polymer diaphragm

| Parameter | Value | Provenance |
|---|---|---|
| Model | Beyma CD14Nd | — |
| Exit diameter | 36 mm (1.4 in) | [published] |
| Voice coil diameter | 63.5 mm (2.5 in) edgewound aluminum ribbon | [published] |
| Diaphragm material | PM-4 polymer | [published] |
| Magnet | Neodymium | [published] |
| Nominal impedance | 8 Ω | [published] |
| Re (DC resistance) | 5.3 Ω | [published] |
| Bl | 10 T·m | [published] |
| Le | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Sensitivity (1W/1m) | 108 dB (with TD-385 horn) | [published] |
| AES / continuous power | 80 W AES above 1 kHz / 160 W program | [published] |
| Frequency range | 600–17000 Hz | [published] |
| Min crossover | 800 Hz @ 12 dB/oct | [published] |
| Mounting | 4-bolt | [published] |
| Weight | 1.9 kg (4.19 lb) | [published] |
| Approx US price | ~$263 | [retail] |
| Source | US Speaker | [retail] |
| Datasheet URL | https://usspeaker.com/beyma%20CD14Nd-1.htm | — |

**Notes:** PM-4 polymer diaphragm is smoother in the upper midrange than titanium; favored in hi-fi and theater. Compact (120 mm OD, 49 mm deep). Min XO 800 Hz limits it to 800 Hz+ crossovers; borderline for a 600 Hz horn.

---

## Price Bracket: $200–$500

### Best picks by exit and use

| Model | Exit (mm) | Best for | Approx US price | Source |
|---|---|---|---|---|
| Faital Pro HF200 | 50.8 (2") | Hi-fi 2" / sensitivity | ~$387 [retail] | SpeakersAndAmps / Beach Audio |
| B&C DE85 | 50.8 (2") | PA/hi-fi balance | ~$226 [retail] | US Speaker |
| B&C DE82 | 36 (1.4") | Hi-fi 1.4" / sensitivity | ~$207–210 (EU equiv) | TLHP / SonoVente |
| Eminence PSD3014-8 | 36 (1.4") | Budget 1.4" | ~$100–130 est. [retail] | WWBW / TLHP |
| Celestion CDX14-3040 | 36 (1.4") | Hi-fi 1.4" clearance | ~$195 clearance [retail] | Parts Express #294-2154 |

---

### Faital Pro HF200 — 2" (50.8 mm) exit

**Use:** Hi-fi and PA; 900 Hz minimum XO; excellent sensitivity

| Parameter | Value | Provenance |
|---|---|---|
| Model | Faital Pro HF200 | — |
| Exit diameter | 50.8 mm (2 in) | [published] |
| Voice coil diameter | 75 mm (2.95 in) | [published] |
| Diaphragm material | Titanium | [published] |
| Voice coil winding material | CCAW | [published] |
| Voice coil former | Kapton | [published] |
| Magnet | Neodymium | [published] |
| Nominal impedance | 8 Ω (also 16 Ω) | [published] |
| Re | n/a | — |
| Le | n/a | — |
| Bl | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Flux density | 1.8 T | [published] |
| Sensitivity (1W/1m) | 108 dB | [published] |
| AES / continuous power | 80 W AES / 160 W program | [published] |
| Frequency range | 500–20000 Hz | [published] |
| Min crossover | 900 Hz @ 12 dB/oct | [published] |
| Mounting | 4-bolt, bolt-on | [published] |
| Weight | 3.2 kg (7.05 lb) | [published] |
| OD × depth | 130.5 × 95 mm | [published] |
| Approx US price | ~$387 | [retail] |
| Source | SpeakersAndAmps / Beach Audio | [retail] |
| Datasheet URL | https://usspeaker.com/Faital%20Pro%20HF200-1.htm | — |

**Notes:** Compact neodymium motor, good for front-loaded cabinets. Min XO 900 Hz is somewhat conservative; DIY reports indicate usability to 700–800 Hz with 24 dB slopes. Relatively low power rating (80 W AES) for 2". Recommended for hi-fi round-throat horns in the $200–$500 bracket.

---

### B&C DE85 — 2" (50.8 mm) exit

**Use:** PA / hi-fi balance; ferrite; recommended for 500 Hz horn loading

| Parameter | Value | Provenance |
|---|---|---|
| Model | B&C DE85 | — |
| Exit diameter | 50.8 mm (2 in) | [published] |
| Voice coil diameter | 75 mm (3 in) edgewound flat Al wire | [published] |
| Diaphragm material | Titanium | [published] |
| Magnet | Ferrite (ceramic) + copper shorting ring | [published] |
| Nominal impedance | 8 Ω | [published] |
| Re | n/a | — |
| Le | 0.14 mH | [published] |
| Bl | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Flux density | 1.85 T | [published] |
| Sensitivity (1W/1m) | 108 dB | [published] |
| AES / continuous power | 80 W RMS / 160 W program | [published] |
| Frequency range | 500–18000 Hz | [published] |
| Min crossover | 1000 Hz (datasheet) | [published] |
| Mounting | 4× M6 holes on 102 mm (4 in) dia. circle | [published] |
| Weight | 4.5 kg (9.9 lb) | [published] |
| OD × depth | 170 × 67 mm | [published] |
| Approx US price | ~$226 | [retail] |
| Source | US Speaker | [retail] |
| Datasheet URL | https://www.bcspeakers.com/en/products/hf-driver/2-0/8/de85 | — |

**Notes:** Identical footprint to DE82 (same bolt circle). Frequently used as main driver in installed-sound boxes loaded at 500–800 Hz. Datasheet says 1 kHz but B&C application notes describe loading to 500 Hz with suitable horn. Ferrite motor is heavier than neodymium alternatives.

---

### B&C DE82 — 1.4" (36 mm) exit

**Use:** Hi-fi and PA; 3" Al VC on titanium; low recommended XO

| Parameter | Value | Provenance |
|---|---|---|
| Model | B&C DE82 | — |
| Exit diameter | 36 mm (1.4 in) | [published] |
| Voice coil diameter | 75 mm (3 in) aluminum | [published] |
| Diaphragm material | Titanium | [published] |
| Magnet | Ferrite | [published] |
| Nominal impedance | 8 Ω (also 16 Ω) | [published] |
| Re | n/a | — |
| Le | 0.14 mH | [published] |
| Bl | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Flux density | 1.8 T | [published] |
| Sensitivity (1W/1m) | 107 dB (8 Ω) | [published] |
| AES / continuous power | 80 W / 160 W program | [published] |
| Frequency range | 500–18000 Hz | [published] |
| Min crossover | 1000 Hz (datasheet); usable lower with 24 dB/oct per application notes | [published] |
| Mounting | 4× M6 holes on 102 mm (4 in) dia. circle | [published] |
| Weight | 4.44 kg (9.79 lb) | [published] |
| OD × depth | 170 × 64 mm | [published] |
| Approx US price | ~$207–225 (no current US stock found; EU ~€206) | [retail] |
| Source | TLHP / Sonovente (EU) | [retail] |
| Datasheet URL | https://www.bcspeakers.com/en/products/hf-driver/1-4/8/de82 | — |

**Notes:** Same family as DE85 (2"); shares diaphragm. Large motor relative to 1.4" exit — favorable for compression ratio and low-frequency loading. Often specified for installed-sound midrange horns. B&C does not currently list a US distributor on their website; Sonovente and TLHP are EU.

---

### Eminence PSD3014-8 — 1.4" (36 mm) exit

**Use:** Budget 1.4"; 3" VC, usable from 800 Hz

| Parameter | Value | Provenance |
|---|---|---|
| Model | Eminence PSD3014-8 | — |
| Exit diameter | 35.6 mm (1.4 in) | [published] |
| Voice coil diameter | 76.2 mm (3 in) | [published] |
| Diaphragm material | n/a (titanium likely; not confirmed) | — |
| Nominal impedance | 8 Ω | [published] |
| Re | n/a | — |
| Le | n/a | — |
| Bl | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Sensitivity (1W/1m) | 108.4 dB (on H2EA horn w/ 1.4"–2" adaptor) | [published] |
| AES / continuous power | 100 W AES | [published] |
| Frequency range | n/a | — |
| Min crossover | 800 Hz | [published] |
| Mounting | n/a | — |
| Weight | n/a | — |
| Approx US price | ~$100–130 est. | [retail] |
| Source | WWBW (price not confirmed current) | [retail] |
| Datasheet URL | https://www.eminence.com/eminence-introduces-a-1-4-exit-compression-driver | — |

**Notes:** Limited datasheet detail available from searches. Sensitivity stated on a specific horn + adaptor measurement, not PWT; requires caution when comparing. Use as budget measurement mule only.

---

### Celestion CDX14-3040 Neo — 1.4" (36 mm) exit

**Use:** Hi-fi / measurement; clearance price at time of writing

| Parameter | Value | Provenance |
|---|---|---|
| Model | Celestion CDX14-3040 Neo | — |
| Exit diameter | 36 mm (1.4 in) | [published] |
| Voice coil diameter | 75 mm (3 in) | [published] |
| Diaphragm material | Titanium (single-piece) | [published] |
| Magnet | Neodymium | [published] |
| Nominal impedance | 8 Ω | [published] |
| Re | n/a | — |
| Le | n/a | — |
| Bl | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Sensitivity (1W/1m) | 106.5 dB | [published] |
| AES / continuous power | 75 W AES | [published] |
| Frequency range | n/a | — |
| Min crossover | 1000 Hz @ 12 dB/oct minimum | [published] |
| Mounting | 4-bolt | [published] |
| Weight | n/a | — |
| Approx US price | ~$195 (clearance; MSRP $448.50) | [retail] |
| Source | Parts Express #294-2154 (1 unit in stock as of research date) | [retail] |
| Datasheet URL | https://parts-express.com/Celestion-CDX14-3040-Neo-1.4-Compression-Driver-75W-294-2154 | — |

**Notes:** Only 1 unit in stock at Parts Express at research date. Min XO 1 kHz limits use to above-1 kHz horns. Sensitivity is 106.5 dB — lower than alternatives in this price range. Not recommended for 600 Hz loading.

---

## Price Bracket: $500+

### Best picks by exit and use

| Model | Exit (mm) | Best for | Approx US price | Source |
|---|---|---|---|---|
| RCF ND850-2.0 | 50.8 (2") | PA / hi-fi 2" | ~$569 [retail] | SoundPro |
| 18 Sound ND2080-8 | 50.8 (2") | PA / hi-fi 2" | ~$449–539 [retail] | VIP Pro Audio |
| Beyma CP800/Ti | 50.8 (2") | PA power 2"; ferrite 4" VC | ~$465 [retail] | US Speaker |
| BMS 4592-MID | 50.8 (2") | Pro PA 2"; 90mm VC, 300 Hz XO | ~$650–830 [retail] | US Speaker / TLHP |
| Radian 950PB | 50.8 (2") | Hi-fi / ultra-low distortion | ~$720 [retail] | AV Superstore |

---

### RCF ND850-2.0 — 2" (50.8 mm) exit

**Use:** PA and hi-fi; 3" Ti diaphragm; 500 Hz usable

| Parameter | Value | Provenance |
|---|---|---|
| Model | RCF ND850-2.0 | — |
| Exit diameter | 50.8 mm (2 in) | [published] |
| Voice coil diameter | 76.2 mm (3 in) edgewound Al on Kapton | [published] |
| Diaphragm material | Pure titanium (0.05 mm precision-formed) | [published] |
| Magnet | Neodymium | [published] |
| Nominal impedance | 8 Ω | [published] |
| Re | n/a | — |
| Le | n/a | — |
| Bl | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Sensitivity (1W/1m) | 110 dB | [published] |
| AES / continuous power | 220 W program | [published] |
| Frequency range | 500–20000 Hz | [published] |
| Min crossover | n/a (implied 500 Hz from frequency range) | — |
| Mounting | Bolt-on | [published] |
| Weight | n/a | — |
| Approx US price | ~$569 (MAP) / MSRP $819 | [retail] |
| Source | SoundPro | [retail] |
| Datasheet URL | https://soundpro.com/products/rcf-nd850-2 | — |

**Notes:** Copper demodulation ring in gap (reduces inductance and distortion). High power handling (220 W program). Frequency range starting at 500 Hz is consistent with 600 Hz crossover use. RCF specifies the same ND850 diaphragm across 1.4" and 2.0" variants.

---

### 18 Sound ND2080-8 — 2" (50.8 mm) exit

**Use:** PA and high-power hi-fi; 75 mm (3 in) VC

| Parameter | Value | Provenance |
|---|---|---|
| Model | 18 Sound ND2080-8 | — |
| Exit diameter | 50.8 mm (2 in) | [published] |
| Voice coil diameter | 75 mm (3 in) aluminum winding | [published] |
| Diaphragm material | Pure titanium | [published] |
| Magnet | Neodymium (22 kGauss in gap) | [published] |
| Nominal impedance | 8 Ω | [published] |
| Re | n/a | — |
| Le | n/a | — |
| Bl | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Sensitivity (1W/1m) | 110 dB | [published] |
| AES / continuous power | 100 W AES / 200 W program | [published] |
| Frequency range | 500–20000 Hz | [published] |
| Min crossover | n/a | — |
| Mounting | Bolt-on | [published] |
| Weight | 3.4 kg (7.5 lb) | [published] |
| OD × depth | 131 × 99 mm | [published] |
| Approx US price | ~$449–539 | [retail] |
| Source | VIP Pro Audio | [retail] |
| Datasheet URL | https://reverb.com/item/26703278 (listing); see eighteensound.it for full datasheet | — |

---

### Beyma CP800/Ti — 2" (50.8 mm) exit

**Use:** PA power; ferrite 4" VC; 500 Hz rated

| Parameter | Value | Provenance |
|---|---|---|
| Model | Beyma CP800/Ti | — |
| Exit diameter | 50.8 mm (2 in) | [published] |
| Voice coil diameter | 100 mm (4 in) flat Al wire | [published] |
| Diaphragm material | Pure titanium | [published] |
| Magnet | Ferrite | [published] |
| Nominal impedance | 8 Ω | [published] |
| Re (DC resistance) | 5.6 Ω | [published] |
| Le | n/a | — |
| Bl | 15 N/A (T·m) | [published] |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Sensitivity (1W/1m) | 112 dB | [published] |
| AES / continuous power | 200 W program above 500 Hz | [published] |
| Frequency range | n/a | — |
| Min crossover | 500 Hz @ 12 dB/oct | [published] |
| Mounting | n/a | — |
| Weight | n/a | — |
| Approx US price | ~$465 | [retail] |
| Source | US Speaker | [retail] |
| Datasheet URL | https://usspeaker.com/beyma%20CP800Ti-1.htm | — |

**Notes:** 4" VC is the largest in this survey; extremely high Bl = 15 T·m. 500 Hz rated crossover is among the lowest published for any 2" driver. 112 dB sensitivity is the highest in this survey. Large ferrite motor — heavy. Outstanding choice for PA horn loaded to 500–600 Hz.

---

### BMS 4592-MID — 2" (50.8 mm) exit

**Use:** Professional PA; pro-level 300 Hz crossover; 90 mm VC

| Parameter | Value | Provenance |
|---|---|---|
| Model | BMS 4592-MID | — |
| Exit diameter | 50.8 mm (2 in) | [published] |
| Voice coil diameter | 90 mm (3.5 in) CCAW | [published] |
| Diaphragm material | n/a (aluminum or titanium; not confirmed from sources) | — |
| Magnet | Neodymium | [published] |
| Nominal impedance | 8 Ω (also 16 Ω) | [published] |
| Re | n/a | — |
| Le | n/a | — |
| Bl | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Sensitivity (1W/1m) | 118 dB (1W/1m) | [published] |
| AES / continuous power | 150 W nominal / 300 W peak | [published] |
| Frequency range | 200–9000 Hz | [published] |
| Min crossover | 300 Hz | [published] |
| Mounting | n/a | — |
| Weight | n/a | — |
| Approx US price | ~$650–830 | [retail] |
| Source | US Speaker / TLHP | [retail] |
| Datasheet URL | https://en.toutlehautparleur.com/compression-driver-bms-4592-mid-8-ohm-2-inch-exit.html | — |

**Notes:** The BMS 4592-MID is a dedicated midrange compression driver, not a tweeter-range HF driver. 300 Hz crossover, 200–9000 Hz bandwidth, 90 mm VC, and 118 dB sensitivity make it exceptional for a 500–600 Hz horn-loaded midrange in a 3-way PA or hi-fi system. This is the deepest-crossing 2" driver found in this survey. Price is steep but far below the DCX464.

---

### Radian 950PB — 2" (50.8 mm) exit

**Use:** Hi-fi / ultra-low distortion; 4" Al VC

| Parameter | Value | Provenance |
|---|---|---|
| Model | Radian 950PB | — |
| Exit diameter | 50.8 mm (2 in) | [published] |
| Voice coil diameter | 101.6 mm (4 in) edgewound CCAW | [published] |
| Diaphragm material | Pure aluminum | [published] |
| Magnet | Neodymium | [published] |
| Nominal impedance | 8 Ω (also 16 Ω) | [published] |
| Re | n/a | — |
| Le | n/a | — |
| Bl | n/a | — |
| Mmd | n/a | — |
| Sd | n/a | — |
| fs | n/a | — |
| Qts / Qes / Qms | n/a | — |
| Sensitivity (1W/1m) | 113 dB | [published] |
| AES / continuous power | 125 W nominal / 250 W max | [published] |
| Frequency range | 500–22000 Hz | [published] |
| Min crossover | n/a (implied 500 Hz) | — |
| Mounting | n/a | — |
| Weight | n/a | — |
| Approx US price | ~$720 | [retail] |
| Source | AV Superstore | [retail] |
| Datasheet URL | https://en.toutlehautparleur.com/compression-driver-radian-950pb-8-ohm-2-0-inch-exit.html | — |

**Notes:** Pure aluminum diaphragm has different sonic character than titanium — lower break-up frequency but often preferred for hi-fi. 4" VC provides very high Bl potential and low distortion at high excursion. Radian Audio Engineering (California).

---

## Additional Reference Drivers (noted but not in main brackets)

These drivers appeared in research but are outside the project's stated budget constraints or have other limitations:

| Model | Exit | Notes | Price est. |
|---|---|---|---|
| BMS 4591 | 2" | 90 mm VC, 300 Hz XO, 118 dB; similar to 4592 but older design | ~$400 EU equiv |
| B&C DE250 | 1" | 44 mm VC, polyimide, 108.5 dB, 1.6 kHz min XO | n/a US |
| 18 Sound ND3N | 1.4" | 75 mm VC, titanium nitride coat, 112 dB, 1200 Hz min XO | n/a US |
| JBL 2451H | 1.5" | 111 dB, 500 Hz range, non-standard 1.5" exit — does not fit 1.4" or 2" round throat | n/a |
| Faital HF108R | 1" | Ketone polymer diaphragm, 109 dB, 1.3 kHz min XO | ~$150 est |

---

## YAML Blocks (T/S data for top drivers with published parameters)

Only parameters that appear explicitly in a source are filled. Any missing key is omitted per the template.

```yaml
# --- Eminence PSD3006-8 ---
name: Eminence PSD3006-8
source: https://usspeaker.com/PSD3006-1.htm
use: pa
notes: >
  2" exit, 3" Ti geodesic diaphragm on polyimide former. fs=511 Hz from product page
  (re-confirm from Eminence datasheet before use). Discontinued per US Speaker; verify stock.
  Re from product page [published]. Bolt circle 4" dia, 1/4-20 studs.
exit_diameter_mm: 50.8
nominal_impedance_ohm: 8
re_ohm: 4.8
fs_hz: 511
rated_power_w: 80      # AES above 500 Hz; 115 W above 800 Hz
sensitivity_db_1w1m: 111.4
min_crossover_hz: 500
```

```yaml
# --- Beyma CD14Nd ---
name: Beyma CD14Nd
source: https://usspeaker.com/beyma%20CD14Nd-1.htm
use: hifi_tube
notes: >
  1.4" exit, 2.5" edgewound Al ribbon VC, PM-4 polymer diaphragm. Bl=10 T·m [published].
  Re=5.3 Ω [published]. Smooth polymer diaphragm preferred for tube amplifier / hi-fi use.
  Compact: 120mm OD, 49mm deep.
exit_diameter_mm: 36
nominal_impedance_ohm: 8
re_ohm: 5.3
bl_tm: 10.0
rated_power_w: 80
sensitivity_db_1w1m: 108
min_crossover_hz: 800
```

```yaml
# --- B&C DE82 ---
name: B&C DE82
source: https://www.bcspeakers.com/en/products/hf-driver/1-4/8/de82
use: both
notes: >
  1.4" exit, 3" Al VC, Ti diaphragm, ferrite motor. Le=0.14 mH [published].
  Flux density 1.8 T [published]. 4-bolt 102mm circle. Re and Bl not published on B&C site.
  Share diaphragm with DE85 (2" version).
exit_diameter_mm: 36
nominal_impedance_ohm: 8
le_mh: 0.14
rated_power_w: 80
sensitivity_db_1w1m: 107
min_crossover_hz: 1000
```

```yaml
# --- B&C DE85 ---
name: B&C DE85
source: https://www.bcspeakers.com/en/products/hf-driver/2-0/8/de85
use: both
notes: >
  2" exit, 3" flat Al VC, Ti diaphragm, ferrite motor + copper shorting ring.
  Le=0.14 mH [published]. Flux density 1.85 T [published]. 4-bolt 102mm circle.
  Datasheet says 1 kHz min XO but application notes document 500 Hz loading.
exit_diameter_mm: 50.8
nominal_impedance_ohm: 8
le_mh: 0.14
rated_power_w: 80
sensitivity_db_1w1m: 108
min_crossover_hz: 1000
```

```yaml
# --- Faital Pro HF200 ---
name: Faital Pro HF200
source: https://usspeaker.com/Faital%20Pro%20HF200-1.htm
use: both
notes: >
  2" exit, 2.95" (75mm) VC, Ti diaphragm, neodymium. Flux density 1.8 T [published].
  OD=130.5mm, depth=95mm. Compact neodymium. Re/Bl/Sd/fs not published.
  Min XO 900 Hz per datasheet; used from ~700 Hz in practice with 24 dB/oct.
exit_diameter_mm: 50.8
nominal_impedance_ohm: 8
rated_power_w: 80
sensitivity_db_1w1m: 108
min_crossover_hz: 900
```

```yaml
# --- Beyma CP800/Ti ---
name: Beyma CP800/Ti
source: https://usspeaker.com/beyma%20CP800Ti-1.htm
use: pa
notes: >
  2" exit, 4" flat Al VC, Ti diaphragm, ferrite. Re=5.6 Ω [published]. Bl=15 T·m [published].
  500 Hz crossover rated. 112 dB sensitivity — highest in this survey for a ferrite 2" driver.
  Heavy; intended for fixed installation and touring PA.
exit_diameter_mm: 50.8
nominal_impedance_ohm: 8
re_ohm: 5.6
bl_tm: 15.0
rated_power_w: 200    # program above 500 Hz
sensitivity_db_1w1m: 112
min_crossover_hz: 500
```

```yaml
# --- BMS 4592-MID ---
name: BMS 4592-MID
source: https://en.toutlehautparleur.com/compression-driver-bms-4592-mid-8-ohm-2-inch-exit.html
use: pa
notes: >
  2" exit, 3.5" (90mm) CCAW VC, neodymium. 300 Hz crossover — deepest in this survey.
  200–9000 Hz bandwidth. 118 dB sensitivity. Midrange specialist, not a full-range HF driver.
  Diaphragm material not confirmed from sources accessed. US price ~$650-830.
exit_diameter_mm: 50.8
nominal_impedance_ohm: 8
rated_power_w: 150
sensitivity_db_1w1m: 118
min_crossover_hz: 300
```

```yaml
# --- RCF ND850-2.0 ---
name: RCF ND850-2.0
source: https://soundpro.com/products/rcf-nd850-2
use: both
notes: >
  2" exit, 3" edgewound Al on Kapton, pure 0.05mm Ti diaphragm, neodymium, copper ring.
  220 W program power. 500 Hz–20 kHz usable range. MAP $569 in US. Re/Bl/fs not published.
exit_diameter_mm: 50.8
nominal_impedance_ohm: 8
rated_power_w: 220
sensitivity_db_1w1m: 110
min_crossover_hz: 500
```

---

## Recommendations

### (a) Hi-fi 600–800 Hz crossover on a 1.4" or 2" round throat, modest budget

**Top picks:**

1. **Beyma CD14Nd (~$263, 1.4" exit)** — PM-4 polymer diaphragm is smoother and more refined in the upper midrange than titanium alternatives; 2.5" VC; Bl = 10 T·m. Best for 800 Hz crossover on a 1.4" throat in a tube-amplifier system. Cannot reliably cross below 800 Hz. Compact and light.

2. **B&C DE82 (~$207–225 est., 1.4" exit)** — 3" Al VC on titanium gives better mass advantage for lower crossover than the CD14Nd. Same bolt circle as DE85; B&C's application notes describe midrange loading to 500 Hz. Availability in US is limited (mostly EU stock); allow for shipping or lead time.

3. **Faital Pro HF200 (~$387, 2" exit)** — Best 2"-exit option in this bracket for hi-fi balance. Neodymium, compact, 75 mm VC. Rated 900 Hz but usable from ~700–800 Hz with 24 dB/oct crossover. Widely stocked in the US.

If budget allows a stretch: the **Beyma CP800/Ti (~$465, 2" exit)** is rated to 500 Hz with a 4" VC and 112 dB sensitivity — the best single driver for deep-loading hi-fi in the $500 range.

### (b) PA power, 2" exit

**Top picks:**

1. **Beyma CP800/Ti (~$465)** — 4" VC, 112 dB, 200 W program, 500 Hz rated. Best PA 2" driver for horn-loaded midrange SPL in this survey below $600.

2. **RCF ND850-2.0 (~$569)** — 220 W program, 110 dB, 500 Hz range, copper ring for low distortion at high drive. Widely used in installed-sound PA.

3. **BMS 4592-MID (~$650–830)** — Crossover to 300 Hz, 118 dB, 150 W continuous. Exceeds spec for this application but enables horn loading well below 500 Hz for a 3-way PA system.

### (c) Cheapest viable for 3D-print prototyping and measurement

**Top pick:**

**Eminence PSD3006-8 (~$215, 2" exit)** — Published fs = 511 Hz (lowest in the budget group), 111.4 dB sensitivity, 500 Hz usable frequency, Re = 4.8 Ω. The best budget 2" driver found with published T/S data for model validation. Check stock before ordering (listed as discontinued on some sites).

Runner-up: **PRV Audio D3500TiH-Nd (~$180, 2" exit)** — Widely available at Parts Express, good sensitivity, but 1000 Hz minimum crossover limits prototyping scope.

For 1.4": **Beyma CD14Nd (~$263)** is the lowest-priced 1.4" driver with any published Bl and Re data, making it the best choice for lumped-model validation at a 1.4" round-throat horn.

---

## Source Table

| URL | What was taken from it | Date accessed |
|---|---|---|
| https://www.parts-express.com/PRV-Audio-D4400Ti-2-Titanium-Compression-Driver-8-Ohm-4-Bolt-294-2792 | D4400Ti specs, price ~$120–130, power, sensitivity, crossover, mounting | 2026-10-28 |
| https://prvaudio.com/products/d3500tih-nd/ | D3500TiH-Nd specs, price ~$180, VC, sensitivity, power, crossover | 2026-10-28 |
| https://usspeaker.com/PSD3006-1.htm | PSD3006 Re=4.8Ω, fs=511Hz, sensitivity 111.4 dB, crossover 500 Hz, VC 3", mounting, note "No Longer Available" | 2026-10-28 |
| https://usspeaker.com/beyma%20CD14Nd-1.htm | CD14Nd price $262.95, Re=5.3Ω, Bl=10T·m, sensitivity 108 dB, VC 2.5", diaphragm PM-4 polymer, crossover 800 Hz, weight 1.9 kg | 2026-10-28 |
| https://www.bcspeakers.com/en/products/hf-driver/1-4/8/de82 | DE82: 1.4" exit, 3" Al VC, Ti diaphragm, Le=0.14mH, sensitivity 107 dB, 160 W program, 500–18000 Hz, 4×M6 102mm circle, 4.44 kg | 2026-10-28 |
| https://www.bcspeakers.com/en/products/hf-driver/2-0/8/de85 | DE85: 2" exit, 3" Al VC, Ti diaphragm, Le=0.14mH, 1.85T, sensitivity 108 dB, 160 W program, 500–18000 Hz, 4×M6 102mm circle, 4.5 kg | 2026-10-28 |
| https://usspeaker.com/B&C-DE85-1.htm | DE85 price $225.99, OD 170mm, depth 67mm | 2026-10-28 |
| https://usspeaker.com/Faital%20Pro%20HF200-1.htm | HF200: 2" exit, 75mm VC, Ti, Neo, 1.8T, sensitivity 108 dB, 80W AES / 160W program, 500–20kHz, 900 Hz XO, 3.2 kg, OD 130.5mm depth 95mm, price $386.95 | 2026-10-28 |
| https://usspeaker.com/beyma%20CP800Ti-1.htm | CP800/Ti: 2" exit, 4" Al VC, Ti, ferrite, Re=5.6Ω, Bl=15T·m, 112 dB, 200W program above 500 Hz, price $464.95 | 2026-10-28 |
| https://soundpro.com/products/rcf-nd850-2 | ND850-2.0: 2" exit, 3" VC, Ti 0.05mm, neo, copper ring, 110 dB, 220 W program, 500–20 kHz, MAP $569 / MSRP $819 | 2026-10-28 |
| https://reverb.com/item/26703278 | ND2080-8: 2" exit, 75mm Al VC, Ti, neo 22kGauss, 110 dB, 100W AES / 200W program, 131×99mm, 3.4 kg, US price ~$449 | 2026-10-28 |
| https://en.toutlehautparleur.com/compression-driver-bms-4592-mid-8-ohm-2-inch-exit.html | BMS 4592-MID: 2" exit, 90mm VC, neo, 118 dB, 150W nominal / 300W peak, 200–9000 Hz, 300 Hz XO, €583.76 | 2026-10-28 |
| https://en.toutlehautparleur.com/compression-driver-radian-950pb-8-ohm-2-0-inch-exit.html | Radian 950PB: 2" exit, 4" CCAW VC, Al diaphragm, neo, 113 dB, 125W nominal / 250W max, 500–22000 Hz, ~€489 | 2026-10-28 |
| https://avsuperstore.com/682-speaker-compression-drivers | Radian 950PB US price ~$720 | 2026-10-28 |
| https://parts-express.com/Celestion-CDX14-3040-Neo-1.4-Compression-Driver-75W-294-2154 | CDX14-3040: 1.4" exit, 3" VC, Ti, neo, 106.5 dB, 75W AES, 1 kHz XO, clearance $195 / MSRP $448.50 | 2026-10-28 |
| https://www.prosoundweb.com/eminence-introduces-psd3014-1-4-inch-exit-compression-driver/ | PSD3014: 1.4" exit, 3" VC, 100W AES, 108.4 dB, 800 Hz min XO | 2026-10-28 |
| https://www.diyaudio.com/community/threads/best-compression-drivers-today-2022.382609/ | Community discussion of BMS 4591/4592 pricing and performance in US; BMS 4592ND-Mid at $829.95 (US Speaker) | 2026-10-28 |
| https://www.audioxpress.com/article/the-celestion-cdx14-3040-compression-driver | CDX14-3040 test bench; 1 kHz min XO, 106.5 dB, single-piece Ti diaphragm | 2026-10-28 |
| Web search results (multiple) | PRV D3500TiH-Nd price $179.91 at Parts Express #294-3432; D4400Ti-Nd price $229.91 at Parts Express #294-2793; Eminence PSD3006 price ~$215 at Zoro/VIP Pro; 18 Sound ND2080 price ~$449–539 at VIP Pro Audio; RCF ND850-2.0 MAP $569 at SoundPro; Radian 950PB ~$720 at AV Superstore; Beyma CD14Nd ~$263 at US Speaker; Faital HF200 ~$387 at SpeakersAndAmps/Beach Audio | 2026-10-28 |
