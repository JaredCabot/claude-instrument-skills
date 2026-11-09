---
name: "keysight-truevolt-dmm"
description: "Operate, program (SCPI over USB/LAN/GPIB) and configure the Keysight Truevolt bench DMMs 34460A/34461A/34465A/34470A: measurement setup, triggering, math, data logging, digitizing, secondary measurements, status, errors, files, I/O, calibration and the full documented command set."
---

# Keysight Truevolt Series DMMs: 34460A / 34461A / 34465A / 34470A

The complete documented feature set, from the Keysight Truevolt Series Operating
and Service Guide (document 34460-90901, English edition; "OSG p.NNN" are its
printed page numbers). Everything here is from the guide unless marked
**[inferred]**. For undocumented DIAGnostic/service commands, the AC-mode
variant and firmware internals, see the separate 344xxA Firmware Supplement
(https://github.com/JaredCabot/344xxA-firmware-research); this skill is the
official feature set only and does not depend on it.

Syntax conventions: `{A|B}` is a required choice, `[X]` an optional node or
parameter, `<x>` a value you supply. SCPI keywords show the short form in
capitals; the lower-case tail is optional (`VOLTage` accepts `VOLT` or
`VOLTAGE`). `MIN`, `MAX`, `DEF` are accepted wherever a numeric `<value>` is,
and a numeric query takes `[{MIN|MAX|DEF}]` to ask the limit instead of the
current value. Boolean parameters accept `{OFF|0|ON|1}`; a query returns `0` or
`1`. Every set command shown has a matching query unless noted "(no query)".

## Models, options and what differs

| Model | Digits | Notes |
|---|---|---|
| 34460A | 6½ | Basic DMM. LAN and the accessory kit are options. No 10 A terminals. |
| 34461A | 6½ | 34401A-replacement. LAN and accessory kit standard. 10 A terminals. |
| 34465A | 6½ | Adds the 34465A/70A-only features below. |
| 34470A | 7½ | Highest resolution; same feature set as the 34465A. |

A large group of commands and parameters is **34465A/70A only**: all `APERture`
and `APERture:ENABled` nodes; `CALCulate:SCALe` GAIN/OFFSet/REFerence/UNIT and
the PCT and SCALe (Mx-B) scale functions; `CALCulate:SMOothing`; `SAMPle:SOURce`
/ `SAMPle:TIMer` / `SAMPle:COUNt:PRETrigger`; `TRIGger:LEVel` and
`TRIGger:SOURce INTernal` (level triggering, needs DIG); `FORMat` binary
transfer and `MMEMory:FORMat:READing`; the secondary-measurement `"CALCulate:DATA"`
and `"PTPeak"` choices; `SYSTem:ACALibration` and `*CAL?`; resistance/temperature
`OCOMpensated` and `POWer:LIMit`; `CURRent:SWITch:MODE`; the thermocouple
transducer; the DC-only 1 µA and 10 µA current ranges and the 1 GΩ resistance
range; and the Data Log and Digitize acquisition modes. Sending one to a
34460A/61A returns `-203,"Command protected; feature not available on this
model"`. (Histogram, the dB and dBm scale functions, and the other
secondary-measurement choices are available on all four models.)

Licensed options, read back with `SYSTem:LICense:CATalog?`:

- **DIG** - digitizing and advanced (level) triggering (34465A/70A). Now
  included with the latest firmware. Without DIG the fastest aperture is 200 µs
  and fastest NPLC 0.02; with DIG, 20 µs and NPLC down to 0.001.
- **MEM** - deep reading memory: 2,000,000 readings instead of 50,000 (34465A/70A).
- **SEC** - NISPOM file security.
- **LAN**, **GPB** - the LAN/LXI interface and the user-installable GPIB module.

Reading-memory depth (no MEM): 34460A 1,000; 34461A 10,000; 34465A/70A 50,000
(OSG p.355).

## Connecting

Keysight VISA resource strings, one per interface (USB, LAN and the web are
enabled by default; GPIB needs the module):

- USB (USB-TMC): `USB0::<vid>::<pid>::<serial>::0::INSTR`. The exact string is on
  `[Shift] > [Help] > About` or from any VISA browser.
- LAN VXI-11: `TCPIP0::<ip>::inst0::INSTR`
- LAN HiSLIP: `TCPIP0::<ip>::hislip0::INSTR`
- LAN raw socket: TCP to **port 5025** (`TCPIP0::<ip>::5025::SOCKET`); end each
  command with `\n`.
- LAN Telnet: **port 5024** (`telnet <ip> 5024`).
- GPIB: `GPIB0::<addr>::INSTR`; address set by
  `SYSTem:COMMunicate:GPIB:ADDRess <n>` (default 22).

Default LAN is DHCP + Auto-IP on; fallback address 169.254.x.x; host name
`K-<model>-nnnnn` (last 5 serial digits). Interface and LAN-service changes take
effect only after a power cycle (OSG p.473).

```python
import pyvisa
rm = pyvisa.ResourceManager()
dmm = rm.open_resource("TCPIP0::192.168.1.50::inst0::INSTR")
dmm.timeout = 10000                      # ms; raise it for long NPLC or big SAMP:COUN
print(dmm.query("*IDN?"))                # Keysight Technologies,34465A,<serial>,<fw>
print(dmm.query("MEAS:VOLT:DC? 10,0.001"))
```

Raw socket without VISA:

```python
import socket
s = socket.create_connection(("192.168.1.50", 5025), timeout=10)
s.sendall(b"MEAS:VOLT:DC? 10,0.001\n")
print(s.recv(256).decode().strip())
```

Enable or disable an interface:
`SYSTem:COMMunicate:ENABle {OFF|ON}, {GPIB|HISLip|USB|LAN|SOCKets|TELNet|VXI11|WEB|USBMtp|USBHost}`.

## The measurement model

Three layers, from least to most control:

1. **`MEASure:<fn>?`** - one-shot: presets the function, autoranges unless you
   give a range, triggers, returns the reading. Equivalent to `CONFigure` +
   `READ?` with defaults. Easiest, least flexible.
2. **`CONFigure:<fn>`** then **`READ?`** - configure the function, adjust it with
   `[SENSe:]` commands in between, then `READ?` to trigger and return.
   `CONFigure` does **not** arm the trigger (OSG p.197). `CONFigure?` returns the
   present function and its range/resolution as a quoted string.
3. **`CONFigure` / `[SENSe:]` / `TRIGger` setup**, then **`INITiate`** to arm,
   then **`FETCh?`** to retrieve. Use this for triggered bursts, data logging and
   digitizing.

Retrieval and control verbs:

- `INITiate[:IMMediate]` - arm: move the instrument from idle to
  wait-for-trigger. Clears previous readings from memory, then stores new ones as
  they are taken. Overlapped (returns immediately).
- `READ?` = `INITiate` + `FETCh?`.
- `FETCh?` - return all readings in memory without re-triggering or erasing them.
- `R? [<max>]` - return and **erase** the oldest readings (FIFO); use it to read
  during a long acquisition without overflowing memory.
- `ABORt` - stop a measurement in progress and return to trigger idle. Use it to
  break out of a wait-for-trigger or a long burst.
- Total readings per `INITiate` = `TRIGger:COUNt` x `SAMPle:COUNt`.

```python
# Fast triggered burst of 100 readings, 10 V range, BUS-triggered
dmm.write("CONF:VOLT:DC 10,1e-5")
dmm.write("VOLT:DC:NPLC 1")
dmm.write("TRIG:SOUR BUS; :SAMP:COUN 100")
dmm.write("INIT")
dmm.write("*TRG")
dmm.query("*OPC?")                       # wait for the burst to finish
vals = dmm.query("FETC?").strip().split(",")
```

## Measurement functions

Select with `CONFigure:<fn>` / `MEASure:<fn>?`, or
`[SENSe:]FUNCtion[:ON] "<function>"`. The 13 valid function strings:
`"VOLTage[:DC]"`, `"VOLTage[:DC]:RATio"`, `"VOLTage:AC"`, `"CURRent[:DC]"`,
`"CURRent:AC"`, `"RESistance"` (2-wire), `"FRESistance"` (4-wire),
`"CAPacitance"`, `"FREQuency"`, `"PERiod"`, `"TEMPerature"`, `"CONTinuity"`,
`"DIODe"`. The query returns the short form, e.g. `"CURR:AC"`. Each function
keeps its own range, resolution and settings; switching back restores them.
Changing function turns off all `CALCulate` math states.

Every measuring function except continuity and diode takes `RANGe <v>`,
`RANGe:AUTO {OFF|ON|ONCE}`, `RESolution <v>`, `NULL[:STATe]`, `NULL:VALue`,
`NULL:VALue:AUTO`, and the integration controls below. Autorange goes up above
120 % of range and down below 10 %. Fixed-range overload shows "Overload" on the
panel and returns `9.9E37` over remote.

### DC voltage - `VOLTage[:DC]` and ratio `VOLTage[:DC]:RATio`
- Ranges 100 mV, 1 V, 10 V, 100 V, 1000 V (`:RANGe {<v>|MIN|MAX|DEF}`, default
  autorange; DC default range 1000 V with autorange on).
- `VOLTage[:DC]:IMPedance:AUTO {OFF|ON}` - OFF fixes 10 MΩ on all ranges; ON
  gives >10 GΩ ("Hi-Z") on 100 mV/1 V/10 V and 10 MΩ on 100 V/1000 V. `CONFigure`
  and `MEASure?` force it OFF. Default OFF.
- `VOLTage[:DC]:ZERO:AUTO {OFF|ON|ONCE}` - autozero, default ON.
- `:RATio` measures the HI-LO input against a DC reference on the Sense
  terminals; uses the DC settings; NULL is not available for ratio. Read the raw
  signal and reference with secondary `"SENSe:DATA"`.

### AC voltage - `VOLTage:AC`
- Ranges 100 mV, 1 V, 10 V, 100 V, 1000 V (`:RANGe` default 10 V; MAX is 1000 V,
  with a 750 VAC rms safety limit on the top range). True-RMS, AC-coupled.
- `VOLTage:AC:BANDwidth {3|20|200}` - AC filter in Hz: 3 (Slow), 20 (Medium,
  default), 200 (Fast). Set it to the lowest frequency present. The Truevolt RMS
  algorithm is not crest-factor sensitive, so no crest-factor derating is needed
  (OSG p.163). Per-reading settling: 3 Hz 2.5 s, 20 Hz 0.625 s, 200 Hz 0.025 s.

### DC / AC current - `CURRent[:DC]` / `CURRent:AC`
- 3 A terminal ranges: 100 µA, 1 mA, 10 mA, 100 mA, 1 A, 3 A. The 34465A/70A add
  DC-only **1 µA and 10 µA** ranges. (The 100 µA and 1 mA ranges exist on every
  model.)
- `CURRent:{AC|DC}:TERMinals {3|10}` - selects the 3 A or 10 A front terminals
  (34461A/65A/70A; the 34460A has no 10 A terminal). You cannot pick the 10 A
  range with `:RANGe`; use `TERMinals 10` or `CONF:CURR 10`. 10 A is front
  terminals only.
- `CURRent:SWITch:MODE {FAST|CONTinuous}` (34465A/70A, 3 A terminals) - internal
  shunt-switching behaviour. CONTinuous (default) avoids a momentary open circuit
  but makes range changes up to 3x slower; FAST allows a brief open circuit.
- `CURRent:AC:BANDwidth {3|20|200}` like AC voltage; ACI settling 3 Hz 1.66 s,
  20 Hz 0.25 s, 200 Hz 0.025 s. DC current has `ZERO:AUTO`.

### 2-wire / 4-wire resistance - `RESistance` / `FRESistance`
- Ranges 100 Ω, 1 kΩ, 10 kΩ, 100 kΩ, 1 MΩ, 10 MΩ, 100 MΩ (default 1 kΩ with
  autorange on). The 34465A/70A add 1 GΩ.
- `OCOMpensated {OFF|ON}` (34465A/70A) - offset compensation; two readings at
  different source currents cancel thermal EMF. Works on 100 Ω to 100 kΩ only;
  roughly doubles reading time.
- `POWer:LIMit[:STATe] {OFF|ON}` (34465A/70A) - low-power ohms, sources less
  current; effective on 100 Ω to 100 kΩ.
- `RESistance:ZERO:AUTO {OFF|ON|ONCE}` - 2-wire autozero (default ON). 4-wire is
  always offset-nulled, so `FRESistance` has no ZERO:AUTO. Use `FRESistance` to
  cancel lead resistance; `RESistance:NULL` nulls it for 2-wire.

### Capacitance - `CAPacitance`
- Ranges 1 nF, 10 nF, 100 nF, 1 µF, 10 µF, 100 µF, default autorange. With
  autorange off, over-range does not report overload; overload happens when the
  measurement times out (too large), or if DC or a short is on the input.
- Flagged 34465A/70A-only in the guide's intro, but the capacitance command pages
  carry no model note; treat availability as model-dependent and check with
  `SYSTem:LICense:CATalog?`/`-203` if unsure.

### Frequency / period - `FREQuency` / `PERiod`
- Reciprocal counting on the voltage input, 3 Hz to 300 kHz. FREQ and PER share
  one set of APERture, RANGe:LOWer and VOLTage:RANGe values; NULL and SECondary
  are independent.
- `{FREQuency|PERiod}:APERture {1e-3|10e-3|100e-3|1}` - gate time 1 ms, 10 ms,
  100 ms (default), 1 s; 1 ms is 34465A/70A only. Longer gate = finer resolution.
- `:RANGe:LOWer {3|20|200}` - the AC filter / lowest expected input frequency,
  default 20 Hz; the gate waits for it.
- `:VOLTage:RANGe {<v>|MIN|MAX|DEF}` sets the input voltage range (default 10 V),
  `:VOLTage:RANGe:AUTO` its autorange, `:TIMeout:AUTO {OFF|ON}` the gate timeout
  (OFF waits 1 s with no signal; ON scales with the filter and returns 0.0 on
  timeout; this is the one non-volatile SENSe setting).

### Temperature - `TEMPerature`
- `TRANsducer:TYPE {FRTD|RTD|FTHermistor|THERmistor|TCouple}` - 4-wire RTD,
  2-wire RTD, 4-wire thermistor, 2-wire thermistor, thermocouple (default FRTD;
  TCouple is 34465A/70A only).
- `CONFigure:TEMPerature [{FRTD|RTD|FTHermistor|THERmistor|TCouple|DEF}
  [,{<type>|DEF} [,1,{<resolution>|MIN|MAX|DEF}]]]`. `<type>` is the probe value
  (e.g. `CONF:TEMP FRTD,85`); the `1` placeholder is reserved.
- RTD: `TRANsducer:{FRTD|RTD}:RESistance[:REFerence] <r0>` sets R0 (default
  100 Ω; range 80-120 Ω on the 34460A/61A, 49-2100 Ω on the 34465A/70A), plus
  `OCOMpensated` and `POWer:LIMit` (34465A/70A).
- Thermistor: the front panel supports 2.2 kΩ (44004), 5 kΩ (44007) and 10 kΩ
  (44006) probes (Steinhart-Hart), but the remote command
  `TRANsducer:{FTHermistor|THERmistor}:TYPE` accepts only `5000`. Set other
  thermistor types from the front panel.
- Thermocouple (34465A/70A): `TCouple:TYPE {E|J|K|N|R|T}` (default J),
  `TCouple:RJUNction:TYPE {INTernal|FIXed}`, `TCouple:RJUNction <temp>` for a
  fixed reference (always °C, -20 to +80), `TCouple:RJUNction:OFFSet:ADJust
  <temp>` (-20 to +20), and `TCouple:CHECk {OFF|ON}` to flag a disconnected
  junction. `SYSTem:TEMPerature?` reads the internal reference temperature.
- `UNIT:TEMPerature {C|F|K}` sets the reported unit (default C).

### Continuity / diode - `CONTinuity` / `DIODe`
- No range or resolution; `CONFigure:CONTinuity`, `CONFigure:DIODe`. Selectable
  through `FUNCtion` only (no `[SENSe:]` subtree).

## Resolution, NPLC and aperture

You set any one of resolution, NPLC or aperture and the others follow (all on the
DC functions, resistance and temperature; AC and frequency use the filter and
gate instead).

- `[SENSe:]<fn>:NPLC {<PLCs>|MIN|MAX|DEF}` - integration in power-line cycles,
  default 10. Allowed sets:
  - 34460A/61A: 0.02, 0.2, 1, 10, 100
  - 34465A/70A without DIG: 0.02, 0.06, 0.2, 1, 10, 100
  - 34465A/70A with DIG: 0.001, 0.002, 0.006, 0.02, 0.06, 0.2, 1, 10, 100
  Only 1, 10 and 100 PLC give power-line (normal-mode) noise rejection.
- `[SENSe:]<fn>:APERture <seconds>` (34465A/70A) sets integration time directly:
  200 µs to 1 s, or 20 µs to 1 s with DIG, 2 µs resolution, default 100 ms.
  Sending `APERture` sets `APERture:ENABled ON`; sending `NPLC` or `RESolution`,
  or any `CONFigure`/`MEASure?`, sets it OFF. The last of NPLC/aperture sent wins.
- `[SENSe:]<fn>:RESolution <v>` is in measurement units (V, A, Ω), not digits;
  `MIN` is finest, `MAX` coarsest; the default maps to 10 PLC.
- The range-and-resolution tables (OSG p.450-453) map each range and NPLC to a
  resolution figure (e.g. 34461A, 10 V range, 10 NPLC gives 10 µV). Look exact
  figures up there rather than quoting from memory.

## Triggering and reading acquisition

```
TRIGger:SOURce {IMMediate|EXTernal|BUS|INTernal}
TRIGger:COUNt {<count>|MIN|MAX|DEF|INFinity}      # trigger events to accept
TRIGger:DELay {<seconds>|MIN|MAX|DEF}             # delay trigger -> first sample
TRIGger:DELay:AUTO {OFF|ON}                       # settling-based auto delay
TRIGger:SLOPe {POSitive|NEGative}                 # external-trigger edge
TRIGger:LEVel {<level>|MIN|MAX|DEF}               # 34465A/70A + DIG: level trigger
SAMPle:COUNt {<count>|MIN|MAX|DEF}                # samples per trigger
SAMPle:SOURce {IMMediate|TIMer}                   # 34465A/70A
SAMPle:TIMer {<interval>|MIN|MAX|DEF}             # 34465A/70A: time between samples
SAMPle:COUNt:PRETrigger {<count>|MIN|MAX|DEF}     # 34465A/70A: pre-trigger samples
```

- `IMMediate` fires continuously; `EXTernal` uses the rear Ext Trig BNC (edge set
  by `TRIGger:SLOPe`); `BUS` waits for `*TRG` (or a GPIB GET); `INTernal` is level
  triggering (34465A/70A with the DIG option, with `TRIGger:LEVel`).
- Sending `*TRG` when the source is not `BUS` raises
  `-221,"Settings conflict; *TRG when TRIG:SOUR BUS not selected"`.
- `OUTPut:TRIGger:SLOPe {POSitive|NEGative}` sets the VM Complete BNC output edge.
- Automatic trigger delays depend on function, range and filter (OSG p.454).

### Acquisition modes
`ABORt`/`INITiate`/`SAMPle`/`TRIGger` are the Continuous-mode SCPI model. The
front panel adds two modes on the 34465A/70A, driven from `[Acquire]`, not from
dedicated SCPI (OSG p.47):

- **Continuous** - default, free-running, the model above.
- **Data Log** - timed logging to memory or file, front panel only. Up to
  1000 readings/s, 100 h, 360,000,000 readings to a file, or the memory depth
  (50,000, or 2,000,000 with MEM) to memory; trigger is auto or one `[Single]`
  only (no external or level). On entry it sets trigger source and delay to auto,
  pretrigger count 0, sample timer mode on with the chosen interval, and samples
  per trigger from the chosen duration.
- **Digitize** - fast fixed-rate sampling (34465A/70A with DIG), front panel
  only, on DCV or DCI with autorange and autozero off. Sample interval 20 µs
  (50 kSa/s) to 100 ms; trigger auto, external or level, with a pretrigger count
  up to total readings minus one. On entry it forces auto/external/level trigger,
  turns off limits and scaling, and post-processes statistics and histogram.
- Entering either mode also sets trigger count 1, turns off secondary
  measurements and smoothing, and clears statistics and the histogram. Reproduce
  the same captures over SCPI with `SAMPle:SOURce TIMer` + `SAMPle:TIMer` (timed
  log) or a short aperture and large `SAMPle:COUNt` (digitize), plus level
  triggering.

## Reading memory and data format

```
READ?                      # trigger + return readings
FETCh?                     # return memory, no re-trigger
R? [<max>]                 # return + erase oldest (FIFO)
DATA:POINts?               # readings currently in memory
DATA:LAST?                 # most recent reading, with units
DATA:REMove? <n> [,WAIT]   # return + erase n oldest; WAIT blocks until n exist
DATA:POINts:EVENt:THReshold <count>   # memory-threshold event level (Operation bit 9)
FORMat[:DATA] {ASCii|REAL} [,<length>]   # 34465A/70A; REAL,64 is binary doubles
FORMat:BORDer {NORMal|SWAPped}           # byte order for REAL
```

For large or fast captures use `FORMat REAL,64` and `query_binary_values`. ASCII
(the default) is fine for modest counts.

## Math (CALCulate)

Math runs on readings as they are taken. Enable a feature's `[:STATe]` and read
its result. Some functions disallow a given math; the instrument replies
`-221,"Settings conflict; ... not allowed in current measurement function; ...
OFF set"` and disables it.

- **Statistics** - `CALCulate:AVERage[:STATe] ON`, then
  `CALCulate:AVERage:{AVERage|MINimum|MAXimum|PTPeak|SDEViation|COUNt|ALL}?`.
  `ALL?` returns average, sdev, min, max in one query. `:CLEar` resets.
- **Limit testing** - `CALCulate:LIMit[:STATe] ON`,
  `CALCulate:LIMit:{LOWer|UPPer}[:DATA] <v>`. A failed reading sets Questionable
  bit 11 (lower) or 12 (upper).
- **Histogram** (all models; the 34465A/70A add on-screen cursors) -
  `CALCulate:TRANsform:HISTogram[:STATe] ON`, `:POINts <bins>` (default 100),
  `:RANGe:AUTO {OFF|ON}`, `:RANGe:{LOWer|UPPer} <v>`; read `:DATA?`, `:ALL?`,
  `:COUNt?`; `:CLEar` resets.
- **Scaling** - `CALCulate:SCALe[:STATe] ON`, `:FUNCtion {DB|DBM|PCT|SCALe}`.
  `DB` and `DBM` work on all models (ACV/DCV only); they use `:DB:REFerence` /
  `:DBM:REFerence` (dBm reference resistance default 600 Ω), or `:REFerence` with
  `:REFerence:AUTO`. The `PCT` (percent) and `SCALe` (Mx-B) functions are
  **34465A/70A only**: for `SCALe`, `:GAIN <m>` and `:OFFSet <b>` compute `m*x+b`,
  and `:UNIT <str>` / `:UNIT:STATe` label the result.
- **Smoothing** (34465A/70A) - `CALCulate:SMOothing[:STATe] ON`,
  `:RESPonse {SLOW|MEDium|FAST}` - a moving-average (boxcar) filter, SLOW over
  100 readings, MEDium 50, FAST 10.
- **Trend chart** - `CALCulate:TCHart[:STATe] {OFF|ON}` (display feature).
- `CALCulate:CLEar[:IMMediate]` clears all math.

## Secondary measurements

Show a second quantity derived from the primary with
`[SENSe:]<fn>:SECondary "<choice>"` (a quoted string), read with
`[SENSe:]DATA2?`, and clear or restart with `[SENSe:]DATA2:CLEar`. The feature
exists on all models; the `"CALCulate:DATA"` (pre-math) and `"PTPeak"` (peak)
choices are 34465A/70A only.

| Primary function | Allowed secondary strings (default `"OFF"`) |
|---|---|
| `VOLTage[:DC]` | `"CALCulate:DATA"`, `"VOLTage:AC"`, `"PTPeak"` |
| `VOLTage:AC` | `"CALCulate:DATA"`, `"FREQuency"`, `"VOLTage[:DC]"` |
| `VOLTage[:DC]:RATio` | `"CALCulate:DATA"`, `"SENSe:DATA"` |
| `CURRent[:DC]` | `"CALCulate:DATA"`, `"CURRent:AC"`, `"PTPeak"` |
| `CURRent:AC` | `"CALCulate:DATA"`, `"FREQuency"`, `"CURRent[:DC]"` |
| `FREQuency` | `"CALCulate:DATA"`, `"PERiod"`, `"VOLTage:AC"` |
| `PERiod` | `"CALCulate:DATA"`, `"FREQuency"`, `"VOLTage:AC"` |
| `RESistance`/`FRESistance` | `"CALCulate:DATA"` |
| `CAPacitance` | `"CALCulate:DATA"` |
| `TEMPerature` | `"CALCulate:DATA"`, `"SENSe:DATA"` |

- `"CALCulate:DATA"` mirrors the reading before math (including NULL).
- `"PTPeak"` returns three values: min peak, max peak, peak-to-peak.
- `"SENSe:DATA"` returns the raw sensor value (ohms for RTD/thermistor; signal and
  reference volts for ratio; TC volts and reference temperature).
- The cross-function pairs (DCV<->ACV, DCI<->ACI) **work from the front panel
  only and are ignored over remote**; program the two functions separately
  instead. `DATA2?` returns `9.91E37` (NaN) when no valid secondary is selected.

## Display, files and state

- `DISPlay[:STATe] {OFF|ON}` - turning the display off speeds up remote readings.
  `DISPlay:VIEW {NUMeric|HISTogram|TCHart|METer}`; `DISPlay:TEXT[:DATA] "<s>"` /
  `DISPlay:TEXT:CLEar` to post a message.
- `HCOPy:SDUMp:DATA?` grabs a screen image; `HCOPy:SDUMp:DATA:FORMat {PNG|BMP}`.
- State slots: `*SAV {0|1|2|3|4}` / `*RCL {0|1|2|3|4}` for the five slots.
  `MMEMory:STORe:STATe <file>` / `MMEMory:LOAD:STATe <file>` store named state
  files; `MMEMory:STORe:PREFerences` / `LOAD:PREFerences` the I/O and display
  preferences. Power-on recall: `MMEMory:STATe:RECall:AUTO ON` with
  `MMEMory:STATe:RECall:SELect <file>`; check a slot with
  `MMEMory:STATe:VALid? <file>`.
- Files: `MMEMory:CATalog[:ALL]?`, `CDIRectory`, `MDIRectory`, `RDIRectory`,
  `COPY <a>,<b>`, `MOVE <a>,<b>`, `DELete`. Transfer:
  `MMEMory:UPLoad? <file>` (read out) and `MMEMory:DOWNload:FNAMe <file>` +
  `MMEMory:DOWNload:DATA <block>` (write in). Store readings with
  `MMEMory:STORe:DATA RDG_STORE, <file>`; CSV layout with
  `MMEMory:FORMat:READing:{CSEParator|INFormation|RLIMit}` (34465A/70A).

## System

- `SYSTem:BEEPer[:IMMediate]` (beep now) / `:BEEPer:STATe`,
  `SYSTem:CLICk:STATe`, `SYSTem:DATE <y>,<m>,<d>` / `:TIME <h>,<m>,<s>`,
  `SYSTem:LABel "<s>"` (banner), `SYSTem:WMESsage "<s>"` (power-on message),
  `SYSTem:LFRequency?`, `SYSTem:TEMPerature?`, `SYSTem:UPTime?`,
  `SYSTem:VERSion?`, `SYSTem:HELP?`, `SYSTem:PRESet` (front-panel Preset),
  `SYSTem:LOCal` (return to local), `SYSTem:USB:HOST:ENABle {OFF|ON}`.
- `*TST?` / `TEST:ALL?` run the full self-test (0 = pass; failures queue a
  `+6xx` error). `*OPT?` returns the installed options as a comma-separated
  string; `SYSTem:LICense:CATalog?` lists them by name. `ROUTe:TERMinals?`
  returns the Front/Rear input switch position (`FRON` or `REAR`; the 34460A
  always returns `FRON`), the only way to read it over remote.
- `SYSTem:IDENtify {DEFault|AT34460A|AT34461A|AT34410A|AT34411A|HP34401A}` makes
  `*IDN?` emulate another model's identity; the valid set depends on the model
  (34460A: AT34460A/HP34401A; 34461A: AT34461A/HP34401A; 34465A/70A:
  AT34410A/AT34411A).
- Interface lock for exclusive control: `SYSTem:LOCK:REQuest?` (returns 1 if
  granted), `SYSTem:LOCK:RELease`, `SYSTem:LOCK:OWNer?`, `SYSTem:LOCK:NAME?`.
  Holding a lock sets Operation bit 10.
- Licensing: `SYSTem:LICense:CATalog?` (installed options),
  `:INSTall [{<folder>|<file>}]`, `:INSTall? "<opt>"`, `:DELete "<opt>"`,
  `:DELete:ALL`, `:DESCription? "<opt>"`, `:ERRor?`, `:ERRor:COUNt?`.
- File security (SEC): `SYSTem:SECurity:IMMediate` sanitizes all user memory
  (NISPOM); `SYSTem:SECurity:COUNt?` returns the sanitize count.
- LAN config: `SYSTem:COMMunicate:LAN:` `DHCP`, `IPADdress`, `SMASk`, `GATeway`,
  `DNS[1|2]`, `HOSTname`, `DOMain?`, `MAC?`, `WINS[1|2]`, `CONTrol?`,
  `TELNet:PROMpt`, `TELNet:WMESsage`; queries take `[{CURRent|STATic}]`. Apply
  changes with `SYSTem:COMMunicate:LAN:UPDate`, then cycle power.
- LXI: `LXI:IDENtify[:STATe] {OFF|ON}` (flash the identify indicator),
  `LXI:MDNS:ENABle`, `LXI:MDNS:HNAMe[:RESolved]?`,
  `LXI:MDNS:SNAMe:DESired "<n>"` / `SNAMe[:RESolved]?`, `LXI:RESet`,
  `LXI:RESTart`.

## Status system

Standard IEEE-488.2 model: a Questionable Data group, a Standard Operation group,
the Standard Event register and the Status Byte. Each group has a condition
register (`:CONDition?`, live, not latched), an event register (`[:EVENt]?`,
latched, cleared on read) and an enable register (`:ENABle <mask>`). `*CLS`
clears every event register and the error queue. The enable masks survive
`*RST`, `SYSTem:PRESet` and `*CLS`; only `STATus:PRESet` clears the Operation and
Questionable enable registers.

Questionable Data register bits (`STATus:QUEStionable`):

| Bit | Dec | Meaning |
|---|---|---|
| 0 | 1 | Voltage overload (event only) |
| 1 | 2 | Current overload (event only) |
| 2 | 4 | Sample timing violation (SAMPle:TIMer; 34465A/70A) |
| 4 | 16 | Temperature overload (event only) |
| 5 | 32 | Frequency overload/underflow (event only) |
| 8 | 256 | Calibration data corrupt |
| 9 | 512 | Resistance overload (event only) |
| 10 | 1024 | Capacitance overload (event only) |
| 11 | 2048 | Lower limit failed |
| 12 | 4096 | Upper limit failed |
| 14 | 16384 | Reading memory overflow (oldest readings lost) |

Overload bits latch once per `INITiate`; clearing one does not re-set it until
the next `INITiate`.

Standard Operation register bits (`STATus:OPERation`):

| Bit | Dec | Meaning |
|---|---|---|
| 0 | 1 | Calibrating |
| 4 | 16 | Measuring (initiated, taking or about to take a reading) |
| 5 | 32 | Waiting for trigger |
| 8 | 256 | Configuration changed since last INIT/READ?/MEASure? |
| 9 | 512 | Memory threshold reached (DATA:POINts:EVENt:THReshold) |
| 10 | 1024 | Instrument locked by a remote interface |
| 13 | 8192 | Global error (some interface has an error queued) |

Standard Event register (`*ESE` / `*ESR?`): bit 0 Operation Complete, 2 Query
error, 3 Device-specific error (any -300 or positive error), 4 Execution error
(-200s), 5 Command error (-100s), 7 Power-on.

Status Byte (`*STB?` / `*SRE`): bit 2 Error queue, 3 Questionable summary,
4 Message available, 5 Standard Event summary, 6 Master summary (RQS), 7 Standard
Operation summary.

`*OPC` / `*OPC?` / `*WAI` synchronize: `*OPC?` returns 1 when a pending overlapped
operation (an `INIT`) finishes. `*PSC {0|1}` controls power-on status clearing.

```python
dmm.write("INIT")
dmm.query("*OPC?")            # blocks until the acquisition completes
n = int(dmm.query("DATA:POIN?"))
```

## Errors

`SYSTem:ERRor[:NEXT]?` pops the oldest error as `<code>,"<text>"`; `+0,"No error"`
when empty. Up to 20 errors, FIFO, per I/O session plus a global hardware queue;
`*CLS` and power cycle clear them, `*RST` and `SYSTem:PRESet` do not. The queue
overflows to `-350,"Queue overflow"`.

By range (OSG p.458-471): command errors -100s, execution -200s, device-specific
-300s, query -400s, network +100s, instrument +200s, licensing +600s, self-test
+611 to +666, calibration +701 onward. The ones worth recognising:

- `-113,"Undefined header"` - misspelled command.
- `-221,"Settings conflict; ..."` - the text after the semicolon says exactly
  what the instrument changed to resolve the conflict (e.g. `...TRIG:SOUR IMM
  set`, `...SAMP:TIM changed`, `...CALC:LIM:STAT OFF set`). Read it.
- `-222,"Data out of range"` - optionally `; value clipped to lower/upper limit`
  or `; value requires license DIG/MEM`.
- `-203,"Command protected; ..."` - the feature needs an unsecured instrument
  (`instrument must be unsecured`), a license (`requires license DIG/SEC/LAN`,
  `large memory requires license MEM`), or a higher model (`feature not available
  on this model`).
- `+6xx` self-test failures name the failing subsystem (ADC, FPGA, references,
  autocal points); `+7xx` are calibration errors (`secure code provided was
  invalid`, `calibration memory is secured`).

```python
def check_errors(dmm):
    errs = []
    while True:
        code, msg = dmm.query("SYST:ERR?").strip().split(",", 1)
        if int(code) == 0:
            return errs
        errs.append((int(code), msg.strip('"')))
```

## Calibration (documented)

The guide documents the secured/unsecured workflow; the full adjustment
procedure, with its reference standards, is OSG p.521-567.

```
*CAL?                                 # autocalibration (34465A/70A); 0 = pass
CALibration[:ALL]?                    # full calibration; 0 = pass
CALibration:ADC?                      # ADC cal; 0 = pass
CALibration:COUNt?                    # times calibrated (increments on STORe)
CALibration:DATE? / :TIME? / :TEMPerature?
CALibration:SECure:STATe {OFF|ON} [,<code>]   # unsecure with the code
CALibration:SECure:CODE <new_code>            # change the code (while unsecured)
CALibration:VALue <value>             # the known value of the applied standard
CALibration:STRing "<string>"         # free-text cal message
CALibration:STORe                     # commit cal constants to nonvolatile memory
SYSTem:ACALibration:DATE? / :TIME? / :TEMPerature?   # 34465A/70A autocal info
```

An adjustment is: unsecure (`CALibration:SECure:STATe OFF,<code>`), apply a
standard, tell the instrument its value (`CALibration:VALue`), run the relevant
`CALibration...?` step, repeat per point, then `CALibration:STORe`. Compare
`CALibration:COUNt?` before and after to confirm the store. A lost security code
is recovered with the guide's **Security Code Override** hardware-jumper
procedure (OSG p.497), which this skill does not reproduce.

## Reset / power-on defaults (the ones that bite)

After `*RST` or `SYSTem:PRESet` (OSG p.472): function **DC volts**, **autorange**,
**10 NPLC** (resolution to match, aperture off/100 ms), **autozero on**, AC filter
**20 Hz (Medium)**, frequency gate **100 ms**, temperature transducer **FRTD**
(R0 100 Ω, TC type J, internal reference 0 °C), current terminals **3 A**,
current switch mode **Continuous**, all nulls **off** (reference 0, auto-reference
on), secondary measurements **off**, math **off** (histogram 100 bins auto,
statistics cleared), screen-shot format **PNG**, reading memory **cleared**.
Nonvolatile (survive reset, bulleted in the guide): dBm reference resistance
(600 Ω), beeper, thousands separator, stored states, calibration state (secured),
and all I/O configuration. The **error queue** is cleared only at power-on, not
by `*RST`.

## Common recipes

```python
# 1. Single reading
dmm.query("MEAS:VOLT:DC? 10,1e-5")

# 2. 4-wire resistance, offset compensated (34465A/70A), 10 NPLC
dmm.write("CONF:FRES 1e3")
dmm.write("FRES:OCOM ON; :FRES:NPLC 10")
print(dmm.query("READ?"))

# 3. Thermocouple type K, internal reference junction (34465A/70A)
dmm.write("CONF:TEMP TCouple,K")
dmm.write("TEMP:TRAN:TC:RJUN:TYPE INT; :UNIT:TEMP C")
print(dmm.query("READ?"))

# 4. 1000-point timed log at 10 ms spacing (34465A/70A), binary transfer
dmm.write("CONF:VOLT:DC 10")
dmm.write("VOLT:DC:NPLC 0.02")
dmm.write("SAMP:SOUR TIM; :SAMP:TIM 0.01; :SAMP:COUN 1000; :TRIG:SOUR IMM")
dmm.write("FORM:DATA REAL,64")
dmm.write("INIT"); dmm.query("*OPC?")
data = dmm.query_binary_values("FETC?", datatype='d')

# 5. Statistics over 100 readings
dmm.write("CONF:VOLT:DC 10")
dmm.write("CALC:AVER:STAT ON; :SAMP:COUN 100; :TRIG:SOUR IMM")
dmm.write("INIT"); dmm.query("*OPC?")
avg, sdev, mn, mx = dmm.query("CALC:AVER:ALL?").strip().split(",")

# 6. Limit test with status
dmm.write("CONF:VOLT:DC 10")
dmm.write("CALC:LIM:LOWer 4.9; :CALC:LIM:UPPer 5.1; :CALC:LIM:STAT ON")

# 7. DCV secondary = AC (program both functions; cross-function secondary is
#    front-panel only over remote). Here: read DCV, then ACV separately.
dmm.write("CONF:VOLT:DC 10"); dc = dmm.query("READ?")
dmm.write("CONF:VOLT:AC 10"); ac = dmm.query("READ?")
```

## Front panel, Probe Hold and web interface

Most front-panel settings have a direct SCPI command; the Front Panel Menu
Reference (OSG p.50) maps them. `[Shift]` is the gold/second key, and a label
printed above a key is its shifted function (`[Shift]+[DCV]` = DCI,
`[Shift]+[Freq]` = Capacitance, `[Shift]+[Null]` = Math, `[Shift]+[Display]` =
Utility, `[Shift]+[Run/Stop]` = Reset). `[Shift] > [Help] > About` shows model,
serial, firmware and options; the Help key shows the remote error queue;
`[Acquire]` selects Continuous/Data Log/Digitize on the 34465A/70A.
`SYSTem:LOCal` or the Local key returns to front-panel control.

- **Probe Hold** (`[Shift]+[Single]`, OSG p.100) captures up to 8 stable
  readings automatically (a beep on each), useful when probing where you cannot
  watch the screen. Front panel only; the held list cannot be read over remote.
- **Web interface**: browse to the instrument's IP. It offers an HTML5 soft
  front panel and an Instrument IO page that sends SCPI, plus LAN configuration.
  The default password for control is `Keysight`; a LAN Reset
  (`[Utility] > I/O Config > LAN Reset`, or `LXI:RESet`) clears a changed
  password and re-enables mDNS. Monitoring from the web does not put the
  instrument in remote, so it is the safe way to watch a data-log or digitize run.
- **Reading memory is cleared** by: a function change, entering or leaving Probe
  Hold, a temperature-unit change, any dB/dBm parameter change, a histogram
  binning change, a probe or R0 change, a state recall, calibration, switching
  3 A/10 A terminals, the Front/Rear switch, a remote-to-local transition, and
  turning null on or off. It is not cleared by a range, aperture, limit or
  display-mode change (OSG p.99).

## Notes and limits

- This is the **documented** feature set of firmware A.03.03. Undocumented
  DIAGnostic/service commands, the AC-mode variant and firmware internals are in
  the 344xxA Firmware Supplement (link above), kept separate on purpose.
- Exact resolution-vs-NPLC figures, accuracy and temperature coefficients are in
  the guide's tables (OSG p.450-453) and the datasheet; look them up rather than
  quoting from memory.
- Where the guide itself is inconsistent (capacitance model availability, the
  5 kΩ-only thermistor type versus the prose, the capacitance NULL default), this
  skill flags it rather than inventing a resolution. Confirm on the instrument
  when it matters.