---
name: hp-3458a
description: Operate, program (GPIB), digitize with, verify and calibrate the HP/Agilent/Keysight 3458A 8.5-digit multimeter - full command set with numeric codes, triggering, formats, memory, math, subprograms and BASIC, autocal, adjustment and performance verification.
---

# HP / Agilent / Keysight 3458A 8.5-digit multimeter

The 3458A is a GPIB-only system multimeter, sold under the HP, Agilent and Keysight names since the late 1980s. It measures DCV, ACV, AC+DCV, DCI, ACI, AC+DCI, 2-wire and 4-wire ohms, frequency and period, and it digitizes through two signal paths: the integrating A/D (up to 100 k samples/s, 150 kHz) and a track-and-hold (2 ns aperture, 12 MHz, direct sampling at 50 k samples/s or sub-sampling at 10 ns effective interval). It resolves up to 8.5 digits on DCV and reads 4.5-digit DCV at 100,000 readings/s.

The command language is the HP multimeter language of the late 1980s. **It is not SCPI and the manuals document no `*` common commands.** Identify with `ID?`, reset with `RESET` or `PRESET`, read errors with `ERRSTR?`.

Sources for this skill: User's Guide (03458-90014 Ed 9, June 2021, Keysight 9018-01343), Calibration Manual (03458-90017 Ed 11, March 2023, Keysight 9018-01342), Quick Reference Guide (Keysight 9018-14517, 2017; the Agilent 2000 edition has the same content), and the front-panel guide 03458-90007. Accuracy specifications are in data sheet 5965-4971E, which is not reproduced here; the performance verification limits in this skill come from the Calibration Manual.

Hardware facts: Motorola 68000 CPU at 8 MHz, separate inguard and outguard processors (`REV?` returns both firmware revisions). Reading memory holds 10,000 readings in SINT format as standard and 75,000 with Option 001. 14 kB of continuous (battery-backed) memory holds subprograms and stored states. Option 002 is the high-stability reference (4 ppm/year).

## Quick start (PyVISA)

```python
import pyvisa, struct, time
rm = pyvisa.ResourceManager()
dmm = rm.open_resource("GPIB0::22::INSTR")   # factory address 22
dmm.write_termination = "\r\n"
dmm.read_termination = "\r\n"     # ASCII readings and query replies end in CR LF
dmm.timeout = 30000               # ms; see "the bus is held" below

dmm.clear()                       # Device Clear first: the meter may be busy
dmm.write("RESET")                # power-on state (NPLC 10, DCV autorange, TRIG AUTO)
print(dmm.query("ID?"))           # "HP3458A" on older units, "Keysight 3458A" on newer
print(dmm.query("REV?"))          # "outguard_rev,inguard_rev"
print(dmm.query("OPT?"))          # 0 = standard memory, 1 = Option 001
print(dmm.query("TEMP?"))         # internal temperature, deg C

def errors():
    """Read and clear all pending errors, auxiliary (200-series) first."""
    out = []
    for _ in range(32):
        r = dmm.query("ERRSTR?")
        if int(r.split(",")[0]) == 0:
            return out
        out.append(r)
    return out

# One DC voltage reading, 10 V range, 1 PLC
dmm.write("PRESET NORM")          # TRIG SYN, NPLC 1, ASCII output, display on
dmm.write("DCV 10;NPLC 1")
dmm.write("TRIG SGL")             # one reading, then trigger goes to HOLD
v = float(dmm.read())
print(v, errors())
```

With PRESET NORM the trigger event is SYN, so simply reading from the meter also takes a reading: `float(dmm.read())` after `PRESET NORM; DCV 10` returns a fresh measurement each time. `TRIG SGL` followed by a read is the explicit form.

### Rules that matter in practice

1. **The bus is held while a command runs.** With the input buffer off (`INBUF OFF`, the power-on state) the meter accepts CR at once but holds the bus on the LF until the command has finished. A PyVISA `write("ACAL ALL")` blocks for about 15 minutes, `TEST` for about 50 s, and `TARM SGL` with 10,000 readings until the last reading is taken. Either raise the VISA timeout for those writes (this gives you free synchronisation) or send `INBUF ON` so the meter buffers up to 255 characters and releases the bus at once; then watch status bit 4 (ready) with a serial poll.
2. **Device Clear before RESET or PRESET** from a program, because the meter may be busy. Device Clear also aborts a running subprogram, clears the input and output buffers, clears status (bits 4, 5, 6 come back if their condition persists) and disables triggering until the next command arrives, when the previous trigger mode resumes.
3. **The output buffer holds one item.** It holds one reading or one query response until it is read or replaced. A query sent while a reading is waiting overwrites the reading. Read `ISCALE?` before triggering or after all readings have been transferred.
4. **Query responses are always ASCII**, whatever `OFORMAT` says. Any configuration command takes a `?` to read its setting (`NPLC?`, `TARM?`). `QFORMAT ALPHA` adds the header ("AZERO ON"); the default `QFORMAT NORM` returns numbers ("1").
5. **Defaults.** A parameter can be omitted, sent as `-1`, or left empty between commas (`ACV,,.01`, remote only). The bare-command default is often different from the power-on value: bare `FIXEDZ`, `OCOMP`, `RATIO`, `INBUF`, `LFILTER` and `LOCK` mean ON; bare `NPLC` means 0 (500 ns); bare `TRIG` means SGL; bare `MEM` means FIFO; bare `END` means ALWAYS.
6. **FIXEDZ stays on in ohms.** If `FIXEDZ ON` is left set and you switch to `OHM`/`OHMF`, the 10 MΩ input divider sits across the unknown and the ohms readings are wrong.
7. **Terminals and Guard switches are front-panel only.** `TERM?` reports FRONT or REAR; you cannot change it remotely. `TERM` itself is a no-op kept for compatibility.
8. **GPIB address** is set from the front panel only (`ADDRESS` from remote gives "command not allowed from remote"). Read it with the shifted Local (Address) key. Address 31 is talk-only mode (ASCII readings to a printer). A failure of the continuous memory (AUXERR 4096) resets the address to 22.
9. **Commands** are separated by `;`, parameters by `,`. Numbers are integer, decimal or exponent form and are rounded where an integer is needed. Command headers have a few abbreviations: `R` for `RANGE`, `T` for `TRIG`, and `FUNC` is optional (`DCV 10` is `FUNC DCV,10`).

## Terminals, guard and safety

- Front and rear terminal sets (Input HI/LO, Ω Sense HI/LO, I, Guard), selected by the front-panel Terminals switch. Guard switch: Open (out) guards the measurement, so connect the Guard terminal to the source LO; To LO (in) ties guard to LO internally.
- Above 42 V on any terminal, treat all terminals as hazardous.

| Terminal pair | Rated | Max non-destructive |
|---|---|---|
| HI to LO | ±1000 V peak | 1200 V peak |
| HI/LO Sense to LO | 200 V peak | 350 V peak |
| HI to LO Sense | 200 V peak | 350 V peak |
| LO to Guard | 200 V peak | 350 V peak |
| Guard to earth | 500 V peak | 1000 V peak |
| Any terminal to earth | 1000 V peak | 1500 V peak |
| Front to rear terminals | 1000 V peak | 1500 V peak |
| I to LO | ±1.5 A peak | < 1.25 A rms |

- Current terminal fuses (front and rear): 1 A 250 V normal-blow (2110-0001). Never fit a slow-blow fuse. Line fuse 1.5 A (100/120 V) or 500 mA T (220/240 V). Line 100/120/220/240 V ±10 %, 48 to 440 Hz, 80 VA.
- `DEFEAT ON` disables input-protection switch sequencing and some error checks to save time. Use it only if any overload on the Input stays within ±100 V peak on the 10 V range and below (the 100 V and 1000 V ranges withstand 1200 V peak). Overloads are tallied for warranty purposes. If more than 300 V is detected, defeat turns itself off and the event is logged.
- `TEST` runs the self-test (over 50 s); disconnect the inputs first. It also checks that every calibration constant is within its limits.

## Power-on, RESET and PRESET states

The front-panel Reset key and `RESET` give the power-on state. Shifted Reset is a full power cycle: it stores the present state as state 0, destroys stored readings and compressed subprograms, sets the power-on SRQ bit, sets the AC method back to analog and runs the power-on self-test. `RESET` also clears reading memory, the error and auxiliary error registers, and the status register except bit 3.

| Setting | Power-on / RESET | PRESET NORM | PRESET FAST | PRESET DIG |
|---|---|---|---|---|
| Function | DCV AUTO | DCV AUTO | DCV 10 | DCV 10 |
| AZERO | ON | ON | OFF | OFF |
| NPLC / APER | NPLC 10 | NPLC 1 | NPLC 1 | APER 3E-6 |
| DELAY | -1 (auto) | -1 | -1 | 0 |
| DISP | ON | ON | OFF | OFF |
| NDIG | 7 | 6 | 6 | 6 |
| BEEP | (stored) | ON | ON | ON |
| TARM | AUTO | AUTO | SYN | HOLD |
| TRIG | AUTO | SYN | AUTO | LEVEL |
| NRDGS | 1,AUTO | 1,AUTO | 1,AUTO | 256,TIMER |
| TIMER | 1 | 1 | 1 | 20E-6 |
| MFORMAT / OFORMAT | SREAL / ASCII | SREAL / ASCII | DINT / DINT | SINT / SINT |
| MEM | OFF | OFF (last op FIFO) | OFF | OFF |
| LEVEL | 0,AC | (unchanged) | (unchanged) | 0,AC |

Common to RESET and all PRESETs: ACBAND 20,2E6; FIXEDZ OFF; FSOURCE ACV; INBUF OFF; LOCK OFF; MATH OFF; MMATH OFF; OCOMP OFF; math registers DEGREE 20, PERC 1, REF 1, RES 50, SCALE 1, others 0. RESET (not PRESET) also sets: DEFEAT OFF, EMASK 32767, END OFF, EXTOUT ICOMP,NEG, LFILTER OFF, LFREQ (line measured and rounded to 50 or 60 Hz), QFORMAT NORM, RATIO OFF, RQS 0 (8 if power-on SRQ was enabled), SETACV ANA, SLOPE POS, SSRC LEVEL,AUTO, SWEEP 100E-9,1024, TBUFF OFF.

