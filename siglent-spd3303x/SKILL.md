---
name: "siglent-spd3303x"
description: "Operate, program (SCPI over USB/LAN), verify and calibrate Siglent SPD3303X / SPD3303X-E bench power supplies, incl. firmware quirks and the adjustment procedure."
---

# Siglent SPD3303X / SPD3303X-E: remote control, verification and calibration

The SPD3303X and SPD3303X-E are three-output linear bench supplies. CH1 and CH2 are programmable
over 0 to 32 V and 0 to 3.2 A and can run independently, in series (0 to 60 V, 3.2 A) or in parallel
(0 to 32 V, 6.4 A). CH3 is a fixed rail, 2.5 V, 3.3 V or 5.0 V at up to 3.2 A, selected by a
front-panel switch. Total output is 220 W. The two models differ in resolution and accuracy only:
1 mV / 1 mA on the SPD3303X, 10 mV / 10 mA on the SPD3303X-E. Remote control is SCPI over a USBTMC
device port or LAN (VXI-11, or a raw socket on TCP 5025).

Everything marked ✔ was checked on a real **SPD3303X, firmware
1.01.01.03.12R1, hardware V6.1**, over USBTMC (August 2026). Behaviour not marked
comes from Siglent's documents or from a disassembly of the same firmware release. Earlier releases
(1.01.01.02.xx, STM32-based) keep the documented command set but are not covered by the firmware
notes here.

## Quick start (PyVISA)

```python
import pyvisa
rm = pyvisa.ResourceManager()
name = [r for r in rm.list_resources() if "0XF4EC" in r.upper() and "0X1430" in r.upper()][0]
spd = rm.open_resource(name)                   # USB0::0xF4EC::0x1430::<serial>::0::INSTR
spd.timeout = 5000
spd.read_termination = spd.write_termination = "\n"
print(spd.query("*IDN?"))   # Siglent Technologies,SPD3303X,<serial>,1.01.01.03.12R1 V6.1 ✔
spd.write("OUTP:TRACK 0")    # independent
spd.write("CH1:VOLT 5.000")
spd.write("CH1:CURR 0.500")
print(spd.query("CH1:VOLT?"))   # 5.000: the set point, read back to confirm it took
spd.write("OUTP CH1,ON")
print(spd.query("MEAS:VOLT? CH1"), spd.query("MEAS:CURR? CH1"))
spd.write("OUTP CH1,OFF")
```

Compare the USB ids upper-cased: a check for `"0xF4EC" in r.upper()` never matches, because the
upper-cased string reads `0XF4EC`. Over LAN use `TCPIP0::<ip>::INSTR` (VXI-11) or
`TCPIP0::<ip>::5025::SOCKET` with `\n` termination.

**Rules that matter in practice:**

1. **The error queue does not report the instrument's refusals.** A setting the instrument
   rejects (out of range, bad channel, wrong keyword, busy timer) leaves `SYST:ERR?` answering
   `+0, No error` ✔. Worse, several commands that work queue `-108,Parameter not allowed` while
   doing exactly what was asked, `TIMER:SET` and the `CAL:` commands among them ✔. Never decide
   success from `SYST:ERR?`. Read the value back after every setting.
2. **An unknown header gets no reply at all.** The query times out and `-113,Undefined
   header,<text>` is queued ✔. Catch the timeout, `spd.clear()`, then drain `SYST:ERR?` until
   `+0`.
3. **Use the spellings in the command appendix exactly.** Matching is case-insensitive
   (`ch1:volt?` works ✔), but Siglent registered most commands in ALL CAPS, which disables the SCPI
   short-form rule. `MEAS:POWE?` and `MEAS:POWER?` work; `MEAS:POW?` and `CH1:VOLTAG?` fail with
   -113 ✔. A few mixed-case patterns (`FACTory:CALibrate:STATus?`, the SCPI-99 set) do short-form.
4. **`MEAS:...?` returns 0.000 while the output is off** ✔. It reads the converter only when the
   channel is on. `*READALL?` does not apply that gate (see below).
5. **CH3 is not remotely controllable**, whatever the Quick Start says. `OUTP CH3,ON` is accepted,
   does nothing and reports no error ✔. Use the front panel.
