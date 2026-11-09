---
name: hp8648-gpib
description: Operate, program (SCPI/HP-IB/GPIB), troubleshoot, verify and service the HP/Agilent 8648A/B/C/D RF signal generators, including the undocumented SERV/DIAG service commands and the original 8648 Service Support Software. Use whenever the user mentions an 8648 (or "8468"), its options (1E2, 1E5, 1E6, 1EA, 1EP), RF/AM/FM/PM/pulse settings over GPIB, its error numbers, calibration/adjustments, or the motherboard utility.
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
print(sg.query("*IDN?"))      # Hewlett-Packard, 8648C, <serial>, B.04.08
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

The full command set (every subsystem, *RST values and ranges) is in Appendix A. Status
registers and every message number are in Appendix B.

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
  are decoded in Appendix B, together with the faulty assembly to check.

## Service-level commands (undocumented)

The 8648 Service Support Software uses a hidden `SERVice`/`DIAGnostic` command set. Treat these as
expert-only. **Read-only queries are safe.** Anything with `PRODuction:CAL`, `:STORE`, `:PUP`,
`:MEM:SCRATCH`, `BOARDID <value>` or `INSTRUMENT:MODEL/SERNUM` writes calibration or identity
memory. It can erase the instrument's calibration and force a complete re-adjustment.
Never send those without the user explicitly asking and confirming.

Verified read-only on a live 8648C (fw B.04.08):

| Query | Reply | Meaning |
|---|---|---|
| `SERV:BOARDID? MOTHER_BD` | `"0314nnnnn\x01"` | A3 motherboard ID: part suffix 0314, then the board serial |
| `SERV:BOARDID? ATTEN_BD` | `"0011nnnnn\x01"` | A11 attenuator: part 0011, then the board serial |
| `SERV:PRODUCTION:CAL? CONFIG_CAL,1` | `+3.2E+009` | maximum frequency (model configuration) |
| `SERV:PRODUCTION:CAL? CONFIG_CAL,2` | `+9.9E+001` | options word (0x63; bits in Appendix C) |
| `SYST:LANG?` | `"scpi"` | current language |

**Calibration arrays** can be read one element at a time with
`SERV:PRODUCTION:CAL? <array>,<index>` (e.g. `out_10db,3`, `timebase,0`). Use the read-only
backup tool in Appendix F (save it as `hp8648_calbackup.py`) rather than ad-hoc loops:
`python hp8648_calbackup.py backup --addr GPIB0::19::INSTR`, then `compare a.json b.json`. The tool refuses any array or index not in its built-in `KNOWN_ARRAYS` table before it reaches the bus.
`restore backup.json` writes a backup back to the same instrument. It is a dry run unless
`--apply` is given; it writes the differing elements of writable arrays (every element with
`--all`), verifies each STORE group by reading
it back before storing, and has its own allow-list (CAL:BEGIN/END, CAL <array>,<i>,<n>,
CAL:STORE <group>; never PUP, MEM, BOARDID/INSTRUMENT). **An agent may run the dry run; it must
never run `--apply` without the user's explicit approval for that run.**
⚠ **Reading an array for option hardware that isn't fitted crashes the firmware.** For example,
`dsp_2fsk_cal` on a unit without 1EP gives "Fatal firmware error", and the unit needs a power
cycle (cal is not affected). Never probe unknown names.
⚠ **Reading one index past the end of an array also crashes it.** For example,
`outllvl_frq,6` gives `FATAL FIRMWARE ERROR: assertion failure 597: h:FileMgr.m`. Most arrays
return −224 for an index that is out of range, but some do not. Read only the exact counts listed in
the `KNOWN_ARRAYS` table (the backup tool does this) and never scan for the end of an array.
After a crash, wait until the self test has finished before you query again. The unit may not
answer GPIB for some time, and VISA discovery tools may show it as an unknown model. Then verify with a backup
followed by `compare`. Per YO4HFU, a bad *write* to CONFIG_CAL can brick the cal EEPROMs
(U59/U201, U18, U35, U803, U804, all 93Cxx), and recovering needs an EEPROM programmer.
⚠ **Never hold `+/−` or SAV while switching the instrument on.** `+/−` rewrites every calibration
file with its defaults (A.02.08 and B.04.08). SAV (B.04.08) rewrites the Config2, Out LF Lvl and
LF Atten EEPROM files from the RAM copy when their checksums differ.
⚠ `SERV:PROD:MEM:BYTE|WORD|LONG <addr>,<value>` writes any memory address. The queries
(`…? <addr>`; B.04.08 needs `#H<hex>`, A.02.08 decimal) read it, but a WORD/LONG read at an odd address, or a read of an
address with nothing behind it, crashes the firmware (power cycle; nothing is written).

The complete catalogue is in Appendix C: array list with sizes and meanings, the config bit
map, DIAG latch and DSP commands, and the write commands with their dangers. The firmware can be
read over GPIB with `SERV:PRODUCTION:MEM:LONG? #H<addr>` (about 37 min for 512 KB; the read loop
is in Appendix F).

## Calibration and adjustments: use the original software

Adjustments write factory-style calibration arrays (`OUT_LOSS`, `GEN_LOSS_CAL`, `OUT_PRE_PWR`,
`OUT_TUNE_CAL`, `OUT_LF_LOSS`, …). Do them with the **original Agilent 8648 Service Support
Software** (EPSG090522), which runs the adjustment DLLs against your test equipment and writes
the arrays in the order the firmware expects. Logins, the adjustment list, required test
equipment, default GPIB addresses and which adjustments follow which repair are in Appendix D.
Manual adjustments that need no software, such as the internal reference using the rear
TIMEBASE ADJ switch, are described there too.

The software is 16-bit Windows code using HP SICL. It runs on a period PC (Windows 3.1/95/98)
with an HP/Agilent GPIB card and SICL. On 64-bit Windows it needs a 16-bit compatibility layer
(for example otvdm/winevdm) plus a 32-bit SICL installation; this skill does not include such a
kit. Whatever the host, keep a GPIB transaction log during adjustments and take a backup with the
Appendix F tool first.

## Performance verification

Chapter 8 of the service manual lists FM accuracy and distortion, AM accuracy and distortion,
PM distortion, residual FM, harmonics, spurious, DC-FM error, RF level accuracy, and pulse
on/off ratio and rise time. For 1EP there are encoder timebase and FSK deviation, and for 1E5
the aging rate. The service software automates the Power Level Accuracy test only.
The specifications needed to set limits are in Appendix E.

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

## Appendix A: SCPI command reference

Source: *HP 8648A/B/C/D Signal Generator Service Guide*, chapter 2 "HP-IB Programming". Replies marked ✔ were verified on a
live 8648C (firmware B.04.08) on 2026-10-05.

Conventions: `[ ]` marks an optional node, `|` separates alternatives, and lower-case letters
may be omitted (`FREQuency` → `FREQ`). `[SOURce]` is implied on all source subsystems.
`<NRf>` is any number; `<NR1>` is an integer. Unit suffixes are listed in the rules near the top.
If no suffix is given, the defaults are Hz, dBm, PCT and radians.

### IEEE 488.2 common commands

| Command | Function |
|---|---|
| `*IDN?` | `Hewlett-Packard, 8648C, <serial>, B.04.08` ✔ |
| `*OPT?` | 6 comma-separated fields, e.g. `HIGH STABILITY REF,0,HIGH POWER,0,0,0,` ✔ (the 0s are absent options) |
| `*RST` | preset to *RST values below (RF OFF, 100 MHz, −136 dBm) |
| `*CLS` | clear status/event registers and error queue |
| `*TST?` | run the "Five second self test" subset of power-up tests; returns 0 = pass |
| `*WAI` | wait for pending operations |
| `*OPC` / `*OPC?` | operation complete bit / query returns 1 |
| `*ESE <n>` / `*ESE?` | standard event status enable |
| `*ESR?` | standard event status register (reading clears) ✔ |
| `*SRE <n>` / `*SRE?` | service request enable |
| `*STB?` | status byte incl. MSS ✔ |
| `*SAV <reg>[,<seq>]` | save setup (registers 0–99, sequences 0–9; seq defaults to the last one used, 0 at power-up) |
| `*RCL <reg>[,<seq>]` | recall setup |

### FREQuency

| Command | *RST | Notes |
|---|---|---|
| `FREQ[:CW\|:FIXed] <NRf>[HZ\|KHZ\|MHZ\|GHZ]` / `?` | 100 MHz | 10 Hz resolution, up to 9 digits. Reply `+1.71800000000000E+009` ✔ |
| `FREQ:REFerence <NRf>` / `?` | 0 Hz | reference used when REF:STAT ON |
| `FREQ:REFerence:STATe ON\|OFF\|1\|0` / `?` | OFF | ON = frequencies entered/queried relative to the reference |

### POWer (amplitude)

| Command | *RST | Notes |
|---|---|---|
| `POW[:LEVel][:IMMediate][:AMPLitude] <NRf>[DBM\|DB\|DBUV\|DBUVEMF\|V\|MV\|UV\|MVEMF\|UVEMF]` / `?` | −136 dBm | 0.1 dB resolution; query returns dBm (or dB when REF ON) ✔. Normal short form `POW:AMPL` |
| `POW:ATTenuation:AUTO ON\|OFF\|1\|0` / `?` | ON | OFF = attenuator hold (ATTN HOLD key): ±10 dB vernier around the held range ✔ |
| `POW:REFerence <NRf>` / `?` | 0 dBm | in REF mode only DB/DBM units are allowed |
| `POW:REFerence:STATe ON\|OFF` / `?` | OFF | |

Levels above +10 dBm (above +13 dBm for B/C/D ≤2.5 GHz) are "unspecified". They set
`STAT:QUES:POW` bit 1 and display "Amplitude exceeds specified range".

### OUTPut

| Command | *RST | Notes |
|---|---|---|
| `OUTP[:STATe] ON\|OFF\|1\|0` / `?` | OFF | RF output on/off. Also re-arms the reverse-power protection after it trips ✔ |

### AM subsystem