`PRESET` with no parameter is `PRESET NORM`. Numeric codes: FAST 0, NORM 1, DIG 2.

Stop readings before you reconfigure: `TARM HOLD`, `TRIG HOLD` or `PRESET NORM`. `TARM AUTO` resumes after TARM HOLD, PRESET FAST or PRESET DIG; `TRIG AUTO` resumes after TRIG HOLD or PRESET NORM.

## Functions and ranges

`FUNC function[,max_input][,%_resolution]`. The range is picked from the absolute value of `max_input`; `AUTO` or `-1` selects autorange. `RANGE max_input[,%res]` changes the range alone. `ARANGE OFF|ON|ONCE` (0/1/2): ONCE picks a range at the first trigger and holds it. For FREQ and PER, `max_input` is the signal amplitude, not the frequency. `FUNC?` returns "function,range" (the actual range, not whether autorange is on; use `ARANGE?`).

Function codes (returned by `FUNC?`): DCV 1, ACV 2, ACDCV 3, OHM 4, OHMF 5, DCI 6, ACI 7, ACDCI 8, FREQ 9, PER 10, DSAC 11, DSDC 12, SSAC 13, SSDC 14.

### DC voltage

| Range | Full scale | Max resolution | Input resistance | max_input selects it |
|---|---|---|---|---|
| 100 mV | 120.00000 mV | 10 nV | > 10 GΩ | 0 to 0.12 |
| 1 V | 1.20000000 V | 10 nV | > 10 GΩ | > 0.12 to 1.2 |
| 10 V | 12.0000000 V | 100 nV | > 10 GΩ | > 1.2 to 12 |
| 100 V | 120.000000 V | 1 µV | 10 MΩ | > 12 to 120 |
| 1000 V | 1050.00000 V | 10 µV | 10 MΩ | > 120 to 1000 |

`FIXEDZ ON` puts 10 MΩ across the input on every range (power-on OFF). It is suspended for AC, current and frequency functions and comes back when you return to DCV, but it stays on into ohms (see rule 6).

### DC current (I and LO terminals)

| Range | Full scale | Max res | Shunt | max_input |
|---|---|---|---|---|
| 100 nA | 120.000 nA | 1 pA | 545.2 kΩ | 0 to 0.12E-6 |
| 1 µA | 1.200000 µA | 1 pA | 45.2 kΩ | to 1.2E-6 |
| 10 µA | 12.000000 µA | 1 pA | 5.2 kΩ | to 12E-6 |
| 100 µA | 120.00000 µA | 10 pA | 730 Ω | to 120E-6 |
| 1 mA | 1.2000000 mA | 100 pA | 100 Ω | to 1.2E-3 |
| 10 mA | 12.000000 mA | 1 nA | 10 Ω | to 12E-3 |
| 100 mA | 120.00000 mA | 10 nA | 1 Ω | to 120E-3 |
| 1 A | 1.0500000 A | 100 nA | 0.1 Ω | to 1.2 |

DCI uses an armature relay: switching between DCI and another function takes 30 to 40 ms. Autozero cannot be turned off for DCI.

### Resistance (OHM 2-wire, OHMF 4-wire)

| Range | Full scale | Max res | Test current | max_input |
|---|---|---|---|---|
| 10 Ω | 12.00000 Ω | 10 µΩ | 10 mA | 0 to 12 |
| 100 Ω | 120.00000 Ω | 10 µΩ | 1 mA | to 120 |
| 1 kΩ | 1.2000000 kΩ | 100 µΩ | 1 mA | to 1.2E3 |
| 10 kΩ | 12.000000 kΩ | 1 mΩ | 100 µA | to 1.2E4 |
| 100 kΩ | 120.00000 kΩ | 10 mΩ | 50 µA | to 1.2E5 |
| 1 MΩ | 1.2000000 MΩ | 100 mΩ | 5 µA | to 1.2E6 |
| 10 MΩ | 12.000000 MΩ | 1 Ω | 500 nA | to 1.2E7 |
| 100 MΩ | 120.00000 MΩ | 10 Ω | 500 nA | to 1.2E8 |
| 1 GΩ | 1.2000000 GΩ | 100 Ω | 500 nA | to 1.2E9 |

- `OCOMP ON` (offset compensation) measures with the source off before each reading and doubles the reading time. It works on the 10 Ω to 100 kΩ ranges only; on 1 MΩ and above it is silently not applied.
- Keep `AZERO ON` for 4-wire ohms, or make every connection first and keep the lead resistance constant. With OCOMP on, zero and offset are measured together.
- Use `MATH NULL` to take out 2-wire lead resistance.
- Above 10 kΩ the automatic settling delay is longer; above 100 kΩ it is long and assumes less than 200 pF across the input.

### AC voltage and current

ACV and ACDCV ranges: 10 mV, 100 mV, 1 V, 10 V, 100 V, 1000 V (max_input 0 to 0.012 selects 10 mV, then ×10 per range). Maximum 6.5 digits. On the 10 mV and 100 mV ranges use shielded leads and a quiet environment.

ACI and ACDCI (analog method only): 100 µA (120.0000 µA FS, 100 pA, 730 Ω), 1 mA (1.200000, 1 nA, 100 Ω), 10 mA (12.00000, 10 nA, 10 Ω), 100 mA (120.0000, 100 nA, 1 Ω), 1 A (1.050000, 1 µA, 0.1 Ω). max_input 0 to 120E-6 selects 100 µA. The AC-DC converter needs at least 10 cycles. AC+DC current excludes AC below 10 Hz.

## Resolution and integration time

The integrating A/D sets resolution and normal-mode rejection by its integration time, given by `NPLC` (power-line cycles) or `APER` (seconds). The two commands replace each other.

| Digits (DCV) | NPLC at 60 Hz | NPLC at 50 Hz |
|---|---|---|
| 4.5 | 0 to 0.000030 | 0 to 0.000025 |
| 5.5 | 0.000036 to 0.000360 | 0.000030 to 0.000300 |
| 6.5 | 0.000366 to 0.030000 | 0.000305 to 0.025000 |
| 7.5 | 0.030006 to 1 | 0.025005 to 1 |
| 8.5 | 2 to 1000 | 2 to 1000 |

- Maximum digits: DCV 8.5 (7.5 on the 100 mV range); DCI and ohms 7.5 (6.5 on the 10 Ω range); analog ACV/ACI 6.5 (4.5 at NPLC up to 0.000030, 5.5 at 0.000036 to 0.000360, 6.5 above).
- NPLC steps: below 1 in steps of 0.000006 (60 Hz) or 0.000005 (50 Hz); 1 to 10 rounds up to an integer (2.5 becomes 3); above 10 rounds up to a multiple of 10 (21 becomes 30), and the reading is the average of 10-PLC integrations. NPLC 1 or more gives at least 60 dB normal-mode rejection; NPLC 1000 gives 80 dB; below 1 there is none.
- Table values: NPLC 0 = 500 ns (NPLC? then returns 29.99994E-6 at 60 Hz, 25E-6 at 50 Hz); NPLC 0.1 returns 99.9958E-3; NPLC 1 = 16.6667 ms (60 Hz) / 20 ms (50 Hz); NPLC 10 = 166.667 ms / 200 ms.
- `APER` 0 to 1 s in 100 ns steps, minimum 500 ns (smaller values give 500 ns; bare `APER` gives 500 ns). One integration, no averaging. Use an integer multiple of a noise period to reject it. `APER?` returns the actual integration time however it was set.
- `%_resolution` = (resolution / max_input) × 100, given as the last parameter of a function or `RANGE` command. `RES %res` does the same against the present range rather than max_input. With autorange, %res × full scale of the selected range is the minimum resolution. If %res is defaulted, the last NPLC/APER stays in force.
- Order matters. NPLC/APER sent before the resolution: whichever gives more integration wins. NPLC/APER sent after: NPLC/APER wins. `NPLC 1; DCV 10,1E-6` gives 100 nV resolution. `NPLC 0; DCV 6,.00167` gives 100 µV. NPLC 1000 overrides a coarser requested resolution. Common practice: send NPLC first for the rejection you need, then %res.
- `NDIG 3..8` (power-on 7, PRESET 6) masks the display only. It does not change GPIB or memory data. NDIG 7 shows 7.5 digits while the meter resolves 8.5 at NPLC 10.
- `LFREQ`: at power-on the meter measures the line and rounds to 50 or 60 Hz (400 Hz is treated as 50). `LFREQ LINE` measures and uses the exact frequency (360 to 440 Hz is divided by 8). `LFREQ 50` matches the DUT's line when it differs. Steps are 100 ns of period, so `LFREQ 60` reads back 59.99988. `LINE?` measures the line frequency.

### Autozero

`AZERO ON|OFF|ONCE` (1/0/2; OFF and ONCE are the same). ON takes a zero reading after every measurement and halves the reading rate. With OFF, one zero is taken at the first trigger-arm event (for TARM EXT, when the TARM EXT command executes) and refreshed when the function, range or integration time changes. In a thermally stable environment AZERO OFF loses little accuracy over about 10 minutes. Turn it off when level triggering DCV.

## AC voltage methods

`SETACV ANA|RNDM|SYNC` (1/2/3, power-on ANA) applies to ACV and ACDCV and persists until power cycle or reset.

| Method | Frequency | Best accuracy | Waveform | Reading rate |
|---|---|---|---|---|
| ANA (analog RMS) | 10 Hz to 2 MHz | 0.03 % | any | 0.8 to 50 rdg/s |
| SYNC (synchronous sampling) | 1 Hz to 10 MHz | 0.01 % | must repeat | 0.025 to 10 rdg/s |
| RNDM (random sampling) | 20 Hz to 10 MHz | 0.1 % | any | 0.025 to 45 rdg/s |

Crest factor up to 5:1 on all methods.

