---
name: siglent-sdg2000x
description: Complete operating and remote-control reference for the Siglent SDG2000X series arbitrary waveform generators (SDG2042X / SDG2082X / SDG2122X) — SCPI programming over USBTMC, LAN (VXI-11 / raw socket / Telnet) and GPIB, arbitrary waveform upload, front-panel operation, specifications, performance verification and troubleshooting. Use this skill whenever the user mentions an SDG2000X, SDG2042X, SDG2082X, SDG2122X, a "Siglent function generator", "Siglent AWG", "waveform generator", or asks to drive a signal generator over USB/USBTMC/PyVISA/VISA, send SCPI to a Siglent instrument, upload or generate an arbitrary waveform, set up sweep/burst/modulation on a bench generator, or verify/calibrate one — even if they don't name the model explicitly. Also use it when writing bench-automation scripts that need a stimulus source.
---

# Siglent SDG2000X — operation and remote control

The SDG2000X is a dual-channel 1.2 GSa/s, 16-bit arbitrary waveform generator sold in
40 MHz (SDG2042X), 80 MHz (SDG2082X) and 120 MHz (SDG2122X) variants. Everything on the
front panel is also reachable over SCPI, so most tasks come down to: pick the interface,
open a session, send `C1:...` / `C2:...` commands, and read back to confirm.

This file is the map. Load the reference file you actually need — they are detailed and
there is no benefit to pulling all of them into context at once.

| Need | Read |
|---|---|
| Connecting: USBTMC, VISA, pyvisa-py, raw socket, Telnet, LabVIEW/MATLAB/C, shell | `references/remote-setup.md` |
| Any specific SCPI command, its parameters, ranges, query response | `references/scpi-reference.md` |
| Building, uploading, or reading back arbitrary waveforms; `.bin`/`.csv`/`.dat` formats; DDS vs TrueArb | `references/arbitrary-waveforms.md` |
| Doing it from the front panel: menus, buttons, Utility tree, Store/Recall | `references/front-panel-operation.md` |
| Numbers: specs, limits, default values, performance verification, self-test, troubleshooting, teardown | `references/specifications.md` |
| Commands that exist but aren't in Siglent's guide — the error queue, diagnostics, aliases, `MMEMory`, firmware package format | `references/undocumented.md` |

`scripts/sdg2000x.py` is a small, dependency-light driver plus CLI. Prefer adapting it over
writing a new VISA wrapper from scratch — it already encodes the parsing and sequencing
quirks described below.

## The model you need in your head

Two independent channels, `C1` and `C2`. Each channel is in exactly one **mode** at a time:
basic wave, modulation, sweep, or burst. Turning on sweep turns off modulation and burst.
The carrier of a modulated/swept/burst signal is set either by `C1:BSWV` beforehand or by the
`CARR,...` sub-parameters of the mode command.

Output amplitude is **computed, not measured**. The generator's source impedance is a fixed
50 Ω; the `LOAD` setting only tells it what you have hung on the end so it can back-calculate.
Set `LOAD` wrong and every voltage you set is wrong — by a factor of 2 between `HZ` and `50`.
This is the single most common source of "the scope reads half what I asked for".

## Verified against hardware

Everything below was checked against an **SDG2122X, firmware 2.01.01.39R7**, over USBTMC.
Where the manuals and the instrument disagree, this skill follows the instrument and says so.
Behaviour marked *(firmware-specific)* is worth re-checking on a different firmware revision.

## The five things that bite people

Read these before writing any automation against this instrument.

**1. There is no `CHDR` on the SDG2000X.** Other SDG families let you suppress the response
header; this one rejects the command outright (`-113,"Undefined header"`). Every
instrument-specific query comes back prefixed:

```
C1:BSWV WVTP,SINE,FRQ,1000HZ,PERI,0.001S,AMP,4V,AMPVRMS,1.414Vrms,AMPDBM,0dBm,MAX_OUTPUT_AMP,20V,OFST,0V,HLEV,2V,LLEV,-2V,PHSE,0,DLY,0S
```