| Command | *RST | Notes |
|---|---|---|
| `AM[:DEPTh] <NRf>[PCT]` / `?` | 30 % | 0.1–99.9 % (0–100 % spec, output ≤ +4 dBm) |
| `AM:STATe ON\|OFF` / `?` | OFF | FM/PM/DM must be OFF, else −221 |
| `AM:SOURce INT[1]\|INT2\|EXT\|INT,EXT\|EXT,INT` / `?` | INT | reply `INTERNAL`, `EXTERNAL`, … ✔. INT2 needs 1E2/1EP |
| `AM:INTernal[1]:FREQuency 400 HZ\|1 KHZ` / `?` | 1 kHz | only the two fixed tones |
| `AM:INTernal2:FREQuency <NRf>` / `?` | 1 kHz | 1E2: 10 Hz–20 kHz; 1EP: 20 Hz–10 kHz |
| `AM:INTernal2:FUNCtion:SHAPe SIN\|TRI\|SQU\|SAW` / `?` | SIN | 1E2 only |
| `AM:EXTernal:COUPling AC\|DC` / `?` | DC | GROund not supported |

### FM subsystem

| Command | *RST | Notes |
|---|---|---|
| `FM[:DEViation] <NRf>[HZ\|KHZ]` / `?` | 3 kHz | range depends on carrier: 200 kHz (<249 MHz), 100 kHz (<501), 200 kHz (<1001), 400 kHz (<2001), 800 kHz (≤4000 MHz) |
| `FM:STATe ON\|OFF` / `?` | OFF | AM/PM/DM must be OFF |
| `FM:SOURce INT[1]\|INT2\|EXT\|INT,EXT\|EXT,INT` / `?` | INT | INT,EXT = FM+FM (external sets ½ deviation at 0.5 V) |
| `FM:INTernal[1]:FREQuency 400 HZ\|1 KHZ` / `?` | 1 kHz | |
| `FM:INTernal2:FREQuency <NRf>` / `?` | 1 kHz | 1E2/1EP |
| `FM:INTernal2:FUNCtion:SHAPe SIN\|TRI\|SQU\|SAW` / `?` | SIN | 1E2 |
| `FM:EXTernal:COUPling AC\|DC` / `?` | DC | DC = DC-FM; run `CAL:DCFM` afterwards |

### PM subsystem

| Command | *RST | Notes |
|---|---|---|
| `PM[:DEViation] <NRf>` / `?` (manual: optional `RAD`; not in B.04.08's unit table, so omit it) | 1.0 rad | 10 rad (<249 MHz), 5 (<501), 10 (<1001), 20 (<2001), 40 (≤4000) |
| `PM:STATe ON\|OFF` / `?` | OFF | AM/FM/DM must be OFF |
| `PM:SOURce INT[1]\|INT2\|EXT\|INT,EXT\|EXT,INT` / `?` | INT | |
| `PM:INTernal[1]:FREQuency 400 HZ\|1 KHZ`, `PM:INTernal2:FREQuency`, `PM:INTernal2:FUNCtion:SHAPe` | | as FM |
| `PM:EXTernal:COUPling AC\|DC` / `?` | DC | front panel cannot do EXT DC for PM (message 001) |

### CAL subsystem

| Command | Notes |
|---|---|
| `CAL:DCFM` | zero the DC-FM carrier offset. EXT DC FM must be active (else −221); MOD INPUT open or 0 V. The display shows "DCFM calibration in progress" (021) |

### PULM (option 1E6)

| Command | *RST | Notes |
|---|---|---|
| `PULM:STATe ON\|OFF` / `?` | OFF | modulator driven from the rear-panel TTL pulse input. −241 if not fitted. Rise/fall < 10 ns; on/off > 80 dB (< 2 GHz) |

### STATus subsystem

`STATus:QUEStionable[:EVENt]? | :CONDition? | :ENABle <NR1> | :ENABle?` and the same four
for the sub-registers `:POWer`, `:MODulation`, `:CALibration:FEXTension` and `:PAGing` (1EP).
See Appendix B for the bit map. The event registers are cleared when read.

### SYSTem

| Command | Notes |
|---|---|
| `SYST:ERRor?` | `+0,"No error; "` ✔ (note the trailing `; ` inside the quotes) |
| `SYST:VERSion?` | `1995.9` ✔ (the manual says YYYY.V; this unit reports 1995.9) |
| `SYST:LANGuage "SCPI"\|"COMP"` / `?` | `"scpi"` ✔. COMP = HP 8656B/8657A/B codes. Wait 0.5 s after switching. The rear switch wins again at the next power-up |

### Option 1EP pager encoder (8648A only)

| Command | Notes |
|---|---|
| `INITiate[:IMMediate]` | start encoding |
| `ABORt` | stop encoding |
| `TRIGger:COUNt <NR1>` / `?` | 0 = continuous, 1 = single (with collapse 0), 1–256 burst; RESYNC: bursts of 1.92 s |
| `DM:FORMat FSK2\|FSK4`, `DM:STATe`, `DM:DEViation <NRf>`, `DM:POLarity NORM\|INV`, `DM:FILTer:STATe` | digital (FSK) modulation; *RST FSK2, OFF, 3 kHz, NORM, ON |
| `PAG[:FORMat]:SELect POCSag\|FLEX\|FTD\|RESYnc\|PN15` | *RST FLEX |
| `PAG:{POCS\|FLEX\|FTD\|PN15}:RATE <NR1>` | FLEX/FTD 1600/3200/6400; POCSAG 512/1200/2400; PN15 any of these |
| `PAG:{POCS\|FLEX\|FTD}:MESSage:SELect <0-6>` | 0 arbitrary, 1–5 fixed, 6 user |
| `PAG:{…}:MESSage:DEFine 'string'` / `:LENGth <n>` | user message, max 40 chars |
| `PAG:{…}:ARBitrary:STARt\|STOP <n>` / `:DEFine <seg>,<d0>,<d1>,…` | 128-segment buffer; 16-bit signed words |
| `PAG:{FLEX\|FTD}:TYPE TONE\|NUMeric\|ALPHanumeric\|HBINary` | |
| `PAG:{FLEX\|FTD}:VECTor STAN\|SPEC\|NUMB`, `:NUMBer <0-63>`, `:HBINary BIT1\|BIT7\|BIT8\|BIT14\|BIT16` | |
| `PAG:{FLEX\|FTD}:CODE 'capcode'` | e.g. `'A0000001'`; derives frame, phase, collapse and address type |
| `PAG:{FLEX\|FTD}:CYCLe <0-4>`, `:FRAMe <0-127>`, `:PHASe A\|B\|C\|D`, `:COLLapse <0-7>`, `:CCOunt?`, `:FCOunt?` | |
| `PAG:{FLEX\|FTD}:ATYPe SHOR\|LONG`, `:ADDR1 <n>`, `:ADDR2 <n>` (legacy: `:SADDress`, `:LADD1`, `:LADD2`) | |
| `PAG:{FLEX\|FTD}:ISTop:STATe`, `:HEADer:STATe`, `:TERMinator:STATe` | |
| `PAG:{FLEX\|FTD}:DCALl:STATe`, `:DCALl:ADDR1\|ADDR2` | dummy call |
| `PAG:{FLEX\|FTD}:ROAMing:SELect NONE\|SSID\|NID`, `:ROAM:SSID:LID\|CZONe\|CCODe\|TMF\|FOFF`, `:ROAM:NID:ADDRess\|CHANnel\|AREA\|MULTiplier\|TMF\|FOFF` | |
| `PAG:FTD:REPeat <0-3>` / `:RCOunt?` | FLEX-TD repeats |
| `PAG:POCSag:TYPE TONE\|NUM\|ALPH\|ALPH7\|ALPH8`, `:FUNCtion <0-3>`, `:CODE <7 digits>` | |

To change the data rate the FSK level must match. For example, FLEX 6400 bps:
`PAG:FLEX:RATE 6400;:DM:FORM FSK4;:DM:DEV 4.8 KHZ;:DM:STAT ON`.

### *RST vs. 8656/57 "clear" values

| Parameter | 8648 *RST | 8648 COMP clear | 8656B | 8657A/B |
|---|---|---|---|---|
| Carrier | 100 MHz | 100 MHz | 100 MHz | 100 MHz |
| Level | −136 dBm | −136 dBm | −127 dBm | −143.5 dBm |
| AM depth | 30 % | 0 % | 0 % | 0 % |
| FM dev | 1.0 kHz¹ | 0 | 0 | 0 |
| Pulse | Off | unchanged | – | unchanged |

¹ The manual's table says 1.0 kHz, but the FM subsystem text and a live query on the 8648C
give 3 kHz (`FM:DEV?` → 3.0E+003). Trust the query.

### HP 8656/8657-compatible language (SYST:LANG "COMP" or rear switch)

Implemented codes (upper or lower case): `FR` frequency, `AP` amplitude, `AM`, `FM`, `AO`
amplitude offset, units `HZ KZ MZ DB DF DM EM MV UV VL PC %`, `UP DN` step, `IS` increment
set, `RC RL` recall, `SV` save, `SQ` sequence, `GT` flexible sequence, `QS` reverse sequence,
`RP` reverse-power reset, `R2 R3` RF off/on (R5 is executed for R2), `S1` external, `S2`
400 Hz, `S3` 1 kHz, `S4` modulation off, `S5` DC FM, `HI` HI ALC.
Not implemented: `LO PD PF PI PM R0 R1`.
Differences: after "RF off" a level change does not turn RF back on (send `OUTP:STAT ON`).
Every line needs a line terminator.

### Not supported (common mistakes)

`FREQ:MODE`, `LIST:*`, `SWEep:*`, `SOUR:POW:ALC`, `DIAG:INFO:OPT?` (→ −113) ✔,
`OUTP:MOD`, `MEMory:*`, and the ESG-style `:SOURCE:RADIO:*`/`BURST`/`ARB`. Those strings appear
in the service-software DLLs because the code is shared with the ESG; they do not apply to the 8648.

## Appendix B: Status reporting and message numbers

### Status model (service guide Fig. 2-1)

```
POWer condition            MODulation condition        PAGing condition (1EP)
 bit0 Reverse power (RPP)   bit0 Ext mod level HIGH     bit0 Start of frame/batch
 bit1 Unspecified amplitude bit1 Ext mod level LOW      bit1 End of encoding
        │                           │                           │
        ▼ (summary)                 ▼ (summary)                 ▼ (summary)
QUEStionable: bit3 POWer*   bit7 MODulation (=128)      bit12 PAGing (=4096)
              bit8 CALibration* (FEXTension sub-register)
        │
        ▼
Status Byte: bit3 QUES summary (*SRE 8 to get SRQ), bit4 MAV, bit5 ESB, bit6 MSS/RQS
Standard Event (*ESR?): bit0 OPC, bit1 Request Control, bit2 Query err, bit3 Device err,
                        bit4 Execution err, bit5 Command err, bit6 User request, bit7 Power on
```
\* The manual shows bit numbers only for MOD (7) and PAG (12). POWer = 3 and CAL = 8 follow
the SCPI convention and have not been verified on hardware yet.

Live example (8648C, nothing connected to MOD INPUT, EXT source selected, after power-up):
`STAT:QUES:MOD:COND?` → `+2` (ext level LOW), `STAT:QUES:COND?` → `+128`, `*ESR?` → `+128`
(power-on), `*STB?` → `+16`.

### Recipes
* **SRQ on external modulation level out of range**: `STAT:QUES:MOD:ENAB 3;:STAT:QUES:ENAB 128;*SRE 8`, then serial poll.
* **Check reverse power protection**: `STAT:QUES:POW:COND?` bit 0. To reset, remove the RF source and send `OUTP:STAT ON`.
* **Unspecified level**: `STAT:QUES:POW:COND?` bit 1 (level > +10 dBm, or ATTN HOLD vernier range exceeded).
* **1EP end of encoding**: `STAT:QUES:PAG:ENAB 2;:STAT:QUES:ENAB 4096;*SRE 8`; start of frame: `PAG:ENAB 1`.

### SCPI error queue (`SYST:ERR?`)

| Code | Text | Typical cause on the 8648 |
|---|---|---|
| 0 | No error | |
| −101 | Invalid character | e.g. `SETUP&` |
| −102 | Syntax error | |
| −103 | Invalid separator | missing `;` |
| −104 | Data type error | |
| −105 | GET not allowed | |
| −108 | Parameter not allowed | too many parameters |
| −109 | Missing parameter | |
| −111 | Header separator error | |
| −112 | Program mnemonic too long | header > 12 chars |
| −113 | Undefined header | command does not exist on the 8648 (e.g. `DIAG:INFO:OPT?`) |
| −121 | Invalid character in number | |
| −123 | Exponent too large | |
| −124 | Too many digits | |
| −128 | Numeric data not allowed | |
| −131 | Invalid suffix | wrong unit for the parameter |
| −134 | Suffix too long | |
| −141 | Invalid character data | wrong enum |
| −144 | Character data too long | |
| −148 | Character data not allowed | |
| −158 | String data not allowed | |
| −168 | Block data not allowed | |
| −178 | Expression data not allowed | |
| −221 | Settings conflict | second modulation turned on; `CAL:DCFM` without EXT DC FM |
| −222 | Data out of range | value outside the model's range or the deviation limit |
| −224 | Illegal parameter value | |
| −241 | Hardware missing | pulse modulation without 1E6 |
| −330 | Self-test failed | |
| −350 | Queue overflow | |
| −410 | Query INTERRUPTED | new command before the reply was read |
| −420 | Query UNTERMINATED | read without a pending query (often after a failed query: do a device clear) |
| −430 | Query DEADLOCKED | |
| −440 | Query UNTERMINATED after indefinite response | |

### Front-panel operation messages

| No. | Message |
|---|---|
| 001 | No external dc coupling for PM |
| 002 | Modulation exceeds deviation range |
| 003 | There are no registers available |
| 004 | Invalid units selection |
| 005 | Increment value entry out of range |
| 006 | End of increment range |
| 007 | Entered value out of range |
| 010 | End of knob range |
| 011 | Amplitude exceeds ATTN HOLD limits (vernier exceeded by > 5 dB) |
| 017 | Copying registers from 8647/8 (83301A memory interface) |
| 020 | Press SAV to copy memory FROM 8647/8 |
| 021 | DCFM calibration in progress |
| 022 | Press SAV to copy memory TO 8647/8 |
| 023 | Copying registers to 8647/8 |
| 024 | Invalid data in Memory Interface |
| 025 | Communication failure: copy aborted |
| 026 | Memory copy was successful |
| — | "Five second self test ..." while `*TST?` runs |

### Service error messages (5xx/6xx, power-up self test)

| No. | Message | Check / replace |
|---|---|---|
| 502 | Updated cal file (RAM updated from cal ROM) | normal after a module swap |
| 503 | Cal corrupt: restored | no action |
| 504 | Modulation cal restore failure | A3 |
| 505 | FM sense cal restore failure | A5 (cal ROM), then A3 (RAM) |
| 506 | FM mult cal restore failure | A5, then A3 |
| 507 | Output level cal restore failure | A6, then A3 |
| 508 | Attenuator cal restore failure | A7, then A3 |
| 509 | Timebase cal restore failure | A4, then A3 |
| 510 | Temperature cal restore failure | A7, then A3 |
| 511 | TC coeff's cal restore failure | A7, then A3 |
| 512 | Generic path cal restore failure | A3 |
| 513 | Output tune cal restore failure | A6, then A3 |
| 515 | FreqExt level cal restore failure | A10, then A3 |
| 516 | Config cal restore failure | A3 |
| 517 | Output prelevel cal restore failure | A6, then A3 |
| 518 | Atten comp loss cal restore failure | A3 |
| 514 | Failed attempt to access cal file (not in the service guide; from the firmware) | A3 |
| 519 | Output LF level cal restore failure (firmware only) | A3 |
| 520 | LF Attenuator cal restore failure (firmware only) | A3 |
| 521 | DSP cal restore failure (firmware only) | A3 |
| 601 | −12 V power supply failure (dropped > 0.4 V) | A3 −12 V regulator / A2 −15 V |
| 603 | +12 V power supply failure | A3 +12 V regulator / A2 +15 V |
| 604 | +38 V power supply failure (dropped > 2.2 V) | A2 +38 V |
| 605 | ALC out-of-lock div/het/main band | A6 output, A5 synth input, A4 ref (het only → A4) |
| 608 | Synth out-of-lock div/het/main band | A5, or A4 reference |
| 611 | 200 kHz reference missing at synth | A4 200 kHz out → A5 |
| 612 | Reference out-of-lock at 10 MHz | remove ext ref; then A4 |
| 613 | Reference out-of-lock at 1 GHz | A4 |
| 614 | 400 Hz modulation source failed | A4 200 kHz → A3 |
| 615 | 1 kHz modulation source failed | A3 (if 400 Hz passed) |
| 616 | AM modulation path failure | A3 |
| 617 | FM modulation path failure | A3 |
| 618 | PM modulation path failure | A3 |
| 619 | Modulation 20 dB step failure | A3 |
| 620 | Comm failure: <assembly> | A3 controller and/or the named assembly |
| 625 | ROM checksum failure | motherboard–ROM board connection |
| 626 | Volatile RAM read/write failure | A3 |
| 627 | Battery RAM failure: memory lost | battery (or DEL held at power-up) |
| 628 | Non-volatile RAM read/write failure | A3 |
| 629 | dsp board failure | DSP board on the display, then A3 |
| 700 | Reverse power: Press a key to reset (firmware only) | remove the source, press a key or `OUTP:STAT ON` |
| 701 | Temperature correction failed (firmware only) | A3 / output board |

Assemblies: A1 front panel, A2 power supply, A3 motherboard/controller (cal RAM), A4 reference,
A5 sig-gen synth, A6 output, A7 attenuator (8648A), A10 frequency extension (B/C/D),
A11 attenuator (B/C/D), A12 reverse-power protection (B/C/D), A13 pulse modulator (1E6),
A14 modulation generator (1E2), A30 pager encoder (1EP).

## Appendix C: Undocumented SERVice / DIAGnostic commands

These commands were reverse-engineered from Agilent's 8648 Service Support Software (all
binaries decompiled). Lines marked ✔ were
verified on a live **8648C, firmware B.04.08** on 2026-10-05.

