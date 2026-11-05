---
name: "tektronix-tds-gpib"
description: "Program Tektronix TDS 400/500/600/700/800 scopes over GPIB (TDS 420-640, 820, A/B/C series, 500D/600C/700D, 694C) - commands by model, waveforms, triggers, events, cal, bench quirks."
---

# Tektronix TDS oscilloscopes: GPIB programming

This skill covers remote control of the monochrome and colour TDS digitizing
oscilloscopes Tektronix sold from 1991 to about 2001: the original TDS
420/460/520/540/620/640, the TDS 820 sampling scope, the A, B and C series
(TDS 410A to 784C), and the last generation (TDS 400A, 510A, 500D, 600C, 700D,
694C). They share one command language: IEEE 488.2 common commands plus a
Tektronix tree (`ACQuire`, `CH<x>`, `HORizontal`, `TRIGger`, `MEASUrement`,
`DATa`, `WFMPre`, `CURVe` and so on). Code written for one model mostly runs on
the others. The differences that break it are listed in sections 15 to 18 and
in the command matrix (Appendix A).

## Sources

| Code | Manual | Models | Printed |
|---|---|---|---|
| O1 | 070-8318-01 TDS Family Programmer Manual | TDS 420, 460, 520, 540, firmware 1.x | Nov 1991 |
| O | 070-8318-05 TDS Family Programmer Manual | TDS 420, 460, 520, 540, 620, 640, firmware 2; options 2F, 13 | Jan 1993 |
| T | 070-8513-01 TDS 820 Digitizing Oscilloscope Programmer Manual | TDS 820 | Feb 1993 |
| A6 | 070-8709-06 TDS Family Programmer Manual | TDS 410, 420, 460, 520A, 524A, 540A, 544A, 620A, 640A, 644A, 684A, 744A, 784A | Nov 1994 |
| A7 | 070-8709-07 TDS Family Programmer Manual | as A6 with 410A, 420A, 460A | 1995 |
| B | 070-9556-00 TDS Family Programmer Manual | TDS 410A, 420A, 460A, 520B, 540B, 620B, 644B, 680B, 684B, 724A, 744A, 784A | |
| B2 | 070-9702-00 TDS Family Programmer Manual | as B without 410A, plus 430A, 510A, 754A, 782A; same command list | |
| C | 070-9876-00 TDS Family Programmer Manual | TDS 420A, 430A, 460A, 510A, 520C, 540C, 620B, 644B, 680B, 684B, 724C, 754C, 784C | |
| D | 063-3060-00 TDS694C Programmer's Manual (WinHelp on floppy) | TDS 400A, 510A, 500D, 600C, 700D, 694C | |

This file is self-contained: everything needed from the nine manuals is
here, so the manuals themselves are not needed to use it. Page numbers are the
printed ones ("O p.2-73"); D is a help file and is cited by topic name. The
PDF manuals are OCR scans, so a few values had to be reconstructed; this file
says where. Sections 2 to 18 were checked claim by claim against the manual
text after writing.

Bench evidence: everything marked **[784D bench]** was measured on a reference TDS 784D (firmware v7.4e) at `GPIB0::3::INSTR`.
Nothing else here has been run on hardware. When the bench disagrees with this
file, believe the bench and update the skill.

Related skills: `tds-decoder-plugin` (TDS Toolkit protocol decoders),
`siglent-sdg2000x` (the bench signal source), `tek-manual-template`.

## Contents

1. Which manual for which scope
2. Things that bite
3. Connecting and identifying
4. Command syntax
5. Status, events and synchronisation
6. Event codes
7. Acquisition and horizontal
8. Vertical, math and FFT
9. Triggers
10. Measurements and cursors
11. Waveform transfer
12. Display, message box and application menu
13. Save, recall, file system and hardcopy
14. Self-cal, diagnostics, FACtory and *RST
15. TDS 420/460/520/540/620/640
16. TDS 820
17. A, B and C series
18. TDS 400A, 510A, 500D, 600C, 700D and 694C
19. TDS 784D bench notes
20. Python driver
21. Recipes
22. Errors in the manuals
Appendix A. Command availability by manual


## 1. Which manual for which scope

Find the model, then read the family section and use the matrix column.

| Model | Generation | Manual (matrix column) | Section |
|---|---|---|---|
| TDS 420, 460, 520, 540 firmware 1.x | original | O1 (O) | 15 |
| TDS 420, 460, 520, 540, 620, 640 firmware 2 | original | O | 15 |
| TDS 820 | sampling | T | 16 |
| TDS 410, 520A, 524A, 540A, 544A, 620A, 640A, 644A, 684A, 744A, 784A | A | A6, A7 (A) | 17 |
| TDS 410A, 420A, 460A | A/B | A7, B | 17 |
| TDS 430A, 510A | B/C | B2, C, D | 17, 18 |
| TDS 520B, 540B, 620B, 644B, 680B, 684B, 724A, 744A, 754A, 782A | B | B, B2 (B) | 17 |
| TDS 520C, 540C, 724C, 754C, 784C | C | C | 17 |
| TDS 520D, 540D, 580D, 724D, 754D, 784D, 794D | D | D | 18, 19 (784D) |
| TDS 640C, 644C, 680C, 684C, 694C | D | D | 18 |

Rules of thumb: a later manual is a superset of the earlier ones for its own
models, so for a C or D model start with D and check the qualifier on each
command. For the TDS 784A/744A, use B or B2 (the A6/A7 text is older). The
400A appears in four manuals; its external clock, roll mode, percent cursors
and the old-style video trigger are its own.

## 2. Things that bite

1. **`FACTORY` turns headers on.** Every query then answers
   `:CH1:SCALE 1.0E-1` instead of `1.0E-1`, and `float()` fails. Send
   `HEADER OFF` at the start and after every `FACTORY` (all manuals; seen on
   the 784D).

2. **An unread reply is lost.** Sending anything after a query, before
   reading its answer, discards the answer with QYE 410/420. A fast
   controller can get half of it. Read every reply; after a timeout, call
   `scope.clear()`.

3. **Events need `*ESR?` first.** `ALLEV?`, `EVMSG?` and `EVENT?` only see
   events that an `*ESR?` has summarised; without it you get code 1. The queue
   holds 20 entries.

4. **Bad values are clipped, not refused.** Most settings out of range are
   rounded or clipped with only a warning (525-528) in the queue. Read back
   what matters. The 784D also accepts `TRIGGER:MAIN:HOLDOFF:VALUE` and does
   nothing with it (section 19).

5. **Measurements always return a number.** A failed measurement still
   answers and queues a 22xx event. Tektronix scopes generally answer 9.9E37
   for "no value"; these manuals never say so and it has not been checked on
   the bench. Check the event queue as well as the number.

6. **Channel and math sources must be displayed** (`SELECT:CH1 ON`) before
   `WFMPRE?`, `CURVE?` or a displayed measurement work; otherwise event 2244.
   A REF must hold data.

7. **8-bit or 16-bit.** SAMple, PEAKdetect and ENVelope data is 8-bit;
   HIRes and AVErage are 16-bit. `DATA:WIDTH 1` throws away the low byte of
   16-bit data; `DATA:WIDTH 2` on 8-bit data pads a zero byte. ASCII on O1 is
   always 8-bit. Use `RIBINARY` and width 2. (The 820 is always 16-bit.)

8. **`WFMPRE?` field order varies.** The manuals print XINCR, PT_OFF; the
   784D sends XINCR, XZERO, PT_OFF, and its `WFMPRE:XINCR?`-style sub-queries
   time out. Ask the whole preamble with `HEADER ON` and parse by name.

9. **Writing a REF needs `ALLOCATE:WAVEFORM:REF<x>` first,** and all REFs
   share one memory pool. Allocations round up to the next legal size.

10. **Several `DATA:SOURCE` entries come back in fixed order** (CH1-4,
    MATH1-3, REF1-4), not the order you listed.

11. **Long operations block.** `*CAL?` (15 s on the 820, 40-60 s on the O
    family, "several minutes" in the A to D manuals), `DIAG:STATE
    EXECUTE` (30 s or more and a warm boot that clears the queues and status
    registers), `AUTOSET EXECUTE` and hardcopies. Raise the VISA timeout for
    them.

12. **A hardcopy in progress blocks DCL.** Send `HARDCOPY ABORT`, then clear.
    On the 784D a 230 s hardcopy at 1 s/div stopped all waveform drawing until
    (presumably) a power cycle.

13. **Model differences.** The 820 has no pretrigger, holdoff in seconds,
    `ACQUIRE:MODE NORMAL` instead of SAMPLE and EXTERNAL as its default
    trigger source. The 620/640/600C have no HIRes or REPEt. The 694C/794D are
    50 Ω only. The 520, 520D, 680C and 724D have AUX 1/AUX 2 as CH3/CH4 and
    some have no rear AUX trigger. 500D/700D-only features (masks, FastFrame,
    DPO, EAL, communication trigger) are absent on the 600C family, the 694C
    included. Check `*IDN?` before branching.

14. **On the 784D the horizontal scale sets the sample rate,** at 50 points
    per division, whatever the record length (section 19). The display shows
    only 500 points.

15. **`*RST` and `FACTORY` are not the same.** `*RST` keeps SRER, ESER,
    `*PSC`, aliases and `*PUD`; `FACTORY` clears the enable registers, deletes
    aliases and turns headers on. Neither touches stored setups, REFs, the
    GPIB address or calibration. With `*PSC 0` the enable registers survive
    power cycles.

16. **Abbreviations changed between models.** Spell keywords in full.

17. **`LOCK ALL` survives a crashed program.** Send `UNLOCK ALL`, or GTL if
    the bus has the scope in local lockout.

## 3. Connecting and identifying

**GPIB.** 24-pin IEEE 488.1 connector on the rear. Set the address on the
front panel: UTILITY (SHIFT DISPLAY on the early models), System = I/O,
Port = GPIB, Configure, Talk/Listen Address. The same menu has Hardcopy (Talk
Only), which sends a hardcopy only when the HARDCOPY button is pressed, and
Off Bus. `FACtory` and `*RST` do not change the address. Interface subsets
(O and T App. C): SH1, AH1, T5, L4, SR1, RL1, PP0, DC1, DT1, C0, E2; no
parallel poll and no controller function.

The scope ends every response with LF plus EOI. It accepts EOI, LF or both as
the input terminator, and white space before it (so CR LF is fine). In pyvisa:

```python
import pyvisa
rm = pyvisa.ResourceManager()
scope = rm.open_resource("GPIB0::1::INSTR")
scope.timeout = 10000            # ms; raise it for *CAL?, DIAg, hardcopy
scope.read_termination = "\n"
scope.write_termination = "\n"
scope.clear()                    # SDC: empties the queues, resets the parser
scope.write("HEADER OFF")
print(scope.query("*IDN?"))
```

**RS-232.** The O manual (option 13) and the TDS 820 manual describe RS-232
as a control port with the same commands and status reporting. From the A
series on, option 13 is described as a hardcopy and file-print port, and D's
interface appendix lists GPIB only, so plan on GPIB for control. Settings:
`RS232:BAUd` 300, 600, 1200, 2400, 4800, 9600, 19200 (O and T leave 2400 out
of the printed list), `RS232:PARity EVEN|ODD|NONe`, `RS232:STOPBits 1|2`,
`RS232:HARDFlagging ON|OFF` (RFR/CTS), `RS232:SOFTFlagging ON|OFF` (XON/XOFF;
XOFF goes out when the 512-byte input buffer has 80 bytes free, XON at 100).

**Identification.** `*IDN?` has four comma-separated fields, with a **space**
between the CF and FV parts of the last one:

```
TEKTRONIX,TDS540,0,CF:91.1CT FV:2.0          O
TEKTRONIX,TDS820,0,CF:91.1CT FV:2.0          T
TEKTRONIX,TDS 544A,0,CF:92.1CT FV:2.0        A, B, C (note the space in "TDS 544A")
TEKTRONIX,TDS 784D,0,CF:91.1CT FV:v7.4e      a D-generation scope (format as on the bench)
```

`ID?` is the older Tektronix form: `TEK/TDS540,CF:91.1CT,FV:2.0` (O, A, B).
The 820 answers `ID TEK/TDS820,0,CF:91.1CT,FV:2.0` (its own `ID` header and an
extra `0` field), and C's example is `ID TEK/TDS 784C,CF:91.1CT,FV:v5.0e`.
Prefer `*IDN?`. Match the model with a regex such as
`TDS\s?(\d{3})([A-Z]?)`, which copes with both spellings, and branch on the
number and suffix (sections 15 to 18). `*OPT?` exists on the 5XXA/6XXA/7XXA,
500B/600B/700A, 510A, 500C/D, 600B/C and 700C/D; the original family, the 820
and the 410/400A series do not have it.

**Front-panel lock.** `LOCk ALL` / `UNLock ALL` lock and free the front panel.
They do nothing while the bus holds the scope in remote with lockout (LLO);
send GTL. Tek's example programs send `LOCK ALL`, so if one aborts, send
`UNLOCK ALL` or cycle the power.

## 4. Command syntax

These rules are the same in every manual (O p.2-1 to 2-10, C section 2, D
"Command Syntax").

- A command is `[:]<Header>[ <Arg>[,<Arg>]...]`; a query is
  `[:]<Header>?[ <Arg>...]`. Queries work on any branch of the tree:
  `MEASUREMENT:MEAS1?` returns every MEAS1 setting.
- Case does not matter. The upper-case part of each keyword in the manuals is
  the shortest accepted form (`ACQ:NUMAV`). The later manuals warn that the
  abbreviation rules changed as models were added and tell you to spell
  keywords out in full. Do that.
- Concatenate with `;`. A new header after a `;` needs a leading colon:
  `ACQUIRE:MODE AVERAGE;:HORIZONTAL:MAIN:SCALE 1E-6`. If only the last keyword
  changes you may drop the shared part: `ACQUIRE:MODE ENVELOPE;NUMAVG 10`.
  Never put a colon in front of a `*` command; a `*` command does not move the
  tree position, so `ACQ:MODE ENV;*TRG;NUMAVG 10` works. Invalid examples
  from the manuals: `DISPLAY:INTENSITY:TEXT 80;ACQUIRE:NUMAVG 10` (missing
  colon), `APPMENU:LABEL:BOTTOM1 "foo";LABEL:BOTTOM2 "fee"` (wrong level;
  write `;BOTTOM2 "fee"`).
- Answers to concatenated queries come back joined by `;` (`80;90` with
  headers off).
- `HEADER OFF|ON` (alias `HDR`) controls whether responses repeat their header.
  `VERBOSE ON|OFF` controls full or short keywords in responses. `*LRN?` and
  `SET?` always include headers. **`FACTORY` turns headers on.** Set
  `HEADER OFF` at the start of every program and after every `FACTORY`.
- Numbers: NR1 integer, NR2 fixed point, NR3 exponent. Any form is accepted
  on input. An out-of-range value is usually rounded or clipped to a legal one
  and a warning (525-528) is queued, not an error. Read back settings that
  matter.
- Strings take `"` or `'`; double the quote to embed one. Embedded CR/LF is
  data. A quoted reply is at most 1000 characters. On GPIB a string cannot end
  with EOI before its closing quote.
- Blocks: `#<n><n digits of length><bytes>`, or indefinite `#0<bytes><LF+EOI>`.
- Mnemonics with numbers: CH1-4, MATH1-3, REF1-4, MEAS1-4, POSITION1-2,
  BOTTOM1-7 (menu buttons left to right), RIGHT1-5 (side menu top to bottom),
  and on later models MASK1-8 and P1-P15 (colour index). `<wfm>` means
  CH<x>, MATH<x> or REF<x>.
- Aliases kept for old programs: `SECdiv` for `SCAle` in horizontal commands,
  `VOLts` for `SCAle` in vertical ones, `DATa:TARget` for `DATa:DESTination`,
  `HDR` for `HEADer`, `SET?` for `*LRN?`. Queries return the primary name.
- `ALIas:DEFINE "NAME","commands"` defines a macro (up to 10, body up to 80
  characters, label up to 12 characters, starting with a letter, not a
  reserved word). `ALIas ON` enables them. Redefining a name is an error;
  delete it first.
- D adds a "(No LRN)" marker for items that `*LRN?` leaves out (mask hit
  counters, `MASK:PASSFail:STATUs?`, FastFrame time stamps).

## 5. Status, events and synchronisation

Same in every manual (O and T section 3, C section 3, D "Status and Events").

**Registers.**

| Register | Set / read | Bits |
|---|---|---|
| SESR | `*ESR?` reads and clears | 7 PON, 6 URQ, 5 CME, 4 EXE, 3 DDE, 2 QYE, 1 RQC (unused), 0 OPC |
| DESER | `DESE <n>` / `DESE?` | same layout as SESR; masks what reaches the SESR **and the event queue** |
| ESER | `*ESE <n>` | which SESR bits set ESB |
| SBR | `*STB?` or serial poll; not cleared by reading | 6 RQS (poll) / MSS (`*STB?`), 5 ESB, 4 MAV |
| SRER | `*SRE <n>` | which SBR bits raise SRQ (ESB 32, MAV 16) |

`*PSC 1` (the default after `FACTORY`): at power-on DESER = 255, ESER = 0,
SRER = 0. `*PSC 0`: all three keep their values through a power cycle, which
surprises programs that expect defaults. Diagnostics completing also sets PON.

**Event queue.** 20 entries; on overflow the 20th becomes 350 "Queue
overflow" (or "Too many events"). An event becomes readable only after `*ESR?`
has summarised it, and each `*ESR?` throws away earlier summaries nobody
fetched. So the sequence is always:

```
*ESR?        -> e.g. 16 (EXE)
ALLEV?       -> 222,"Data out of range; CH1:SCALE 20";527,"Parameter rounded; ..."
```

`EVENT?` returns the next code, `EVMSG?` the next `code,"text"`, `ALLEV?` all of
them, `EVQTY?` the count. Code 0 means the queue is empty; code 1 means events
are waiting for `*ESR?`. Message plus the offending command is limited to 60
characters, with the command right-justified and cut short.