- **ANA**: resolution set by NPLC (above). AC+DC excludes AC below 10 Hz. Rate at full accuracy: 1 rdg/s for 10 Hz to 1 kHz, 10 rdg/s for 1 to 10 kHz, 50 rdg/s for 10 kHz to 2 MHz. To go faster, lower the resolution or set `DELAY` to about 10 / f_lowest (1 kHz content: at least 10 ms). Example: `NPLC .0001; SETACV ANA; ACV 10,1E-4` gives 10 µV resolution at about 40 s per reading.
- **SYNC**: resolution only through %res: 0.001 = 7.5 digits, 0.01 = 6.5 (default), 0.1 = 5.5, 1 = 4.5. It measures the signal period, then samples sequentially or in 20 µs bursts. It is DC-coupled internally and subtracts DC mathematically for ACV, so a large DC component can overload the range. Noise causes false level triggers; `LFILTER ON` helps. If the signal disappears the reading falls back to random sampling unless `SSRC ...,HOLD` is set. All of TARM, TRIG and NRDGS must be satisfied before the sync source starts.
- **RNDM**: fixed 4.5 digits, default %res 0.4. Sampling intervals 20 to 40 µs in 10 ns steps.
- `ACBAND low,high` (power-on 20,2E6 Hz) tells the meter the signal band. For ANA it sets the settling; for SYNC it sets timeouts and sampling; for FREQ/PER autorange it sets the autorange time, so set the low limit correctly. Put commands in this order for speed: `DELAY ...;ACBAND ...;ACV range`.
- `SSRC EXT|LEVEL[,AUTO|HOLD]` (2/7, 1/4; power-on LEVEL,AUTO) picks the sync source for SYNC ACV and sub-sampling. EXT paces from the Ext Trig input; LEVEL uses the level detector (automatic level and slope for SYNC ACV).
- Fast settings from the manual: SYNC about 10 rdg/s with `SETACV SYNC; ACV 10,2; ACBAND 5E3,8E3`; RNDM about 45 rdg/s with `ACV 10,6`; ANA faster with NPLC 0.1 plus ACBAND.

## Frequency and period

`FREQ [max_input][,%res]`, `PER [max_input][,%res]`. Input from `FSOURCE ACV|ACDCV|ACI|ACDCI` (codes 2/3/7/8, power-on ACV). Voltage source: 1 Hz to 10 MHz (period 100 ns to 1 s). Current source: 1 Hz to 100 kHz (10 µs to 1 s). The leading digit is a full 0-9 digit.

| %res | Gate | Digits (Table 3-11) | Rate (product note) |
|---|---|---|---|
| 0.00001 (default) | 1 s | 7 | 1 rdg/s |
| 0.0001 | 100 ms | 7 | 10 rdg/s |
| 0.001 | 10 ms | 6 | 73 rdg/s |
| 0.01 | 1 ms | 5 | 215 rdg/s |
| 0.1 | 100 µs | 4 | 270 rdg/s |

- Reading time is the longest of one input period, the gate time, or the 1.2 s default timeout.
- An overload means the amplitude is too large for the range, not the frequency.
- `LEVEL pct,AC|DC` and `SLOPE` set the counter's threshold, coupling and edge. FREQ/PER cannot use the LEVEL trigger or sample event, or the LINE trigger event. `LFILTER ON` (75 kHz single pole before the level detector) reduces noise.
- Examples: `FSOURCE ACV; FREQ 10,.00001`; `FSOURCE ACI; FREQ .01,.001` (10 mA range, 10 ms gate, 5 digits).

## Ratio

`RATIO ON` (select the function first) gives signal / reference. Signal on Input (DCV, ACV or ACDCV, any method), DC reference on the Ω Sense terminals, up to ±12 VDC, always autoranged. Sense LO and Input LO are common and must stay within 0.25 V of each other.

## Triggering

Three levels of event, all of which must be satisfied:

1. **Trigger arm** `TARM event[,number_arms]`: AUTO 1, EXT 2, SGL 3, HOLD 4, SYN 5. Power-on AUTO. `TARM SGL,n` arms n times; each arm gives one group (record) of NRDGS readings.
2. **Trigger** `TRIG event`: AUTO 1, EXT 2, SGL 3, HOLD 4, SYN 5, LEVEL 7, LINE 8. Power-on AUTO; bare `TRIG` = SGL. After a SGL trigger the event becomes HOLD.
3. **Sample** `NRDGS count[,event]`: count 1 to 16,777,215; events AUTO 1, EXT 2, SYN 5, TIMER 6, LEVEL 7, LINE 8. Power-on 1,AUTO.

Event meanings:

- AUTO: as soon as possible.
- EXT: negative TTL edge on the rear Ext Trig BNC, minimum width 250 ns, 5 MHz bandwidth. `TARM EXT` + `TRIG EXT` needs two edges.
- SGL: once on command, then HOLD.
- HOLD: stop.
- SYN: when the output buffer is empty, memory is off or empty, and the controller asks for data. With SYN at more than one level, one data request satisfies all of them and the first sample; each further read is one SYN event.
- LEVEL: input crosses `LEVEL` with `SLOPE`; DCV and direct-sampled digitizing only.
- LINE: zero crossing of the power line; not for SYNC/RNDM ACV, FREQ or PER.
- TIMER: sample at `TIMER` intervals (start-to-start), first sample after `DELAY`. Not for SYNC/RNDM ACV, FREQ or PER. It suspends autorange; autorange resumes when another sample event is chosen.

Illegal combinations (TARM / TRIG / NRDGS):

- any / EXT / SYN
- any / LEVEL / SYN or LINE
- any / LINE / SYN or LEVEL
- EXT / SGL
- SGL / SGL
- SYN / SGL

`TRIG SGL` or `TARM SGL` with a SYN sample event needs `INBUF ON` or the CR LF suppressed (end the command with `;` and no terminator), because the SGL command holds the bus that the SYN read needs.

Related commands:

- `TIMER seconds` (power-on 1 s; minimum is 1 / maximum rate, 100 ns steps, up to 6000 s). If the interval is too short you get TRIGGER TOO FAST.
- `SWEEP interval,count` is the same as `NRDGS count,TIMER` plus `TIMER interval`; whichever is sent last wins. Power-on 100E-9,1024; bare default 20 µs, 1024.
- `DELAY seconds`: time from the trigger event to the first sample, 1E-7 to 6000 s (100 ns steps; 10 ns for DS/SS); 0 = minimum; -1 = automatic settling based on function, range, resolution and ACBAND. A fixed delay persists until RESET, PRESET, power cycle or DELAY -1.
- `TBUFF ON` stores one EXT trigger that arrives during a reading instead of raising TRIGGER TOO FAST. Use it with a scanner on EXTOUT ICOMP.
- GPIB Group Execute Trigger (GET) triggers once like `TRIG SGL` if the meter is armed, then holds. If a subprogram is PAUSEd, GET resumes it instead.

Single reading pattern: `PRESET NORM; ... ; TRIG SGL`, then read. Several readings per `TRIG SGL`: send `INBUF ON` first, otherwise the bus is held until all are taken and only the last one is readable (unless memory is on).

Multiple arming example: `NRDGS 3; MEM FIFO; TARM SGL,10` gives 10 records of 3 readings; `RMEM 1,3,6` returns the three readings of record 6.

## Ext Out and scanners

`EXTOUT event[,polarity]` drives the rear Ext Out BNC (TTL). Events: OFF 0, ICOMP 1, ONCE 2, APER 3, BCOMP 4, SRQ 5, RCOMP 6. Polarity NEG 0 (low-going, default), POS 1. Power-on ICOMP,NEG.

- RCOMP: 1 µs pulse after each reading (for sampled ACV, after each computed reading).
- BCOMP: 1 µs pulse after each NRDGS/SWEEP burst.
- ICOMP: 1 µs pulse when the A/D has finished integrating, before the reading is complete (for DS/SS: when the track-and-hold has acquired). Pair it with `TBUFF ON` for relay scanners.
- APER: level output, active while the A/D integrates (including autozero and autorange). Use it to hold off external switching.
- SRQ: 1 µs pulse on any RQS-enabled status event.
- ONCE: one pulse, then the setting reverts to OFF.

Scanner loop: `PRESET NORM; MEM FIFO; TRIG EXT; EXTOUT RCOMP,NEG` (or BCOMP with NRDGS n per channel, or ICOMP with TBUFF ON). Wire the DMM's Ext Out to the scanner's channel-advance input and the scanner's channel-closed output to the DMM's Ext Trig. No controller waits are needed.

## Output formats, reading memory and reading data back

| Format | Code | Bytes (bus) | Bytes in memory | Use |
|---|---|---|---|---|
| ASCII | 1 | 15 + CR LF (`SD.DDDDDDDDESDD`) | 16 | slow, simple |
| SINT | 2 | 2, 16-bit two's complement × ISCALE | 2 | 3.5/4.5 digits, fixed range, fastest |
| DINT | 3 | 4, 32-bit two's complement × ISCALE | 4 | 5.5+ digits, fixed range |
| SREAL | 4 | 4, IEEE 754 single | 4 | up to 6.5 digits, any config |
| DREAL | 5 | 8, IEEE 754 double | 8 | 7.5/8.5 digits, any config |

- Binary data is big-endian (byte 0 holds the sign and exponent): Python `'>h'`, `'>i'`, `'>f'`, `'>d'`.
- `OFORMAT` (power-on ASCII) sets the GPIB format of readings. `MFORMAT` (power-on SREAL) sets the memory format, and sending it clears reading memory. Matching the two avoids conversion and gives the fastest transfer out of memory.
- SINT/DINT need the scale factor from `ISCALE?` (1 for ASCII and real formats). The factor depends on function, range and integration time when queried, and readings recalled from memory are scaled with the present configuration, so keep the configuration unchanged. Do not use SINT/DINT for FREQ/PER, with math (except STAT/PFAIL), or with autorange.
- Overload: memory stores ±1E+38. Output SINT +32767/-32768, DINT +2147483647/-2147483648, ASCII/SREAL/DREAL ±1.0E+38 (round SREAL to 7 digits before comparing).
- Binary formats have no line ending. Set `END ALWAYS` (EOI with the last byte of every reading) or `END ON` (EOI with the last byte of the last reading of a burst, or of each single reading), or read a known byte count. `END` codes: OFF 0 (power-on), ON 1, ALWAYS 2 (bare default).

Reading memory:

- `MEM OFF|LIFO|FIFO|CONT` (0/1/2/3; power-on OFF; bare MEM = FIFO).
  - FIFO: when full it keeps the old readings and stops storing; in high-speed mode TARM becomes HOLD.
  - LIFO: when full it overwrites the oldest readings.
  - OFF: keeps the readings already stored and stops storing.
  - CONT: resumes the previous mode without clearing.
  - Setting FIFO or LIFO erases memory.