So parsing is always: strip everything through the first space, then split the remainder on
commas into alternating key/value pairs, then strip the unit suffix (`HZ`, `S`, `V`, `Vrms`,
`dBm`, `dBc`, `ppm`, `Sa/s`, `%`) off each value. `scripts/sdg2000x.py` does this in
`query_dict()`. The exception: SCPI-style queries (`SYST:...`, `*IDN?`, `*OPC?`) and
`VOLTPRT?` return a **bare value with no header**, so don't assume a prefix unconditionally.

**2. `*IDN?` uses the short form.** The instrument answers
`Siglent Technologies,SDG2122X,<serial>,2.01.01.39R7` — four fields, no `*IDN,` prefix,
no hardware-version field. Code written against an SDG1000 or SDG5000 will be off by one.

**3. `STATE,ON` must come first for MDWV / SWWV / BTWV.** Modulation, sweep and burst
parameters cannot be set — or even read — until that mode is enabled. Querying a disabled mode
returns just `C1:MDWV STATE,OFF` and nothing else, and a parameter written while the mode is
off is discarded silently. The order is always `C1:MDWV STATE,ON` → `C1:MDWV AM,DEPTH,80`.
The three modes are mutually exclusive: enabling sweep turns modulation off.

**4. There IS an error queue, but it has a large blind spot.** `SYST:ERR?` works and returns
standard SCPI (`0,"No error"` when clean). So does `*ESR?` (self-clearing on read), `*CLS`,
`*STB?`, `*TST?`, `*SRE?` and `*ESE?`. Use them — they are the fastest way to test whether a
command exists.

What the queue catches:

| Code | Cause |
|---|---|
| `-113,"Undefined header"` | Unknown command, and any bad channel prefix (`C3:`, `C0:`) |
| `-108,"Parameter not allowed"` | A parameter the command doesn't accept |
| `-101,"Invalid character"` | Malformed argument |
| `-200,"Execution error"` | Header recognised but not executable on this model |

What it **misses entirely** — every one of these answers `0,"No error"` and does nothing:

- **Unknown parameter names.** `C1:BSWV NOSUCHPARAM,5`
- **Unrecognised enum values.** `C1:BSWV WVTP,BANANA` → `WVTP` stays `SINE`
- **No parameter at all.** `C1:BSWV`
- **Non-numeric where a number belongs.** `C1:BSWV FRQ,abc`
- **Bad unit suffix.** `C1:BSWV FRQ,1000QQ`
- **Exponent overflow.** `C1:BSWV FRQ,1E999`
- **Negative where positive.** `C1:BSWV FRQ,-5000`
- **String where an enum belongs.** `C1:OUTP LOAD,"abc"`
- **Excess parameters.** `C1:INVT ON,ON,ON,ON`
- **Clamping.** `C1:BSWV FRQ,200000000` on a 120 MHz unit → `120000000HZ`. Same for
  30 Vpp → 20 V, 20 Vpp above 20 MHz → 10 V, 0.1 mVpp → 0.002 V, harmonic order 17 → 16,
  burst count 2000000 → 1000000, TrueArb 100 MSa/s → 75 MSa/s.

The instrument's numeric and parameter validation simply isn't wired to the error path. Error
checking here catches a misspelled command and essentially nothing else.

So `SYST:ERR?` proves a command *exists*; only a read-back proves it *did anything*. That is
what `set_and_verify()` in the driver script is for, and it is not optional on this instrument.

**5. Nothing gets dropped, but `BSWV` writes are expensive.** USBTMC writes are
flow-controlled — 100 unpaced `C1:BSWV FRQ,n` writes all landed, in order, with an empty error
queue. The problem is cost, not reliability. Measured on this unit:

| Operation | Time |
|---|---|
| `C1:BSWV <anything>` write | **~45 ms**, even writing the value it already holds |
| `C1:OUTP LOAD,50` write | ~1.2 ms |
| `*OPC` write | ~0.1 ms |
| `C1:BSWV?` query round trip | ~4.3 ms |
| `C1:OUTP ON` (to `*OPC?`) | ~74 ms |

The ~45 ms is the instrument re-evaluating the whole basic-wave parameter set, so it is charged
per *command*, not per parameter changed. The practical consequence is worth internalising:

```
C1:BSWV WVTP,SINE
C1:BSWV FRQ,1000        <- four commands, ~194 ms
C1:BSWV AMP,2
C1:BSWV OFST,0

C1:BSWV WVTP,SINE,FRQ,1000,AMP,2,OFST,0    <- one command, ~60 ms
```

