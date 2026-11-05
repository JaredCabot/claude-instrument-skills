---
name: "hp-53132a"
description: "Operate, program (SCPI/GPIB), verify and calibrate the HP 53132A/53131A/53181A counter, incl. GPS reference, hidden menus, cal-code recovery, EEPROM, :DIAG, Ch3 option and pForth."
---

# HP / Agilent 53132A universal counter

Distilled from the three Agilent manuals: Programming Guide 53131-90044 ("Prog"), Operating Guide
53131-90055 ("Op") and Assembly-Level Service Guide 53131-90039 ("Svc"). Page numbers are PDF
pages of those files. The 53131A is the same instrument with less resolution; differences are flagged.
Everything here is from the manuals unless marked **[inferred]**, **[Supp]** or **[bench]**.

**[Supp]** marks material from firmware reverse-engineering (a companion 531xxA firmware supplement and its tools). Its bench results were taken on a reference **53131A** (option 030, firmware 4243). Items marked **[bench]** were confirmed on a reference **53132A** (see "Bench-verified responses"). When a
manual contradicts itself or the supplement, this file says so and gives the query that settles it.
Where the Supplement and the Service Guide disagree, prefer the Supplement (it was checked against the
firmware and a running unit).

Reference setup: 53132A on GPIB **address 1** (not the factory 3), controlled from Python (pyvisa, NI-VISA) on Windows, with a **GPS-disciplined 10 MHz on the rear Ref In** and a GPS-locked signal generator on Ch1/Ch2. A tested driver is included at the end of this file.

## Safety: what can destroy calibration or hang the bus

**Commands that overwrite stored calibration or configuration in the EEPROM.** The documented ones also increment `:CAL:COUN?`; the [Supp] ones may leave no trace:

| command | what it does | precondition |
|---|---|---|
| `:CAL:DATA <block>` | replaces all 56 bytes of calibration data | a block from `:CAL:DATA?` |
| `:DIAG:CAL:INP[1|2]:OFFS:AUTO ONCE` | input offset calibration | input disconnected |
| `:DIAG:CAL:INP[1|2]:GAIN:AUTO ONCE` | input gain calibration | **+5.000 V ±1 mV applied**, voltmeter removed |
| `:DIAG:CAL:TINT:QUIC`, `:DIAG:CAL:TINT:FINE1..4` | Ch1/Ch2 path-delay calibration | clean 10 MHz square on Ch1, or a 59992A TI calibrator |
| `:DIAG:CAL:ROSC:AUTO ONCE` | oven timebase calibration (options 001/010/012 only) | 10 MHz into **Channel 1**, oven warmed up 24 h |
| `:CAL:SEC:STAT ON|OFF,<code>`, `:CAL:SEC:CODE <n>` | change calibration security (non-volatile) | |
| `:DIAG:OPT:HFR <p>,<opt>,<c>` (also `:DIAG:OPT:CODE`, `:DIAG:OPT:HPIB`) **[Supp]** | rewrites the EEPROM header (Channel 3 option and prescale) | see "Channel 3 option" |
| `:DIAG:SPI:HDAC…`, `:DIAG:SPI:TDAC…`, `:DIAG:SPI:IACONTROL` **[Supp]** | load the trigger, hysteresis and interpolator DACs directly | never on a calibrated unit |
| pForth `fe_cal_offset`, `fe_cal_gain`, `wr_eeprom`, `c!`, `hdac_write`, `tdac_write`, `fpga_wr16` **[Supp]** | write calibration or hardware **below the security layer**. `fe_cal_*` work while the unit is secured and do **not** bump the cal count, so no trace is left. | pForth console only |

**Rules:**
- Never send these unless the user explicitly asks for a calibration.
- **Always save `:CAL:DATA?` to a file first.** The manual itself recommends this (Svc p.105).
  - **Never load a block taken from another unit.** The constants are unit-specific.
- **Never hold LEFT + RIGHT arrow together while switching on [Supp].**
  - That chord is the firmware's full non-volatile memory clear (`EEPROM CLEAR` scrolls on the display).
  - It erases the calibration, the save/recall registers, stored configuration and the Channel 3 option record.
  - It resets the security code to the model default.
- **Hidden-menu items can also write the EEPROM [Supp]:** `MODEL ?` (re-selects the stored model identity), `OPT:`, `GPIB ENABLED`, and toggles such as `PFORTH:`. Look; don't change them unless the user asks.
- These are safe: `*CAL?`, `:CAL?` and `:DIAG:CAL:INT:AUTO ONCE` only recalibrate the interpolators, which are not stored and not security-protected. `:CAL:COUN?`, `:CAL:SEC:STAT?` and `:DIAG:CAL:STAT?` are read-only.
- **Security code:** the factory code is the model number, **53132** (53131 on the 53131A).
  - While the counter is unsecured, entering *any other number* at the front-panel `CODE:` prompt silently becomes the new code. The reference 53132A was found **unsecured** on 2026-10-03 [bench].
  - The Service Guide says a forgotten code can only be cleared by Agilent's confidential full non-volatile memory reset, which also erases the calibration (cal count 0 = uncalibrated) (Svc p.104–105, p.111).
  - **Better: read the code without changing anything [Supp].**
    1. Send `:DIAG:SYST:HMACCESS 1` over GPIB. This only sets a RAM gate, so it must be re-sent after every power cycle.
    2. Switch off, hold **+/-**, and switch on to open the debug menu.
    3. Step with +/- to `CAL CODE ?` and press an arrow: the display scrolls `CAL CODE IS <n>`.
    4. Calibration, configuration and the cal count are untouched.
    - The supplement also says start-up clears the gate, which seems to contradict step 2 (a power cycle between unlocking and entering). Possibly the key is decoded before RAM is cleared, or the front-panel switch is only standby. The procedure is what the reference tools use, but it hasn't been tried on the 53132A. If the menu doesn't open, report it rather than trying other key combinations.
  - The "confidential procedure" is the LEFT+RIGHT arrow power-on clear above. **Contrary to the Service Guide, it does not reset the cal count** (the count keeps incrementing [Supp]).
    - Use it only if the code can't be read, and only after `:CAL:DATA?` is backed up.
    - Afterwards the unit must be recalibrated.
  - Units with 53131A firmware 3317/3335/3402 predate calibration security: `CAL:` is in the Utility menu there and needs no code [Supp].

**Queries that block the bus until the measurement ends:** `:READ?`, `:MEAS?`, `:FETC?`, `*OPC?`, `*WAI`, and `:CALC:DATA?` / `:CALC2:LIM:FAIL?` when math or limits are on.
- `*RST` and `*CLS` do **not** release them. Only Device Clear (`inst.clear()` in pyvisa) or a power cycle does (Prog p.199, 301, 311).
- So always use a read timeout longer than gate time + 3 input periods, and send `inst.clear()` after any time-out.
- Exception: `[:SENS]:DATA?` never blocks; it returns the previous result.