**Output queue.** A new command message after a response clears the unread
response, with QYE 410 (INTERRUPTED) or 420 (UNTERMINATED). Read every reply
before sending the next message. A fast controller can get part of the old
reply; `scope.clear()` (DCL/SDC) recovers.

**`*CLS`** clears the event queue, SESR and SBR (not MAV). It clears the output
queue and MAV only if it comes straight after EOI. It can also kill the SRQ of
an `*OPC` whose operation is still running.

**Operations that take time.** Single-sequence acquisition
(`ACQUIRE:STOPAFTER SEQUENCE` then `ACQUIRE:STATE RUN`), `*CAL?`,
`AUTOSET EXECUTE`, `HARDCOPY START`, and on the 820 and the later models the
limit-test comparison and calibration commands. Single sequence and hardcopy
also make `BUSY?` return 1. Ways to wait (O p.3-7 to 3-12):

| Method | Commands | Notes |
|---|---|---|
| `*OPC?` | send after the operation, read "1" | simplest; set the VISA timeout longer than the operation |
| `*WAI` | send after the operation | the scope executes nothing else meanwhile; a full input buffer makes the controller time out |
| `BUSY?` loop | poll until 0 | more bus traffic, no blocking |
| `*OPC` + serial poll | `DESE 1;*ESE 1;*SRE 0`, then `*OPC`, poll for ESB | |
| `*OPC` + SRQ | `DESE 1;*ESE 1;*SRE 32`, then `*OPC`, wait for SRQ | the controller can do other work |

Typical single shot:

```
ACQUIRE:STOPAFTER SEQUENCE
ACQUIRE:STATE RUN
*OPC?                       -> 1 when the record is complete
MEASUREMENT:IMMED:VALUE?
```

A `MEASUREMENT:...:VALUE?` that fails still returns a number and queues a
22xx event. Check the event queue. (Tektronix's usual "no value" answer is
9.9E37; the manuals don't state it.)

## 6. Event codes

The union of every manual's Tables 3-3 to 3-9. D's list (plus the 820's
calibration rows) is the most complete; the column says which manuals list a code
where it is not all of them. `ALLEV?` text is the message, then `; ` and the
command that caused it.

**No event:** 0 queue empty; 1 new events pending `*ESR?`.

**Command errors (CME, bit 5).** 100 Command error, 101 Invalid character, 102
Syntax error, 103 Invalid separator, 104 Data type error, 105 GET not allowed,
106 Invalid program data separator, 108 Parameter not allowed, 109 Missing
parameter, 110 Command header error, 111 Header separator error, 112 Program
mnemonic too long, **113 Undefined header** (the usual answer to a command the
model lacks), 118 Query not allowed, 120 Numeric data error, 121 Invalid
character in number, 123 Exponent too large, 124 Too many digits, 128 Numeric
data not allowed, 130 Suffix error, 131 Invalid suffix, 134 Suffix too long,
138 Suffix not allowed, 140 Character data error, 141 Invalid character data,
144 Character data too long, 148 Character data not allowed, 150 String data
error, 151 Invalid string data, 152 String data too long, 158 String data not
allowed, 160 Block data error, 161 Invalid block data, 168 Block data not
allowed, 170 Expression error, 171 Invalid expression, 178 Expression data not
allowed, 180 Alias error, 181 Invalid outside alias definition, 183 Invalid
inside alias definition, 184 Command in alias requires more/fewer parameters.

**Execution errors (EXE, bit 4).**

| Code | Message | Where |
|---|---|---|
| 200 | Execution error | |
| 201 | Invalid while in local | |
| 202 | Settings lost due to rtl | not O (-05) or T |
| 210, 211, 212 | Trigger error, Trigger ignored, Arm ignored | |
| 220 | Parameter error | |
| 221 | Settings conflict | |
| 222 | Data out of range | |
| 223 | Too much data | |
| 224 | Illegal parameter value | |
| 230 | Data corrupt or stale | |
| 240-243 | Hardware error, missing, configuration error, I/O device error | not O1 |
| 250-258 | Mass storage error, Missing mass storage, Missing media, Corrupt media, Media full, Directory full, File name not found, File name error, Media protected | file-system models |
| 260, 261 | Expression error, Math error in expression | |
| 2200-2230 | Measurement errors (below) | |
| 2235-2237 | Math error: Invalid math description, Reference waveform is invalid, Out of acquisition memory | |
| 2238 | Too many channels need to be acquired | B on |
| 2239 | EAL turned off | C, D |
| 2240 | Invalid password | |
| 2241 | Waveform request is invalid | |
| 2242 | Data start and stop > record length | |
| 2243 | Waveform requested is not a data source | |
| 2244 | Waveform requested is not turned on | |
| 2245-2248 | Saveref error: Selected channel is turned off, Selected channel data invalid, Out of reference memory, Source reference data invalid | |
| 2249 | Reference deletion error, Waveform in use for math | |
| 2250-2269 | TDS 820 sampler and VCO calibration errors (section 16) | T |
| 2258 | Acq must be stopped | C, D |
| 2259 | File too big | C, D |
| 2260 | Calibration error | |
| 2270-2280 | Alias errors: error, syntax, execution, illegal label, parameter, definition too long, expansion, redefinition not allowed, header not found, label too long, table full | |
| 2281 | Wrong configuration | C, D |
| 2285, 2286 | TekSecure Pass, TekSecure Fail | not O1 |
| 2290-2293 | Limit error: Reference in use, Reference data invalid, Out of reference memory, Selected channel is turned off | not O1 |
| 2301 | Cursor error, Off-screen | not O1 |
| 2302 | Cursor error, cursors in different frames | A on |
| 2311 | Group requested has not been selected or has been deleted | A on |

Measurement errors, each "Measurement error, ...": 2200 Measurement system
error, 2201 Zero period, 2202 No period found, 2203 No period second waveform,
2204 Low signal amplitude, 2205 Low amplitude second waveform, 2206 Invalid
gate, 2207 Measurement overflow, 2208 Waveform does not cross Mid Ref, 2209 No
second Mid Ref crossing, 2210 No Mid Ref crossing second waveform, 2211 No
backwards Mid Ref crossing, 2212 No negative crossing, 2213 No positive
crossing, 2214 No crossing, 2215 No crossing second waveform, 2216 No crossing
target waveform, 2217 Constant waveform, 2218 Unused, 2219 No valid edge - No
arm sample, 2220 No arm cross, 2221 No trigger cross, 2222 No second cross,
2223 Waveform mismatch, 2224 WAIT calculating, 2225 No waveform to measure,
2226 Null Waveform, 2227 Positive and Negative Clipping, 2228 Positive
Clipping, 2229 Negative Clipping, 2230 High Ref < Low Ref.

**Device errors (DDE, bit 3).** 300 Device-specific error, 310 System error,
311 Memory error, 312 PUD memory lost, 313 Calibration memory lost, 314
Save/recall memory lost, 315 Configuration memory lost, 350 Queue overflow
(does not set DDE). 313 after power-up means the calibration constants are
gone.

**System events.** 400 Query event, 401 Power on (PON), 402 Operation complete
(OPC), 403 User request (URQ), 404 Power fail (DDE), 405 Request control, 410
Query INTERRUPTED, 420 Query UNTERMINATED, 430 Query DEADLOCKED, 440 Query
UNTERMINATED after indefinite response (all QYE), 450-454 right menu button
1-5 pushed, 460-466 bottom menu button 1-7 pushed (URQ).

**Execution warnings (EXE).** 500 Execution warning, 510 String data too long,
truncated, 525 Parameter underrange, 526 Parameter overrange, 527 Parameter
rounded, 528 Parameter out of range, 530 Data stop > stop, values swapped
internally, 531 Data stop > record length, curve truncated, 532 Curve data too
long, curve truncated, 540 Measurement warning, 541 Low signal amplitude, 542
Unstable histogram, 543 Low resolution, 544 Uncertain edge, 545 Invalid in
minmax, 546 Need 3 edges, 547 Clipping positive/negative, 548 Clipping
positive, 549 Clipping negative. Later additions: 550 InstaVu (D: DPO mode)
active - deactivate to see change and 551 ... to use math (A on); 552 EAL on -
turn off to see change and 553 ... to use math (C, D); 570 Saveref warning,
decimated 500k waveform to 250k Ref (700A/700D), **571 Option 05 not present,
572 Option 2F not present** (B on).

**Internal warnings.** 600 Internal warning, 620 Bad thermistor, **630 50 Ω
overload** (the manuals say nothing more; read the channel's impedance back
after an overdrive).

## 7. Acquisition and horizontal

Wording and ranges below follow D, the newest manual; the per-family
sections give the older or different values.

**Acquisition.**

| Command | Arguments |
|---|---|
| `ACQuire:MODe` | `SAMple | PEAKdetect | HIRes | AVErage | ENVelope`. No HIRes on any 600 model; no PEAKdetect on the 620/640 and 620A/640A/644A/684A. The 820 uses `NORMal | AVErage | ENVelope`. |
| `ACQuire:NUMAVg` | 2 to 10000 |
| `ACQuire:NUMEnv` | 1 to 2000, or `INFInite` (0). Single sequence with infinite envelope stops after 2001 acquisitions (the O scan reads 2007, probably OCR). |
| `ACQuire:STATE` | `OFF | ON | RUN | STOP | <NR1>`. RUN restarts an average or envelope and resets `NUMACq`. |
| `ACQuire:STOPAfter` | `RUNSTop | SEQuence | LIMit` (LIMit stops when the limit test condition is met; not on O1) |
| `ACQuire:NUMACq?` | acquisitions since the last start, up to 2^30-1 (D); reset by any acquisition, horizontal or vertical change |
| `ACQuire:REPEt` | `OFF | ON`: fill the whole record in equivalent time before stopping. 420/460/520/540, A/B/C real-time-plus-ET models, 400A/510A/500D/700D; not 620/640 or 600C |
| `ACQuire:AUTOSAve` | `OFF | ON` (500D/600C/700D): single sequence clears all REFs, then saves CH1-4 to REF1-4 |

`ACQuire:STOPAfter SEQuence` means "stop when the mode is satisfied": one
record in SAMple at a real-time timebase, NUMAVg records in AVErage, a full
record in equivalent time with REPEt on.

**Horizontal.**

| Command | Notes |
|---|---|
| `HORizontal:MAIn:SCAle` (= `HORizontal:SCAle`, `:SECdiv`) | 1-2-5 steps (1-2.5-5 on 620/640/640C/644C); values in between snap. D: 400A 20 s to 1 ns; 510A/500D/600C/700D 10 s to 500 ps; 684C/784D/794D 200 ps; 694C 100 ps |
| `HORizontal:DELay:SCAle` | delayed time base; slower than main makes both the delay value |
| `HORizontal:MODe` | `MAIn | INTENSIFied | DELAYEd` |
| `HORizontal:DELay:MODe` | `RUNSAfter | TRIGAfter` |
| `HORizontal:DELay:TIMe` (`:RUNSAfter`, `:TRIGAfter`) | 16 ns to 250 s, 4 ns steps; 400A/420/460 10 ns (runs after) or 60 ns (trig after) to 20 s, 10 ns steps |
| `HORizontal:RECOrdlength` | per model, see below |
| `HORizontal:TRIGger:POSition` | pretrigger, 0-100 % of the record (20-80 % on 620/640). Not on the 820 |
| `HORizontal:POSition` | 0-100 %: how much of the record is left of screen centre (a display pan) |
| `HORizontal:FITtoscreen` | `ON | OFF`: compress the whole record onto the screen (A on; not 820) |
| `HORizontal:CLOck INTernal|EXTernal`, `:CLOck:MAXRate`, `HORizontal:ROLL OFF|ON|AUTO` | external clock and roll mode, TDS 400A (and 410A/420A/460A) only. With external clock on, `HORizontal:MAIn:SCAle?` returns 50 |
| `HORizontal:EXTDACQ`, `:RECORDSTART`, `:ACQLENGTH?`, `:ACQDURATION?` | extended acquisition, 500D/700D option 2M (section 18) |
| `HORizontal:FASTframe:*` | FastFrame: 5XXA/7XXA, 500B/700A, 500C/700C, 500D/700D (sections 17, 18) |

There is no sample-rate query on any of these. On the 784D the rate is
50 points per division of the timebase (section 19). `HORIZONTAL:MAIN:SAMPLERATE?`
is event 113.

Record lengths (`HORizontal:RECOrdlength`):

| Family | Standard | Options |
|---|---|---|
| 420/460 (O) | 500, 1000, 2500, 5000, 15000 | 1M: 30000, 60000 |
| 520/540 (O) | 500 to 15000 | 1M: 50000 |
| 620/640 (O) | 500, 1000, 2000 | |
| 820 (T) | 500, 1000, 2500, 5000, 15000 | |
| 420A/430A/460A (D) | 500, 1000, 2500, 5000, 15000, 30000 | 1M: 60000, 120000 |
| 510A/520D/724D (D) | 500 to 15000, 50000 | 1M or 2M, 520D/724D only: 75000, 100000, 130000, 250000 |
| 600C (D) | 500, 1000, 2500, 5000, 15000 (+30000 on 694C) | 1M on 694C: 30000, 50000, 75000, 100000, 120000 |
| 540D/580D/754D/784D/794D (D) | 500 to 15000, 50000 | 1M or 2M: 75000, 100000, 130000, 250000, 500000; 2M with EAL: 2 M/4 M/8 M acquisition |

The A, B and C values are in section 17. Read the length back after setting
it (`HORIZONTAL:RECORDLENGTH?`).

## 8. Vertical, math and FFT

| Command | Arguments and notes |
|---|---|
| `CH<x>:SCAle` (= `:VOLts`) | 1 mV to 10 V/div at 1X probe. 694C/794D: 10 mV to 1 V/div (to 100 V/div with a P6339A). 820: 1 mV to 10 V/div |
| `CH<x>:POSition` | ±5 div, applied before digitising |
| `CH<x>:OFFSet` | volts subtracted before acquisition; a larger offset moves the trace down. Range depends on scale and probe: ±1 V to 100 mV/div, ±10 V to 1 V/div, ±100 V to 10 V/div at 1X on most models; less on the 520/520D/724D AUX inputs, the 820 (±2 V, ±1 V with option 1D) and the 694C/794D (section 18) |
| `CH<x>:COUPling` | `AC | DC | GND`. Not on the 820. 694C/794D need a P6339A for AC |
| `CH<x>:IMPedance` | `FIFty | MEG`. Not on the 820; 694C/794D 50 Ω only. Level II probes set it automatically on 500D/600C/700D |
| `CH<x>:BANdwidth` | `TWEnty | HUNdred | ONEFifty | TWOfifty | FULl`, model dependent: TWEnty 20 MHz everywhere, HUNdred 100 MHz (O family, A series except 684A/7XXA, 400A, 510A), TWOfifty 250 MHz (684A/7XXA, then 500B/600B/700A onward), ONEFifty 150 MHz (694C/794D with P6339A). Not on the 820 |
| `CH<x>:PRObe?` | probe attenuation factor as **gain**: a 10X probe reads 100.0E-3 |
| `CH<x>:PROBEFunc:EXTAtten <NR3>` / `:EXTDBatten <NR3>` | external attenuation 1E-6 to 1E6, or ±120 dB (C: 500C/700C; D: 500D/600C/700D). The 820 spells it `PROBEFunct`. Send with a space, not the colon D's syntax line shows |
| `CH<x>:DESKew` | ±25 ns, 1 ps steps (B, C, D). The 820 has `HORizontal:DESKew:CH<x>` 0 to 10 ns |
| `CH<x>:PROBECal?` | `PASS | INIT | FAIl` (B, C, D) |
| `SELect:<wfm>` | `ON | OFF`. ON also makes it the selected waveform. Up to 11 displayed |
| `SELect:CONTROl <wfm>` | the waveform that cursor and vertical commands act on |

**Math.** `MATH<x>:DEFINE "<expr>"`, x = 1 to 3.

- Dual: `"<src><op><src>"` with op `+`, `-`, `*`, and from the A series on
  also `/` (not on the 4XX/4XXA/400A). Sources are CH<x> or REF<x>, never
  MATH<x>. Example: `MATH2:DEFINE "CH1 + CH2"`.
- Single: `"INV(CH1)"`. With option 2F (Advanced DSP Math; standard on some
  later models): `"DIF(CH1)"`, `"INT(CH1)"`,
  `"FFT(CH1[,<window>][,<scaling>][,<phase suppression>])"`.
- FFT windows `RECtangular | HAMming | HANning | BLAckmanharris`; scaling
  `LOGrms | LINearrms | DEGreesphase | RADiansphase`; phase suppression
  -100 to +100 dB. Example: `MATH1:DEFINE "FFT(CH1, HAMM, LINEARRMS, 20)"`.
  Without 2F the scope returns warning 572 "Option 2F not present" (D).
- `MATH<x>:PROCessing OFF|AVErage` and `MATH<x>:NUMAVg <n>` average a math
  waveform (510A/500D/600C/700D; some need 2F).
- Factory: MATH1 = CH1+CH2, MATH2 = CH1-CH2 (an FFT of CH1 on scopes with
  option 2F), MATH3 = INV(CH1).
- A MATH or REF waveform can only be scaled or moved with `ZOOm:*`
  (`ZOOm:STATE ON`, `ZOOm:VERTical:SCAle`, `:POSition`, `ZOOm:HORizontal:*`).
- Math is refused in DPO mode (551) and in EAL mode (553).

## 9. Triggers

Every model uses the `TRIGger:MAIn` tree (A trigger); all but the 820 add
`TRIGger:DELay` (B trigger). The 820's own short edge-only tree
(`TRIGger:SOUrce`, `:LEVel`, `:HOLdoff:VALue` ...) also answers to the
`TRIGger:MAIn:EDGE:*`, `:LEVel`, `:MODe` and `:HOLdoff:*` forms (section 16).

**Common.**

| Command | Arguments |
|---|---|
| `TRIGger:MAIn:TYPe` | `EDGE | LOGIc | PULse | VIDeo | COMMunication`. LOGIc and PULse: 520/540/620/640 and every later model except the 4XX/400A series; VIDeo needs option 05; COMMunication 500C/700C and 500D/700D |
| `TRIGger:MAIn:MODe` | `AUTO | NORMal` |
| `TRIGger:MAIn:LEVel` | `ECL | TTL | <NR3>` (ECL -1.3 V, TTL 1.4 V) |
| `TRIGger:MAIn SETLevel` | level to 50 % of the signal |
| `TRIGger FORCe` | force a trigger when the state is READY |
| `TRIGger:STATE?` | `ARMED | AUTO | PARTIAL | READY | SAVE | TRIGGER`; also `FASTFRAME` and `INSTAVU` on 500D/700D in those modes. PARTIAL = main triggered, waiting for the delayed trigger |

**Edge.** `TRIGger:MAIn:EDGE:SOUrce AUXiliary|CH<x>|LINE` (no AUXiliary on
the 520, 520D and 724D; plus `TLAAUXiliary` on the 694C), `:SLOpe RISe|FALL`,
`:COUPling AC|DC|HFRej|LFRej|NOISErej`.

**Holdoff.** There are three schemes:

| Models | Command | Unit |
|---|---|---|
| O family, A series, 400A, 510A | `TRIGger:MAIn:HOLdoff:VALue <NR1>` | 0-100 % of the holdoff range |
| 684A/7XXA, then 500B/600B/700A, 500C, 500D/600C/700D (and the 784D on the bench) | `TRIGger:MAIn:HOLDOff:BY TIMe|DEFAult`, `:HOLDOff:TIMe <NR3>`, `:HOLDOff:ACTUal?` | seconds, 250 ns to 12 s |
| 820 | `TRIGger:HOLdoff:VALue <NR3>`, `:HOLdoff:ACTUal?` | seconds, 15 µs to 2 s |

On the 784D `:VALue` is accepted without an error and ignored (section 19). D gives the
default holdoff as the larger of 5 divisions or 250 ns, then works its own
example out at 25 divisions.

**Logic** (`TRIGger:MAIn:LOGIc:*`). `:CLAss PATtern|STATE|SETHold` (SETHold
500D/600C/700D), `:FUNCtion AND|NANd|NOR|OR`, `:INPut:CH<x> HIGH|LOW|X`
(x = 1-3), `:PATtern:INPut:CH4 HIGH|LOW|X`, `:STATE:INPut:CH4 RISe|FALL`
(STATE samples CH1-3 on a CH4 edge), `:WHEn TRUe|FALSe`,
`:PATtern:WHEn TRUe|FALSe|LESSThan|MOREThan` with `:WHEn:LESSLimit` and
`:MORELimit` (time qualified, evaluated at the true-to-false transition),
`:THReshold:CH<x> <NR3>`. Setup/hold: `:SETHold:CLOCk:SOUrce|EDGE|LEVel`,
`:SETHold:DATa:SOUrce|LEVel`, `:SETHold:SETTime`, `:HOLDTime`.

**Pulse** (`TRIGger:MAIn:PULse:*`). `:SOUrce CH<x>`,
`:CLAss GLItch|RUNT|WIDth|SLEWRate|TIMEOut`. SLEWRate (with runt
WHEn/WIDth and THReshold:BOTh) is 684A/7XXA in A6/A7 and 500/600/700 from B
on; TIMEOut arrives in B. Neither is on the 400A or 510A.

- Glitch: `:GLItch:WIDth`, `:FILTer ACCept|REJect` (ACCept triggers on
  pulses narrower than the width), `:POLarity EITher|NEGAtive|POSITIVe`.
- Runt: `:RUNT:THReshold:HIGH|LOW`, `:THReshold:BOTh TTL|ECL`,
  `:POLarity`, `:WHEn OCCurs|WIDERthan`, `:WIDth`.
- Width: `:WIDth:LOWLimit`, `:HIGHLimit`, `:WHEn WIThin|OUTside`,
  `:POLarity NEGAtive|POSITIVe`.
- Slew rate: `:SLEWRate:DELTATime`, `:THReshold:HIGH|LOW|BOTh`
  (TTL 1.8/0.8 V, ECL -1.1/-1.5 V), `:POLarity`, `:WHEn FASTERthan|SLOWERthan`,
  `:SLEWRate?` (V/s). D's syntax lines for these are wrong (they print
  `PULse:RUNT:DELTATime` and `SLEWRate:THReshold:WHEn`); use the names above.