**Batch every parameter you can into one `BSWV`** — measured 3.2x faster. Sprinkling
`sleep()` between writes is not just unnecessary, it is actively wasteful.

**6. One command takes the interface down: `C1:WVDT:BLOCK` with a non-block argument.** After
it, writes still succeed and **every read times out**. No software recovery exists — not
`dev.clear()`, not reopening the session. Only unplugging the USB cable. The instrument keeps
enumerating and the front panel looks fine, so it presents as a dead interface on a healthy
instrument. Never put it in a probe list.

The cause is a discarded return value: the handler calls `SCPI_ParamArbitraryBlock`, ignores
whether it succeeded, and copies from a NULL pointer with an uninitialised length, killing the
task that answers reads. Sent *correctly* the command is harmless and works, but it is just
`C1:WVDT`'s parameter list wrapped in an IEEE 488.2 block and buys you nothing, so use the
plain form.

Ordinary read timeouts are *harmless* — `Clear_fcnt?`, `DEL_STORE_FILE?`, `ReadFLASH?` and
`PAraCoPy?` have no query form, time out, and leave everything working. But a timeout does
desynchronise the session, so a probe loop that continues through one will report every later
header as present. Probe with the **write form plus a bogus parameter** and stop on the first
timeout.

Note the 45 ms in #5 is *not* display redraw — `SCPI_UPDATE_UI OFF` changed it from 45.1 ms to
45.2 ms. Turning it off is not a performance fix.

## Quickest path to a working connection

USB is the default answer: plug a USB-B cable into the **rear** USB Device port (the front
USB Host port is for flash drives and the optional GPIB adapter), and the instrument enumerates
as a USBTMC device with no configuration on the instrument at all — there is no menu to enable it.

```python
import pyvisa
rm = pyvisa.ResourceManager()          # add '@py' for pyvisa-py, no NI-VISA needed
print(rm.list_resources())
sdg = rm.open_resource('USB0::0xF4EC::0x1102::<serial>::0::INSTR')
sdg.write_termination = '\n'
sdg.read_termination = '\n'
print(sdg.query('*IDN?'))
```

That resource string is a real one, and it is a warning in itself: the VID/PID observed on an
SDG2122X is `0xF4EC:0x1102` — not the `0xF4ED:0xEE3A` that Siglent's own MATLAB example prints,
and `0x1102` is the same PID their SDG7000A examples show, so the PID is not model-specific.
Note also the trailing `::0` interface index, which some units include and some don't.
**Enumerate and match `*IDN?` on `SDG2`; never hard-code the VID, PID or serial.** `references/remote-setup.md` covers Linux `/dev/usbtmc0`, udev rules,
pyvisa-py without NI-VISA, LAN setup, raw sockets on port 5025, Telnet on 5024, GPIB, LabVIEW,
MATLAB and C, and how to diagnose a connection that won't open.

## Recipes

These cover the great majority of what people ask for. Full parameter lists are in
`references/scpi-reference.md`.

**A basic output.** Set the load first, then the waveform, then enable the output last so the
DUT never sees an intermediate state:

```
C1:OUTP LOAD,50
C1:BSWV WVTP,SINE,FRQ,1000000,AMP,2,OFST,0,PHSE,0
C1:OUTP ON
```

Note the whole waveform goes in one `BSWV` — a `BSWV` write costs ~45 ms whatever it changes,
so four separate writes cost ~194 ms where this one costs ~60 ms. `AMP` is Vpp. Use `AMPVRMS` for Vrms or `AMPDBM` for dBm — dBm requires a non-HiZ load, since
power is undefined into infinity. `HLEV`/`LLEV` are an alternative to `AMP`/`OFST`; setting one
pair updates the other.

**A pulse with defined edges.** `WIDTH` and `DUTY` are two views of the same thing; `RISE` and
`FALL` are 10–90% and 90–10% respectively and are independently settable:

```
C1:BSWV WVTP,PULSE,FRQ,100000,AMP,3.3,OFST,1.65,WIDTH,2e-6,RISE,10e-9,FALL,10e-9
```