- Capacity is the first value of `MSIZE?` (`reading_bytes,largest_free_subprogram_block`) divided by bytes per reading. Standard memory: 10,000 SINT readings. Option 001 (`OPT?` = 1): 75,000. `MSIZE` itself does nothing on the 3458A.
- `MCOUNT?` returns the number of readings stored.
- Reading numbers: the most recent reading is 1, the oldest has the highest number. Records (one NRDGS/SWEEP burst each) are numbered the same way.
- `RMEM first[,count[,record]]` (defaults 1,1,1) copies readings without removing them and turns memory OFF (resume with `MEM CONT`). Multiple ASCII readings come back comma-separated with one CR LF at the end. From the front panel, RMEM is the only way to view memory.
- **Implied read**: reading from the meter while memory is enabled and the output buffer is empty removes readings from memory (FIFO gives the oldest first, LIFO the newest), in OFORMAT. It does not turn memory off.

### Python: burst into memory, SREAL (no scaling)

```python
dmm.clear()
dmm.write("PRESET NORM")
dmm.write("DCV 10;NPLC 1;AZERO ON;MFORMAT SREAL;OFORMAT SREAL;MEM FIFO;NRDGS 500,AUTO;TRIG HOLD")
dmm.timeout = 120000
dmm.write("TRIG SGL")                  # INBUF OFF: returns when all 500 are stored
n = int(float(dmm.query("MCOUNT?")))
raw = dmm.read_bytes(4 * n)            # implied read, oldest first
vals = struct.unpack(">%df" % n, raw)
```

### Python: maximum-rate DCV (manual example, about 100 k readings/s)

```python
N = 10000
dmm.clear()
dmm.write("PRESET FAST")               # DCV 10, AZERO OFF, DISP OFF, TARM SYN, TRIG AUTO
dmm.write("TARM HOLD;NPLC 0;MEM FIFO;MFORMAT SINT;OFORMAT SINT")   # NPLC 0 = 500 ns; APER 1.4E-6 for >100 k/s
dmm.write("NRDGS %d,AUTO" % N)
s = float(dmm.query("ISCALE?"))        # before triggering
dmm.timeout = 60000
dmm.write("TARM SGL")                  # bus held until all N readings are in memory
raw = dmm.read_bytes(2 * N)
counts = struct.unpack(">%dh" % N, raw)
volts = [c * s for c in counts]
overload = [abs(c) >= 32767 for c in counts]
```

Direct to the controller without memory, the GPIB must keep up: SINT at 100 k readings/s needs over 200 kB/s, or the meter reports TRIGGER TOO FAST. Use a SYN arm or trigger so the controller is ready when the first reading appears (`PRESET FAST; APER 1.4E-6; OFORMAT SINT; NRDGS 30000,AUTO`, then read 60000 bytes; query `ISCALE?` afterwards).

## Speed

- **High-speed mode** applies to DCV, DCI, OHM/OHMF and DS/SS digitizing. The conditions are: integration below 10 PLC, `ARANGE OFF`, `DISP OFF`, `MATH OFF`, and SINT/DINT as the memory format (memory on) or output format (memory off). In this mode the meter processes no commands until the readings are done. It waits for each reading to be taken from the output buffer, so none are lost. The input buffer is disabled and END ALWAYS acts as END ON. Only Device Clear gets it out. Outside high-speed mode, a new reading overwrites an unread one in the output buffer.
- DCV rates: 4.5 digits at 100 k rdg/s down to 8.5 digits at 6 rdg/s. Function change + range change + measure + output: about 200 per second.
- What sets the reading rate: integration time for DC, ohms and analog AC; resolution for SYNC/RNDM; gate time for FREQ/PER. The fastest triggering is all events AUTO, or TIMER/SWEEP (rate = 1 / interval).
- To measure the rate: use TIMER/SWEEP, or count `EXTOUT RCOMP` pulses on a counter, or time a `TARM SGL` with INBUF OFF.
- Speed tips from the product notes:
  - fixed ranges, the right NPLC/APER and an explicit DELAY
  - store readings in memory
  - put repeated sequences in subprograms (they are compiled)
  - `DISP OFF` (halves execution time)
  - `AZERO OFF` (doubles the rate)
  - `DEFEAT ON` (small gain)
  - suppress the line ending on the last command so the controller is free
- Changing the integration time costs 6 to 10 ms. Staying at one setting (for example `APER 100E-6`, 6.5 digits, about 10 k rdg/s) is often faster overall.

## Digitizing

Three methods. The meter has no anti-alias filter; the sample rate is 1/TIMER or 1/SWEEP interval.

| Method | Function | Rate | Bandwidth | Signal |
|---|---|---|---|---|
| DCV (integrating A/D) | `DCV` with TIMER/SWEEP | up to 100 k samples/s | about 150 kHz, single-pole | any |
| Direct sampling (track-and-hold) | `DSAC`, `DSDC` | up to 50 k samples/s (20 µs min) | 12 MHz, 2 ns aperture | any |
| Sub-sampling (track-and-hold) | `SSAC`, `SSDC` | effective interval down to 10 ns | 12 MHz | must repeat |

### DCV digitizing

- Up to 28 bits. 16 bits at 100 k samples/s, 18 bits at 50 k samples/s. Trigger latency under 175 ns, sample-to-sample jitter under 100 ps. It cannot be AC coupled; aperture = integration time (500 ns to 1 s).
- Aperture vs 3 dB bandwidth error and bits:

  | Aperture | 3 dB point | Bits |
  |---|---|---|
  | 500 ns | 400 kHz | 15 |
  | 1 µs | 206 kHz | 16 |
  | 3 µs | 69 kHz | 17 |
  | 6 µs | 35 kHz | 18 |
  | 100 µs | 2 kHz | 21 |

- Use SINT for APER up to 1.4 µs, DINT above. SINT still works up to 10.8 µs (low bits dropped). Above 10.8 µs SINT takes the meter out of high-speed mode, so use DINT.
- `PRESET DIG` sets 256 samples at 50 k samples/s on the 10 V range, level trigger at 0 V, positive slope, AC coupled. That captures roughly 200 Hz to 25 kHz. Example at 100 k samples/s: `PRESET DIG; TIMER 10E-6; APER 1.4E-6; MEM FIFO; TARM SGL`, then read SINT and multiply by ISCALE?.

### Direct sampling (DSAC, DSDC)

`DSAC|DSDC [max_input][,%res ignored]`, default 10 V. No autorange.

| Range | max_input | SINT full scale | DINT full scale |
|---|---|---|---|
| 10 mV | 0 to 0.012 | 12 mV | 50 mV |
| 100 mV | to 0.12 | 120 mV | 500 mV |
| 1 V | to 1.2 | 1.2 V | 5.0 V |
| 10 V | to 12 | 12 V | 50 V |
| 100 V | to 120 | 120 V | 500 V |
| 1000 V | to 1000 | 1050 V | 1050 V |

- Use SINT if the peak stays below 120 % of range, DINT up to 500 %. `LEVEL` goes to ±500 % of range in 5 % steps for DS/SS. Slew limit: above 2 MHz and above 120 % of range.
- Sample with TIMER/NRDGS or SWEEP (SWEEP sets the sample event to TIMER). For content at 1 MHz or above, set `DELAY 500E-9` before the first sample.
- About 2 ns trigger jitter, and it can capture the peak of 40 ns pulses. Rise times under 10 ns cause overshoot, so band-limit them. For Nyquist the maximum signal frequency is 25 kHz (DCV path: 50 kHz).
- Example: `PRESET FAST; SWEEP 30E-6,200; DSDC 10; LEVEL 250,DC; TRIG LEVEL; MEM FIFO` (134 kB/s if sent direct to the controller).

### Sub-sampling (SSAC, SSDC)

- Repetitive signals only. The real sample rate is at most 50 k/s; the effective interval is 10 ns minimum (100 MS/s effective). An effective interval of 20 µs or more is plain direct sampling.
- Only TARM and the sync source (`SSRC LEVEL` default, or `SSRC EXT`) apply; TRIG and NRDGS events are ignored. Use `SWEEP eff_interval,count`, not NRDGS. Autozero and autorange are suspended. MATH is not allowed (MMATH is).
- With MEM OFF the output format is forced to SINT (restored when the function changes) and must be read at 100 kB/s. With memory: MEM FIFO, empty, MFORMAT SINT before the arm event, or you get SETTINGS CONFLICT. Memory then holds the reordered composite waveform and any OFORMAT can be used to read it.
- `DELAY` (default 0) is the time from each sync event to the first sample of each burst; use 500E-9 for content at 1 MHz or above.
- Effective intervals under 35 ns are covered by the 12 MHz bandwidth, which limits aliasing.
- `SSPARM?` returns N1,N2,N: N1 bursts of N samples and N2 bursts of N-1 samples. The meter reorders samples itself when memory is used. Without memory you reorder them yourself. With Inc = N1 + N2, for i = 1..N1 place burst i's N samples at positions i, i+Inc, i+2·Inc, ...; for i = N1+1..N1+N2 place N-1 samples the same way. Example: 22 samples at 5 µs on 10 kHz gives 2,2,6.
- Example: `PRESET FAST; MEM FIFO; MFORMAT SINT; SSDC 10; SWEEP 10E-9,4000; LEVEL 75,DC; SLOPE POS; SSRC LEVEL; TARM SGL`.

### Level triggering details

- `LEVEL pct[,DC|AC]` (coupling codes DC 1, AC 2; power-on 0,AC): DCV -120 to 120 % of range in 1 % steps; DS/SS -500 to 500 % in 5 % steps. Hysteresis ±4 % of range. AC-coupled input (DSAC/SSAC) forces AC level coupling.
- `SLOPE NEG|POS` (0/1, default POS). `LFILTER ON` puts a 75 kHz low-pass ahead of the level detector against false triggers.
- Example: `PRESET DIG; TRIG LEVEL; SLOPE NEG; LEVEL 50,AC`.
- Option 005 was the Waveform Analysis Library for HP BASIC (03458-80005).

## Math

