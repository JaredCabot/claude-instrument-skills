# HP 8648A/B/C/D specifications (service guide chapter 4, condensed)

Specifications are warranted from 0 to 50 °C after a 30 min warm-up. Performance below 250 kHz
is typical. *Italic*/"typ" values are supplemental (not warranted).

## Frequency
| | 8648A | 8648B | 8648C | 8648D |
|---|---|---|---|---|
| Range | 100 kHz–1000 MHz | 9 kHz–2000 MHz | 9 kHz–3200 MHz | 9 kHz–4000 MHz |

Early B/C units (serial prefix < 3623A/3629U) start at 100 kHz.
* Resolution: 0.001 Hz (10 Hz displayed). Accuracy: same as the timebase.
* Switching time (typ): < 75 ms below 1001 MHz, < 100 ms above.
* Timebase:
  * Standard: aging < ±2 ppm/yr, temperature < ±1 ppm, line < ±0.5 ppm.
  * **1E5:** < ±0.1 ppm/yr or < ±0.0005 ppm/day (after 4 days), temperature < ±0.01 ppm typ.
* 10 MHz OUT > 0.5 Vrms into 50 Ω.
* EXT REF IN: 2, 5 or 10 MHz ± 5 ppm, 0.5–2 Vrms.

## Output
* Range:
  * 8648A: +10 to −136 dBm.
  * B/C/D: +13 to −136 dBm (≤ 2500 MHz), +10 dBm (≤ 4000 MHz).
* **1EA** maximum leveled power:

  | Frequency | 1EA | 1EA + 1E6 |
  |---|---|---|
  | < 100 kHz | +17 dBm | +13 dBm |
  | < 100 MHz | +20 dBm | +13 dBm (typ +16) |
  | ≤ 1000 MHz | +20 dBm | +18 dBm |
  | ≤ 1500 MHz | +19 dBm | +17 dBm |
  | ≤ 2100 MHz | +17 dBm | +15 dBm |
  | ≤ 2500 MHz | +15 dBm | +13 dBm |
  | < 4000 MHz | +13 dBm | +11 dBm |

* Resolution 0.1 dB.
* Accuracy (at 25 ± 5 °C):

  | Level | ≤ 2500 MHz | ≤ 3200 MHz | ≤ 4000 MHz |
  |---|---|---|---|
  | ≥ −100 dBm | ±1.0 dB | ±1.5 dB | ±2.0 dB |
  | < −100 dBm | ±3.0 dB | ±3.0 dB | ±3.0 dB |

  Below 100 kHz the accuracy is ±1.0 dB. Accuracy is valid down to −127 dBm and degrades
  typically ±0.5 dB over 0–50 °C or above +13 dBm.
* Reverse power protection: 50 W (≤ 2 GHz), 25 W (≤ 4 GHz). Impedance 50 Ω.

## Spectral purity
* Harmonics < −30 dBc at ≤ +4 dBm.
* Non-harmonics (≥ 5 kHz offset, ≤ +4 dBm): < −55 dBc (< 249 MHz), −60 (< 1001), −54 (< 2001),
  −48 (≤ 4000).
* Residual FM (CCITT rms): < 7 Hz (< 249 MHz), 4 Hz (< 501), 7 Hz (< 1001), 14 Hz (< 2001),
  28 Hz (≤ 4000).
* SSB phase noise at 20 kHz (typ): −120 dBc/Hz (500 MHz), −116 (1 GHz), −110 (2 GHz), −106 (3 GHz),
  −104 (4 GHz).

## FM
* Peak deviation: 200 kHz (< 249 MHz), 100 kHz (< 501), 200 kHz (< 1001), 400 kHz (< 2001),
  800 kHz (≤ 4000).
* Resolution:

  | Deviation | < 2001 MHz | ≥ 2001 MHz |
  |---|---|---|
  | ≤ 10 % of max | 10 Hz | 20 Hz |
  | > 10 % of max | 100 Hz | 200 Hz |

* Accuracy (1 kHz internal): ±3 % ± 30 Hz (< 1001 MHz), ±60 Hz (< 2001), ±120 Hz (≤ 4000).
* Rates: internal 400 Hz/1 kHz; 1E2 10 Hz–20 kHz; ext DC dc–150 kHz; ext AC 1 Hz–150 kHz (3 dB).
* Distortion (1 kHz, THD+N, 0.3–3 kHz): < 1 % at dev > 4/8/16 kHz (< 1001/2001/4000 MHz).
* DC-FM carrier accuracy: ±100 Hz (< 1001 MHz, dev < 10 kHz), ±200 Hz, ±400 Hz, within 1 h of
  `CAL:DCFM`.

## PM
* Deviation: 10 rad (< 249 MHz), 5 (< 501), 10 (< 1001), 20 (< 2001), 40 (≤ 4000).
* Resolution 0.01 rad (< 2001 MHz), 0.02 rad above.
* Accuracy (typ): ±3 % ± 0.05 rad (< 1001 MHz), ±5 % ± 0.1 rad (< 2001), ±5 % ± 0.2 rad.
* Rates: internal 400 Hz/1 kHz; 1E2 20 Hz–10 kHz; external 20 Hz–10 kHz.
* Distortion < 1 % at ≥ 3/6/12 rad.

## AM (not specified below 1.5 MHz; typical above 1001 MHz)
* 0–100 % (output ≤ +4 dBm), resolution 0.1 %.
* Accuracy ±5 % of setting ± 1.5 % (1 kHz, < 70 % depth, 25 ± 5 °C).
* Rates: internal 400 Hz/1 kHz; 1E2 10 Hz–20 kHz; ext DC dc–25 kHz; AC 1 Hz–25 kHz.
* Distortion:

  | Depth | 8648A | 8648B/C/D |
  |---|---|---|
  | 30 % AM | < 2 % | < 2 % |
  | 90 % AM | < 3 % | – |
  | 70 % AM | – | < 3 % |

## Modulation source and I/O
* MOD INPUT/OUTPUT front BNC, 1 Vpk into 600 Ω for full scale. A HI/LO indicator works up to 10 kHz.
* **1E2:** sine 10 Hz–20 kHz; square/triangle/saw 100 Hz–2 kHz. Accuracy ±0.01 % typ,
  resolution 1 Hz.
* **1E6 pulse:** rise/fall < 10 ns, on/off > 80 dB (< 2 GHz) / > 70 dB, 10 MHz max rate, TTL input.
* **1EP:** POCSAG 512/1200/2400 bps; FLEX/FLEX-TD 1600/3200 (2FSK), 3200/6400 (4FSK).
  FSK deviation accuracy ±60 Hz at 4.8 kHz. Data-rate accuracy ±5 ppm.

## Remote / general
* HP-IB: SH1 AH1 T6 TE0 L4 LE0 SR1 RL1 PP0 DC1 DT0 C0 E2. SCPI 1992.0 and 8656B/8657 code compatibility.
* 300 storage registers (10 sequences × 30); 1EP has 70.
* Power 90–264 V, 48–440 Hz, 170 VA. Weight 7 kg (A) / 8.5 kg (B/C/D). Size 165 × 330 × 368 mm.
