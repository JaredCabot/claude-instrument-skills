---
name: "agilent-epm-power-meter"
description: "Operate, program (SCPI/GPIB), verify and service Agilent E4418B/E4419B EPM power meters and their 8480, E-series and N8480 sensors, incl. hidden DIAG/SERV commands, sensor EEPROM, boot ROM and firmware."
---

# Agilent E4418B / E4419B EPM power meters: GPIB control, sensors and service

The EPM series are average-power meters for thermocouple and diode sensors. The **E4418B** has
one channel (A); the **E4419B** has two (A and B) and adds ratio and difference measurements.
Both speak **SCPI over GPIB (IEEE-488.2)**, with an optional RS-232/RS-422 interface, and each
can emulate an older meter: HP 437B (E4418B) or HP 438A (E4419B), plus an undocumented HP 436A
mode on the E4418B. The front panel has a 1 mW, 50 MHz power reference output for calibrating
sensors.

Everything in this skill marked ✔ was checked on a real **E4419B** (firmware A2.09.01, boot ROM A.02.00), at GPIB address 13, with an N8482A on channel A and an 8481A on channel B. Undocumented behaviour comes from a full disassembly of firmware
A1.09.01 (E4418B) and A2.09.01 (E4419B); addresses are E4418B unless marked. Other firmware
revisions keep the command set but move the addresses.

The undocumented commands and internals are documented more fully in a companion firmware-analysis write-up.

## Quick start (PyVISA)

```python
import pyvisa
rm = pyvisa.ResourceManager()
pm = rm.open_resource("GPIB0::13::INSTR")      # factory address 13
pm.timeout = 10000                              # zero/cal and averaged reads are slow
print(pm.query("*IDN?"))      # Agilent Technologies,E4419B,<serial>,A2.09.01 ✔
pm.write("*CLS")
pm.write("UNIT1:POW DBM")
pm.write("SENS1:FREQ 1GHZ")    # frequency for the cal-factor correction
print(pm.query("FETC1?"))      # works with INIT:CONT ON (the power-up state)
print(pm.query("SYST:ERR?"))   # +0,"No error"
pm.control_ren(6)              # GTL: give the front panel back
```

`Tools/bench.py` in the project folder wraps this (`connect`, `q`, `w`, `local`, `identify`,
`verify_sensor`, `grab_display`) and is the quickest way to start a bench session.

**Rules that matter in practice:**

1. **`READ?` and `MEAS?` need `INIT:CONT OFF`.** With continuous triggering on (the power-up
   state) they fail with **-213 Init ignored** ✔. Use `FETC?` while continuous, or
   `INIT:CONT OFF` then `READ?`/`MEAS?`.
2. **A failed query sends no reply.** The read times out and the error sits in the queue ✔
   (seen with `SERV:SENS:FREQ:MAX?`, `CFAC?` on an E-series sensor, `*_TRG?`). Catch the
   timeout, do a device clear (`pm.clear()`), then read `SYST:ERR?` until `+0`.
3. **Zero, then calibrate, before trusting a reading.** Connect the sensor to the POWER REF
   output: `CAL1:ZERO:AUTO ONCE` (about 10 s; the meter switches the reference off for it),
   wait with `*OPC?`, then `CAL1:AUTO ONCE` (or `CAL1:ALL?`, which does both and returns 0 for
   pass). E-series and N8480 sensors without Option CFT set the reference cal factor
   themselves; 8480-series and N8480 Option CFT sensors need `CAL1:RCF <pct>` from the label
   (or an enabled CSET1 table) first. Some sensors need an adapter or the 11708A 30 dB pad on
   the reference (8481D, 8484A, 8485A/D, 8487A/D and others; see "Sensors").
4. **8480-series and N8480 Option CFT sensors need cal factors; the others carry them.** Either
   set `SENS1:CORR:CFAC <pct>` at each frequency or select a sensor table
   (`SENS1:CORR:CSET1:SEL "HP8481A";:SENS1:CORR:CSET1:STAT ON`) and set `SENS1:FREQ`.
   An EEPROM sensor reads its own table; `CFAC`, `GAIN1` and `LOSS1` then return -241 ✔
   (unless its stinger revision bytes are `4` and `1`, `3` or `5`).
5. **`OUTP:ROSC ON` turns the 50 MHz reference on and holds it on** ✔ (0 dBm read
   +0.00002 to +0.0021 dBm on an 8481A after zero and cal). Turn it off afterwards.
6. **Short forms must be exact.** `STAT:DEB:HAP` (not `HAPP`), `DIAG:BATT:FIT` (not `FITT`),
   `DIAG:DET:IMAG:HEADER` (full word). An intermediate truncation gives -113 ✔.
7. **Window and channel suffixes differ.** On `CONF`, `FETC`, `READ`, `MEAS`, `CALC`,
   `DISP:WIND` and `UNIT` the suffix is the **window** (1 upper, 2 lower). On `SENS`, `CAL`,
   `TRIG`, `INIT`, `ABOR`, `SERV:SENS` and `DIAG` it is the **channel** (1 = A, 2 = B). The source
   list `(@1)`/`(@2)` picks channels for a window. Channel 2 on an E4418B gives -114.
8. **Remote locks the panel.** Any GPIB traffic puts the meter in REMOTE. Send GTL
   (`pm.control_ren(6)`) or press Local when done.
9. Numeric replies are NR3 (`-3.58623935E+001`). 9.91E+37 means "not a number" ✔.
10. **`FETC?` right after `*RST` or a settings change gives -230** (no valid data). `*RST`
    also sets `INIT:CONT OFF`; `SYST:PRES` and power-up leave it ON.

## Typical tasks

| Task | Commands |
|---|---|
| One reading, dBm | `INIT1:CONT OFF;:UNIT1:POW DBM;:READ1?` |
| Zero and cal (E-series, N8480 without CFT) | sensor on POWER REF: `CAL1:ZERO:AUTO ONCE;*OPC?` then `CAL1:AUTO ONCE;*OPC?` |
| Zero and cal (8480, N8480 Opt CFT) | `CAL1:RCF 98.5` (from the sensor label), then as above |
| Frequency correction | `SENS1:FREQ 2.4GHZ` |
| 8480 cal-factor table | `SENS1:CORR:CSET1:SEL "HP8481A";:SENS1:CORR:CSET1:STAT ON;:SENS1:FREQ 10GHZ` |
| Fixed cal factor | `SENS1:CORR:CFAC 97.2` (8480, N8480 CFT); `SENS1:CORR:LOSS1 2.8` is the same thing as a loss ✔ |
| Offset (attenuator, coupler) | `SENS1:CORR:GAIN2 -20;:SENS1:CORR:GAIN2:STAT ON` |
| Averaging | `SENS1:AVER:COUN 64` (turns auto off); `SENS1:AVER:COUN:AUTO ON` to go back |
| Ratio A/B (E4419B) | `CONF2:POW:AC:RAT DEF,DEF,(@1),(@2)` then `READ2:POW:AC:RAT?` (CONF sets INIT:CONT OFF on the listed channels) |
| Difference A-B (E4419B) | `CONF2:POW:AC:DIFF DEF,DEF,(@1),(@2)` then `READ2:POW:AC:DIFF?` |
| Fast readings (E-series) | `SENS1:SPE 200;:TRIG1:SOUR IMM;:INIT1:CONT ON;:UNIT1:POW W;:FORM REAL`, then `FETC1?` in a loop |
| Relative to current | `CALC1:REL:AUTO ONCE` |
| Watts | `UNIT1:POW W` |
| Reference on/off | `OUTP:ROSC ON` / `OUTP:ROSC OFF` |
| Language | `SYST:LANG HP437B` (E4418B, documented) / `SYST:LANG HP438A` (E4419B; accepted by the firmware, no keyword in the manual) / `SYST:LANG SCPI`. Wait 100 ms; the meter goes to local |
| GPIB address | `SYST:COMM:GPIB:ADDR 13` |
| Sensor identity (E-series) | `SERV:SENS1:TYPE?`, `:SNUM?`, `:CDAT?`, `:CPL?` |
| Sensor EEPROM dump | `python Tools/dump_sensor_eeprom.py out.bin [channel] [size]` (read-only, one byte per query) ✔ |

Exact syntax, ranges and *RST values are in the appendices. Where this table and the appendix
disagree, trust the appendix (it is taken from the Programming Guide).

## Sensors

| Family | Examples | How the meter handles it |
|---|---|---|
| 8480 series (thermocouple and diode) | 8481A/B/D/H, 8482A/B/H, 8483A, 8485A/D, R/Q8486A/D, V/W8486A, 8487A/D | No EEPROM. Needs a reference cal factor for zero/cal and cal factors per frequency (fixed `CFAC` or a sensor table). `SERV:SENS:TYPE?` returns `A`, `B`, `D` or `H` ✔ (A seen). V8486A/W8486A need `SENS:V2P DTYP` |
| E-series | E4412A, E4413A, E9300/E9301/E9304 | EEPROM holds linearity, temperature compensation and cal factors, read at connect. Two ranges (`SENS:POW:AC:RANG`), 200 rdg/s capable. E9320 is not covered by these manuals |
| N8480 series | N8481A/B/H, N8482A/B/H, N8485A, N8486AR/AQ, N8487A, N8488A | Without Option CFT: EEPROM, handled like an E-series sensor (the N8482A identifies as "Stinger", internal type 6 ✔). With Option CFT: like the 8480 series, and the built-in tables do not apply |

On the 50 MHz reference: 8481D and 8484A need the 11708A 30 dB attenuator during cal; 8485D
and 8487D need the 11708A plus their N adapter for zero and cal; 8483A needs the 75-to-50 ohm
adapter 1250-0597; 8485A/N8485A/E4413A need adapter 08485-60005; 8487A/N8487A/N8488A need
08487-60001; B-type (high-power) sensors calibrate with their attenuator removed. The full
table is in the "Sensors and reference" appendix.

Built-in sensor tables (`MEM:CAT:TABL?` ✔): DEFAULT, HP8481A, HP8482A, HP8483A, HP8481D,
HP8485A, R8486A, Q8486A, R8486D, HP8487A and the user tables CUSTOM_0 to CUSTOM_9. A sensor table
only applies when `SENS:CORR:CSET1:STAT ON`.

Undocumented sensor queries ✔ (all run with the N8482A): `SERV:SENS[1|2]:TNUM?` (test
number), `DIAG:DET:IMAG:HEADER?` (model, serial, place, date, stinger revision) and
`DIAG:DET:IMAG:BLOC?` (installed data blocks) need an EEPROM sensor; `DIAG:DET:TEMP?`
(thermistor), `DIAG:DET:MRES?` (mount resistor, used to identify the sensor type) and
`DIAG:RADC?` (raw ADC) read the measurement board. The
`SERV:SENS:FREQ:MAX?/MIN?` and `:POW:...:MAX?` limit queries need a sensor with the extended
EEPROM block; the N8482A has none and returns -241 ✔.