`MATH op[,op2]` works in real time on each reading; `MMATH op[,op2]` post-processes readings as they leave memory (memory itself is unchanged). Two operations run in order, the second on the result of the first. `MATH OFF`, `MATH CONT` (re-enable the first), `MATH CONT,CONT`. Math persists until disabled, power cycle, RESET or PRESET. Enabling MMATH (other than STAT/PFAIL) disables MATH. MMATH STAT and MMATH PFAIL run once, immediately, on what is already in memory (store readings first, else MEMORY ERROR). Results go to the display from the front panel and to the output buffer from remote. FILTER, RMS, STAT and PFAIL restart when the configuration changes. Real-time math turns the display's half digit into a full digit.

Operation codes: OFF 0, CONT 1, CTHRM 3, DB 4, DBM 5, FILTER 6, FTHRM 8, NULL 9, PERC 10, PFAIL 11, RMS 12, SCALE 13, STAT 14, CTHRM2K 16, CTHRM10K 17, FTHRM2K 18, FTHRM10K 19, CRTD85 20, CRTD92 21, FRTD85 22, FRTD92 23.

| Op | Result |
|---|---|
| NULL | first reading goes into OFFSET; result = reading - OFFSET. Change OFFSET with SMATH only after the first reading. |
| SCALE | (reading - OFFSET) / SCALE. OFFSET is not loaded automatically (default 0); SCALE default 1. |
| PERC | (reading - PERC) / PERC × 100; PERC default 1 |
| DB | 20 log10(reading / REF); REF default 1 (gives dBV) |
| DBM | 10 log10(reading² / RES / 1 mW); RES default 50 Ω; DCV, ACV or ACDCV only |
| STAT | MEAN, SDEV, NSAMP, UPPER, LOWER |
| PFAIL | limits MIN (lower) and MAX (upper), default 0. Out of limits sets status bit 1 (value 2); display shows FAILED HIGH/LOW; PFAILNUM = readings passed before the first failure. |
| FILTER | r = prev·(DEGREE-1)/DEGREE + reading/DEGREE. DEGREE readings reach 63 %; τ ≈ DEGREE / sample rate for DEGREE > 10. |
| RMS | sqrt(prev²·(DEGREE-1)/DEGREE + reading²/DEGREE), for digitized low-frequency signals. STAT SDEV of a digitized sine also gives its AC RMS. |
| CTHRM2K / FTHRM2K | 2 kΩ thermistor (40653A), °C / °F |
| CTHRM / FTHRM | 5 kΩ thermistor (40653B); use the 10 kΩ ohms range or higher |
| CTHRM10K / FTHRM10K | 10 kΩ thermistor (40653C) |
| CRTD85 / FRTD85 | 100 Ω RTD, alpha 0.00385 (40654A/B) |
| CRTD92 / FRTD92 | 100 Ω RTD, alpha 0.003916 |

For temperature use OHMF: `PRESET NORM; OHMF 10E3; MATH CTHRM10K; TRIG SGL`.

Registers: `SMATH register,value` writes; `RMATH register` reads (ASCII). Codes: DEGREE 1, LOWER 2, MAX 3, MEAN 4, MIN 5, NSAMP 6, OFFSET 7, PERC 8, REF 9, RES 10, SCALE 11, SDEV 12 (read only), UPPER 13, HIRES 14 (unused), PFAILNUM 15. The default register is DEGREE. `SMATH reg` with no value stores the last reading (`SMATH RES` loads the last reading into RES); -1 is written literally, not taken as a default. STAT overwrites its registers when enabled.

## Status, SRQ and errors

Status byte:

| Bit | Value | Meaning |
|---|---|---|
| 0 | 1 | subprogram complete |
| 1 | 2 | high or low limit exceeded (PFAIL) |
| 2 | 4 | `SRQ` command executed |
| 3 | 8 | power-on |
| 4 | 16 | ready for instructions |
| 5 | 32 | error (masked by EMASK) |
| 6 | 64 | service requested |
| 7 | 128 | data available |

- `RQS value` enables bits to assert SRQ (bit 6 cannot be disabled); `RQS 42` enables bits 1, 3 and 5. Power-on RQS is 8 if power-on SRQ was enabled at power-down (stored), else 0.
- `STB?` returns the sum without clearing it and never shows bit 4. It also replaces any reading in the output buffer. A serial poll does not interrupt the CPU, shows the ready bit and leaves output data alone; with SRQ true it clears bits whose condition has gone.
- `CSB` clears the register; bits 4, 5 and 6 come back if their condition persists. Clearing bit 6 drops SRQ.

Error register (`ERR?` returns the sum and clears it, the ERR annunciator and status bit 5). The same values form `EMASK` (power-on 32767), which masks only status bit 5 and SRQ, not the register:

| Value | Error |
|---|---|
| 1 | hardware (details in AUXERR?) |
| 2 | calibration or autocal error |
| 4 | trigger too fast |
| 8 | syntax |
| 16 | command not allowed from remote |
| 32 | undefined parameter |
| 64 | parameter out of range |
| 128 | memory error |
| 256 | destructive overload |
| 512 | out of calibration |
| 1024 | calibration required |
| 2048 | settings conflict |
| 4096 | math error |
| 8192 | subprogram error |
| 16384 | system error |

Auxiliary register (`AUXERR?` returns the sum and clears it; it cannot be masked; reading it does not clear ERR bit 0, so read `ERR?` too):

| Value | Error |
|---|---|
| 1 | slave processor not responding |
| 2 | DTACK failure |
| 4 | slave processor self-test failure |
| 8 | isolator test failure |
| 16 | A/D convergence failure |
| 32 | calibration value out of range |
| 64 | GPIB chip failure |
| 128 | UART failure |
| 256 | timer failure |
| 512 | internal overload |
| 1024 | ROM checksum, low byte |
| 2048 | ROM checksum, high byte |
| 4096 | nonvolatile RAM failure |
| 8192 | option RAM failure |
| 16384 | cal RAM write or protection failure |

`ERRSTR?` returns `number,"message"` for the lowest set bit, reading the auxiliary register first (200-series numbers) and then the error register (100-series), and clears that bit. It returns `0,"NO ERROR"` when both are empty. A hardware error sets an AUXERR bit and ERR bit 0; a programming error sets only the ERR register.

`BEEP OFF|ON|ONCE` (stored): 1 kHz beep on errors. `TONE` beeps once.

### GPIB interface

- Capabilities SH1 AH1 T5 L4 SR1 RL1 PP0 DC1 DT1 C0 E2 (tri-state, up to 1 MB/s).
- IFC clears the interface.
- Device Clear: see rule 2.
- GTL with LLO enables the keys until the next remote command. LLO disables the Local key and is cleared only by REN false or a power cycle.
- `LOCK ON` disables the keyboard including Local, independently of LLO; only the controller or a power cycle re-enables it. Clear both LOCK and LLO to get the keys back.

## Subprograms, stored states, user keys and internal BASIC

### Subprograms

- `SUB name` ... `SUBEND` stores a command sequence. Names are up to 10 characters, letter first, `_` and `?` allowed, and must not clash with a command, parameter or state name. An integer 0 to 127 becomes SUBn.
- Subprograms and states share 14 kB of continuous memory; when it is full you get a memory error (ERR bit 7). Storing needs at least 800 bytes free.
- The ASCII source is kept in continuous memory and a compiled copy in volatile memory. Storing a sub with the same name overwrites it.
- `CALL name` runs it; nesting goes up to 10 levels. With INBUF OFF the bus is held until the subprogram finishes or PAUSEs.
- `PAUSE` suspends it and releases the bus; `CONT` or GET resumes it (GET does not trigger in that case). Only one paused subprogram is kept. A sub containing PAUSE cannot be called from another sub. `PAUSE?` returns 1 or 0.
- Readings inside a subprogram are taken only by `TARM SGL` or `TRIG SGL` (the sub waits until they are done; configure before them). Other trigger settings take effect after the sub completes. `TARM EXT` inside a sub waits for the external edge before the next line, which synchronises the sub with other equipment.
- SUBEND sets status bit 0 (subprogram complete).
- `SUB 0` runs automatically at power-on and front-panel Reset (for example `RSTATE 0; LFREQ LINE`).
- `COMPRESS name` drops the ASCII source; the compiled copy lives only in volatile memory and is lost at power-off or shifted Reset. Compress each sub before downloading the next, to avoid fragmentation.
- `DELSUB name` deletes one; `SCRATCH` deletes all subprograms and states and defragments memory.
- These cannot be stored inside a sub: CONT, COMPRESS, DELSUB, SCRATCH, a second SUB, Device Clear. RESET aborts execution. A sub is aborted by an error or Device Clear.
- A called sub must exist before you store the caller (syntax is checked at store time). A 10-command sub takes about 600 bytes. Good practice: `SCRATCH`, then download all subs at the start of a test program.

### Stored states

- `SSTATE name` (up to 10 characters, or 0 to 127 stored as STATEn; state 0 is overwritten at power loss with the power-down state). `RSTATE name` (default 0), `PURGE name`.
- About 300 bytes each; at most 46 states with no subprograms stored.
- A state does not include subprograms, reading memory, user keys or the MENU mode. Of the math registers it stores DEGREE, LOWER, OFFSET, PERC, REF, RES, SCALE and UPPER; the others recall as 0. NULL in a recalled state reloads OFFSET from the first reading.

### User keys and the front panel

- `DEFKEY n,'string'` (n 0 to 9 or F0 to F9, up to 40 characters, `;` between commands, no embedded quotes) defines a user key. `DEFKEY DEFAULT` clears all. `DEFKEY? n` returns the string. Keys are battery backed; keys defined from remote cannot be edited from the panel.
- `MENU SHORT|FULL` (0/1, stored, default FULL). The front-panel menu shows CAL? and SCAL only in FULL mode.
- Front-panel recall (Last Entry) holds previous commands, but not immediate-execute keys and not commands containing the security code.
- Shifted keys give alphabetic access to every command and parameter, scrolled with the menu keys.
- Front-panel queries show results on the display only; remote queries put results in the output buffer only.
- `DISP OFF|ON|MSG|CLR[,'message']` (0/1/2/3, message up to 75 characters; quote it if it has a space, comma or semicolon). With DISP OFF the display shows the message or dashes, and the annunciators are off except ERR. `DSP?` reads the display (internal BASIC).
- Annunciators: SMPL, REM, SRQ, TALK, LSTN, AZERO OFF, MRNG, MATH, ERR, SHIFT, MORE INFO (press the More Info key to see what is in a non-standard state).