- Timeout: `:TIMEOut:TIMe`, `:POLarity STAYSHigh|STAYSLow|EITher`
  (POSITIVe/NEGAtive also accepted).

**Video** (option 05). Two different trees:

- 420/460 and 400A: `TRIGger:MAIn:VIDeo:SYStem NTSc|PAL|SECAM|CUSTom`,
  `:FIELD`, `:SCAN RATE1..RATE4` (15-20, 20-25, 25-35, 35-64 kHz), `:BY
  TIMe|LINES`, `:LINES`, `:TIMe`, `:INTERLAce`, `:HOLdoff:VALue`, `:SYNc`,
  `:SOUrce`.
- 510A, 500D, 600C, 700D (and B/C): `:STANdard NTSC|PAL|HDTv|FLEXformat`,
  `:NTSc MONo|COLOr`, `:PAL MONo|COLOr|SECAm`, `:HDTv 787|1050|1125|1250`,
  `:FIELDType NUMERic|ALL|EVEN|ODD`, `:LINE <n>`, and the `:FLEXformat:*`
  set (FIELDRATE, FIELDS, LINES, NEGSyncwidth, V1/V2 start and stop times).

**Communication** (500C/D, 700C/D). `TRIGger:MAIn:COMMunication:SOUrce`,
`:CODe AMI|CMI|NRZ`, `:BITRate`, `:STANdard DS1 ... OC12 ... FC1063 ...`
(D adds ENET10/100/1250 and VIDEO360), `:AMI:PULSEForm`, `:AMI:THReshold:HIGH|LOW`,
`:CMI:PULSEForm`, `:NRZ:PULSEForm`. Changing CODe or BITRate makes the
standard CUSTom; the last of STANdard and BITRate sent wins.

**Delayed (B) trigger.** `TRIGger:DELay:BY EVENTS|TIMe|EVENTSTime|RUNSAfter`
(EVENTSTime: count events, then wait; not on 420/460/400A),
`:EVENTS:COUNt` (2 to 10E7; 1 to 10E7-1 on the 400A), `:TIMe`,
`:EDGE:SOUrce|SLOpe|COUPling` (D adds coupling `MAINTrigger`), `:LEVel`,
`:TYPe EDGE`, `TRIGger:DELay SETLevel`. Use with `HORizontal:MODe DELAYEd`
and `HORizontal:DELay:MODe TRIGAfter`.

## 10. Measurements and cursors

**Measurements.** Four displayed slots (`MEASUrement:MEAS1` to `MEAS4`) and
one immediate measurement (`MEASUrement:IMMed`) that is never displayed and is
computed when queried. Use IMMed from programs; MEAS<x>:VALue? is a display
value refreshed about every 1/3 s and needs its source displayed.

```
MEASUREMENT:IMMED:TYPE FREQUENCY
MEASUREMENT:IMMED:SOURCE1 CH1
MEASUREMENT:IMMED:VALUE?          -> 1.000012E+6
MEASUREMENT:IMMED:UNITS?          -> "Hz"
```

Types (D): AMPlitude, AREA, BURst, CARea, CMEan, CRMs, DELay, FALL,
FREQuency, HIGH, LOW, MAXimum, MEAN, MINImum, NDUty, NOVershoot, NWIdth,
PDUTy, PERIod, PHAse, PK2pk, POVershoot, PWIdth, RISe, RMS. Histogram and
optical types on 500D/600C/700D: EXTINCTDB, EXTINCTPCT, EXTINCTRATIO,
HITS, PEAKHits, MEDian, MEANDBM, SIGMA1-3, STDdev, WAVEFORMS (with
`SOURCE1 HIStogram`). The 820 adds NCRoss and PCRoss. O1 lacks AREA, CARea
and PHASE. `UNIts?` returns "V", "s", "Hz", "VV" (volts squared), "%" (and
"dB" on the 820; clock units on the 400A with external clock).

| Command | Notes |
|---|---|
| `MEASUrement:IMMed:SOURCE1`, `:SOURCE2` | SOURCE2 is the second waveform for DELay and PHAse |
| `MEASUrement:IMMed:DELay:EDGE1|EDGE2 RISe|FALL`, `:DIRection FORWards|BACkwards` | for DELay |
| `MEASUrement:MEAS<x>:STATE ON`, `:TYPe`, `:SOURCE1/2`, `:VALue?`, `:UNIts?` | displayed slots |
| `MEASUrement:MEAS<x>:COUNt?`, `:MAXimum?`, `:MEAN?`, `:MINImum?`, `:STDdev?` | statistics since reset (500C/700C; 500D/600C/700D) |
| `MEASUrement:STATIstics:MODE OFF|MINMax|MEANSTDdev`, `:WEIghting <n>` | statistics display and time constant |
| `MEASUrement:METHod HIStogram|MINMax` | how HIGH and LOW are found |
| `MEASUrement:REFLevel:METHod ABSolute|PERCent` | |
| `MEASUrement:REFLevel:PERCent:HIGH|LOW|MID|MID2` | defaults 90, 10, 50, 50 %. MID2 is the mid level of the second waveform for DELay |
| `MEASUrement:REFLevel:ABSolute:HIGH|LOW|MID|MID2` | volts, default 0 |
| `MEASUrement:GATing ON|OFF` | gate on the vertical-bar cursors |
| `MEASUrement:SNAPShot`, `:CLEARSNapshot` | on-screen table of all measurements (not O1) |

A failed measurement still answers with a number (Tektronix's usual 9.9E37
"no value", not documented in these manuals) plus an event in 2200-2230 or a
warning in 540-549. Read `*ESR?` and `ALLEV?` when the value matters.

**Histograms** (500C/700C; 500D/600C/700D). `HIStogram:MODe OFF|HORizontal|VERTical`
(turns EAL and DPO off), `HIStogram:SOUrce CH<x>`, `HIStogram:BOX l,t,r,b`
(waveform units) or `HIStogram:BOXPcnt` (percent), `HIStogram:DISplay
LINEAr|LOG|OFF`, `HIStogram:SIZe`, `HIStogram:COUNt RESET`.

**Cursors.**

| Command | Notes |
|---|---|
| `CURSor:FUNCtion` | `OFF | HBArs | VBArs | PAIred` (PAIred not O1) |
| `CURSor:HBArs:POSITION<x>` | volts relative to ground; `:DELTa?`; `:SELect CURSOR1|CURSOR2` |
| `CURSor:VBArs:POSITION<x>` | relative to the trigger in `:UNIts` (`SECOnds | HERtz`); `:DELTa?`; `CURSor:VBArs SNAp` moves them to `DATa:STARt/STOP` |
| `CURSor:VBArs:POSITION<x>Pcnt`, `CURSor:HBArs:POSITION<x>Pcnt`, `CURSor:PAIred:POSITION<x>Pcnt` | percent forms, 0-100 %; 410A/420A/430A/460A only (A7 on) |
| `CURSor:PAIred:POSITION<x>`, `:HPOS1?`, `:HPOS2?`, `:HDELTA?`, `:VDELTA?` | paired cursors; the 820 and A6 spell the setters `POSITION1`/`POSITION2` |
| `CURSor:MODe TRACk|INDependent` | |

Cursors act on the selected waveform (`SELect:CONTROl`). Readings come from
screen positions, so they are only as fine as a pixel.

**Limit test** (O from -05, T, A, B, C, D). Build a template from a waveform
plus tolerances, store it in a REF, compare live channels with it:

```
LIMIT:TEMPLATE:SOURCE CH1
LIMIT:TEMPLATE:DESTINATION REF1
LIMIT:TEMPLATE:TOLERANCE:HORIZONTAL 0.2      divisions (0 to 5)
LIMIT:TEMPLATE:TOLERANCE:VERTICAL 0.2
LIMIT:TEMPLATE STORE
LIMIT:COMPARE:CH1 REF1
LIMIT:STATE ON
ACQUIRE:STOPAFTER LIMIT                      stop on the first failure
```

Changes to source, destination or tolerances need a new `TEMPLATE STORE`.
`LIMit:BELl` and `LIMit:HARDCopy` act on failures. In EAL or DPO mode
`LIMit:STATE` is accepted and does nothing.

## 11. Waveform transfer

**Reading from the scope.**

```
SELECT:CH1 ON                     channel and math sources must be displayed
DATA:SOURCE CH1
DATA:ENCDG RIBINARY               signed, MSB first
DATA:WIDTH 2
DATA:START 1
DATA:STOP 15000                   past the record length just truncates (531)
WFMPRE?                           ask with HEADER ON and parse by name
CURVE?                            #<n><len><data><LF>
```

`WAVFRM?` is `WFMPRE?;CURVE?` in one reply.

**Encodings** (`DATa:ENCdg`; setting one also sets the WFMPre fields, O
Table 2-24):

| DATa:ENCdg | WFMPre ENCdg | BN_Fmt | BYT_Or |
|---|---|---|---|
| ASCIi | ASC | n/a | n/a |
| RIBinary | BIN | RI | MSB |
| RPBinary | BIN | RP | MSB |
| SRIbinary | BIN | RI | LSB |
| SRPbinary | BIN | RP | LSB |

RI: -128..127 or -32768..32767, 0 = screen centre. RP: 0..255 (centre 127)
or 0..65535. The code range spans one division above the top of the screen
to one below the bottom (10 divisions on an 8-division graticule, so about 25
codes per division at width 1; 6400 per division at width 2 measured for REFs
on the 784D). Always scale with YMULT, not these figures. RIBinary width 2 is
the fastest transfer; the S forms are little-endian for PCs. Byte order is
ignored at width 1.

**Width and resolution.** SAMple, PEAKdetect and ENVelope data is 8-bit;
HIRes and AVErage are 16-bit; the 820 is 16-bit. Width 2 on 8-bit data pads a
zero low byte; width 1 on 16-bit data drops the low byte. ASCII on O1 is
always 1 byte per point.

**Range.** `DATa:STARt` and `:STOP` run from 1 to the record length (the
acquisition length in EAL). STOP below STARt: O, T and A6 swap them (warning 530); from A7 on
the manuals say STOP becomes STARt + (STARt - STOP), so START 30, STOP 20
sends points 30 to 40. Always send START ≤ STOP. Both past the record
is error 2242. `DATa SNAp` copies the vertical-bar cursors into START/STOP,
`DATa INIT` resets the DATa settings, `DATa RECORDSNAp` (500C/700C, 500D/700D) selects
the whole acquisition.

**Several sources.** `DATA:SOURCE CH1,CH2` returns comma-separated blocks in
the fixed order CH1-4, MATH1-3, REF1-4, whatever order you list.

**Preamble.** `WFMPre?` returns the shared fields, then one group per source:

```
BYT_NR 2;BIT_NR 16;ENCDG BIN;BN_FMT RI;BYT_OR MSB;
CH1:WFID "Ch1, DC coupling, 100.0mV/div, 500.0us/div, 500 points, Sample mode";
NR_PT 500;PT_FMT Y;XUNIT "s";XINCR 1.0E-5;PT_OFF 250;
YUNIT "V";YMULT 1.5625E-5;YOFF 0.0E+0;YZERO 0.0E+0
```

(Layout from the manuals. XZERO appears in the `WFMPRE?` reply from B
(070-9556-00) to C, for the 500B/600B/700A and later; D's reply format leaves
it out and documents only `WFMPre:<wfm>:XZEro` (500D/600C/700D); the 784D sends it between XINCR and PT_OFF; O and A
leave it out; C's own example has `XZERO 8.95E-6;PT_OFF -249`, so PT_OFF can
be negative. Parse by name.)

Scaling, PT_FMT Y:

```
t(n) = XZERO + XINCR * (n - PT_OFF)      n = 0.. counted from DATA:START
v(n) = YZERO + YMULT * (code(n) - YOFF)
```

PT_FMT ENV sends max/min pairs for each point, scaled the same way. PT_OFF is
the trigger point relative to `DATA:START` (C p.2-350). On the 820 PT_OFF is
always 0 and XZERO is "the time base position of the waveform data" in
seconds (T), which reads as trigger to first record point. On the 784D XZERO is
a sub-sample trigger offset of a few microseconds. YMULT is volts per
digitising level (the global `WFMPre:YMUlt` entry says "per division"; the
formula needs per level). WFID is text with coupling, V/div, s/div, record
length and mode; on the 400A with external clock its time/div field changes.

**Writing a reference.**

```
DATA:DESTINATION REF1
ALLOCATE:WAVEFORM:REF1 500         required before CURVE can store data
DATA:ENCDG RIBINARY;WIDTH 2;START 1
WFMPRE:XINCR 1E-6;PT_OFF 0;YMULT 1.5625E-5;YOFF 0;YZERO 0;PT_FMT Y
CURVE #41000<1000 bytes>
SELECT:REF1 ON
```

`<wfm>` in `WFMPRE:<wfm>:...` is ignored on input; DATA:DESTINATION decides.
DATA:STOP is ignored on input. One waveform per transfer. Accepted and ignored
for compatibility: `WFMPre:CRVchk`, `NR_PT`, `WFId`, `XUNit`, `XMUlt`,
`XOFf`, `XZEro` (ignored in O and A; a real field from B on), `YUNit`, `ZMUlt`, `ZOFf`,
`ZUNit`, `ZZEro`. The manuals say the block length "includes checksum"; there
is no checksum byte.

**Reference memory.** `ALLOCATE:WAVEFORM:REF<x> <points>` (the query returns
0 for an empty REF; free one with `DELETE:WAVEFORM`),
`ALLOCATE:WAVEFORM:FREE?` (approximate free points, about 20 used for
bookkeeping), `ALLOCATE?`. The four REFs share one pool. Odd sizes round up to
the next legal record length and anything above the maximum clips to it (O:
all models; C and D state it only for the 500C/600B and 500D/600C).
`DELETE:WAVEFORM REF<x>|ALL` frees the allocation but does not erase the data
(`TEKSECURE` does). `SAVE:WAVEFORM CH1,REF1` copies a live waveform.