**AM at 50% depth, 1 kHz tone on a 10 MHz carrier:**

```
C1:MDWV STATE,ON
C1:MDWV CARR,WVTP,SINE,CARR,FRQ,10000000,CARR,AMP,1
C1:MDWV AM,SRC,INT,AM,MDSP,SINE,AM,FRQ,1000,AM,DEPTH,50
C1:OUTP ON
```

Swap `AM` for `FM` (with `DEVI` as the deviation in Hz), `PM` (`DEVI` in degrees),
`PWM` (`DEVI` as duty deviation, pulse carrier only), or the keying types `ASK`/`FSK`/`PSK`.
`SRC` can be `INT`, `EXT` (rear Aux In, 12 Vpp nominal for 100% modulation), or — a genuinely
useful trick — `CH1`/`CH2` to modulate one channel with the other with no cable.

**A 100 Hz → 100 kHz log sweep, one sweep per manual trigger:**

```
C1:SWWV STATE,ON
C1:SWWV START,100,STOP,100000,TIME,0.05,SWMD,LOG,DIR,UP,TRSR,MAN
C1:OUTP ON
C1:SWWV MTRIG          <- fires one sweep; repeat as needed
```

`TRSR,INT` free-runs; `TRSR,EXT` takes a CMOS edge on the rear Aux In/Out, with `EDGE,RISE|FALL`.
`TRMD,ON` emits a trigger pulse on Aux In/Out at the start of each sweep (internal/manual only).

**A 5-cycle burst on every external rising edge:**

```
C1:BTWV STATE,ON
C1:BTWV GATE_NCYC,NCYC,TIME,5,STPS,0,TRSR,EXT,EDGE,RISE
C1:BTWV CARR,WVTP,SINE,CARR,FRQ,10000
C1:OUTP ON
```

`TIME,INF` gives infinite burst (gate the carrier on and leave it). `GATE_NCYC,GATE` with
`PLRT,POS|NEG` gates on level instead of edge. With `TRSR,INT`, `PRD` sets the repetition period.

**Pick a built-in arbitrary waveform** (index 0–198, names in `references/scpi-reference.md`;
the index table there was confirmed against the instrument at fifteen points. An index above
198 clamps to 198):

```
C1:BSWV WVTP,ARB
C1:ARWV INDEX,26        <- Cardiac
```

For anything involving your own waveform data, read `references/arbitrary-waveforms.md` — the
wire format is raw little-endian signed 16-bit codewords appended to a `C1:WVDT ... WAVEDATA,`
command, which needs `write_raw` and a large `chunk_size`, and there are real traps in it.

**Two channels in a fixed relationship.** For a quadrature pair, put the instrument in
phase-locked mode and phase-couple the channels:

```
MODE PHASELOCKED
COUP FCOUP,ON,FRAT,1
COUP PCOUP,ON,PDEV,90
```

`COUP TRACE,ON` instead makes CH2 a slave clone of CH1. `PACP C2,C1` is a one-shot copy of all
parameters. Note phase is only meaningful in `PHASELOCKED` mode — in `INDEPENDENT` the phase
relationship drifts and the parameter disappears. Watch the spelling asymmetry: you *set*
`MODE PHASELOCKED` but `MODE?` answers `MODE PHASE-LOCKED`, with a hyphen, so a naive
round-trip comparison fails.

**Measure something.** The rear Counter BNC is a real 200 MHz frequency counter:

```
FCNT STATE,ON
FCNT MODE,AC,HFR,OFF,TRG,0
FCNT?                    <- returns FRQ, DUTY, PW, NW, FRQDEV, ...
```

Turn `HFR` (high-frequency rejection) **on** below 250 kHz and **off** above it; the 200 MHz
ceiling requires HFR off.

## Grabbing the screen

Two undocumented commands, both verified. `SCDP` returns the screen over the interface with no
file involved, which is usually what you want:

```python
dev.chunk_size = 4 * 1024 * 1024
dev.write("SCDP")               # a query whose name has no '?'; SCDP? gives -113
bmp = dev.read_raw()            # 391,734 bytes: 480x272, 24-bit, uncompressed BMP
open("screen.bmp", "wb").write(bmp[:391734])
```