### Internal BASIC (inside subprograms)

- No strings, line numbers, GOTO, GOSUB, local variables or parameters. Arrays use option base 0.
- Variables are global and volatile (lost at power-off; SCRATCH purges them). Names up to 10 characters.
- Declarations:
  - `LET var=expr` (the LET keyword is required)
  - `REAL` (64-bit) and `INTEGER` (16-bit, -32767 to 32767), scalars and arrays
  - `DIM name(size)` (real array)
  - `FILL array,list`: volatile and not preserved across a power cycle in a sub, so use LETs there
  - Subscripts 0 to 999, about 10 kB total. `SIZE? array` returns the element count.
  - Every sub that uses a variable must declare it the same way; changing a type needs SCRATCH.
- Operators and functions:
  - arithmetic `+ - * / ^ DIV MOD`; write unary minus as `0-B`
  - comparison `= > < >= <= <>`; logic `AND OR EXOR NOT`
  - `ABS SQR LOG` (ln) `EXP LGT` (log10) `SIN COS ATN` (radians)
  - 16-bit bit operations `BINAND BINCMP BINEOR BINIOR BIT(x,pos) ROTATE SHIFT`
- Control: `FOR ... NEXT [STEP]`, `WHILE ... ENDWHILE`, `IF ... THEN [ELSE] ENDIF` (nest 7 deep).
- I/O and other commands:
  - `ENTER var` removes one reading from memory
  - `OUTPUT var` sends to the display or GPIB, depending on the caller
  - `U_RANGE`, `D_RANGE` move up or down one range
  - `DSP string|var` (firmware 2.1 and later), `SCROLL LEFT|RIGHT`, `ECHO string`
  - `RMATHV register,var` (firmware 5.1 and later)
  - `WAIT msec` (up to 32 s), `RETURN`
  - `CALLARRAY array,list` runs 68000 machine code loaded with FILL
- `CAT` lists SUB, IARRAY, RARRAY, STATE, INT and REAL names and ends with "DONE" (up to 400 characters). `LIST name` returns a sub's source, ending with "SUBEND".

Manual example, trimmed mean of 300 stored readings:

```
SUB CALC_MEAN
MMATH STAT
RMATHV MEAN,AVG
RMATHV UPPER,BIG
RMATHV LOWER,SMALL
LET M=(AVG*300-BIG-SMALL)/298
OUTPUT M
SUBEND
```

## Autocal (ACAL)

`ACAL [type][,security_code]` corrects drift of everything except the two external references, using the internal 7 V reference and 40 kΩ reference resistor. It recalculates 197 of the 253 calibration constants.