**Raw sensor EEPROM** ✔: `DIAG[1|2]:DET:EEPR? <addr>,<n>` reads it, but prints each byte as `%d`
with no separator (`DIAG:DET:EEPR? 0,16` returned `60007054110195187024922`), so always read one
byte per query (`<addr>,1`); that runs at about 64 bytes/s. `Tools/dump_sensor_eeprom.py` does
this and checks every block against its directory checksum. The N8482A (MY51520008) dump is
format 6 with seven blocks: types 1 to 5, plus types 18 and 19 (five bytes of `AA` each, not
registered by the firmware, so ignored); data ends at byte 2276 and reads 0xFF to at least 8191.
The dump is that sensor's calibration data: keep it local (`Work/eeprom/`), never publish it.

## Undocumented commands: what is safe

About 150 command codes are in no Agilent manual, most under `DIAGnostic[1|2]` (suffix =
channel). The complete catalogue is in the "Undocumented command catalogue" appendix. Treat
them in three tiers:

| Tier | Commands | Rule |
|---|---|---|
| **Read-only, safe** | `DIAG:PEEK?`, `:PEEK:BLOCK?`, `:PEEK:BYTE?`, `DIAG:VERS:FW?`, `:VERS:BOOT?`, `DIAG:SETT?`, `DIAG:STAT?`, `DIAG:DISP:DUMP?`, `DIAG:DSP? <addr>`, `DIAG:UART:REGS?`, `DIAG:BATT:*?`, `DIAG:DET:IMAG:HEADER?`, `:IMAG:BLOC?`, `DIAG:DET:EEPR? <addr>,1`, `DIAG:DET:IMAG:CF:NPTS?`, `DIAG:DET:TEMP?`, `:MRES?`, `DIAG:RADC?`, `SERV:SENS:TNUM?`, `STAT:DEB:HAP <n>` (only queues an error) | Fine to run on request ✔ |
| **Volatile** (RAM, gone at power cycle or sensor re-read) | `DIAG:DSP <addr>,<val>`, `DIAG:DET:SPE`, `:RCAL`, `:GSW`, `DIAG:RCAL`, `DIAG:SRAT`, `DIAG:SETV`, `DIAG:AVER:*`, `DIAG:RPAD`, `DIAG:DET:IMAG:*:ENTR`/`:DON`, `DIAG:BIST:KEYB:DIS` | Only when asked; they change readings with no error or warning. Re-connect the sensor or power cycle to undo |
| **Persistent or destructive** | `DIAG:POKE`, `:POKE:BYTE`, `DIAG:DET:EEPR <addr>,<byte>` (sensor EEPROM), `DIAG:DET:EEPR:TEST`, `DIAG:CPF`, `DIAG:DOWN:FW:HPIB/RS232/RS422`, `SERV:SNUM`, `SERV:OPT`, `SERV:VERS:PROC`, `SERV:VERS:SYST`, `DIAG:DISP:BRIG:SET?`, `DIAG:DISP:CONT:SET`, `DIAG:MON` | **Never without the author's explicit request and confirmation for that run.** Read and record the original value first |

Specific hazards:

* `DIAG:DET:EEPR <addr>,<byte>` (no question mark) writes the sensor's own calibration store with
  no checks. Dump the whole EEPROM first with `Tools/dump_sensor_eeprom.py` and keep the file.
  Any script that reads the EEPROM must only ever send the `?` form.
* `DIAG:CPF` clears the power-up magic. The next boot is a first power-up: it zeroes BSS,
  empties the serial number, options and both version strings, and resets backlight,
  contrast and the GPIB address (13). The empty processor-board version then selects the old
  self-test menu and disables the fan test. Record those strings first.
* `DIAG:DOWN:FW:*` hands the CPU to the boot ROM loader and never returns. Only a power cycle
  gets out if no image follows. `RS232`/`RS422` return -241 without the serial option.
* `SERV:VERS:PROC` is also a feature switch: below revision "C" the meter shows the old
  self-test menu and drops the fan test. `SERV:VERS:SYST` reprograms the PLD mode ("2" = mode
  1). The bench unit reports C and 2 ✔. Put the original back if either is changed.
* `SERV:SNUM` and the front-panel Edit Serial Number accept any string with no check and no
  undo. Record the original first.
* `DIAG:DET:GSW` always returns -310 on purpose; that error is not a failure.

`STAT:DEB:HAP <n>` makes the parser report internal code n as if a command had failed, which
is the easiest way to test an application's error handling (negative n: generic errors;
122 to 139: the device codes in the "Internals" appendix) ✔.

## Reading memory and firmware

`DIAG:PEEK? <addr>` returns one 16-bit word (decimal address, even only; odd gives -224).
`DIAG:PEEK:BLOCK? <addr>,<n>` returns n words (n up to 256) as raw bytes, high byte first,
plus a newline: read it with `read_raw()`, not `query()`. Address 0 is refused with -222; read
word 0 with `PEEK?` ✔. `Tools/dump_bootrom.py out.bin [start] [end]` does this: 128 KB takes
about 7 minutes, the whole 1 MB flash about an hour ✔.

| Range | Content |
|---|---|
| 0x000000 to 0x01FFFF | Boot ROM A.02.00 (code to 0x00A1AF, rest 0xFF) ✔ |
| 0x020000 to 0x0FFFFF | Main firmware: the `.dload` image (to 0x0F1D5B on E4419B A2.09.01), 0xFF above ✔ |
| 0xE00000 to 0xE3FFFF | Battery-backed RAM: header at 0xE05000, data segment, BSS |
| 0xE40000 to 0xE7FFFF | RAM: pSOS+ regions, heap, stack |
| 0xF00000, 0xF00800 | GPIB controller; 16550 UART (RS-232/422) |

Useful words ✔: `DIAG:PEEK? 14700660` (0xE05074) = GPIB address; `DIAG:PEEK:BLOCK? 14700544,2`
(0xE05000) = `12 34 56 78`, the power-up magic. The battery-backed header layout is in the
"Internals" appendix.

The `.dload` firmware file is `WL` + load address + inclusive end address + data, twice (code
at 0x020000, then initialised data), then `H0`. Load it with `Tools/dload.py`; reading it as
one flat block puts the data segment 10 bytes high. The installed flash on the bench unit
matches `Firmware/E4419-A2-09-01.dload` byte for byte ✔.

## Front-panel service menus

Reached on the E4419B ✔ (hard keys along the bottom, softkeys SK1 to SK4 to the right of the
display):

| Item | Path |
|---|---|
| Service menu | System/Inputs > More > Service (Self Test, Display, Version, Serial Diagnostic) |
| Individual self tests | ... Service > Self Test > Individual: Memory, Lithium Battery, Measure Assemblies, Calibrator / Keyboard, Fan, Display, Serial Interface |
| Version screen | ... Service > Version: model, serial, firmware, boot ROM, processor-board and system versions, DSP and gate-array revision per channel |
| Edit Serial Number | ... Service > Version > Edit Serial Number (writes the serial, no check) |
| Command set / language | System/Inputs > Remote Interface > Command Set |
| Power reference on/off | System/Inputs > More > Power Ref |

The LCD can be captured over GPIB: `bench.grab_display(pm, "screen.png")` reads 208 rows with
`DIAG:DISP:DUMP? <row>` (40 bytes per row, bits least significant first) and returns the meter
to local ✔. Use it to confirm what the panel shows while a user presses keys.

## Boot ROM and firmware download

At power-up the boot ROM scans four front-panel key rows; a key held on one of them selects
HP-IB download, RS-232 download, RS-422 download, or **clear all RAM** (settings and user
tables). Which physical keys sit on which row is not known. **Never hold keys at power-up on
an instrument whose state matters.** ESC or Ctrl-F on the boot console (the 68332 SCI, not the
rear RS-232 UART; pins and baud rate not traced) enters a ROM monitor with memory display/set,
`hmon` download and a gdb stub. Details: `Analysis/BOOTROM.md`.

Firmware updates: Agilent shipped upgrades as a PC download package (E4418-61035 on disc, or
from the web) over GPIB or RS-232/422; the Service Guide gives no step-by-step procedure and
says to download firmware after replacing the processor board. Over GPIB the firmware's own
entry is `DIAG:DOWN:FW:HPIB`, after which the boot ROM accepts `WL`/`GU`/`H0`
records. Nothing in this project has been used to load firmware; do not attempt it without
the user's explicit go-ahead and a verified image.

## Troubleshooting

* **Timeout on a query:** the query failed (rule 2). Device clear, then `SYST:ERR?`.
* **-213 Init ignored:** `READ?`/`MEAS?`/`INIT` while `INIT:CONT ON`. Use `FETC?` or turn
  continuous off.
* **-214 Trigger deadlock:** `READ?`/`MEAS?` with `TRIG:SOUR BUS` or `HOLD`.
* **-230 Data corrupt or stale:** `FETC?` with no new measurement since `*RST` or a settings
  change, or the zero/cal lockout (`CAL:RCAL ON`) is waiting for a zero and cal.
* **-231 Data questionable:** ZERO ERROR (power on the sensor during zero), CAL ERROR (no 1 mW
  on the sensor), Input Overload, PLEASE ZERO, or a negative difference shown in log units.
* **-241 Hardware missing:** the command does not apply to this sensor (CFAC/LOSS1/GAIN1 with
  an EEPROM sensor, SERV:SENS limits without the extended block, channel B on an E4418B
  recorder, RS-232/422 commands without the option).
* **-114 Header suffix out of range:** channel 2 on an E4418B.
* **-221 Settings conflict:** `READ?`/`FETC?` parameters differ from the settings; averaging,
  offsets, limits, relative or duty cycle at 200 rdg/s; `CFAC` with a sensor table selected;
  or `MEM:TABL:*` with no table selected. `MEM:TABL:SEL ""` is
  rejected with -224, so a selection cannot be cleared; it only targets table edits and does
  not correct measurements ✔.
* **-113 Undefined header:** a truncated short form (rule 6) or an E4419B-only command on an
  E4418B (`READD`, `CONF:RAT`, `CONF:DIFF`).
* **Reading drifts or is offset after diagnostics:** a volatile DIAG override is still active.
  Reconnect the sensor or power cycle.