**Input damage levels (Op p.174–176):**
- Ch1/Ch2 at 50 Ω: 5 Vrms.
- Ch1/Ch2 at 1 MΩ: 350 V (dc + ac peak) up to 3.5 kHz, derated linearly to 5 Vrms at 100 kHz, and 5 Vrms above that.
- Ext Arm and Ref In: 10 Vrms.
- Ch3: option 030 is 5 Vrms; options 050/124 are +25 dBm.
- Front and rear panels are at earth ground: use an isolation transformer to measure mains.

## Connecting

- **GPIB address:** factory default **3**, range 0–30, or TALK (talk-only, for a printer: the counter then ignores commands). **The reference unit is at 1** [bench]; `find_counter()` in the project driver scans the bus.
  - To set it: power off, hold **Recall (Utility)**, press POWER, press Recall until `HP-IB:`, set it with the arrow keys, then **Enter** (mandatory).
  - Current firmware shows `HP-IB AT n` briefly at power-up.
  - The address is non-volatile; `*RST` does not change it. There is **no SCPI command for the address** (Prog p.74, Op p.136).
- **Termination:** replies end with LF + EOI. Use `read_termination = '\n'` and `write_termination = '\n'`. A command terminates on LF or on EOI.
- **Numeric replies carry a leading `+`** (`+1`, `+2619`, `+128,N030,0`) [bench]: parse with `int(float(x))`, never compare strings.
- **Identity:** `*IDN?` → `HEWLETT-PACKARD,53132A,0,<firmware rev>`. Later units may say AGILENT.
  - **[Supp]** In every ROM image examined the template is literal, and the third field is always `0`.
  - There is **no electronic serial number** anywhere in the firmware, and none can be programmed in. Track the unit by its rear label.
  - The model name is compiled into the firmware: 53132A EPROMs in a 53131A chassis report 53132A.
  - Known revisions: 53131A 3317/3335/3402 (early), 3427/3646/3944/4243; **53132A 3703/3944/4613**; 53181A 3703/3944/4243.
  - `*IDN?`, `*OPT?` and `:CALC:MATH:EXPR?` must be the **last query in a program message**, otherwise you get error −440.
- **Options:** `*OPT?` → `<timebase>,<RF>`. Timebase is `0` (standard TCXO), `001` (medium-stability oven) or `010` (option 010 or 012 oven). RF is `0` or `030` (option 030 or 050 channel 3).
- **Firmware and serial differences** (Prog p.16–19; Op p.24–26):
  - **Hysteresis is inverted on firmware 3317/3335/3402:** there, 100 % = most sensitive. On current firmware, 0 % = most sensitive. Those revisions are early 53131A firmware only [Supp], so on a 53132A, 0 % = most sensitive.
  - 53132A serial prefix **≥ 3646** has two-layer time-interval arming (start/stop delay by time or by events). Below 3646 the only option is a stop delay by time.
  - On pre-3646 units, `*OPC` sent while idle never fires.
  - 53131A firmware 3413 has broken `:MEAS`/`:READ` for voltage peaks.
  - Firmware ≥ 3622 makes recall register 0 volatile.
  - The firmware revision is also shown as `REV:` in the Utility menu.
- **Front-panel errors:** in remote, the Remote LED **flashes** while an error is queued. In Single mode or a menu the display shows `HP-IB -nnn`. Save & Print becomes the **Local** key in remote.

```python
import pyvisa
rm = pyvisa.ResourceManager()
c = rm.open_resource('GPIB0::1::INSTR')         # the reference address (factory default 3)
c.read_termination = c.write_termination = '\n'
c.timeout = 20000
c.clear()                                  # Device Clear: also frees a hung READ?
for s in ('*RST', '*CLS', '*SRE 0', '*ESE 0', ':STAT:PRES'):
    c.write(s)
print(c.query('*IDN?'))
```

## The model to keep in your head

- **Data flow:** SENSe → CALC1 (scale & offset) → CALC2 (limit test) → CALC3 (limit filter, then statistics) → bus and display (Prog p.174).
  - Each CALC block does nothing until its STATe is ON: `:CALC:MATH:STAT`, `:CALC2:LIM:STAT`, `:CALC3:LFIL:STAT`, `:CALC3:AVER:STAT`.
  - Totalize and voltage peaks bypass CALC entirely; those queries return error −221.
- **Measurement commands:**
  - `:MEAS:<f>?` = `:CONF:<f>` + `:INIT` + `:FETC?`.
  - `:READ?` = `:INIT` + `:FETC?`.
  - `:FETC?` returns the last result; you can fetch several times from one acquisition.
  - FETC?/READ? can only *derive* frequency ↔ period and the voltage-peak variants (max ↔ min ↔ peak-to-peak). Anything else needs a new acquisition (Prog p.57).
- **`:CONF` and `:MEAS?` reset a lot:**
  - They set the function's default arming (frequency/period → **digits** arming, 4 digits).
  - They re-enable **auto-trigger** at 50 %.
  - They **switch math, statistics and limit testing OFF** (Prog p.222, 224).
  - `[:SENS]:FUNC "<f> <ch>"` changes only the function and keeps everything else. However, a bare `:READ?`/`:FETC?` still uses the function of the last CONF/MEAS/READ/FETC, so after a `:FUNC` change use `:READ:FREQ?`, `:READ:PER?` and so on (Prog p.259).
  - An unexpected parameter to CONF/MEAS is **silently ignored**: no error, only Questionable bit 14 (Command Warning) gets set.
- **Single vs continuous:**
  - **Power-on** = Run (`:INIT:CONT ON`) with math/limit recalculation ON. **`*RST`** = Single (`:INIT:CONT OFF`) with recalculation OFF (Prog p.177, 214).
  - `:INIT` while running or mid-measurement → −213. `:INIT:CONT OFF` during a single measurement → −210.
  - After `*RST` the trigger level stays at 0 V until the first measurement starts (Op p.162).
- **`*RST` changes a lot, but not everything (Prog p.66–69, 305):**
  - It does **not** clear the error queue or status registers (send `*CLS`).
  - It does not touch `*SRE`, `*ESE`, the STAT enable/transition registers, the GPIB address, RS-232 settings, radix, calibration or security.
  - It **does** force `:ROSC:SOUR:AUTO ON`, `:ROSC:EXT:CHEC ON`, `:FREQ:EXP:AUTO ON`, `:DIAG:CAL:INT:AUTO ON`, `:DISP:ENAB ON` and `*EMC 0`.
- **`*SAV n` / `*RCL n`:**
  - Registers 1–20 for save, 0–20 for recall. `*RCL` first copies the current state to register 0, so register 0 is "undo".
  - **Not saved:** the reference-oscillator settings, expected frequency, interpolator auto-cal, display enable, macros, status enables (Prog p.304–306).
  - The Operating Guide's table 2-7B claims the timebase source *is* saved on 53132A units with serial prefix ≥ 3646. Don't rely on either answer: set it every session.
- **Macros** (`*DMC`) need `*EMC 1`, which `*RST` turns off. They are lost at power-off; registers are not.

## Reference oscillator with a GPS 10 MHz (most important section)