6. **Series and parallel slave CH2's set point to CH1's, and it stays slaved after independent is
   restored** ✔. A 0, 1, 2, 0 sequence of `OUTP:TRACK` left CH2 at CH1's 24.000 V / 3.200 A having
   started at 18.000 V / 2.000 A. Re-set and read back both channels after changing tracking.
   `OUTP CH2,...` is refused (silently) in series or parallel.
7. **Settle before you read.** An unloaded channel has nothing to discharge into and falls for
   seconds after a downward step. Poll `MEAS:VOLT?` until two readings agree within about 2 mV.
   A reading taken too early once produced a bad calibration fit.
8. **Limits and parsing.** Voltage up to 32.0 V, current up to 3.232 A (1 % above the 3.2 A
   specification), OCP up to 3.5 A; a value equal to the limit is accepted. Setting values pass
   through `fabs`, so `CH1:VOLT -5` sets +5 V. Keyword parameters are case-insensitive
   (`OUTP ch1,on`).
9. **A running timer locks the channel.** `VOLT`, `CURR` and the OCP setters are refused,
   without an error, while that channel's timer is running. `TIMER` and `TIMER:SET` are refused in
   series or parallel.
10. **Do not send commands that are not in this skill.** The firmware registers 147 command
    spellings, and some of the unlisted ones rewrite stored identity data or non-volatile settings
    with no confirmation. Do not probe for them on an instrument that matters.

## Typical tasks

**Set a channel and confirm it.** Write, wait about 0.2 s, read the set point back and compare
within 0.02. Switch the output on and confirm from the status word (bit 4 CH1, bit 5 CH2), since
the instrument reports success either way.

```python
def setv(ch, v):
    spd.write(f"CH{ch}:VOLT {v:.3f}"); time.sleep(0.2)
    got = float(spd.query(f"CH{ch}:VOLT?"))
    if abs(got - v) > 0.02: raise RuntimeError(f"CH{ch} asked {v}, reads {got}")

def status():
    return int(spd.query("SYST:STAT?"), 16)      # e.g. '0x34'

def output(ch, on):
    spd.write(f"OUTP CH{ch},{'ON' if on else 'OFF'}"); time.sleep(0.3)
    if bool(status() & (0x10 << (ch - 1))) != on: raise RuntimeError("output did not switch")
```

**Everything in one query.** `*READALL?` (undocumented) returns eleven fields: status word as a
*decimal* integer, CH1 V, I, P, CH2 V, I, P (measured), then CH1 Vset, Iset, CH2 Vset, Iset ✔:

```
52,24.022,0.001,0.032,24.003,0.001,0.018,24.000,3.200,24.000,3.200
```

The measured fields are **not** zeroed when an output is off: they hold the last value measured
before switch-off, indefinitely ✔. Check the output bits in field 1 before trusting them.

**Over-current protection.** `CH1:OCP 2.0` / `CH1:OCP?` (undocumented; ceiling and default
3.500 A ✔). When the output current reaches the threshold the channel switches off. The setting is
stored in non-volatile memory. OCP arrived in firmware 1.01.01.02.07R2.

**Timed sequence.** Up to five steps per channel, each up to 10000 s, independent mode only:

```
TIMER:SET CH1,1,5.0,0.5,10        # group, volts, amps, seconds
TIMER:SET? CH1,1                  -> 5.000,0.500,10,   (trailing comma ✔)
TIMER CH1,ON
```

Switching the output off pauses the countdown; switching it on resumes it.

**Save and recall.** `*SAV n` / `*RCL n`, n = 1 to 5 (mode, set points, timer setup). `*DEL n`
(undocumented) deletes a slot. `*RCL` of an empty slot is refused silently.

**Front-panel lock.** `*LOCK`, `*UNLOCK`, `*LOCK?` -> `LOCK` / `UNLOCK` ✔ (undocumented).

**Network.** `IP?`, `MASK?`, `GATE?` (short forms of `IPADDR?` etc.), `DHCP?` -> `DHCP:ON`.
`IPST?` (undocumented) returns the whole configuration in one line ✔:
`IPST,IP,0,0,0,0,NETMASK,0,0,0,0,GATEWAY,0,0,0,0,MAC,74,5B,C5,22,72,DF,DHCP,1`. Static addresses
are ignored while DHCP is on.

**Instrument health.** `FACT:CAL:STAT?` returns `1` when the firmware's internal check list
passes ✔, otherwise `0` followed by `file:line,message;` records. `FACT:TIME:STAR?` is seconds
since power-on ✔ (not a power-cycle count).

## Front panel