| Type | Code | Covers | Time (User's Guide) | Settle after |
|---|---|---|---|---|
| ALL | 0 (default) | everything | about 16 min | 30 min |
| DCV | 1 | DC voltage and the basis for all functions | about 2 min 45 s | 15 min |
| AC | 2 | ACV/ACDCV all methods, ACI, digitizing, FREQ/PER | about 2 min 45 s | 15 min |
| OHMS | 4 | ohms, DCI, ACI | about 11 min | 30 min |

The front-panel guide gives about 12 min for ALL, 2 min DCV, 1 min AC and 9 min OHMS; the Calibration Manual says about 10 min for OHMS and 1 min for AC. Allow for the longer times.

- Warm the meter up for at least 2 hours, thermally stable, before ACAL (4 hours before external calibration). Disconnect the inputs.
- Run ACAL ALL every 24 hours, or when `TEMP?` has moved ±1 °C from the last calibration or autocal. ACAL reduces the DCV gain temperature coefficient from about 1 ppm/°C to 0.15 ppm/°C, and ACV from 30 ppm/°C to under 1 ppm/°C.
- Run DCV before AC or OHMS.
- Never power-cycle or reset during ACAL. The meter then reports ACAL REQUIRED and you must run ACAL ALL.
- If autocal is secured, the security code is required (`ACAL ALL,3458`) and CALNUM increments with each autocal.
- Send `INBUF ON` first if you do not want the bus held for the whole autocal; with INBUF OFF, set the VISA timeout to about 20 minutes and the write returns when ACAL is done.
- ACAL constants are kept in continuous memory.

## Calibration security

- `SECURE old_code,new_code[,acal_secure]` changes the code. Codes are integers from -2.1E9 to 2.1E9; new_code 0 removes security for calibration and autocal. acal_secure OFF 0 / ON 1 says whether ACAL also needs the code. Examples: `SECURE 3458,4448,ON`; `SECURE 3458,0`.
- Factory code: 3458. The User's Guide examples print "3458A"; the Calibration Manual and the QRG say 3458, which is a valid integer code.
- The factory acal_secure setting conflicts between manuals (the Calibration Manual chapter 1 says ON, other pages say OFF). Check by sending `ACAL DCV` without a code and looking at the error register.
- The Last Entry key never shows security codes.
- Lost code (service-trained personnel, power off, covers off): move jumper JM600 on the 03458-66505 board (03458-66515 with Option 001) from left to right, which sets the code to 0. Power up and send `SECURE 0,new_code`, then put the jumper back. If no new code is entered, the original code returns.
- Hardware lockout: jumper J132 on the same board to the right refuses CAL and ACAL even with the correct code; to the left allows them. Seal the cover.
- `CALNUM?` counts external calibrations (and autocals if autocal is secured). It is held in protected memory. To detect unauthorised calibration, store it in the cal string (`CALSTR 'CALNUM=270'`) and compare later.
- `CALSTR 'string'[,code]` stores up to 75 characters (quotes required; code needed if secured; remote only). `CALSTR?` always works. Store the date and internal temperature, for example `CALSTR 'CALIBRATED 04/02/1987; temp(C)=43.1'`.
- Appendix C of the User's Guide describes a switch lockout: remove the pushrods of the Terminals and Guard switches and fit caps (service personnel; reinstall the cover ground screws and run ACAL ALL afterwards).

## Adjustment (external calibration)

The 3458A has no potentiometers. It needs three external inputs: a 4-terminal short, a 10 V DC standard and a 10 kΩ standard. The AC adjustment is needed only every 2 years or after repair of the 03458-66502 or 66503 assembly. The whole procedure takes about an hour. Calibration interval: typically 1 year. From the front panel, CAL? and SCAL appear only with `MENU FULL`.

Conditions: 4-hour warm-up, ambient 15 to 30 °C and stable, no drafts. Use low-thermal, low-dielectric-absorption cables.

Equipment:

- low-thermal 4-terminal short (12/14 AWG solid copper)
- 10 V standard (Fluke 732A). Any 1 to 12 V works, but below 10 V the accuracy degrades.
- 10 kΩ standard (Fluke 742-10K). Any 1 to 12 kΩ works, but below 10 kΩ the accuracy degrades.
- For AC: 3325A synthesizer, thermal converters 3 V / 1 V / 0.5 V (Ballantine 1395A-3/-1/-0.4), 50 Ω cable and load, BNC-banana adapter 1251-2277.

Before you start: inputs disconnected, DCV 100 mV range, Terminals Front, 4-hour warm-up. Record `CALNUM?` and `TEMP?` before and after.

1. **Front offset.** Connect the 4-terminal short to front Input HI/LO and Sense HI/LO. Wait 5 minutes without touching it. Send `CAL 0` (about 5 min; adjusts DCV, DCI, OHM and OHMF offsets).
2. **Rear offset.** Move the short to the rear terminals, set Terminals to Rear, wait 5 min, send `CAL 0` again (about 5 min).
3. **DC gain.** DCV, Terminals Front, standard on Input HI/LO. Either connect a guard wire and set Guard Open, or set Guard To LO. Send `CAL <exact value>`, for example `CAL 10.0001` (about 2 min). This measures the internal 7 V reference and includes ACAL DCV.
4. **Ohms and DCI gain** (after DC gain). `OHMF`, `OCOMP ON`, 4-wire to the standard, guard as above. Send `CAL <exact value>`, for example `CAL 10.003E3` (about 12 min). Default settling is 50 ms; for slow cables or a standard with dielectric absorption, set `DELAY 200E-3` before CAL (values below 50 ms become 50 ms; never above 60 s). This adjusts the internal 40 kΩ reference. Then `ACAL AC` (about 2 min) and wait 15 min.
5. **AC (every 2 years).** Run `ACAL AC`, wait 15 min, then `RESET`. Set Terminals Front and Guard To LO.
   - First characterise the synthesizer's flatness with the thermal converters. Line A: 3 V 100 kHz, note the DC reading. Line C: 3 V 2 MHz, adjust the synthesizer to within 0.2 % of A. Repeat for D (3 V 8 MHz), E (1 V 100 kHz), F (1 V 8 MHz), G (100 mV 100 kHz) and H (100 mV 8 MHz).
   - Then drive the DMM through the 50 Ω load:

   | Signal | ACBAND | Command | Adjusts |
   |---|---|---|---|
   | 3 V 100 kHz (A) | 10,2E6 | `SCAL 1E5` | frequency (crystal) |
   | 3 V 100 kHz (A) | 10,2E6 | `SCAL 10` | low-frequency reference |
   | 3 V 2 MHz (C) | 10,10E6 | `SCAL 10` | interpolator and flatness |
   | 3 V 8 MHz (D) | 10,10E6 | `SCAL 10` | flatness |
   | 1 V 100 kHz (E) | 10,2E6 | `SCAL 1` | |
   | 1 V 8 MHz (F) | 10,10E6 | `SCAL 1` | |
   | 100 mV 100 kHz (G) | 10,2E6 | `SCAL 0.1` | |
   | 100 mV 8 MHz (H) | 10,10E6 | `SCAL 0.1` | |

   The voltages may be 3 to 10 V, 300 mV to 1 V and 30 to 100 mV; keep the same SCAL arguments. The meter can stay in DCV during SCAL. Finish with `ACAL AC`.

`CAL value[,code]` and `SCAL value[,code]` need the code when the meter is secured (code not 0).

### Calibration constants (`CAL?`)

`CAL? const_id[,item]`: item 0 = nominal, 1 = actual value (default), 3 = upper limit, 5 = lower limit. Use `QFORMAT ALPHA` to get the description text with the value.

| ID | Constant |
|---|---|
| 1 | 40 K reference (from CAL 10E3) |
| 2 | 7 V reference (from CAL 10) |
| 3-12 | DCV zero, front/rear, 100 mV to 1 kV |
| 13-30 | ohm zero, front/rear, 10 Ω to 1 GΩ |
| 31-48 | ohmf zero, front/rear |
| 49-57 | offset ohm 10 Ω to 1 GΩ |
| 58 | CAL 0 temperature |
| 59 | CAL 10 temperature |
| 60 | CAL 10K temperature |
| 61 | vos dac |
| 62-69 | DCI zero rear 100 nA to 1 A |
| 70-74 | DCV gain 100 mV to 1 kV |
| 75-83 | ohm gain |
| 84-92 | ohm ocomp gain |
| 93-100 | DCI gain |
| 101-106 | precharge dac, mc dac, high speed gain, il, il2, rin (10 MΩ attenuator) |
| 107-112 | aperture constants |
| 113-174 | under/overload limits for DCV, ohms (with ocomp), DCI |
| 175 | ACAL DCV temperature |
| 176 | ACAL ohm temperature |
| 177 | ACAL ACV temperature |
| 178-200 | AC, ACDC, ACDCI offset dacs and flatness dacs |
| 201-204 | level dacs |
| 205-209 | DCV trigger offset |
| 210-227 | ACDCV/ACV sync offset and gain |
| 228-229 | ab ratio, gain ratio |
| 230-241 | ACV analog gain and offset |
| 242-246 | rmsdc ratio, sampdc ratio, ACI gain, freq gain, attenuator HF dac |
| 247-252 | amplifier HF dac 10 mV to 1 kV (SCAL) |
| 253 | interpolator (SCAL) |

Of the 253 constants:

- 44 are set externally: 6 DCV offsets, 18 2-wire offsets, 18 4-wire offsets, the voltage reference and the resistance reference.
- 6 are one-time AC constants: frequency, interpolator and HF response.
- 6 are temperatures.
- 197 are recalculated by ACAL.

`TEST` checks that all constants are within limits.

How the internal transfer works (Product Note 3458A-3):

- The A/D is a multislope integrator with INL under 0.1 ppm and DNL 0.02 ppm, verified against a Josephson array.
- The internal reference drifts under 2 ppm on average in the first 90 days (3-sigma under 4 ppm). DCV transfer short-term stability is 0.1 ppm. The internal reference resistor is 5 ppm/year and 1 ppm/°C.
- DC gain transfers from the 10 V range to 1 V and 100 mV, and to 100 V and 1000 V through the 100:1 attenuator. The cumulative transfer error is under 1 ppm on the three lowest DCV ranges.

## Operational verification (quick check)

This is the Calibration Manual's short test, at 90 % confidence. It needs a stable DCV and ohms standard (Fluke 5700A), a transfer 3458A with Option 002 calibrated within 90 days, and a low-thermal short and leads.

1. Warm up 4 hours. The internal temperature must be within 5 °C of the last calibration: compare `TEMP?` with `CAL? 59` (DCV cal temperature) and `CAL? 60` (ohms cal temperature).
2. `TEST` must report SELF TEST PASSED.
3. `ACAL OHMS`, wait 30 min. Set both DMMs to `OHM; NDIG 8; NPLC 100; TRIG SGL`. Measure a 2-wire short on the 10 Ω range after 5 min, front and rear: limit 0.25007 Ω.
4. 10 kΩ by transfer (OHMF): the difference must be within 0.142 Ω (14.2 ppm).
5. `ACAL DCV`, wait 15 min. On the 10 V range compare +10 V and -10 V: difference limit 89.2 µV (standard reference) or 62.4 µV (Option 002). Offset with the short, 10 V range, after 5 min: 2.3 µV.
6. Turnover check: with readings R4 (+10 V), R5 (-10 V) and R6 (short), A = R4 - R6 and B = R5 - R6; ||A| - |B|| must be 4 µV or less.

## Performance verification (1-year limits)

Method: run ACAL for the function on both the transfer DMM and the unit under test (UUT) and let them settle (ALL 30, DCV 15, OHMS 30, AC 15 min). Measure the source with the transfer DMM, then with the UUT. Compare |transfer - UUT| with the limit.

Equipment: Fluke 5700A, 3325A, a transfer 3458A with Option 002 calibrated within 90 days, low-thermal short and leads (11053A, 11174A, 11058A), shielded leads 11000-60001. The internal temperature must be within 5 °C of the last adjustment (`CAL? 58`, `59`, `60`). If it is not, check the fan, clean the filter and keep the ambient near 25 °C. Clean the terminals with an alcohol swab, use NPLC 1000 (80 dB NMR), connect guard to source LO with Guard Open, and watch for thermal EMF, EMI and ground loops. The 24-hour and 90-day specifications need checks at those intervals.

**DCV** (`ACAL DCV`, 15 min; `DCV; NDIG 8; NPLC 100; TRIG SGL`):

- Offsets with the short, front and rear. Wait 5 min first on 100 mV; that thermal stability carries over to 1 V and 10 V. On 100 V and 1000 V the input relays are open.
- Gain: null the transfer DMM and the UUT on the shorted source through a shielded low-thermal cable with guard, then apply the points below. Ramp the source down after the 1000 V point.

| Range | Offset limit | Gain point | Gain limit, std / Opt 002 |
|---|---|---|---|
| 100 mV | 1.06 µV | 100 mV | 2.12 / 1.88 µV |
| 1 V | 1.06 µV | 1 V | 9.98 / 7.40 µV |
| 10 V | 2.3 µV | ±1 V | 11.1 / 8.5 µV |
| 10 V | | ±10 V | 89.2 / 62.4 µV |
| 100 V | 36 µV | 100 V | 1.114 / 0.853 mV |
| 1000 V | 100 µV | 1000 V | 23.96 / 19.34 mV |

**ACV, analog method** (`ACAL AC`, 15 min). Transfer DMM: `ACV; SETACV SYNC; ACBAND 10,2E6; RANGE 10; RES .001; TRIG SGL; LFILTER ON`. UUT: the same but `SETACV ANA; RES .01`. Limits are the same with and without Option 002.

| Range | Input | Limit |
|---|---|---|
| 100 mV | 100 mV 1 kHz | 0.0250 mV |
| 1 V | 1 V 1 kHz | 0.250 mV |
| 10 V | 1 V 1 kHz | 0.96 mV |
| 10 V | 10 V 20 Hz | 13.38 mV |
| 10 V | 10 V 1 kHz | 2.50 mV |
| 10 V | 10 V 20 kHz | 2.72 mV |
| 10 V | 10 V 100 kHz | 53.72 mV |
| 10 V | 10 V 1 MHz | 554.5 mV |
| 100 V | 100 V 1 kHz | 36.4 mV |
| 1000 V | 700 V 1 kHz | 0.544 V |

**DCI** (`ACAL OHMS`, 30 min; `DCI; NDIG 8; NPLC 100`; I and LO terminals). Offsets with the input open. If one is out of limits, run ACAL again, wait 30 min and repeat.

| Range | Offset (open) | Gain at full range |
|---|---|---|
| 100 µA | 0.95 nA | 3.56 nA |
| 1 mA | 6.5 nA | 32.3 nA |
| 10 mA | 65 nA | 323 nA |
| 100 mA | 650 nA | 4.89 µA |
| 1 A | 11.5 µA | 134.9 µA |

**Ohms** (`ACAL OHMS` again if the temperature moved more than 1 °C since the DCI tests; 30 min). Transfer DMM: `OHMF; NDIG 8; NPLC 100; OCOMP ON`. UUT: the same. Offsets: 2-wire short on 10 Ω after 5 min, front and rear, 0.25007 Ω; 4-wire short `OHMF,10`, front and rear, 0.00007 Ω. OHMF gain:

| Range | Limit |
|---|---|
| 10 Ω | 0.28 mΩ |
| 100 Ω | 2.31 mΩ |
| 1 kΩ | 14.2 mΩ |
| 10 kΩ | 142 mΩ |
| 100 kΩ | 1.42 Ω |
| 1 MΩ | 20.9 Ω |
| 10 MΩ | 703 Ω (may be done 2-wire; sense-lead leakage) |

**Frequency** (`FREQ; TRIG SGL; FSOURCE ACDCV; LEVEL 0,DC`; 3325A at 1 V p-p): 1 Hz within ±0.000500 Hz; 10 MHz within ±0.00100 MHz (100 Hz, 10 ppm).

## Command reference

Codes in parentheses are the numeric values accepted in place of the keyword and returned by queries with QFORMAT NORM. "P-on" is the power-on/RESET value; "bare" is the value used when the parameter is omitted.

| Command | Parameters | P-on | Bare | Notes |
|---|---|---|---|---|
| `ACAL` | ALL(0) DCV(1) AC(2) OHMS(4) [,code] | | ALL | autocal; see Autocal |
| `ACBAND` | low,high Hz | 20,2E6 | 20,2E6 | AC signal band; `ACBAND?` returns "low,high" |
| `ACDCI`, `ACDCV`, `ACI`, `ACV` | [max_input][,%res] | | AUTO | AC functions |
| `ADDRESS` | 0-31 | stored, factory 22 | | front panel only; 31 = talk-only |
| `APER` | 0-1 s, 100 ns steps | (NPLC 10) | 500 ns | integration time |
| `ARANGE` | OFF(0) ON(1) ONCE(2) | ON | ON | not for DS/SS or with TIMER/SWEEP |
| `AUXERR?` | | | | auxiliary error sum, clears it |
| `AZERO` | OFF(0) ON(1) ONCE(2) | ON | ON | |
| `BEEP` | OFF ON ONCE | stored | ONCE | |
| `CAL` | value[,code] | | | external adjustment: 0, 10 V, 10 kΩ |
| `CAL?` | const_id[,0/1/3/5] | | | calibration constants |
| `CALL` | [name] | | 0 | run subprogram |
| `CALNUM?` | | | | calibration count |
| `CALSTR` | 'string'[,code] | | | up to 75 characters |
| `CAT` | | | | list subs, states, variables |
| `COMPRESS` | name | | | drop sub source |
| `CONT` | | | | resume paused sub |
| `CSB` | | | | clear status byte |
| `DB`, `DBM` | (via MATH) | | | |
| `DCI`, `DCV` | [max_input][,%res] | DCV AUTO | AUTO | |
| `DEFEAT` | OFF ON | OFF | OFF | see safety |
| `DEFKEY` | n,'string' / DEFAULT | stored | | user keys |
| `DELAY` | -1, 0, 1E-7-6000 s | -1 | -1 (auto) | |
| `DELSUB` | name | | | |
| `DIAGNOST` | | | | service only (Assembly Level Repair Manual) |
| `DISP` | OFF(0) ON(1) MSG(2) CLR(3)[,'msg'] | ON | ON | |
| `DSAC`, `DSDC` | [max_input][,%res ignored] | | 10 | direct sampling |
| `EMASK` | 0-32767 | 32767 | 32767 | error mask for status bit 5 |
| `END` | OFF(0) ON(1) ALWAYS(2) | OFF | ALWAYS | EOI |
| `ERR?` | | | | error register sum, clears it |
| `ERRSTR?` | | | | `n,"message"`, clears that bit |
| `EXTOUT` | OFF(0) ICOMP(1) ONCE(2) APER(3) BCOMP(4) SRQ(5) RCOMP(6)[,NEG(0)/POS(1)] | ICOMP,NEG | ICOMP,NEG | |
| `FIXEDZ` | OFF(0) ON(1) | OFF | ON | 10 MΩ input; bare command enables it |
| `FREQ` | [max_input][,%res] | | AUTO,.00001 | |
| `FSOURCE` | ACV(2) ACDCV(3) ACI(7) ACDCI(8) | ACV | ACV | FREQ/PER input |
| `FUNC` | function[,max_input][,%res] | DCV | DCV,AUTO | header optional |
| `ID?` | | | | model string |
| `INBUF` | OFF(0) ON(1) | OFF | ON | 255-character input buffer |
| `ISCALE?` | | | | SINT/DINT scale factor |
| `LEVEL` | pct[,DC(1)/AC(2)] | 0,AC | 0,AC | trigger/counter threshold |
| `LFILTER` | OFF ON | OFF | ON | 75 kHz filter in level path |
| `LFREQ` | 45-65, 360-440 Hz / LINE | measured, rounded | measured exact | |
| `LINE?` | | | | measures line frequency |
| `LIST` | name | | | sub source |
| `LOCK` | OFF ON | OFF | ON | keyboard lock |
| `MATH` | op[,op] | OFF | | real-time math |
| `MCOUNT?` | | | | readings in memory |
| `MEM` | OFF(0) LIFO(1) FIFO(2) CONT(3) | OFF | FIFO | |
| `MENU` | SHORT(0) FULL(1) | stored | FULL | |
| `MFORMAT` | ASCII(1) SINT(2) DINT(3) SREAL(4) DREAL(5) | SREAL | SREAL | clears memory |
| `MMATH` | op[,op] | OFF | | post-process math |
| `MSIZE?` | | | | "reading_bytes,largest_sub_block" |
| `NDIG` | 3-8 | 7 | 7 | display digits only |
| `NPLC` | 0-1000 | 10 | 0 | |
| `NRDGS` | count[,AUTO(1) EXT(2) SYN(5) TIMER(6) LEVEL(7) LINE(8)] | 1,AUTO | 1,AUTO | |
| `OCOMP` | OFF ON | OFF | ON | ohms offset compensation |
| `OFORMAT` | ASCII(1) SINT(2) DINT(3) SREAL(4) DREAL(5) | ASCII | ASCII | |
| `OHM`, `OHMF` | [max_input][,%res] | | AUTO | 2-wire, 4-wire |
| `OPT?` | | | | 0 or 1 (Option 001) |
| `PAUSE` | | | | in subs only |
| `PER` | [max_input][,%res] | | AUTO,.00001 | |
| `PRESET` | FAST(0) NORM(1) DIG(2) | | NORM | |
| `PURGE` | name | | | delete state |
| `QFORMAT` | NUM(0) NORM(1) ALPHA | NORM | NORM | query format |
| `RANGE` (`R`) | max_input[,%res] | | AUTO | |
| `RATIO` | OFF ON | OFF | ON | |
| `RES` | %res | | | resolution against present range |
| `RESET` | | | | power-on state |
| `REV?` | | | | "outguard,inguard" firmware |
| `RMATH` | register | | DEGREE | read math register |
| `RMEM` | first[,count[,record]] | | 1,1,1 | copy from memory; MEM OFF |
| `RQS` | 0-255 | 0 or 8 | 0 | SRQ enable |
| `RSTATE` | name | | 0 | recall state |
| `SCAL` | 1E5, 10, 1, 0.1[,code] | | | AC adjustment |
| `SCRATCH` | | | | delete all subs, states, variables |
| `SECURE` | old,new[,OFF(0)/ON(1)] | | | security code |
| `SETACV` | ANA(1) RNDM(2) SYNC(3) | ANA | ANA | ACV method |
| `SLOPE` | NEG(0) POS(1) | POS | POS | |
| `SMATH` | register[,value] | | DEGREE, last reading | write math register |
| `SRQ` | | | | sets status bit 2 |
| `SSAC`, `SSDC` | [max_input][,%res ignored] | | 10 | sub-sampling |
| `SSPARM?` | | | | N1,N2,N |
| `SSRC` | EXT(2) LEVEL(7)[,AUTO(1)/HOLD(4)] | LEVEL,AUTO | LEVEL,AUTO | sync source |
| `SSTATE` | name | | | store state |
| `STB?` | | | | status byte (no bit 4) |
| `SUB` / `SUBEND` | name | | | define subprogram |
| `SWEEP` | interval,count | 100E-9,1024 | 20E-6,1024 | |
| `TARM` | AUTO(1) EXT(2) SGL(3) HOLD(4) SYN(5)[,n] | AUTO | AUTO | |
| `TBUFF` | OFF ON | OFF | OFF | trigger buffer |
| `TEMP?` | | | | internal °C |
| `TERM` / `TERM?` | | | | no-op; `?` returns FRONT/REAR |
| `TEST` | | | | self-test |
| `TIMER` | seconds | 1 | 1 | sample interval |
| `TONE` | | | | one beep |
| `TRIG` (`T`) | AUTO(1) EXT(2) SGL(3) HOLD(4) SYN(5) LEVEL(7) LINE(8) | AUTO | SGL | |

Table 6-1 limits on which commands apply to which functions:

- AZERO: DCV, DCI and ohms only.
- OCOMP: ohms only.
- FIXEDZ: DCV.
- APER, NPLC, LFREQ: DCV, ohms, DCI and analog AC.
- ACBAND: AC (all methods) and FREQ/PER.
- FSOURCE: FREQ/PER.
- SSRC: SYNC ACV and sub-sampling.
- SWEEP, TIMER: not SYNC/RNDM ACV, FREQ or PER.
- MATH: not sub-sampling (MMATH is allowed).

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| VISA timeout on a write | The command is still running with INBUF OFF (ACAL, TEST, TARM SGL with many readings, CALL). Raise the timeout or send INBUF ON. |
| Query returns a reading, or a reading is lost | The output buffer holds one item; a query replaces an unread reading. Read readings first or use memory. |
| TRIGGER TOO FAST | TIMER/SWEEP interval shorter than the reading time, or the controller is not reading fast enough for direct output. Lengthen the interval, use memory, or for EXT triggers use TBUFF ON. |
| SETTINGS CONFLICT | Illegal trigger combination, or sub-sampling without MEM FIFO + MFORMAT SINT. |
| Ohms reading low or wrong | FIXEDZ left ON (10 MΩ across the input). Send FIXEDZ OFF. |
| Ohms readings drift or slow | High-value resistor with cable capacitance: increase DELAY. Thermal EMF on low values: OCOMP ON. |
| SINT/DINT values nonsense | Scale factor from a different configuration, or autorange/math enabled. Query ISCALE? with the same configuration. |
| No readings with MEM FIFO | Memory full: FIFO stops storing. MCOUNT?, then clear with MEM FIFO. |
| Meter ignores commands | It is in high-speed mode waiting for readings to be taken, or a sub is running. Device Clear. |
| ACAL REQUIRED | Power was cycled or Reset during autocal. Run ACAL ALL. |
| OUT OF CAL / CAL error | A constant is out of limits. Read AUXERR?, run TEST, check CAL? limits for the function. |
| SYNC ACV unstable | Noisy signal causes false sync. LFILTER ON, SSRC EXT with a clean sync, or use ANA. |
| SYNC ACV overloads with DC on the input | SYNC is DC-coupled internally. Use a higher range or remove the DC. |
| Keys dead | LOCK ON or GPIB LLO. Send LOCK OFF and GTL, or cycle power. |
| `*IDN?` gets no identity reply | It is not in the command set; use ID?. |

## Discrepancies in the manuals

- ACBAND power-on high limit: the User's Guide command page says 20 MHz; Table 2-1 and the QRG say 2 MHz. Use 2 MHz (20,2E6).
- Bare `MEM`: the User's Guide says "ON"; the QRG says FIFO. FIFO is the documented mode.
- Security code: User's Guide examples print "3458A"; the Calibration Manual and QRG give 3458.
- Factory acal_secure: ON in the Calibration Manual chapter 1 and the ACAL page; OFF on the SECURE page and in User's Guide chapter 3. Check the instrument.
- ACI range table: ".120E-6" should be 120E-6 for the 100 µA range.
- PFAIL example: says "bit 2"; the limit bit has value 2, which is bit 1.
- SUBEND page says it sets "bit 1"; the status table gives bit 0 for subprogram complete.
- ACAL times: User's Guide 16 min / 2:45 / 2:45 / 11 min (ALL, DCV, AC, OHMS); front-panel guide 12 / 2 / 1 / 9 min; Calibration Manual about 10 min for OHMS.
- FREQ digits per gate: the User's Guide table gives 7/7/6/5/4 digits for 1 s to 100 µs gates; Product Note 3458A-1 gives 7.5/6.5/5.5/4.5/3.5.
- The QRG lists "GFORMAT" under the system commands; it means QFORMAT.
- `ID?` reply: the current manual prints "Keysight 3458A"; older instruments reply "HP3458A". Match on "3458A".
