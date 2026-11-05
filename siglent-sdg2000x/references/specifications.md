# SDG2000X specifications, verification and service

Numbers below are from the SDG2000X Service Manual (SM0202X-E01C) and User Manual (EN03A).
Where the service manual states values "according to the SDG2122X", the bandwidth-dependent
entries scale down for the 80 MHz and 40 MHz models.

## Models

| Model | Analog bandwidth | Channels |
|---|---|---|
| SDG2042X | 40 MHz | 2 |
| SDG2082X | 80 MHz | 2 |
| SDG2122X | 120 MHz | 2 |

Common to all: 1.2 GSa/s, 16-bit vertical resolution, 20 Vpp maximum output, 80 dB dynamic
range, TrueArb (8 pts–8 Mpts, 1 µSa/s–75 MSa/s), EasyPulse, ~197 built-in arbitrary waveforms,
4.3" resistive touchscreen. Power-on default is Sine, 1 kHz, 4 Vpp, CH1, outputs off.

## Frequency reference

| Parameter | Value |
|---|---|
| Resolution | 1 µHz |
| Initial accuracy | ±1 ppm at 25 °C; ±2 ppm over 0–40 °C |
| Aging | ±1 ppm first year; ±3.5 ppm over 10 years (25 °C) |

## Sine

| Parameter | Value |
|---|---|
| Frequency | 1 µHz – 120 MHz |
| Harmonic distortion (0 dBm) | −65 dBc to 10 MHz; −60 dBc to 20 MHz; −55 dBc to 40 MHz; −50 dBc to 60 MHz; −45 dBc to 80 MHz; −40 dBc to 100 MHz; −38 dBc to 120 MHz |
| THD | 0.075 % (0 dBm, 10 Hz–20 kHz) |
| Non-harmonic spurious | −70 dBc ≤50 MHz; −65 dBc >50 MHz |

## Square

| Parameter | Value |
|---|---|
| Frequency | 1 µHz – 25 MHz |
| Rise/fall time | ≤9 ns (10–90 %, 1 Vpp, 50 Ω) |
| Overshoot | ≤3 % (100 kHz, 1 Vpp, 50 Ω) |
| Duty cycle | 0.001 – 99.999 %, constrained by frequency |
| Jitter (rms, cycle-cycle) | ≤150 ps |

## Pulse

| Parameter | Value |
|---|---|
| Frequency | 1 µHz – 25 MHz |
| Minimum pulse width | 16.3 ns |
| Pulse width accuracy | ±(0.01 % + 0.3 ns) |
| Rise/fall time | 8.4 ns – 22.4 ns (10–90 %, 1 Vpp, 50 Ω), further constrained by width |
| Overshoot | ≤3 % |
| Duty cycle | 0.001 – 99.999 %, resolution 0.001 % |
| Jitter (rms) | ≤150 ps |

## Ramp

Frequency 1 µHz – 1 MHz; symmetry 0–100 %; linearity ≤1 % of peak-to-peak (1 kHz, 1 Vpp,
100 % symmetry).

## Noise

−3 dB bandwidth ≥120 MHz. Gaussian, set by standard deviation and mean, with an optional
bandwidth limit.

## Arbitrary

| Parameter | Value |
|---|---|
| Frequency (DDS) | 1 µHz – 20 MHz |
| Waveform length | 8 pts – 8 Mpts |
| Sample rate | 1 µSa/s – 75 MSa/s (TrueArb); 300 MSa/s effective (DDS) |
| Vertical resolution | 16 bit |
| Jitter (rms, TrueArb) | ≤150 ps (1 Vpp, 50 Ω) |

## DC

Range ±10 V into HiZ, ±5 V into 50 Ω. Accuracy ±(1 % + 2 mV) into HiZ.

## Output

