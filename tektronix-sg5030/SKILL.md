---
name: tektronix-sg5030
description: Operate, program (GPIB), verify and adjust the Tektronix SG 5030 leveled sine wave generator (TM 5000 plug-in), incl. firmware behaviour and the hidden SPCL 2535537 constants.
---

# Tektronix SG 5030 programmable leveled sine wave generator

The SG 5030 is a TM 5000-series plug-in (about 1990-1997) that makes a leveled, low-distortion sine wave from 0.1 Hz to 550 MHz at 4.5 mV to 5.5 V peak-to-peak into 50 Ω. Its main use is checking oscilloscope bandwidth and flatness. The output comes out of a separately cabled **Output Leveling Head**, which contains the attenuators, the level detectors and the impedance-matching circuits. Each head is calibrated to one generator: the serial number on the head cable must match the generator, and swapping heads needs the full adjustment procedure.

Control is through the front panel or GPIB (IEEE 488.1, Tektronix Codes and Formats V81.1). **It is not an IEEE 488.2 instrument: there are no `*` common commands and no SCPI.** `*IDN?` gives error 151; the identity query is `ID?`.

Manuals: Operator's 070-7705-01, Service 070-7703-01, Instrument Interfacing Guide 070-7704-00. Firmware V1.2 reports `ID TEK/SG5030,V81.1,F1.2`. The firmware notes in this skill come from a disassembly of V1.2 and were checked on a working instrument; where only the code was read, the text says so.

## Quick start (PyVISA)

```python
import pyvisa, time
rm = pyvisa.ResourceManager()
sg = rm.open_resource("GPIB0::10::INSTR")   # factory address 10
sg.write_termination = "\n"
sg.read_termination = ""     # works for both terminator settings; strip replies yourself
sg.timeout = 10000

def q(cmd, tries=40):
    """Query. While busy the SG 5030 answers a single 0xFF byte, so ask again."""
    for _ in range(tries):
        sg.write(cmd)
        r = sg.read_raw().decode("latin1").strip()
        if r and r != "\xff":
            return r
        time.sleep(0.25)
    raise TimeoutError(cmd)

def errors():
    """Drain the event queue (RQS ON): serial poll, then ERR?, until ERROR 0."""
    codes = []
    for _ in range(20):
        sg.read_stb()
        c = int(q("ERR?").split()[-1])
        if c == 0:
            return codes
        if c != 455:          # 455 = another event waiting, poll again
            codes.append(c)
    return codes

print(q("ID?"))                  # ID TEK/SG5030,V81.1,F1.2
print(errors())                  # [401] after power-up: the power-on event
sg.write("FRE 100E6;AMP 0.5;OUT ON")
time.sleep(0.2)                  # settling: <150 ms OFF->ON, <80 ms other changes
print(q("SET?"), q("LEV?"), errors())
sg.write("OUT OFF")
```

### Rules that matter in practice

