# HP 8648A/B/C/D SCPI command reference

Source: *HP 8648A/B/C/D Signal Generator Service Guide*, chapter 2 "HP-IB Programming"
(keep a local copy in `reference/manuals/`; manuals are not tracked). OCR noise has been cleaned up. Replies marked ✔ were verified on a
live 8648C (firmware B.04.08) on 2026-10-05.

Conventions: `[ ]` marks an optional node, `|` separates alternatives, and lower-case letters
may be omitted (`FREQuency` → `FREQ`). `[SOURce]` is implied on all source subsystems.
`<NRf>` is any number; `<NR1>` is an integer. Unit suffixes are listed in the SKILL.md rules.
If no suffix is given, the defaults are Hz, dBm, PCT and radians.

## IEEE 488.2 common commands

| Command | Function |
|---|---|
| `*IDN?` | `Hewlett-Packard, 8648C, 3642U01792, B.04.08` ✔ |
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

## FREQuency

| Command | *RST | Notes |
|---|---|---|
| `FREQ[:CW\|:FIXed] <NRf>[HZ\|KHZ\|MHZ\|GHZ]` / `?` | 100 MHz | 10 Hz resolution, up to 9 digits. Reply `+1.71800000000000E+009` ✔ |
| `FREQ:REFerence <NRf>` / `?` | 0 Hz | reference used when REF:STAT ON |
| `FREQ:REFerence:STATe ON\|OFF\|1\|0` / `?` | OFF | ON = frequencies entered/queried relative to the reference |

## POWer (amplitude)

| Command | *RST | Notes |
|---|---|---|
| `POW[:LEVel][:IMMediate][:AMPLitude] <NRf>[DBM\|DB\|DBUV\|DBUVEMF\|V\|MV\|UV\|MVEMF\|UVEMF]` / `?` | −136 dBm | 0.1 dB resolution; query returns dBm (or dB when REF ON) ✔. Normal short form `POW:AMPL` |
| `POW:ATTenuation:AUTO ON\|OFF\|1\|0` / `?` | ON | OFF = attenuator hold (ATTN HOLD key): ±10 dB vernier around the held range ✔ |
| `POW:REFerence <NRf>` / `?` | 0 dBm | in REF mode only DB/DBM units are allowed |
| `POW:REFerence:STATe ON\|OFF` / `?` | OFF | |

Levels above +10 dBm (above +13 dBm for B/C/D ≤2.5 GHz) are "unspecified". They set
`STAT:QUES:POW` bit 1 and display "Amplitude exceeds specified range".

## OUTPut

| Command | *RST | Notes |
|---|---|---|
| `OUTP[:STATe] ON\|OFF\|1\|0` / `?` | OFF | RF output on/off. Also re-arms the reverse-power protection after it trips ✔ |

## AM subsystem

| Command | *RST | Notes |
|---|---|---|
| `AM[:DEPTh] <NRf>[PCT]` / `?` | 30 % | 0.1–99.9 % (0–100 % spec, output ≤ +4 dBm) |
| `AM:STATe ON\|OFF` / `?` | OFF | FM/PM/DM must be OFF, else −221 |
| `AM:SOURce INT[1]\|INT2\|EXT\|INT,EXT\|EXT,INT` / `?` | INT | reply `INTERNAL`, `EXTERNAL`, … ✔. INT2 needs 1E2/1EP |
| `AM:INTernal[1]:FREQuency 400 HZ\|1 KHZ` / `?` | 1 kHz | only the two fixed tones |
| `AM:INTernal2:FREQuency <NRf>` / `?` | 1 kHz | 1E2: 10 Hz–20 kHz; 1EP: 20 Hz–10 kHz |
| `AM:INTernal2:FUNCtion:SHAPe SIN\|TRI\|SQU\|SAW` / `?` | SIN | 1E2 only |
| `AM:EXTernal:COUPling AC\|DC` / `?` | DC | GROund not supported |

## FM subsystem

| Command | *RST | Notes |
|---|---|---|
| `FM[:DEViation] <NRf>[HZ\|KHZ]` / `?` | 3 kHz | range depends on carrier: 200 kHz (<249 MHz), 100 kHz (<501), 200 kHz (<1001), 400 kHz (<2001), 800 kHz (≤4000 MHz) |
| `FM:STATe ON\|OFF` / `?` | OFF | AM/PM/DM must be OFF |
| `FM:SOURce INT[1]\|INT2\|EXT\|INT,EXT\|EXT,INT` / `?` | INT | INT,EXT = FM+FM (external sets ½ deviation at 0.5 V) |
| `FM:INTernal[1]:FREQuency 400 HZ\|1 KHZ` / `?` | 1 kHz | |
| `FM:INTernal2:FREQuency <NRf>` / `?` | 1 kHz | 1E2/1EP |
| `FM:INTernal2:FUNCtion:SHAPe SIN\|TRI\|SQU\|SAW` / `?` | SIN | 1E2 |
| `FM:EXTernal:COUPling AC\|DC` / `?` | DC | DC = DC-FM; run `CAL:DCFM` afterwards |