| Key | Short press | Long press |
|---|---|---|
| Wavedisp | Waveform display (yellow = voltage, green = current) | |
| Ser / Para | Series / parallel mode | |
| IP/Store | LAN settings | (after a short press) Store/Recall, FILE1 to FILE5 |
| Timer | Timer setup | |
| System/version key | Version information | Key lock on/off |
| 1 / 2 | Select CH1 / CH2 | |
| On/Off (per channel) | Output on/off | |
| All On/Off | Both outputs | **at power-on: production self-test, see below** |
| CH3 On/Off | CH3 output | |
| Fine | Select digit | Enter/exit OCP (per the 1.01.01.02.07R2 release note) |
| Left / Right | Move cursor | Left: CC-mode beep on/off (1.01.01.03.12R1). The Quick Start says long Right enters OCP; the release note says Fine. Not checked on the bench. |

**Holding All On/Off while switching on starts Siglent's production self-test** (confirmed on the bench
on this unit). It runs only when the instrument's factory flag is set, which it is after any
settings reset. When the test finishes it **restores default settings and saves them**: OCP back to
3.5 A on both channels, IP, mask and gateway to 0.0.0.0, DHCP on, timer groups cleared.
Calibration, serial number and MAC address are not touched. Record `IPST?`, `CH1:OCP?`,
`CH2:OCP?` and `*READALL?` before trying it on an instrument whose configuration matters.

Rear panel: the AC input selector (100 / 120 / 220 / 230 V). Disconnect mains before changing it.
A mismatch blows the fuse.

Wiring for tracked modes: series takes the load between CH2 + and CH1 -, controlled from CH1;
parallel takes it from the CH1 terminals, and CH2 runs in CC only.

Set points drift until the supply has been on for about 30 minutes; Siglent says so in the Quick
Start troubleshooting section, and that is the warm-up to allow before any measurement that
matters.

## Calibration (adjustment)

Each of four quantities per channel is corrected by a straight line, `corrected = a * raw + b`,
fitted through two measured points: voltage setting, voltage readback, current setting, current
readback. Siglent documents the commands in the note "SPD series Adjustment method by manual".