Ref In facts (Op p.176):
- The 53132A accepts **10 MHz only**; the 53131A takes 1, 5 or 10 MHz.
- Level 200 mVrms to 10 Vrms (damage 10 Vrms); input is 1 kΩ, 23 pF, with a 0 V threshold.
- The **ExtRef** annunciator lights when the external reference is in use.
- Time-interval calibrations ignore any external timebase.
- Whether the rear **10 MHz Out** follows the external reference is not stated; check with a second counter or a scope **[inferred: unknown]**.

**AUTO mode** (the power-on and `*RST` default; not in non-volatile memory) silently uses the internal timebase whenever Ref In is invalid.
- If the reference drops mid-measurement, you get **+2010** "External timebase failed during measurement": that result is invalid and the counter carries on with the internal timebase. The display shows `NEW TIMEBASE`.
- **EXT selected explicitly** with a missing reference gives **+2009** "No valid external timebase" (display `NO TIMEBASE`), and the counter never reports Measuring, so reads hang until the timeout (Prog p.101, 260–262, 322).

The recipe, after every `*RST` and every power-up (works on the reference unit [bench]):
```
:ROSC:SOUR EXT          # explicit; also sets :ROSC:SOUR:AUTO OFF
:ROSC:EXT:CHEC ONCE     # checks now -> +2009 if absent; leaves CHECk OFF afterwards
:ROSC:EXT:CHEC ON       # re-check at every measurement completion
:SYST:ERR?              # must be +0
:ROSC:EXT:FREQ?         # -> +1.00000E+007  (9.91E37 = internal or unknown)
:STAT:OPER:COND?        # bit 9 (512) = "using internal reference": must be 0
```
- **To be alerted if the GPS reference is lost:** `:STAT:OPER:PTR 512; :STAT:OPER:ENAB 512; *SRE 128`. The service request then fires when bit 9 goes true.
- **Throughput mode** (`:ROSC:EXT:CHEC OFF`) removes the presence check. Don't use it with GPS unless you watch bit 9.
- **Never put the GPS on Ref In when checking the internal timebase.** In AUTO the counter locks to it, and you end up measuring the GPS against itself. To check or adjust the internal timebase, feed the GPS 10 MHz into **Channel 1** with `:ROSC:SOUR INT` (Svc p.121–122).

## Inputs and triggering (Ch1/Ch2, Op p.174, Prog p.216–252)

| item | value / command |
|---|---|
| Frequency range | DC coupling: DC–225 MHz. AC coupling: **30 Hz**–225 MHz at 1 MΩ, 1 MHz–225 MHz at 50 Ω. **Use DC coupling below 30 Hz.** |
| Sensitivity (sine) | 20 mVrms to 100 MHz, 30 mVrms to 200 MHz, 40 mVrms to 225 MHz; signal range ±5 V ac+dc (×1) |
| Impedance | `:INP1:IMP 50` or `1E6` (*RST 1 MΩ; 30 pF) |
| Coupling | `:INP1:COUP AC|DC` (*RST **AC**) |
| Attenuator | `:INP1:ATT 1|10` (×10 multiplies every voltage spec by 10) |
| 100 kHz low-pass filter | `:INP1:FILT ON|OFF` (−20 dB above 1 MHz). Cuts the noise bandwidth from 225 MHz to 100 kHz, but slows the edges reaching the comparator; keep it off near and above ~50 kHz **[inferred]**. |
| Trigger level | `:EVEN1:LEV <V>`: ±5.125 V, 5 mV resolution, accuracy ±(15 mV + 1 %). It is the **centre** of the hysteresis band. **Setting a level turns auto-trigger off.** |
| Auto-trigger | `:EVEN1:LEV:AUTO ON` with `:EVEN1:LEV:REL 0..100` (10 % steps, *RST 50 %). **Only specified above 100 Hz and 100 mVpp, with no AM.** Each `:INIT` runs a level-finding pre-measurement. |
| Slope | `:EVEN1:SLOP POS|NEG` |
| Sensitivity | `:EVEN1:HYST:REL 0|50|100` = HI/MED/LO on current firmware (*RST 0 = HI). LO has about twice the hysteresis and is useful on noisy or slow signals. **Inverted on early 53131A firmware 3317/3335/3402** (not any 53132A). |
| Common/separate routing | `:EVEN2:FEED "INP1"|"INP2"`; time interval only (*RST separate) |

- The channel number defaults to 1 when it is left off (`:INP:COUP` means Ch1).
- Channel 3 (options 030/050/124) is fixed at 50 Ω, AC, with no level control. It measures frequency, period and ratio only.
- The front-panel trigger LED **flashing** means triggering; **steady on** means the input is too high; **off** means the input is too low.

## Gate and arming (Prog p.253–258; Op p.94–104, p.186)

Frequency, period and ratio share the `[:SENS]:FREQ:ARM` tree:

| mode | commands | notes |
|---|---|---|
| AUTO | `:FREQ:ARM:STAR:SOUR IMM; :FREQ:ARM:STOP:SOUR IMM` | fastest, least resolution. Gate = 1 period below 1 MHz, 4 periods above. |
| TIME | `...STOP:SOUR TIM; :FREQ:ARM:STOP:TIM <s>` | **1 ms – 1000 s** (*RST: TIMer, 0.1 s) |
| DIGITS | `...STOP:SOUR DIG; :FREQ:ARM:STOP:DIG <3..15>` | the counter picks the gate (*RST 4 digits) |
| EXTERNAL | `:FREQ:ARM:STAR:SOUR EXT; ...:STAR:SLOP POS|NEG` + stop IMM / EXT (with `:STOP:SLOP`) / TIM | a signal **must** be on the rear Ext Arm input (TTL, 1 kΩ) |

- **`:FREQ:EXP<ch> <Hz>`** skips the frequency-finding pre-measurement (also used by phase and duty cycle).
  - The real input must be **within 10 %** of the expected value.
  - The range is 0.1 Hz–225 MHz.
  - Sending a value is the only way to turn `:FREQ:EXP:AUTO` off; `*RST` turns AUTO back on. It is not saved by `*SAV`.
- **`:MEAS:FREQ? [<expected>[,<resolution>]][,(@n)]`:**
  - It uses **digits** arming.
  - The default expected value is **10 MHz** and the default resolution 4 digits.
  - The resolution must be 1 × 10ⁿ.
  - For low-frequency work, set up the measurement yourself instead.
- **Totalize:** `:CONF:TOT:CONT` (CONF only), then `:INIT`, then `:ABOR` to stop, then `:FETC?`. `:MEAS:TOT:TIM? <gate>` counts for a fixed time.
- **Time-interval arming:**
  - Serial prefix < 3646: `:TINT:ARM[:STAR]:SOUR IMM|EXT`, `:TINT:ARM:STOP:SOUR IMM|TIM`, `:TINT:ARM:STOP:TIM` (100 µs–10 s; 1 ms on old firmware).
  - Serial prefix ≥ 3646: `:TINT:ARM:ESTART:LAY2:SOUR IMM|EXT` and `:TINT:ARM:ESTART[:LAY1]:SOUR IMM|TIM|INT1` with `:TIM` (100 ns–999.9999 ms) or `:ECO` (1–99,999,999 events), plus the matching `ESTOP` set (stop delay up to 10 s). Send them in that order.