**Timing and size.** Bytes = (STOP - START + 1) × width per source. On the 784D
a 15000-point width-2 `CURVE?` takes 0.09 s and 50000 points 0.24 s. An 8 M
EAL record in ASCII is over 26.8 MB and takes over 25 minutes.

## 12. Display, message box and application menu

**Display.** `DISplay:FORMat YT|XY` (XY pairs CH1/CH2, CH3/CH4, REF1/REF2,
REF3/REF4; `XYZ` in DPO mode on 500D/700D), `DISplay:STYle
DOTs|VECtors|INTENSIFied|VARpersist|INFPersist`, `DISplay:PERSistence` 0.25 to
10 s, `DISplay:GRAticule FULl|GRId|CROSSHair|FRAme` (A series on add `NTSc` and
`PAL`), `DISplay:FILTer LINEAr|SINX` (O1 and T spell it `LINEar`),
`DISplay:INTENSITy:WAVEform|TEXt|OVERALL|CONTRast` (percent; OVERALL and
CONTRast are for monochrome models: 400A/510A/500D/6X0C in D, so not the
700D or the colour 600Cs), `DISplay:CLOCk ON|OFF`,
`DISplay:TRIGT`, `DISplay:TRIGBar OFF|SHORt|LONG`. Colour models (B/C/D
colour, 6X4C, 700D): `DISplay:COLOr:PALEtte:REGular NORMal|BOLd|HARDCopy|MONo`,
`:PALEtte:PERSistence TEMPErature|SPECTral|GRAYscale`, `:PALEtte:<pal>:<item>
h,l,s` (hue 0-359, lightness and saturation 0-100), `:MAP:<wfm>:TO`,
`DISplay:COLOr:CONTRast`. Turning waveform display off still acquires and
transfers, and updates faster.

**Message box.** One text box anywhere on the screen.

```
MESSAGE:BOX 74,84,475,135         x1,y1,x2,y2 pixels, 0-640 x 0-480, origin top left
MESSAGE:SHOW "Line one\nLine two" LF splits lines; up to 1000 characters
MESSAGE:STATE ON
MESSAGE CLEAR                     same as MESSAGE:SHOW ""
```

Characters are 15 pixels high. Inside the string, TAB followed by two digits
(O, T) or two bytes MSB, LSB (A6 on, e.g. TAB NUL CR = column 13) sets the
pixel column, and ESC @ toggles
reverse video. D adds `MESSage:OPAQue ON|OFF` (fills the background) and
`MESSage:PRIOrity <n>` (default 6; error windows are 5; higher draws on top;
set it before showing the box). `MESSAGE:OPAQUE` also works on the 784D
(section 19). The font is proportional.

**Application menu.** Your own bezel-button menu:

```
APPMENU:TITLE "Bench"
APPMENU:LABEL:BOTTOM1 "Start"     1-7, about 10 characters x 3 lines
APPMENU:LABEL:RIGHT1 "Abort"      1-5, about 12 characters x 2 lines
APPMENU ACTIVATE
```

While it is shown, each bezel press queues event 450-454 (right buttons) or
460-466 (bottom buttons) and sets URQ. For an SRQ, enable URQ (bit 6) in DESE
and `*ESE` and ESB in `*SRE`; otherwise poll `*ESR?` and `EVENT?`.
`CLEARMENU` removes it. `APPMENU:LABEL CLEAR` blanks the labels.

**Java applications and GP knob** (D: 500D, 600C, 700D).
`APPLication:ACTivate "hd0:TDSPRT1.APP"` starts an on-scope application.
`APPLication:GPKNOB:UNIts`, `:RESOlution`, `:MINValue`, `:MAXValue`,
`:VALue`, `:LABel`, then `:ACTIVE ON` hands the general-purpose knob to a
program value (label + value + units share about 32 characters).

**TDS 820 graphics.** `GRAPhics:POInts` draws up to 100 line points on the
graticule (section 16). No other model has it.

**Zoom.** `ZOOm:STATE ON|OFF|PREView`,
`ZOOm:HORizontal:SCAle|POSition|LOCk ALL|LIVe|NONe`,
`ZOOm:VERTical:SCAle|POSition`, `ZOOm RESet`, `ZOOm:DUAl`,
`ZOOm:DUAl:OFFSet`, `ZOOm:GRAticule UPPer|LOWEr`. PREView and dual zoom are
7XXA-only in A6, 400A/500B/600B/700A in B, and 400A/500D/600C/700D in D (not
the 510A); `ZOOm:GRAticule` is in every edition from A6 on. Zoom is the only way to
scale or move MATH and REF waveforms.

## 13. Save, recall, file system and hardcopy

**Internal storage (all models).** Ten setup slots and four REFs.

| Command | Notes |
|---|---|
| `*SAV <1-10>`, `SAVe:SETUp <1-10>` | store the setup |
| `*RCL <1-10>`, `RECAll:SETUp FACtory|<1-10>` | recall; out of range gives 222 |
| `DELEte:SETUp <1-10>|ALL` | resets the slot to the factory setup |
| `SAVe:WAVEform <wfm>,REF<x>` | copy a waveform into a REF |
| `DELEte:WAVEform REF<x>|ALL` | free the REF (data stays in memory) |
| `*LRN?` / `SET?` | the whole setup as a command string, always with headers; send it back to restore |
| `TEKSecure` | zero all REF memory and reset all setups (events 2285/2286); not O1 |

**File system** (A, B, C and D models with the floppy, option 1F;
`READFile`/`WRITEFile` only from C on). Not on the O family or the 820. Paths are quoted,
`"<drive>/<dir>/<file>"`, 8.3 names; `fd0:` is the floppy, `hd0:` the hard
disk where fitted.

| Command | Notes |
|---|---|
| `FILESystem:CWD "<dir>"` / `?` | current directory |
| `FILESystem:DIR?` | quoted names in the current directory |
| `FILESystem:COPy "<src>","<dst>"`, `:DELEte`, `:REName`, `:MKDir`, `:RMDir` | `*.*` allowed in COPy and DELEte sources |
| `FILESystem:FREESpace?` | bytes free |
| `FILESystem:FORMat "fd0:"` | |
| `FILESystem:OVERWrite ON|OFF` | ON protects files from being overwritten |
| `FILESystem:DELWarn` | front-panel warning only |
| `FILESystem:PRInt "<file>",GPIb|RS232|CENtronics` | send a file to a port |
| `FILESystem:READFile "<file>"` | send a file's bytes out over GPIB (500D/700D in D) |
| `FILESystem:WRITEFile "<file>",<block>` | write a block to a file (500D/700D). 2.9 kB/s on the 784D |
| `SAVe:WAVEform <wfm>,"<file>"`, `RECAll:WAVEform "<file>",REF<x>` | waveform files |
| `SAVe:WAVEform:FILEFormat INTERNal|SPREADSheet|MATHCad` | .WFM, .CSV, .DAT (not 510A) |
| `SAVe:SETUp "<file>"`, `RECAll:SETUp "<file>"` | setups may not move between models or firmware versions |
| `SAVe:ACQDATA CH<x>,"<file>"`, `RECAll:ACQDATA "<file>",CH<x>` | EAL acquisition data, 500D/700D (argument order reversed) |

Events 250-258 are file-system errors (missing media, media full, file name
not found, media protected and so on).

**Hardcopy.**

| Command | Notes |
|---|---|
| `HARDCopy STARt|ABOrt|CLEARSpool` | STARt is a BUSY and OPC operation; O1 has only ABOrt and STARt |
| `HARDCopy:PORT` | `GPIb` (sends the image to the controller), `CENtronics`, `RS232`, and `FILE` on file-system models. O1 has GPIb only; the 820 has GPIb, CENtronics, RS232 |
| `HARDCopy:FILEName "TEK??.BMP"` | with port FILE; each `?` becomes a sequence digit |
| `HARDCopy:FORMat` | O: BMP, DESKJet, DPU411, DPU412, EPSColor, EPSImage, EPSMono, EPSOn, HPGl, INTERLeaf, LASERJet, PCX, THInkjet, TIFf. O1: only DESKJet, EPSImage, EPSOn, HPGl, INTERLeaf, LASERJet, THInkjet. The 820 has O's list without DPU411/DPU412. Later editions add BMPCOLOR, EPSCOLImg, PCXCOLOR, RLE (5XXA/6XXA/7XXA only in A6; not on 400A/510A in C) and DESKJETC (B on). Monochrome models map colour formats to mono and report the mapped name |
| `HARDCopy:LAYout LANDscape|PORTRait` | |
| `HARDCopy:PALEtte CURRent|HARDCopy` | colour models (644C, 684C, 700D) |

Over GPIB: set the port and format, send `HARDCOPY START`, then read raw
bytes until EOI (switch off the read termination character, section 21).
`HARDCopy` is not IEEE 488.2 compatible: while one runs, DCL does not clear the
output queue, so send `HARDCOPY ABORT` first, and put `*WAI` between
consecutive STARts.

## 14. Self-cal, diagnostics, FACtory and *RST

**Signal path compensation.** `*CAL?` runs the internal calibration and
returns 0 on success (O1: 10 warming up, 11 temperature moved over 5 °C, 20
constants reset, 21 failed; the 820 returns -1 on failure). It blocks
everything for 15 s (820), 40 s (520/540), 60 s and more (420/460/620/640) and
"several minutes" by the A to C manuals. Remove
input signals first. The 820 also has `CALibrate:ALL STARt` and
`CALibrate:ALL:STATUs?` → PASS|FAIL|INIT. `CH<x>:PROBECal?` reports probe
calibration on B/C/D.

**Diagnostics.**

```
DIAG:SELECT:ALL ALL               or :ACQUISITION, :CPU, :DISPLAY, :FPANEL with ALL
DIAG:STATE EXECUTE                30 s or more, warm boot, returns to the prior state
DIAG:RESULT:FLAG?                 PASS | FAIL
DIAG:RESULT:LOG?                  "pass--Processor,pass--Display,...,FAIL--Front Panel"
```

`DIAg:STATE EXECute` clears the event queue, input queue, SESR and SBR. PON is
set when it finishes, so `DESE 128;*ESE 128;*SRE 32;*PSC 0` beforehand gives
an SRQ at the end. `*TST?` only tests the GPIB interface and returns 0.

**FACtory** resets the instrument to its factory setup and also: clears ESER
and SRER, sets DESER to 255 and `*PSC` to 1, deletes all aliases, **turns
HEADer on**, empties `*DDT` and cancels pending operations. It keeps the GPIB
address and state, calibration, stored setups, the password and `*PUD`
(C, D). The O and 820 factory tables also list saved waveforms as unchanged,
and D's Appendix C lists the hardcopy settings as unchanged. On the 694C it leaves `TRIGger:TLAAUXiliary:DELay`
alone.

**\*RST** resets the instrument settings but keeps the GPIB settings,
calibration, output queue, SRER, ESER, `*PSC`, aliases, stored setups,
hardcopy settings and `*PUD`. It disables `PASSWord`.

**Factory setup highlights** (App. D of each manual): CH1 on, 100 mV/div, DC,
1 MΩ (50 Ω on the 694C/794D), full bandwidth (no coupling, impedance or
bandwidth on the 820); 500 points; trigger position 50 %;
edge trigger on CH1, rising, 0 V, AUTO (the 820: source External, 1 ns/div);
holdoff 0 % on the O family, 15 µs on the 820; main 500 µs/div on the O family; display Vectors (O)
or Dots (820); MATH1 = CH1+CH2, MATH2 = CH1-CH2 (FFT of CH1 with 2F), MATH3 = INV(CH1); message
box 74,84,475,135; measurement levels 90/50/10 %.

**Protected user data and password.** `PASSWord "XYZZY"` (the factory
password, always valid, case sensitive) enables `*PUD <block>` (up to 100
characters, readable without a password) and `NEWpass "<pw>"` (up to 10
characters) until power-off, `FACtory`, `*RST` or `PASSWord` with no argument.

**Other housekeeping.** `DATE "yyyy-mm-dd"`, `TIMe "hh:mm:ss"` (printed as
`*DATE`/`*TIMe` in some group tables; there is no star), `*DDT` (macro run by
`*TRG` or GET), `REM "<text>"`, `BELl`, `AUTOSet EXECute`, `LOCk ALL|NONe`,
`UNLock ALL`, `VERBose`, `HEADer`.

## 15. TDS 420/460/520/540/620/640

Manual O (070-8318-05) for firmware 2 and the 620/640; O1 (070-8318-01) for
the first 420/460/520/540 firmware (`FV:1.0`). All monochrome. There is no
floppy, no file system and no `*OPT?`: setups go to ten internal slots and
waveforms to REF1-REF4.

| Item | 420/460 | 520 | 540 | 620/640 |
|---|---|---|---|---|
| Inputs | CH1-CH4 | CH1, CH2 and AUX 1/AUX 2 addressed as CH3/CH4 | CH1-CH4 | CH1-CH4 |
| Rear AUX trigger in | yes | no (`AUXiliary` refused) | yes | yes |
| ACQuire:MODe | SAMple, PEAKdetect, HIRes, AVErage, ENVelope | same | same | SAMple, AVErage, ENVelope |
| ACQuire:REPEt | yes | yes | yes | no |
| Record lengths | 500, 1000, 2500, 5000, 15000; 1M adds 30000, 60000 | 500 to 15000; 1M adds 50000 | as 520 | 500, 1000, 2000 |
| Main time/div | 20 s to 1 ns | 10 s to 500 ps, 1-2-5 | same | 5 s to 500 ps, 1-2.5-5 |
| Delay runs after | 10 ns to 20 s, 4 ns resolution | 16 ns to 250 s, 4 ns resolution | same | same |
| Trigger position | 0-100 % | 0-100 % | 0-100 % | 20-80 % |
| Main trigger types | EDGE (VIDeo with option 05) | EDGE, LOGIc, PULse | same | same |
| TRIGger:DELay:BY EVENTSTime | no | yes | yes | yes |
| *CAL? time | 60 s or more | 40 s or more | 40 s or more | 60 s or more |

O1 p.2-6 (the O table is lost in the OCR): "For the TDS 520, CH3 and CH4
represent the front-panel inputs labeled AUX 1 and AUX 2 respectively." Their offset ranges differ from CH1/CH2 (O
Tables 2-22/2-23, p.2-55): CH1/CH2 and all channels of the other models are
±1 V (1-99.5 mV/div), ±10 V (100-995 mV/div), ±100 V (1-10 V/div); the 520's
AUX inputs are ±5 V up to 1 V/div and ±50 V at 5 and 10 V/div.

Options that change the commands: **1M** (longer records), **2F** Advanced DSP
Math (adds `DIF`, `INT`, `FFT` to `MATH<x>:DEFINE`; without it only `INV` and
`+ - *`), **13** RS-232/Centronics (`RS232:*`, `HARDCopy:PORT CENtronics|RS232`),
**05** video trigger on the 420/460 only.

The manual does not give bandwidth or sample rate. From general knowledge,
not checked: 420 about 150 MHz and 460 about 350 MHz at 100 MS/s; 520 and 540
500 MHz at 500 MS/s and 1 GS/s; 620/640 500 MHz at 2 GS/s with short records.

Things that are different on this family:

- `MEASUrement` has 25 types (no NCRoss/PCRoss, no optical, no extinction
  ratio). O's description of `IMMed:VALue?` says the source comes from
  `SELect`; set `MEASUrement:IMMed:SOURCE1` explicitly anyway.
- `TRIGger:MAIn:HOLdoff:VALue` is 0-100 % of the holdoff range, not seconds.
- Hardcopy formats in O: BMP, DESKJet, DPU411, DPU412, EPSColor, EPSImage,
  EPSMono, EPSOn, HPGl, INTERLeaf, LASERJet, PCX, THInkjet, TIFf. O1 had only
  DESKJet, EPSImage, EPSOn, HPGl, INTERLeaf, LASERJet, THInkjet and port GPIb.
- `ALLOcate:WAVEform:REF<x>`: 500, 1000, 2500, 5000, 15000 (plus 30000/60000
  on a 420/460 1M, 50000 on a 520/540 1M); 620/640 500, 1000, 2000. On the
  540 the four REFs together cannot exceed 50000 points.

Changes from O1 to O (worth knowing if the scope reports `FV:1.x`):

- New in O: `DATE`, `TIMe`, `DISplay:CLOCk`, `DISplay:TRIGBar`, `CURSor:MODe`,
  `CURSor:PAIred:*`, all `LIMit:*`, `ACQuire:STOPAfter LIMit`,
  `DISplay:STYle INTENSIFied`, `MEASUrement:SNAPShot`, the AREA, CARea and
  PHASE measurements, `RS232:*`, `TEKSecure`, logic-trigger `WHEn` limits,
  `TRIGger:DELay:BY EVENTSTime` and MATH DIF/INT/FFT. (The summary queries
  such as `CH<x>?`, `MATH<x>?` and `SELect?` are already in O1.)
- `*CAL?` in O1 returns 0, or 10 (still warming up), 11 (temperature moved more
  than 5° since the last cal), 20 (constants reset to factory, power lost
  during cal) or 21 (cal failed). O only says non-zero means failure.
- ASCII `CURVe` in O1 is always one byte per point (-128..127) whatever
  `DATa:WIDth` says. In O it follows `DATa:WIDth`.
- O1 says the base 420/460 lacks 15000 points and 1M adds 15000 and 30000.
- O1 marks `TRIGger:MAIn:EDGE:SOUrce` and `TRIGger:DELay:EDGE:SOUrce` as
  420/460/540 only.
- Event 202 "Settings lost due to rtl" is in O1 but not O (it returns in A to D).

Undocumented: the `*LRN?` example shows `:DIAG:LOOP:OPTION ONCE;COUNT 1;:DIAG:STATE HALT`
and Appendix B lists reserved words ONCe, ALWays, OPTion, HALt, EXERciser,
SELFdiag, FIRst, CYCLE, LOG, REFSelect, XYZ, YZ with no documented command.
They look like diagnostic loop commands (`DIAg:LOOP:*`, `DIAg:STATE HALT`)
that none of the eight manuals document. Untested.

## 16. TDS 820

