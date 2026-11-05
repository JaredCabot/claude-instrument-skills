---
name: hp8648-gpib
description: Operate, program (SCPI/HP-IB/GPIB), troubleshoot, verify and service the HP/Agilent 8648A/B/C/D RF signal generators, including the undocumented SERV/DIAG service commands and running the original 8648 Service Support Software on Windows 10/11. Use whenever the user mentions an 8648 (or "8468"), its options (1E2, 1E5, 1E6, 1EA, 1EP), RF/AM/FM/PM/pulse settings over GPIB, its error numbers, calibration/adjustments, or the motherboard utility.
---

# HP / Agilent 8648A/B/C/D: GPIB control and service

The 8648 family are synthesized RF signal generators from about 1995 to 2003. They speak
**SCPI over HP-IB (IEEE-488.2)** (the manual says SCPI 1992.0; B.04.08 reports 1995.9). A rear-panel switch selects a second language that
is compatible with the **HP 8656B/8657A/B**. Only the GPIB interface is programmable; there is
no LAN, USB or RS-232.

| Model | Frequency | Level (std) | Notes |
|---|---|---|---|
| 8648A | 100 kHz – 1000 MHz | +10 to −136 dBm | Opt 1EP pager encoder (A only) |
| 8648B | 9 kHz – 2000 MHz | +13 to −136 dBm (≤2.5 GHz) | Early units start at 100 kHz (serial prefix < 3623A/3629U) |
| 8648C | 9 kHz – 3200 MHz | +13 (≤2.5 GHz) / +10 dBm | |
| 8648D | 9 kHz – 4000 MHz | +13 (≤2.5 GHz) / +10 dBm | |

Options: **1E2** mod generator (10 Hz–20 kHz sine/tri/sqr/saw, "INT2"), **1E5** high-stability
timebase, **1E6** pulse modulation (B/C/D), **1EA** high power (B/C/D, up to +20 dBm),
**1EP** pager encoder (A only; includes 1E2 functions).

## Quick start (PyVISA)

```python
import pyvisa
rm = pyvisa.ResourceManager()
sg = rm.open_resource("GPIB0::19::INSTR")      # factory address 19
sg.read_termination = "\n"; sg.write_termination = "\n"; sg.timeout = 5000
print(sg.query("*IDN?"))      # Hewlett-Packard, 8648C, 3642U01792, B.04.08
print(sg.query("*OPT?"))      # HIGH STABILITY REF,0,HIGH POWER,0,0,0,
sg.write("*RST;*CLS")
sg.write("FREQ:CW 100 MHZ")
sg.write("POW:AMPL -10 DBM")
sg.write("OUTP:STAT ON")       # RF output is OFF after *RST and at power-up
print(sg.query("SYST:ERR?"))   # +0,"No error; "
sg.control_ren(6)              # GTL + deassert REN -> front panel back to local
```

**Rules that matter in practice** (they bite every new 8648 program):
1. **Only one of AM, FM, PM (and DM) can be ON at a time.** Turning one on while another is on
   gives **−221 Settings conflict**, and the instrument state stays unchanged. Always turn the
   others off first: `AM:STAT OFF;:PM:STAT OFF;:FM:STAT ON`.
2. Setting a depth or deviation does **not** enable the modulation. Use `xx:STAT ON`.
3. `OUTP:STAT` is **OFF** after power-up and after `*RST`.
4. Concatenate commands with `;` and restart at the root with `;:`, for example
   `FREQ:CW 500 MHZ;:POW:AMPL -47 DBM`.
5. Numeric replies are `+1.71800000000000E+009` (NR3). Enumerations come back long-form
   (`EXTERNAL`, `DC`). Booleans come back as `0`/`1`.
6. Default units: Hz, dBm, PCT, radians. Optional suffixes: `HZ KHZ MHZ GHZ`, `DBM DB DBUV DBUVEMF
   V MV UV MVEMF UVEMF`, `PCT`. The manual also shows `RAD`, but B.04.08's unit table has no RAD:
   send PM deviation as a bare number.
7. Use `*OPC?` after slow changes (frequency band switches, attenuator, DCFM cal) before
   measuring. Typical frequency switching is under 75 ms (<1001 MHz) and under 100 ms above that.
8. Reading the next error after a bad command: a failed query often leaves
   **−420 Query UNTERMINATED**. Do a `device clear` (`sg.clear()`) and then `*CLS`.

The full command set (every subsystem, *RST values and ranges) is in
`references/scpi-commands.md`. Status registers are in `references/status-and-errors.md`.

## Typical tasks