`SCREEN_SHOT` is the file-writing counterpart: it writes `Local/screen.png` (or `.bmp`, per
`SCREEN_SHOT_TYPE`) on the instrument, **no USB drive needed**. The name is fixed, so each
capture overwrites the last, and you then need `MMEMory` to see it.

## Managing files on the instrument

The Programming Manual marks the whole `MMEMory` subsystem SDG7000A-only. It is wrong: on the
SDG2000X `MMEMory` works, with the documented syntax and quoted paths, and it is the right tool
for storage. It gives you the only directory listing with sizes and free space, the only way to
make and remove directories, and a delete that removes exactly the file you name.

```
MMEMory:CATalog? "Local"          -> free,used,"name,type,size","name,type,size",...
MMEMory:MDIRectory "Local/tmp"
MMEMory:COPY "Local/a.bin","Local/tmp/a.bin"
MMEMory:MOVE "Local/tmp/a.bin","Local/tmp/b.bin"
MMEMory:DELete "Local/tmp/b.bin"
MMEMory:RDIRectory "Local/tmp"
```

Four things to know. `MMEMory:CATalog?` **returns nothing without its path argument** and
leaves `-200` in the queue, which is what makes the subsystem look unimplemented. In its listing
a file is `"name,type,size"` but a **subdirectory is a bare quoted name** with no type or size,
and a path that does not exist answers `0,0` with a clean queue, so parse on the field count and
treat an empty listing as the only signal of a bad path. `COPY` and
`MOVE` **do the work and then report `-108,"Parameter not allowed"`** — the error is spurious,
so do not treat a non-empty queue as failure there. And a user waveform is a *pair*,
`<name>.bin` plus `<name>.info`; the undocumented `DEL_STORE_FILE` removes only the `.bin` and
orphans the `.info` invisibly, so prefer `MMEMory:DELete` and remove both members. There is no
undo — back a library up with `WVDT? USER,<name>` first. Full table in
`references/undocumented.md`.

A file whose name contains a literal `"` (legal on the instrument's filesystem, so it happens
with files copied from a USB drive) **cannot be deleted, moved or renamed remotely at all**: the
firmware strips every `"` from the path first, so the operation hits the wrong name — and
`MMEMory:DELete` of a quoted name will delete the un-quoted namesake if one exists. There is no
SCPI escape for it; use the front panel. See `references/undocumented.md`.

## When you are asked to write a test script

Structure it the way a careful bench engineer would:

1. Open the session, `*IDN?`, and assert the model actually is an SDG2000X — the SCPI dialect
   differs meaningfully across SDG families, and a script silently doing nothing on an SDG1000X
   is worse than one that refuses to run.
2. `*RST` to a known state if the user won't mind losing their setup — ask if unsure, since it
   wipes their front-panel work.
3. Set `LOAD` before amplitude, always.
4. Configure with the output **off**, enable the output last, and disable it in a `finally`
   block so a crashed script doesn't leave a live signal on someone's prototype.
5. Read back and verify anything the test depends on, and check `SYST:ERR?` after each phase
   — remembering that a clean queue does not mean a parameter took (see #4).

`scripts/sdg2000x.py` implements this shape; `python scripts/sdg2000x.py --help` shows the CLI
for quick one-off sends from a shell.

## Safety and hardware limits worth respecting

The outputs are protected but not invincible. Over-voltage protection (`VOLTPRT ON`) trips and
kills the output at roughly ±11 V of externally applied voltage when the channel is set above
3.2 Vpp or ±2 V offset, and at roughly ±4 V below those settings — so back-driving a channel
from a power supply or another generator is a real risk. Note that `VOLTSTAT?` and `CURRPRT`,
which the programming guide lists for this model, are **not implemented** — both return
`-113,"Undefined header"` — so there is no way to poll the trip state over SCPI. (`BOARD_TEST?`
does work and returns `DAC,pass,FPGA,pass`; see `references/undocumented.md`.) Only
`VOLTPRT ON|OFF` works, and `VOLTPRT?` answers with a bare `ON`/`OFF`.
Output current is limited to ±200 mA. The BNC shells are tied to chassis ground: this
instrument cannot float, and connecting its ground to a non-ground node will short that node
to earth. Full electrical and environmental limits are in `references/specifications.md`.