Manual T (070-8513-01). The TDS 820 is a two-channel **sequential
equivalent-time sampling** scope: one sample per trigger, with the delay
stepped after each trigger, so a record is built over many triggers
(T Glossary-1). Most of the differences follow from that. The manual gives no
bandwidth; from general knowledge it is a 6 GHz, 50 Ω scope (not checked).

Waveforms: CH1, CH2, MATH1-3, REF1-4. Record lengths 500, 1000, 2500, 5000,
15000. Main and delayed time/div 20 ps to 500 ms, rounded to 10 ps
(T p.2-125). CH<x>:SCAle 1 mV to 10 V/div at 1X, position ±5 div. Data is
16-bit. `*IDN?` gives `TEKTRONIX,TDS820,0,CF:91.1CT FV:2.0` and `ID?` gives
`ID TEK/TDS820,0,CF:91.1CT,FV:2.0` (T p.2-133). The manual does not state the
default GPIB address.

**Option 1D** removes the input delay lines. Then CH1/CH2 cannot be the
trigger source (`TRIGger:SOUrce CH<x>` gives a parameter error, T p.2-207), the
time base position starts at +16 ns instead of -1.5 ns, and offset at 1X is
±1 V instead of ±2 V. Setting the source to CH1 and checking for an error is a
way to detect 1D.

How it differs from the real-time TDS:

- **No pretrigger.** The record is placed with `HORizontal:TBPosition`
  (also `:MAIn:TBPosition`, `:DELay:TBPosition`): seconds from the trigger to
  the first sample, -1.5 ns (16 ns with 1D) to 50 ms, 1 ps steps (T p.2-126,
  2-132). `HORizontal:POSition` only pans the display. There is no
  `HORizontal:TRIGger:POSition`, `HORizontal:DELay:TIMe` or `FITtoscreen`.
- `HORizontal:MODe MAIn|INTENSIFied|DELAYEd`; the delayed time base has only
  SCAle and TBPosition. `HORizontal:DESKew:CH<x>` 0 to 10 ns, 1 ps steps.
- **Trigger** is edge only, with its own short tree: `TRIGger:SOUrce CH<x>|EXTernal|INTClock`
  (EXTernal is the rear Auxiliary Trigger Input and is the **factory
  default**), `TRIGger:LEVel`, `:SLOpe`, `:MODe AUTO|NORMal` (AUTO forces a
  record after 50 ms), `TRIGger:INTRate` 10 Hz to 500 kHz in 1-2-5 steps
  (default 100 kHz, used with INTClock), `TRIGger:HOLdoff:VALue` **15 µs to 2 s
  in seconds**, `TRIGger:HOLdoff:ACTUal?`, `TRIGger:MAXSamprate?` (1/holdoff,
  or the slower of INTRate and 1/holdoff for INTClock), `TRIGger SETLevel`.
  `TRIGger:MAIn:*` forms are aliases. `TRIGger:STATE?` returns
  REAdy|TRIGger|SAVe|AUTO (no ARMED/PARTIAL). There is no `TRIGger FORCe`, no
  coupling, no B trigger and no logic, pulse or video trigger.
- `ACQuire:MODe NORMal|AVErage|ENVelope`. The mode is **NORMal, not SAMple**;
  there is no PEAKdetect, HIRes or REPEt. `ACQuire:STOPAfter RUNSTop|LIMit|SEQuence`.
  `NUMAVg` 2-10000, `NUMEnv` 1-2000 or INFInite.
- No `CH<x>:COUPling`, `:IMPedance` or `:BANdwidth`. `CH<x>:PRObe?` returns
  gain (a 10X probe reads 100.0E-3). External attenuation is
  `CH<x>:PROBEFunct:EXTAtten` (1E-6 to 1E6) and `:EXTDBatten` (±120 dB); note
  the spelling **PROBEFunct**, where the C and D manuals have `PROBEFunc`.
- `CALibrate:ALL STARt` then `CALibrate:ALL:STATUs?` → PASS|FAIL|INIT (INIT:
  defaults restored after memory loss, calibrate before use). `*CAL?` returns
  0 or -1 and takes 15 s or more; remove signals first.
- `GRAPhics:*` draws up to 100 line points on the graticule:
  `GRAPhics:POInts x,y[,x,y...]` (a negative X means move-to), `:MOVe`,
  `:DRAw`, `:DISplay`, `:DELEte ALL`, `:NUMPoints?`. Coordinates X 24-524,
  Y 34-434 graticule pixels; brightness follows `DISplay:INTENSITy:TEXt`.
  No other TDS has this.
- `MEASUrement` has 27 types: O's 25 plus NCRoss and PCRoss (time from
  trigger to the negative/positive mid crossing). T says this time can be
  negative only on option 1D units (no delay lines), which looks backwards,
  since only delay lines let the record start before the trigger; check on
  the scope.
- `LIMit:*` template testing (as on O), `TEKSecure`, `DISplay:TRIGBar
  OFF|SHORT|LONG`, `MESSage:*`, `APPMenu:*`, `ZOOm:*`.
- `HARDCopy:PORT GPIb|CENtronics|RS232`, no file or disk; formats BMP,
  DESKJet, EPSColor, EPSImage, EPSMono, EPSOn, HPGl, INTERLeaf, LASERJet, PCX,
  THInkjet, TIFf.
- `ALLOcate:WAVEform:REF<x>` sizes 500, 1000, 2500, 15000, 50000 (no 5000);
  the four REFs share 50000 points. Other values round up.
- No `*OPT?`, no file system, no `DIAg:LOOP` (the `*LRN?` example on p.2-144
  shows one; it was copied from another model). `*TST?` always returns 0.

Waveform transfer differences: `WFMPre:<wfm>:PT_Off` **always returns 0**
(T p.2-223). The trigger-relative time comes from
`WFMPre:<wfm>:XZEro`, which on the 820 is the time base position (trigger to
first record point). Taking n from 0 at the first transferred point,
`t(n) = XZEro + XINcr * (DATa:STARt - 1 + n)`. That is an interpretation; the
manual's own X formula leaves XZEro out, so check it with `DATa:STARt` above 1
before relying on it. XINcr is the
equivalent-time spacing, not a sample clock. A full record needs at least as
many triggers as points: at the 15 µs minimum holdoff (about 66.7 kHz) a
15000-point record takes at least 0.22 s, and averaging multiplies that.
Up to 15000 points per `CURVe?`.

Event codes 2250-2269 are the 820's own sampler and VCO calibration errors,
each prefixed "Calibration error, ":
2250 Strobe delay meas failed, 2251 HLUT entry out of bounds, 2252 HLUT
corrections not working, 2253 Excessive amplitude on DC measurement, 2254
Excessive offset on DC measurement, 2255 Incorrect forward gain at sampler,
2256 VLUT underrange cannot be calculated, 2257 VLUT overrange cannot be
calculated, 2260 Calibration error, 2261 VCO coarse DAC out of bounds, 2262
VCO coarse DAC nonfunctional, 2263 VCO coarse DAC did not converge, 2264 VCO
fine DAC nonfunctional, 2265 VCO fine DAC did not converge, 2266 VCO tcgain
DAC out of bounds, 2267 VCO frequency measurement failed, 2268 Diagnostic A/D
timed out, 2269 VCO wrap delay out of bounds.

Factory settings that catch people (T App. D): trigger source **External**,
mode Auto, holdoff 15 µs, level 0 V; 1 ns/div, 500 points, main TB position
-1.5 ns (16 ns with 1D); 100 mV/div; display style Dots. After `FACtory` or
`*RST`, a signal on CH1 with nothing on EXT gives untriggered AUTO records:
send `TRIGger:SOUrce CH1` (needs delay lines) or use INTClock.

Manual errors in T: the `*LRN?` example's `DIAG:LOOP`; `DATE` and `TIMe`
printed as `*DATE`/`*TIMe` in Table 2-15; the HORizontal:DELay related-commands
list names `DELay:MODe?` and `DELay:TIMe?`, which do not exist;
`TRIGger:MAIn:HOLdoff:VALue` shown as `<NR1>` on p.2-205 (send NR3 seconds,
as `TRIGger:HOLdoff:VALue` on p.2-202 shows); NCRoss/PCRoss said to go negative
only without delay lines;
the CURVe block's `<yyy>` is said to include a checksum (none is sent;
`WFMPre:CRVchk` is accepted and ignored).

## 17. A, B and C series

Five editions of the "TDS Family Programmer Manual" cover the A, B and C
generations. Their syntax, status chapter, encodings and example programs are
the same; what changes is which models get which commands.

| Code | Manual | Models (shorthand used in its qualifiers) |
|---|---|---|
| A6 | 070-8709-06 (Nov 1994) | TDS 410/420/460 ("4XX"), 520A/524A/540A/544A ("5XXA"), 620A/640A/644A/684A ("6XXA"), 744A/784A ("7XXA") |
| A7 | 070-8709-07 (1995) | as A6 with 410A/420A/460A ("4XXA") |
| B | 070-9556-00 | 410A/420A/460A ("400A"), 520B/540B ("500B"), 620B/644B/680B/684B ("600B"), 724A/744A/784A ("700A") |
| B2 | 070-9702-00 | drops 410A; adds 430A, 510A, 754A, 782A ("700A" = 724A/744A/754A/782A/784A) |
| C | 070-9876-00 | 420A/430A/460A ("400A"), 510A, 520C/540C ("500C"), 620B/644B/680B/684B ("600B"), 724C/754C/784C ("700C") |