### Golden rules

1. **Queries only, unless the user explicitly asks for a write and confirms it.**
2. **Back up first:**
   `python hp8648_calbackup.py backup --addr GPIB0::19::INSTR` (Appendix F), and
   `... compare old.json new.json` afterwards.
3. **Never read cal arrays that belong to option hardware the unit doesn't have.**
   ✔ `SERV:PRODUCTION:CAL? dsp_2fsk_cal,0` on an 8648C without 1EP caused a **"Fatal firmware
   error"**. The instrument stopped answering GPIB, even device clear and IFC, until it was power
   cycled. Calibration was verified unchanged afterwards. Treat `dsp_*` (1E2/1EP DSP) and other
   FSK/pager/encoder arrays (`*fsk*`, `*pag*`, `*enc*`, `dsp_sin_cal`) as **option-only**.
4. **Never read past the last element.** ✔ `outllvl_frq,6` (the array has 6 elements) halted the
   firmware with "assertion failure 597: h:FileMgr.m,v 1.18". Use only the exact counts below.
5. Do not "discover" array names or lengths by trial. Unknown *queries* are mostly harmless
   (−113/−224), but rules 3 and 4 show that even reads can crash the firmware. Never guess write
   commands.

### Reading calibration arrays (safe for the arrays listed below)