1. **Only `ID?`, never `*IDN?`.** Instrument-discovery software (for example a VISA vendor's connection utility) often sends `*IDN?` when the instrument appears on the bus, which leaves an E151 on the display and a 151 in the queue after every power-up. It is harmless; turn off automatic identification to stop it.
2. **Terminator.** Factory setting is **EOI only**: replies end with EOI on the last character and no line ending. With **LF EOI** selected (SPCL 241), replies end with **CR LF**, EOI on the LF, and input may end with LF. Set the VISA read termination to none and strip replies, and the same code works with both.
3. **Busy replies.** If a query is read before the instrument has finished (after `TES`, `REC n`, sending back a `SET?` string), the reply is a single **0xFF** byte plus the terminator. Retry until you get text. Plain `pyvisa.query()` fails on it with a decode error.
4. **One query per message.** The manual warns that responses can be lost if a message holds several queries, with no error raised. A new message also discards unread output.
5. **Errors need a serial poll first when RQS is ON.** `ERR?` returns the event from the last serial poll. If another event is waiting and you have not polled, it returns **455**. Serial poll, then `ERR?`, repeat until 0. With `RQS OFF`, `ERR?` returns events in turn without polling.
6. **Every syntax problem is error 151.** Misspelt or unknown headers, unknown arguments, a missing `?`, a bad number and a sign where none is allowed all report 151 on V1.2. The other 1xx codes in the manual did not appear in testing, and 154 can never occur (bytes 0x80-0xFF pass the lexer as ordinary characters).
7. **Out-of-range values are clamped and raise 205.** `FRE 700E6` sets 550 MHz and gives 205. Values with too much resolution are rounded silently.
8. **Output is OFF at every power-up.** All other settings come back as they were at power-off.
9. **In local state only queries are executed.** Setting commands give an error while the instrument is under front-panel control. The controller puts it in remote with REN; most front-panel keys return it to local.
10. **Frequency changes are applied to the hardware only while the output is ON.** With the output off a new frequency is stored and checked, and the synthesizer is reprogrammed when `OUT ON` arrives, so allow the 150 ms OFF-to-ON settling.

## Specifications (Operator's Manual Table 1-2)

| Item | Value |
|---|---|
| Frequency | 0.1 Hz to 550 MHz. Resolution 0.1 Hz to 4.9999 kHz, 1 Hz to 49.999 kHz, 10 Hz from 50 kHz |
| Frequency accuracy, internal timebase (1 yr) | ±(3 ppm + 0.06 Hz) to 4.9999 kHz, ±(3 ppm + 0.3 Hz) to 49.999 kHz, ±(3 ppm + 3 Hz) above. Aging 1 ppm/yr |
| External timebase | 10 MHz ±1.5 ppm, -10 to +10 dBm (70-700 mV rms), 50 Ω AC / 500 Ω DC, locks in < 3 s |
| Timebase out | 10 MHz, 400 mV p-p into 50 Ω, 50 Ω source |
| Amplitude | 4.50 mV to 5.500 V p-p into 50 Ω, or -42.95 to +18.75 dBm. Resolution 0.02 mV to 55.00 mV, 0.2 mV to 550.0 mV, 2 mV to 5.500 V, 0.05 dB |
| Amplitude accuracy | ±1.5 % of setting, 0.1 Hz to 50 kHz |
| Flatness (relative to 50 kHz) | ±1.5 % to 100 MHz, ±3 % to 250 MHz, ±4 % to 550 MHz |
| Source resistance | 50 Ω ±1 %; VSWR < 1.2:1 to 550 MHz |
| DC offset | < ±1 % of Vpp (20-30 °C), < ±2 % (0-40 °C) |
| Harmonics, 50 kHz-550 MHz | 2nd < -30 dBc, 3rd < -35 dBc, others < -40 dBc |
| Spurious and noise | Below 50 kHz all harmonics and spurs < -50 dBc. Non-harmonics < -40 dBc. Phase noise < -85 dBc/Hz at 10 kHz offset |
| GPIB settling (from EOI) | Output OFF to ON < 150 ms; other changes < 80 ms |
| Reference frequency | Fixed 50.00 kHz (REF FREQ), amplitude from the AMPL setting |
| Warm-up | 30 minutes (60 after exposure to condensing humidity) |
| GPIB subsets | SH1 AH1 T6 L4 SR1 RL1 PP0 DC1 DT0 C0 E2 (no parallel poll, no GET) |

Amplitude is peak-to-peak into 50 Ω. Into a high-impedance load the voltage doubles; use a 50 Ω feed-through at the load. 0 dBm corresponds to 632.5 mV p-p (223.6 mV rms).

## Command reference

Headers need their first three letters (ID needs two); any extra letters must match the full spelling (`FREQ` is fine, `FREX` is 151). Case does not matter. Commands are separated by `;`. A unit suffix follows `:`. The space after a header is optional and may be followed by an optional comma (`FRE ,1E6`). Numbers are `digits[.digits][E[+|-]digits]`; only AMPLITUDE accepts a leading sign. Responses are upper case.

| Command | Form | Notes |
|---|---|---|
| `AMPlitude <num>[:DBM]` | set | Volts p-p, or dBm with `:DBM`. `AMP 0.5`, `AMP 3.5E-2`, `AMP -30:DBM` |
| `AMPlitude?` | query | `AMPLITUDE 400.0E-3` or `AMPLITUDE -15.00:DBM` (whichever unit was last set) |
| `FREquency <num>` | set | Hz. `FRE 1.5E4` |
| `FREquency?` | query | `FREQ 125.00E+3` |
| `REFreq ON\|OFF`, `REFreq?` | set/query | 50 kHz reference on/off; the variable frequency is kept and comes back with OFF |
| `OUTput ON\|OFF`, `OUTput?` | set/query | Output on/off at the head; 50 Ω source kept when off |
| `STOre <1-20>` | operational | Saves the current settings; 0 or 21 gives 253 |
| `RECall <0-20>` | operational | 0 = INIT defaults; an empty slot gives the defaults |
| `INIt` | system | OUTPUT OFF, AMPLITUDE 1.000, FREQUENCY 10 MHz, REFREQ OFF, RQS ON, USEREQ OFF. Stored setups, address and terminator unchanged |
| `SET?` | query | All settings as a command string (up to 84 bytes) that can be sent back: `OUTPUT ON;AMPLITUDE 17.40E-3;FREQUENCY 123.34543E+6;REFREQ OFF;RQS ON;USEREQ OFF` |
| `TESt` | operational | Self test (about 2 s), then restores settings; a failure raises an SRQ (codes 360-377) |
| `RQS ON\|OFF`, `RQS?` | status | Service requests on/off. With OFF, events are still queued and the SRQ LED lights |
| `USEreq ON\|OFF`, `USEreq?` | status | INST ID button raises event 403 only when ON |
| `ERRor?` / `EVEnt?` | query | `ERROR 205`. Same command, two names |
| `LEVeled?` | query | `LEVELED YES` / `NO` |
| `EXTtb?` | query | `EXTTB ACTIVE` / `INACTIVE` (10 MHz present on EXT TIMEBASE) |
| `ID?` | query | `ID TEK/SG5030,V81.1,F1.2` |
| `HELp?` | query | List of headers |
| `CAL?` | query | The 12 calibration DAC values: `CAL 139,136,140,2746,2755,2747,2838,340,2843,341,2841,342` (manual example). **Read only**: there is no command to write them |
| `ABStouch <0-27>` | setting | Presses a front-panel control (table below) |

`CAL?` order: 1 LF power amp offset, 2 LF preamp offset, 3 RF power amp offset (offset DACs, 1-254); 4-6 LF gain x1, x10, x100; 7/8 RF gain max/min x1; 9/10 RF max/min x10; 11/12 RF max/min x100. **Save the `CAL?` line before any repair or battery work.** Lost CAL values can only be restored by the SPCL 99 adjustment (or by writing the NVRAM chips directly).

### ABSTOUCH codes

| n | Control | n | Control | n | Control |
|---|---|---|---|---|---|
| 0 | Knob up | 10 | 3 | 20 | AMPLITUDE |
| 1 | Knob down | 11 | kHz/mV | 21 | VARIABLE (frequency) |
| 2 | OUTPUT ON/OFF | 12 | 4 | 22 | STORE |
| 3 | CLEAR | 13 | 5 | 23 | SPCL |
| 4 | 0 | 14 | 6 | 24 | < digit select |
| 5 | . | 15 | MHz/V | 25 | > digit select |
| 6 | +/- | 16 | 7 | 26 | REF FREQ |
| 7 | Hz/dBm/ENTER | 17 | 8 | 27 | RECALL |
| 8 | 1 | 18 | 9 | 28+ | error 205 |
| 9 | 2 | 19 | INST ID | | |

26 and 27 are in the Interfacing Guide but not in the Operator's Manual table. ABSTOUCH keys are accepted in remote and are the only way to reach SPCL functions over the bus:

```python
DIGIT = {'0': 4, '.': 5, '1': 8, '2': 9, '3': 10, '4': 12, '5': 13, '6': 14,
         '7': 16, '8': 17, '9': 18}
def press(*keys):
    """press(23, '240', 7) = SPCL 2 4 0 ENTER"""
    for k in keys:
        for c in ([k] if isinstance(k, int) else [DIGIT[ch] for ch in k]):
            sg.write("ABS %d" % c)
            time.sleep(0.25)
```

An error caused by an ABSTOUCH key (for example E250 from SPCL 99 with adjustment disabled) is shown on the display only. It does not reach the GPIB error queue, because the firmware treats ABSTOUCH keys as front-panel input.

## Status byte and event codes

Serial poll byte = class + 0x40 (requesting service) + 0x10 (message processor busy, the "or" values below).

| Code | Meaning | STB |
|---|---|---|
| 0 | No event | - |
| 101-107, 150, 151, 153-156 | Command errors (V1.2 only produces 151) | 97 / 113 |
| 205 | Argument out of range | 98 / 114 |
| 250 | Not in adjustment mode | 98 / 114 |
| 251 | I/O buffers full, output flushed (input and output both full; output discarded) | 98 / 114 |
| 252 | Settings buffer empty | 98 / 114 |
| 253 | Illegal settings number | 98 / 114 |
| 254 | Beyond adjustment limit (never raised by V1.2; SPCL 99 clamps instead) | 98 / 114 |
| 301 / 302 | Interrupt fault / system error | 99 / 115 |
| 350 | HF unleveled | 99 / 115 |
| 351-355 | Reference / wide / narrow / offset / DDS loop unlocked | 99 / 115 |
| 356 | Leveling head unplugged | 99 / 115 |
| 360-364 | EPROM checksum, NVRAM test, RAM test, NVRAM battery, CAL checksum | 99 / 115 |
| 370-377 | Self-test: output off, ref freq, DDS off, 10.00000 MHz, 10.00001 MHz, 500 MHz (actually run at 550 MHz), wide-loop divider, output amp | 99 / 115 |
| 401 | Power on | 65 / 81 |
| 403 | INST ID user request (USEREQ ON) | 67 / 83 |
| 455 | ERR? read with another event pending and no serial poll | - |

Events from GPIB commands go into the queue (41 deep; the oldest is dropped when full) and are also shown on the display as E-codes. Front-panel events show on the display only, except 403. **Device clear** (`sg.clear()`) empties the queue and releases SRQ, but keeps a pending power-on event (401). E360-E377 found at power-up can only be cleared from the front panel.

## Front panel

- **AMPL / VARIABLE / REF FREQ** select what the display and keypad set. Enter a value on the keypad and finish with a unit key (MHz/V, kHz/mV, Hz/dBm/ENTER). Over-resolved entries are rounded.
- **Knob and < > DIGIT SELECT**: the selected digit blinks; the knob steps it. At power-up the knob steps the third significant digit.
- **STORE n ENTER** (1-20), **RECALL n ENTER** (0-20, 0 = defaults). CLEAR cancels.
- **OUTPUT ON/OFF** at the OUTPUT HEAD connectors. Unplugging the head's multi-wire control cable turns the output off and lights UNLVL. With only the BNC unplugged the signal is still at the front panel but not at the load.
- **INST ID** shows the GPIB address and terminator (`10 LFEOI` or `10   EOI`) and raises 403 if USEREQ is ON.
- Indicators: REM, ADRS, SRQ (lit at power-up until the 401 is read), RECAL (CAL constants lost or adjustment in progress), UNLVL, UNLOC, EXT TIMEBASE ACTIVE.
- A display of `FE` and five hex digits means a firmware internal check failed (the digits are the code address). The firmware then marks the settings invalid and halts; power-cycle, and the defaults load.

### SPCL functions (SPCL, code, ENTER)

| Code | Function |
|---|---|
| 99 | Adjustment (calibration) mode. Needs SW3020 toggle 3 closed, else E250 |
| 201 | INIT the current settings **and all 20 stored setups** |
| 240 | Shows `GPIb  10`. Type a new address (0-31; 31 takes it off the bus) and ENTER |
| 241 | Shows `LF EOI` or `EOI`. The digit keys do nothing here: **turn the knob** to change it, then ENTER |
| 2535537 | Hidden service entry for 12 level-flatness constants (below). Not in any manual |

### Hidden SPCL 2535537: level-flatness constants

Twelve signed constants in NVRAM, separate from the CAL DACs and not reported by `CAL?`, set the RF flatness correction: four per attenuator decade (x1, x10, x100), in units of 0.01 % of amplitude. K1 is a slope against log frequency up to 100 MHz; K2-K4 are a quadratic in frequency above 100 MHz. Factory defaults: **11, 68, 115, -82, 13, 63, 178, -100, 24, 89, 286, -85**.

Behaviour, confirmed on V1.2:
- Entering the code turns the output OFF and shows `01 0011` (constant number, value; negatives as `04 -0082`).
- Each ENTER moves to the next constant. **ENTER with nothing typed keeps the value**; a typed number replaces it.
- The ENTER after constant 12 saves the checksum, leaves SPCL mode and **runs INIT**, so save `SET?` first and send it back afterwards.
- The values can only be read on the display. Write them down before changing anything. If the checksum is ever wrong at power-up, the firmware reloads the defaults.

Changing these alters RF flatness. Treat it as part of calibration and re-check flatness afterwards.

## Using it well

- Connect the leveling head **directly** to the load. Cable between head and load adds frequency-dependent loss that the leveling cannot correct. If a cable is unavoidable, use air line.
- For a high-impedance input (scope at 1 MΩ), put a precision 50 Ω feed-through at the input. The source then sees 25 Ω in parallel with the input capacitance; the -3 dB corner is 1/(2π·25 Ω·C).
- Use a DC block when the load has DC on it or is DC-sensitive (spectrum analyzer inputs). The block attenuates below about 1 MHz.
- For levels below 4.5 mV, add attenuators after the head.
- **Bandwidth measurement**: at the 50 kHz reference frequency (REF FREQ) set six divisions on the scope; switch to VARIABLE and raise the frequency until the trace is 4.2 divisions (70.7 %). The displayed frequency is the -3 dB point. With a wideband DVM, look for 70.7 % of the reference reading.
- Neither an open head nor a 75 Ω load trips LEVELED NO; the manual's causes are a short, an open control line or a leveling fault.

## Power-up, NVRAM and the DIP switch

At power-up the CPU checks both EPROMs, RAM and NVRAM, lights every LED and segment (lamp test), runs the hardware self test and restores the last settings with the output OFF. Hard ROM/RAM/NVRAM failures stop with a pattern on the four CPU-board LEDs:

| Failure | LED1 | LED2 | LED3 | LED4 |
|---|---|---|---|---|
| ROM | off | on | on | on |
| RAM | off | off | on | on |
| NVRAM | on | off | on | on |

The NVRAM chips (U3060, U3070 on the A3 CPU board) contain their own batteries (about ten years). When they fail, settings, stored setups, address and terminator are lost (E361/E363), and CAL constants too (E364, RECAL lit, nominal values loaded). The V1.2 firmware reloads address 10 and terminator EOI only (the Operator's Manual says 25). Replacement chips need the full adjustment and the setups re-entered.

DIP switch SW3020 is reached through the rear panel below the GPIB connector. Facing the rear, toggles are numbered from the top; **closed = pushed left**. Normal operation: all open (right).

| Toggle | Closed |
|---|---|
| 1 | Reinitialize firmware: according to the firmware, the current settings, address (10) and terminator (EOI) are reset at power-up; CAL values are kept while their checksum is good. Not tried |
| 2 | Diagnostic bypass (the firmware skips the power-up lamp test) |
| 3 | Enable adjustment (SPCL 99). Read when SPCL 99 is entered, so no power cycle is needed |
| 4 | Not used |

## Performance verification (Service Manual section 5)

Warm up 30 minutes. Equipment: counter (0.75 ppm), AC DVM (0.25 %, 1 Hz-100 kHz, for example a 3458A), spectrum analyzer to 3 GHz, RF power meter and sensor (100 kHz-3 GHz), precision 50 Ω terminations (SMA, and a BNC feed-through ±0.1 %), DC block, adapters.

1. **Frequency** (5.5 V, head to counter through 50 Ω): 10 Hz 9.93997-10.06003 Hz; 4.9999 kHz 4.999825-4.999975 kHz; 5 kHz 4.999685-5.000315 kHz; 49.999 kHz 49.99855-49.99945 kHz; REF 50 kHz 49.99685-50.00315 kHz; 10 MHz 9.999967-10.000033 MHz; 10.00001 MHz 9.999977-10.000043 MHz; 550 MHz 549.998347-550.001653 MHz.
2. **Spectral purity** (5.5 V, through a DC block): 2nd < -30 dBc, 3rd < -35 dBc, 4th-5th < -40 dBc. The output filters switch at 155/305 MHz going up and 145/295 MHz going down, so sweep up and down through 140-160 MHz and 290-320 MHz.
3. **Amplitude accuracy** (DVM AC rms on a 50 Ω feed-through): reading = Vpp / (2√2) ±1.5 %. 5.5 V gives 1.9445 V (1.9154-1.9737); 550 mV gives 0.19445 V; 552 mV gives 0.19516 V (0.19223-0.19809); 55 mV gives 19.445 mV; 1 V gives 0.35355 V; 2.5 V gives 0.88388 V. Checked at several frequencies from 10 Hz to 49.999 kHz.
4. **Flatness**: 50-100 kHz by DVM ratio to 50 kHz (0.985-1.015); 100 kHz to 550 MHz by power meter relative to 100 kHz, corrected with the sensor's cal factors; limits as in the specification table.
5. **VSWR**: < 1.2:1 to 550 MHz, measured with the power meter at the points the manual describes (Figures 5-5 and 5-6, worksheet Table 5-4).

## Adjustment (Service Manual section 6)

Only if the performance check fails, except the timebase, which should be set yearly. Use an insulated tool.

1. **Preparation**: close SW3020 toggle 3; remove the oscillator cover screw (top panel; not tethered or magnetic); take the right side cover off and run the unit in the left slot of a TM 5006A so the Output board adjustments can be reached through the empty slots. 30 minutes warm-up.
2. **Output hybrid bias** (only if spectral purity fails): 5.5 V. At 295 MHz approached from above, adjust cur6 for best 2nd harmonic. At 145 MHz approached from above, then slowly up to the worst 2nd harmonic, adjust cur1 and cur2. At 50 kHz adjust vee2 and cur4. Aim for 2nd and 3rd at -40 dBc and higher harmonics at -55 dBc, with the 3rd slightly below the 2nd for best flatness. The adjustments interact, so repeat. The heatsinks are hot.
3. **Timebase**: counter on TIMEBASE OUT, trim to 10.000000 MHz ±10 Hz.
4. **CAL constants, SPCL 99** (head into a precision 50 Ω feed-through on the DVM). Once started, finish it in order. The display shows `01- nnnn` (step, value); RECAL stays lit until the end. **The knob writes the value to NVRAM immediately** (CAL? shows it before ENTER); ENTER moves to the next step.

| Step | Target (DVM) | Window | Firmware clamp |
|---|---|---|---|
| 1 LF power amp offset | 0.0 mV DC | ±3 mV | 1-254 |
| 2 LF preamp offset | 0.0 mV DC | ±1 mV | 1-254 |
| 3 RF power amp offset | 0.0 mV DC | ±3 mV | 1-254 |
| 4 LF gain x1 | 1.9445 V AC | 1.9435-1.9455 | 2635-2935 |
| 5 LF gain x10 | 0.19445 V AC | 0.19435-0.19455 | 2615-2915 |
| 6 LF gain x100 | 19.445 mV AC | 19.435-19.455 | 2575-2875 |
| 7 RF gain max x1 | 1.9445 V AC | 1.9430-1.9460 | 2640-2960 |
| 8 RF gain min x1 | 0.19445 V AC | 0.19390-0.19500 | 180-500 |
| 9 RF gain max x10 | 0.19445 V AC | 0.19430-0.19460 | 2620-2940 |
| 10 RF gain min x10 | 19.445 mV AC | 19.390-19.500 | 180-500 |
| 11 RF gain max x100 | 19.445 mV AC | 19.430-19.460 | 2585-2905 |
| 12 RF gain min x100 | 1.9445 mV AC | 1.9420-1.9470 | 175-475 |

The ENTER after step 12 saves the CAL checksum, turns RECAL off and runs INIT. Open toggle 3 again afterwards. A value stuck at a clamp limit means the hardware needs more correction than the firmware allows: troubleshoot rather than accept it. Steps 1-3 null DC offsets with no signal; 4-6 run the LF path at 1 kHz; 7-12 run the HF path at 50 kHz. The max/min steps are the 5.5 V and 0.55 V points of each decade, which the level calculation interpolates between.

Pressing ENTER at every step without turning the knob walks through the procedure without changing anything, which is a safe way to read the stored values on the display.

## Backup before service

1. `SET?`, `CAL?`, `ID?`.
2. Each stored setup: `REC n` then `SET?` (n = 1-20; restore with the string then `STO n`).
3. The 12 SPCL 2535537 constants, read off the display (ENTER through all twelve, then send the `SET?` string back).
4. Address and terminator: press INST ID.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `pyvisa` decode error on a read | The 0xFF busy reply; read raw and retry |
| Read times out | Terminator mismatch: read termination must be none (EOI only) or `\n` |
| E151 at power-up, 151 in the queue | Discovery software sent `*IDN?` |
| ERR? keeps answering 455 | RQS ON and no serial poll between reads |
| Setting commands ignored, errors raised | Instrument in local; assert REN / address it |
| UNLVL lit, output off | Head control cable unplugged (356), short, leveling fault (350) |
| UNLOC lit | A synthesizer loop is unlocked (351-355); check EXT TIMEBASE signal |
| RECAL lit at power-up | CAL checksum bad (E364): nominal constants loaded, run SPCL 99 |
| E250 when entering SPCL 99 | SW3020 toggle 3 open (or set the wrong way) |
| `FE xxxxx` on the display | Firmware internal check failed; power-cycle |
| CPU LEDs show a pattern, no display | Hard ROM/RAM/NVRAM failure (table above) |

## Internals (V1.2, from the firmware)

- MC68HC000 at 10 MHz; two 27C512 EPROMs (160-6447 U2051 even byte, 160-6448 U3050 odd byte), RAM at 40000, battery NVRAM at 50000, TMS9914A GPIB controller, pSOS-68000 V4.13 kernel, XC2018 LCA loaded from the EPROMs at boot.
- Synthesis: a DDS below 50 kHz (10 MHz/6 clock below 5 kHz), and above 50 kHz a wide loop with divider N = ceil((f + 910 MHz)/10 MHz) - 1 plus a 1-2 MHz DDS offset. Output filters switch at 155/305 MHz up and 145/295 MHz down.
- Level: three decades set by two 20 dB pads in the head, with a level DAC interpolated between the CAL max/min points of each decade, plus the SPCL 2535537 flatness correction above 50 kHz.
- The EPROM checksum words at 1FFF8-1FFFF must be updated in any patched image, or the instrument stops with E360 or a hard LED code.