| Task | Commands |
|---|---|
| CW carrier | `FREQ:CW 433.92 MHZ;:POW:AMPL 0 DBM;:OUTP:STAT ON` |
| FM 1 kHz, 5 kHz dev | `AM:STAT OFF;:PM:STAT OFF;:FM:SOUR INT;:FM:INT:FREQ 1 KHZ;:FM:DEV 5 KHZ;:FM:STAT ON` |
| AM 30 % 400 Hz | `FM:STAT OFF;:PM:STAT OFF;:AM:SOUR INT;:AM:INT:FREQ 400 HZ;:AM:DEPT 30 PCT;:AM:STAT ON` |
| External DC-FM + zero offset | `FM:SOUR EXT;:FM:EXT:COUP DC;:FM:STAT ON;:CAL:DCFM` (MOD INPUT open or 0 V) |
| Internal + external (FM+FM) | `FM:SOUR INT,EXT` |
| 1E2 variable tone | `FM:SOUR INT2;:FM:INT2:FREQ 2.5 KHZ;:FM:INT2:FUNC:SHAP TRI` |
| PM 2 rad | `PM:DEV 2;:PM:STAT ON` (radians; no external DC coupling for PM) |
| Pulse (1E6, rear TTL in) | `PULM:STAT ON` (−241 if not fitted) |
| Hold attenuator (glitch-free level sweeps) | `POW:ATT:AUTO OFF` (±10 dB vernier, keep within +5 dB) |
| Relative level/frequency | `POW:REF 0 DBM;:POW:REF:STAT ON` / `FREQ:REF ...;:FREQ:REF:STAT ON` |
| Save/recall setups | `*SAV <reg>[,<seq>]`, `*RCL <reg>[,<seq>]` (10 sequences × 30 registers) |
| Language switch | `SYST:LANG "COMP"` (8656/57 codes) / `SYST:LANG "SCPI"`; wait 0.5 s afterwards |

A frequency/level sweep is just a loop over `FREQ:CW` and `POW:AMPL` with `*OPC?`. The 8648 has
no list or sweep subsystem.

## Status and errors (summary)

* `SYST:ERR?` returns `<code>,"<text>; "`. Read it until you get `+0`.
* Questionable status bits: **POWer** (bit 0 RPP tripped, bit 1 amplitude in unspecified range,
  i.e. above +10 dBm), **MODulation** (bit 0 ext input high, bit 1 ext input low),
  **CALibration:FEXTension**, and **PAGing** (1EP).
  For example, `STAT:QUES:MOD:COND?` returns `+2` when nothing is connected to MOD INPUT and EXT
  is selected.
* After reverse power protection trips, remove the source, then send `OUTP:STAT ON` to reset it.
* Service messages 5xx/6xx (cal restore failures, PSU, out-of-lock, comm failure, DSP board)
  are decoded in `references/status-and-errors.md`, together with the faulty assembly to check.

## Service-level commands (undocumented)

The 8648 Service Support Software uses a hidden `SERVice`/`DIAGnostic` command set. Treat these as
expert-only. **Read-only queries are safe.** Anything with `PRODuction:CAL`, `:STORE`, `:PUP`,
`:MEM:SCRATCH`, `BOARDID <value>` or `INSTRUMENT:MODEL/SERNUM` writes calibration or identity
memory. It can erase the instrument's calibration and force a complete re-adjustment.
Never send those without the user explicitly asking and confirming.

Verified read-only on a live 8648C (fw B.04.08):

| Query | Reply | Meaning |
|---|---|---|
| `SERV:BOARDID? MOTHER_BD` | `"031403293\x01"` | A3 motherboard ID: part 0314, serial 03293 |
| `SERV:BOARDID? ATTEN_BD` | `"00113351A\x01"` | A11 attenuator: part 0011, serial 3351A |
| `SERV:PRODUCTION:CAL? CONFIG_CAL,1` | `+3.2E+009` | maximum frequency (model configuration) |
| `SERV:PRODUCTION:CAL? CONFIG_CAL,2` | `+9.9E+001` | options word (0x63; bits in the service-commands reference) |
| `SYST:LANG?` | `"scpi"` | current language |