`SERV:PRODUCTION:CAL? <array>,<index>` reads one element. ✔
* Array names are case-insensitive and at most 12 characters (longer → −112 "Program mnemonic
  too long"). Indices start at 0.
* Unknown array → no reply, error −224 "Illegal parameter value". Index past the end → usually
  −224 "Index into file is outside of legal range!", **but on some arrays (`outllvl_frq`) a
  firmware crash**, so never rely on it. The −224 replies also leave −420
  (query unterminated): device clear and drain `SYST:ERR?`. ✔
* Numeric array ids (`165,0`) are rejected with −128 on B.04.08, although an unused helper in
  the motherboard utility tries them. ✔
* STORE/file names (`OUT_LOSS`, `Outlvl_data`, `OUT_TUNE_CAL`, …) are *not* readable arrays. ✔

Arrays present on the 8648C (element counts) ✔:

| Array | n | Meaning (inferred from the adjustment that writes it) | Written by |
|---|---|---|---|
| `config_cal` | 5 | [0] min freq, [1] max freq (Hz in the reply; stored as kHz), [2] options word (bits below), [3] min settable amplitude dBm (−136), [4] max settable amplitude dBm (13/14.5; ≥ +16.01 makes `*OPT?` report HIGH POWER = 1EA) [fw] | motherboard utility |
| `config2_cal` | 1 | 10: level (dBm) above which the AM ALC bandwidth is reduced [fw] | motherboard utility |
| `timebase` | 2 | reference DAC coarse, fine (0–255) | ATBASE / TIMEBASE ADJ switch |
| `out_pre_pwr` | 7 | preleveler constants (2.5e9, 14, 4, 16, 12, 4, 16) | motherboard utility |
| `atn_comp_cal` | 106 | attenuator compensation (dB) | motherboard utility defaults / factory |
| `gen_loss_cal` | 34 | general path loss vs frequency (0 after the AM-level adjustment) | AAMLVL*, motherboard utility |
| `out_lvl_gain`, `out_lvl_ofs` | 32 | output-level DAC slope/offset vs frequency (8648A main band, B/C/D prelevel) | AOM_LVL, APRE_LVL (store `Outlvl_data`) |
| `fextlvl_gain`, `fextlvl_ofs` | 108 | frequency-extension level slope/offset | AFE_LVL (store `fextlvl_data`) |
| `outllvl_gain`, `outllvl_ofs` | 6 | LF (9–100 kHz) output level slope/offset | AOMLLVL (store `Out_lf_data`) |
| `out_0db` … `out_130db` | 22 each | level correction per attenuator step (dB) vs frequency | AHF_PLA (store `out_loss`) |
| `outl_0db` … `outl_130db` | 6 each | LF level correction per attenuator step | ALF_PLA (store `out_lf_loss`) |
| `mod_am_1khz/400hz/extdc/extac` | 2 | AM path full-scale DAC values | AAUDPATH (store `mod_dac`) |
| `mod_fm_*`, `mod_pm_*` (same suffixes) | 4 | FM/PM path full-scale DAC values | AAUDPATH |

More arrays. Counts are for B/C/D, with 8648A in brackets, and all agree with firmware
B.04.08's read routines. The *_frq arrays hold the frequency
points of the matching data arrays and cannot be written.
`gen_loss_frq` 34 · `out_loss_frq` 22 (34) · `outlloss_frq` 6 · `atn_comp_frq` 106 (A: none) ·
`fextlvl_frq` 108 (A: none) · `fm_acfm_dac` 1 (A: none) · `out_lvl_frq` 32 · `outllvl_frq` **6, index 6
crashes** · `fm_sens_frq` 44 · `fm_sens_sgn` 44 · `fm_sens_mult` 1 · `out_tune_frq` 25 ·
`out_tune_dac` 25 · `out_temp_cal` 1 · `tc_thru_path`, `tc_10_40db`, `tc_50_70db`, `tc_80_100db`,
`tc_110_130db` 3 each. The authoritative list is the `KNOWN_ARRAYS` table in the Appendix F tool, which refuses any index beyond it.
`gen_loss_frq` and `gen_loss_cal` have 34 elements on every model (firmware limit; the 8648C
answered all 34). `outllvl_frq` is the one array whose read routine has no index check.

Option-only arrays (read **only** if the option is fitted): `dsp_sin_cal` (1E2/1EP audio
generator, AAUDENC), `dsp_2fsk_cal`, `dsp_4fsk_cal` (1EP filter path, APG_ENC). The
`fm_sens_*` arrays are standard: YO4HFU reads them on an 8648B, and 1EP exists only on the 8648A.

Board IDs for `SERV:BOARDID?`: `MOTHER_BD`, `OUTPUT_BD`, `SYNTH_BD`, `REF_BD`, `ATTEN_BD`,
`FREQ_EXT_BD`. Typical CONFIG_CAL[2] values for B/C/D: 97/99 = no options, 101 = 1E6,
105 = H01, 225 = 1E2 (YO4HFU).

`config_cal[2]` bits (from firmware B.04.08): 0x01 model B/C/D (clear = 8648A), 0x02 default
low-band breakpoints from 100 kHz (clear: 250 kHz), 0x04 pulse 1E6, 0x08 when clear the
pulse/RF-off state is reset at power-on [inferred], 0x10 150 Hz internal source instead of
400 Hz, 0x20 DC-coupled external AM allowed, 0x40 output level below 100 kHz supported, 0x80
audio generator 1E2 (DSP), 0x100 pager encoder 1EP (DSP). **1E5 and 1EA are not in this word**:
1E5 is read from a hardware ID line and 1EA is `config_cal[4]` ≥ +16.01. The reference 8648C reads
**99 = 0x63**. The motherboard utility's model bases (A 0x22, B/C 0x23, D 0x61, newer B/C +0x3E)
would write 97 to that unit, clearing bit 0x02 (only the default breakpoints change).

`*OPT?` always returns six comma-terminated fields (name or 0): HIGH STABILITY REF, PULSE
MODULATION, HIGH POWER, 150 HZ MODULATION, AUDIO GENERATOR, PAGER ENCODER.

### Other read-only queries ✔

| Query | Reply (8648C) |
|---|---|
| `SERV:BOARDID? MOTHER_BD` | `"0314nnnnn\x01"`: A3 part suffix 0314, then the board serial |
| `SERV:BOARDID? ATTEN_BD` | `"0011nnnnn\x01"`: A11 attenuator part 0011, then the board serial (not on 8648A) |
| `SYST:LANG?` | `"scpi"` |
| `DIAG:LATCH:SEL "<name>"` then `DIAG:LATCH:VAL?` | reads a hardware latch/DAC (the select only chooses; not verified live) |

### Write / service commands (expert only, NEVER without explicit consent)

| Command | Effect |
|---|---|
| `SERV:PRODUCTION:CAL:BEGIN` … `SERV:PRODUCTION:CAL <array>,<i>,<value>` … `SERV:PRODUCTION:CAL:END` | stage new array values |
| `SERV:PRODUCTION:CAL:STORE <group>` | **commit to calibration EEPROM.** B.04.08 groups (18): `ATN_COMP_CAL`, `CONFIG2_CAL`, `CONFIG_CAL`, `DSP_CAL`, `FEXTLVL_DATA`, `FM_SENS_KV`, `FM_SENS_MULT`, `GEN_LOSS_CAL`, `MOD_DAC`, `OUTLVL_DATA`, `OUT_LF_DATA`, `OUT_LF_LOSS`, `OUT_LOSS`, `OUT_PRE_PWR`, `OUT_TEMP_CAL`, `OUT_TUNE_CAL`, `TC_COEFF_CAL`, `TIMEBASE`. The array → group map is `RESTORE_GROUP` in the Appendix F tool |
| `SERV:PRODUCTION:BOARDID <board>,"<id>"` | rewrite an assembly ID |
| `SERV:PRODUCTION:INSTRUMENT:MODEL "HP8648x"` / `:SERNUM "<sn>"` | rewrite the identity |
| `SERV:PRODUCTION:MEM:SCRATCH` | initialise (erase) scratch/state memory |
| `SERV:PRODUCTION:PUP` | executes a 68000 RESET: warm reboot (used after STORE) |
| `CAL:DCFM` | documented. Stores the DC-FM offset |
| `DIAG:LATCH:VAL #H<hex>` | raw latch/DAC write (volatile; can drive hardware out of range) |
| `SERV:PRODUCTION:MEM:BYTE\|WORD\|LONG #H<addr>,<value>` | raw memory write, no checks. The queries read memory (B.04.08: `#H` address only); an odd-address WORD/LONG or unmapped read halts the firmware |
| Holding `+/−` at power-on | rewrites every cal file with defaults |
| Holding SAV at power-on | rewrites Config2, Out LF Lvl and LF Atten EEPROM files from RAM when their checksums differ |
| `DIAG:BLOCK:DSP:RESET`, `:DSP:MOD:ABORT`, `:DSP:PATH LPF_LF\|LPF_HF\|THRU\|OFF`, `:DSP:MOD:SIN f,amp`, `:DSP:MOD:OFFSET n`, `:DSP:CAL:SETTO g,o,g,o`, `:DSP:CAL:FSK …` | 1E2/1EP DSP control (volatile) |
| `DIAG:BLOCK:SG:SYNT:CWF <f>` | set the synthesizer directly (1EP FSK cal) |
| `SERV:PRODUCTION:DISP:FILL` / `:CLEAR` | display test pattern |

Latch names used by the adjustments: `out_carrier_level_DAC`, `freq_ext_level_DAC`,
`refs_DAC_coarse`, `refs_DAC_fine`, `refs_tbase_select`, `out_service_mux`, `out_ALC_bw_cntl`,
`fext_service_level_DAC`, `fext_service_mux`, `atten_4GHz_rpp_reset`,
`atten_4GHz_am_mod_select`, `fext_ALC_state`, `modist_mod_range_DAC`, `gsyn_sdfm_FM_level_DAC`.

The service DLLs also contain ESG commands (`:SOURCE:RADIO:*`, `BURST`, `ARB`, `DIAG:BLOCK:IQCAL?`,
`SERV:PROD:CARD:DATA?`, `DIAG:BLOC:LNF:AUTO`, `SOUR:AM:WID`) from shared code. **They are not
8648 commands; do not send them.**

### Firmware

The firmware (68000, Objective-C) lives in ROMs on the **A3A1 memory board**. It can be read over
GPIB, read-only, with `SERV:PRODUCTION:MEM:LONG? #H<addr>` (B.04.08), 0x000000–0x07FFFF, using the
read loop in Appendix F. There is no command to load firmware. `DIAG:BLOCk:DSP:STATus?` is a single latch read;
`:TEST?` has no board-presence check (no write or halt path found; untried on a non-DSP unit).

## Appendix D: 8648 Service Support Software

### Host and setup

EPSG090522 rev A7.0 ("7.01") is 16-bit Windows software. The test executive and the motherboard
utility talk to the bus through HP SICL (`iolib_32.dll` → `sicl32.dll`), with the GPIB card as
SICL interface `hpib7` by default. It needs a period Windows PC with HP/Agilent SICL, or on
64-bit Windows a 16-bit compatibility layer and a 32-bit SICL; no installer is included here.

* Install into a short 8.3-safe path (no spaces, at most 8 characters per folder name).
* Keep a GPIB transaction log during adjustments (a bus analyser, or a logging SICL/VISA layer):
  it is the record of what was written to the instrument.
* Datapack points are gated by the DUT's `*IDN?`/`*OPT?` (per-model option bit tables).
* `Ete.ini` holds your test-equipment list; the program edits it in Admin mode.

### Running

| Program | Launch | Login |
|---|---|---|
| Test executive | `testexec.exe` (Start menu "8648 Service Software") | `User` / `User` runs tests; `Admin` / `Falcon` also edits test equipment, drivers and datapacks (case-sensitive; publicly documented) |
| Motherboard Repair Utility | Start menu entry | **Cancel** at the password = read-only view (auto-reads serial, model, options, board IDs). Password `8648` enables **Send Data** |

Flow: DUT Selection (family 8648, model, serial, GPIB address), then Select Test Equipment and
Tests, then a Save As log file (`HP8648\Log\*.log` under the install folder), then Run / Stop / Restart /
Next Test / Rerun / Abort.
In Admin mode, enter every instrument first under **File ▸ Test Equipment**: model, serial,
GPIB address, cal due date and trace number. A power sensor must use GPIB address **−1** and
needs its cal-factor table (CAL DATA: frequency in MHz / cal factor in %).

> ⚠ **Never press Send Data in the Motherboard Utility unless the A3 motherboard has really
> been replaced.** Send Data erases the scratch memory and rewrites CONFIG_CAL/CONFIG2_CAL,
> OUT_PRE_PWR, the board IDs, model and serial. It also resets GEN_LOSS/OUT_LOSS/OUT_LF_LOSS and
> the level tables to defaults, so every adjustment must then be re-run.
> On a stock unit it can also clear configuration bits the utility doesn't know about. Example: an
> 8648C reads `CONFIG_CAL,2 = 99` (0x63); the utility would write 97 (0x61).
> Take a backup first with the Appendix F tool (`backup`). It can be put back with `restore`.

### Tests available

| Test (DLL) | Description | Models | Required test equipment |
|---|---|---|---|
| AAMLVL | AM Level and Distortion | A | DVM 3458A, function gen 33120A, J31 test-point extender |
| AAMLVL05 | AM Level | B/C/D | DVM, function gen, J31 extender |
| AAMLVLFE | AM Level: FE | B/C/D | DVM, function gen, J31 extender |
| AAMMOD | AM Modulator | A | measuring receiver 8902A, audio analyzer 8903B, function gen, DVM, J31 |
| AAUDPATH | Motherboard Audio Path | all | function gen, DVM, measuring receiver |
| ADCFM | DCFM | all | none |
| ADET_OFS | Predistortion and Detector Offset | B/C/D | power meter 438A + sensor 8482A |
| AOMDETOF | Detector Offset | A | power meter + sensor |
| AOM_LVL | Output Level | A | power meter + sensor |
| AFE_LVL | Output Level: FE | B/C/D | power meter + sensor |
| APRE_LVL | Prelevel | B/C/D | power meter + sensor |
| AOMLLVL | LF Output Level (9–100 kHz) | B/C/D (not early B/C) | DVM + 50 Ω feedthrough |
| ALF_PLA | LF Power Level Accuracy | B/C/D (not early B/C) | DVM, spectrum analyzer 8560E/8563E, 6 dB pad, feedthrough |
| AHF_PLA | HF Power Level Accuracy | all | power meter + sensor, spectrum analyzer, LF amp 8447D, HF amp 8449B, 6 dB pad |
| ATBASE | Time Base DAC | all | spectrum analyzer + 10 MHz primary standard |
| AAUDENC | Audio Generator | 1E2/1EP | DVM |
| AFSK | FSK Deviation | A 1EP | VSA 89441A |
| APG_ENC | Filter Path | A 1EP | VSA 89441A |
| PHF_PLA | Power Level Accuracy (performance test) | all | as AHF_PLA |

Default GPIB addresses expected by the drivers: 33120A=10, 3458A=22, 438A=13, 53131A/53132A=3,
8560E/8563E=18, 8663A=19, 8902A=14, 8903A/B=28, 8904A=26, 89441A=99 (set your own),
power sensor=−1, DUT 8648=19 (clashes with the 8663A default, so change one of them).

Adjustments that applied only before serial prefix 3847A/3847U (pot-based output/FE modules):
AM Level & Distortion, AM Level, Detector Offset, AM Level: FE and Predistortion & Detector
Offset. The software asks whether pots are present.

Warm-up: DUT and all test equipment for **≥ 45 min** before adjusting.

### Manual adjustments (no software)

* **Internal reference oscillator**:
  1. Power off and set the rear **TIMEBASE ADJ** switch to 1.
  2. Power on and follow the display prompts, using the knobs, until the counter (locked to a
     primary standard) reads 100 MHz ± 1 Hz at the RF output.
  3. Power off and set the switch back to 0.
  Equivalent to the automated ATBASE (writes cal array `timebase`, 2 elements = coarse/fine DAC).
* **Pager encoder timebase (1EP)**:
  1. Select FM, ENCODER, FORMAT=SERVICE, CALIBRATION FSK=3200/2 and START.
  2. Trim the "TIMEBASE ADJUST 1EP" capacitor until MOD OUT reads 1600 Hz ± 0.0016 Hz.

### Which adjustments after which repair (service guide table 5-2, abridged)

A3 motherboard: all (after the motherboard utility). A3A1 memory (ROM) board: none.
A3BT1 battery: DCFM. A4 reference: Time Base DAC. A5 synth: DCFM and FSK Deviation (1EP).
A6 output: Output Level/Prelevel family + AM + HF PLA. A7/A11 attenuator: HF PLA (+ LF PLA).
A10 FE: Output Level: FE, AM Level: FE, Predistortion & Det Offset.
A14/A30: Audio Generator (+ Filter Path, FSK for 1EP).

### Under the hood (for debugging)

`testexec.exe` → test DLL (`HP8648\Adj\a*.dll`, `Perf\phf_pla.dll`) driven by a datapack
(`HP8648\DP\*.00n`), then the equipment drivers (`DRIVERS\drv*.dll`) and the DUT driver
`drv8648.dll`, then `io_sicl.dll` → `BIN\iolib_32.dll` → `sicl32.dll`.
Configuration lives in `Testexec.ini`, `Models.ini`, `Devices.ini`, `Dut.ini`, `Ete.ini` (your
equipment list), `HP8648\Adjust.ini` and `HP8648\Test.ini`. Setting the environment variable
`HSI_DEBUG_ETE=1` puts the original `iolib_32` into its "SICL I/O is in debug mode" simulation.

## Appendix E: Specifications (service guide chapter 4, condensed)

Specifications are warranted from 0 to 50 °C after a 30 min warm-up. Performance below 250 kHz
is typical. *Italic*/"typ" values are supplemental (not warranted).

### Frequency
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

### Output
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

### Spectral purity
* Harmonics < −30 dBc at ≤ +4 dBm.
* Non-harmonics (≥ 5 kHz offset, ≤ +4 dBm): < −55 dBc (< 249 MHz), −60 (< 1001), −54 (< 2001),
  −48 (≤ 4000).
* Residual FM (CCITT rms): < 7 Hz (< 249 MHz), 4 Hz (< 501), 7 Hz (< 1001), 14 Hz (< 2001),
  28 Hz (≤ 4000).
* SSB phase noise at 20 kHz (typ): −120 dBc/Hz (500 MHz), −116 (1 GHz), −110 (2 GHz), −106 (3 GHz),
  −104 (4 GHz).

### FM
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

### PM
* Deviation: 10 rad (< 249 MHz), 5 (< 501), 10 (< 1001), 20 (< 2001), 40 (≤ 4000).
* Resolution 0.01 rad (< 2001 MHz), 0.02 rad above.
* Accuracy (typ): ±3 % ± 0.05 rad (< 1001 MHz), ±5 % ± 0.1 rad (< 2001), ±5 % ± 0.2 rad.
* Rates: internal 400 Hz/1 kHz; 1E2 20 Hz–10 kHz; external 20 Hz–10 kHz.
* Distortion < 1 % at ≥ 3/6/12 rad.

### AM (not specified below 1.5 MHz; typical above 1001 MHz)
* 0–100 % (output ≤ +4 dBm), resolution 0.1 %.
* Accuracy ±5 % of setting ± 1.5 % (1 kHz, < 70 % depth, 25 ± 5 °C).
* Rates: internal 400 Hz/1 kHz; 1E2 10 Hz–20 kHz; ext DC dc–25 kHz; AC 1 Hz–25 kHz.
* Distortion:

  | Depth | 8648A | 8648B/C/D |
  |---|---|---|
  | 30 % AM | < 2 % | < 2 % |
  | 90 % AM | < 3 % | – |
  | 70 % AM | – | < 3 % |

### Modulation source and I/O
* MOD INPUT/OUTPUT front BNC, 1 Vpk into 600 Ω for full scale. A HI/LO indicator works up to 10 kHz.
* **1E2:** sine 10 Hz–20 kHz; square/triangle/saw 100 Hz–2 kHz. Accuracy ±0.01 % typ,
  resolution 1 Hz.
* **1E6 pulse:** rise/fall < 10 ns, on/off > 80 dB (< 2 GHz) / > 70 dB, 10 MHz max rate, TTL input.
* **1EP:** POCSAG 512/1200/2400 bps; FLEX/FLEX-TD 1600/3200 (2FSK), 3200/6400 (4FSK).
  FSK deviation accuracy ±60 Hz at 4.8 kHz. Data-rate accuracy ±5 ppm.

### Remote / general
* HP-IB: SH1 AH1 T6 TE0 L4 LE0 SR1 RL1 PP0 DC1 DT0 C0 E2. SCPI 1992.0 and 8656B/8657 code compatibility.
* 300 storage registers (10 sequences × 30); 1EP has 70.
* Power 90–264 V, 48–440 Hz, 170 VA. Weight 7 kg (A) / 8.5 kg (B/C/D). Size 165 × 330 × 368 mm.

## Appendix F: Calibration backup tool and ROM reader

Save the following as `hp8648_calbackup.py`. It needs Python 3.8+ and PyVISA with a VISA backend. `backup` and `compare` only read; `restore` is a dry run unless `--apply` is given. Every safety rule in the docstring is enforced in code before anything reaches the bus.

```python
#!/usr/bin/env python3
"""
hp8648_calbackup.py - backup, compare and (guarded) restore of an HP 8648A/B/C/D's
calibration arrays over GPIB (PyVISA).

SAFETY DESIGN
-------------
Two choke points; nothing reaches the instrument except through them.

`Bus.send()` (backup, compare, verification reads) is READ-ONLY. It refuses, before
touching the bus, anything that is not
  * one of the allow-listed queries: *IDN?  *OPT?  SYST:ERR?  SERV:BOARDID? <board>
  * SERV:PRODUCTION:CAL? <array>,<index> where <array> is listed in KNOWN_ARRAYS
    and 0 <= <index> < its element count, and <array> is not an option-hardware array.

`WriteBus.write()` (restore only) additionally allows exactly four write forms:
    SERV:PRODUCTION:CAL:BEGIN
    SERV:PRODUCTION:CAL <array>,<index>,<number>   array in RESTORE_GROUP, index in range
    SERV:PRODUCTION:CAL:END
    SERV:PRODUCTION:CAL:STORE <group>              group in RESTORE_GROUP's values
It can never emit PUP, MEM:*, MEM:SCRATCH, BOARDID or INSTRUMENT writes, DIAG:LATCH,
*RST or anything else. CONFIG_CAL / CONFIG2_CAL writes also need --include-config.

Reads are NOT automatically harmless. On an 8648C (fw B.04.08), 2026-10-05:
  * reading an option array whose hardware is not fitted (dsp_2fsk_cal,0 without 1EP)
    -> "Fatal firmware error";
  * reading one index past the end (outllvl_frq,6)
    -> "FATAL FIRMWARE ERROR: assertion failure 597: h:FileMgr.m".
Both needed a power cycle (calibration was verified unchanged). Hence the exact counts in
KNOWN_ARRAYS; never guess names or lengths.

RESTORE (writes calibration EEPROM; get the user's approval before using --apply)
------------------------------------------------------------------------------------
  1. Only to the SAME instrument: model, serial and firmware must match the backup.
  2. A fresh full backup is taken first and saved ("pre-restore").
  3. Only elements whose current value differs from the backup are written (with --all, or the
     menu's default, every element of every writable array is written). Frequency-list
     arrays (*_frq) have no firmware write routine and are never written; fm_acfm_dac has no
     STORE group and is never written; option DSP arrays are never written.
  4. Per STORE group, in the order the HP service software uses:
       CAL:BEGIN, CAL <array>,<i>,<v> ..., CAL:END,
       then every element of the group's arrays is read back and must equal the backup,
       and the error queue must be empty, and ONLY THEN CAL:STORE <group>.
     If a check fails the group is NOT stored and the restore stops. The written values are
     then only in the instrument's working copy [inferred from the firmware: CAL writes go to
     the RAM image, STORE copies it to the board EEPROM]; power-cycle to discard them, then
     run a backup and compare it with the pre-restore one.
  5. A final backup is taken and compared with the target.
Without --apply nothing is written: the plan is printed (dry run).

USAGE
    python hp8648_calbackup.py backup  --addr GPIB0::19::INSTR [--out DIR] [--arrays FILE]
    python hp8648_calbackup.py compare a.json b.json        (exit status 1 if they differ)
    python hp8648_calbackup.py restore backup.json [--addr ...] [--out DIR]   (dry run)
    python hp8648_calbackup.py restore backup.json --apply [--all] [--include-config]
Output: hp8648_<serial>_<timestamp>.json/.csv/.log in --out (default: cwd).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

FIXED = {"*IDN?", "*OPT?", "SYST:ERR?"}
BOARD_Q = re.compile(r"^SERV:BOARDID\? [A-Z][A-Z0-9_]{0,20}\Z")
CAL_Q = re.compile(r"^SERV:PRODUCTION:CAL\? ([A-Za-z][A-Za-z0-9_]{0,11}),(\d{1,4})\Z")
KNOWN_BOARDS = ["MOTHER_BD", "OUTPUT_BD", "SYNTH_BD", "REF_BD", "ATTEN_BD", "FREQ_EXT_BD"]
# Option-hardware arrays (1EP pager encoder / 1E2 audio generator DSP). fm_sens_* are standard.
OPTION_ARRAY = re.compile(r"(^dsp_|fsk|pag|enc|sin_cal)", re.I)

# Writable array -> STORE group, from fw B.04.08: the per-array write routine (table 0x2695A)
# writes internal EEPROM file N, and :STORe <group> commits file N (group table 0x4AC66,
# file table 0x43F98).
_DB = ["0db", "10db", "20db", "30db", "40db", "50db", "60db", "70db", "80db", "90db",
       "100db", "110db", "120db", "130db"]
RESTORE_GROUP = {
    "out_tune_dac": "OUT_TUNE_CAL",
    "out_lvl_gain": "OUTLVL_DATA", "out_lvl_ofs": "OUTLVL_DATA",
    "out_pre_pwr": "OUT_PRE_PWR",
    "fextlvl_gain": "FEXTLVL_DATA", "fextlvl_ofs": "FEXTLVL_DATA",
    "fm_sens_sgn": "FM_SENS_KV", "fm_sens_mult": "FM_SENS_MULT",
    "timebase": "TIMEBASE",
    "out_temp_cal": "OUT_TEMP_CAL",
    "gen_loss_cal": "GEN_LOSS_CAL",
    "config_cal": "CONFIG_CAL", "config2_cal": "CONFIG2_CAL",
    "atn_comp_cal": "ATN_COMP_CAL",
    "outllvl_gain": "OUT_LF_DATA", "outllvl_ofs": "OUT_LF_DATA",
}
RESTORE_GROUP.update({"out_" + d: "OUT_LOSS" for d in _DB})
RESTORE_GROUP.update({"outl_" + d: "OUT_LF_LOSS" for d in _DB})
RESTORE_GROUP.update({"mod_%s_%s" % (m, s): "MOD_DAC"
                      for m in ("fm", "pm", "am") for s in ("1khz", "400hz", "extdc", "extac")})
RESTORE_GROUP.update({t: "TC_COEFF_CAL" for t in
                      ("tc_thru_path", "tc_10_40db", "tc_50_70db", "tc_80_100db", "tc_110_130db")})
CONFIG_GROUPS = {"CONFIG_CAL", "CONFIG2_CAL"}
NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([Ee][+-]?\d{1,3})?\Z")
CAL_W = re.compile(r"^SERV:PRODUCTION:CAL ([a-z][a-z0-9_]{0,11}),(\d{1,4}),(\S{1,24})\Z")
STORE_W = re.compile(r"^SERV:PRODUCTION:CAL:STORE ([A-Z][A-Z0-9_]{0,15})\Z")
TXN_W = {"SERV:PRODUCTION:CAL:BEGIN", "SERV:PRODUCTION:CAL:END"}


class InstrumentUnresponsive(RuntimeError):
    pass


class Bus:
    """`inst` is anything with query()/clear()/close() (a PyVISA resource in practice).
    `limits` maps lower-case array name -> number of elements that may be read."""

    def __init__(self, inst, log, limits, allow_option=False):
        self.inst, self.log, self.limits, self.allow_option = inst, log, limits, allow_option
        self.n = 0

    def _log(self, s):
        self.log.write("%s %s\n" % (dt.datetime.now().isoformat(sep=" ", timespec="milliseconds"), s))

    def check(self, q):
        """Raise PermissionError unless q is safe to send."""
        if q in FIXED or BOARD_Q.match(q):
            return
        m = CAL_Q.match(q)
        if not m:
            raise PermissionError("refusing non-allow-listed command: %r" % q)
        name, idx = m.group(1).lower(), int(m.group(2))
        if OPTION_ARRAY.search(name) and not self.allow_option:
            raise PermissionError("option-hardware array %r is blocked (see --allow-option-arrays)" % name)
        if idx >= self.limits.get(name, 0):
            raise PermissionError("%s[%d] is outside the known length (%s); reading past the end can "
                                  "halt the firmware" % (name, idx, self.limits.get(name, "unknown array")))

    def send(self, q):
        """Send a safe query. Returns the reply, or None if the instrument gave none."""
        self.check(q)
        self.n += 1
        try:
            r = self.inst.query(q).strip()
            self._log("Q %s -> %s" % (q, r))
            return r
        except Exception as e:  # timeout: instrument produced no reply
            self._log("Q %s -> (no reply: %s)" % (q, type(e).__name__))
            try:
                self.inst.clear()      # IEEE-488 device clear (SDC)
            except Exception as e2:
                self._log("device clear failed: %s -> instrument unresponsive" % e2)
                raise InstrumentUnresponsive("no response to device clear after %r" % q)
            return None

    def errors(self):
        out = []
        for _ in range(20):
            e = self.send("SYST:ERR?")
            if e is None or e.startswith("+0") or e.startswith("0,"):
                break
            out.append(e)
        return out


class WriteBus(Bus):
    """Bus plus the four calibration write forms used by restore. Nothing else is writable."""

    def __init__(self, inst, log, limits, include_config=False):
        Bus.__init__(self, inst, log, limits, allow_option=False)
        self.include_config = include_config

    def check_write(self, cmd):
        if cmd in TXN_W:
            return
        m = STORE_W.match(cmd)
        if m:
            g = m.group(1)
            if g not in set(RESTORE_GROUP.values()):
                raise PermissionError("STORE group %r is not restorable" % g)
            if g in CONFIG_GROUPS and not self.include_config:
                raise PermissionError("STORE %s needs --include-config" % g)
            return
        m = CAL_W.match(cmd)
        if not m:
            raise PermissionError("refusing non-allow-listed write: %r" % cmd)
        name, idx, val = m.group(1), int(m.group(2)), m.group(3)
        g = RESTORE_GROUP.get(name)
        if g is None:
            raise PermissionError("array %r is not restorable" % name)
        if g in CONFIG_GROUPS and not self.include_config:
            raise PermissionError("writing %s needs --include-config" % name)
        if idx >= self.limits.get(name, 0):
            raise PermissionError("%s[%d] is outside the known length" % (name, idx))
        if not NUMBER.match(val):
            raise PermissionError("value %r for %s[%d] is not a plain number" % (val, name, idx))

    def write(self, cmd):
        self.check_write(cmd)
        self.n += 1
        self._log("W %s" % cmd)
        self.inst.write(cmd)


def ident(bus):
    idn = bus.send("*IDN?")
    opt = bus.send("*OPT?")
    boards = {b: bus.send("SERV:BOARDID? %s" % b) for b in KNOWN_BOARDS}
    bus.errors()
    parts = [p.strip() for p in (idn or "").split(",")]
    return {"idn": idn, "opt": opt, "boards": boards,
            "model": parts[1] if len(parts) > 1 else "", "serial": parts[2] if len(parts) > 2 else "",
            "firmware": parts[3] if len(parts) > 3 else ""}


def dump_array(bus, name, count):
    """Read elements 0..count-1. Returns None if the array does not exist on this instrument."""
    vals = []
    for i in range(count):
        r = bus.send("SERV:PRODUCTION:CAL? %s,%d" % (name, i))
        if r is None:
            errs = bus.errors()
            if i == 0 and errs and all(("-224" in e or "-420" in e) for e in errs):
                return None
            raise InstrumentUnresponsive("unexpected failure reading %s[%d]: %s" % (name, i, errs))
        vals.append(r)
    return vals


KNOWN_ARRAYS = """\
# Calibration arrays read by 'backup' and their EXACT element counts.
# The tool reads indices 0..count-1 and NEVER probes past the end:
#   2026-10-05: reading outllvl_frq index 6 (one past the end) on an 8648C fw B.04.08 halted the
#   firmware: "FATAL FIRMWARE ERROR: assertion failure 597: h:FileMgr.m,v 1.18 96/01/20".
#   Power cycle recovered it; calibration unchanged.  Some arrays return -224 instead, but you
#   cannot know which in advance.
# Columns: name  count_BCD  count_A   (0 = array not present on that model; '?' = unverified)
# Counts checked against fw B.04.08's read routines.
# Sources: [C] read on a reference 8648C fw B.04.08; [Y] YO4HFU READ_v1.5.py log, 8648B fw B.04.09;
#          8648A counts from YO4HFU's script (model A branch), not verified on hardware.
config_cal      5    5     # [C][Y]
config2_cal     1    1     # [C][Y]
out_pre_pwr     7    7     # [C][Y]
gen_loss_frq    34   34    # [C] fw B.04.08 limit 34 on all models (read FUN_000314cc idx<0x22); 8648C read 34
gen_loss_cal    34   34    # [C] fw B.04.08 limit 34 on all models (read FUN_00031704 idx<0x22); 8648C read 34
out_loss_frq    22   34    # [C][Y]
out_0db         22   34
out_10db        22   34
out_20db        22   34
out_30db        22   34
out_40db        22   34
out_50db        22   34
out_60db        22   34
out_70db        22   34
out_80db        22   34
out_90db        22   34
out_100db       22   34
out_110db       22   34
out_120db       22   34
out_130db       22   34
outlloss_frq    6    6     # [C] fw B.04.08 limit 6 (read FUN_0002eb26); 8648C answered 6
outl_0db        6    6
outl_10db       6    6
outl_20db       6    6
outl_30db       6    6
outl_40db       6    6
outl_50db       6    6
outl_60db       6    6
outl_70db       6    6
outl_80db       6    6
outl_90db       6    6
outl_100db      6    6
outl_110db      6    6
outl_120db      6    6
outl_130db      6    6
atn_comp_frq    106  0     # B/C/D only
atn_comp_cal    106  0
fextlvl_frq     108  0     # B/C/D only (A10 frequency extension)
fextlvl_gain    108  0
fextlvl_ofs     108  0
fm_acfm_dac     1    0
out_lvl_frq     32   32
out_lvl_gain    32   32
out_lvl_ofs     32   32
outllvl_frq     6    6     # index 6 CRASHES the firmware: its read routine has NO range check
outllvl_gain    6    6
outllvl_ofs     6    6
mod_fm_1khz     4    4
mod_fm_400hz    4    4
mod_fm_extdc    4    4
mod_fm_extac    4    4
mod_pm_1khz     4    4
mod_pm_400hz    4    4
mod_pm_extdc    4    4
mod_pm_extac    4    4
mod_am_1khz     2    2
mod_am_400hz    2    2
mod_am_extdc    2    2
mod_am_extac    2    2
fm_sens_frq     44   44    # [Y]
fm_sens_sgn     44   44    # [Y]
fm_sens_mult    1    1     # [Y]
out_tune_frq    25   25    # [Y]
out_tune_dac    25   25    # [Y]
timebase        2    2     # [C][Y]
out_temp_cal    1    1     # [Y]
tc_thru_path    3    3     # [Y]
tc_10_40db      3    3     # [Y]
tc_50_70db      3    3     # [Y]
tc_80_100db     3    3     # [Y]
tc_110_130db    3    3     # [Y]

# Option 1EP (pager/DSP) arrays. B.04.08 ACCEPTS these names (ROM name table 0x4acba), but they
# are deliberately NOT read: on a unit without 1EP they crash the firmware (dsp_2fsk_cal did so,
# 2026-10-05). Listed here as known-but-excluded so the tool never probes them.
# dsp_sin_cal    ?    ?    # 1EP only - DO NOT READ without the option fitted
# dsp_2fsk_cal   ?    ?    # 1EP only - DO NOT READ
# dsp_4fsk_cal   ?    ?    # 1EP only - DO NOT READ
"""


def load_known(path=None):
    """Array table rows: name count_BCD count_A  [# comment]. Default: KNOWN_ARRAYS above."""
    rows = []
    text = open(path).read() if path else KNOWN_ARRAYS
    if True:
        for line in text.splitlines():
            w = line.split("#")[0].split()
            if len(w) >= 3:
                rows.append((w[0].lower(), int(w[1]), int(w[2])))
    return rows


def limits_for(table, model):
    col = 2 if (model or "").upper() == "8648A" else 1
    return {row[0]: row[col] for row in table}


def read_all(bus, out=print):
    """Read every known array. Returns (data, missing, aborted)."""
    data, missing, aborted = {}, [], None
    try:
        for name, cnt in bus.limits.items():
            if cnt <= 0:
                continue
            vals = dump_array(bus, name, cnt)
            if vals is None:
                missing.append(name)
                out("  %-28s (not present)" % name)
            else:
                data[name] = vals
                out("  %-28s %4d elements" % (name, len(vals)))
    except InstrumentUnresponsive as e:
        aborted = str(e)
        out("\n*** ABORTED: %s\n*** Check the instrument front panel; a power cycle may be needed." % e)
    return data, missing, aborted


def save_doc(doc, out_dir, serial, stamp, tag=""):
    base = os.path.join(out_dir, "hp8648_%s_%s%s" % (serial or "unknown", stamp, tag))
    with open(base + ".json", "w") as f:
        json.dump(doc, f, indent=1)
    with open(base + ".csv", "w") as f:
        f.write("array,index,value\n")
        for n, vals in doc["arrays"].items():
            for i, v in enumerate(vals):
                f.write("%s,%d,%s\n" % (n, i, v))
    return base


def backup_doc(bus, table, out=print, note="Read-only backup."):
    """Identity, all arrays, identity again. Sets bus.limits from the model."""
    bus.limits = {}
    info = ident(bus)
    out("Instrument: %s" % info["idn"])
    if "8648" not in (info["idn"] or ""):
        raise SystemExit("not an 8648: %r" % info["idn"])
    bus.limits = limits_for(table, info["model"])
    data, missing, aborted = read_all(bus, out)
    info2 = None if aborted else ident(bus)
    return {"tool": "hp8648_calbackup.py", "created": dt.datetime.now().isoformat(timespec="seconds"),
            "instrument": info, "instrument_after": info2, "arrays": data, "not_present": missing,
            "aborted": aborted,
            "note": "Values are the raw SCPI replies of SERV:PRODUCTION:CAL? <array>,<index>. " + note}


def open_inst(a):
    import pyvisa
    return pyvisa.ResourceManager().open_resource(a.addr, timeout=a.timeout,
                                                  read_termination="\n", write_termination="\n")


def give_back(inst):
    try:
        inst.control_ren(6)   # GTL: give the front panel back
    except Exception:
        pass


def cmd_backup(a):
    table = load_known(a.arrays)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(a.out, "hp8648_backup_%s.log" % stamp)
    inst = open_inst(a)
    with open(log_path, "a", encoding="utf-8", buffering=1) as log:   # line-buffered: survives crashes
        bus = Bus(inst, log, {}, a.allow_option_arrays)
        try:
            doc = backup_doc(bus, table)
        finally:
            give_back(inst)
            inst.close()
    base = save_doc(doc, a.out, doc["instrument"].get("serial"), stamp)
    os.replace(log_path, base + ".log")
    print("Saved %s.json/.csv/.log  (%d transactions; identity unchanged: %s)"
          % (base, bus.n, doc["instrument"] == doc["instrument_after"]))
    return 1 if doc["aborted"] else 0


def compare(A, B, out=print):
    """Print differences between two backup documents; return the number of differences."""
    diffs = 0
    ia, ib = A["instrument"], B["instrument"]
    for k in ("model", "serial", "firmware", "opt"):
        if ia.get(k) != ib.get(k):
            diffs += 1
            out("instrument %-8s %s -> %s" % (k, ia.get(k), ib.get(k)))
    ba, bb = ia.get("boards") or {}, ib.get("boards") or {}
    for k in sorted(set(ba) & set(bb)):        # older backups read fewer boards
        if ba[k] != bb[k]:
            diffs += 1
            out("board %-12s %s -> %s" % (k, ba[k], bb[k]))
    for doc, tag in ((A, "A"), (B, "B")):
        if doc.get("aborted"):
            diffs += 1
            out("WARNING: backup %s was aborted (%s); it is incomplete" % (tag, doc["aborted"]))
    for n in sorted(set(A["arrays"]) | set(B["arrays"])):
        x, y = A["arrays"].get(n), B["arrays"].get(n)
        if x == y:
            continue
        diffs += 1
        if x is None or y is None:
            out("%-24s only in %s" % (n, "A" if y is None else "B"))
            continue
        for i in range(max(len(x), len(y))):
            u, v = (x[i] if i < len(x) else None), (y[i] if i < len(y) else None)
            if u != v:
                out("%-24s [%3d] %s -> %s" % (n, i, u, v))
    out("identical" if not diffs else "%d differences" % diffs)
    return diffs


def cmd_compare(a):
    with open(a.a) as fa, open(a.b) as fb:
        return 1 if compare(json.load(fa), json.load(fb)) else 0


# ------------------------------------------------------------------ restore

def same_value(u, v):
    """Two SCPI number replies are equal if they parse to the same float."""
    try:
        return float(u) == float(v)
    except (TypeError, ValueError):
        return u == v


def plan_restore(target, current, include_config=False, full=False):
    """Work out what a restore would write. With full=True every element of every writable
    array is written, not only the ones that differ.

    Returns (plan, skipped, problems):
      plan     {group: [(array, index, value), ...]}  elements that differ and can be written
      skipped  [text]  differences that restore will not touch (read-only or excluded arrays)
      problems [text]  reasons the restore must not run at all"""
    problems, skipped, plan = [], [], {}
    ti, ci = target.get("instrument") or {}, current.get("instrument") or {}
    for k in ("model", "serial", "firmware"):
        if not ti.get(k) or ti.get(k) != ci.get(k):
            problems.append("%s differs: backup %r, instrument %r" % (k, ti.get(k), ci.get(k)))
    for doc, tag in ((target, "backup"), (current, "pre-restore read")):
        if doc.get("aborted"):
            problems.append("%s is incomplete (%s)" % (tag, doc["aborted"]))
    tb, cb_ = ti.get("boards") or {}, ci.get("boards") or {}
    for b in sorted(set(tb) & set(cb_)):
        if tb[b] != cb_[b]:
            problems.append("board %s ID differs (%s -> %s): a board was changed; "
                            "its calibration must be redone, not restored" % (b, tb[b], cb_[b]))
    for name in sorted(set(target["arrays"]) | set(current["arrays"])):
        t, c = target["arrays"].get(name), current["arrays"].get(name)
        if t is None or c is None:
            problems.append("array %s is only in the %s" % (name, "instrument" if t is None else "backup"))
            continue
        if len(t) != len(c):
            problems.append("array %s has %d elements in the backup, %d now" % (name, len(t), len(c)))
            continue
        diff = [(i, t[i]) for i in range(len(t)) if not same_value(t[i], c[i])]
        g = RESTORE_GROUP.get(name)
        if full and g is not None:
            diff = list(enumerate(t))
        if not diff:
            continue
        if g is None:
            skipped.append("%s: %d element(s) differ but this array is not writable (left as is)"
                           % (name, len(diff)))
            continue
        if g in CONFIG_GROUPS and not include_config:
            if not full or any(not same_value(t[i], c[i]) for i in range(len(t))):
                skipped.append("%s: %d element(s) differ; CONFIG data is only written with "
                               "--include-config" % (name, len(diff)))
            continue
        for i, v in diff:
            if not NUMBER.match(v):
                problems.append("%s[%d] backup value %r is not a plain number" % (name, i, v))
        plan.setdefault(g, []).extend((name, i, v) for i, v in diff)
    return plan, skipped, problems


def print_plan(plan, skipped, problems, out=print, current=None):
    for p in problems:
        out("PROBLEM: " + p)
    for s in skipped:
        out("not restored: " + s)
    if not plan:
        out("Nothing to write: every restorable element already matches the backup.")
    for g in sorted(plan):
        out("STORE group %s: %d element(s)" % (g, len(plan[g])))
        for name, i, v in plan[g]:
            same = current is not None and same_value(current["arrays"][name][i], v)
            out("    %-14s [%3d] -> %s%s" % (name, i, v, "  (unchanged)" if same else ""))


def apply_group(wbus, target, group, items, out=print):
    """Write one group, verify it, and store it only if verification passes. Returns True if stored."""
    wbus.write("SERV:PRODUCTION:CAL:BEGIN")
    for name, i, v in items:
        wbus.write("SERV:PRODUCTION:CAL %s,%d,%s" % (name, i, v))
    wbus.write("SERV:PRODUCTION:CAL:END")
    errs = wbus.errors()
    if errs:
        out("  %s: instrument reported %s; NOT stored" % (group, errs))
        return False
    for name in sorted({n for n, g in RESTORE_GROUP.items() if g == group} & set(target["arrays"])):
        now = dump_array(wbus, name, len(target["arrays"][name]))
        bad = [i for i, (u, w) in enumerate(zip(target["arrays"][name], now or [])) if not same_value(u, w)]
        if now is None or bad:
            out("  %s: read-back of %s does not match the backup at %s; NOT stored"
                % (group, name, bad[:10] if now else "(no reply)"))
            return False
    wbus.write("SERV:PRODUCTION:CAL:STORE %s" % group)
    errs = wbus.errors()
    if errs:
        out("  %s: STORE reported %s" % (group, errs))
        return False
    out("  %s: %d element(s) written, verified and stored" % (group, len(items)))
    return True


def confirm(prompt_serial, ask=None):
    s = (ask or input)("Type the instrument serial number (%s) to write its calibration: " % prompt_serial)
    return s.strip() == prompt_serial


def run_restore(inst, target, table, out_dir, apply=False, include_config=False,
                out=print, ask=None, log=None, full=False):
    """The whole restore procedure on an open instrument. Returns a process exit status."""
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log = log or open(os.path.join(out_dir, "hp8648_restore_%s.log" % stamp), "a", encoding="utf-8",
                      buffering=1)
    wbus = WriteBus(inst, log, {}, include_config)
    out("Reading the instrument's current calibration (pre-restore backup)...")
    current = backup_doc(wbus, table, out, note="Taken by restore before writing.")
    base = save_doc(current, out_dir, current["instrument"].get("serial"), stamp, "_prerestore")
    out("Saved %s.json" % base)
    plan, skipped, problems = plan_restore(target, current, include_config, full)
    print_plan(plan, skipped, problems, out, current)
    if full and plan:
        out("Full restore: %d element(s) in %d group(s), %d of them different from now."
            % (sum(len(v) for v in plan.values()), len(plan),
               sum(1 for v in plan.values() for n, i, x in v
                   if not same_value(current["arrays"][n][i], x))))
    if problems:
        out("Restore refused.")
        return 2
    if not plan:
        return 0
    if not apply:
        out("Dry run: nothing was written. (Command line: add --apply to write the groups above.)")
        return 0
    if not confirm(current["instrument"]["serial"], ask):
        out("Serial number not confirmed; nothing was written.")
        return 2
    wbus.limits = limits_for(table, current["instrument"]["model"])
    for g in sorted(plan):
        try:
            ok = apply_group(wbus, target, g, plan[g], out)
        except InstrumentUnresponsive as e:
            ok = False
            out("  %s: instrument stopped responding (%s)" % (g, e))
        if not ok:
            out("\n*** Restore stopped at group %s. Groups before it were stored. Group %s was NOT\n"
                "*** stored; its new values are only in the working copy. Power-cycle the instrument\n"
                "*** to discard them, then run a backup and compare it with %s.json." % (g, g, base))
            return 1
    out("Final check...")
    final = backup_doc(wbus, table, out, note="Taken by restore after writing.")
    fbase = save_doc(final, out_dir, final["instrument"].get("serial"), stamp, "_postrestore")
    rest, _, _ = plan_restore(target, final, include_config)
    if rest:
        out("WARNING: some elements still differ after the restore:")
        print_plan(rest, [], [], out)
        return 1
    out("Restore complete; saved %s.json. Every restorable element now matches the backup." % fbase)
    return 0


def cmd_restore(a):
    with open(a.backup) as f:
        target = json.load(f)
    table = load_known(a.arrays)
    inst = open_inst(a)
    try:
        return run_restore(inst, target, table, a.out, a.apply, a.include_config, full=a.all)
    finally:
        give_back(inst)
        inst.close()


def main(argv=None):
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("backup")
    p.add_argument("--addr", default="GPIB0::19::INSTR")
    p.add_argument("--out", default=".")
    p.add_argument("--timeout", type=int, default=1200, help="ms per query")
    p.add_argument("--arrays", help="array table file (default: the KNOWN_ARRAYS table built into this script)")
    p.add_argument("--allow-option-arrays", action="store_true",
                   help="also read 1EP/1E2 DSP arrays (ONLY if those options are fitted)")
    p = sub.add_parser("compare")
    p.add_argument("a")
    p.add_argument("b")
    p = sub.add_parser("restore", help="write a backup back to the SAME instrument (dry run by default)")
    p.add_argument("backup", help="backup .json made by this tool from this instrument")
    p.add_argument("--addr", default="GPIB0::19::INSTR")
    p.add_argument("--out", default=".")
    p.add_argument("--timeout", type=int, default=1200, help="ms per query")
    p.add_argument("--arrays", help="array table file (default: the KNOWN_ARRAYS table built into this script)")
    p.add_argument("--apply", action="store_true", help="actually write (asks for the serial number)")
    p.add_argument("--all", action="store_true",
                   help="write every element of every writable array, not only the ones that differ")
    p.add_argument("--include-config", action="store_true",
                   help="also restore CONFIG_CAL / CONFIG2_CAL (model, frequency range, option bits)")
    a = ap.parse_args(argv)
    return {"backup": cmd_backup, "compare": cmd_compare, "restore": cmd_restore}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
```

### ROM reader

The firmware ROMs on the A3A1 board can be read over GPIB with a read-only loop. Run it twice and compare the files before trusting a dump.

```python
import struct, pyvisa

def rom_dump(inst, start=0x000000, end=0x080000, path="hp8648_rom.bin"):
    """Read-only. Long words at multiples of 4 only; stops at the first error.
    An odd or unmapped address halts the firmware (power cycle; nothing is written)."""
    assert start % 4 == 0 and end % 4 == 0 and end > start
    with open(path, "wb") as f:
        for addr in range(start, end, 4):
            v = int(inst.query("SERV:PRODUCTION:MEM:LONG? #H%X" % addr)) & 0xFFFFFFFF
            f.write(struct.pack(">I", v))
    print(inst.query("SYST:ERR?"))

inst = pyvisa.ResourceManager().open_resource("GPIB0::19::INSTR")
inst.timeout = 2000
rom_dump(inst)          # 0x000000-0x07FFFF, about 37 minutes on B.04.08
```