* **"RAM Battery Fault":** the lithium cell BT1 (1420-0338, about 5 years; the Service Guide
  advises 3) holds the serial number, processor-board revision, options, user setups and
  sensor tables. Read and record them before replacing it. After the replacement,
  `SERV:BIST:BMON` re-arms the check word; restore the strings with `SERV:SNUM`,
  `SERV:VERS:PROC` and `SERV:OPT` (with the user's go-ahead).
* **Front panel stays in REMOTE:** GTL or the Local key.

## Known firmware bugs and oddities

* `MEMory:TABLe:LOSS[:MAGNitude]` (undocumented) is broken: values are not converted from
  percent, are stored as 100 - v (16-bit wrap), and read back as 100 + t ✔. Use `MEM:TABL:GAIN`
  with cal factors in percent. Restore a damaged user table with `MEM:CLE:TABL`.
* `*_TRG?` exists in the firmware but its keyword has a leading underscore, so it cannot be
  sent (-101) ✔. Use `*TRG` and then read.
* `READD` is accepted as `READ` on the E4419B ✔.
* `[SENSe]:CORRection:STATe` exists, stores a flag and changes nothing ✔ (returns 0).
* `DIAG:RMTIO:TEST?` always reports a pass; the test is not implemented.
* `DIAG:DET:EEPR? <addr>,<n>` prints each byte as unseparated decimals ✔ (read one byte per
  query). `DIAG:DET:IMAG:CF:CORR? <f>` just echoes f ✔.


---
# Appendices

The documented appendices are condensed from the Agilent manuals; where the manuals contradict
each other the text says "Ambiguous". The last two appendices come from the firmware.

Sources (in `Manuals/`): E4418B/E4419B Programming Guide (E4418-90029, 3rd ed., April 2013) = PG; E4418B User's Guide (E4418-90032, 8th ed., April 2013) = UG; Service Guide E4418-90059 Revision C, Sept 2003 (Agilent) = SG-2003; Service Guide E4418-90059 Revision M, June 2015 (Keysight) = SG-2015; CLIP E4418-90031 (Aug 2007). Only what the manuals state. The UG is the E4418B edition; no E4419B User's Guide was supplied.

Notation: uppercase = short form; `[]` = optional node; `|` = alternatives; `<bool>` = ON|OFF|1|0 (queries return 1/0). Every command also has a query form unless marked "no query" or "query only". DEF/MIN/MAX are accepted wherever a range is listed.

## Appendix: SCPI command reference (documented)

### Numeric suffix rules

| Suffix on | Meaning | Default if omitted |
|---|---|---|
| CONFigure, FETCh, READ, MEASure, CALCulate, DISPlay:WINDow, UNIT | window: 1 = upper, 2 = lower | upper (1) |
| SENSe, CALibration, TRIGger, INITiate, ABORt, SERVice:SENSor | channel: 1 = A, 2 = B | channel A (1) |
| OUTPut:TTL | 1 = upper-window TTL output (Rmt I/O pin 3), 2 = lower (pin 4) | 1 |
| OUTPut:RECorder | recorder output 1 or 2 (SG: recorder A on A4 J23, B on A4 J24). PG does not say REC2 is E4419B-only; presumably so | 1 |
| Source list `(@1)`, `(@2)` | channel A, channel B. Order sets A-B vs B-A and A/B vs B/A | current window setup |

- On the E4418B, the channel-2 forms (SENSe2, CALibration2, TRIGger2, INITiate2, ABORt2) give "Header suffix out of range" (-114 from the firmware; PG gives no number). Window 2 is valid on the E4418B and shows channel A.
- E4419B-only: channel 2, `(@2)`, MATH strings other than "(SENS1)", all DIFFerence and RATio forms, UNIT:POWer:RATio (-113 on E4418B), SERVice:SENSor2.
- `*RST` defaults below come from each command page and PG Table 11-1. SYSTem:PRESet equals *RST except INITiate:CONTinuous (ON after SYST:PRES, OFF after *RST).

### Measurement commands (MEAS / CONF / READ / FETCh / INIT / ABORt)

All take `[<expected_value>[,<resolution>[,<source list>]]]`. Parameters default from the right; `DEF` is a placeholder that leaves the value unchanged.

| Command | Function set | Notes |
|---|---|---|
| CONFigure[1\|2]? | query only | Returns `"<function> <expected_value>,<resolution>,<source list>"`, e.g. `:POW:AC (@1)`, `:POW:AC:DIFF:REL (@2),(@1)`. *RST: `:POW:AC`, +20 dBm, resolution 3, E4418B A/A, E4419B upper A, lower B |
| CONFigure[1\|2][:SCALar][:POWer:AC] | single channel, rel off | no query. Also sets INIT:CONT OFF, TRIG:SOUR IMM, TRIG:DEL:AUTO ON, AVER:COUN:AUTO ON, AVER:STAT ON on the channel(s) in the source list |
| ...[:POWer:AC]:RELative | single, rel on | reference from CALC:REL:AUTO |
| ...:DIFFerence | difference, rel off | E4419B. Expected value ignored. Default A-B unless window already shows a difference |
| ...:DIFFerence:RELative | difference, rel on | E4419B |
| ...:RATio | ratio, rel off | E4419B. Default A/B unless window already shows a ratio |
| ...:RATio:RELative | ratio, rel on | E4419B |
| FETCh[1\|2][:SCALar][:POWer:AC][:RELative \| :DIFFerence[:RELative] \| :RATio[:RELative]]? | sets the window function, recalculates from existing data | query only. Returns NR3, e.g. `-6.98970004E-001`. Waits until data valid, except: -230 if idle with invalid data, or after a reset/SENSe change with no new INIT (common cause: FETC? after *RST). -221 if expected value or resolution differ from the current settings |
| READ[1\|2][...same forms...]? | ABORt + INITiate + FETCh? (difference/ratio: aborts and initiates both channels) | query only. Needs INIT:CONT OFF (else -213) and TRIG:SOUR IMM (BUS or HOLD gives -214). -221 on parameter mismatch |
| MEASure[1\|2][...same forms...]? | ABORt + CONFigure + READ? | query only. Runs in trigger-with-delay mode |
| INITiate[1\|2][:IMMediate] | wait-for-trigger | no query; see TRIGger table |
| ABORt[1\|2] | to idle | no query; see TRIGger table |

Parameter rules: `<expected_value>` (dBm or W, default unit from UNIT:POWer) only matters for E-Series and N8480 sensors without Option CFT. It picks one of the sensor's two ranges and shortens the time to a result when the current range is wrong. `<resolution>` 1 to 4 sets the window resolution (DISPlay table); it does not change GPIB data resolution but does change auto-averaging. For ratio/difference it applies to both channels. Units of results: power functions use UNIT:POWer; relative and ratio functions use UNIT:POWer:RATio.

### CALCulate (suffix = window)

| Command | Parameters / range | *RST | Notes |
|---|---|---|---|
| CALCulate[1\|2]:GAIN[:MAGNitude] | -100.000 to +100.000 dB, DEF 0 | 0 dB | Display offset, applied after MATH. Entering a value sets GAIN:STAT ON. -221 if SENS:SPE is 200 |
| CALC[1\|2]:GAIN:STATe | `<bool>` | OFF | -221 at 200 rdg/s |
| CALC[1\|2]:LIMit:CLEar:AUTO | `<bool>`\|ONCE | ON | ON: fail counter (FCO) zeroed at each INIT[:IMM], INIT:CONT ON, MEAS?, READ?. ONCE: zeroed at first initiation only |
| CALC[1\|2]:LIMit:CLEar[:IMMediate] | none | n/a | Zeroes FCO now; no query |
| CALC[1\|2]:LIMit:FAIL? | returns 1/0 | 0 | 1 when FCO is non-zero |
| CALC[1\|2]:LIMit:FCOunt? | returns count | 0 | +1 per initiated measurement outside limits; equal to limit is a pass; wraps to 0 after 2^16-1 |
| CALC[1\|2]:LIMit:LOWer[:DATA] | -150 to +230 dBm, or -180 to +200 dB | -90 dBm / -90 dB | Fail when result < limit. Units follow the window: single channel W/dBm (rel off) or %/dB (rel on); ratio %/dB; difference W/dBm (rel off) or %/dB (rel on) |
| CALC[1\|2]:LIMit:UPPer[:DATA] | same ranges | +90 dBm / +90 dB | Fail when result > limit |
| CALC[1\|2]:LIMit:STATe | `<bool>` | OFF | -221 at 200 rdg/s. Only one limit set (channel or window) can be on at a time |
| CALC[1\|2]:MATH[:EXPRession] | `"(SENS1)"`; E4419B also `"(SENS2)"`, `"(SENS1-SENS2)"`, `"(SENS2-SENS1)"`, `"(SENS1/SENS2)"`, `"(SENS2/SENS1)"`. Quotes mandatory | E4418B both windows "(SENS1)"; E4419B upper "(SENS1)", lower "(SENS2)" | E4419B: -221 if CALC1 is not SENS1 or CALC2 not SENS2 while 200 rdg/s |
| CALC[1\|2]:MATH[:EXPRession]:CATalog? | query only | n/a | E4418B `"(SENS1)"`; E4419B all six strings |
| CALC[1\|2]:RELative[:MAGNitude]:AUTO | ONCE\|OFF (ON gives -224) | OFF | ONCE stores the current result (after MATH and display offset) as reference and sets REL:STAT ON. Query always OFF. -221 at 200 rdg/s |
| CALC[1\|2]:RELative:STATe | `<bool>` | OFF | -221 at 200 rdg/s |

### CALibration (suffix = channel; all overlapped except RCFactor)

| Command | Parameters / range | *RST | Notes |
|---|---|---|---|
| CALibration[1\|2][:ALL] | none | n/a | Event, no query. Zero then cal; sensor on POWER REF. Errors -231 "CAL ERROR" / "ZERO ERROR" (E4419B adds channel) |
| CALibration[1\|2][:ALL]? | returns 0 = pass, 1 = fail | n/a | Same sequence with a result |
| CAL[1\|2]:AUTO | ONCE\|OFF (ON gives -224) | OFF; query always 0 | Calibrates on a 1 mW reference. Turns POWER REF on, restores its previous state. Zero first. Offset, relative and duty cycle are ignored during cal |
| CAL[1\|2]:ECONtrol:STATe | `<bool>` | disabled | Rear Rmt I/O TTL zero/cal inputs. Ambiguous: Table 11-1 lists "ON" with the comment "TTL zero/cal inputs disabled" |
| CAL[1\|2]:RCALibration | `<bool>` | not affected | Zero/cal lockout. While ON and the sensor is not zeroed and calibrated, FETC?/READ?/MEAS? return -230 "Please zero and Cal" |
| CAL[1\|2]:RCFactor | 1.0 to 150.0 PCT, DEF 100 | 100 % | Reference cal factor for 8480 and N8480 Opt CFT sensors. The most recently set value (this command or an enabled CSET1 table) is used. -241 with E-Series or N8480 (non-CFT) |
| CAL[1\|2]:ZERO:AUTO | ONCE\|OFF (ON gives -224) | OFF; query always 0 | Zero, about 10 s, no power on sensor. Turns POWER REF off, restores it after. -231 "ZERO ERROR" |

### DISPlay (WINDow suffix = window)

| Command | Parameters / range | *RST | Notes |
|---|---|---|---|
| DISPlay:CONTrast | 0 (min) to 1 (max); DEF = factory value | not affected | Power cycle returns factory default |
| DISPlay:ENABle | `<bool>` | ON | Always enabled at power-up |
| DISPlay[:WINDow[1\|2]]:FORMat | DIGital\|ANALog\|DEF | E4418B upper DIG, lower ANAL; E4419B both DIG | Query returns DIG or ANAL |
| DISP[:WIND[1\|2]]:METer:LOWer / :UPPer | -150 to 230 dBm, DEF -70 / 20 | -70 / +20 dBm | Analog scale; units as limits |
| DISP[:WIND[1\|2]]:RESolution | 1 to 4, DEF 3 | 3 | Linear: significant digits; log: 1, 0.1, 0.01, 0.001 dB. Auto-averaging uses the highest resolution of all windows showing that channel |
| DISP[:WIND[1\|2]]:SELect | none; query 1/0 | upper selected | Selects window |
| DISP[:WIND[1\|2]][:STATe] | `<bool>` | both ON | Disabling the only enabled window re-enables the other |

### FORMat

| Command | Parameters | *RST | Notes |
|---|---|---|---|
| FORMat[:READings][:DATA] | ASCii\|REAL | ASCii | Affects FETCh?, READ?, MEASure? only. REAL = definite-length block of IEEE 754 64-bit values |
| FORMat[:READings]:BORDer | NORMal\|SWAPped | NORMal | Used only with REAL |

### MEMory

Tables: 20 sensor calibration tables and 10 frequency dependent offset tables, 80 points each, kept through power-down. None can be created or deleted, only edited and renamed. Save/recall registers: 10.

| Command | Parameters / range | Notes |
|---|---|---|
| MEMory:CATalog[:ALL]? / :CATalog:STATe? / :CATalog:TABLe? | query only | `<bytes used>,<bytes available>{,"name,TABL\|STAT,size"}` |
| MEMory:CLEar[:NAME] | `<string>` table or register name | No query. Clears contents, keeps name. -224 if name does not exist |
| MEMory:CLEar:TABLe | none | No query. Clears the table selected by MEM:TABL:SEL; -221 if none selected |
| MEMory:FREE[:ALL]? / :FREE:STATe? / :FREE:TABLe? | query only | `<bytes_available>,<bytes_in_use>` |
| MEMory:NSTates? | query only | Always 10 |
| MEMory:STATe:CATalog? | query only | Register names in register order |
| MEMory:STATe:DEFine | `<string>,<n>`; name up to 12 chars A-Z a-z 0-9 _ ; n 0 to 9 | -222 number out of range, -224 bad name, -257 name already used. Ambiguous: *SAV/*RCL use 1 to 10 |
| MEMory:TABLe:SELect | `<string>`, up to 12 chars | Must precede any edit. Query returns name |
| MEMory:TABLe:FREQuency | `<f>{,<f>}` 1 kHz to 999.9 GHz, ascending, max 80, default unit Hz | Replaces the list. -108 more than 80, -220 not ascending, -221 no table selected, -222 out of range |
| MEMory:TABLe:FREQuency:POINts? | query only | 0 if empty, NAN (9.91E37) if no table selected |
| MEMory:TABLe:GAIN[:MAGNitude] | `<v>{,<v>}` 1.0 to 150.0, unit PCT (optional) | Cal table: up to 81 values, first = reference cal factor. Offset table: up to 80 values |
| MEMory:TABLe:GAIN[:MAGNitude]:POINts? | query only | Includes the RCF for cal tables; 0 empty, NAN no table |
| MEMory:TABLe:MOVE | `"old","new"` | Rename. -224 invalid name, -256 old not found, -257 new name exists |

Factory tables: DEFAULT (RCF and all CF 100 %, for performance testing), HP8481A, HP8482A (also used for 8482B and 8482H), HP8483A, HP8481D, HP8485A, R8486A, Q8486A, R8486D, HP8487A, empty CUSTOM_0 to CUSTOM_9; offset tables CUSTOM_A to CUSTOM_J (empty). Predefined tables do not apply to N8480 Opt CFT sensors.

### OUTPut

| Command | Parameters / range | *RST | Notes |
|---|---|---|---|
| OUTPut:RECorder[1]\|2:LIMit:LOWer / :UPPer | -150 to +20 dBm, 1 aW to 100 mW, or 0 to 100 % | -150 / +20 dBm | Power that gives 0 V / 1 V |
| OUTPut:RECorder[1]\|2:STATe | `<bool>` | OFF | |
| OUTPut:ROSCillator[:STATe] | `<bool>` | OFF | POWER REF 50 MHz 1 mW output |
| OUTPut:TTL[1\|2]:ACTive | HIGH\|LOW | LOW | Level that signals a window limit fail |
| OUTPut:TTL[1\|2]:FEED | `"CALC1:LIM:LOW"`, `"CALC1:LIM:UPP"`, `"CALC1:LIM:LOW,CALC1:LIM:UPP"` (CALC2 for TTL2) | upper limit fail | Strings must match exactly; quotes mandatory |
| OUTPut:TTL[1\|2]:STATe | `<bool>` | OFF | Enables the TTL output |

### [SENSe] (suffix = channel)

| Command | Parameters / range | *RST | Notes |
|---|---|---|---|
| [SENSe[1]]\|SENSe2:AVERage:COUNt | 1 to 1024, DEF 4 | 4 | Sets COUN:AUTO OFF and AVER:STAT ON. At 200 rdg/s: -221. Max 512 in 437B language |
| ...:AVERage:COUNt:AUTO | `<bool>`\|ONCE (ONCE has no effect) | ON | ON sets AVER:STAT ON |
| ...:AVERage:SDETect | `<bool>` | ON | Step detection: in AUTO filter mode, if the mean of the last 4 values differs from the filter mean by more than 12.5 %, the filter is cleared |
| ...:AVERage[:STATe] | `<bool>` | ON | -221 at 200 rdg/s |
| ...:CORRection:CFACtor\|GAIN1[:INPut][:MAGNitude] | 1 to 150 PCT, DEF 100 | 100 % | Measurement cal factor, 8480 and N8480 Opt CFT, when no cal table is set up; -221 if a sensor cal table is selected |
| ...:CORRection:CSET[1]\|CSET2[:SELect] | `<string>` existing table | not affected | CSET1 = sensor cal table, CSET2 = frequency dependent offset table. -224 invalid, -256 not found, -226 lists not same length (CSET1 needs CF points = freq points + 1; CSET2 needs equal counts). CSET1 with E-Series or N8480 non-CFT: -241 |
| ...:CORRection:CSET[1]\|CSET2:STATe | `<bool>` | not affected | ON with no table selected: -221. CSET1 ON makes calibration use the table RCF |
| ...:CORRection:DCYCle\|GAIN3[:INPut][:MAGNitude] | 0.001 to 99.999 PCT, DEF 1 | 1 % | Sets STAT ON. -221 at 200 rdg/s. With E-Series: -310 "Dty Cyc may impair accuracy with ECP sensor" |
| ...:CORRection:DCYCle\|GAIN3:STATe | `<bool>` | OFF | |
| ...:CORRection:FDOFfset\|GAIN4[:INPut][:MAGNitude]? | query only | not affected | Offset now applied from CSET2 |
| ...:CORRection:GAIN2[:INPut][:MAGNitude] | -100 to +100 dB, DEF 0 | 0 dB | Channel offset; sets GAIN2:STAT ON. Coupled to LOSS2 (Loss = -Gain in dB) |
| ...:CORRection:GAIN2:STATe / :LOSS2:STATe | `<bool>` | OFF | Same state |
| ...:CORRection:LOSS2[:INPut][:MAGNitude] | -100 to +100 dB, DEF 0 | 0 dB | Sets LOSS2:STAT ON |
| ...:FREQuency[:CW\|:FIXed] | 1 kHz to 999.999 GHz, DEF 50 MHz | 50 MHz | Selects the cal factor (CSET1 interpolation, or EEPROM data) and the CSET2 offset |
| ...:LIMit:CLEar:AUTO, :CLEar[:IMMediate], :FAIL?, :FCOunt? | | | As CALC limits, per channel |
| ...:LIMit:LOWer / :UPPer[:DATA] | -150 to +230 dBm, DEF -90 / +90 | -90 / +90 dBm | Channel limits are always dBm |
| ...:LIMit:STATe | `<bool>` | OFF | -221 at 200 rdg/s |
| ...:POWer:AC:RANGe | 0 = lower, 1 = upper | 1 | E-Series and N8480 non-CFT only (else -241). Sets RANG:AUTO OFF |
| ...:POWer:AC:RANGe:AUTO | `<bool>` | ON | |
| ...:SPEed | 20\|40\|200 | 20 | Cycle time 50, 25, 5 ms. 200 needs an E-Series sensor (-241) |
| ...:V2P | ATYPe\|DTYPe | ATYPe | Linearity table; only V8486A and W8486A need DTYP. -241 if no sensor or not an A type |

### STATus

Registers (each has the five subcommands below): STATus:DEVice, :OPERation, :OPERation:CALibrating[:SUMMary], :OPERation:LLFail[:SUMMary], :OPERation:MEASuring[:SUMMary], :OPERation:SENSe[:SUMMary], :OPERation:TRIGger[:SUMMary], :OPERation:ULFail[:SUMMary], :QUEStionable, :QUEStionable:CALibration[:SUMMary], :QUEStionable:POWer[:SUMMary].

| Subcommand | Parameters | Notes |
|---|---|---|
| :CONDition? | query only | not cleared by reading |
| [:EVENt]? | query only | clears the event register |
| :ENABle / :NTRansition / :PTRansition | `<NRf>` or #H/#Q/#B, 0 to 2^16-1 | Bit 15 forced 0 |
| STATus:PRESet | none | OPER and QUES: ENABle 0, PTR all 1, NTR 0. All other registers: ENABle all 1, PTR all 1, NTR 0 |

### TRIGger, INITiate, ABORt (suffix = channel)

| Command | Parameters | *RST | Notes |
|---|---|---|---|
| ABORt[1\|2] | none | n/a | To idle. If INIT:CONT is ON the channel goes straight back to wait-for-trigger |
| INITiate[1\|2]:CONTinuous | `<bool>` | OFF (*RST); ON after SYST:PRES, power-up and on entering local | |
| INITiate[1\|2][:IMMediate] | none | n/a | -213 if not idle or CONT ON |
| TRIGger[1\|2]:DELay:AUTO | `<bool>` | ON | Settling delay from the current filter length. MEAS? and CONF set ON |
| TRIGger[1\|2][:IMMediate] | none | n/a | -211 if not in wait-for-trigger |
| TRIGger[1\|2]:SOURce | BUS\|IMMediate\|HOLD | IMM | BUS: GET, *TRG or TRIG:IMM. HOLD: only TRIG:IMM. MEAS?, READ?, CONF set IMM |

### UNIT (suffix = window)

| Command | Parameters | *RST | Notes |
|---|---|---|---|
| UNIT[1\|2]:POWer | W\|DBM | dBm | Window units. W gives % and DBM gives dB for ratio/relative results |
| UNIT[1\|2]:POWer:RATio | DB\|PCT | dB | E4419B (-113 on E4418B) |

### SYSTem

| Command | Parameters / range | *RST | Notes |
|---|---|---|---|
| SYSTem:COMMunicate:GPIB[:SELF]:ADDRess | 0 to 30, DEF 13 | not affected | Non-volatile |
| SYST:COMM:SERial:CONTrol:DTR / :RTS | ON\|OFF\|IBFull | unaffected | DTR RS232 only (-221 on RS422) |
| SYST:COMM:SERial[:RECeive]:BAUD | 50 to 115200, DEF 9600 | unaffected | Receive and transmit tied |
| SYST:COMM:SERial[:RECeive]:BITs / :PACE / :PARity[:TYPE] / :SBITs | 7\|8; XON\|NONE; EVEN\|ODD\|ZERO\|ONE\|NONE; 1\|2 | unaffected | Tied to TRANsmit |
| SYST:COMM:SERial:TRANsmit:ECHO / :PACE | ON\|OFF; XON\|NONE | unaffected | |
| SYSTem:ERRor? | query only | not affected | FIFO, 30 entries; overflow gives -350; empty returns `+0,"No error"` |
| SYSTem:LANGuage | SCPI\|HP437B (example `SYST:LANG HP437`) | not affected | Non-volatile. Wait 100 ms after changing; meter goes to local; preset recommended. The PG lists no parameter for the E4419B 438A language |
| SYSTem:LOCal / :REMote / :RWLock | none | n/a | Serial interface only; -113 on GPIB |
| SYSTem:PRESet | none | n/a | As *RST but INIT:CONT ON |
| SYSTem:RINTerface | GPIB\|RS232\|RS422 | not affected | Selects remote interface |
| SYSTem:VERSion? | query only | n/a | SCPI version |

### SERVice

| Command | Parameters | Notes |
|---|---|---|
| SERVice:OPTion | `<string>` up to 30 chars | Writes the stored option list. Ambiguous: *OPT? is documented to return only "", "002" or "003" |
| SERVice:SENSor[1\|2]:CDATE? / :CPLace? / :SNUMber? | query only | Cal date, cal place, serial from the EEPROM; -241 otherwise |
| SERVice:SENSor[1\|2]:TYPE? | query only | 8480: "A", "B", "D" or "H"; E-Series/N8480: model from EEPROM; -241 if no sensor |
| SERVice:SNUMber | alphanumeric up to 30 | Writes meter serial number |
| SERVice:VERSion:PROCessor / :SYSTem | `<string>` up to 20 | Writes processor board revision / system version (see the hazards above) |

### IEEE-488.2 common and universal commands

| Command | Notes |
|---|---|
| *CLS | Clears event registers, ESR, status byte, error queue |
| *DDT `<block>`\|`<string>` | Action on GET/*TRG: FETC?, FETC1?, FETC2? (E4419B), *TRG, TRIG1, TRIG2. *RST: *TRG |
| *ESE / *ESE?, *ESR? | Standard event enable / read and clear |
| *IDN? | Must be the last query in a string (-440) |
| *OPC / *OPC? | Sets ESR bit 0 / returns "1" when pending operations finish |
| *OPT? | "" standard, "002", "003" |
| *RCL `<1-10>` / *SAV `<1-10>` | Recall / save state. *RCL of an empty register: -224 |
| *SRE / *SRE?, *STB? | Service request enable; status byte |
| *TRG | Triggers channels in wait-for-trigger; -211 if TRIG:SOUR is not BUS |
| *TST? | Self test, about 30 s; 0 pass, 1 fail. Always 0000 in 437B language |
| *WAI | Waits for pending operations |
| DCL / SDC | Halts pending operations, resets parser, clears output buffer; measurements abort; settings unchanged |
| GTL | Local, front panel enabled, triggering set to free run |
| LLO | Disables the Local key |

## Appendix: Measurement recipes

### Zero and calibrate

Zero when the temperature changes by 5 C, when the sensor is changed, every 24 hours, and before measuring low levels. Allow 30 minutes warm-up. Zero with the sensor disconnected from POWER REF for the zero-set spec to apply.

```
CAL1:ZERO:AUTO ONCE      ; no RF on sensor, about 10 s
*OPC?
CAL1:RCF 98.7PCT         ; 8480 / N8480 Opt CFT only; E-Series sets RCF itself (else -241)
CAL1:AUTO ONCE           ; sensor on POWER REF (1 mW, 50 MHz)
*OPC?
; or both in one: CAL1:ALL?  -> 0 pass, 1 fail
```
Non-blocking variant: `*CLS`, `*ESE 1`, `CAL:AUTO ONCE;*OPC`, then poll the status byte bit 5. Zero/cal failures also set QUES:CAL bits and queue -231. Typical times: zero 10 s (8480), 12 s (E-Series), 20 s (N8480 non-CFT), 8 s (N8480 CFT); cal 6 s, 7 s, 9 s, 6 s.

### Speed, triggering and FORMat REAL

Speed: `SENS:SPE 20|40|200` (50, 25, 5 ms cycle), per channel on the E4419B. 200 rdg/s is for E-Series sensors only and forces, on that channel, AVER:STAT, LIM:STAT, DCYC:STAT, GAIN2:STAT OFF; when either channel is at 200: CALC:GAIN:STAT and CALC:REL:STAT OFF, CALC1:MATH "(SENSe1)", CALC2:MATH "(SENSe2)". Both channels can run 20 or 40 rdg/s together, but not 200 together.

Trigger modes:
- Free run: INIT:CONT ON, TRIG:SOUR IMM. Read with FETC? only. Best speed.
- Trigger immediate (any of): `TRIG:DEL:AUTO OFF; INIT:CONT OFF; TRIG:SOUR IMM; INIT`, or `TRIG:SOUR BUS; INIT:CONT ON; TRIG`, or `TRIG:DEL:AUTO OFF; INIT:CONT OFF; TRIG:SOUR IMM; READ?`.
- Trigger with delay: the same with TRIG:DEL:AUTO ON; MEAS? always uses it. The result waits until the filter is full (settled). Rate is roughly speed / filter length.
- For large power changes the delay may not be enough; take two readings and compare.

Fast reads: `SENS1:SPE 200; TRIG1:SOUR IMM; INIT1:CONT ON; UNIT1:POW W; FORM REAL` (8-byte IEEE 754 blocks; `FORM:BORD SWAP` if needed), then `FETC1?` repeatedly.

### Averaging

`SENS:AVER:COUN:AUTO ON` (default) or `SENS:AVER:COUN <1-1024>`. Auto filter length depends on window resolution and power level (normal speed):

| Power band | Res 1 | Res 2 | Res 3 | Res 4 |
|---|---|---|---|---|
| min sensor power to +10 dB | 1 | 8 | 128 | 128 |
| next 10 dB | 1 | 1 | 16 | 256 |
| next 10 dB | 1 | 1 | 2 | 32 |
| next 10 dB | 1 | 1 | 1 | 16 |
| top band to max sensor power | 1 | 1 | 1 | 8 |

Ambiguous: PG Fig 1-3 reads 8 (not 1) for resolution 1 in the lowest band. Noise multipliers and settling-time tables versus averaging count: Programming Guide chapter 1 and the User's Guide specifications.

### Sensor calibration tables (8480, N8480 Opt CFT)

```
MEM:TABL:SEL "CUSTOM_0"
MEM:TABL:FREQ 50MHZ,1GHZ,2GHZ          ; ascending, max 80, Hz default
MEM:TABL:GAIN 98.0,99.5,97.4,96.1      ; first value = RCF; count = freq count + 1
MEM:TABL:MOVE "CUSTOM_0","MY8481A"     ; optional rename, 12 chars A-Z a-z 0-9 _
SENS1:CORR:CSET1:SEL "MY8481A"         ; checks list lengths (-226)
SENS1:CORR:CSET1:STAT ON               ; -221 if none selected
CAL1:ALL?                              ; RCF taken from table
SENS1:FREQ 500KHZ                      ; CF interpolated linearly
SENS1:CORR:CFAC?                       ; CF in use
```
Outside the table's frequency span the end point is used. To modify, resend the complete lists.

### Frequency dependent offset tables

Same flow with CSET2 (offset count equals frequency count): `SENS1:CORR:CSET2:SEL "Offset1"; SENS1:CORR:CSET2:STAT ON; SENS1:FREQ 500KHZ`, then read; `SENS1:CORR:FDOF?` returns the offset in use.

### Offsets, duty cycle, relative

Channel offset (before window math): `SENS1:CORR:GAIN2 -10` or `SENS1:CORR:LOSS2 10`. Display offset (after math, per window): `CALC1:GAIN -20 DB`. LOSS1 and GAIN1 are reserved for cal factors.

Duty cycle (pulse power = average / duty cycle, rectangular pulses only): `SENS1:CORR:DCYC 16PCT; SENS1:CORR:DCYC:STAT ON`. Not recommended with E-Series sensors (-310 warning).

Relative: `CALC1:REL:AUTO ONCE` captures the reference and enables REL; `CALC1:REL:STAT OFF|ON` toggles.

### Difference and ratio (E4419B)

```
ABOR1
ABOR2
CONF2:POW:AC:DIFF DEF,DEF,(@1),(@2)    ; A-B on lower window
INIT1:IMM
INIT2:IMM
FETC2:POW:AC:DIFF?
FETC2:POW:AC:DIFF? DEF,DEF,(@2),(@1)   ; B-A from the same data
```
Ratio: `CONF2:POW:AC:RAT DEF,DEF,(@1),(@2)`, then `READ2:POW:AC:RAT?` or INIT both and `FETC2:POW:AC:RAT?`. A negative difference shown in log units gives -231 "Upper/Lower window log error".

### Limits and SRQ

Channel limits (dBm): `SENS:LIM:UPP 10; SENS:LIM:LOW 4; SENS:LIM:STAT ON`, then `SENS:LIM:FAIL?`, `SENS:LIM:FCO?`. Window limits with TTL output: `CALC1:LIM:LOW -30; CALC1:LIM:UPP -10; CALC1:LIM:STAT ON; OUTP:TTL1:FEED "CALC1:LIM:LOW,CALC1:LIM:UPP"; OUTP:TTL1:ACT HIGH; OUTP:TTL1:STAT ON`.

SRQ on over-limit: `*CLS; SYST:PRES; SENS:LIM:UPP 2DBM; SENS:LIM:STAT ON; STAT:OPER:PTR 4096; STAT:OPER:ENAB 4096; *SRE 128`; on SRQ read `STAT:OPER?` then `STAT:OPER:ULF?`. SRQ on sensor connect/disconnect: `STAT:DEV:ENAB 2; STAT:DEV:NTR 2; STAT:DEV:PTR 2; *SRE 2`.

### Save/recall

`*SAV 1..10`, `*RCL 1..10`. Not stored: error list, GPIB address, language, sensor table data, zero and cal data. Name registers with MEM:STAT:DEF.

## Appendix: Sensors and reference

| Item | Manual text |
|---|---|
| Families | 8480 Series, E-Series, N8480 Series (with or without Option CFT). 100 kHz to 110 GHz, -70 dBm to +44 dBm, sensor dependent. E9320 sensors are not mentioned |
| Single-sensor dynamic range | 90 dB E-Series, 50 dB 8480, 55 dB N8480 non-CFT, 50 dB N8480 CFT |
| E-Series and N8480 non-CFT | Cal table in sensor EEPROM, downloaded automatically; RCF and CSET1 commands give -241; two ranges. On connect: "Reading Sensor ChA"; failure gives -310 and a warning |
| 8480 and N8480 Opt CFT | Need RCF and a cal factor per frequency (CFAC or CSET1 table) |
| Linearity | A or D type chosen automatically for most 8480; V8486A and W8486A need `SENS:V2P DTYP` |

Connecting to the 50 MHz reference for calibration (UG Table 2-1):

| Sensors | Requirement |
|---|---|
| 8481A, 8481H, 8482A, 8482H, N8481A, N8481H, N8482A, N8482H, E4412A, E930xA, E930xH, E9304 H18/H19 | Direct to POWER REF |
| 8481D, 8484A | 11708A 30 dB reference attenuator during cal; remove for measurement |
| 8483A | 75 ohm (f) to 50 ohm (m) N adapter 1250-0597; remove after |
| R/Q/V/W8486A, R/Q8486D, N8486AR/AQ | Use the waveguide sensor's N-type connector |
| 8481B, N8481B, 8482B, N8482B, E930xB | Remove the attenuator for cal, refit for measurement |
| 8485A, N8485A, E4413A, E9300A H24/H25 | APC 3.5 (f) to N (m) adapter 08485-60005 |
| 8485D | 11708A plus 08485-60005 during zero and cal |
| 8487A, N8487A, N8488A | APC 2.4 (f) to N (m) adapter 08487-60001 |
| 8487D | 11708A plus 08487-60001 during zero and cal |

1 mW power reference: 1.00 mW (0.0 dBm), 50 MHz nominal, type N (f) 50 ohm. Factory set to +/-0.4 % traceable to NPL. Two-year accuracy: +/-0.9 % (0 to 55 C), +/-0.6 % (25 +/-10 C), +/-0.5 % (23 +/-3 C). SWR 1.06 max (1.08 for Option 003 rear output). Frequency 50.0 +/-0.5 MHz.

## Appendix: Status system

Status Byte: bit 1 (2) Device summary; 2 (4) error queue not empty; 3 (8) Questionable summary; 4 (16) MAV; 5 (32) Standard Event summary; 6 (64) RQS/MSS; 7 (128) Operation summary.

Standard Event: 0 (1) Operation Complete; 2 (4) Query error; 3 (8) Device error; 4 (16) Execution error; 5 (32) Command error; 7 (128) Power On.

Questionable: 3 (8) POWer summary; 8 (256) CALibration summary; 9 (512) power-on self test failed.
- QUES:POWer: 1 (2) channel A power; 2 (4) channel B power; 3 (8) upper window; 4 (16) lower window; 5 (32) channel A please zero; 6 (64) channel B please zero.
- QUES:CALibration: 1 (2) channel A; 2 (4) channel B. Set by ZERO ERROR / CAL ERROR; cleared when one succeeds.

Operation: 0 (1) CALibrating; 4 (16) MEASuring; 5 (32) waiting for TRIGger; 10 (1024) SENSe (reading an EEPROM); 11 (2048) lower limit fail; 12 (4096) upper limit fail.
- OPER:CALibrating, :MEASuring, :SENSe, :TRIGger: 1 (2) channel A, 2 (4) channel B.
- OPER:LLFail and :ULFail: 1 (2) channel A, 2 (4) channel B, 3 (8) upper window, 4 (16) lower window.

Device: 1 (2) channel A sensor connected; 2 (4) channel B connected; 3 (8) channel A sensor error; 4 (16) channel B sensor error; 5 (32) channel A sensor on rear panel; 6 (64) channel B rear; 14 (16384) front-panel key pressed (event only). PTR = event on connect, NTR = event on disconnect.

## Appendix: Error messages

| Code | Text | Cause (manual) |
|---|---|---|
| -101 | Invalid character | e.g. `LIM:LOW O#` |
| -102 | Syntax error | |
| -103 | Invalid separator | e.g. `OUTP:ROSC,1` |
| -108 | Parameter not allowed | Extra parameter; more than 80 freqs or 81/80 table values |
| -109 | Missing parameter | |
| -112 | Program mnemonic too long | Header over 12 characters |
| -113 | Undefined header | Bad or unsupported command; SYST:LOC/REM/RWL on GPIB; UNIT:POW:RAT on E4418B |
| -131 | Invalid suffix | `SENS:FREQ 200KZ` |
| -148 | Character data not allowed | `MEM:CLE CUSTOM_1` (needs quotes) |
| -158 | String data not allowed | `LIM:STAT 'ON'` |
| -211 | Trigger ignored | GET/*TRG/TRIG:IMM when not waiting for trigger |
| -213 | Init ignored | INIT while initiated or INIT:CONT ON; READ? with INIT:CONT ON |
| -214 | Trigger deadlock | READ?/MEAS? with TRIG:SOUR BUS or HOLD |
| -220 | Parameter error;Frequency list must be in ascending order | MEM:TABL:FREQ |
| -221 | Settings conflict | READ?/FETC? parameters differ from settings; averaging, duty cycle, limits, offsets, relative or math at 200 rdg/s; CSET STAT ON with no table; table writes with none selected; CFAC with a cal table selected |
| -222 | Data out of range | e.g. `SENS:FREQ 2KHZ`; table values |
| -224 | Illegal parameter value | Invalid choice, ON for CAL:AUTO / ZERO:AUTO / REL:AUTO, bad speed, bad names, *RCL of empty register |
| -226 | Lists not same length | CSET table lists mismatch |
| -230 | Data corrupt or stale | FETC? after reset or state change with no new measurement; "Please zero and calibrate" with CAL:RCAL ON |
| -231 | Data questionable | CAL ERROR (no 1 mW applied), ZERO ERROR (power applied during zero), Input Overload, PLEASE ZERO, Upper/Lower window log error |
| -241 | Hardware missing | No sensor, or command needs a different sensor type; 200 rdg/s without E-Series; RCF/CSET1 with E-Series; V2P without A-type |
| -256 | File name not found | MEM:TABL:MOVE, CSET:SEL |
| -257 | File name error | Name already used |
| -310 | System error | Duty cycle with an E-Series sensor; sensor EEPROM read failures ("Read Failed - critical", "optional data block(s) not found", "unknown EEPROM table format", "<block> data not found"); Option 001 battery charger fault; sensors on both front and rear inputs |
| -330 | Self-test Failed | Measurement Channel Fault, RAM Battery Fault, Calibrator Fault, ROM Check Failed, RAM Check Failed, Display Assy. Fault, Confidence Check Fault, Serial Interface Fault, Option 001 battery |
| -350 | Queue overflow | More than 30 errors |
| -361 / -362 / -363 | Parity / framing error / input buffer overrun | Serial interface |
| -410 / -420 / -430 / -440 | Query interrupted / unterminated / deadlocked / unterminated after indefinite response | -440: *IDN? not last in string |

Front-panel messages: "No Sensor", "Reading Sensor ChA", "Please Zero + Cal ChA", "Linearity Override May be Required", "Power-up H/W Err" on a power-on self-test failure; window flags "Undr Lmt", "Over Lmt", "Rel", "Ofs", "Rng Hld", "Dty Cyc".

## Appendix: HP 437B / 438A languages

- SCPI (factory) plus one emulation per model: E4418B emulates the HP 437B, E4419B the HP 438A. Selection is non-volatile. Front panel: System/Inputs, Remote Interface, Command Set.
- Remote: `SYST:LANG HP437B` (example `SYST:LANG HP437`); return with `SYST:LANG SCPI` (accepted in emulation mode). Wait 100 ms after switching; preset recommended. The PG documents no keyword for 438A mode; the firmware accepts `HP438A` and `HP438`. HP 436A emulation (E4418B) is not in any manual; see the catalogue appendix.
- 437B commands act only on the upper window. Filter length is limited to 512. *TST? always returns 0000. For command details the guides refer to the HP 437B Operating Manual and the HP 438A Operating and Service Manual. The emulations add `SPD 20|40`, `SYST:LANG SCPI` and `TK?` to the original command sets.

## Appendix: Service, performance tests and adjustments

### Self tests

| Mode | Tests | Notes |
|---|---|---|
| Power-on (about 10 s) | RAM Battery, Calibrator, Measurement Assembly, Fan, Serial Interface, Option 001 Battery | Failure: "Power-up H/W Err", errors queued, QUES bit 9 |
| Instrument Self Test (Service > Self Test) | ROM checksum, RAM, RAM Battery, Display Assembly, Calibrator, Measurement Assembly, Fan, Serial Interface | |
| *TST? (about 30 s) | ROM checksum, RAM, RAM Battery, Display Assembly, Calibrator, Measurement Assembly | 0 = pass, 1 = fail |
| Confidence Check | Sensor on POWER REF (with the adapters above); passes if the reference reads within spec | -330 Confidence Check Fault |
| Individual | Memory, Lithium Battery, Measurement Assembly, Calibrator, Keyboard, Fan, Display (Assy, RAM, Bitmaps), Serial Interface (UART Config, Local Loop Back, RS232 and RS422 Loop Back) | Keyboard and bitmap tests need the operator; loop-back tests need a connector: RS232 Tx(3)-Rx(2), RTS(7)-CTS(8), DTR(4)-DSR(6) |

### Performance verification

Conditions: 30 min warm-up, ambient 0 to 55 C; recommended every two years. E4419B: repeat per channel. Equipment: 3458A DMM; Datron 4000A or Fluke 5720A DC calibrator; 11683A range calibrator (Option H01 for specification-level testing); 53132A counter; 432A power meter with 478A Opt H75/H76 or 8478B Opt H01 thermistor mount; an E-Series sensor; 11708A 30 dB attenuator; 11730A or E9288A cable.

| Test | Method | Limits |
|---|---|---|
| Zero Test | 11683A on 3 uW range, STANDBY; W units; manual filter 512; zero; wait 30 s | -76.40 nW to +76.40 nW |
| Instrument Accuracy, Procedure 1 | 11683A: zero on 3 uW STANDBY, cal on 1 mW CALIBRATE, then step ranges | 1 mW 0.995 to 1.005; full table in the Service Guide |
| Instrument Accuracy, Procedure 2 (specification) | 11683A Opt H01 driven by the DC calibrator (cal at 144.93 mV), resolution 4 | +/-0.5 % or +/-0.02 dB per range; table in the Service Guide |
| Power Reference Level | 432A + 478A + 3458A; Pmeas = (2 Vcomp (V1 - V0) + V0^2 - V1^2) / (4 R CalFactor) | SG-2015: 0.991 to 1.009 mW. SG-2003: 0.999 to 1.001 mW |
| E-Series Sensor Interface Test | Connect: "No Sensor", then "Reading Sensor ChA", then a reading | Pass/fail |
| E-Series Sensor Functional Test | Zero, cal, POWER REF on through the 11708A: both ranges -30 dBm +/-1 dB; no pad: upper range 0 dBm +/-1 dB | Pass/fail |
| Output SWR (SG-2015) | 432A bridge at 200 and 100 ohm | 1.06 max front, 1.08 max rear |

### Adjustments

| Adjustment | Equipment | Steps |
|---|---|---|
| Power reference frequency | 53132A | If not 50.0 +/-0.5 MHz, adjust A2L9; recheck level afterwards |
| Power reference level | 432A, 478A, 3458A | Measure bridge R, V0, Vcomp; compute target V1 for 1 mW from the Service Guide equation; adjust A2R90. Goal 1 mW +/-0.4 % |
| Display brightness and contrast | none | Service > Display > Set Contrast, then Set Brightness |

### Firmware, batteries, fan, assemblies

- Firmware: upgradable from a PC over GPIB or RS232/422 (package E4418-61035). Download firmware after replacing the processor board. CLIP: processor CCA E4418-60028 carries U7 E4418-80019 and U8 E4418-80020 (4 Mbit flash) and U14 E4418-80022 (EPLD); measurement CCA E4418-60003 carries U13 E4418-80023 (512 kbit DSP flash).
- RAM battery BT1 1420-0338 (3 V lithium), about 5 years; the Service Guide advises replacement every three years. Below 3 V the meter loses the serial number, processor card revision letter, options, user setups and sensor tables.
- Option 001 battery E9287A (NiMH). Fan A7 E4418-61004. Line fuse 2110-0957, F3.15AH 250 V.
- Assemblies: A1 power supply, A2 processor (with the 50 MHz calibrator), A3 front panel, A4 comms (GPIB, UART, TTL, recorder), A5 daughter board, A6 measurement assembly (E4418-60007, one per channel), A7 fan.
- Service Guide chapter 6 troubleshooting covers only the Rmt I/O TTL lines and the serial port, and decides between A2 and A4.

## Appendix: Specifications

| Item | Value |
|---|---|
| Instrumentation accuracy | Absolute +/-0.02 dB or +/-0.5 %; relative +/-0.04 dB or +/-1.0 % (add sensor linearity) |
| Measurement speed (GPIB) | Normal 20, x2 40, Fast 200 rdg/s (E-Series only); fastest with binary output in free run |
| Recorder output | 0 to 1 V, 1 kohm, BNC |
| Rmt I/O | RJ-45: pin 2 ground, 3 upper-window TTL out, 4 lower-window TTL out, 5 TTL in 1, 6 TTL in 2, 7 and 8 ground |
| GPIB | IEEE 488.2; address 0 to 30, factory 13 |
| RS-232/422 | 9-pin male D, DTE. RS232: 2 Rx, 3 Tx, 4 DTR, 5 GND, 6 DSR, 7 RTS, 8 CTS. Default 9600 baud |
| Options | 001 battery; 002 rear sensor inputs, POWER REF front; 003 rear sensor inputs and rear POWER REF |
| Calibration interval | Two years |

## Appendix: Undocumented command catalogue

From the firmware (command code in hex, E4418B handler addresses in `Analysis/COMMANDS.md`).
✔ = run on the E4419B. All `DIAGnostic` commands take the suffix `[1|2]` for the channel
(default 1; the E4418B has only 1). Parameters: `<num>` accepts MIN/MAX/DEF, `<bool>` is
ON|OFF|1|0. Addresses are decimal on the bus.

### SERVice and STATus extras

| Command | Code | Behaviour |
|---|---|---|
| `SERV:BIST:BMONitor` | 00A | Writes 0x12345678 to the RAM battery check word (0xE05070); clears "RAM Battery Fault" after a battery change |
| `SERV:BIST:CALibrator <x>` | 014 | Accepts a parameter, does nothing |
| `SERV:SENSor[1\|2]:TNUMber?` | 011 | 16-character test number from the E-series EEPROM ✔ |
| `SERV:SENSor[1\|2]:FREQuency:MAXimum?` / `:MINimum?` | 015, 016 | Frequency limits from the extended EEPROM block; -241 without it ✔ |
| `SERV:SENSor[1\|2]:POWer:AVERage:MAXimum?`, `:PEAK:MAXimum?`, `:USABle:MAXimum?`, `:USABle:MINimum?` | 017 to 01A | Power limits, same conditions |
| `STATus:DEBug:HAPpenning <n>` (short `STAT:DEB:HAP`) | 077 | Reports internal code n as a command failure ✔ |
| `STATus:DEBug:ENBALL` | 078 | Sets every status enable mask to 0x7FFF |
| `[SENSe[1]]\|SENSe2:CORRection:STATe <bool>` / `?` | 146 | Stores a per-channel flag nothing reads; query 0 ✔ |
| `[SENSe]:CORRection:LOSS1 <pct>` / `?` | 14D | Only mentioned in a Programming Guide note. LOSS1 = 100 - CF, range -50 to 99 (GAIN1 is the documented alias of CFACtor). Manual-cal-factor sensors only ✔ |
| `MEMory:TABLe:LOSS[:MAGNitude] <v>{,<v>}` / `?` | 170 | Broken (see "Known firmware bugs") ✔ |
| `TCONF <x>` | 0B1 | Does nothing |
| `FORMat:SREGister` | 0BB | Reads FORM:DATA, no effect |
| `RTEST<n>:ONE?\|TWO?\|FOUR?\|FIVE?\|TEST?` | 12F | `FETCh?` handler with forced channel 1, 2, 4, 5 or n (range-check hook) |
| `READD` (E4419B) | as READ | Alias of `READ` ✔ |
| `*_TRG?` | 086 | Trigger plus read; unreachable (-101) ✔ |
| `SYST:LANG HP436A\|HP437\|HP438` | | HP436A: E4418B-only 436A emulation; HP437/HP438 are short aliases |

### DIAGnostic: memory, versions, monitor, download

| Command | Code | Behaviour |
|---|---|---|
| `DIAG:POKE <addr>,<word>` | 12A | Write 16-bit word (odd address -224). **Destructive** |
| `DIAG:PEEK? <addr>` | 12B | Read 16-bit word ✔ |
| `DIAG:PEEK:BLOCK? <addr>,<n>` | 12C | n ≤ 256 words, binary, high byte first; address 0 gives -222 ✔ |
| `DIAG:PEEK:BYTE? <addr>` | 12D | Read a byte |
| `DIAG:POKE:BYTE <addr>,<byte>` | 12E | Write a byte. **Destructive** |
| `DIAG:CPF` | 0BF | Clears the power-up magic. Next boot is a first power-up: BSS zeroed, serial/options/version strings emptied, backlight 70, contrast 33, GPIB address 13. **Destructive** |
| `DIAG:BIST:BMONitor` | 110 | Same as `SERV:BIST:BMON` |
| `DIAG:DOWNload:FW:HPIB\|RS232\|RS422` | 0E7 to 0E9 | Enter the boot ROM loader; never returns. **Destructive** |
| `DIAG:MONitor` | 0F9 | `TRAP #0` into the boot ROM monitor (console only) |
| `DIAG:PSOS:PS\|SREP\|MREP\|MHREP\|SEMREP` | 103 to 107 | pSOS+ reports on the debug console; nothing returned over GPIB |
| `DIAG:VERSion:FW?` | 11A | Build date and time, e.g. `May 12 2009 10:17:44` ✔ |
| `DIAG:VERSion:BOOT?` | 11B | Boot ROM version, `A.02.00` ✔ |

### DIAGnostic: sensor EEPROM and calibration image

| Command | Code | Behaviour |
|---|---|---|
| `DIAG:DETector:EEPRom? <addr>,<n>` | 0DA | Read n (1 to 16) EEPROM bytes. Each byte is printed as `%d` with no separator, so a multi-byte reply cannot be split; read one byte per query (`<addr>,1`, about 64 bytes/s) ✔ |
| `DIAG:DETector:EEPRom <addr>,<byte>` | 0DA | **Writes the sensor EEPROM**, no checks |
| `DIAG:DETector:EEPRom:TEST` / `?` | 0C5 | Write test over two scratch windows (saves and restores; do not interrupt); E-series only |
| `DIAG:DETector:EEPRom:READ` | 0DF | Re-reads the sensor EEPROM |
| `DIAG:DETector:READEEPRom?` | 0E0 | Re-parses the held image, returns parser status |
| `DIAG:DETector:IMAGe:HEADER?` | 0E1 | Model, serial, place, date, stinger rev ✔ (serial prints twice; date is a raw value) |
| `DIAG:DETector:IMAGe:BLOCks?` | 0E2 | Installed blocks, one "Block type n, format n" each ✔ |
| `DIAG:DET:IMAG:V2P:POINter\|ENTRy\|DONe` | 0C6 to 0C8 | Linearity table in RAM (rows of 65 longwords). Volatile |
| `DIAG:DET:IMAG:TC:...`, `:TCCoeffs:...` | 0CC, 0CD, 0D1, 0D3 | Temperature-compensation table and coefficients. Volatile |
| `DIAG:DET:IMAG:ZTC:...`, `:TC:MEAS?`, `:TC:CAL:UPP?\|LOW?` | 0C9 to 0CB, 0CE to 0D0 | Zero and temp-comp channel readings |
| `DIAG:TC:UPDate?` | 0D2 | Run the temp-comp update; 1, or 0 without an E-series sensor |
| `DIAG:DET:IMAG:CF:FREQ <f>` / `?`, `:CF:CORRect? <f>`, `:CF:NPTS?`, `:CF:MAKEDUMMY` | 0DB | Cal-factor lookup (channel A only). `:NPTS?` returns the point count (22 on the N8482A) ✔; `:CORR?` just echoes f ✔ |
| `DIAG:EEPROM:DUMMY:READALL?` etc. | 0C0 to 0C3 | Built-in dummy EEPROM image and stubs |

### DIAGnostic: measurement board and DSP

| Command | Code | Behaviour |
|---|---|---|
| `DIAG:DSP? <addr>` | 0E5 | Read ADSP-2101 data-memory word (bus 0xF002) ✔ (`14366` = 0x381E) |
| `DIAG:DSP <addr>,<value>` | 0E5 | Write DSP data memory. Volatile |
| `DIAG:RADC?` | 102 | Raw 4-byte ADC reading ✔ |
| `DIAG:DET:TEMPerature?` | 0D8 | Sensor thermistor ✔ |
| `DIAG:DET:MRESistor?` | 0D9 | Mount resistor (sensor-type ID) ✔ |
| `DIAG:DET:GSWitch <1\|2>` | 0D5 | Force detector gain path; always returns -310 by design |
| `DIAG:DET:SPEed <bool>` | 0D6 | Board speed bit (config bit 0) |
| `DIAG:RCALibrate <bool>` | 0F7 | RCAL path (bit 1) |
| `DIAG:DET:RCALibrate <bool>` | 0D7 | Reference calibrator (bit 2) |
| `DIAG:DET:THIRd` | 0D4 | E-series with flag: DSP 0x3815 = 0x105 for one cycle |
| `DIAG:SRATe <bool>` / `?` | 0FA | One of two sample periods; recomputes filter length |
| `DIAG:SETVar <name>,<value>` / `DIAG:SETVar? <name>` | 0E6 | MEAS, G_SENSOR, CAL_OFFSET, RAW_ADC, SENSOR_RANGE, TC_VALUE, ZERO_LOWER, ZERO_UPPER, CAL_CHAR, VTHerm, RCAL_DELAY, FC_VALUE, TC_THRESHOLD, POSTAVE_MEAS, PREAVE_MEAS. Volatile |
| `DIAG:AVERage:ZERO\|RCAL\|CAL:LOWer\|UPPer <n>` | 0F1 to 0F6 | Filter length for zero, ref-cal and cal (0 = default) |
| `DIAG:RPAD <dB>` / `?` | 0EB | Reference-pad attenuation |
| `DIAG:SDET...`, `DIAG:ZDT...`, `DIAG:CAL:CHECk`, `:ZERO:CHECk`, `:ZERO:DRIFt:CHECk` | 0EC to 0F0 | Stored test limits |

### DIAGnostic: status, display, keyboard, self tests, interfaces

| Command | Code | Behaviour |
|---|---|---|
| `DIAG:SETTings?` | 0E3 | Text block of channel settings ✔ |
| `DIAG:STATes?` | 0E4 | Mode, trigger state, sensor and position ✔ |
| `DIAG:DISPlay:DUMP? <row>` | 0FB | 40 bytes of LCD memory for a 320-pixel row ✔ |
| `DIAG:DISP:BRIGhtness:UP\|DOWN`, `:CONTrast:UP\|DOWN` | 0FC, 0FD, 0FF, 100 | Step backlight or contrast |
| `DIAG:DISP:BRIG:SET?`, `DIAG:DISP:CONT:SET` | 0FE, 101 | Calibrate/save to battery-backed RAM. Persistent |
| `DIAG:DISP:DBUFF <bool>`, `:BUFF <1\|2>`, `:RBUFferring` | 108 to 10A | Display buffer control |
| `DIAG:BIST:DISPlay:TEST <n>` | 115 | Display test pattern n |
| `DIAG:BIST:KEYBoard:DISable\|ENABle` | 116, 117 | Lock or unlock the keys |
| `DIAG:BIST:KEYBoard:KEY?` | 119 | Last key code (0 ZERO_CAL ... 19 SPLIT_WINDOW) |
| `DIAG:BATTery:FITted?\|ABSent?\|CAPacity?\|CHARge?\|TIME?` | 10B to 10F | Optional battery pack ✔ (0/1/0/0/65535 with none) |
| `DIAG:BIST:MEAS?` | 111 | Measurement-board self test |
| `DIAG:BIST:ANALog? <point>` | 112 | DUMMY1, DUMMY2, THERMA, LED_I_MON, DUMMY3, REF_TP2, REF_TP1, LCD_CONT1 |
| `DIAG:RECorder[1\|2]:TEST?`, `DIAG:TTL:TEST?` | 113, 114 | Output tests |
| `DIAG:RS232:TEST?`, `DIAG:RS422:TEST?` | 122, 123 | Serial loop-back tests; run only while internal variable 0xAE is 0 (else -221); RS-422 needs the interface fitted |
| `DIAG:UART:REGS?` | 124 | 16550 register dump ✔ |
| `DIAG:RMTIO:TEST?` | 127 | Always "passed"; not implemented |
| `DIAG:PLD:MODE` | 128 | Rewrites the PLD mode register from the stored mode |
| `DIAG:MONGO:PORT <string>` | 129 | Sensor-port description string |
| `DIAG:HADDRess <n>` | | Alias of `SYST:COMM:GPIB:ADDR` |
| `DIAG:RECorder[1\|2]:CHANnel` | 029 | Which channel drives the recorder output |
| `DIAG:UNIT:SCPIPOWER?\|SCPIRATIO?` | 0BC, 0BD | Internal unit variables |

### HP 436A emulation (E4418B, `SYST:LANG HP436A`)

Each 436A code is translated into SCPI: `+` cal factor off (`GAIN1 100`), `-` cal factor on,
`1`..`5` manual range, `9` autorange, `A` watts, `B` dB relative, `C` dB reference (capture),
`D` dBm, `H` hold, `I` trigger immediate, `R` free run, `T` trigger with delay, `V` = `R`,
`Z` zero. Extras: `FR <value> KZ|MZ|GZ` (frequency), `X1`/`X2` (speed 20/40), and
`SYST:LANG SCPI` or `SYST:LANG?` to leave the mode. The front panel gains an "HP436A Modes"
menu (Zero Mode, Filter Mode). Not exercised on hardware.

## Appendix: Internals

### Device error codes

Handlers return small internal codes. Negative ones map through a 110-entry table; positive
ones (device-specific, `STAT:DEB:HAP 122` to `139`) through this table:

| Code | SCPI | Meaning | Code | SCPI | Meaning |
|---|---|---|---|---|---|
| 0x7A (122) | -211 | Trigger ignored ✔ | 0x82 (130) | -256 | File name not found ✔ |
| 0x7B (123) | -213 | Init ignored ✔ | 0x83 | -257 | File name error |
| 0x7C (124) | -214 | Trigger deadlock ✔ | 0x84 | -226 | Lists not same length |
| 0x7D (125) | -114 | Header suffix out of range ✔ | 0x85 | -330 | Self-test failed |
| 0x7E (126) | -221 | Settings conflict ✔ | 0x86 (134) | -231 | Data questionable ✔ |
| 0x7F (127) | -230 | Data corrupt or stale ✔ | 0x89 | -361 | Parity error |
| 0x80 (128) | -241 | Hardware missing ✔ | 0x8A | -362 | Framing error |
| 0x81 (129) | -220 | Parameter error ✔ | 0x8B | -363 | Input buffer overrun |

0x87 and 0x88 change a status bit and queue nothing. Negative examples ✔: -11 gives -222,
-57 gives -224, -8 gives -200.

### Battery-backed header (RAM 0xE05000; survives power-off and firmware loads)

| Address | Content | Written by |
|---|---|---|
| 0xE05000 | Power-up magic 0x12345678 ✔ | `DIAG:CPF` clears |
| 0xE05004 | System version string | `SERV:VERS:SYST` |
| 0xE05018 | Processor-board version string | `SERV:VERS:PROC` |
| 0xE0502C | Serial number string | `SERV:SNUM`, Edit Serial Number |
| 0xE0504A | Options string | `SERV:OPT` |
| 0xE05068 | Backlight drive (default 70) | `DIAG:DISP:BRIG:SET?` |
| 0xE0506C | Contrast (default 33) | `DIAG:DISP:CONT:SET` |
| 0xE05070 | RAM battery check word | `SERV:BIST:BMON` |
| 0xE05074 | GPIB address (default 13) ✔ | `SYST:COMM:GPIB:ADDR` |

### Hardware

* Processor board: MC68332 (CPU32) running pSOS+; two 4 Mbit flash chips (one per byte lane)
  hold the boot ROM (bottom 128 KB) and the main firmware; SED1330 LCD controller; 16550 UART
  for the RS-232/422 option.
* Measurement assembly (A6 E4418-60007, one per channel; board E4418-60003): ADSP-2101 DSP
  booted from its own 64 KB flash (E4418-80023, DSP firmware A.01.11), and a Xilinx XC3042A
  gate array (1821-1672) that loads its bitstream from the top 3,856 bytes of the same flash
  (master-parallel-down). The main CPU talks to the DSP over a serial bus: bits 15 to 11 of
  each 16-bit command word are the opcode, bit 10 the channel. Configuration opcode 0x2800
  carries four bits: speed, RCAL path, reference calibrator, gain path.
* Sensor EEPROM (E-series, N8480): byte 0 format (1, 2, 3, 6, 7 accepted), byte 4 block count,
  then 7-byte directory entries `{u16 addr, u8 type, u8 format, u16 length, u8 checksum}`; each
  block's 8-bit additive sum must equal its checksum. Block types: 1 Linearity, 2 Temp-Comp,
  3 Cal Factor, 4 Header, 5 Misc (required), 6 Basic Params, 8 Auto-Filter (optional); other
  types are not registered and are skipped. Cal Factor block: 9-byte header with the point count
  at byte 5, then 8-byte records of u32 frequency in kHz and two u16 factors (0x4000 = 100 %).
  The N8482A carries types 1 to 5 plus 18 and 19 (five bytes of 0xAA each); its 22 cal-factor
  points run 100 kHz to 6 GHz ✔.
* Self-test menu choice: processor-board version "C" or later gives Memory / Lithium Battery /
  Fan; earlier gives ROM Checksum / RAM / RAM Battery.