| Parameter | Value |
|---|---|
| Amplitude range | 2 mVpp – 20 Vpp ≤20 MHz (HiZ); 2 mVpp – 10 Vpp >20 MHz (HiZ). Halve for 50 Ω. |
| Amplitude accuracy | ±(1 % + 1 mVpp) at 10 kHz sine, 0 V offset |
| Flatness (50 Ω, 2.5 Vpp, ref 10 kHz) | ±0.3 dB to 100 MHz; ±0.4 dB 100–120 MHz |
| Output impedance | 50 Ω typical (49.5–50.5 Ω at 10 kHz) — **fixed**; the `LOAD` setting is a compensation figure only |
| Output current | ±200 mA |
| Channel crosstalk | ≤−60 dBc |

## Modulation

| Type | Key limits |
|---|---|
| AM | Depth 0–120 %; modulating frequency 1 mHz – 1 MHz internal; carriers Sine/Square/Ramp/Arb |
| FM | Deviation 0 – 0.5 × bandwidth, limited by carrier frequency; modulating 1 mHz – 1 MHz |
| PM | Deviation 0–360°; modulating 1 mHz – 1 MHz |
| PWM | Pulse carrier only; modulating 1 mHz – 1 MHz; width-deviation resolution 6.67 ns |
| ASK / FSK / PSK | Modulating wave is a 50 % square; keying rate 1 mHz – 1 MHz internal |

## Burst and sweep

| Parameter | Value |
|---|---|
| Burst carriers | Sine, Square, Ramp, Pulse, Noise, Arb |
| Burst type | Count 1 – 1,000,000, Infinite, Gated |
| Burst carrier frequency | 2 mHz – bandwidth |
| Burst internal period | 1 µs – 1000 s |
| Burst trigger delay | up to 100 s |
| Sweep carriers | Sine, Square, Ramp, Arb |
| Sweep type | Linear, Log (Step also available via `SWMD,STEP`) |
| Sweep time | 1 ms – 500 s |

## Frequency counter

| Parameter | Value |
|---|---|
| Functions | Frequency, period, +/− pulse width, duty cycle |
| Coupling | AC, DC, HFREJ |
| Range | 100 mHz – 200 MHz (DC coupled); 10 Hz – 200 MHz (AC coupled) |
| Input amplitude | 100 mVrms min below 100 MHz; 200 mVrms min 100–200 MHz. Max ±2.5 V (DC) / 5 Vpp (AC) |
| Input impedance | 1 MΩ |

## Auxiliary and clock connectors

| Port | Specification |
|---|---|
| 10 MHz reference in | 10 MHz typical, ≥1.4 Vpp, 5 kΩ AC-coupled |
| 10 MHz reference out | 10 MHz, 2–3.3 Vpp into HiZ, 50 Ω source |
| Trigger in | VIH 2–5.5 V, VIL −0.5–0.8 V, 100 kΩ, min pulse width 100 ns, response ≤100 ns (sweep) / ≤600 ns (burst) |
| Trigger out | VOH ≥3.8 V at −8 mA, VOL ≤0.44 V at 8 mA, ~100 Ω, max 1 MHz |
| Sync out | Same levels as trigger out, ~500 ns typical width, max 1 MHz |
| Modulation in | 0–50 kHz, 10 kΩ, 11–13 Vpp (12 typical) for 100 % modulation |

## General

| Parameter | Value |
|---|---|
| Line voltage | 100–240 Vrms ±10 %, 50/60 Hz; or 100–120 Vrms ±10 %, 400 Hz. Auto-sensing. |
| Power consumption | 25.5 W typical, 50 W max |
| Fuse | F2.0AL, 250 V, 5 × 20 mm |
| Operating temperature | 0 – 40 °C |
| Storage temperature | −20 – 60 °C |
| Operating humidity | 5–90 % RH ≤30 °C; 5–50 % RH at 40 °C |
| Operating altitude | ≤3048 m at ≤30 °C |
| Warm-up | 30 minutes continuous within 18–28 °C before specifications apply |
| Calibration interval | 1 year |
| Dimensions (W×H×D) | 260.3 × 107.2 × 295.7 mm |
| Net weight | 3.43 kg |
| Ventilation | 15 cm clearance both sides |
| Ratings | Installation category II (mains) / I (measuring), pollution degree 2, IP20 |
| Compliance | IEC 61010-1:2010, EN 61326-1:2013 |
| Warranty | 3 years from shipment (repair parts 90 days) |

