# SDG2000X SCPI command reference

Distilled from Siglent *SDG Series Programming Guide* PG02-E05C, filtered to the commands the
availability tables mark as supported on **SDG2000X**, then **corrected against a real
SDG2122X running firmware 2.01.01.39R7**. Entries marked *(verified)* were exercised on that
instrument; entries marked *(guide says supported — actually rejected)* are documentation
errors in PG02-E05C that will waste your time otherwise. Commands belonging to other SDG families
(sequences, digital channels, frequency hop, IQ, `MMEMory:`, `SENSe:COUNTer:`, PRBS, digital
filter, output skew) are omitted — they will not work here.

## Contents

- [Syntax and conventions](#syntax-and-conventions)
- [Common (IEEE 488.2) commands](#common-ieee-4882-commands)
- [OUTPUT — output port, load, polarity](#output--output-port-load-polarity)
- [BSWV — basic waveform](#bswv--basic-waveform)
- [MDWV — modulation](#mdwv--modulation)
- [SWWV — sweep](#swwv--sweep)
- [BTWV — burst](#btwv--burst)
- [ARWV / STL / WVDT — arbitrary waveforms](#arwv--stl--wvdt--arbitrary-waveforms)
- [SRATE — DDS vs TrueArb](#srate--dds-vs-truearb)
- [HARM — harmonic generation](#harm--harmonic-generation)
- [COUP / PACP / MODE / EQPHASE / CMBN — channel relationships](#coup--pacp--mode--eqphase--cmbn--channel-relationships)
- [SYNC — sync output](#sync--sync-output)
- [FCNT — frequency counter](#fcnt--frequency-counter)
- [ROSC — clock source](#rosc--clock-source)
- [Protection and status](#protection-and-status)
- [System and interface](#system-and-interface)
- [VKEY — virtual front-panel keys](#vkey--virtual-front-panel-keys)
- [CASCADE — multi-instrument sync](#cascade--multi-instrument-sync)
- [Built-in arbitrary waveform index table](#built-in-arbitrary-waveform-index-table)
- [Commands NOT supported on SDG2000X](#commands-not-supported-on-sdg2000x)

## Syntax and conventions

- `<channel>` is `C1` or `C2`. Most signal commands are channel-prefixed; system commands are not.
- Keywords have a long and a short form; the short form is the capitalised part of the long form
  (`BaSic_WaVe` → `BSWV`). Both are accepted. Case is not significant.
- Parameters follow the command as comma-separated `KEY,VALUE` pairs. Multiple pairs go in one
  command: `C1:BSWV WVTP,SINE,FRQ,1000,AMP,2`.
- Terminate every command with `\n`. Queries end with `?`.
- Numbers accept plain decimal (`1000000`), scientific (`1E6`, `100e-9`) and, for some
  parameters, unit suffixes. Plain SI-base numbers are the safest: Hz, seconds, volts.
- Query responses **always** carry the command header — there is no `CHDR` on this model.

## Common (IEEE 488.2) commands

| Command | Effect |
|---|---|
| `*IDN?` | Returns `Siglent Technologies,<model>,<serial>,<firmware>`. Note this is the *short* response format — no `*IDN,` prefix, no hardware-version field, unlike SDG800/1000/5000. |
| `*OPC` / `*OPC?` | Sets/queries the OPC bit. `*OPC?` always returns `1`, but only once every prior command has been fully processed — which makes it a cheap and effective synchronisation handshake. |
| `*RST` | Full device reset to factory defaults. Takes ~2–3 s; wait before querying. Wipes the user's front-panel setup, so ask before using it in a script. Note the reset load is **HiZ**, not the 50 Ω the user manual's default table implies. |
| `*CLS` | Clears the status registers and the error queue. *(verified)* |
| `*ESR?` | Standard Event Status Register. Returns 32 after a command error; **self-clears on read**. *(verified)* |
| `*STB?`, `*TST?`, `*SRE?`, `*ESE?` | All present and answer. `*TST?` returns 0. *(verified)* |
| `SYST:ERR?` | **The error queue — it exists**, contrary to what the absence of any mention in the programming guide suggests. FIFO, standard SCPI format, `0,"No error"` when clean. *(verified)* |

### Using the error queue

`SYST:ERR?` is the fastest and most definitive way to test whether a command exists on this
model — far better than waiting for a query to time out:

```python
dev.write(candidate_command)
verdict = dev.query("SYST:ERR?")     # '0,"No error"' means the header was understood
```

Codes seen in practice: `-113,"Undefined header;<the command>"` for an unknown command or a bad
channel prefix (`C3:`, `C0:`); `-108,"Parameter not allowed"`; `-101,"Invalid character"`;
`-200,"Execution error"` for a header the parser knows but this model cannot execute.

**Its blind spot is the important part.** All of the following return `0,"No error"` and have
no effect: an unknown parameter name (`C1:BSWV NOSUCHPARAM,5`), an unrecognised enum value
(`C1:BSWV WVTP,BANANA` leaves `WVTP` at `SINE`), and every kind of range clamping. A clean
queue proves the command was *parsed*, never that it was *applied*. Read back to confirm.

The queue persists across sessions — drain it at the start of a script, or `*CLS`, so you are
not reading errors left by whatever ran before you.

## OUTPUT — output port, load, polarity

```
<channel>:OUTPut ON|OFF
<channel>:OUTPut LOAD,<load>
<channel>:OUTPut PLRT,NOR|INVT
<channel>:OUTPut?
OUT_BOTHCH ON|OFF
```

| Parameter | Values |
|---|---|
| state | `ON` / `OFF` |
| `LOAD` | `50` to `100000` (ohms), or `HZ` for High-Z. Default 50. |
| `PLRT` | `NOR` (normal) / `INVT` (inverted). Inverting the waveform does **not** invert the sync output. |

Query response *(verified)*, which carries an undocumented `POWERON_STATE` field:

```
C1:OUTP OFF,LOAD,HZ,POWERON_STATE,OFF,PLRT,NOR
```

`LOAD` was verified accepting `HZ`, `50`, `75`, `600` and `100000`. Switching a channel from
`HZ` to `50` with a 2 Vpp setting reports `1V` afterwards — the factor-of-two the load model
predicts.

`OUT_BOTHCH ON` switches both channels together — useful when two channels feed a differential
input and you don't want a window where only one is live.

`<channel>:BSWV MAX_OUTPUT_AMP,<1-20>` sets a maximum-amplitude ceiling in Vpp, mirroring
`Utility > Output > Amplitude`. *(verified: setting 5 then asking for `AMP,15` yields `5V`, and
the ceiling applies to **both channels** — `C2:BSWV?` reports the same `MAX_OUTPUT_AMP`.)*
Worth setting before handing a script to someone with fragile hardware on the bench. It also
appears in every `BSWV?` response.

`<channel>:NOISE_ADD STATE,ON|OFF,RATIO,<S/N>` (or `RATIO_DB,<dB>`) adds noise at a specified
SNR. The header is accepted and `C1:NOISE_ADD?` answers
`C1:NOISE_ADD STATE,OFF,RATIO,100,RATIO_DB,20dB`, but in testing neither `STATE,ON` nor a
`RATIO` value took effect from a default state — it presumably has a carrier-type or mode
precondition. Read back before relying on it.

## BSWV — basic waveform

```
<channel>:BaSic_WaVe <param>,<value>[,<param>,<value>...]
<channel>:BaSic_WaVe?
```

| Param | Value | Notes |
|---|---|---|
| `WVTP` | `SINE`,`SQUARE`,`RAMP`,`PULSE`,`NOISE`,`ARB`,`DC` | Omitting it leaves the current type. |
| `FRQ` | Hz | Not valid for NOISE/DC. Sine 1 µHz–120 MHz (model-dependent), Square/Pulse 1 µHz–25 MHz, Ramp 1 µHz–1 MHz, Arb-DDS 1 µHz–20 MHz. |
| `PERI` | seconds | The reciprocal view of `FRQ`. |
| `AMP` | Vpp | 2 mVpp–20 Vpp into HiZ below 20 MHz; 10 Vpp above 20 MHz; halved into 50 Ω. |
| `AMPVRMS` | Vrms | |
| `AMPDBM` | dBm | Only meaningful with a non-HiZ load. |
| `OFST` | volts | Not valid for NOISE. |
| `HLEV` / `LLEV` | volts | High/low level. Equivalent to `AMP`/`OFST`; setting one pair updates the other. |
| `PHSE` | 0–360 degrees | Not valid for NOISE, PULSE or DC. Only meaningful in `MODE PHASELOCKED`. |
| `SYM` | 0–100 % | RAMP only — percentage of the period spent rising. 100 % = sawtooth, 50 % = triangle. |
| `DUTY` | 0.001–99.999 % | SQUARE or PULSE. Achievable range narrows as frequency rises. |
| `WIDTH` | seconds | PULSE only. Minimum 16.3 ns. Another view of `DUTY`. |
| `RISE` / `FALL` | seconds | PULSE only. 10–90 % and 90–10 %. Range 8.4 ns–22.4 ns, further constrained by the pulse width. |
| `DLY` | seconds | Waveform delay. |
| `STDEV` | volts | NOISE only — Gaussian standard deviation. |
| `MEAN` | volts | NOISE only. |
| `BANDSTATE` | `ON`/`OFF` | NOISE only — enables the noise bandwidth limit. |
| `BANDWIDTH` | Hz | NOISE only, and only when `BANDSTATE,ON`. |

Query response *(verified — richer than the programming guide shows, with `AMPDBM`,
`MAX_OUTPUT_AMP` and `DLY` always present)*:

```
C1:BSWV WVTP,SINE,FRQ,1000HZ,PERI,0.001S,AMP,4V,AMPVRMS,1.414Vrms,AMPDBM,0dBm,MAX_OUTPUT_AMP,20V,OFST,0V,HLEV,2V,LLEV,-2V,PHSE,0,DLY,0S
```

Verified clamping behaviour on an SDG2122X, all silent and all with an empty error queue:

| Requested | Result |
|---|---|
| `WVTP,SINE,FRQ,200000000` | `120000000HZ` |
| `WVTP,SQUARE,FRQ,50000000` | `25000000HZ` |
| `WVTP,RAMP,FRQ,5000000` | `1000000HZ` |
| `AMP,30` at 1 kHz | `20V` |
| `AMP,20` at 50 MHz | `10V` |
| `AMP,0.0001` | `0.002V` |
| `WVTP,PRBS` or `WVTP,IQ` or `WVTP,BANANA` | ignored, `WVTP` unchanged |

`AMPDBM,0` into a 50 Ω load gives `AMP,0.632551V` — correct for 0 dBm. Into `LOAD,HZ` the
command is accepted without error; treat dBm as meaningful only with a real load set.

DC output is just `WVTP,DC` plus `OFST`: ±10 V into HiZ, ±5 V into 50 Ω. Note that in the
front-panel "high resolution" DC setting, changing gear (every ±2 V at HiZ, ±1 V at 50 Ω)
briefly drops the output to 0 V; the low-resolution setting avoids the glitch at the cost of
accuracy within a gear.

## MDWV — modulation

```
<channel>:MoDulateWaVe STATE,ON        <- required first
<channel>:MoDulateWaVe <TYPE>          <- select modulation type
<channel>:MoDulateWaVe <TYPE>,<param>,<value>
<channel>:MoDulateWaVe CARR,<param>,<value>
<channel>:MoDulateWaVe?
```

`<TYPE>` is one of `AM`, `DSBAM`, `FM`, `PM`, `PWM`, `ASK`, `FSK`, `PSK`.

Common sub-parameters, prefixed by the type (e.g. `AM,FRQ,1000`):

| Sub-param | Applies to | Values |
|---|---|---|
| `SRC` | all | `INT`, `EXT`; additionally `CH1`/`CH2` for AM, FM, PM, PWM (use the other channel as the modulating source — no cable needed). DSBAM/ASK/FSK/PSK are `INT`/`EXT` only. |
| `MDSP` | AM, DSBAM, FM, PM, PWM | `SINE`,`SQUARE`,`TRIANGLE`,`UPRAMP`,`DNRAMP`,`NOISE`,`ARB`. Internal source only. |
| `FRQ` | AM, DSBAM, FM, PM, PWM | Modulating frequency, 1 mHz–1 MHz internal. |
| `DEPTH` | AM | 0–120 %. At high depth the peak-to-peak output exceeds the set amplitude — carrier *power* is held constant, not peak voltage. |
| `DEVI` | FM | Frequency deviation in Hz, 0 to 0.5 × instrument bandwidth, further limited by the carrier frequency. |
| `DEVI` | PM | Phase deviation, 0–360°. |
| `DEVI` | PWM | Duty-cycle deviation in %, limited by the carrier duty. Resolution 6.67 ns of pulse width. |
| `KFRQ` | ASK, FSK, PSK | Keying rate, 1 mHz–1 MHz internal. |
| `HFRQ` | FSK | The "1" frequency; the "0" frequency is the carrier frequency. |
| `PLRT` | PSK | `POS` / `NEG`. |

Carrier sub-parameters, prefixed `CARR`: `WVTP` (`SINE`,`SQUARE`,`RAMP`,`ARB`,`PULSE`), `FRQ`,
`PHSE`, `AMP`, `OFST`, `SYM`, `DUTY`, `RISE`, `FALL`, `DLY`. PWM requires a `PULSE` carrier;
the other types do not accept PULSE, NOISE or DC carriers.

With external modulation the depth/deviation is set by the input amplitude on the rear Aux In:
11–13 Vpp (12 typical) corresponds to 100 % modulation, input bandwidth 0–50 kHz, 10 kΩ input
impedance. The UI stops showing the modulation frequency/shape in this mode because they now
come entirely from the external signal.

Query with `STATE,OFF` returns only `C1:MDWV STATE,OFF`, and a parameter written while the
mode is off is discarded with no error. Real responses *(verified)*:

```
C1:MDWV STATE,ON,AM,MDSP,SINE,SRC,INT,FRQ,100HZ,DEPTH,100,CARR,WVTP,SINE,FRQ,1000HZ,AMP,4V,AMPVRMS,1.414Vrms,AMPDBM,0dBm,OFST,0V,PHSE,0
C1:MDWV STATE,ON,FM,MDSP,SINE,SRC,INT,FRQ,100HZ,DEVI,100HZ,CARR,WVTP,SINE,FRQ,1000HZ,AMP,4V,AMPVRMS,1.414Vrms,AMPDBM,0dBm,OFST,0V,PHSE,0
```

Note `FRQ` appears twice — once as the modulation rate and once inside `CARR`. Any parser that
flattens the response into a single dict must namespace everything after `CARR`.

## SWWV — sweep

```
<channel>:SweepWaVe STATE,ON           <- required first
<channel>:SweepWaVe <param>,<value>
<channel>:SweepWaVe MTRIG              <- fire one sweep (TRSR,MAN only)
<channel>:SweepWaVe?
```

| Param | Values |
|---|---|
| `TIME` | Sweep duration, seconds. 1 ms–500 s. |
| `START` / `STOP` | Start/stop frequency, Hz. |
| `CENTER` / `SPAN` | The equivalent centre/span view. |
| `SWMD` | `LINE` (linear), `LOG` (logarithmic), `STEP` |
| `DIR` | `UP`, `DOWN`, `UP_DOWN` |
| `SYM` | 0–100 %, split between up and down halves when `DIR,UP_DOWN` |
| `TRSR` | `INT` (free-run), `EXT` (rear Aux In edge), `MAN` (`MTRIG` or the on-screen button) |
| `TRMD` | `ON`/`OFF` — emit a trigger pulse on Aux In/Out at sweep start. Invalid when `TRSR,EXT`. |
| `EDGE` | `RISE`/`FALL` — which external edge triggers |
| `MARK_STATE` / `MARK_FREQ` | Frequency marker on/off and its frequency (must lie between start and stop) |
| `CARR,...` | `WVTP` (`SINE`,`SQUARE`,`RAMP`,`ARB`), `FRQ`, `PHSE`, `AMP`, `OFST`, `SYM`, `DUTY` |

`STARTTIME`, `ENDTIME` and `BACKTIME` (start-hold / end-hold / return time) appear in the
command table but are **not implemented on the SDG2000X**: they are accepted with an empty
error queue and never appear in the query response or take effect. Treat them as absent —
this is exactly the blind spot described in the error-queue section.

Real response *(verified)*, carrying two undocumented fields, `IDLE_FREQ` and `STEPNUM`:

```
C1:SWWV STATE,ON,TIME,1S,STOP,1500HZ,START,500HZ,CENTER,1000HZ,SPAN,1000HZ,TRSR,INT,TRMD,OFF,SWMD,LINE,DIR,UP,SYM,9.21166270775824e-48,MARK_STATE,OFF,MARK_FREQ,0HZ,IDLE_FREQ,START_FREQ,STEPNUM,2,CARR,WVTP,SINE,FRQ,1000HZ,AMP,4V,AMPVRMS,1.414Vrms,AMPDBM,0dBm,OFST,0V,PHSE,0
```

`IDLE_FREQ` is the front panel's idle-frequency choice (`START_FREQ` by default) and `STEPNUM`
the step count for `SWMD,STEP`. `SWMD` accepts `LINE`, `LOG` and `STEP`, all verified by
read-back. Ignore `SYM` unless `DIR,UP_DOWN` is active — it reports uninitialised garbage
(`9.2e-48` above) otherwise.

Log sweep is frequency-only. With external or manual triggering the frequency returns to the
start value and holds after each sweep completes.

## BTWV — burst

```
<channel>:BursTWaVe STATE,ON           <- required first
<channel>:BursTWaVe <param>,<value>
<channel>:BursTWaVe MTRIG
<channel>:BursTWaVe?
```

| Param | Values |
|---|---|
| `GATE_NCYC` | `NCYC` (N-cycle) or `GATE` (gated). Not valid with a NOISE carrier. |
| `TIME` | `INF`, or the cycle count 1…1,000,000. NCYC only. |
| `PRD` | Burst period, 1 µs–1000 s. `TRSR,INT` only; invalid for gated or external trigger. |
| `STPS` | Start phase, 0–360°. Not valid for NOISE or PULSE carriers. |
| `TRSR` | `INT`, `EXT`, `MAN` |
| `DLAY` | Trigger delay, up to 100 s. NCYC only. |
| `PLRT` | `POS`/`NEG` — gate polarity. GATE only. |
| `TRMD` | `RISE`, `FALL`, `OFF` — trigger-out edge alignment. NCYC with `TRSR,INT` or `MAN`. |
| `EDGE` | `RISE`/`FALL` — external trigger edge |
| `COUNT` | Number of bursts emitted per trigger. `TRSR,EXT` or `MAN` only. |
| `CARR,...` | `WVTP` (`SINE`,`SQUARE`,`RAMP`,`ARB`,`PULSE`,`NOISE`), `FRQ`, `PHSE`, `AMP`, `OFST`, `SYM`, `DUTY`, `RISE`, `FALL`, `DLY`, `STDEV`, `MEAN` |

Carrier frequency range in burst mode starts at 2 mHz. Trigger response time is up to 600 ns
(versus 100 ns for sweep), which matters if you are timing against the trigger-out.

Real response *(verified)*, and the 629 ns default `DLAY` the manual documents:

```
C1:BTWV STATE,ON,PRD,0.01S,STPS,0,TRSR,INT,TRMD,OFF,TIME,1,DLAY,6.29035e-07S,GATE_NCYC,NCYC,CARR,WVTP,SINE,FRQ,1000HZ,AMP,4V,AMPVRMS,1.414Vrms,AMPDBM,0dBm,OFST,0V,PHSE,0
```

`TIME` verified accepting `1`, `1000000` and `INF`; `2000000` clamps to `1000000`.

`COUP TRDUCH,ON` makes a manual trigger fire both channels at once — the only way to get
simultaneous two-channel bursts, and only in manual-trigger mode.

## ARWV / STL / WVDT — arbitrary waveforms

```
<channel>:ArbWaVe INDEX,<2-198>        <- built-in waveform by index
<channel>:ArbWaVe NAME,<name>          <- user-stored waveform by name
<channel>:ArbWaVe?
SToreList?                             <- everything stored
SToreList? BUILDIN                     <- built-in waveform names
SToreList? USER                        <- user waveform names
```

On the SDG2000X, `INDEX` addresses **built-in** waveforms only and `NAME` addresses
**user-defined** waveforms only. The path form (`NAME,"Local/wave.bin"`) is SDG7000A-only.
Select `C1:BSWV WVTP,ARB` first. Query response: `C1:ARWV INDEX,2,NAME,StairUp`.

Verified: indices **0 and 1 do work** (`Sine` and `Noise`) despite the programming guide giving
the range as 2–198, and an index above 198 clamps to 198 rather than erroring.

A trap after recalling a user waveform by name: `C1:ARWV NAME,skilltest` succeeds, but
`C1:ARWV?` then answers `C1:ARWV NAME,skilltest.bin` — with the extension appended and no
`INDEX` field — and feeding that string back as `C1:ARWV NAME,skilltest.bin` is rejected with
`-101,"Invalid character"`. Always recall by the bare name; strip any `.bin` you read back.

`STL?` returns an `M<n>, <name>` list; empty user slots read back as `EMPTY`.

For uploading waveform data (`WVDT`), the binary format, and the `.bin`/`.csv`/`.dat` file
layouts, see `arbitrary-waveforms.md`.

## SRATE — DDS vs TrueArb

```
<channel>:SampleRATE MODE,DDS|TARB
<channel>:SampleRATE VALUE,<samples per second>
<channel>:SRATE?
```

`DDS` resamples the stored waveform to hit a set output frequency (up to 20 MHz for arbs);
`TARB` (TrueArb) plays the points one-for-one at a chosen sample rate, 1 µSa/s–75 MSa/s, which
preserves fine detail and gives lower jitter. `VALUE` only applies in `TARB`.

The `INTER,<interpolation>` parameter is **silently ignored** on the SDG2000X: it raises no
error, and no `INTER` field ever appears in the `SRATE?` response *(verified)*. If you need
zero-order hold for a digital pattern, set it from the front-panel Arb menu.

Verified: `MODE,TARB` defaults to `VALUE,16384000Sa/s`; `VALUE,100000000` clamps to
`75000000Sa/s`. Response format is `C1:SRATE MODE,TARB,VALUE,10000000Sa/s`, or just
`C1:SRATE MODE,DDS` in DDS mode.

## HARM — harmonic generation

```
<channel>:HARMonic HARMSTATE,ON|OFF
<channel>:HARMonic HARMTYPE,EVEN|ODD|ALL
<channel>:HARMonic HARMORDER,<n>,HARMAMP,<Vpp>
<channel>:HARMonic HARMORDER,<n>,HARMDBC,<dBc>
<channel>:HARMonic HARMPHASE,<degrees>
<channel>:HARMonic?
```

Sine carrier only. Maximum order 16 *(verified: `HARMORDER,17` and `HARMORDER,20` both clamp
to 16, silently)*. Response format:
`C1:HARM HARMSTATE,ON,HARMTYPE,ALL,HARMORDER,2,HARMAMP,0V,HARMDBC,-80dBc,HARMPHASE,0`. `HARMTYPE,ALL` (the front panel calls it "Custom") allows
any order from 2 up; `ODD`/`EVEN` restrict the order accordingly. Amplitude is given either
absolutely in Vpp or relative to the fundamental in dBc.

Building a harmonic set means issuing one `HARMORDER,n,HARMDBC,x` per harmonic — the order
selector is a cursor, not a list.

## COUP / PACP / MODE / EQPHASE / CMBN — channel relationships

```
COUPling <param>,<value>
COUPling?
ParaCoPy C2,C1
MODE PHASELOCKED|INDEPENDENT
EQPHASE
<channel>:CoMBiNe ON|OFF
<channel>:INVerT ON|OFF
```

| `COUP` param | Values |
|---|---|
| `TRACE` | `ON`/`OFF` — channel tracking; CH2 mirrors CH1 entirely. Must be `OFF` before any other coupling parameter can be set. |
| `FCOUP` | `ON`/`OFF` — frequency coupling |
| `FDEV` / `FRAT` | Frequency deviation (Hz) or ratio between channels |
| `PCOUP` | `ON`/`OFF` — phase coupling |
| `PDEV` / `PRAT` | Phase deviation (degrees) or ratio |
| `ACOUP` | `ON`/`OFF` — amplitude coupling |
| `ADEV` / `ARAT` | Amplitude deviation (Vpp) or ratio |
| `TRDUCH` | `ON`/`OFF` — manual trigger fires both channels |

Coupling only works when both channels are outputting basic waveforms. Copy, coupling and
tracking are mutually exclusive with each other.

`MODE PHASELOCKED` resets both DDS engines on any frequency change so the inter-channel phase
stays fixed; `INDEPENDENT` does not, and the phase parameter disappears entirely. **The set and
query spellings differ**: you write `MODE PHASELOCKED` but `MODE?` answers `MODE PHASE-LOCKED`,
with a hyphen. `MODE INDEPENDENT` round-trips unchanged. *(verified)*

`COUP?` response *(verified)*: `COUP TRACE,OFF,FCOUP,OFF,PCOUP,OFF,ACOUP,OFF,TRDUCH,OFF`. The
`STATE` and `BSCH` parameters from the SDG1000/5000 dialect are accepted without error but
never appear in the response and have no effect — another instance of the blind spot. `EQPHASE`
realigns both channels at their current settings — a one-shot version of the same idea.

`CMBN ON` sums CH1+CH2 onto that channel's physical connector.

## SYNC — sync output

```
<channel>:SYNC ON|OFF
<channel>:SYNC ON,TYPE,CH1|CH2|MOD_CH1|MOD_CH2
<channel>:SYNC?
```

Sync comes out of the rear **Aux In/Out** BNC as CMOS, ~500 ns wide typical, up to 1 MHz.
Rules worth knowing: basic waveforms above 10 MHz produce no sync; NOISE and DC produce no sync;
under internal modulation the sync tracks the *modulating* frequency; with external modulation
there is no sync (the connector is being used as the input); in sweep and burst modes the sync
output is unavailable entirely. Inverting a waveform does not invert its sync.

## FCNT — frequency counter

```
FreqCouNTer STATE,ON|OFF
FreqCouNTer <param>,<value>
FreqCouNTer?
```

Settable: `REFQ` (reference frequency for the ppm deviation reading), `TRG` (trigger level,
−3 V to +1.5 V), `MODE` (`AC`/`DC` coupling), `HFR` (`ON`/`OFF`, high-frequency rejection).

There is also an undocumented **`TYPE`** parameter, `SLOW` or `FAST`, matching the front
panel's sampling-depth choice — settable and readable over SCPI despite not appearing in the
programming guide. *(verified)*

Read-only in the query response: `FRQ`, `PW` (positive width), `NW` (negative width), `DUTY`,
`FRQDEV` (in ppm relative to `REFQ`). Real response *(verified)*:

```
FCNT STATE,ON,FRQ,0HZ,DUTY,0,REFQ,1e+07HZ,TRG,0V,PW,0S,NW,0S,FRQDEV,0ppm,MODE,AC,HFR,OFF,TYPE,SLOW
```

`TRG` clamps to the documented range: `TRG,-3` holds, `TRG,5` becomes `1.5V`.

Input is the rear **Counter** BNC, 1 MΩ. Range 100 mHz–200 MHz DC-coupled, 10 Hz–200 MHz
AC-coupled; 100 mVrms minimum below 100 MHz, 200 mVrms above. Turn `HFR` on below 250 kHz for
noisy low-frequency signals, off above it — the 200 MHz ceiling needs it off.

## ROSC — clock source

```
ROSCillator INT|EXT
ROSCillator 10MOUT,ON|OFF
ROSC?
```

External reference in on the rear **10MHz In/Out** BNC: 10 MHz, ≥1.4 Vpp, 5 kΩ AC-coupled.
The same port outputs the internal 10 MHz reference (2–3.3 Vpp into HiZ, 50 Ω source) when
`10MOUT,ON`. Selecting `EXT` with no valid signal present pops a warning on screen but the
setting still reads back as external — so verify with a scope, not just the query.

**`ROSC INT` and `ROSC EXT` work. `ROSC 10MOUT,<state>` does not** — it returns
`-108,"Parameter not allowed"` *and still changes the setting*, always to `OFF`, in both the
`ROSC 10MOUT,ON` and `ROSC INT,10MOUT,ON` forms. So the one command that looks like it enables
the 10 MHz output actually disables it and reports an error. `ROSC?` does report the state
correctly (`ROSC INT,10MOUT,ON`), and `*RST` restores it to `ON`. Set it from
`Utility > Clock` on the front panel, and never send `10MOUT` over SCPI. *(verified)*

## Protection and status

```
VOLTPRT ON|OFF        over-voltage protection   (verified)
VOLTPRT?              -> bare 'ON' or 'OFF', with no command header
```

**`CURRPRT` and `VOLTSTAT?` are documented for the SDG2000X but not implemented** — both
return `-113,"Undefined header"` on firmware 2.01.01.39R7 *(verified)*. There is therefore no
way to poll the over-voltage trip state over SCPI; the instrument only reports a trip on its
own screen. If a script drives something that could back-drive the generator, the practical
mitigation is to leave `VOLTPRT ON` and verify the output is still doing what you expect by
measuring it, not by querying protection status.

## System and interface

```
BUZZer ON|OFF                                    beeper
SCreen_SaVe OFF|1|5|15|30|60|120|300             screensaver timeout, minutes
LAnGuaGe EN|CH                                   UI language
NumBer_ForMat PNT,DOT|COMMA
NumBer_ForMat SEPT,SPACE|OFF|ON
Sys_CFG DEFAULT|LAST|USER                        power-on configuration
SYSTem:COMMunicate:LAN:IPADdress "10.11.13.203"
SYSTem:COMMunicate:LAN:SMASk "255.255.255.0"
SYSTem:COMMunicate:LAN:GATeway "10.11.13.1"
```

LAN settings take effect on the interface and are stored in non-volatile memory. IP first octet
1–223. DHCP is off by default; it is a front-panel setting (`Utility > Interface > LAN Setup`)
with no documented SCPI equivalent.

**The LAN read-back queries are broken on firmware 2.01.01.39R7.** `SYST:COMM:LAN:IPAD?` and
`SYST:COMM:LAN:SMAS?` both return the same malformed string (`"12670.0.0.78558"`), and the
value changes between runs — it is reading uninitialised memory. `SYST:COMM:LAN:GAT?` is worse:
it returns raw bytes that are not valid UTF-8, e.g.

```
b'"78558\x07\xd3.\x1c\xed*6\x04\x0c1.1.19.19"\n'
```

which raises `UnicodeDecodeError` inside PyVISA's `read()` and will crash a naive script. If
you must touch these, use `read_raw()` and treat the result as untrusted; otherwise read the
network settings off the front panel. *(verified)*

`SYST:DATE` and `SYST:TIME` **are** supported despite the programming guide's availability
table not listing the SDG2000X: `SYST:DATE?` returns e.g. `19700101` and `SYST:TIME?` `003034`,
both bare and headerless, and the set forms are accepted *(verified)*. `POWER:ON:MODE` and
`KEY` really are absent (`-113`).

Headerless queries seen so far: `*IDN?`, `*OPC?`, `*ESR?`, `*STB?`, `*TST?`, `*SRE?`, `*ESE?`,
`SYST:ERR?`, `SYST:DATE?`, `SYST:TIME?`, `SYST:COMM:LAN:*?` and `VOLTPRT?`. Everything with a
`C1:`/`C2:` prefix, plus `COUP?`, `ROSC?`, `MODE?`, `FCNT?`, `BUZZ?`, `SCSV?`, `NBFM?`,
`LAGG?`, `SCFG?` and `CASCADE?`, carries its header.

## VKEY — virtual front-panel keys

```
VirtualKEY VALUE,<name or index>,STATE,1
```

**Not usable on firmware 2.01.01.39R7.** Every form tested — by name (`KB_UTILITY`,
`KB_WAVES`, `KB_OUTPUT1`) and by index (`11`, `4`, `153`) — returns
`-108,"Parameter not allowed"` and does nothing. The table below is kept for reference in case
another firmware revision implements it, but do not build anything on `VKEY`; if you need a
function with no SCPI equivalent, it has to be done at the front panel. *(verified)*

In principle it simulates a key press: `STATE,1` presses, `STATE,0` is a no-op.

| Name | Index | Name | Index |
|---|---|---|---|
| `KB_FUNC1`…`KB_FUNC6` | 28, 23, 18, 13, 8, 3 | `KB_NUMBER_0`…`KB_NUMBER_9` | 48–57 |
| `KB_MOD` | 15 | `KB_POINT` | 46 |
| `KB_SWEEP` | 16 | `KB_NEGATIVE` | 43 |
| `KB_BURST` | 17 | `KB_LEFT` / `KB_RIGHT` | 44 / 40 |
| `KB_WAVES` | 4 | `KB_ENTER` | 58 |
| `KB_UTILITY` | 11 | `KB_K` / `KB_M` / `KB_G` | 59 / 60 / 61 |
| `KB_PARAMETER` | 5 | `KB_OUTPUT1` / `KB_OUTPUT2` | 153 / 152 |
| `KB_STORE_RECALL` | 70 | `KB_KNOB_LEFT` / `KB_KNOB_RIGHT` / `KB_KNOB_DOWN` | 177 / 175 / 176 |
| `KB_CHANNEL` | 72 | | |

`KB_HELP`, and the direct waveform keys `KB_SINE`/`KB_SQUARE`/`KB_RAMP`/`KB_PULSE`/`KB_NOISE`/
`KB_ARB`, plus `KB_UP`/`KB_DOWN`, are listed as unavailable on the SDG2000X (its front panel
reaches waveforms through `KB_WAVES` and the soft keys).

## CASCADE — multi-instrument sync

```
CASCADE STATE,ON,MODE,MASTER
CASCADE STATE,ON,MODE,SLAVE,DELAY,<0 to 25e-6>
CASCADE?
```

Wire the master's `10MHz Out` to each slave's `10MHz In` (slaves set to `ROSC EXT`) and the
master's Aux/Trig out to each slave's Aux/Trig in. `DELAY` (slave only, 0–25 µs) compensates
cable propagation so the outputs land in phase. Use matched BNC cables — a fixed offset
proportional to cable length is expected otherwise.

## Built-in arbitrary waveform index table

Addressable range is **0–198** via `C1:ARWV INDEX,<n>` — indices 0 (`Sine`) and 1 (`Noise`) do
work, despite the guide giving the range as 2–198, and anything above 198 clamps to 198.
Confirmed against the instrument at fifteen points; `STL? BUILDIN` returns the live 199-entry
list in about a second and is authoritative.

**Index 67 is `Radar`, not `NA`.** The guide's placeholder is wrong — the firmware ships the
table as `70_radar_ram.bin` and `STL? BUILDIN` answers `Radar`.

| Idx | Name | Idx | Name | Idx | Name | Idx | Name |
|---|---|---|---|---|---|---|---|
| 2 | StairUp | 52 | RoundHalf | 102 | LFPulse | 152 | Duty16 |
| 3 | StairDn | 53 | RoundsPM | 103 | Tens1 | 153 | Duty18 |
| 4 | StairUD | 54 | BlaseiWave | 104 | Tens2 | 154 | Duty20 |
| 5 | Ppulse | 55 | DampedOsc | 105 | Tens3 | 155 | Duty22 |
| 6 | Npulse | 56 | SwingOsc | 106 | Airy | 156 | Duty24 |
| 7 | Trapezia | 57 | Discharge | 107 | Besselj | 157 | Duty26 |
| 8 | Upramp | 58 | Pahcur | 108 | Bessely | 158 | Duty28 |
| 9 | Dnramp | 59 | Combin | 109 | Dirichlet | 159 | Duty30 |
| 10 | ExpFal | 60 | SCR | 110 | Erf | 160 | Duty32 |
| 11 | ExpRise | 61 | Butterworth | 111 | Erfc | 161 | Duty34 |
| 12 | LogFall | 62 | Chebyshev1 | 112 | ErfcInv | 162 | Duty36 |
| 13 | LogRise | 63 | Chebyshev2 | 113 | ErfInv | 163 | Duty38 |
| 14 | Sqrt | 64 | TV | 114 | Laguerre | 164 | Duty40 |
| 15 | Root3 | 65 | Voice | 115 | Legend | 165 | Duty42 |
| 16 | X^2 | 66 | Surge | 116 | Versiera | 166 | Duty44 |
| 17 | X^3 | 67 | **Radar** | 117 | Weibull | 167 | Duty46 |
| 18 | Sinc | 68 | Ripple | 118 | LogNormal | 168 | Duty48 |
| 19 | Gaussian | 69 | Gamma | 119 | Laplace | 169 | Duty50 |
| 20 | Dlorentz | 70 | StepResp | 120 | Maxwell | 170 | Duty52 |
| 21 | Haversine | 71 | BandLimited | 121 | Rayleigh | 171 | Duty54 |
| 22 | Lorentz | 72 | CPulse | 122 | Cauchy | 172 | Duty56 |
| 23 | Gauspuls | 73 | CWPulse | 123 | CosH | 173 | Duty58 |
| 24 | Gmonopuls | 74 | GateVibr | 124 | CosInt | 174 | Duty60 |
| 25 | Tripuls | 75 | LFMPulse | 125 | CotH | 175 | Duty62 |
| 26 | Cardiac | 76 | MCNoise | 126 | CscH | 176 | Duty64 |
| 27 | Quake | 77 | AM | 127 | SecH | 177 | Duty66 |
| 28 | Chirp | 78 | FM | 128 | SinH | 178 | Duty68 |
| 29 | Twotone | 79 | PFM | 129 | SinInt | 179 | Duty70 |
| 30 | SNR | 80 | PM | 130 | TanH | 180 | Duty72 |
| 31 | Hamming | 81 | PWM | 131 | ACosH | 181 | Duty74 |
| 32 | Hanning | 82 | EOG | 132 | ASecH | 182 | Duty76 |
| 33 | Kaiser | 83 | EEG | 133 | ASinH | 183 | Duty78 |
| 34 | Blackman | 84 | EMG | 134 | ATanH | 184 | Duty80 |
| 35 | Gausswin | 85 | Pulseilogram | 135 | ACsch | 185 | Duty82 |
| 36 | Triang | 86 | ResSpeed | 136 | ACoth | 186 | Duty84 |
| 37 | BlackmanH | 87 | ECG1 | 137 | Bartlett | 187 | Duty86 |
| 38 | Bartlett | 88 | ECG2 | 138 | BohmanWin | 188 | Duty88 |
| 39 | Tan | 89 | ECG3 | 139 | ChebWin | 189 | Duty90 |
| 40 | Cot | 90 | ECG4 | 140 | FlattopWin | 190 | Duty92 |
| 41 | Sec | 91 | ECG5 | 141 | ParzenWin | 191 | Duty94 |
| 42 | Csc | 92 | ECG6 | 142 | TaylorWin | 192 | Duty96 |
| 43 | Asin | 93 | ECG7 | 143 | TukeyWin | 193 | Duty98 |
| 44 | Acos | 94 | ECG8 | 144 | Duty01 | 194 | Duty99 |
| 45 | Atan | 95 | ECG9 | 145 | Duty02 | 195 | demo1_375 |
| 46 | Acot | 96 | ECG10 | 146 | Duty04 | 196 | demo1_16k |
| 47 | Square | 97 | ECG11 | 147 | Duty06 | 197 | demo2_3k |
| 48 | SineTra | 98 | ECG12 | 148 | Duty08 | 198 | demo2_16k |
| 49 | SineVer | 99 | ECG13 | 149 | Duty10 | | |
| 50 | AmpALT | 100 | ECG14 | 150 | Duty12 | | |
| 51 | AttALT | 101 | ECG15 | 151 | Duty14 | | |

The `Duty01`…`Duty99` family is a set of fixed-duty square waves — handy when you need a duty
cycle outside what `BSWV DUTY` can reach at a given frequency. Note that PG02-E05C's own `STL?`
example shows these as `SquareDuty01` and the demos as `demo1_375pts`; the instrument returns
the short forms `Duty01` and `demo1_375`, which are what `ARWV?` reports and `ARWV NAME`
accepts. The table above uses the short forms.

## Commands NOT supported on SDG2000X

Present in the shared SDG programming guide but unavailable here. If a script or an
AI-generated snippet uses one of these, it was written for a different SDG family:

- `CHDR` / `COMM_HEADER` — headers cannot be suppressed
- `<channel>:SWEep:*` long-form sweep tree — SDG7000A only; use `SWWV`
- `<channel>:SEQuence:*`, `<channel>:ARBMode`, `DIG:*`, `<channel>:FHOP:*` — SDG7000A only
- `IQ:*` — SDG6000X/SDG7000A only
- `:SENSe:COUNTer:*` — SDG7000A only; use `FCNT`
- `MMEMory:*` file operations — SDG7000A only
- `<channel>:FILTer` (digital filter), `<channel>:OUTPut:SKEW` — SDG7000A only
- PRBS: `BSWV` params `LENGTH`, `EDGE`, `BITRATE`, `LOGICLEVEL`, `DIFFSTATE`, `FORMAT`, `COM_OFST`
- `SRATE INTER` interpolation selection
- `COUP STATE` and `COUP BSCH` (SDG1000/5000 style)
- `LAGG RU` (Russian)
- `WVDT` `LENGTH` on send (unnecessary on X-series — but note `LENGTH` and `TYPE` **do** come
  back in the `WVDT?` response, contrary to the guide's availability table)

Confirmed absent on firmware 2.01.01.39R7 by error-queue probe, despite the programming guide
listing them for the SDG2000X:

| Command | Result |
|---|---|
| `VOLTSTAT?` | `-113,"Undefined header"` |
| `CURRPRT` | `-113,"Undefined header"` |
| `VKEY` (all forms) | `-108,"Parameter not allowed"` |
| `ROSC 10MOUT,<state>` | `-108`, and corrupts the setting to OFF |
| `C1:SWWV STARTTIME` / `ENDTIME` / `BACKTIME` | silently ignored |
| `C1:SRATE INTER` | silently ignored |
| `COUP STATE` / `COUP BSCH` | silently ignored |

And confirmed *present* despite the guide saying otherwise: `SYST:ERR?` and the whole IEEE
488.2 status model, `SYST:DATE`/`SYST:TIME`, `FCNT TYPE`, `LAGG RU`, `C1:ARWV INDEX,0` and
`INDEX,1`.