**Calibration arrays** can be read one element at a time with
`SERV:PRODUCTION:CAL? <array>,<index>` (e.g. `out_10db,3`, `timebase,0`). Use the read-only
backup tool rather than ad-hoc loops:
`python scripts/hp8648_calbackup.py backup --addr GPIB0::19::INSTR` (bundled with this skill), then `compare a.json b.json`. The tool refuses any array or index not in `scripts/known_arrays.txt` before it reaches the bus.
`restore backup.json` writes a backup back to the same instrument. It is a dry run unless
`--apply` is given; it writes the differing elements of writable arrays (every element with
`--all`, the default in the `tools/fw/gpib_romdump.py` menu), verifies each STORE group by reading
it back before storing, and has its own allow-list (CAL:BEGIN/END, CAL <array>,<i>,<n>,
CAL:STORE <group>; never PUP, MEM, BOARDID/INSTRUMENT). **An agent may run the dry run; it must
never run `--apply` (or the menu's restore in `tools/fw/gpib_romdump.py`) without the user's explicit
approval for that run.**
⚠ **Reading an array for option hardware that isn't fitted crashes the firmware.** For example,
`dsp_2fsk_cal` on a unit without 1EP gives "Fatal firmware error", and the unit needs a power
cycle (cal is not affected). Never probe unknown names.
⚠ **Reading one index past the end of an array also crashes it.** For example,
`outllvl_frq,6` gives `FATAL FIRMWARE ERROR: assertion failure 597: h:FileMgr.m`. Most arrays
return −224 for an index that is out of range, but some do not. Read only the exact counts listed in
`known_arrays.txt` (the backup tool does this) and never scan for the end of an array.
After a crash, wait until the self test has finished before you query again. The unit may not
answer GPIB for some time, and Connection Expert may show "unknown model". Then verify with a backup
followed by `compare`. Per YO4HFU, a bad *write* to CONFIG_CAL can brick the cal EEPROMs
(U59/U201, U18, U35, U803, U804, all 93Cxx), and recovering needs an EEPROM programmer.
⚠ **Never hold `+/−` or SAV while switching the instrument on.** `+/−` rewrites every calibration
file with its defaults (A.02.08 and B.04.08). SAV (B.04.08) rewrites the Config2, Out LF Lvl and
LF Atten EEPROM files from the RAM copy when their checksums differ (`docs/re/firmware.md`).
⚠ `SERV:PROD:MEM:BYTE|WORD|LONG <addr>,<value>` writes any memory address. The queries
(`…? <addr>`; B.04.08 needs `#H<hex>`, A.02.08 decimal) read it, but a WORD/LONG read at an odd address, or a read of an
address with nothing behind it, crashes the firmware (power cycle; nothing is written).

The complete catalogue is in `references/service-commands.md`: array list with sizes and
meanings, the config bit map, DIAG latch and DSP commands, and the write commands with their
dangers. The firmware can be read over GPIB with `SERV:PRODUCTION:MEM:LONG? #H<addr>`
(`tools/fw/gpib_romdump.py`, ~37 min for 512 KB); its analysis is in `docs/re/firmware.md`,
`docs/re/firmware-b0408-report.md` and the reference manual in `docs/re/manual/`.

## Calibration and adjustments: use the original software

Adjustments write factory-style calibration arrays (`OUT_LOSS`, `GEN_LOSS_CAL`, `OUT_PRE_PWR`,
`OUT_TUNE_CAL`, `OUT_LF_LOSS`, …). Do them with the **original Agilent 8648 Service Support
Software**, which this project makes run on Windows 10/11:

```
legacy\install.cmd      # one-time install (PowerShell; options: legacy\install.ps1 -?)
C:\HP_SVC\TestExec.cmd   # login User/User (run tests) or Admin/Falcon (configure equipment)
C:\HP_SVC\MBUtil.cmd     # motherboard utility; Cancel at the password = read-only view
```

How it works: otvdm runs the 16-bit program, and our `iolib_32.dll` shim maps `hpib7` to `gpib0`.
Setting `[Debug] Log=` in `C:\HP_SVC\BIN\iolib_32.ini` records every GPIB transaction.
The adjustment list, required test equipment, default GPIB addresses and the datapack format
are in `references/service-software.md`. Manual adjustments that need no software, such as the
internal reference using the rear TIMEBASE ADJ switch, are described there too.

## Performance verification

Chapter 8 of the service manual lists FM accuracy and distortion, AM accuracy and distortion,
PM distortion, residual FM, harmonics, spurious, DC-FM error, RF level accuracy, and pulse
on/off ratio and rise time. For 1EP there are encoder timebase and FSK deviation, and for 1E5
the aging rate. The service software automates the Power Level Accuracy test only.
The specifications needed to set limits are in `references/specifications.md`.

## Troubleshooting checklist

* **No response / timeout:** check the address (front panel `ADRS`; factory 19). The rear
  language switch must be SCPI unless you speak 8656 codes. The instrument must have finished
  its power-up self test.
* **−113 Undefined header:** a typo, or a command another SCPI generator has but the 8648 lacks,
  e.g. `DIAG:INFO:OPT?`, `FREQ:MODE`, `LIST`. The 8648 subset is small; check the reference.
* **−221 Settings conflict:** another modulation is still on, or `CAL:DCFM` was sent without
  EXT DC FM active.
* **−222 Data out of range:** the value is outside the model's range or the deviation limit
  at that carrier.
* **−241:** pulse modulation requested without option 1E6.
* **The front panel stays in REMOTE:** send GTL (`control_ren(6)`) or press LOCAL.

## Project files

The service-software kit and analysis include:
* `legacy/`: the Windows 10/11 kit for the original software (installer and iolib_32 shim)
* `analysis/`: Ghidra decompilation and string dumps of every original binary
* `reference/manuals/`: (local only, not tracked) service manual and bench-equipment manuals
* `docs/`: architecture, reverse-engineering notes and project status