## Accuracy: how to choose the gate (Op p.177–185, formulas checked against the page images)

Symbols: F = frequency; GT = gate time; TE = rms trigger error; TBE = time-base error.

**Auto or external arming, and any signal below 100 Hz with timed arming (no averaging):**
- LSD = (t_res / GT) × F
- RMS resolution = (√(t_res² + 2·TE²) / GT) × F
- 53132A: t_res = 200 ps. Auto-armed gate = N/F, with N = 1 (Ch1/2 below 1 MHz), 4 (Ch1/2 above 1 MHz), 128 (Ch3).
- Systematic = ±TBE ± (t_acc / GT) × F, with t_acc = 100 ps typical, 500 ps worst (53131A: 650 ps, and 350 ps / 1.25 ns).

**Time or digits arming, input above 100 Hz (averaging):**
- NS = GT × F (F < 200 kHz) or GT × 200,000 (F > 200 kHz)
- LSD = (2√2·t_res / (GT·√NS) + t_jitter / GT) × F
- RMS resolution = (4·√(t_res² + 2·TE²) / (GT·√NS) + t_jitter / GT) × F
- 53132A: t_res = 225 ps, t_jitter = 3 ps; t_acc = 10 ps typical, 100 ps worst (53131A: 500 ps, 50 ps, 100/300 ps).

**Trigger error and totals:**
- TE = √(E_input² + E_signal²) / (slew rate at the trigger point).
  - E_input = 1 mVrms (350 µVrms typical); the internal algorithms reduce this term in practice.
  - E_signal = signal noise in 225 MHz, or in 100 kHz with the filter on.
- Total error (2σ) = ±systematic ± 2 × RMS resolution.
- **Averaging never reduces the timebase error.** With the GPS on Ref In, TBE is the GPS's own error.
- Worked example (Op p.180): 15 MHz, 1 s gate, high-stability oven calibrated 3 days earlier gives ±60.2 mHz, dominated by the 4 × 10⁻⁹ timebase. Resolution is 75 µHz (1σ).
- Statistics (`:CALC3`) improve resolution roughly as √N.
- With time/digits arming above 100 Hz, `:DIAG:MEAS:PRES?` returns 1 if a reading fell in a reduced-resolution band (up to 10× worse), near 10 MHz/fs = integer + simple fraction.

**Rules of thumb for sine waves [inferred from the formulas above; confirmed on the reference unit, see "Bench-verified responses"]:**
- At low frequency, trigger noise dominates.
- 1 Vrms at 0.5 Hz slews at 4.4 V/s, so TE ≈ 80–225 µs: about 10⁻⁵ fractional with a 10 s gate. Resolution there comes from long gates and statistics, not from the counter's picoseconds.
- At 1 kHz with a 1 s gate, expect about 10⁻⁸; at 100 kHz, about 10⁻¹¹.
- A reading never finishes faster than gate + one input period + the wait for the first edge. A 0.5 Hz reading with an 8 s gate took 14 s [bench].

## Recipes