| Command | Meaning |
|---|---|
| `*CALCLS n` | Reset one coefficient pair to a = 1, b = 0. n = 0 to 3 for CH1 (volt set, volt readback, current set, current readback), 4 to 7 for CH2 in the same order, **any value above 7 clears everything**. No parameter: nothing happens. |
| `CAL:VOLT CHx,{1\|2},<measured>` | Voltage pass. One pass fixes setting and readback together. |
| `CAL:CURR CHx,{1\|2},<measured>` | Current readback pass (the load sets the current). |
| `CAL:CURR CHx,{3\|4},<measured>` | Current setting pass (the supply's limit sets the current). |
| `*CALST` | Write the working coefficients to flash. **The only irreversible step.** |
| `*CALRCL` | Reload the stored coefficients, discarding the working copy (undocumented). |

`CALIBRATION:VOLTAGE`, `CALIBRATION:VOLT` and `CAL:VOLTAGE` are the same command, and likewise for
current.

**The working-copy model, demonstrated about ten times on this unit:** `*CALCLS` and `CAL:` change
RAM only and take effect immediately; `*CALRCL` and a power cycle both restore what is in flash;
only `*CALST` writes. Clearing the CH1 voltage readback pair moved the reported voltage from
24.0270 V to 23.6600 V, and `*CALRCL` returned it to 24.0270 V exactly, every time ✔.

**There is no backup and no restore.** The instrument cannot report its stored coefficients.
Deriving them by measurement was built once and deliberately dropped: it is inference, not a
read-back, and readjusting is easy. Do not reintroduce it. After `*CALST`, the only way back is to
adjust again against a reference.

**Two rules Siglent's note leaves out:**

1. **Clear the pairs a pass overwrites, immediately before that pass.** The instrument fits the new
   line through the values it currently reports, which already carry the old correction; skip the
   clear and the correction is applied twice (a 2.5 % gain applied twice, on this unit). Voltage:
   `*CALCLS 0` and `1` (CH1), `4` and `5` (CH2). Current readback: `3` / `7`. Current setting:
   `2` / `6`.
2. **Never interleave passes.** The first point waits in a working register for the second; voltage
   uses two registers and **both** current passes share one. Finish a pass or abandon it with
   `*CALRCL`.

**Procedure** (points from Siglent's note; meter 5.5 or 6.5 digit, electronic load with 0.1 mV /
0.1 mA readback; 30 min warm-up, 18 to 28 °C):

1. `OUTP:TRACK 0`, confirm status bits 2-3 read 01.
2. Voltage, meter alone across the channel: clear, set 1 A limit, set 1 V, output on, settle, read
   the meter, `CAL:VOLT CH1,1,<reading>`; repeat at 25 V with point 2.
3. Current readback, load and meter in series: clear, set 10 V and a 3 A limit, load CC 100 mA,
   `CAL:CURR CH1,1,<reading>`; load 2.5 A, `CAL:CURR CH1,2,<reading>`.
4. Current setting, same wiring: clear, load CC 3 A, set the limit to 100 mA,
   `CAL:CURR CH1,3,<reading>`; limit 2.5 A, `CAL:CURR CH1,4,<reading>`.
5. Verify as left (below). Only then `*CALST`.

A malformed calibration value (two decimal points, a bad point number) is refused with no visible
error, like every other refusal. Verify by measuring.

## Performance verification

Published accuracy (setting and readback alike):

| | SPD3303X | SPD3303X-E |
|---|---|---|
| Voltage | ±(0.03 % of reading + 10 mV) | ±(0.5 % + 2 digits) = 0.5 % + 20 mV |
| Current | ±(0.3 % of reading + 10 mA) | ±(0.5 % + 2 digits) = 0.5 % + 20 mA |

Worked limits for the SPD3303X: 1 V ± 10.3 mV, 25 V ± 17.5 mV, 100 mA ± 10.3 mA, 2.5 A
± 17.5 mA. An unknown model should be graded against the tighter SPD3303X figures.

Chapter 2 of the SPD3000X Series Service Manual (E01B) is the full verification. Its points:

| Test | Setup | Limit |
|---|---|---|
| Voltage accuracy | 32, 28, 22, 15, 10, 1, 0.1, 0.01, 0 V at 0.1 A limit, meter only | as above |
| Current accuracy | 0, 0.01, 0.1, 1, 2, 3.2 A at 32 V, load in CV at 31 V, meter in series | as above |
| CH3 | 2.5, 3.3, 5.0 V by the front switch | ± 8 % |
| Load regulation, CV | Vset 1, 5, 9, 13, 17, 21, 25, 29, 32 V; no load, then load CC 1, 2, 3 A | 0.01 % of Vset + 3 mV |
| Load regulation, CC | Iset 1, 2, 3.2 A at 32 V; load CV 31 V stepped down to 1 V | 0.2 % of Iset + 3 mA |
| Line regulation, CV | mains 100, 110, 120, 200, 220, 230, 240 VAC from a variable transformer; Vo 2 to 32 V in 3 V steps; load 3.198 A | 0.01 % + 3 mV |
| Line regulation, CC | same mains steps; Iset 1, 2, 3.2 A; load CV 31 V | 0.2 % + 3 mA |
| Ripple and noise | 32 V, load 3.198 A; scope 20 MHz limit, AC, 1:1 probe, 10 µF at the test point | 1 mVrms CV, 3 mArms CC |
| Overshoot | scope on the output at switch-on and off, no load and full load | "no overshoot" (no number given) |
| Transient response | load dynamic 1.598 / 3.198 A, 10 A/µs, 50 Hz | back within 15 mV in < 50 µs |

The manual's text for CV load regulation says 1, 2, 3 A while its blank table is headed 0, 1, 2,
3.2 A. The manual's 4-wire voltage table does not apply: these models have no sense terminals.
For line regulation, change the rear selector to match the transformer group every time.

Grade line and load regulation against the no-load or nominal-line reading, not against the set
point. Leave overshoot ungraded: Siglent gives no limit, and inventing one would put a number on a
certificate as if it were theirs.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `VI_ERROR_NCIC` opening any instrument, USB or GPIB | Host VISA fault, not the supply; it has been seen to clear by itself. Restart the VISA service or the PC. |
| Query times out | Unrecognised spelling (rule 3). Clear, then read `SYST:ERR?`. |
| A setting does not change, `SYST:ERR?` says no error | Refused: over the limit, timer running, or CH2 in a tracked mode. Read it back. |
| `MEAS:VOLT?` reads 0.000 | Output is off. |
| `*READALL?` shows voltage on an off channel | Stale value held from before switch-off. |
| CH2 set point changed by itself | A series or parallel selection slaved it to CH1. |
| `OUTP CH3,ON` does nothing | CH3 has no remote control. |
| Readings creep after power-on | 30 minute warm-up. |
| Calibration fit came out badly wrong | Pass not cleared first, passes interleaved, or a point read before the output settled. |
| Fuse blown during line regulation | Rear selector did not match the transformer setting. |
| `SCDP` screen capture returns short, ragged lines | Firmware defect: each line is cut at its first zero byte, so the BMP cannot be rebuilt over USBTMC. |
| Stored settings reset to defaults after a power-on | All On/Off was held at power-on and the production self-test ran. |


# Appendices

## Appendix: documented commands

Only these spellings are accepted (any capitalisation). `[CHx:]` forms with no prefix act on the
channel chosen by `INST`.

| Command | Spellings | Notes |
|---|---|---|
| Identity | `*IDN?` | vendor, model, serial, firmware, space, hardware |
| Save / recall | `*SAV n`, `*RCL n` | n = 1 to 5 |
| Channel select | `INSTRUMENT`, `INST` {CH1\|CH2}; `INSTRUMENT?`, `INST?` | |
| Voltage set | `CH1:VOLT`, `CH1:VOLTAGE`, `CH2:VOLT`, `CH2:VOLTAGE`, `VOLT`, `VOLTAGE` <V> | 0 to 32.0 |
| Voltage set point | the same with `?` | the set point, not a measurement |
| Current set | `CH1:CURR`, `CH1:CURRENT`, `CH2:CURR`, `CH2:CURRENT`, `CURR`, `CURRENT` <A> | 0 to 3.232 |
| Current set point | the same with `?` | |
| Measure | `MEAS:VOLT?`, `MEAS:VOLTAGE?`, `MEASURE:VOLT?`, `MEASURE:VOLTAGE?`, and `CURR`/`CURRENT`, `POWE`/`POWER` likewise, optional ` CH1`/` CH2` | 0 when the output is off |
| Output | `OUTP`, `OUTPUT` {CH1\|CH2},{ON\|OFF} | CH3 accepted but ignored |
| Tracking | `OUTP:TRACK`, `OUTPUT:TRACK` {0\|1\|2} | independent, series, parallel |
| Waveform display | `OUTP:WAVE`, `OUTPUT:WAVE` {CH1\|CH2},{ON\|OFF} | |
| Timer | `TIMER`, `TIME` {CH1\|CH2},{ON\|OFF} | |
| Timer step | `TIMER:SET`, `TIME:SET` CHx,group,V,A,s; `...:SET? CHx,group` | queues -108 although it works |
| Version | `SYSTEM:VERSION?`, `SYSTEM:VERS?`, `SYST:VERSION?`, `SYST:VERS?` | `1.01.01.03.12R1` |
| Errors | `SYSTEM:ERROR?`, `SYSTEM:ERR?`, `SYST:ERR?`, `SYST:ERROR?`, `SYST:ERR:NEXT?` | parser errors only |
| Status | `SYSTEM:STATUS?`, `SYSTEM:STAT?`, `SYST:STATUS?`, `SYST:STAT?` | `0x%x`, lower case |
| Network | `IPADDR`/`IP`, `MASKADDR`/`MASK`, `GATEADDR`/`GATE` <a.b.c.d> and `?`; `DHCP {ON\|OFF}`, `DHCP?` | short forms undocumented |
| Calibration | `CAL:VOLT`, `CAL:CURR` (and the long forms), `*CALCLS n`, `*CALST` | see Calibration |

## Appendix: useful undocumented commands

All confirmed on the bench unless noted.

| Command | Returns / does |
|---|---|
| `*READALL?` | eleven fields, see Typical tasks |
| `CH1:OCP <A>`, `CH2:OCP <A>`, `CH1:OCP?`, `CH2:OCP?` | over-current threshold, max and default 3.5 A |
| `OUTP:WAVE? CHx` | `ON` / `OFF` |
| `*DEL n` | delete save slot n (not exercised) |
| `*LOCK`, `*UNLOCK`, `*LOCK?` | front-panel lock |
| `*CALRCL` | reload stored calibration |
| `FACT:CAL:STAT?` | `1` = internal checks pass |
| `FACT:TIME:STAR?` | seconds since power-on |
| `IPST?` | full network configuration, MAC in upper case |
| `MAC?` | MAC address, lower case, e.g. `74:5b:c5:22:72:df` |
| `SRLN?` | `SRLN Default,<serial>` |
| `system:product:id?` | `70` on the SPD3303X (the -E update file carries 71) |
| `IDN-SGLT-PRI?` | `IDN-SGLT-PRI SPD3303X` |
| `*CPU?` | `GD32F427VET6` (a fixed string) |
| `**READID` | `SPD` |
| `SCDP <line>` | one display line, 1 to 272; truncated by a firmware defect, see Troubleshooting |

## Appendix: SCPI-99 common and status commands

Supplied by the parser library, all live, short forms work ✔: `*CLS`, `*ESE`, `*ESE?`, `*ESR?`,
`*OPC`, `*OPC?` (1), `*SRE`, `*SRE?`, `*STB?`, `*TST?` (0), `*WAI`, `SYST:COUN?`,
`STAT:OPER:COND?`, `STAT:OPER:ENAB`, `STAT:OPER[:EVEN]?`, the three `STAT:QUES` equivalents, and
`STAT:PRES`. None reflects instrument state usefully; use `SYST:STAT?`.

## Appendix: status word (`SYST:STAT?`)

| Bit | Meaning |
|---|---|
| 0 | CH1 0 = CV, 1 = CC |
| 1 | CH2 0 = CV, 1 = CC |
| 2-3 | tracking: 01 independent (0x4), 11 series (0xC), 10 parallel (0x8) ✔. The Quick Start omits series. |
| 4 | CH1 output on |
| 5 | CH2 output on |
| 6 | CH1 timer running |
| 7 | CH2 timer running |
| 8 | CH1 waveform display |
| 9 | CH2 waveform display |

At rest, independent, both off: `0x4` ✔. CH1 then CH2 on: `0x14`, `0x34` ✔.

## Appendix: errors

`SYST:ERR?` is the parser library's queue: `-113,Undefined header,<text>` for an unknown command,
`-108,Parameter not allowed,` from some working multi-parameter commands, `+0, No error` when empty.
Read destructively, one entry per query.

The instrument's own refusals use a separate eleven-message table that drives on-screen
notifications only and is never visible to a host. The ones that occur: 1 "Too many numeric
suffices", 3 "Command keywords were not recognized" (bad keyword parameter), 6 "Wrong type of
parameter(s)" (two decimal points in a calibration value), 9 "Data out of range" (over a limit, bad
calibration point, `*CALCLS` with no parameter, bad `SCDP` line).