## Over-voltage protection

Enabled with `VOLTPRT ON`. The output shuts down and an alert appears when externally applied
voltage exceeds:

- **±11 V ±0.5 V** when the channel is set to ≥3.2 Vpp *or* ≥|2 V| offset
- **±4 V ±0.5 V** when set below both of those

`VOLTSTAT?` reports the current overload state. There is also `CURRPRT` for over-current.

## Default settings (`*RST` / Set To Default)

| Parameter | Default | Parameter | Default |
|---|---|---|---|
| Channel output | Off | AM depth | 100 % |
| **Load** | **HiZ** *(verified — not the 50 Ω the user manual's table implies)* | Burst trigger delay | 629 ns |
| Waveform | Sine | FM deviation | 100 Hz |
| Frequency | 1 kHz | PM deviation | 100° |
| Amplitude | 4 Vpp | FSK hop frequency | 1 MHz |
| Offset | 0 V | PSK polarity | Normal |
| Phase | 0° | PWM width deviation | 190 µs |
| Ramp symmetry | 50 % | Sweep time | 1 s |
| Modulation source | Internal | Sweep start / stop | 500 Hz / 1.5 kHz |
| Modulating wave | Sine | Sweep centre / span | 1 kHz / 1 kHz |
| Modulation frequency | 100 Hz | Sweep mode / direction | Linear / Up |
| Keying frequency | 100 Hz | Burst period | 10 ms |
| PSK rate | 100 Hz | Burst mode / cycles | NCycle / 1 |
| Trigger source (sweep, burst) | Internal | Burst start phase | 0° |
| Trigger output | Off | Burst delay | 629 ns |

CH1 and CH2 defaults are identical.

Verified against an SDG2122X: after `*RST`, `C1:OUTP?` reports
`C1:OUTP OFF,LOAD,HZ,POWERON_STATE,OFF,PLRT,NOR` and `C1:BSWV?` reports 1 kHz / 4 Vpp / 0 V
offset sine with `MAX_OUTPUT_AMP,20V`. `*RST` takes 2–3 seconds — wait before querying. It also
restores the 10 MHz reference output to ON.

## Performance verification

Perform on receipt and at each calibration interval. Warm up 30 minutes at 18–28 °C first.
The service manual documents three formal tests; other specification values are stated but not
part of the documented test suite. A failure means adjustment or repair — there is no
user-accessible calibration menu, password, or secure mode on this instrument.

If you are writing up results, the `calibration-certificate` skill produces the report.

### DC output accuracy

DMM on CH1, waveform DC, load HiZ, output on. Spec is ±(1 % + 2 mV).

| Setting | Limits |
|---|---|
| 0 mV | −2 … +2 mV |
| ±10 mV | ±7.9 … ±12.1 mV |
| ±100 mV | ±97 … ±103 mV |
| ±1 V | ±0.988 … ±1.012 V |
| ±3 V | ±2.968 … ±3.032 V |
| ±10 V | ±9.898 … ±10.102 V |

### AC amplitude accuracy

DMM on CH1, load 50 Ω, sine at 10 kHz. Spec is ±(1 % + 1 mV). Repeat for CH2.

| Setting (Vpp) | Limits (V) |
|---|---|
| 10 | 9.899 – 10.101 |
| 5.6 | 5.543 – 5.657 |
| 2 | 1.979 – 2.021 |
| 0.9 | 0.890 – 0.910 |
| 0.4 | 0.395 – 0.405 |
| 0.142 | 0.13958 – 0.14442 |
| 0.064 | 0.06236 – 0.06564 |
| 0.022 | 0.02078 – 0.02322 |
| 0.010 | 0.00890 – 0.01110 |
| 0.004 | 0.00296 – 0.00504 |

### Frequency response (flatness)

Power meter on CH1, load 50 Ω, sine, at 10 kHz / 100 kHz / 1 / 5 / 10 / 20 / 30 / 50 / 80 /
100 / 110 / 120 MHz. Repeat for CH2.

| Amplitude | 10 kHz – 100 MHz | 110 – 120 MHz |
|---|---|---|
| 1 V | 3.6794 – 4.2794 dBm | 3.5794 – 4.3794 dBm |
| 2.5 V | 11.64 – 12.24 dBm | 11.54 – 12.34 dBm |

Automating this is straightforward: step `C1:BSWV FRQ,<f>` through the list, read the power
meter, compare. The measurement instrument, not the generator, is the awkward part.

## Self test

`Utility > Test/Cal > SelfTest` runs ScrTest (screen), KeyTest (buttons and knob), LEDTest, and
BoardTest (internal chips — all should report `Pass`). A power-on self-test also runs
automatically; if it fails the instrument may hang with a black screen, which is a service issue.

There is no SCPI command to invoke self test.

## Troubleshooting

| Symptom | Sequence |
|---|---|
| Won't start | Check the power cord → the power button → the fuse (replace with same rating) → the PSU-to-main-board connection |
| Starts, dark screen | Check PSU-to-main-board connection → keypad-board-to-main-board connection |
| Buttons dead or display abnormal | Check keypad-board-to-main-board connection |
| Output amplitude wrong | Check the connection to the load → **check that the `Load` setting matches the actual load impedance** → contact service |

That third row is the one to try first in practice — it is the explanation far more often than
a hardware fault.

**Internal test points** (qualified personnel, mains disconnected, 3 minutes for capacitor
discharge, antistatic precautions):

- Channel board power connector, 6 pins: +20 V (red), −20 V (white), +6.5 V (yellow),
  −6.5 V (blue), ±10 % when connected, ±30 % with the connector removed. In spec when connected
  = PSU good. Out of spec connected but in spec disconnected = load fault on the channel/main
  board. Out of spec disconnected = replace the PSU module. The mains fuse lives inside the PSU
  assembly; if it fails, the whole assembly is replaced.
- Channel board rails, all ±5 %: +15, −15, −5, +5, 1.8, 3.3, 2.5 A, 2.5 B, 1.5, 1.1, PLL 3.3 V.
- Channel board 10 MHz TCXO: 3.3 V LVCMOS at the marked test point.
- `FPGA_LED` should flash at 1 Hz. Off or wrong rate suggests an FPGA fault.
- Main board rails ±5 %: 16 V, 3.3 V, 5 V. `CLK_25MHz` at ±50 ppm, 3.3 V LVCMOS.
  `ARM_LED` on = firmware loaded and CPU running.
- Connectors: `CON_J1` main↔channel, `CON_J5` channel↔interface, `CON_J6` channel power,
  `CON_J7` fan; `M_CON_J3` main↔key/LCD, `M_CON_J14` main power, `M_CON_J4` main↔channel,
  `M_CON_J15` USB host.

Service tools: T10 and T15 Torx. Module removal order: handle → metal shell and rear cabinet →
front cabinet → display module → main body.

Recommended test equipment: a DMM with ≥±0.015 % DC accuracy (Siglent suggest SDM3055) and a
300 MHz oscilloscope (SDS2304X).

## Firmware update

`Utility > System > Page 1/3 > Firmware Update`, loading an ADS file from a USB stick. Neither
manual documents a procedure beyond this, and there is no SCPI equivalent.

## Safety notes worth repeating

- The on/standby button does not disconnect mains — unplug the cord to fully power down.
- Hazardous stored energy in the PSU and LCD modules; wait 3 minutes after disconnecting.
- Do not measure mains circuits with this instrument, and do not connect it to a person.
- BNC shells are at chassis ground — the instrument cannot float.
- Keep 15 cm of ventilation clearance on both sides.
- Clean the exterior only, with a damp cloth, unplugged, and dry it fully before repowering.
- If an abnormal condition persists after one restart, stop using the instrument and contact
  service rather than trusting the data.