**AUX inputs as CH3/CH4** (reduced range: offset ±0.5 V at 50/100 mV/div,
±5 V at 500 mV/1 V, ±50 V at 5/10 V/div; only those six scales listed):
520A, 524A, 620A (A6/A7); 520B, 620B, 680B, 724A (B); plus 782A (B2); 520C,
620B, 680B, 724C (C). **No rear AUX trigger input** (`AUXiliary` refused):
520A, 524A; 520B, 724A; 782A; 520C, 724C. The 410/410A have two channels;
the 430A probably too (C's XY table excludes it from the CH3/CH4 pair).

**Colour models** (`DISplay:COLOr:*`, `HARDCopy:PALEtte`): 524A, 544A, 644A,
684A, 744A, 784A (A6/A7); 6X4B and 7X4A (B); 6X4B and 700A (B2); 6X4B and 700C
(C). The B and C 500s are monochrome. `DISplay:INTENSITy:OVERALL` and
`:CONTRast` are for the monochrome ones.

**Options.**

| Option | Meaning |
|---|---|
| 1M | longer records: 4XX 30000/60000 (A6); 4XXA/400A 60000, 120000; 5XXA 50000; 7XXA/700x 75000 to 500000; not on 510A; 600B has none |
| 2M | extended acquisition length, 500C and 700C (C only) |
| 1F | file system: floppy `fd0:` (C also mentions an HD file system, `hd0:`) |
| 2F | Advanced DSP Math (DIF, INT, FFT; math averaging on some). Optional on 420/460/520A/540A/620A/640A (A); 420A/460A/520B/540B/620B/680B (B); adds 430A, 510A, 520C, 540C (B2, C). Standard on the rest. Missing gives event 572 (B on) |
| 13 | RS-232/Centronics hardcopy ports and `RS232:*` |
| 05 | video trigger; two different command sets (400A style and 510A/500/600/700 style, section 9). Missing gives event 571 (B on) |

`*OPT?` exists on 5XXA/6XXA/7XXA (A), 500B/600B/700A (B), everything except
the 400A (B2, C). Example: `13:Rs232/cent,1M:extended record length,2F:math pack,05:video trigger,0,CD:color display`.

**Record lengths.** A6: 4XX 500-15000 (1M 30000, 60000); 5XXA 500-15000 (1M
50000); 620A/640A/644A 500, 1000, 2000; 684A 500-15000; 7XXA 500-15000 and
50000 (1M 75000, 100000, 130000, 250000, 500000). From A7: 410A/420A/460A
standard to 30000, 1M 60000 and 120000. C Table 2-32: 400A to 30000 (1M 60000,
120000); 510A/520C/724C to 50000 (1M on 520C/724C 75000, 100000, 130000,
250000); 600B to 15000, no options; 540C/754C/784C to 50000 (1M to 500000).
Reference memory (C Table 2-26) lists how many REFs fit: 400A 30000 (4),
60000 (2), 120000 (1); 520C/724C 75000 (3), 100000 (2), 130000 (2), 250000
(1); 540C/754C/784C 50000 (4), 75000 (3), 100000/130000 (2), 250000 (1),
500000 (no complete REF).

**Time base.** Main 400A 20 s to 1 ns; 510A/500/600B/700 10 s to 500 ps (200 ps
on the 784A; C repeats B's wording and never names the 784C) in 1-2-5; the 620A/640A/644A run 5 s to 500 ps in 1-2.5-5.
Delay time 16 ns to 250 s in 4 ns steps (400A: 10 ns or 60 ns to 20 s).
External clock and roll mode (`HORizontal:CLOCk`, `:CLOCk:MAXRate`,
`HORizontal:ROLL`) are 4XXA/400A only; with the external clock on, the 400A's
time units become clocks and `CURSor:VBArs:UNITS` gains BASe/INVert.

**Acquisition modes.** No HIRes on any 600 model. 620A/640A/644A/684A also
lack PEAKdetect; the 600B gained it. ACQuire:REPEt: 400A, 510A, 500x, 700x.
ACQuire:AUTOSAve: 7XXA and some 6XXA (A), 500x/600B/700x later.

**Feature spread by edition.**

- A6: logic and pulse triggers on 5XXA/6XXA/7XXA. Setup/hold, slew rate, runt
  WHEn/WIDth, `THReshold:BOTh`, holdoff `BY`/`TIMe`/`ACTUal?`, the 250 MHz
  bandwidth limit and delayed coupling `MAINTrigger` only on 684A and 7XXA
  (which lack `HOLDOff:VALue`). InstaVu 7XXA only; FastFrame 5XXA and 7XXA;
  dual zoom 7XXA; `SAVe:WAVEform:FILEFormat` 7XXA. Separate headings
  `CURSor:PAIred:POSITION1` and `POSITION2`.
- A7: the 4XXA low end; adds `HORizontal:CLOCk`, the percent cursor forms
  (`CURSor:HBArs:POSITION<x>Pcnt`, `VBArs:POSITION<x>Pcnt`,
  `PAIred:POSITION<x>Pcnt`, `VBArs:UNITSTring?`) and
  `TRIGger:MAIn:VIDeo:SCANPeriod`, all 4XXA only; merges the paired-cursor
  setters into `CURSor:PAIred:POSITION<x>`; introduces the record-length and
  allocation tables; changes STOP < START handling (section 11).
- B: the 684A/7XXA-only trigger features spread to 500B/600B/700A; InstaVu and
  FastFrame on 500B and 700A; adds `CH<x>:DESKew`, `CH<x>:PROBECal?`, the
  TIMEOut pulse class, `WFMPre:<wfm>:XZEro` (XZERO appears in `WFMPRE?`),
  a full `HORizontal:ROLL` entry (A7 lists it only in its summary), hardcopy
  DESKJETC; events 2238, 570, 571, 572. Dual zoom and
  `SAVe:WAVEform:FILEFormat` widen to 400A/500B/600B/700A. `HOLDOff:VALue`
  becomes 400A only.
- B2: no new headers; the 510A joins with its own limits (no 1M, no dual zoom,
  no FILEFormat, 100 MHz bandwidth limit, percent holdoff).
- C: 500C and 700C add extended acquisition (`HORizontal:EXTDACQ`,
  `:RECORDSTART`, `:ACQLENGTH?`, `:ACQDURATION?`, `DATa RECORDSNAp`,
  `SAVe/RECAll:ACQDATA`), `HIStogram:*`, `MASK:*`, the communication trigger,
  measurement statistics and histogram/optical types,
  `CH<x>:PROBEFunc:EXTAtten`/`EXTDBatten`, `FILESystem:READFile`/`WRITEFile`;
  events 2239, 2258, 2259, 2281, 552, 553. `ID?` example becomes TDS 784C
  v5.0e.

**InstaVu** (7XXA; 500B/700A; 500C/700C). `DISplay:MODe INStavu|NORMal`,
`DISplay:INStavu:PERSistence INFPersist|VARpersist`, `:STYle DOTs|VECtors`,
`:VARpersist`. It forces a 500-point record and turns off averaging,
envelope, zoom, autosave, limit test, math, FastFrame and XY; `TRIGger:STATE?`
returns INSTAVU. D renames it "DPO".

**Cursor units.** `CURSor:HBArs:UNITS BASe|IRE` and `CURSor:PAIred:UNITS`
(IRE for video); `CURSor:VBArs:UNITS SECOnds|HERtz|LINE` (LINE with option 05).

**Display.** `DISplay:GRAticule` adds NTSc and PAL. Colour palette items:
BACKGround, CH1-4, MATH, REF, TEXt, SCROLLTEXT, ZONe, COLLision, GRAticule,
SCROLLBAR and (700C) HISTOMask.

**`*CAL?`** "can take several minutes" in these manuals; there is no
`CALibrate:*` subsystem. 500C/600B/700C: an active 50 Ω probe cuts the maximum
scale from 10 V/div to 1 V/div.

**Factory setup differences** (C App. D): repetitive ON on 400A/510A/500C/700C;
intensity text/waveform 100 % on colour models, 60/75 % on monochrome;
contrast 175 % (510A 150 %); zoom 2.0X (510A 1.0X); MATH2 becomes an FFT of
CH1 when 2F is fitted; logic thresholds 1.4 V (clipped to 1.2 V at the default
scale without a 10X probe); setup 3 ns, hold 2 ns.

**Manual errors in these editions.** The encoding table prints SRIbinary
twice (the second row is SRPbinary). C's FastFrame headers say "500C & 700A";
"640B" appears in the option-13 list (B, B2, C); C's time-base text keeps B's
"500B ... 700A" names; C's factory table gives "680A" overall intensity for
the 680B; the zoom group table spells "ZOOm:GRAticle"; the `CH<x>:SCAle` text
says "100 mV per division to 1 mV per division";
the `WFMPre?` example shows `NR_PT 1` for a 500-point record; ENV pairs are
described both as max/min and min/max; `WAVPre?` is listed with no
description; the alias-off error is given as both 102 and 110. The `*LRN?`
output in every edition contains `:DIAG:LOOP:OPTION ONCE;COUNT 1;:DIAG:STATE HALT`,
so the firmware has `DIAg:LOOP:*` and `DIAg:STATE HALT`, which no manual
describes.

## 18. TDS 400A, 510A, 500D, 600C, 700D and 694C

Manual D (063-3060-00), the WinHelp "TDS694C Programmer's Manual" on floppy
(1999, 542 topics). Despite its title it is the shared family text for the TDS
400A, 510A, 500D, 600C and 700D, with 694C notes added. Models named in it:
TDS 420A, 430A, 460A, 510A, 520D, 540D, 580D, 724D, 754D, 784D, 794D, 640C,
644C, 680C, 684C, 694C. The command set is C's plus a few additions (below);
the event codes are the same 199 as C. A readable PDF of D exists, rebuilt in the Tek house style.

**Model groups used in the qualifiers.**

- 400A: TDS 420A, 430A, 460A. 510A: TDS 510A.
- 500D: TDS 520D, 540D, 580D. 700D: TDS 724D, 754D, 784D, 794D.
- 600C: TDS 640C, 644C, 680C, 684C, 694C. "6X4C" means the colour ones (644C,
  684C, 694C), "6X0C" the monochrome ones (640C, 680C).
- **2+2 models** (two full channels plus AUX 1/AUX 2 as CH3/CH4): TDS 520D,
  680C, 724D. The 520D and 724D have no rear AUX trigger input, so
  `AUXiliary` is refused as a trigger source.
- The TDS 794D is the 700D twin of the 694C and shares its input notes.

**500D/700D only** (so not on a 600C or a 694C): communication trigger, mask
testing, FastFrame and time stamps, DPO (InstaVu) display, extended
acquisition length (option 2M), `HORizontal:RECORDSTART`, `:ACQLENGTH?`,
`:ACQDURATION?`, `SAVe/RECAll:ACQDATA`, `SAVe/RECAll:IMAGEHistogram`,
`FILESystem:READFile/WRITEFile`, `DATa RECORDSNAp`, `DISplay:MODe`,
`DISplay:INStavu:*`. On a 600C expect a command or execution error (D does not
say which).

**500D, 600C and 700D** (also the 694C): histograms, measurement statistics,
slew-rate and timeout pulse triggers, setup/hold logic trigger, runt
WHEn/WIDth, holdoff by time, `ACQuire:AUTOSAve`, `CH<x>:DESKew`,
`CH<x>:PROBECal?`, `CH<x>:PROBEFunc`, `APPLication:*` (Java applications and the
GP knob), `MESSage:OPAQue` and `:PRIOrity`, extinction-ratio and histogram
measurement types, colour commands (6X4C and 700D), dual zoom and zoom preview.

**TDS 694C specifics** (and the 794D where noted):

- **50 Ω inputs only.** `CH<x>:IMPedance MEG` is not available on the 694C or
  794D; factory impedance is 50 Ω there, 1 MΩ on everything else.
- `CH<x>:SCAle`: 10 mV to 1 V/div at 1X; 10 mV to 100 V/div with a P6339A
  probe. Other models: 1 mV to 10 V/div.
- `CH<x>:BANdwidth TWEnty|HUNdred|ONEFifty|TWOfifty|FULl`. The 694C/794D have
  TWEnty, ONEFifty and FULl with a P6339A and only FULl without it.
  ONEFifty = 150 MHz (694C/794D with P6339A), HUNdred = 100 MHz (400A, 510A),
  TWOfifty = 250 MHz (500D/600C/700D).
- AC coupling needs a P6339A.
- Offset ranges (D's Table 2-27 for the 694C/794D) are damaged in the help:
  as printed "10 mV/div & 50 mV/div ±0.5 V; 50.5 mV/div & 100 mV/div ±0.25 V;
  101 V/div & 500 mV/div +5 V; 505 mV/div & 1 V/div +2.5 V". It reads as two
  attenuator ranges (10-100 mV and 101 mV-1 V/div) each with two offset
  windows. Measure before relying on it.
- `HORizontal:MAIn:SCAle` down to **100 ps/div** (200 ps on 684C/784D/794D,
  500 ps on 510A/500D/600C/700D; 640C/644C step 1-2.5-5).
- Record length: 500, 1000, 2500, 5000, 15000 and **30000** standard; with
  option 1M 30000, 50000, 75000, 100000, 120000. The ALLOcate table has no
  694C row for these, so read `ALLOCATE:WAVEFORM:FREE?` instead of trusting
  it.
- `ACQuire:MODe` on the 600C has **no HIRes**, and there is no `ACQuire:REPEt`
  (real-time only). The help does not state the sample rate.
- `TRIGger:MAIn:EDGE:SOUrce` adds **`TLAAUXiliary`** (694C only): the rear AUX
  trigger input with a compensating delay for a Tektronix TLA logic analyser.
  `TRIGger:TLAAUXiliary:DELay <NR3>` 0 to 750 ns in 1 ns steps, applied only
  with an edge trigger on TLAAUXiliary. `FACtory` and `*RST` leave it alone.
  The `TRIGger?` example shows `:TRIGGER:TLAAUXILIARY:DELAY 350` with no unit;
  read it back with `HEADER ON` to see what it really returns.
- `DISplay:INTENSITy:OVERALL` and `:CONTRast` are 400A/510A/500D/6X0C only.
- Check event 630 (50 Ω overload) after any overdrive.

**Commands in D and not in C.** `TRIGger:TLAAUXiliary:DELay` and the
TLAAUXiliary source; `MASK:AUTOSet:STANdard`, `MASK:INVert`,
`MASK:MARgin:PERCent` (-50 to +50 %, positive is harder to pass),
`MASK:MARgin:STATE`, `MASK:PASSFail:BELl|STATE|STATUs?|THReshold|WAVEform`;
`MESSage:OPAQue`, `MESSage:PRIOrity` (default 6; error windows are 5; higher
draws on top); `SAVe:IMAGEHistogram`, `RECAll:IMAGEHistogram`;
`DISplay:INStavu:ACCUmulate SHALlow|DEEP`, `:AUTOBright`, `:BRIGHTness`,
`:CONTRast`, `:MAP PERCent|INTENSITy`, `:PERCent:P<x>`;
`HORizontal:FASTframe:FRAMELock`, `:REF` and the `:TIMEStamp` subtree;
`APPLication:ACTivate "<path>"` and `APPLication:GPKNOB:*`; the `ONEFifty`
bandwidth; `TRIGger:DELay:EDGE:COUPling MAINTrigger`; Ethernet (ENET10,
ENET100, ENET1250) and VIDEO360 standards in the mask and communication
trigger lists, masks DS1Rate and DS3Time. The C manual's family had the rest
(base mask set, FastFrame count/length/position, histogram, file system, EAL,
communication trigger, slew rate, timeout, FlexFormat video).

**Masks** (500D/700D). `MASK:STANdard <std>` builds masks 1..n for a telecom
standard (OC1, OC3, OC12, DS0Single ... DS3, E1-E5, STM1E, STS1, STS3, FC133
... FC1063, D1, D2, VIDEO360, ENET..., FDDI, NONe, USERMask). The help prints
`DSOSingle` with a letter O in one syntax line; the argument is `DS0Single`
with a zero. User masks: `MASK:MASK<x>:POINTS t1,v1,t2,v2,...` (user units,
up to 50 points, x = 1-8) or `:POINTSPcnt` (0,0 top left to 100,100 bottom
right; 500 × 200 pixel resolution). Counting: `MASK:SOUrce CH<x>`,
`MASK:COUNt:STATE ON`, `MASK:COUNt RESET`, `MASK:COUNt:TOTal?`,
`MASK:MASK<x>:COUNt?`, `MASK:COUNt:WAVEFORMS?`. Pass/fail:
`MASK:PASSFail:THReshold <hits>`, `:WAVEform <n>` (default 20), `:STATE ON`,
`:STATUs?` → PASSING, PASSED or FAILED. `MASK:FILTer ENAble` (optical
reference receiver) works only with an optical standard, the matching time/div,
500 points, one channel, full bandwidth. On the 784D, masks written from
inside the instrument by a Java application lost their horizontal coordinates
(TDS Toolkit bench work); over GPIB this is untested.

**FastFrame** (500D/700D). `HORizontal:FASTframe:LENgth <points>`,
`:COUNt <frames>`, `:STATE ON`, then `ACQUIRE:STATE RUN`; the scope is ready
for the burst 400 ms later. While it is on, `TRIGger:STATE?` returns
`FASTFRAME`, so wait with `*OPC?` or `BUSY?`. `:POSition <n>` selects the frame
shown. Time stamps (D only, need FastFrame on): `:TIMEStamp:STATE ON`,
`:TIMEStamp:FRAme? <n>` (text: `@Pos: n`, `DD MMM YYYY`, `HH:MM:SS.mmm`,
`uuu,nnn,ppp`), `:TIMEStamp:DELTa?` (position frame minus reference frame),
`:TIMEStamp:BETWeen? <a>,<b>` (a query with arguments), `:REF <n>`.

**DPO / InstaVu** (500D/700D). `DISplay:MODe INStavu|NORMal`. DPO uses a
500-point record with no averaging or envelope and turns off zoom, autosave,
limit test, math, FastFrame and XY until it is switched off. `TRIGger:STATE?`
returns `INSTAVU`. `DISplay:FORMat XYZ` works only in DPO (CH1 = X, CH2 = Y,
CH3 = intensity; not on 2+2 models).

**Extended acquisition (EAL, option 2M, 500D/700D).** `HORizontal:EXTDACQ ON`
(DPO must be off). Acquisition/waveform record: 1 channel 8 M / 500 k, 2
channels 4 M / 250 k, 3-4 channels 2 M / 100 k (2+2 models: 4 M and 2 M).
`HORizontal:RECORDSTART` (0 to 93.75 % for 4 M and 8 M, 95 % for 2 M) places
the waveform record in the acquisition; `HORizontal:ACQLENGTH?` and
`:ACQDURATION?` report it. To fetch acquisition data: `DATA:SOURCE CH<x>`,
`DATA RECORDSNAP` (sets START/STOP to the whole acquisition), `CURVE?`. In EAL
`ACQuire:MODe` acts as SAMple except PEAKdetect; `ACQuire:AUTOSAve`,
`STOPAfter`, `CH<x>:DESKew`, `RECOrdlength`, `LIMit:STATE` and FastFrame
accept settings and do nothing (read-back is not proof); math is refused
(552/553). `AUTOSet EXECute` and a histogram turn EAL off (event 2239). An
8 M record in ASCII is over 26.8 MB and can take more than 25 minutes; use
binary. On the 784D, 2M lengths are reachable only with Extended Acquisition
on (section 19).

**Reference memory** (D Table 2-23). 400A: standard 500 to 30000 (4 refs);
1M 60000 (2 refs), 120000 (1 ref). 510A/520D/724D: standard to 50000; option
75000 (3), 100000 (2), 130000 (2), 250000 (1). 540D/754D/784D: standard to
50000 (4 refs); option 75000 (3), 100000 (2), 130000 (2), 250000 (1), 500000
(no complete ref). Odd sizes round up (15002 on a 520D/1M becomes 50000).
Saving a 500 k waveform on a 700D decimates it to 250 k (warning 570).

**Save and recall to disk** (option 1F on the C/D families; `fd0:` floppy,
`hd0:` hard disk where fitted). `SAVe:WAVEform:FILEFormat INTERNal|SPREADSheet|MATHCad`
(.WFM, .CSV, .DAT; not on 510A); the MathCad file is ASCII, CR-separated,
with record length, sample interval, trigger index and fractional trigger
position at the top. `SAVe:SETUp "<path>"`, `RECAll:SETUp "<path>"`.
`SAVe:ACQDATA CH<x>,"<path>"` but `RECAll:ACQDATA "<path>",CH<x>` (arguments
reversed). Setups may not transfer between models or firmware versions.

**Interfaces.** D's Appendix B lists GPIB only: RS-232 on these models is a
hardcopy port (option 13), not a control port.

**`*OPT?`** example: `13:Rs232/cent,1M:extended record length,2F:math pack,05:video trigger,0,CD:color display`.

**Errors in D.** Wrong syntax lines in the slew-rate topics
(`PULse:RUNT:DELTATime`, `SLEWRate:THReshold:WHEn`), `EXTAtten:<NR3>` with a
colon (send a space), the topic title "EXTBatten" (the command is
`EXTDBatten`), `DSOSingle` for `DS0Single`, `ZOOm DUAl` written with a space,
`TRIGger:MAIn:STATE:WHEn` for `TRIGger:MAIn:LOGIc:STATE:WHEn`, `DS3 Rate` for
`DS3Rate`, the `MASK?` example's `:MSK:` and `:MSAK:`, the
`FILESYSTEM:WRITEFILE` example `#21hello world` (needs `#211hello world`),
`RECAll:IMAGEHistogram` example using `.IMG` where save requires `.IMH`,
`NEGSynchwidth` in a topic title for `NEGSyncwidth`, the `MEANDBM`
description copied from MEDian, and a reserved-word list that misses the new
keywords (GPKNOB, TLAAUXiliary, PASSFail and others).

## 19. TDS 784D bench notes

Measured on a reference TDS 784D (firmware v7.4e) through a Keysight 82357B at `GPIB0::3::INSTR`. None of this is in the manuals. The 784D is a
D-generation scope (section 18) but behaves like a 7xxA in several places.

**The horizontal scale sets the sample rate.** The acquisition always takes
50 points per division, so `sample rate = 50 / (s/div)` and
`duration = record length / sample rate`. Record length and time/div are
independent. At 5 ms/div the rate is 10 kS/s for any record length, and a
15000-point record spans 1.5 s, not the 50 ms the screen suggests. If edges
come out one sample wide and `XINCR` is 100.0E-6, this is why. For 9600 baud
serial, 100 µs/div gives 500 kS/s (52 samples per bit) and 500 µs/div gives
100 kS/s (10.4).

**The display shows 500 points**, one per pixel, 50 per division. A long
record can look like a flat line while holding everything. `HORIZONTAL:POSITION`
is the percentage of the record left of the **centre** graticule, so the
visible window starts 250 points before it. Set `HORIZONTAL:POSITION` equal to
`HORIZONTAL:TRIGGER:POSITION` to put the window on the trigger.

**Holdoff is set by time.** `TRIGGER:MAIN:HOLDOFF:VALUE` is accepted without an
error and does nothing. This works (250 ns to 12 s):

```
TRIGGER:MAIN:HOLDOFF:BY TIME
TRIGGER:MAIN:HOLDOFF:TIME 40E-3
TRIGGER:MAIN:HOLDOFF:ACTUAL?
```

A holdoff longer than a repeating message but shorter than its period makes
every trigger land on the message's first edge, which makes captures of
periodic traffic repeatable.

**WFMPRE sub-queries time out.** `WFMPRE:XINCR?`, `WFMPRE:XZERO?` and
`WFMPRE:PT_OFF?` all time out. Ask for the whole `WFMPRE?` with `HEADER ON` and
parse it by name (with `HEADER OFF` it is positional). On the 784D the field
order is XINCR, XZERO, PT_OFF, not the XINCR, PT_OFF, XZERO the manuals print.
XZERO is a sub-sample trigger offset of a few microseconds, not the time of the
first point: `t(i) = XZERO + (i - PT_OFF) * XINCR`.

**`HORIZONTAL:MAIN:SAMPLERATE?` does not exist** (event 113).

**`FACTORY` leaves `HEADER ON`.** Every query then answers with its own header
and `float()` fails mid-script. Send `HEADER OFF` after every `FACTORY`.

**Reference waveforms as a drawing surface.** A REF is scaled at
**6400 counts per division** (16-bit levels; the graticule is 10.24 divisions
of them), so a sample value is a screen position. Verified: a baseline asked
for at -2.90 div landed on row 379 against 380 predicted. There is no
`REF<x>:POSition` or `:SCAle`; a REF is placed by the preamble stored with it.
Run `ALLOCATE:WAVEFORM:REF<x> <n>` first; `ALLOCATE:WAVEFORM:FREE?` showed
260 500 points free.

**`MESSAGE:OPAQUE ON|OFF` is undocumented but works.** With OPAQUE ON the box
background is filled. There is one message box. The screen font is
proportional (space 5 px, digits 10, M/W/m 15, line pitch 15 px), so lay text
out by pixels, not character count.

**Long hardcopy hazard.** After a `HARDCOPY` that ran 230 s, started while
the scope swept at 1 s/div, the scope stopped drawing any waveform (channels
and references) while graticule, readouts, message box, triggering,
`MEASUREMENT:IMMED` and `CURVE?` all kept working. `SELECT` toggles,
`DISPLAY:STYLE`, `:FORMAT`, `:PERSISTENCE`, `:INTENSITY:WAVEFORM`, `:FILTER`,
`CLEARMENU`, freeing REF memory and `FACTORY` did not bring it back. A power
cycle is the untested remedy. Don't start a hardcopy when the timebase is so
slow that an acquisition cannot finish within it.

**2M memory (EAL).** Option 2M is Extended Acquisition Length. With Extended
Acquisition off, `HORIZONTAL:RECORDLENGTH` stops at 500 000; the 2 M, 4 M and
8 M lengths need it on. `HORIZONTAL:RECORDLENGTH` is the waveform record, not
the acquisition length (front-panel Acq Len). The C manual's `CURVe` entry
says that in extended-acquisition mode `CURVe?` on a channel can return the
acquisition record (C p.2-96).

**Timings** (82357B):

| Operation | Time |
|---|---|
| `CURVE?` 15 000 points, RIBINARY, width 2 | 0.09 s |
| `CURVE?` 50 000 points | 0.24 s |
| `FILESYSTEM:WRITEFILE` | 2.9 kB/s |
| Hardcopy capture and read back | about 6 s |

**16-bit references** (TDS Toolkit, 2026-11-01): an averaged waveform saved
to a REF kept its low bytes (2497 of 2500 non-zero), and a 16-bit `.wfm`
restored identical.

**Service territory.** The NVRAM bootloader answers at `GPIB0::29` (TDS
Toolkit's NVRAM backup and restore). The undocumented `WORDCONSTANT:ATPUT
<index>,<value>` writes firmware constants in NVRAM (firmware study points to
index 327695 as the 2M option word; not tried); don't send it outside a planned, backed-up service job.

## 20. Python driver

A small pyvisa driver that works across the families. It sends `HEADER OFF`
on open and after `FACTORY`, reads the model from `*IDN?`, parses `WFMPRE?` by
name with headers on (the 784D's field order differs from the manuals and its
sub-queries time out), and fetches 16-bit binary curves. Tested against a fake
instrument only; the calls themselves are the ones verified on the 784D.

```python
"""Small pyvisa driver for Tektronix TDS 400/500/600/700/800 scopes.

Copy into a project and extend. Standard library plus pyvisa (numpy optional).
"""
import re
import time

import pyvisa

INVALID = 9.9e37          # Tektronix "no value" answer (not stated in these manuals)


class TdsError(Exception):
    pass


class Tds:
    def __init__(self, resource, timeout_ms=10000, rm=None):
        self.rm = rm or pyvisa.ResourceManager()
        self.io = self.rm.open_resource(resource)
        self.io.timeout = timeout_ms
        self.io.read_termination = "\n"
        self.io.write_termination = "\n"
        self.io.clear()                       # SDC: empties input/output queues
        self.write("HEADER OFF")
        self.idn = self.ask("*IDN?")
        m = re.search(r"TDS\s?(\d{3})([A-Z]?)", self.idn)
        if not m:
            raise TdsError("not a TDS: " + self.idn)
        self.number, self.suffix = int(m.group(1)), m.group(2)
        self.model = "TDS %d%s" % (self.number, self.suffix)
        fv = re.search(r"FV:\s*v?([\d.]+\w*)", self.idn)
        self.firmware = fv.group(1) if fv else ""
        self.sampling = self.number == 820   # equivalent-time, one point per trigger

    # --- plumbing -----------------------------------------------------
    def write(self, cmd):
        self.io.write(cmd)

    def ask(self, cmd):
        return self.io.query(cmd).strip()

    def num(self, cmd):
        return float(self.ask(cmd))

    def opc(self, timeout_ms=None):
        """Block until pending operations finish (single sequence, *CAL, hardcopy...)."""
        old = self.io.timeout
        if timeout_ms:
            self.io.timeout = timeout_ms
        try:
            return self.ask("*OPC?") == "1"
        finally:
            self.io.timeout = old

    def events(self):
        """Read and clear the event queue: [(code, text), ...]. *ESR? must come first."""
        self.ask("*ESR?")
        reply = self.ask("ALLEV?")
        found = [(int(c), t.strip()) for c, t in re.findall(r'(-?\d+),"([^"]*)"', reply)]
        return [e for e in found if e[0] not in (0, 1)]

    def check(self, what=""):
        bad = [e for e in self.events() if e[0] < 400 or e[0] >= 2000]
        if bad:
            raise TdsError("%s: %s" % (what or "command", bad))

    # --- setup --------------------------------------------------------
    def factory(self):
        self.write("FACTORY")
        self.opc()
        self.write("HEADER OFF")              # FACTORY turns headers back on
        self.write("*CLS")

    def single(self, timeout_ms=30000):
        """Arm one single-sequence acquisition and wait for it to finish."""
        self.write("ACQUIRE:STOPAFTER SEQUENCE")
        self.write("ACQUIRE:STATE RUN")
        if not self.opc(timeout_ms):
            raise TdsError("acquisition did not complete")

    def run(self):
        self.write("ACQUIRE:STOPAFTER RUNSTOP")
        self.write("ACQUIRE:STATE RUN")

    # --- measurements -------------------------------------------------
    def measure(self, kind, source="CH1", source2=None):
        """Immediate measurement, e.g. measure('FREQUENCY'). None if no valid value."""
        self.write("MEASUREMENT:IMMED:TYPE " + kind)
        self.write("MEASUREMENT:IMMED:SOURCE1 " + source)
        if source2:
            self.write("MEASUREMENT:IMMED:SOURCE2 " + source2)
        v = self.num("MEASUREMENT:IMMED:VALUE?")
        return None if abs(v) >= INVALID else v

    # --- waveform transfer --------------------------------------------
    def preamble(self):
        """WFMPRE? parsed by name. Asked with HEADER ON: field order differs by model."""
        self.write("HEADER ON")
        self.write("VERBOSE ON")
        try:
            text = self.ask("WFMPRE?")
        finally:
            self.write("HEADER OFF")
        out = {}
        for part in re.findall(r'(?:[^;"]|"[^"]*")+', text):
            part = part.strip()
            if " " not in part:
                continue
            name, value = part.split(" ", 1)
            name = name.rsplit(":", 1)[-1].upper()
            value = value.strip()
            if value.startswith('"'):
                out[name] = value.strip('"')
            else:
                try:
                    out[name] = float(value) if re.search(r"[.Ee]", value) else int(value)
                except ValueError:
                    out[name] = value
        return out

    def curve(self, source="CH1", start=1, stop=None):
        """Return (times, volts) for one displayed waveform, 16-bit signed big-endian."""
        if stop is None:
            stop = int(self.num("HORIZONTAL:RECORDLENGTH?"))
        self.write("DATA:SOURCE " + source)
        self.write("DATA:ENCDG RIBINARY")
        self.write("DATA:WIDTH 2")
        self.write("DATA:START %d" % start)
        self.write("DATA:STOP %d" % stop)
        pre = self.preamble()
        raw = self.io.query_binary_values("CURVE?", datatype="h", is_big_endian=True,
                                          container=list)
        xinc, xzero, ptoff = pre["XINCR"], pre.get("XZERO", 0.0), pre.get("PT_OFF", 0)
        ymult, yoff, yzero = pre["YMULT"], pre["YOFF"], pre["YZERO"]
        t = [xzero + (i - ptoff) * xinc for i in range(len(raw))]
        v = [(r - yoff) * ymult + yzero for r in raw]
        return t, v

    def close(self):
        self.io.close()


if __name__ == "__main__":
    import sys
    scope = Tds(sys.argv[1] if len(sys.argv) > 1 else "GPIB0::1::INSTR")
    print(scope.model, scope.firmware)
    print("frequency", scope.measure("FREQUENCY"))
    print("events", scope.events())
```

Notes on using it:

- `curve()` needs the source displayed (`SELECT:CH1 ON`); otherwise event
  2244 and a timeout or empty block.
- On the 820, `PT_OFF` is always 0 and `XZERO` is the time base position
  (section 16); the same formula then gives trigger-relative time for
  `DATA:START 1`.
- SAMple, PEAKdetect and ENVelope data is 8-bit; `DATA:WIDTH 2` pads it with
  a zero low byte, so values step in 256s. HIRes and AVErage are true 16-bit.
- For several sources in one `CURVE?`, the blocks come back in the fixed
  order CH1-CH4, MATH1-3, REF1-4, comma-separated. Read them one source at a
  time unless the speed matters.
- `query_binary_values` reads the `#<n><len>` header and drains the trailing
  LF. For an indefinite `#0` block (some uploads use it), use `read_raw()`.

## 21. Recipes

All of these assume the driver in section 20 (`s = Tds("GPIB0::3::INSTR")`)
or plain pyvisa with `HEADER OFF`.

**Known starting state.**

```python
s.factory()                       # FACTORY, *OPC?, HEADER OFF, *CLS
s.write("SELECT:CH1 ON")
s.write("CH1:SCALE 0.5;POSITION 0;COUPLING DC")      # no COUPLING on the 820
s.write("HORIZONTAL:MAIN:SCALE 200E-6")
s.write("TRIGGER:MAIN:EDGE:SOURCE CH1;SLOPE RISE")   # 820: TRIGGER:SOURCE CH1
s.write("TRIGGER:MAIN SETLEVEL")                      # level to 50 %
s.check("setup")
```

`FACTORY` keeps the GPIB address, calibration, stored setups and REFs. It
clears ESER and SRER, sets DESER 255 and `*PSC 1`, deletes aliases, empties
`*DDT` and turns headers on. `*RST` resets the same instrument settings but
keeps SRER, ESER, `*PSC`, aliases, `*PUD` and the output queue.

**One measurement on a single acquisition.**

```python
s.single()                                   # STOPAFTER SEQUENCE, STATE RUN, *OPC?
f = s.measure("FREQUENCY", "CH1")            # None if 9.9E37
vpp = s.measure("PK2PK", "CH1")
dly = s.measure("DELAY", "CH1", "CH2")       # set MEASUREMENT:IMMED:DELAY:EDGE1/2 first
s.run()
```

`MEASUREMENT:MEAS<x>:VALUE?` reads a displayed slot that updates about three
times a second (slower with long records); use `IMMED` from programs.
Averaging: `ACQUIRE:MODE AVERAGE;NUMAVG 16`, then `single()` completes after
16 acquisitions.

**Waveform to CSV.**

```python
t, v = s.curve("CH1")
with open("ch1.csv", "w") as f:
    f.write("time_s,volts\n")
    f.writelines("%.6e,%.6e\n" % p for p in zip(t, v))
```

**Upload a reference waveform** (O p.2-27 order; also T, C, D).

```python
import struct
n = len(codes)                                    # int16 digitiser levels
s.write("DATA:DESTINATION REF1")
s.write("ALLOCATE:WAVEFORM:REF1 %d" % n)         # rounded up to a legal size
s.write("DATA:ENCDG RIBINARY;WIDTH 2;START 1")
s.write("WFMPRE:BYT_NR 2;BIT_NR 16;ENCDG BIN;BN_FMT RI;BYT_OR MSB")
s.write("WFMPRE:REF1:NR_PT %d;PT_FMT Y;XINCR 1E-6;PT_OFF 0;"
        "XUNIT \"s\";YMULT 1.5625E-5;YOFF 0;YZERO 0;YUNIT \"V\"" % n)
s.io.write_binary_values("CURVE ", codes, datatype="h", is_big_endian=True)
s.write("SELECT:REF1 ON")
s.check("upload")
```

On the 784D a REF is 6400 counts per division whatever YMULT says about
volts (section 19). `<wfm>` in `WFMPRE:<wfm>:...` is ignored on input;
`DATA:DESTINATION` decides. `DATA:STOP` is ignored on input.

**Screen dump over GPIB.**

```python
s.write("HARDCOPY:PORT GPIB")       # FILE also exists on C/D with a floppy
s.write("HARDCOPY:FORMAT BMP")      # TIFF, PCX ... see section 13
s.write("HARDCOPY START")
s.io.read_termination = None        # binary: read to EOI, not to the first LF
old = s.io.timeout
s.io.timeout = 60000
try:
    img = s.io.read_raw()
finally:
    s.io.read_termination = "\n"
    s.io.timeout = old
open("screen.bmp", "wb").write(img)
```

About 6 s on the 784D. While a hardcopy runs, DCL does not clear the output
queue; send `HARDCOPY ABORT` first. Put `*WAI` between successive
`HARDCOPY START`s. Don't start one at a slow timebase (section 19).

**Self-calibration and diagnostics.**

```python
import time
s.write("*CLS")
s.io.timeout = 300000               # *CAL? takes 15 s (820) to several minutes
cal = s.ask("*CAL?")                # "0" = pass
s.write("DIAG:SELECT:ALL ALL")
s.write("DIAG:STATE EXECUTE")       # warm boot; bus silent 30 s or more
time.sleep(60)
print(s.ask("DIAG:RESULT:FLAG?"), s.ask("DIAG:RESULT:LOG?"))
s.io.timeout = 10000
```

Disconnect the inputs before `*CAL?`. `DIAg:STATE EXECute` clears the event
queue, input queue, SESR and SBR; PON is set when it finishes. To get an SRQ
instead of sleeping: `DESE 128;*ESE 128;*SRE 32;*PSC 0` before running it.

**Does this scope have a command?**

```python
def has(s, cmd):
    s.events()                       # flush
    try:
        s.ask(cmd + "?")
    except pyvisa.errors.VisaIOError:
        s.io.clear()
        return False
    return not any(c in (113, 110, 241) for c, _ in s.events())
```

The command matrix (Appendix A) answers it on paper. On the hardware, beware
commands that are accepted and do nothing (holdoff `:VALUE` on the 784D, EAL
and DPO side effects in section 18).

**Save a setup to floppy** (C/D with option 1F).

```python
s.write('FILESYSTEM:CWD "fd0:/"')
s.write('SAVE:SETUP "fd0:/BENCH.SET"')
s.opc()
print(s.ask("FILESYSTEM:DIR?"))
```

**Front-panel message for the operator.**

```python
s.write("MESSAGE:BOX 100,100,540,160")
s.write('MESSAGE:SHOW "Connect CH1 to the calibrator, then press RUN"')
s.write("MESSAGE:STATE ON")
```

Characters are 15 pixels high; the box is in screen pixels (0-640, 0-480).
`MESSAGE:STATE OFF` removes it.

## 22. Errors in the manuals

Per-manual errors are at the end of sections 15 to 18. The ones that cost
the most time:

- **Syntax lines that are wrong.** D's slew-rate topics, `EXTAtten:<NR3>`
  with a colon, `DSOSingle`, `ZOOm DUAl`, `TRIGger:MAIn:STATE:WHEn`. The T
  manual's `TRIGger:MAIn:HOLdoff:VALue <NR1>`. Trust the topic or heading name
  and the argument list over the printed syntax line.
- **Group tables that mark set/query commands as query only**
  (`ALLOcate:WAVEform:REF<x>`, `CURSor:PAIred:SELect` in O), and `DATE`/`TIMe`
  printed as `*DATE`/`*TIMe`.
- **Examples copied from other models:** `DIAG:LOOP` in every `*LRN?`
  example (the firmware has it, the manuals never describe it); T's
  related-command list naming `HORizontal:DELay:MODe?` and `:TIMe?`; C's
  `WFMPre?` example with `NR_PT 1`.
- **The encoding table** printing SRIbinary twice (A to C).
- **The CURVe block** "including checksum" (there is none).
- **YMULT** described as "per division" in the global `WFMPre:YMUlt` entry;
  the scaling formula needs per digitising level.
- **The `WFMPRE?` field order** in every manual differs from what the 784D
  sends.
- **Default holdoff.** D says the greater of 5 divisions or 250 ns, then
  computes its example as 1 ms/div × 25 div.
- **Holdoff.** The 784D accepts `TRIGGER:MAIN:HOLDOFF:VALUE` without an error even
  though D gives `:VALue` to the 400A/510A only.
- **Model qualifiers** that are wrong or stale (C: "500C & 700A" FastFrame,
  "640B"; D: an ALLOcate table without the 694C's longer records; the 694C
  offset table).
- **OCR.** In the PDF scans the micro sign often reads as "m": C's factory
  time/div "500 ms" is 500 µs. Check an "ms" figure against the exponent in the
  example.

## Appendix A. Command availability by manual

Every documented command header, grouped by the manuals that document it.
O = 070-8318-01/-05 (TDS 420-640), T = 070-8513-01 (TDS 820), A = 070-8709-06/-07
(A6/A7 when only one edition has it), B = 070-9556-00/070-9702-00, C = 070-9876-00,
D = 063-3060-00. ? = query only, (NQ) = no query form. A header can still be limited
to some models of a family, and arguments differ between families (sections 15-18).
Extracted from OCR text; a few O-only spellings may be OCR matches. Undocumented
commands (MESSage:OPAQue before D, DIAg:LOOP, WORDCONSTANT) are not listed.

**O T A B C D** (200): ACQuire:MODe, ACQuire:NUMACq?, ACQuire:NUMAVg, ACQuire:NUMEnv, ACQuire:STATE, ACQuire:STOPAfter, ACQuire?, ALIas, ALIas:CATalog?, ALIas:DEFIne, ALIas:DELEte (NQ), ALIas:DELEte:ALL (NQ), ALIas:DELEte:NAMe (NQ), ALIas:STATE, ALLEv?, ALLOcate:WAVEform:FREE?, ALLOcate:WAVEform:REF<x>, ALLOcate:WAVEform?, ALLOcate?, APPMenu, APPMenu:LABel, APPMenu:LABel:RIGHT<x>, APPMenu:TITLe, AUTOSet (NQ), BELl (NQ), BUSY?, *CAL?, CH<x>:OFFSet, CH<x>:POSition, CH<x>:PROBE?, CH<x>:SCAle, CH<x>:VOLts, CH<x>?, CLEARMenu (NQ), *CLS (NQ), CURSor:FUNCtion, CURSor:HBArs:DELTa?, CURSor:HBArs:SELect, CURSor:HBArs?, CURSor:MODe, CURSor:PAIred:HDELTA?, CURSor:PAIred:HPOS1?, CURSor:PAIred:HPOS2?, CURSor:PAIred:SELect, CURSor:VBArs, CURSor:VBArs:DELTa?, CURSor:VBArs:SELect, CURSor:VBArs:UNITS, CURSor?, CURVe, DATa, DATa:DESTination, DATa:ENCdg, DATa:SOUrce, DATa:STARt, DATa:STOP, DATa:TARget, DATa:WIDth, DATE, *DDT, DELEte:SETUp (NQ), DELEte:WAVEform (NQ), DESE, DIAg:RESUlt:FLAg?, DIAg:RESUlt:LOG?, DIAg:SELect:ACQUISition (NQ), DIAg:SELect:ALL (NQ), DIAg:SELect:CPU (NQ), DIAg:SELect:DISplay (NQ), DIAg:SELect:FPAnel (NQ), DIAg:STATE (NQ), DISplay:CLOCk, DISplay:FILTer, DISplay:FORMat, DISplay:GRAticule, DISplay:INTENSITy:OVERAll, DISplay:INTENSITy:TEXt, DISplay:INTENSITy?, DISplay:PERSistence, DISplay:STYle, DISplay:TRIGBar, DISplay:TRIGT, DISplay?, *ESE, *ESR?, EVENT?, EVMsg?, EVQty?, FACtory (NQ), HARDCopy, HARDCopy:FORMat, HARDCopy:LAYout, HARDCopy:PORT, HDR, HEADer, HORizontal:DELay:SCAle, HORizontal:DELay:SECdiv, HORizontal:DELay?, HORizontal:MAIn?, HORizontal:MODe, HORizontal:POSition, HORizontal:RECORDLength, HORizontal:SCAle, HORizontal:SECdiv, HORizontal?, ID?, *IDN?, LIMit:BELl, LIMit:COMPARE:CH<x>, LIMit:TEMPLate:TOLerance:VERTical, LOCk, *LRN?, MATH<x>?, MEASUrement:GATing, MEASUrement:IMMed:DELay:DIREction, MEASUrement:IMMed:DELay:EDGE1, MEASUrement:IMMed:DELay?, MEASUrement:IMMed:SOURCE2, MEASUrement:IMMed:SOURCE[1], MEASUrement:IMMed:TYPe, MEASUrement:IMMed:UNITS?, MEASUrement:IMMed:VALue?, MEASUrement:IMMed?, MEASUrement:MEAS<x>:SOURCE2, MEASUrement:MEAS<x>:SOURCE[1], MEASUrement:MEAS<x>?, MEASUrement:METHod, MEASUrement:REFLevel:ABSolute:HIGH, MEASUrement:REFLevel:ABSolute:LOW, MEASUrement:REFLevel:ABSolute:MID, MEASUrement:REFLevel:ABSolute:MID2, MEASUrement:REFLevel:METHod, MEASUrement:REFLevel:PERCent:HIGH, MEASUrement:REFLevel:PERCent:LOW, MEASUrement:REFLevel:PERCent:MID, MEASUrement:REFLevel:PERCent:MID2, MEASUrement:REFLevel?, MEASUrement:SNAPShot, MEASUrement?, MESSage, MESSage:BOX, MESSage:SHOW, MESSage:STATE, NEWpass (NQ), *OPC, PASSWord (NQ), *PSC, *PUD, *RCL (NQ), REM (NQ), RS232:BAUd, RS232:HARDFlagging, RS232:PARity, RS232:SOFTFlagging, RS232:STOPBits, RS232?, *RST (NQ), *SAV (NQ), SAVe:SETUp (NQ), SAVe:WAVEform (NQ), SELect:<wfm>, SELect:CONTROl, SELect?, SET?, *SRE, *STB?, TEKSecure, *TRG (NQ), TRIGger:STATE?, *TST?, UNLock (NQ), VERBose, *WAI (NQ), WAVFrm?, WFMPre:<wfm>:NR_Pt, WFMPre:<wfm>:PT_Fmt, WFMPre:<wfm>:WFId, WFMPre:<wfm>:XINcr, WFMPre:<wfm>:YMUlt, WFMPre:<wfm>:YOFf, WFMPre:<wfm>:YUNit, WFMPre:<wfm>:YZEro, WFMPre:<wfm>?, WFMPre:BIT_Nr, WFMPre:BN_Fmt, WFMPre:BYT_Nr, WFMPre:BYT_Or, WFMPre:ENCdg, WFMPre:PT_Fmt (NQ), WFMPre:XINcr (NQ), WFMPre:YMUlt (NQ), WFMPre:YOFf (NQ), WFMPre:YZEro (NQ), WFMPre?, ZOOm:HORizontal:LOCk, ZOOm:HORizontal:POSition, ZOOm:HORizontal:SCAle, ZOOm:STATE, ZOOm:VERTical:POSition, ZOOm:VERTical:SCAle

**A B C D** (92): ACQuire:AUTOSAve, CURSor:HBArs:POSITION<x>, CURSor:HBArs:UNITS, CURSor:PAIred:UNITS, CURSor:VBArs:POSITION<x>, DISplay:COLOr:CONTRast, DISplay:COLOr:PALEtte:PERSistence, DISplay:COLOr:PALEtte:REGular, DISplay:COLOr:PALEtte:RESETALL (NQ), DISplay:INStavu:PERSistence, DISplay:INStavu:STYle, DISplay:INStavu:VARpersist, DISplay:MODe, FILESystem:COPy (NQ), FILESystem:CWD, FILESystem:DELEte (NQ), FILESystem:DELWarn, FILESystem:DIR?, FILESystem:FORMat (NQ), FILESystem:FREESpace?, FILESystem:MKDir (NQ), FILESystem:OVERWrite, FILESystem:PRInt (NQ), FILESystem:REName (NQ), FILESystem:RMDir (NQ), HARDCopy:FILEName, HARDCopy:PALEtte, HORizontal:FASTframe:COUNt, HORizontal:FASTframe:LENgth, HORizontal:FASTframe:POSition, HORizontal:FASTframe:STATE, HORizontal:FITtoscreen, LIMit:COMPARE:MATH<x>, LIMit:TEMPLate:DESTination, LIMit:TEMPLate:TOLerance:HORizontal, MATH<x>:DEFINE, MATH<x>:NUMAVg, MATH<x>:PROCessing, MEASUrement:MEAS<x>:DELay:DIREction, MEASUrement:MEAS<x>:DELay:EDGE1, MEASUrement:MEAS<x>:DELay:EDGE2, MEASUrement:MEAS<x>:DELay?, MEASUrement:MEAS<x>:STATE, MEASUrement:MEAS<x>:UNITS?, MEASUrement:MEAS<x>:VALue?, *OPT?, RECAll:WAVEform (NQ), SAVe:WAVEform:FILEFormat, TIMe, TRIGger, TRIGger:MAIn:HOLDOff:ACTUal?, TRIGger:MAIn:HOLDOff:BY, TRIGger:MAIn:HOLDOff:TIMe, TRIGger:MAIn:LOGIc:INPut:CH<x>, TRIGger:MAIn:LOGIc:SETHold:CLOCk:EDGE, TRIGger:MAIn:LOGIc:SETHold:CLOCk:LEVel, TRIGger:MAIn:LOGIc:SETHold:CLOCk:SOUrce, TRIGger:MAIn:LOGIc:SETHold:DATa:LEVel, TRIGger:MAIn:LOGIc:SETHold:DATa:SOUrce, TRIGger:MAIn:LOGIc:SETHold:HOLDTime, TRIGger:MAIn:LOGIc:SETHold:SETTime, TRIGger:MAIn:PULse:RUNT:THReshold:BOTh, TRIGger:MAIn:PULse:RUNT:WHEn, TRIGger:MAIn:PULse:RUNT:WIDth, TRIGger:MAIn:PULse:SLEWRate:DELTATime, TRIGger:MAIn:PULse:SLEWRate:POLarity, TRIGger:MAIn:PULse:SLEWRate:SLEWRate?, TRIGger:MAIn:PULse:SLEWRate:THReshold:BOTh, TRIGger:MAIn:PULse:SLEWRate:THReshold:HIGH, TRIGger:MAIn:PULse:SLEWRate:THReshold:LOW, TRIGger:MAIn:PULse:SLEWRate:WHEn, TRIGger:MAIn:VIDeo:FIELDType, TRIGger:MAIn:VIDeo:FLEXformat:FIELDRATE, TRIGger:MAIn:VIDeo:FLEXformat:FIELDS, TRIGger:MAIn:VIDeo:FLEXformat:LINES, TRIGger:MAIn:VIDeo:FLEXformat:NEGSyncwidth, TRIGger:MAIn:VIDeo:FLEXformat:V1STArttime, TRIGger:MAIn:VIDeo:FLEXformat:V1STOptime, TRIGger:MAIn:VIDeo:FLEXformat:V2STArttime, TRIGger:MAIn:VIDeo:FLEXformat:V2STOptime, TRIGger:MAIn:VIDeo:FLEXformat?, TRIGger:MAIn:VIDeo:HDTv, TRIGger:MAIn:VIDeo:LINE, TRIGger:MAIn:VIDeo:NTSc, TRIGger:MAIn:VIDeo:PAL, TRIGger:MAIn:VIDeo:STANdard, TRIGger:MAIn:VIDeo?, WFMPre:<wfm>:XUNit, ZOOm, ZOOm:DUAl, ZOOm:DUAl:OFFSet, ZOOm:GRAticule

**O A B C D** (81): ACQuire:REPEt, APPMenu:LABel:BOTTOM<x>, CH<x>:BANdwidth, CH<x>:COUPling, CH<x>:IMPedance, CURSor:PAIred:VDELTA?, DISplay:INTENSITy:CONTRast, DISplay:INTENSITy:WAVEform, HORizontal:DELay:MODe, HORizontal:DELay:TIMe?, HORizontal:DELay:TIMe:RUNSAfter, HORizontal:DELay:TIMe:TRIGAfter, HORizontal:MAIn:SCAle, HORizontal:MAIn:SECdiv, HORizontal:TRIGger:POSition, HORizontal:TRIGger?, MEASUrement:CLEARSNapshot, MEASUrement:IMMed:DELay:EDGE2, TRIGger:DELay, TRIGger:DELay:BY, TRIGger:DELay:EDGE:COUPling, TRIGger:DELay:EDGE:SLOpe, TRIGger:DELay:EDGE:SOUrce, TRIGger:DELay:EDGE?, TRIGger:DELay:EVENTS:COUNt, TRIGger:DELay:EVENTS?, TRIGger:DELay:LEVel, TRIGger:DELay:TIMe, TRIGger:DELay:TYPe, TRIGger:MAIn, TRIGger:MAIn:EDGE:COUPling, TRIGger:MAIn:EDGE:SLOpe, TRIGger:MAIn:EDGE:SOUrce, TRIGger:MAIn:EDGE?, TRIGger:MAIn:HOLDOff:VALue, TRIGger:MAIn:HOLDOff?, TRIGger:MAIn:LEVel, TRIGger:MAIn:LOGIc:CLAss, TRIGger:MAIn:LOGIc:FUNCtion, TRIGger:MAIn:LOGIc:INPut?, TRIGger:MAIn:LOGIc:PATtern:INPut:CH4, TRIGger:MAIn:LOGIc:PATtern:WHEn, TRIGger:MAIn:LOGIc:PATtern:WHEn:LESSLimit, TRIGger:MAIn:LOGIc:PATtern:WHEn:MORELimit, TRIGger:MAIn:LOGIc:STATE:INPut:CH4, TRIGger:MAIn:LOGIc:STATE:WHEn, TRIGger:MAIn:LOGIc:THReshold:CH<x>, TRIGger:MAIn:LOGIc:THReshold?, TRIGger:MAIn:LOGIc:WHEn, TRIGger:MAIn:LOGIc?, TRIGger:MAIn:MODe, TRIGger:MAIn:PULse:CLAss, TRIGger:MAIn:PULse:GLItch:FILTer, TRIGger:MAIn:PULse:GLItch:POLarity, TRIGger:MAIn:PULse:GLItch:WIDth, TRIGger:MAIn:PULse:GLItch?, TRIGger:MAIn:PULse:RUNT:POLarity, TRIGger:MAIn:PULse:RUNT:THReshold:HIGH, TRIGger:MAIn:PULse:RUNT:THReshold:LOW, TRIGger:MAIn:PULse:RUNT:THReshold?, TRIGger:MAIn:PULse:RUNT?, TRIGger:MAIn:PULse:SOUrce, TRIGger:MAIn:PULse:WIDth:HIGHLimit, TRIGger:MAIn:PULse:WIDth:LOWLimit, TRIGger:MAIn:PULse:WIDth:POLarity, TRIGger:MAIn:PULse:WIDth:WHEn, TRIGger:MAIn:PULse:WIDth?, TRIGger:MAIn:PULse?, TRIGger:MAIn:TYPe, TRIGger:MAIn:VIDeo:BY, TRIGger:MAIn:VIDeo:FIELD, TRIGger:MAIn:VIDeo:HOLdoff:VALue, TRIGger:MAIn:VIDeo:HOLdoff?, TRIGger:MAIn:VIDeo:INTERLAce, TRIGger:MAIn:VIDeo:LINES, TRIGger:MAIn:VIDeo:SCAN, TRIGger:MAIn:VIDeo:SOUrce, TRIGger:MAIn:VIDeo:SYNc, TRIGger:MAIn:VIDeo:SYStem, TRIGger:MAIn:VIDeo:TIMe, WFMPre:PT_Off (NQ)

**C D** (51): CH<x>:PROBEFunc:EXTAtten, CH<x>:PROBEFunc:EXTDBatten, FILESystem:READFile, FILESystem:WRITEFile, HIStogram:BOX, HIStogram:BOXPcnt, HIStogram:COUNt, HIStogram:DISplay, HIStogram:MODe, HIStogram:SIZe, HIStogram:SOUrce, HIStogram?, HORizontal:ACQDURATION?, HORizontal:ACQLENGTH?, HORizontal:EXTDACQ, HORizontal:RECORDSTART, MASK:AUTOSet:MODe, MASK:AUTOSet:OFFSETAdj, MASK:COUNt, MASK:COUNt:STATE, MASK:COUNt:TOTal?, MASK:COUNt:WAVEFORMS?, MASK:DISplay, MASK:FILTer, MASK:MASK<n>:COUNt?, MASK:MASK<n>:NR_Pt?, MASK:MASK<n>:POINTS, MASK:MASK<n>:POINTSPcnt, MASK:MASK<n>?, MASK:SOUrce, MASK:STANdard, MASK:TBPosition, MASK?, MEASUrement:MEAS<x>:COUNt?, MEASUrement:MEAS<x>:MAXimum?, MEASUrement:MEAS<x>:MEAN?, MEASUrement:MEAS<x>:MINImum?, MEASUrement:MEAS<x>:STDdev?, MEASUrement:STATIstics:MODE, MEASUrement:STATIstics:WEIghting, RECAll:ACQDATA (NQ), SAVe:ACQDATA (NQ), TRIGger:MAIn:COMMunication:AMI:PULSEForm, TRIGger:MAIn:COMMunication:AMI:THReshold:HIGH, TRIGger:MAIn:COMMunication:AMI:THReshold:LOW, TRIGger:MAIn:COMMunication:BITRate, TRIGger:MAIn:COMMunication:CMI:PULSEForm, TRIGger:MAIn:COMMunication:CODe, TRIGger:MAIn:COMMunication:NRZ:PULSEForm, TRIGger:MAIn:COMMunication:SOUrce, TRIGger:MAIn:COMMunication:STANdard

**D** (43): APPLication:ACTivate, APPLication:GPKNOB:ACTIVE, APPLication:GPKNOB:LABel, APPLication:GPKNOB:MAXValue, APPLication:GPKNOB:MINValue, APPLication:GPKNOB:RESOlution, APPLication:GPKNOB:UNIts, APPLication:GPKNOB:VALue, DISplay:COLOr:MAP:<item name>:BYCONTents, DISplay:COLOr:MAP:<item name>:TO, DISplay:COLOr:PALEtte:<palette name>:<item name>, DISplay:COLOr:PALEtte:<palette name>:RESET, DISplay:COLOr:PALEtte:<persistPalette>:P<x>, DISplay:INStavu:ACCUmulate, DISplay:INStavu:AUTOBright, DISplay:INStavu:BRIGHTness, DISplay:INStavu:CONTRast, DISplay:INStavu:MAP, DISplay:INStavu:PERCent:P<x>, HORizontal:FASTframe:FRAMELock, HORizontal:FASTframe:REF, HORizontal:FASTframe:TIMEStamp:BETWeen?, HORizontal:FASTframe:TIMEStamp:CLEARSNapshot, HORizontal:FASTframe:TIMEStamp:DELTa?, HORizontal:FASTframe:TIMEStamp:FRAme?, HORizontal:FASTframe:TIMEStamp:POSition?, HORizontal:FASTframe:TIMEStamp:REF?, HORizontal:FASTframe:TIMEStamp:SNAPShot, HORizontal:FASTframe:TIMEStamp:STATE, MASK:AUTOSet:STANdard, MASK:INVert, MASK:MARgin:PERCent, MASK:MARgin:STATE, MASK:PASSFail:BELl, MASK:PASSFail:STATE, MASK:PASSFail:STATUs?, MASK:PASSFail:THReshold, MASK:PASSFail:WAVEform, MESSage:OPAQue, MESSage:PRIOrity, RECAll:IMAGEHistogram, SAVe:IMAGEHistogram, TRIGger:TLAAUXiliary:DELay

**T** (21): CALibrate:ALL, CALibrate:ALL:STATUs?, CH<x>:PROBEFunct:EXTAtten, CH<x>:PROBEFunct:EXTDBatten, GRAPhics:DELEte (NQ), GRAPhics:DISplay, GRAPhics:DRAw (NQ), GRAPhics:MOVe (NQ), GRAPhics:NUMPoints?, GRAPhics:POInts, GRAPhics?, HORizontal:DELay:TBPosition, HORizontal:TBPosition, TRIGger:HOLDoff:ACTUal?, TRIGger:HOLDoff:VALue, TRIGger:INTRate, TRIGger:LEVel, TRIGger:MAXSamprate?, TRIGger:MODe, TRIGger:SLOpe, TRIGger:SOUrce

**A7 B C D** (8): CURSor:HBArs:POSITION<x>Pcnt, CURSor:PAIred:POSITION<x>, CURSor:PAIred:POSITION<x>Pcnt, CURSor:VBArs:POSITION<x>Pcnt, CURSor:VBArs:UNITSTring?, HORizontal:CLOCk, HORizontal:CLOCk:MAXRate, TRIGger:MAIn:VIDeo:SCANPeriod

**T A B C D** (8): CURSor:PAIred, LIMit:HARDCopy, LIMit:STATE, LIMit:TEMPLate (NQ), LIMit:TEMPLate:SOUrce, MEASUrement:MEAS<x>:TYPe, RECAll:SETUp (NQ), WFMPre:<wfm>:PT_Off

**B C D** (5): CH<x>:DESKew, CH<x>:PROBECal?, HORizontal:ROLL, TRIGger:MAIn:PULse:TIMEOut:POLarity, TRIGger:MAIn:PULse:TIMEOut:TIMe

**O T A6** (2): CURSor:PAIred:POSITION1, CURSor:PAIred:POSITION2

**T B C D** (1): WFMPre:<wfm>:XZEro