**Clean frequency reading, any frequency, GPS reference (the driver's `frequency()`):**
```
*RST; *CLS; *SRE 0; *ESE 0; :STAT:PRES      (after Device Clear)
:ROSC:SOUR EXT; :ROSC:EXT:CHEC ONCE; :ROSC:EXT:CHEC ON; :SYST:ERR?
:INP1:COUP DC; :INP1:IMP 1E6; :INP1:ATT 1; :INP1:FILT OFF
:EVEN1:SLOP POS; :EVEN1:LEV 0.000              (fixed level at the signal midpoint)
:INIT:CONT OFF; :FUNC "FREQ 1"
:FREQ:ARM:STAR:SOUR IMM; :FREQ:ARM:STOP:SOUR TIM; :FREQ:ARM:STOP:TIM 1
:FREQ:EXP1 <nominal>                         (within 10 %; skips the pre-measurement)
:READ:FREQ?                                  (timeout > gate + 3/f + margin)
:SYST:ERR?                                   (loop until +0)
```
A reading of `9.91E37` means no valid result (no signal, or an aborted reading); that is also when −230 is queued. A reading during which the reference failed under AUTO is flagged by +2010. For a signal with a DC offset, set the level at the midpoint. Use slope NEG for the other edge.

**Low frequency (below 100 Hz, down to 0.1 Hz):**
- DC coupling and a manual level (auto-trigger is not valid there).
- An expected value so there is no pre-measurement.
- A gate of several periods (the project's calcheck uses max(1 s, 4 periods)).
- Statistics for averaging.
- Period mode (`:FUNC "PER 1"`, `:READ:PER?`) is equivalent: period range 4.44 ns–10 s.

**Statistics block** (`statistics()` in the driver):
```
:CALC3:AVER:COUN 20; :CALC3:AVER ON; :TRIG:COUN:AUTO ON
:INIT; *OPC?                       (blocks for the whole block: timeout = N x per-reading time)
:CALC3:AVER:TYPE MEAN; :CALC3:DATA?   (then SDEV, MIN, MAX)
```
- `:CALC3:AVER:ALL?` returns four values, but the manual gives two different orders (p.187: "mean, std dev, max, min" vs "mean, standard deviation, minimum, maximum"). Read each value by TYPE, or check once on the unit.
- Without `:TRIG:COUN:AUTO ON`, each `:INIT` adds only one sample.
- With the limit filter on, the block waits for N *in-limit* readings and may never finish.
- The CALC2 limits and CALC3 filter limits are the same two numbers.

**Maximum throughput** (about 200 readings/s ASCII, Prog p.105–107, 143):
- Fixed levels.
- AUTO arming.
- `:ROSC:SOUR INT|EXT` with `:ROSC:EXT:CHEC OFF`.
- `:DIAG:CAL:INT:AUTO OFF`. This makes the results "questionable": Questionable bits 2, 5 and 6 get set.
- `:DISP:ENAB OFF`, `:HCOP:CONT OFF`, and math/limits/statistics OFF.
- `:FREQ:EXP1 <f>`.
- `*DDT #15FETC?` and `:INIT:CONT ON`.
- Prime with one `:FETC:FREQ?`, then use GET (`inst.assert_trigger()`) and read.
- All of these are reset by `*RST` and a power cycle.

**Waiting for a long measurement without blocking the bus:**
```
:STAT:OPER:PTR 0; :STAT:OPER:NTR 16; :STAT:OPER:ENAB 16; *SRE 128; :INIT
```
The service request fires when Measuring (Operation bit 4) falls; the serial poll returns 192. Then `:FETC?`. Alternatively send `:INIT; *OPC` with `*ESE 1; *SRE 32` (poll 96), re-sending `*OPC` before every measurement.

**Other functions** (`:MEAS:<f>? (@...)`, see Prog p.227):
- Two-channel functions: `TINT (@1),(@2)` (start Ch1, stop Ch2; LSD 150 ps, RMS 300 ps), `PHAS (@1),(@2)` (−180°…+360°; positive means Ch1 leads), `FREQ:RAT (@1),(@2)` (put the higher frequency on Ch1).
- Ch1 only: `PWID`, `NWID`, `DCYC` (result 0–1), `RISE:TIME`, `FALL:TIME` (10/90 %).
- `MAX`, `MIN`, `PTP` (voltage peaks, AC from 100 Hz, ±(25 mV + 10 %)).
- `TOT:TIM? <gate>`.

**Back up calibration data before touching anything:**
- Send `:CAL:DATA?` and read **raw to EOI**: the 56 data bytes can contain 0x0A, so disable `read_termination` for this read.
- The reply is `#256` + 56 bytes (+ LF), covering input gain, offset, reference oscillator and TI (not the interpolators). The 14-word layout is under "Firmware internals".
- Also record `:CAL:COUN?`; an unexpected change means someone calibrated the unit.
- Restoring the block (`:CAL:DATA <block>`) needs the unit unsecured, writes the EEPROM and increments the count.
- A read-only first-contact tool can do all of this and save the block raw and decoded.

## Status registers (Prog p.89–104)

**Status Byte (`*STB?`, `*SRE`):**
- 8 = Questionable summary
- 16 = MAV
- 32 = Standard Event summary
- 64 = RQS/MSS
- 128 = Operation summary

**Standard Event (`*ESR?`, `*ESE`):**
- 1 = OPC
- 4 = query error (−4xx)
- 8 = device error (−3xx, +2xxx)
- 16 = execution error (−2xx)
- 32 = command error (−1xx, or a GET inside a message)
- 128 = power-on

**Operation (`:STAT:OPER:COND?` / `[:EVEN]?` / `:ENAB` / `:PTR` / `:NTR`):**
- 1 = calibrating
- 16 = measuring
- 256 = computing statistics
- **512 = using internal reference**
- 1024 = in-limit event

**Questionable (`:STAT:QUES...`):**
- 4 / 32 / 64 = time / frequency / phase questionable (interpolator auto-cal off)
- 256 = calibration error
- 1024 = out-of-limit event
- **16384 = command warning** (a parameter was ignored)

**Which commands clear what:**
- `*CLS` clears the event registers and the error queue.
- `:STAT:PRES` sets the enables to 0, NTR to 0, PTR to all ones. Power-on does the same and also clears `*SRE`/`*ESE`. `*RST` touches none of these.

## Errors (`:SYST:ERR?` → `<n>,"<text>"`; queue of 30, FIFO; Prog p.313–322, checked against p.322)

**SCPI errors:**
- −1xx syntax. Common ones:
  - −102 syntax
  - −105 GET not allowed
  - −108 too many parameters
  - −109 missing parameter
  - −113 undefined header
  - −131 invalid suffix
- −2xx execution:
  - −210 trigger error
  - −213 init ignored (already measuring, or continuous)
  - −220 parameter error (e.g. bad cal block)
  - **−221 settings conflict:** e.g. CALC queries with the block off, totalize/peaks, calibration while secured, `CHEC ONCE` without EXT
  - **−222 data out of range: the value is clipped and still applied**
  - −224 illegal value (e.g. `*DDT`)
  - **−230 data corrupt or stale** (no valid result)
  - −241 hardware missing (e.g. no channel 3, or oven calibration on a standard timebase)
- −330 self-test failed.
- −350 queue overflow.
- −4xx query errors:
  - −410 interrupted (a new command was sent before the reply was read)
  - −420 unterminated (read with no query)
  - −440 (a query after `*IDN?`/`*OPT?` in the same message)

**Counter-specific errors:**

| code | meaning |
|---|---|
| +2000 / +2001 | Ch1 / Ch2 offset calibration failed |
| +2002 / +2003 | Ch1 / Ch2 gain calibration failed |
| +2004 | interpolator calibration failed |
| +2005 | oscillator calibration failed |
| +2006 | time interval calibration failed |
| +2007 | measurement hardware calibration failed |
| +2008 | measurement interpolator calibration failed |
| **+2009** | **no valid external timebase** |
| **+2010** | **external timebase failed during measurement** (AUTO: result invalid, switched to internal) |
| +2011 | recall failed (hardware fault or empty register) |
| +2012 | save failed |
| +2013 | EEPROM failed (writing a stored setting or calibration) |

Display messages: dashes = no valid measurement (check level and coupling, or press Stop/Single). `UNCALIBRATED` at power-up means a calibration type has never been performed.

## Self-test, verification, calibration (Svc ch.1–2)

**Self-tests:**
- `*TST?` → 0 means pass. Power-up shows `SELFTST: PASS`.
- The Utility menu (hold Recall at power-up) offers `TEST: ALL?` and individual tests: DISP, CPU, ROM, RAM, **EEPROM** (checksums the calibration memory), HP-IB, QSPI, FPGA, FR END, MEAS, INTERP, KEYPAD, PRINT.
- Almost every failure points to the **A1 motherboard**. A1 holds the EEPROM, so replacing A1 loses all calibration. Display failures point to A2; front-end, measurement and interpolator failures can also point to the A4 supply.
- **Power-supply check** at A1 J18: +5.0 V ±0.25 V, +12 V ±0.6 V, −12 V ±1.2 V. The fan must run when power is applied. A4 is internally fused: a blown fuse means replace A4.
- After unplugging, **wait 6 min** for the capacitors to discharge. Use ESD precautions.

**Operational verification** (at least every 2 years; 30 min warm-up):
1. Self-test passes.
2. Rear 10 MHz Out → tee → Ch1 and Ch2: Ch1 reads `10.000 000 000 MHz` (53132A).
3. Ch2 reads the same.
4. `TEST: ALL` → `ALL: PASS`.
5. 50 Ω termination measures 51.1 ±3 Ω; 1 MΩ measures ≈1 MΩ.
6. External arm: totalize gated by a pulse gives ≈1000 counts.
7. 10 MHz at 200 mVrms into Ref In and 2 MHz into Ch1: reads ≈2 MHz with **ExtRef lit**.

**Performance-test limits (53132A, 1 s gate):**
- Time interval: 150 ns ±2.5 ns.
- Trigger level: 0 V ±15 mV.
- Sensitivity: 20 / 30 / 40 mVrms (−21 / −17.5 / −15 dBm) to 100 / 200 / 225 MHz.
- Frequency accuracy: **±200 µHz at 1 MHz**, ±15 mHz at 100 MHz, ±30 mHz at 200 MHz, ±35 mHz at 225 MHz.
- Peak volts: ±1.00 ±0.12 V.
- The accuracy limits only hold with the **source and the counter on the same reference**: put the GPS on both.

**Calibration** (front-panel menu: hold **Scale & Offset** at power-up → `CAL SECURE|UNSECURE`; unsecure via `CODE:` 53132 + Enter):
- **Order:** offset (inputs disconnected) → gain (+5.000 V from a supply on a tee; remove the DVM before Enter) → TI QUIK (10 MHz square, ±0.5 V, into 50 Ω on Ch1) or TI FINE (59992A) → timebase.
- **Standard TCXO:** the only hardware adjustment. Rear **Osc Adjust** pot, 30 min warm-up, 10 MHz on Ch1, adjust to 10.00000000 MHz (manual tolerance ±5 Hz; with GPS and a long gate you can trim far closer). The pot is not in the EEPROM and does not change the cal count.
- **Oven options:** `CAL: TIMEBAS?` / `:DIAG:CAL:ROSC:AUTO ONCE` after **24 h** warm-up. The result is `:CAL:DATA?` word 12 [bench].
  - Leave the counter plugged in: standby keeps the oven powered.
  - Unplugged for more than 24 h, an oven can take up to **30 days** to recover its daily aging rate.
- A failed calibration leaves the old values in place.
- **Re-secure afterwards**, then run the operational verification. After replacing any assembly, recalibrate.

**Internal timebase specs (Op p.176):**
- Temperature stability: standard < 5 × 10⁻⁶; option 001 < 2 × 10⁻⁷; options 010/012 < 2.5 × 10⁻⁹.
- Aging, standard: < 3 × 10⁻⁷ per month.
- Aging, option 001: < 4 × 10⁻⁸ per day, < 2 × 10⁻⁷ per month.
- Aging, option 010: < 5 × 10⁻¹⁰ per day, < 1.5 × 10⁻⁸ per month.
- Aging, option 012: < 1 × 10⁻¹⁰ per day, < 3 × 10⁻⁹ per month, < 2 × 10⁻⁸ per year.

## Front panel quick reference

- **Utility menu** (hold Recall at power-up): `REV`, `HP-IB` address, `TIMEBAS AUTO|INT|EXT` (not remembered across power-up), tests, RS-232 baud/parity/pacing/DTR (DTR can be the limit output on pin 4), `SHOW 9 AS`. Changing Utility items needs a power cycle, which loses the current setup, so `SAVE` it first.
- **Numeric entry needs Enter**; menus time out and select after 2 s.
- `SET OFFSET?` under Scale & Offset subtracts the last reading. That is how you see digits 13–15.
- Stats menu: N 2–1,000,000. Run clears the statistics.
- **If the counter ignores the bus** even though the address is right: check `GPIB ENABLED` in the option menu (see the power-on table below) [Supp].

**Keys held at power-on [Supp]** (the gated ones need `:DIAG:SYST:HMACCESS 1` sent in the same power session first; otherwise the key does nothing):

| key held | mode | gated |
|---|---|---|
| Scale & Offset | Calibration menu (documented) | no |
| Recall | Utility / self-test menu (documented) | no |
| +/- | **debug menu** `MENU:` | yes |
| TRIG/SENS 1 | "service menu": scrolls `SERVICE MENU` and returns; it has no items | yes |
| TRIG/SENS 2 | `NO OPT MENU`: items `OPT:` (Ch3 option) and `GPIB ENABLED` | yes |
| **LEFT + RIGHT arrows** | **`EEPROM CLEAR` — destroys calibration. Never.** | no |

**Debug menu items, in order:**
- `MLB TEAM ?` (the developers' names)
- `MODEL ?` (can re-select the model: don't)
- `DEBUG O/P:`, `PFORTH:`, `DEBUG OS:`, `GPIB BUF:`, `SHOW PLUS:`, `DISPLAY:`
- `CAL CODE ?`
- `NV COUNT ?` (write counts of the two EEPROM record slots)

Navigation in the debug and option menus: **+/- steps** from item to item. **The arrows act on the current item**: they show a `?` item, and switch a `:` toggle (which is stored).

## Firmware internals and undocumented features [Supp]

Everything in this section comes from the 531XX-90RE1 supplement, verified on the reference 53131A; the 53132A runs the same code base. The read-only parts were also confirmed on the reference 53132A [bench].

**Hardware and memory map:**
- CPU is an MC68331 (CPU32) running pSOS.
- Firmware is in four 128 KB EPROMs U8–U11 (27C010/27C1001). U8 (even bytes) interleaves with U10 (odd bytes) for the low 256 KB; U9 interleaves with U11 for the high 256 KB.
  - Reset vectors: SP `$0010FFFE`, PC `$0000172C`.
- RAM is at `$100000`; the keyboard ports are at `$300000`/`$300001`.
- Non-volatile memory is **U14, an AT28C64B 8 KB EEPROM at `$400000`**. It has no battery and no software data protection. It sits on A1, so replacing A1 loses the calibration.
- EEPROM header (`$00`–`$1F`):

| offset | contents |
|---|---|
| `$00` | checksum |
| `$02` | signature `HP53131 is a winner!` |
| `$16` | config word `$00000A3B` (2619, which is what `:DIAG:OPT:CODE?` returns) |
| `$1A` | status |
| `$1B` | Ch3 option code; bit 7 is the HFR coupling flag |
| `$1C` | Ch3 prescale / 128 |

- **Calibration and configuration records:** two 64-byte, bit-packed records at `$400020` and `$400060`, tagged `$5313`.
  - They are written alternately, and the record with the higher generation count is active (`NV COUNT ?`, `:DIAG:SYST:NVCOUNT?`).
  - Because the records are bit-packed, the security code (RAM `$100184`) cannot be read straight out of a dump. Use `CAL CODE ?`.
- `531xx_eeprom_tool.py` decodes, backs up and blanks EEPROM dumps (blanking is the off-line equivalent of the memory clear). The "53181A U14 ROMs" folder holds real dumps.

**`:CAL:DATA?` decoded:** `#256` + 14 big-endian signed 32-bit words + LF. The values are unit-specific (53131A / reference 53132A shown).

| word | meaning |
|---|---|
| 0, 1 | Ch1 / Ch2 offset trim (about 2048; 2049/2046 on the 53132A) |
| 2, 3 | Ch1 / Ch2 gain (1744/1751 on the 53131A; 1771/1757 on the 53132A) |
| 4–11 | time-interval constants (identical to `:DIAG:CAL:TINT:DATA?`, also on the 53132A [bench]) |
| 12 | **oven timebase calibration** (= `:DIAG:CAL:ROSC:DATA?`: 2113 on the reference 53132A with option 010; 2048 = mid-scale on units without an oven) [bench] |
| 13 | checksum |

A calibration backup belongs to the specific unit it came from: never load one unit's block into another.

**Undocumented `:DIAG` queries that are safe to read** (Supplement Table 6-2):

| query | returns |
|---|---|
| `:DIAG:SYST:NVCOUNT?` | NV write-count ceiling, current count (e.g. `30,27`; the reference 53132A answers `+68,+4294967295`) |
| `:DIAG:SYST:PSTARTUP?`, `:DPSOS?`, `:DOUTPUT?` | start-up mode / debug flags (0 = normal/off) |
| `:DIAG:OPT:HFR?` | `<prescale>,<option>,<flag>`, e.g. `128,N030,1` |
| `:DIAG:OPT:CODE?` | 2619 |
| `:DIAG:CAL:STAT?` | 1 = calibration valid |
| `:DIAG:CAL:INT:DATA?`, `:DIAG:CAL:TINT:DATA?` | interpolator / TI constants |
| `:DIAG:CAL:ROSC:DATA?` | oven calibration (= `:CAL:DATA?` word 12). **−241 means no oven is fitted**, so it doubles as an option probe. |
| `:DIAG:MEAS:RES?`, `:COMP?`, `:SCO?`, `:DIAG:GPT:COMP?` | last raw result, done flag, sample count, comparator |
| `:INP3:COUP?`, `:INP3:IMP?` | AC, 50 Ω (query-only on Ch3) |

- `:DIAG:SYST:HMACCESS 1` is the one harmless setter: it unlocks the gated power-on menus until the next power cycle.
- **Don't send** `:DIAG:SPI:*`, `:DIAG:HPIB:*` (message injection), `:DIAG:MENU:INIT`, or `:DIAG:OPT:*` writes.
- A bare query that answers −109 is a leaf that needs an argument; −113 means a set-only leaf. An unknown query gives no reply (time-out, then Device Clear) and queues −113.
- Array data-type keywords also exist: BARR/DARR/FARR/IARR/TARR.

**Channel 3 option (identity is stored in the counter's EEPROM, not on the A3 board):**
- `*OPT?` → e.g. `0,030`.
- To change it: `:DIAG:OPT:HFR <prescale>,<Nxxx>,<0|1>`, or the `OPT:` item of the TRIG/SENS 2 menu (which sets only the option code). The write needs `allow_cal=True` in the driver.
- All three arguments are mandatory. A malformed command is refused without writing anything: −109 missing, −108 extra, −148 keyword first, −222 prescale out of 128–16384, −224 unknown keyword.

| option | board | prescale | ceiling (above it: 9.9E37) |
|---|---|---|---|
| N015 | 1.5 GHz | 128 | 1.7 GHz |
| N030 | 3 GHz | 128 | 3.5 GHz |
| N050 | 5 GHz | 512 | 5.5 GHz |
| N124 | 12.4 GHz | 512 | 13.4 GHz |
| N160 / N200 | never sold (53181A) | 512+ | 16.5 / 22 GHz |

- **The prescale and the keyword must describe the same board.** Example: `512,N030` on a 12.4 GHz board gives −230 and dashes, and the fault survives power cycles.
- The prescale scales readings directly: 512 stored on a ÷128 board reads 4× high.
- The coupling flag is inert on a prescaler channel; factory values differ (the Supplement's 030 units store 1, the reference 53132A stores 0 [bench]).
- To find an unknown ratio N, feed a known frequency F: N = P·F/R, where P is the stored prescale and R the reading. `531xx_ch3_ceiling_test.py` and `531xx_ceiling_prescale_test.py` automate this.
- Before changing anything, record `*OPT?` and `:DIAG:OPT:HFR?`. Afterwards, power-cycle and check with a known Channel 3 signal.

**pForth monitor:**
- **Enabling it:** set `PFORTH: ON` in the debug menu. The setting is stored, so it survives power cycles.
- **Connecting:** the console is the rear RS-232 at 9600 8N1. The port is DTE, so use a **null-modem** cable.
  - Prompt: `p4th D >` (D = decimal base). The monitor runs as an extra pSOS task.
  - Note that the Operating Guide calls this port output-only (printer); with pForth enabled it also takes input.
- **Safe words:** `ver`, `words`, `.s`, `ps`, `mem_rep`, `s_rep`, `pr_max_nv`, `pr_eeprom_debug`, and `fe_measure_high_peak` / `fe_measure_low_peak` (mV).
- **Dangerous words:**
  - `wr_eeprom`, `c!` / `!` to `$400000` (no security check, no checksum fix-up), `hdac_write`, `tdac_write`, `fpga_wr16`.
  - `fe_cal_offset` / `fe_cal_gain` silently rewrite calibration without bumping the count.
  - `fe_set_*` changes the hardware without updating the SCPI state.
- `531xx_pforth.py` is a terminal for it.


## Bench-verified responses [bench]

Example responses read from a reference 53132A (read-only):

| item | value |
|---|---|
| address | GPIB0::1::INSTR (`find_counter()` in the driver scans the bus) |
| `*IDN?` | `HEWLETT-PACKARD,53132A,0,4613` |
| `*OPT?` | `010,030`: high-stability oven (option 010 or 012) and Channel 3 option 030 |
| `:CAL:COUN?` | 54 |
| `:CAL:SEC:STAT?` | **0 - calibration security is OFF** (re-secure from the Calibration menu) |
| `:DIAG:OPT:HFR?` | `+128,N030,0` |
| `:DIAG:OPT:CODE?` | `+2619` |
| `:DIAG:SYST:NVCOUNT?` | `+68,+4294967295` (format differs from the Supplement's `30,27` example; meaning of the second field unconfirmed) |
| `:DIAG:CAL:ROSC:DATA?` | `+2113` = `:CAL:DATA?` word 12 |
| `:DIAG:CAL:TINT:DATA?` | equals `:CAL:DATA?` words 4-11, as the Supplement says |

- The documented reference recipe works: `:ROSC:SOUR EXT` + `CHEC ONCE` gives no error with the GPS
  present, `:ROSC:EXT:FREQ?` = 1E7 and Operation bit 9 clear.
- SDG CH1 10 MHz (GPS-locked) into Ch1, 50 Ω, 1 s gate, 10 readings: offset −2×10⁻¹², sdev 3×10⁻¹¹.
- The oscillator-check set-up (DC, 1 MΩ, 0 V level, expected value, gate max(1 s, 4 periods)) on a
  1 Vrms SDG sine. All readings were valid. Offsets were trigger-noise limited at low frequency,
  as the formulas predict:

| f | offset | time per reading |
|---|---|---|
| 0.5 Hz | +2.8×10⁻⁶ | 14 s |
| 2 Hz | +7.9×10⁻⁶ | 4.5 s |
| 20 Hz | −3.7×10⁻⁶ | 1.7 s |
| 200 Hz | +6×10⁻⁸ | 1.4 s |
| 2 kHz | −3×10⁻⁹ | 1.1 s |
| 20 kHz | +5×10⁻¹¹ | 1.1 s |
| 120 kHz | −5×10⁻¹¹ | 1.1 s |

## Driver

The driver encodes the rules above:
- known-state reset;
- explicit external reference with a check;
- `:FUNC`-based configuration that keeps the input set-up;
- `:READ:FREQ?`, not a bare `:READ?`;
- timeouts sized from the gate and the lowest frequency, with Device Clear on a time-out;
- 9.91E37 → None;
- statistics read by TYPE;
- a raw `:CAL:DATA?` backup;
- a guard that refuses any calibration or security write, and the undocumented `:DIAG:OPT/SPI/HPIB/MENU` writes, in any part of a `;` message, unless `allow_cal=True`.

It was tested offline against a scripted fake instrument and then on a reference counter [bench]. It also has `find_counter()`, which scans GPIB for a 5313x/53181A, trying address 1 and then 3 first.

```python
import re

# calibration/security writes + undocumented EEPROM/DAC service leaves [Supp]
CAL_WRITE = re.compile(r'^\s*:?(CAL(IBRATION)?:(DATA\s|SEC)|DIAG(NOSTIC)?:(CAL(IBRATION)?:'
                       r'(INP|TINT|ROSC)|OPT(ION)?:|SPI|HPIB|MENU))', re.I)
TC_OK = re.compile(r'^\s*:?DIAG(NOSTIC)?:CAL(IBRATION)?:INT', re.I)   # interpolator: not stored

def _guarded(cmd):      # check every ';'-separated part of a program message
    return any(p.strip() and CAL_WRITE.match(p.strip()) and not TC_OK.match(p.strip())
               and not p.strip().endswith('?') for p in cmd.split(';'))

class CounterError(Exception):
    pass

class HP53132A:
    def __init__(self, resource='GPIB0::1::INSTR', timeout_s=10.0, inst=None):
        if inst is None:
            import pyvisa
            inst = pyvisa.ResourceManager().open_resource(resource)
        self.inst = inst
        inst.read_termination = inst.write_termination = '\n'
        inst.timeout = int(timeout_s * 1000)
        self.allow_cal = False

    def write(self, cmd):
        if _guarded(cmd) and not self.allow_cal:
            raise CounterError('refused: %r writes stored calibration/security' % cmd)
        self.inst.write(cmd)

    def query(self, cmd, timeout_s=None):
        old = self.inst.timeout
        if timeout_s is not None:
            self.inst.timeout = int(timeout_s * 1000)
        try:
            self.write(cmd)
            return self.inst.read().strip()
        except Exception as ex:
            if 'timeout' in str(ex).lower() or type(ex).__name__ == 'VisaIOError':
                self.inst.clear()             # Device Clear frees the held-off parser
                raise CounterError('%s timed out (Device Clear sent)' % cmd) from ex
            raise
        finally:
            self.inst.timeout = old

    def number(self, cmd, timeout_s=None):
        v = float(self.query(cmd, timeout_s))
        return None if v >= 9.9e37 else v     # 9.91E37 = not a number

    def errors(self):
        out = []
        for _ in range(31):
            code, _, text = self.query(':SYST:ERR?').partition(',')
            if int(code) == 0:
                break
            out.append((int(code), text.strip('"')))
        return out

    def check(self, what):
        e = self.errors()
        if e:
            raise CounterError('%s: %s' % (what, e))

    def reset(self):
        self.inst.clear()
        for c in ('*RST', '*CLS', '*SRE 0', '*ESE 0', ':STAT:PRES'):
            self.write(c)
        idn = self.query('*IDN?')             # HEWLETT-PACKARD,53132A,0,<fw>
        if ',5313' not in idn:
            raise CounterError('not a 53131A/53132A: %r' % idn)
        self.check('reset')
        return idn

    def use_external_reference(self):
        self.write(':ROSC:SOUR EXT')
        self.write(':ROSC:EXT:CHEC ONCE')      # +2009 now if the 10 MHz is missing
        e = self.errors()
        self.write(':ROSC:EXT:CHEC ON')
        if e:
            raise CounterError('external reference: %s' % e)
        internal = int(self.query(':STAT:OPER:COND?')) & 512
        return self.number(':ROSC:EXT:FREQ?'), not internal

    def setup_input(self, ch=1, coupling='DC', impedance=1e6, atten=1, lp_filter=False,
                    level=None, slope='POS', hysteresis=None):
        w = self.write
        w(':INP%d:COUP %s' % (ch, coupling)); w(':INP%d:IMP %g' % (ch, impedance))
        w(':INP%d:ATT %d' % (ch, atten)); w(':INP%d:FILT %s' % (ch, 'ON' if lp_filter else 'OFF'))
        w(':EVEN%d:SLOP %s' % (ch, slope))
        w(':EVEN%d:LEV:AUTO ON' % ch if level is None else ':EVEN%d:LEV %.3f' % (ch, level))
        if hysteresis is not None:            # 0 = HI sensitivity (current firmware)
            w(':EVEN%d:HYST:REL %d' % (ch, hysteresis))
        self.check('input setup')

    @staticmethod
    def read_timeout(gate, f_min):
        return gate + 3.0 / f_min + 3.0

    def configure(self, ch=1, gate=1.0, expected=None, period=False):
        func = 'PER' if period else 'FREQ'
        for c in (':INIT:CONT OFF', ':FUNC "%s %d"' % (func, ch), ':FREQ:ARM:STAR:SOUR IMM',
                  ':FREQ:ARM:STOP:SOUR TIM', ':FREQ:ARM:STOP:TIM %g' % gate):
            self.write(c)
        if expected:
            self.write(':FREQ:EXP%d %g' % (ch, expected))   # within 10 % of the input
        self.check('configure')
        return func

    def frequency(self, ch=1, gate=1.0, expected=None, f_min=None, period=False):
        func = self.configure(ch, gate, expected, period)
        v = self.number(':READ:%s?' % func, self.read_timeout(gate, f_min or expected or 100.0))
        self.check('reading')
        return v

    def statistics(self, n, ch=1, gate=1.0, expected=None, f_min=None):
        self.configure(ch, gate, expected)
        for c in (':CALC3:AVER:COUN %d' % n, ':CALC3:AVER ON', ':TRIG:COUN:AUTO ON', ':INIT'):
            self.write(c)
        self.query('*OPC?', n * self.read_timeout(gate, f_min or expected or 100.0))
        out = {}
        for k in ('MEAN', 'SDEV', 'MIN', 'MAX'):
            self.write(':CALC3:AVER:TYPE %s' % k)
            out[k.lower()] = self.number(':CALC3:DATA?')
        self.write(':CALC3:AVER OFF'); self.write(':TRIG:COUN:AUTO OFF')
        self.check('statistics')
        return out

    def backup_cal_data(self, path):
        """read-only: '#256' + 56 bytes -> file, plus the calibration count"""
        self.write(':CAL:DATA?')
        term, self.inst.read_termination = self.inst.read_termination, None
        try:
            raw = self.inst.read_raw()        # binary: may contain 0x0A, read to EOI
        finally:
            self.inst.read_termination = term
        n = int(raw[1:2]); block = raw[:2 + n + int(raw[2:2 + n])]
        open(path, 'wb').write(block)
        return len(block), int(self.query(':CAL:COUN?'))
```

Example (a lock-in's internal oscillator, 0.5 Hz-120 kHz, 1 Vrms sine):
```python
c = HP53132A('GPIB0::1::INSTR')                          # the reference address
c.reset()
print(c.use_external_reference())                        # (10000000.0, True)
c.setup_input(1, coupling='DC', impedance=1e6, level=0.0,
              lp_filter=False)                            # LP filter on only well below 100 kHz
f = c.frequency(1, gate=10.0, expected=0.5, f_min=0.45)  # about 12-14 s at 0.5 Hz
s = c.statistics(10, 1, gate=1.0, expected=1000.0)       # mean/sdev/min/max at 1 kHz
```