## PM subsystem

| Command | *RST | Notes |
|---|---|---|
| `PM[:DEViation] <NRf>` / `?` (manual: optional `RAD`; not in B.04.08's unit table, so omit it) | 1.0 rad | 10 rad (<249 MHz), 5 (<501), 10 (<1001), 20 (<2001), 40 (≤4000) |
| `PM:STATe ON\|OFF` / `?` | OFF | AM/FM/DM must be OFF |
| `PM:SOURce INT[1]\|INT2\|EXT\|INT,EXT\|EXT,INT` / `?` | INT | |
| `PM:INTernal[1]:FREQuency 400 HZ\|1 KHZ`, `PM:INTernal2:FREQuency`, `PM:INTernal2:FUNCtion:SHAPe` | | as FM |
| `PM:EXTernal:COUPling AC\|DC` / `?` | DC | front panel cannot do EXT DC for PM (message 001) |

## CAL subsystem

| Command | Notes |
|---|---|
| `CAL:DCFM` | zero the DC-FM carrier offset. EXT DC FM must be active (else −221); MOD INPUT open or 0 V. The display shows "DCFM calibration in progress" (021) |

## PULM (option 1E6)

| Command | *RST | Notes |
|---|---|---|
| `PULM:STATe ON\|OFF` / `?` | OFF | modulator driven from the rear-panel TTL pulse input. −241 if not fitted. Rise/fall < 10 ns; on/off > 80 dB (< 2 GHz) |

## STATus subsystem

`STATus:QUEStionable[:EVENt]? | :CONDition? | :ENABle <NR1> | :ENABle?` and the same four
for the sub-registers `:POWer`, `:MODulation`, `:CALibration:FEXTension` and `:PAGing` (1EP).
See `status-and-errors.md` for the bit map. The event registers are cleared when read.

## SYSTem

| Command | Notes |
|---|---|
| `SYST:ERRor?` | `+0,"No error; "` ✔ (note the trailing `; ` inside the quotes) |
| `SYST:VERSion?` | `1995.9` ✔ (the manual says YYYY.V; this unit reports 1995.9) |
| `SYST:LANGuage "SCPI"\|"COMP"` / `?` | `"scpi"` ✔. COMP = HP 8656B/8657A/B codes. Wait 0.5 s after switching. The rear switch wins again at the next power-up |

## Option 1EP pager encoder (8648A only)

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

## *RST vs. 8656/57 "clear" values

| Parameter | 8648 *RST | 8648 COMP clear | 8656B | 8657A/B |
|---|---|---|---|---|
| Carrier | 100 MHz | 100 MHz | 100 MHz | 100 MHz |
| Level | −136 dBm | −136 dBm | −127 dBm | −143.5 dBm |
| AM depth | 30 % | 0 % | 0 % | 0 % |
| FM dev | 1.0 kHz¹ | 0 | 0 | 0 |
| Pulse | Off | unchanged | – | unchanged |

¹ The manual's table says 1.0 kHz, but the FM subsystem text and a live query on the 8648C
give 3 kHz (`FM:DEV?` → 3.0E+003). Trust the query.

## HP 8656/8657-compatible language (SYST:LANG "COMP" or rear switch)

Implemented codes (upper or lower case): `FR` frequency, `AP` amplitude, `AM`, `FM`, `AO`
amplitude offset, units `HZ KZ MZ DB DF DM EM MV UV VL PC %`, `UP DN` step, `IS` increment
set, `RC RL` recall, `SV` save, `SQ` sequence, `GT` flexible sequence, `QS` reverse sequence,
`RP` reverse-power reset, `R2 R3` RF off/on (R5 is executed for R2), `S1` external, `S2`
400 Hz, `S3` 1 kHz, `S4` modulation off, `S5` DC FM, `HI` HI ALC.
Not implemented: `LO PD PF PI PM R0 R1`.
Differences: after "RF off" a level change does not turn RF back on (send `OUTP:STAT ON`).
Every line needs a line terminator.

## Not supported (common mistakes)

`FREQ:MODE`, `LIST:*`, `SWEep:*`, `SOUR:POW:ALC`, `DIAG:INFO:OPT?` (→ −113) ✔,
`OUTP:MOD`, `MEMory:*`, and the ESG-style `:SOURCE:RADIO:*`/`BURST`/`ARB`. Those strings appear
in the service-software DLLs because the code is shared with the ESG; they do not apply to the 8648.