## Appendix: specifications (Service Manual E01B)

| Item | Value |
|---|---|
| CH1, CH2 | 0 to 32 V, 0 to 3.2 A each; series 0 to 60 V; parallel 0 to 6.4 A |
| CH3 | 2.5 / 3.3 / 5.0 V ± 8 %, 3.2 A |
| Load and line regulation, CV | ≤ 0.01 % + 3 mV |
| Load and line regulation, CC | ≤ 0.2 % + 3 mA |
| Ripple and noise | ≤ 1 mVrms (5 Hz to 1 MHz) CV, ≤ 3 mArms CC |
| Recovery time | < 50 µs for a 50 % load change, minimum load 0.5 A |
| Parallel | load and line regulation ≤ 0.01 % + 3 mV |
| Series | line ≤ 0.01 % + 5 mV, load ≤ 300 mV |
| CH3 regulation and ripple | ≤ 0.01 % + 3 mV, ≤ 1 mVrms |
| Maximum output | 220 W |
| Mains | 100 / 120 / 220 / 230 V ± 10 %, 50/60 Hz, selector on the rear |
| Display | 4.3 in TFT, 480 × 272 |
| Environment | 0 to 40 °C operating, ≤ 80 % RH |
| Size, weight | 225 × 143 × 278 mm, about 8 kg |

## Appendix: firmware versions

| Version | Date | Notes |
|---|---|---|
| 1.01.01.02.07R2 | 2021-02-07 | OCP added. STM32 MCU. |
| 1.01.01.03.10 | 2022-09-02 | GD32F427 MCU, hardware V6.1 only. 1.01.01.02.xx units cannot take it. |
| 1.01.01.03.12R1 | 2025-06-13 | Long press Left toggles the CC-mode beep. The version covered here. |

Updates go through Siglent's EasyPower application over USBTMC. The SPD3303X and SPD3303X-E ship
separate images of the same release; the model name in `*IDN?` is fixed in each build.