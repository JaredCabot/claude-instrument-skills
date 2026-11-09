---
name: siglent-sdg2000x
description: Complete operating and remote-control reference for the Siglent SDG2000X series arbitrary waveform generators (SDG2042X / SDG2082X / SDG2122X) — SCPI programming over USBTMC, LAN (VXI-11 / raw socket / Telnet) and GPIB, arbitrary waveform upload, front-panel operation, specifications, performance verification and troubleshooting. Use this skill whenever the user mentions an SDG2000X, SDG2042X, SDG2082X, SDG2122X, a "Siglent function generator", "Siglent AWG", "waveform generator", or asks to drive a signal generator over USB/USBTMC/PyVISA/VISA, send SCPI to a Siglent instrument, upload or generate an arbitrary waveform, set up sweep/burst/modulation on a bench generator, or verify/calibrate one — even if they don't name the model explicitly. Also use it when writing bench-automation scripts that need a stimulus source.
---

# Siglent SDG2000X — operation and remote control

The SDG2000X is a dual-channel 1.2 GSa/s, 16-bit arbitrary waveform generator sold in
40 MHz (SDG2042X), 80 MHz (SDG2082X) and 120 MHz (SDG2122X) variants. Everything on the
front panel is also reachable over SCPI, so most tasks come down to: pick the interface,
open a session, send `C1:...` / `C2:...` commands, and read back to confirm.

This file has the essentials first, then appendices:

| Need | Appendix |
|---|---|
| Connecting: USBTMC, VISA, pyvisa-py, raw socket, Telnet, LabVIEW/MATLAB/C, shell | A |
| Any specific SCPI command, its parameters, ranges, query response | B |
| Building, uploading, or reading back arbitrary waveforms; `.bin`/`.csv`/`.dat` formats; DDS vs TrueArb | C |
| Doing it from the front panel: menus, buttons, Utility tree, Store/Recall | D |
| Numbers: specs, limits, default values, performance verification, self-test, troubleshooting, teardown | E |
| Commands that exist but aren't in Siglent's guide: the error queue, diagnostics, aliases, `MMEMory`, firmware package format | F |
| A small, dependency-light Python driver plus CLI (save as `sdg2000x.py`) | G |

Prefer adapting the Appendix G driver over writing a new VISA wrapper from scratch: it already
encodes the parsing and sequencing quirks described below.

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
`dBm`, `dBc`, `ppm`, `Sa/s`, `%`) off each value. the Appendix G driver does this in
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
**Enumerate and match `*IDN?` on `SDG2`; never hard-code the VID, PID or serial.** Appendix A covers Linux `/dev/usbtmc0`, udev rules,
pyvisa-py without NI-VISA, LAN setup, raw sockets on port 5025, Telnet on 5024, GPIB, LabVIEW,
MATLAB and C, and how to diagnose a connection that won't open.

## Recipes

These cover the great majority of what people ask for. Full parameter lists are in
Appendix B.

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

**Pick a built-in arbitrary waveform** (index 0–198, names in Appendix B;
the index table there was confirmed against the instrument at fifteen points. An index above
198 clamps to 198):

```
C1:BSWV WVTP,ARB
C1:ARWV INDEX,26        <- Cardiac
```

For anything involving your own waveform data, read Appendix C — the
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
Appendix F.

A file whose name contains a literal `"` (legal on the instrument's filesystem, so it happens
with files copied from a USB drive) **cannot be deleted, moved or renamed remotely at all**: the
firmware strips every `"` from the path first, so the operation hits the wrong name — and
`MMEMory:DELete` of a quoted name will delete the un-quoted namesake if one exists. There is no
SCPI escape for it; use the front panel. See Appendix F.

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

the Appendix G driver implements this shape; `python sdg2000x.py --help` shows the CLI
for quick one-off sends from a shell.

## Safety and hardware limits worth respecting

The outputs are protected but not invincible. Over-voltage protection (`VOLTPRT ON`) trips and
kills the output at roughly ±11 V of externally applied voltage when the channel is set above
3.2 Vpp or ±2 V offset, and at roughly ±4 V below those settings — so back-driving a channel
from a power supply or another generator is a real risk. Note that `VOLTSTAT?` and `CURRPRT`,
which the programming guide lists for this model, are **not implemented** — both return
`-113,"Undefined header"` — so there is no way to poll the trip state over SCPI. (`BOARD_TEST?`
does work and returns `DAC,pass,FPGA,pass`; see Appendix F.) Only
`VOLTPRT ON|OFF` works, and `VOLTPRT?` answers with a bare `ON`/`OFF`.
Output current is limited to ±200 mA. The BNC shells are tied to chassis ground: this
instrument cannot float, and connecting its ground to a non-ground node will short that node
to earth. Full electrical and environmental limits are in Appendix E.

## Appendix A: Connecting (USB, LAN, GPIB, other languages)

Four transports, in rough order of how often they are the right answer: USB (USBTMC), LAN
(VXI-11), LAN (raw socket), LAN (Telnet). GPIB exists via an optional adapter. Everything
below carries the same SCPI payload — only the plumbing differs.

### USB / USBTMC

Use the **rear-panel USB Device** port (type B). The front USB Host port is for flash drives
and the optional USB-GPIB adapter and will not work for control.

There is nothing to configure on the instrument — no menu, no mode switch. Plug it in and it
enumerates as a USB Test & Measurement Class device.

On the host you need one of:

- **NI-VISA** (Windows/macOS/Linux). The Run-Time Engine is sufficient; the full package adds
  NI-MAX, whose VISA Test Panel is genuinely the fastest way to sanity-check an instrument
  before writing any code.
- **Keysight IO Libraries** — also fine, also provides a `visa32/visa64` DLL.
- **pyvisa-py** — pure Python, no vendor install. See below.
- **The Linux kernel `usbtmc` driver** — no VISA at all. See below.

### Finding the resource string

Never hard-code it. Serial numbers differ per unit and the USB PID has varied across firmware
and production runs. Enumerate and match:

```python
import pyvisa
rm = pyvisa.ResourceManager()
candidates = [r for r in rm.list_resources() if 'USB' in r and '0xF4E' in r.upper()]
```

or, more robustly, open each candidate and check `*IDN?` for `SDG2`.

An actual SDG2122X on Windows with NI-VISA enumerates as:

```
USB0::0xF4EC::0x1102::<serial>::0::INSTR
```

Three things to take from that. The vendor ID is `0xF4EC`, not the `0xF4ED` in Siglent's own
MATLAB example. The product ID is `0x1102` — the same PID that example uses for an SDG7000A,
so **the PID does not identify the model**. And there is a trailing `::0` interface index that
some units and VISA versions include and others don't. Any of the three will break a
hard-coded string, which is why matching `*IDN?` against `SDG2` is the only reliable approach.

### Linux without VISA

The mainline kernel ships a `usbtmc` driver. Plug the instrument in and you get a character
device:

```bash
ls -l /dev/usbtmc*          # /dev/usbtmc0
dmesg | tail                # confirms the class driver bound
lsusb | grep -i siglent     # gives you the real VID:PID for this unit
```

Then it is just a file:

```bash
printf '*IDN?\n' > /dev/usbtmc0 && head -c 200 /dev/usbtmc0
```

```python
with open('/dev/usbtmc0', 'r+b', buffering=0) as f:
    f.write(b'*IDN?\n')
    print(f.read(300).decode().strip())
```

By default only root can open it. Add a udev rule so your user group can — substitute the real
VID/PID from `lsusb`:

```
# /etc/udev/rules.d/99-siglent.rules
SUBSYSTEM=="usb", ATTRS{idVendor}=="f4ec", MODE="0666", GROUP="plugdev"
SUBSYSTEMS=="usb", ACTION=="add", KERNEL=="usbtmc[0-9]*", MODE="0666", GROUP="plugdev"
```

then `sudo udevadm control --reload-rules && sudo udevadm trigger` and re-plug.

Reads block until the instrument has something to say, so never read after a command that isn't
a query — you will hang until timeout.

### pyvisa-py: VISA-compatible, no NI install

```bash
pip install pyvisa pyvisa-py pyusb
```

```python
rm = pyvisa.ResourceManager('@py')
```

On Linux, pyvisa-py's USB backend goes through libusb and needs the kernel `usbtmc` driver
*not* to be holding the device — the udev rule above plus pyusb's automatic detach normally
handles it, but if you get "Resource busy", `sudo modprobe -r usbtmc` is the blunt fix (you
then lose `/dev/usbtmc0`, so pick one approach and stick with it). On Windows, pyvisa-py's USB
support requires a libusb-compatible driver bound to the device (Zadig), which is usually more
trouble than just installing NI-VISA. LAN via pyvisa-py works everywhere with no drivers at all
and is the easy escape hatch when USB fights you.

### LAN

Configure on the instrument: `Utility > Page 1/3 > Interface > LAN State > On`, then
`LAN Setup` for IP / subnet / gateway / DHCP. **DHCP is off by default** — out of the box the
instrument has a static address. Settings persist in non-volatile memory. The prompt bar on
screen shows link status.

Once it has an address, three ways in:

**VXI-11** (what VISA uses; behaves identically to USB from your code's point of view):

```python
sdg = rm.open_resource('TCPIP0::192.168.1.50::INSTR')
```

**Raw socket, port 5025** — no VISA, no libraries, works from anything with a TCP stack. Every
command must end with `\n`:

```python
import socket
s = socket.create_connection(('192.168.1.50', 5025), timeout=5)
s.sendall(b'*IDN?\n')
print(s.recv(4096).decode().strip())
s.close()
```

As a VISA resource string the same thing is `TCPIP0::192.168.1.50::5025::SOCKET`, which needs
`read_termination = '\n'` set explicitly since SOCKET sessions have no message framing.

**Telnet, port 5024** — an interactive `SCPI>` prompt for poking at the instrument by hand.
`telnet 192.168.1.50 5024`, type commands, `Ctrl+]` then `quit` to leave. Useful for a quick
manual check; useless for automation.

Instruments with hardware version `06-xx-xx-xx-xx` also serve a web control page over HTTP with
a virtual front panel, password-protected via `Utility > Interface > Web Password`, plus VNC on
a configurable port 5900–5999.

You can also set the network parameters over an existing connection:

```
SYST:COMM:LAN:IPAD "192.168.1.50"
SYST:COMM:LAN:SMAS "255.255.255.0"
SYST:COMM:LAN:GAT  "192.168.1.1"
```

Changing the IP over LAN will of course drop your session.

### GPIB

Requires the optional Siglent USB-GPIB adapter: its USB end goes into the instrument's **front**
USB Host port, its GPIB end into the controller's card. Address defaults to 18, settable 1–30
under `Utility > Interface > GPIB`, stored non-volatile and shown at power-on. Resource string
`GPIB0::18::INSTR`. There is no native GPIB connector on this instrument.

### Session hygiene that actually matters

```python
sdg = rm.open_resource(resource)
sdg.timeout = 5000              # ms; raise to 50000+ before uploading large waveforms
sdg.write_termination = '\n'
sdg.read_termination = '\n'
sdg.chunk_size = 20 * 1024 * 1024   # only needed for arb transfers
```

- `\n` termination on writes is required. Missing it is the classic "the instrument ignores
  everything I send".
- Default timeouts are too short for `WVDT` uploads of megabyte waveforms. 50 s is not
  unreasonable for a 16 MB transfer over USB.
- Close the session, or use a context manager. A leaked USBTMC session can leave the device
  unable to accept a new connection until it is re-plugged.
- Send `*OPC?` to synchronise after a batch of settings rather than sprinkling `sleep()` calls.
- Turn off `Utility > System > SCPI UPUI` if you are pushing settings fast — redrawing the
  front-panel display for every command costs real time.

### Other languages

**MATLAB** (Instrument Control Toolbox; the modern `visadev` supersedes the legacy `visa`
shown in Siglent's manual):

```matlab
v = visadev("USB0::0xF4ED::0xEE3A::sdg2000x::INSTR");
configureTerminator(v, "LF");
writeline(v, "*IDN?");
disp(readline(v));
writeline(v, "C1:BSWV WVTP,SINE,FRQ,1000,AMP,2");
writeline(v, "C1:OUTP ON");
clear v
```

**LabVIEW**: VISA Open → VISA Write → VISA Read → VISA Close, with the resource picked from a
VISA Resource Name control. One thing catches people out over TCP/IP: LabVIEW's VISA Write/Read
default to *asynchronous* I/O, which misbehaves here — right-click the node and choose
`Synchronous I/O Mode > Synchronous`. USBTMC is fine with the default.

**C / C++ with NI-VISA**: link `visa32.lib`, include `visa.h`, then the standard sequence
`viOpenDefaultRM` → `viOpen` → `viPrintf(vi, "*IDN?\n")` → `viScanf(vi, "%t", buf)` → `viClose`.
`viFindRsrc(rm, "USB?*INSTR", ...)` enumerates USB instruments so you can avoid hard-coding.
Set `VI_ATTR_TMO_VALUE` generously before any waveform transfer.

### Shell one-liners

Over LAN with netcat — no dependencies at all:

```bash
printf '*IDN?\n' | nc -q1 192.168.1.50 5025
printf 'C1:BSWV WVTP,SINE,FRQ,1000,AMP,2\nC1:OUTP ON\n' | nc -q1 192.168.1.50 5025
```

Over USB on Linux:

```bash
printf 'C1:OUTP ON\n' > /dev/usbtmc0
```

Or use the bundled driver's CLI, which works over both transports:

```bash
python sdg2000x.py --send 'C1:BSWV WVTP,SINE,FRQ,1e6,AMP,2'
python sdg2000x.py --query 'C1:BSWV?'
python sdg2000x.py --resource TCPIP0::192.168.1.50::INSTR --query '*IDN?'
```

### Troubleshooting a connection

**Nothing enumerates over USB.** Confirm you are on the *rear* port. Check `lsusb` /
Device Manager for the device at all — if the OS doesn't see it, it is a cable or port problem,
not a driver problem. Siglent's USB-B ports are known to be fussy about marginal cables.

**Enumerates but VISA won't open it.** Another process is holding the session (NI-MAX, a
previous crashed script, EasyWaveX). Close them, or re-plug. On Linux, the kernel `usbtmc`
driver and pyvisa-py/libusb fight over the same device — pick one.

**Opens but every query times out.** Almost always missing `\n` termination, or reading after a
command that isn't a query. Verify with `*IDN?` first, which is the least ambiguous test.

**Works, but responses are garbled or off by one field.** You are parsing an SDG1000/5000-style
response. This model returns `*IDN?` in the short format and cannot suppress command headers on
other queries. See the parsing notes in the main section.

**LAN pings but VISA won't connect.** Check `LAN State` is `On` in the Interface menu; it is a
separate switch from having an IP address. Confirm host and instrument are on the same subnet.
Try raw socket port 5025 before blaming VISA — if the socket works, the problem is the VXI-11
layer or a firewall.

**Commands are accepted but nothing changes.** Query `SYST:ERR?` first — the error queue does
exist on this instrument and `-113,"Undefined header;<your command>"` immediately tells you the
command isn't implemented on this model. If the queue is clean, the causes in order of
likelihood are: the parameter needs its mode enabled first (`STATE,ON` for
`MDWV`/`SWWV`/`BTWV`); the parameter name or enum value is not one this model recognises, which
the error queue does **not** report; or the value was silently clamped. Read the value back —
that is the only test that distinguishes them. See Appendix B for the full account.

**Everything works but the script is slow.** Each `BSWV` write costs about 45 ms on this
instrument regardless of what it changes, while a query round trip is about 4 ms. Combine
parameters into a single `BSWV` command rather than issuing one per parameter, and drop any
`sleep()` calls between writes — USBTMC writes are flow-controlled, so nothing is lost by
sending them back to back.

**A LAN query raises `UnicodeDecodeError`.** `SYST:COMM:LAN:GAT?` returns bytes that are not
valid UTF-8 on firmware 2.01.01.39R7, and the IP and subnet queries return malformed strings.
This is a firmware bug, not your code. Read the network settings from the front panel.

## Appendix B: SCPI command reference

Distilled from Siglent *SDG Series Programming Guide* PG02-E05C, filtered to the commands the
availability tables mark as supported on **SDG2000X**, then **corrected against a real
SDG2122X running firmware 2.01.01.39R7**. Entries marked *(verified)* were exercised on that
instrument; entries marked *(guide says supported — actually rejected)* are documentation
errors in PG02-E05C that will waste your time otherwise. Commands belonging to other SDG families
(sequences, digital channels, frequency hop, IQ, `MMEMory:`, `SENSe:COUNTer:`, PRBS, digital
filter, output skew) are omitted — they will not work here.

### Syntax and conventions

- `<channel>` is `C1` or `C2`. Most signal commands are channel-prefixed; system commands are not.
- Keywords have a long and a short form; the short form is the capitalised part of the long form
  (`BaSic_WaVe` → `BSWV`). Both are accepted. Case is not significant.
- Parameters follow the command as comma-separated `KEY,VALUE` pairs. Multiple pairs go in one
  command: `C1:BSWV WVTP,SINE,FRQ,1000,AMP,2`.
- Terminate every command with `\n`. Queries end with `?`.
- Numbers accept plain decimal (`1000000`), scientific (`1E6`, `100e-9`) and, for some
  parameters, unit suffixes. Plain SI-base numbers are the safest: Hz, seconds, volts.
- Query responses **always** carry the command header — there is no `CHDR` on this model.

### Common (IEEE 488.2) commands

| Command | Effect |
|---|---|
| `*IDN?` | Returns `Siglent Technologies,<model>,<serial>,<firmware>`. Note this is the *short* response format — no `*IDN,` prefix, no hardware-version field, unlike SDG800/1000/5000. |
| `*OPC` / `*OPC?` | Sets/queries the OPC bit. `*OPC?` always returns `1`, but only once every prior command has been fully processed — which makes it a cheap and effective synchronisation handshake. |
| `*RST` | Full device reset to factory defaults. Takes ~2–3 s; wait before querying. Wipes the user's front-panel setup, so ask before using it in a script. Note the reset load is **HiZ**, not the 50 Ω the user manual's default table implies. |
| `*CLS` | Clears the status registers and the error queue. *(verified)* |
| `*ESR?` | Standard Event Status Register. Returns 32 after a command error; **self-clears on read**. *(verified)* |
| `*STB?`, `*TST?`, `*SRE?`, `*ESE?` | All present and answer. `*TST?` returns 0. *(verified)* |
| `SYST:ERR?` | **The error queue — it exists**, contrary to what the absence of any mention in the programming guide suggests. FIFO, standard SCPI format, `0,"No error"` when clean. *(verified)* |

#### Using the error queue

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

### OUTPUT — output port, load, polarity

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

### BSWV — basic waveform

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

### MDWV — modulation

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

### SWWV — sweep

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

### BTWV — burst

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

### ARWV / STL / WVDT — arbitrary waveforms

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
layouts, see Appendix C.

### SRATE — DDS vs TrueArb

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

### HARM — harmonic generation

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

### COUP / PACP / MODE / EQPHASE / CMBN — channel relationships

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

### SYNC — sync output

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

### FCNT — frequency counter

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

### ROSC — clock source

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

### Protection and status

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

### System and interface

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

### VKEY — virtual front-panel keys

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

### CASCADE — multi-instrument sync

```
CASCADE STATE,ON,MODE,MASTER
CASCADE STATE,ON,MODE,SLAVE,DELAY,<0 to 25e-6>
CASCADE?
```

Wire the master's `10MHz Out` to each slave's `10MHz In` (slaves set to `ROSC EXT`) and the
master's Aux/Trig out to each slave's Aux/Trig in. `DELAY` (slave only, 0–25 µs) compensates
cable propagation so the outputs land in phase. Use matched BNC cables — a fixed offset
proportional to cable length is expected otherwise.

### Built-in arbitrary waveform index table

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

### Commands NOT supported on SDG2000X

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

## Appendix C: Arbitrary waveforms

Three distinct things get called "arbitrary waveform" here and confusing them wastes hours:

1. **Built-in waveforms** — 197 shapes baked into the instrument, selected by index
   (`C1:ARWV INDEX,26`). Nothing is transferred.
2. **User waveforms stored on the instrument** — uploaded once by name, then recalled by name
   (`C1:ARWV NAME,mywave`). This is what `WVDT` writes.
3. **Waveform files on a USB stick or made in EasyWaveX** — `.bin`, `.csv`, `.dat` loaded
   through the front-panel file manager.

### Playback modes: DDS vs TrueArb

This choice matters more than most people expect.

**DDS** takes the stored waveform and resamples it to produce whatever output frequency you
ask for, up to 20 MHz for arbs, using a 300 MSa/s effective rate. The waveform is stretched or
compressed to exactly one period per cycle. Fine for smooth analogue shapes; it will smear fast
transitions and re-time edges, because it is interpolating between your points.

**TrueArb** plays your points one-for-one at a sample rate you choose, 1 µSa/s to 75 MSa/s.
Every point comes out exactly once per cycle, with ~150 ps rms jitter. This is what you want for
digital patterns, precise edge placement, and anything where the sample-to-sample detail *is*
the signal.

```
C1:SRATE MODE,TARB
C1:SRATE VALUE,10000000     <- 10 MSa/s; period = length / rate
C1:SRATE?
```

In TrueArb, output period = (number of points) ÷ (sample rate). You control frequency by
choosing the point count and rate together, not by setting `FRQ`.

Waveform length: 8 points to 8 Mpts. Vertical resolution 16 bits.

### Uploading waveform data over SCPI

The command is:

```
<channel>:WVDT WVNM,<name>,FREQ,<Hz>,AMPL,<Vpp>,OFST,<V>,PHASE,<deg>,WAVEDATA,<raw bytes>
```

followed by a recall to actually select it:

```
<channel>:ARWV NAME,<name>
```

**The payload is raw little-endian signed 16-bit codewords**, range −32768…+32767, appended
directly after `WAVEDATA,` with no length prefix, no terminator inside the block, and no ASCII
encoding. Full negative scale is −32768, full positive is +32767. Length 4 bytes to 16 MB
(2 to 8 Mpts). The `LENGTH` parameter that older SDG families require is unnecessary on the
X-series and can be omitted.

Because the payload is binary, you cannot use a normal string `write()` — it will mangle bytes
and may inject a terminator. Use `write_raw` with a bytes object:

```python
import struct, pyvisa, math

n = 8192
samples = [int(32767 * math.sin(2 * math.pi * i / n)) for i in range(n)]
payload = struct.pack('<%dh' % n, *samples)     # little-endian int16

header = b'C1:WVDT WVNM,mysine,FREQ,1000,AMPL,4,OFST,0,PHASE,0,WAVEDATA,'
sdg.timeout = 60000
sdg.chunk_size = 20 * 1024 * 1024
sdg.write_raw(header + payload + b'\n')
sdg.write('C1:ARWV NAME,mysine')
sdg.write('C1:BSWV WVTP,ARB')
```

With numpy:

```python
import numpy as np
samples = (32767 * np.sin(np.linspace(0, 2*np.pi, n, endpoint=False))).astype('<i2')
payload = samples.tobytes()
```

The driver in Appendix G wraps all of this in `upload_arb()`, including scaling a
float array in −1…+1 to codewords and clipping instead of wrapping — worth reusing, because a
value that overflows int16 wraps from +full-scale to −full-scale and produces a waveform with
violent spikes that looks like a hardware fault.

**Verified on an SDG2122X (firmware 2.01.01.39R7):** a 4096-point sine uploaded in about
0.5 s, left the error queue clean, appeared immediately in `STL? USER`, and read back
byte-identical.

#### Things that go wrong here

- **`write()` instead of `write_raw()`.** Corrupts the payload. Symptom: the instrument accepts
  it and plays noise.
- **Default timeout.** A multi-megabyte transfer over USBTMC takes many seconds; the default
  2–5 s timeout aborts mid-transfer and leaves a truncated waveform stored.
- **Small `chunk_size`.** PyVISA's default chunking can stall large transfers. 20 MB is a safe
  setting for the duration of the upload.
- **Forgetting the recall.** `WVDT` stores; `ARWV NAME,...` selects. Uploading alone changes
  nothing audible or visible, which reads as "the upload failed".
- **Feeding the queried name back in.** After `C1:ARWV NAME,mysine`, the query answers
  `C1:ARWV NAME,mysine.bin` — with the extension appended. Sending that back as
  `C1:ARWV NAME,mysine.bin` is rejected with `-101,"Invalid character"`. Recall by the bare
  name and strip any `.bin` you read.
- **Byte order.** Big-endian data plays as a completely different, symmetric-looking garbage
  waveform. If your uploaded sine looks like a strange sawtooth, check endianness first.
- **Amplitude scaling.** `AMPL` in the `WVDT` command sets the amplitude the waveform is stored
  with; the channel's `BSWV AMP` still scales the output. Full-scale codewords map to the set
  amplitude, so if your data only reaches ±16000 you are throwing away 6 dB of the DAC's range
  and its noise floor. Normalise to full scale and set the amplitude with `BSWV AMP`.

### Reading a waveform back

```
WVDT? USER,<name>
```

returns a header plus the same raw binary after `WAVEDATA,`. The real header *(verified)* —
note the spaces after commas, and that it carries `LENGTH` and `TYPE` even though the
programming guide marks `TYPE` unavailable on this model:

```
WVDT POS, /Local, WVNM, skilltest, LENGTH, 8192B, TYPE, 6, WAVEDATA,<8192 raw bytes>\n
```

**A single `read_raw()` is not enough.** It returns only the first fragment — 104 bytes of an
8192-byte payload in testing — so the read has to loop until the expected length arrives:

```python
dev.timeout = 60000
dev.chunk_size = 20 * 1024 * 1024
dev.write("WVDT? USER,mysine")
time.sleep(0.5)
buf, deadline = b"", time.time() + 10
while time.time() < deadline:
    try:
        buf += dev.read_raw()
    except Exception:
        break
    if len(buf) >= expected_bytes + 60:      # payload plus header
        break
payload = buf[buf.find(b"WAVEDATA,") + 9:]
```

With that loop the returned payload is byte-for-byte identical to what was uploaded (plus a
single trailing `\n`). the Appendix G driver implements this as `download_arb()`.

One more firmware wrinkle: **`WVDT? USER,<name>` queues a spurious
`-108,"Parameter not allowed"` even when it succeeds and returns correct data.** It is the only
command in normal use that does this. Drain the error queue after a readback, or a later
`SYST:ERR?` check will report a failure that never happened. *(verified)*
`WVDT? M<n>` fetches a built-in waveform (M0–M196, 32 KB each) in the same shape. Always
`read_raw()`, never `read()` — the binary will contain bytes that are not valid UTF-8.

`STL?`, `STL? BUILDIN` and `STL? USER` list what is stored. Empty user slots read `EMPTY`.

### File formats

For getting waveforms onto the instrument via a USB stick or EasyWaveX rather than SCPI.
Filenames should stick to English letters, digits and underscores — other characters render
unreliably in the file manager.

**`.bin`** — the native format, and exactly the same bytes as the `WAVEDATA` payload: raw
little-endian signed 16-bit codewords, −32768…32767, no header. 4 B to 16 MB on this model.
Loading a `.bin` keeps the instrument's current amplitude/frequency/offset and simply maps
codewords to voltage. Not human-editable, but trivially generated.

**`.csv`** — text, and the friendliest format for hand-built or spreadsheet-derived waveforms.
Header lines followed by a start-of-data marker followed by one sample per line:

```
amp, 4
offset, 0
frequency, 1000
data length, 4096
Second, Volt
0.0, 0.0
2.44140625e-07, 0.00153
...
```

The four header items (`amp`, `offset`, `frequency`, `data length`) must all be present; extra
items are ignored. Any of `Second, Volt` / `Xpos, value` / `Time, Ampl` / `Second, Value` works
as the data start marker. The instrument converts CSV to `.bin` internally on load.

**`.dat`** — identical to `.csv` with the header stripped: data rows only.

`.mat`, `.awg`, `.wav`, `.arb` and `.hop` are other-family formats and are **not** supported on
the SDG2000X.

**`.xml`** is not a waveform at all — it is a full instrument state file, written by
`Store/Recall` and used by `Sys_CFG USER` for a custom power-on state.

### EasyWaveX

Siglent's free PC editor. Connects over USB or LAN, offers twelve standard shapes, freehand and
line drawing, point/coordinate entry with connect and smooth options, and equation entry, then
sends the result to a chosen channel. It also exports CSV, which is often the most convenient
path: draw in EasyWaveX or generate in Python, save CSV, load from a USB stick.

For anything scriptable, generating the array yourself and using `WVDT` is faster and
reproducible; EasyWaveX earns its place for one-off shapes you want to draw by eye.

### A worked example: two synchronised digital patterns

A common real task — a clock on CH1 and a data pattern on CH2, locked together:

1. Generate both patterns as arrays of the same length, at the same sample rate.
2. Upload each with `WVDT` and recall with `ARWV NAME,...`.
3. Put both channels in TrueArb at the same rate: `C1:SRATE MODE,TARB,VALUE,<rate>` and the
   same for `C2`.
4. Lock them: `MODE PHASELOCKED`, then `COUP FCOUP,ON,FRAT,1`.
5. `EQPHASE` to align, then enable both outputs with `OUT_BOTHCH ON`.

Use TrueArb, not DDS — DDS interpolation will round the edges of a digital pattern and destroy
the timing relationship you are trying to create.

## Appendix D: Front-panel operation

For when someone is standing at the instrument, or when a remote task has no SCPI equivalent
and has to be done through `VKEY` or by hand.

### Panels

**Front:** power button, USB Host port (flash drives, USB-GPIB adapter), 4.3" 24-bit resistive
touchscreen, numeric keypad, rotary knob, left/right arrow keys, waveform-selection buttons,
mode/auxiliary function keys, six menu softkeys down the right edge mapping 1:1 to on-screen
labels, a channel-switch key, and per-channel `Output` buttons with BNC outputs.

**Rear:** `Counter` BNC (frequency-meter input, 1 MΩ), `Aux In/Out` BNC (external trigger in,
trigger out, sync out, external modulation in), `10MHz In/Out` BNC (reference clock),
chassis ground terminal, IEC C13 mains inlet, `USB Device` port (USBTMC — this is the one for
PC control), `LAN` port.

The BNC shells are tied to chassis/safety ground. The instrument cannot float.

### Key behaviours worth knowing

- **Knob**: rotate to change the selected digit; press to select a parameter box; use ◀ ▶ to
  choose which digit the knob acts on. **Long-press the knob (~2 s) takes a screenshot**, saved
  to the USB stick if one is inserted, otherwise to local storage. Format is set under
  `Utility > System > Page 1/3 > Page 2/3 > Capt Type` (PNG or BMP).
- **Output button**: press to toggle the output; **hold for ~2 s to toggle that channel's load
  between 50 Ω and HiZ**. This is the fastest fix for "the amplitude is half what I set".
- **Numeric entry**: type the digits, then press the unit softkey (`MHz`, `Vpp`, `°`, …). The
  entry isn't committed until a unit is chosen.
- **Mod / Sweep / Burst**: each button toggles the function and jumps to its parameters; the
  button backlights while active. They are mutually exclusive.
- **Channel status bar**: tap it to switch channels; tap again for a shortcut menu (Mod, Sweep,
  Burst, Parameter, Utility, Store/Recall).

### Setting up a basic output

`Waveforms` → pick the shape → set `Load` (under `Utility > Output Setup`, or the Output-button
hold shortcut) → `Frequency` → `Amplitude` → `Offset` → `Phase` → press `Output`.

Setting the load first is not fussiness: amplitude is computed from the assumed load, so
changing it afterwards changes every voltage you have already entered.

Amplitude accepts Vpp, Vrms, and dBm — dBm only appears when the load is not HiZ.
`Amplitude`/`Offset` and `HighLevel`/`LowLevel` are two views of the same pair.

Per-waveform extras: `Symmetry` for Ramp (% of the period rising), `DutyCycle` for Square,
`Width`/`DutyCycle` plus independent `Rise`/`Fall` for Pulse, `Stdev`/`Mean`/`Bandwidth` for
Noise (bandwidth needs its own enable switch), `Offset` only for DC.

DC has a resolution setting: **high resolution** drops the output momentarily to 0 V when
crossing a gear boundary (every ±2 V at HiZ, ±1 V at 50 Ω); **low resolution** switches gears
without the glitch but with coarser accuracy inside a gear. If a DC step is glitching a DUT,
this is why.

### Harmonic mode

A sub-function of the Sine carrier. `Type` = Odd / Even / Custom, `Order` up to 16, amplitude in
Vpp or dBc relative to the fundamental, plus per-harmonic phase. The screen shows both a
time-domain preview and a bar chart of the harmonic amplitudes. Mixing odd and even harmonics
requires `Custom`.

### Arbitrary waveforms

`Waveforms > Page 1/2 > Arb`. Choose `DDS` (1 µHz–20 MHz, frequency-driven) or `TrueArb`
(sample-rate driven, 1 µSa/s–75 MSa/s, point-for-point). Data source is either a built-in
waveform — organised into categories: commonly used, mathematical, engineering, window
functions, trigonometric, square waves, medical, modulation, filters, demonstrations — or a
stored waveform, which opens the file manager for you to pick and `Recall`.

### Modulation

`Mod` button. Types: AM, DSB-AM, FM, PM, PWM, ASK, FSK, PSK.

Source is `Internal`, `External` (rear Aux In), or `Channel` (the other channel — no cable
needed). With an external source, 12 Vpp nominal corresponds to 100 % modulation and the
modulation frequency and shape controls disappear from the UI, since the external signal
determines them entirely.

PWM requires a Pulse carrier. The other types accept Sine, Square, Ramp and Arb carriers but not
Pulse, Noise or DC.

A thing that surprises people: at high AM depth the peak-to-peak output exceeds the set
amplitude. That is correct behaviour — carrier *power* is held constant across depth, not peak
voltage.

### Sweep

`Sweep` button. Linear, Log, or Step. Direction Up, Down, or Up-and-down (linear only, with a
settable symmetry so the up and down halves can differ). Trigger source Internal (free-running),
External (CMOS edge on Aux In, rising or falling), or Manual (on-screen button).

Start/Stop and Center/Span are two views of the same range. `Trig Out` emits a pulse at the
start of each sweep (internal and manual triggering only). With external or manual triggering
the frequency returns to the idle frequency — selectable as start, end, or start point — and
holds there between sweeps. Log sweep is frequency-only.

### Burst

`Burst` button. `NCycle` emits a set number of carrier cycles per trigger (or `Infinite` for a
continuous carrier after one trigger); `Gated` follows a gate signal with selectable polarity.

Internal triggering uses `Burst Period` as the repetition rate. Manual triggering adds a
`Burst Counter` — the number of bursts emitted per button press. `Trig Delay` has a
hardware-limited minimum. `Trig Out` can align to the rising or falling edge.

### Channel copy, coupling and tracking

`Utility > CH Copy Coupling`. Three mutually exclusive features:

- **Channel Copy** — one-shot copy of all parameters, CH1⇒CH2 or CH2⇒CH1.
- **Channel Coupling** — frequency, amplitude and/or phase coupled by a deviation or a ratio,
  so changing one channel drags the other. Both channels must be on basic waveforms.
- **Track** — CH2 becomes a live mirror of CH1; the UI locks to CH1 and you cannot switch.

`Trigger CH` (single or dual) makes a manual trigger fire both channels at once. Only valid in
burst manual-trigger mode, and mutually exclusive with Track.

### Output setup

`Utility > Output Setup`: `Load` (HighZ, or 50 Ω–100 kΩ), `Polarity` (Normal/Invert — note the
sync output is *not* inverted with the waveform), `EqPhase` (realign both channels at their
current settings), `Wave Combine` (output CH1, or CH1+CH2 summed, on each connector),
`Amplitude` (a maximum-output ceiling applied to both channels immediately), and `Power-on State`
(requires PowerOn Setting to be Last or Custom).

### Utility tree

| Function | Path | Notes |
|---|---|---|
| Number Format | `System > Number Format` | Decimal point and thousands separator |
| Language | `System > Language` | Simplified Chinese / English |
| PowerOn Setting | `System > PowerOn Setting` | Last / Default / Custom (needs a saved state file) |
| Set To Default | `System > Set To Default` | Factory reset — same as `*RST` |
| Beeper | `System > Beeper` | |
| Screen Saver | `System > Page 1/3 > ScrnSvr` | 1, 5, 15, 30 min, 1, 2, 5 hr, or Close |
| System Info | `System > Page 1/3 > System Info` | Firmware and hardware versions |
| Firmware Update | `System > Page 1/3 > Firmware Update` | Loads an ADS file from USB |
| UI Style | `System > Page 1/3 > UI Style` | Classical / Normal |
| SCPI UPUI | `System > Page 1/3 > Page 2/3` | Whether SCPI commands redraw the screen — **turn off for fast scripted control** |
| Capture Type | `System > Page 1/3 > Page 2/3 > Capt Type` | PNG / BMP for knob-long-press screenshots |
| Test/Cal | `Utility > Test/Cal` | Self tests and touch calibration |
| Counter | `Utility > Counter` | Frequency meter |
| Interface | `Utility > Page 1/3 > Interface` | GPIB address, LAN state and setup, VNC port, web password |
| Sync | `Utility > Page 1/3 > Sync` | Sync output state and source channel |
| Clock | `Utility > Page 1/3 > Clock` | Internal/External 10 MHz, and phase mode |
| OverVoltage Protection | `Utility > Page 1/3` | |
| Multi-Device Sync | `Utility > Page 1/3 > Page 2/3` | Master/slave with delay compensation |

### Phase mode

Under `Utility > Page 1/3 > Clock`:

- **Phase Locked** — both DDS engines reset on any frequency change, so the CH1–CH2 phase
  difference stays fixed. Phase is settable only in this mode.
- **Independent Channel** — no reset; the phase relationship drifts randomly and the phase
  parameter is hidden entirely.
- **Frequency Compensation** — corrects the frequency control word so integer-multiple channel
  frequencies don't drift apart from rounding error.

### Counter

`Utility > Counter`. Displays Frequency/Period, positive and negative pulse width, and duty.
`RefFreq` sets the reference for the ppm deviation reading. `TrigLev` defaults to 0 V, range
−3 V to +1.5 V. Under `Setup`: `HFR` (high-frequency rejection, default off), `Mode` (AC/DC
coupling), `Type` (Slow = more samples/more accurate, Fast = fewer/quicker).

Rule of thumb: HFR **on** below 250 kHz, **off** above — and the full 200 MHz range needs it off.

### Store / Recall

Two locations: `Local (C:)` internal non-volatile memory, and `USB Device (0:)` which appears
and disappears as you insert and remove a stick.

| Extension | Content |
|---|---|
| `.xml` | Complete instrument state — all functional and system settings |
| `.bin` | Binary arbitrary waveform data, loaded directly |
| `.csv` | Text arbitrary waveform data, converted to `.bin` on load |
| `.dat` | Text arbitrary waveform data (CSV without the header), converted on load |

Operations: Save, Browse, Recall, Rename, New Folder, Copy, Paste, Delete. Stick to English
letters, digits and underscores in filenames — anything else may render incorrectly.

### Self test and touch calibration

`Utility > Test/Cal > SelfTest`:

- **ScrTest** — full-screen red/green/blue for dead pixels and scratches. `7` cycles colours,
  `8` exits.
- **KeyTest** — rotate each knob and press each button, watching the on-screen counter and
  highlights. Exit with `8` pressed three times.
- **LEDTest** — `7` steps through each button LED, `8` exits.
- **BoardTest** — internal chip self-check; everything should read `Pass`. A failure means a
  hardware fault needing service.

`TouchCal` recalibrates the touchscreen by tapping four corner targets in sequence.

### Multi-device synchronisation

Master `10MHz Out` → each slave's `10MHz In`, with slaves set to external clock. Master's
`Trig/Sync` → each slave's `Trig/Sync`, splitting where needed. Set the same output frequency
everywhere, enable outputs, trigger sync from the master. Expect a fixed phase offset from
cable propagation delay — use matched cables and the "compensate for slave delay" setting
(`CASCADE ... DELAY,<0–25 µs>` over SCPI) to null it.

## Appendix E: Specifications, verification and service

Numbers below are from the SDG2000X Service Manual (SM0202X-E01C) and User Manual (EN03A).
Where the service manual states values "according to the SDG2122X", the bandwidth-dependent
entries scale down for the 80 MHz and 40 MHz models.

### Models

| Model | Analog bandwidth | Channels |
|---|---|---|
| SDG2042X | 40 MHz | 2 |
| SDG2082X | 80 MHz | 2 |
| SDG2122X | 120 MHz | 2 |

Common to all: 1.2 GSa/s, 16-bit vertical resolution, 20 Vpp maximum output, 80 dB dynamic
range, TrueArb (8 pts–8 Mpts, 1 µSa/s–75 MSa/s), EasyPulse, ~197 built-in arbitrary waveforms,
4.3" resistive touchscreen. Power-on default is Sine, 1 kHz, 4 Vpp, CH1, outputs off.

### Frequency reference

| Parameter | Value |
|---|---|
| Resolution | 1 µHz |
| Initial accuracy | ±1 ppm at 25 °C; ±2 ppm over 0–40 °C |
| Aging | ±1 ppm first year; ±3.5 ppm over 10 years (25 °C) |

### Sine

| Parameter | Value |
|---|---|
| Frequency | 1 µHz – 120 MHz |
| Harmonic distortion (0 dBm) | −65 dBc to 10 MHz; −60 dBc to 20 MHz; −55 dBc to 40 MHz; −50 dBc to 60 MHz; −45 dBc to 80 MHz; −40 dBc to 100 MHz; −38 dBc to 120 MHz |
| THD | 0.075 % (0 dBm, 10 Hz–20 kHz) |
| Non-harmonic spurious | −70 dBc ≤50 MHz; −65 dBc >50 MHz |

### Square

| Parameter | Value |
|---|---|
| Frequency | 1 µHz – 25 MHz |
| Rise/fall time | ≤9 ns (10–90 %, 1 Vpp, 50 Ω) |
| Overshoot | ≤3 % (100 kHz, 1 Vpp, 50 Ω) |
| Duty cycle | 0.001 – 99.999 %, constrained by frequency |
| Jitter (rms, cycle-cycle) | ≤150 ps |

### Pulse

| Parameter | Value |
|---|---|
| Frequency | 1 µHz – 25 MHz |
| Minimum pulse width | 16.3 ns |
| Pulse width accuracy | ±(0.01 % + 0.3 ns) |
| Rise/fall time | 8.4 ns – 22.4 ns (10–90 %, 1 Vpp, 50 Ω), further constrained by width |
| Overshoot | ≤3 % |
| Duty cycle | 0.001 – 99.999 %, resolution 0.001 % |
| Jitter (rms) | ≤150 ps |

### Ramp

Frequency 1 µHz – 1 MHz; symmetry 0–100 %; linearity ≤1 % of peak-to-peak (1 kHz, 1 Vpp,
100 % symmetry).

### Noise

−3 dB bandwidth ≥120 MHz. Gaussian, set by standard deviation and mean, with an optional
bandwidth limit.

### Arbitrary

| Parameter | Value |
|---|---|
| Frequency (DDS) | 1 µHz – 20 MHz |
| Waveform length | 8 pts – 8 Mpts |
| Sample rate | 1 µSa/s – 75 MSa/s (TrueArb); 300 MSa/s effective (DDS) |
| Vertical resolution | 16 bit |
| Jitter (rms, TrueArb) | ≤150 ps (1 Vpp, 50 Ω) |

### DC

Range ±10 V into HiZ, ±5 V into 50 Ω. Accuracy ±(1 % + 2 mV) into HiZ.

### Output

| Parameter | Value |
|---|---|
| Amplitude range | 2 mVpp – 20 Vpp ≤20 MHz (HiZ); 2 mVpp – 10 Vpp >20 MHz (HiZ). Halve for 50 Ω. |
| Amplitude accuracy | ±(1 % + 1 mVpp) at 10 kHz sine, 0 V offset |
| Flatness (50 Ω, 2.5 Vpp, ref 10 kHz) | ±0.3 dB to 100 MHz; ±0.4 dB 100–120 MHz |
| Output impedance | 50 Ω typical (49.5–50.5 Ω at 10 kHz) — **fixed**; the `LOAD` setting is a compensation figure only |
| Output current | ±200 mA |
| Channel crosstalk | ≤−60 dBc |

### Modulation

| Type | Key limits |
|---|---|
| AM | Depth 0–120 %; modulating frequency 1 mHz – 1 MHz internal; carriers Sine/Square/Ramp/Arb |
| FM | Deviation 0 – 0.5 × bandwidth, limited by carrier frequency; modulating 1 mHz – 1 MHz |
| PM | Deviation 0–360°; modulating 1 mHz – 1 MHz |
| PWM | Pulse carrier only; modulating 1 mHz – 1 MHz; width-deviation resolution 6.67 ns |
| ASK / FSK / PSK | Modulating wave is a 50 % square; keying rate 1 mHz – 1 MHz internal |

### Burst and sweep

| Parameter | Value |
|---|---|
| Burst carriers | Sine, Square, Ramp, Pulse, Noise, Arb |
| Burst type | Count 1 – 1,000,000, Infinite, Gated |
| Burst carrier frequency | 2 mHz – bandwidth |
| Burst internal period | 1 µs – 1000 s |
| Burst trigger delay | up to 100 s |
| Sweep carriers | Sine, Square, Ramp, Arb |
| Sweep type | Linear, Log (Step also available via `SWMD,STEP`) |
| Sweep time | 1 ms – 500 s |

### Frequency counter

| Parameter | Value |
|---|---|
| Functions | Frequency, period, +/− pulse width, duty cycle |
| Coupling | AC, DC, HFREJ |
| Range | 100 mHz – 200 MHz (DC coupled); 10 Hz – 200 MHz (AC coupled) |
| Input amplitude | 100 mVrms min below 100 MHz; 200 mVrms min 100–200 MHz. Max ±2.5 V (DC) / 5 Vpp (AC) |
| Input impedance | 1 MΩ |

### Auxiliary and clock connectors

| Port | Specification |
|---|---|
| 10 MHz reference in | 10 MHz typical, ≥1.4 Vpp, 5 kΩ AC-coupled |
| 10 MHz reference out | 10 MHz, 2–3.3 Vpp into HiZ, 50 Ω source |
| Trigger in | VIH 2–5.5 V, VIL −0.5–0.8 V, 100 kΩ, min pulse width 100 ns, response ≤100 ns (sweep) / ≤600 ns (burst) |
| Trigger out | VOH ≥3.8 V at −8 mA, VOL ≤0.44 V at 8 mA, ~100 Ω, max 1 MHz |
| Sync out | Same levels as trigger out, ~500 ns typical width, max 1 MHz |
| Modulation in | 0–50 kHz, 10 kΩ, 11–13 Vpp (12 typical) for 100 % modulation |

### General

| Parameter | Value |
|---|---|
| Line voltage | 100–240 Vrms ±10 %, 50/60 Hz; or 100–120 Vrms ±10 %, 400 Hz. Auto-sensing. |
| Power consumption | 25.5 W typical, 50 W max |
| Fuse | F2.0AL, 250 V, 5 × 20 mm |
| Operating temperature | 0 – 40 °C |
| Storage temperature | −20 – 60 °C |
| Operating humidity | 5–90 % RH ≤30 °C; 5–50 % RH at 40 °C |
| Operating altitude | ≤3048 m at ≤30 °C |
| Warm-up | 30 minutes continuous within 18–28 °C before specifications apply |
| Calibration interval | 1 year |
| Dimensions (W×H×D) | 260.3 × 107.2 × 295.7 mm |
| Net weight | 3.43 kg |
| Ventilation | 15 cm clearance both sides |
| Ratings | Installation category II (mains) / I (measuring), pollution degree 2, IP20 |
| Compliance | IEC 61010-1:2010, EN 61326-1:2013 |
| Warranty | 3 years from shipment (repair parts 90 days) |

### Over-voltage protection

Enabled with `VOLTPRT ON`. The output shuts down and an alert appears when externally applied
voltage exceeds:

- **±11 V ±0.5 V** when the channel is set to ≥3.2 Vpp *or* ≥|2 V| offset
- **±4 V ±0.5 V** when set below both of those

`VOLTSTAT?` reports the current overload state. There is also `CURRPRT` for over-current.

### Default settings (`*RST` / Set To Default)

| Parameter | Default | Parameter | Default |
|---|---|---|---|
| Channel output | Off | AM depth | 100 % |
| **Load** | **HiZ** *(verified — not the 50 Ω the user manual's table implies)* | Burst trigger delay | 629 ns |
| Waveform | Sine | FM deviation | 100 Hz |
| Frequency | 1 kHz | PM deviation | 100° |
| Amplitude | 4 Vpp | FSK hop frequency | 1 MHz |
| Offset | 0 V | PSK polarity | Normal |
| Phase | 0° | PWM width deviation | 190 µs |
| Ramp symmetry | 50 % | Sweep time | 1 s |
| Modulation source | Internal | Sweep start / stop | 500 Hz / 1.5 kHz |
| Modulating wave | Sine | Sweep centre / span | 1 kHz / 1 kHz |
| Modulation frequency | 100 Hz | Sweep mode / direction | Linear / Up |
| Keying frequency | 100 Hz | Burst period | 10 ms |
| PSK rate | 100 Hz | Burst mode / cycles | NCycle / 1 |
| Trigger source (sweep, burst) | Internal | Burst start phase | 0° |
| Trigger output | Off | Burst delay | 629 ns |

CH1 and CH2 defaults are identical.

Verified against an SDG2122X: after `*RST`, `C1:OUTP?` reports
`C1:OUTP OFF,LOAD,HZ,POWERON_STATE,OFF,PLRT,NOR` and `C1:BSWV?` reports 1 kHz / 4 Vpp / 0 V
offset sine with `MAX_OUTPUT_AMP,20V`. `*RST` takes 2–3 seconds — wait before querying. It also
restores the 10 MHz reference output to ON.

### Performance verification

Perform on receipt and at each calibration interval. Warm up 30 minutes at 18–28 °C first.
The service manual documents three formal tests; other specification values are stated but not
part of the documented test suite. A failure means adjustment or repair — there is no
user-accessible calibration menu, password, or secure mode on this instrument.


#### DC output accuracy

DMM on CH1, waveform DC, load HiZ, output on. Spec is ±(1 % + 2 mV).

| Setting | Limits |
|---|---|
| 0 mV | −2 … +2 mV |
| ±10 mV | ±7.9 … ±12.1 mV |
| ±100 mV | ±97 … ±103 mV |
| ±1 V | ±0.988 … ±1.012 V |
| ±3 V | ±2.968 … ±3.032 V |
| ±10 V | ±9.898 … ±10.102 V |

#### AC amplitude accuracy

DMM on CH1, load 50 Ω, sine at 10 kHz. Spec is ±(1 % + 1 mV). Repeat for CH2.

| Setting (Vpp) | Limits (V) |
|---|---|
| 10 | 9.899 – 10.101 |
| 5.6 | 5.543 – 5.657 |
| 2 | 1.979 – 2.021 |
| 0.9 | 0.890 – 0.910 |
| 0.4 | 0.395 – 0.405 |
| 0.142 | 0.13958 – 0.14442 |
| 0.064 | 0.06236 – 0.06564 |
| 0.022 | 0.02078 – 0.02322 |
| 0.010 | 0.00890 – 0.01110 |
| 0.004 | 0.00296 – 0.00504 |

#### Frequency response (flatness)

Power meter on CH1, load 50 Ω, sine, at 10 kHz / 100 kHz / 1 / 5 / 10 / 20 / 30 / 50 / 80 /
100 / 110 / 120 MHz. Repeat for CH2.

| Amplitude | 10 kHz – 100 MHz | 110 – 120 MHz |
|---|---|---|
| 1 V | 3.6794 – 4.2794 dBm | 3.5794 – 4.3794 dBm |
| 2.5 V | 11.64 – 12.24 dBm | 11.54 – 12.34 dBm |

Automating this is straightforward: step `C1:BSWV FRQ,<f>` through the list, read the power
meter, compare. The measurement instrument, not the generator, is the awkward part.

### Self test

`Utility > Test/Cal > SelfTest` runs ScrTest (screen), KeyTest (buttons and knob), LEDTest, and
BoardTest (internal chips — all should report `Pass`). A power-on self-test also runs
automatically; if it fails the instrument may hang with a black screen, which is a service issue.

There is no SCPI command to invoke self test.

### Troubleshooting

| Symptom | Sequence |
|---|---|
| Won't start | Check the power cord → the power button → the fuse (replace with same rating) → the PSU-to-main-board connection |
| Starts, dark screen | Check PSU-to-main-board connection → keypad-board-to-main-board connection |
| Buttons dead or display abnormal | Check keypad-board-to-main-board connection |
| Output amplitude wrong | Check the connection to the load → **check that the `Load` setting matches the actual load impedance** → contact service |

That third row is the one to try first in practice — it is the explanation far more often than
a hardware fault.

**Internal test points** (qualified personnel, mains disconnected, 3 minutes for capacitor
discharge, antistatic precautions):

- Channel board power connector, 6 pins: +20 V (red), −20 V (white), +6.5 V (yellow),
  −6.5 V (blue), ±10 % when connected, ±30 % with the connector removed. In spec when connected
  = PSU good. Out of spec connected but in spec disconnected = load fault on the channel/main
  board. Out of spec disconnected = replace the PSU module. The mains fuse lives inside the PSU
  assembly; if it fails, the whole assembly is replaced.
- Channel board rails, all ±5 %: +15, −15, −5, +5, 1.8, 3.3, 2.5 A, 2.5 B, 1.5, 1.1, PLL 3.3 V.
- Channel board 10 MHz TCXO: 3.3 V LVCMOS at the marked test point.
- `FPGA_LED` should flash at 1 Hz. Off or wrong rate suggests an FPGA fault.
- Main board rails ±5 %: 16 V, 3.3 V, 5 V. `CLK_25MHz` at ±50 ppm, 3.3 V LVCMOS.
  `ARM_LED` on = firmware loaded and CPU running.
- Connectors: `CON_J1` main↔channel, `CON_J5` channel↔interface, `CON_J6` channel power,
  `CON_J7` fan; `M_CON_J3` main↔key/LCD, `M_CON_J14` main power, `M_CON_J4` main↔channel,
  `M_CON_J15` USB host.

Service tools: T10 and T15 Torx. Module removal order: handle → metal shell and rear cabinet →
front cabinet → display module → main body.

Recommended test equipment: a DMM with ≥±0.015 % DC accuracy (Siglent suggest SDM3055) and a
300 MHz oscilloscope (SDS2304X).

### Firmware update

`Utility > System > Page 1/3 > Firmware Update`, loading an ADS file from a USB stick. Neither
manual documents a procedure beyond this, and there is no SCPI equivalent.

### Safety notes worth repeating

- The on/standby button does not disconnect mains — unplug the cord to fully power down.
- Hazardous stored energy in the PSU and LCD modules; wait 3 minutes after disconnecting.
- Do not measure mains circuits with this instrument, and do not connect it to a person.
- BNC shells are at chassis ground — the instrument cannot float.
- Keep 15 cm of ventilation clearance on both sides.
- Clean the exterior only, with a damp cloth, unplugged, and dry it fully before repowering.
- If an abnormal condition persists after one restart, stop using the instrument and contact
  service rather than trusting the data.

## Appendix F: Undocumented commands and behaviour

Recovered from the firmware image `SDG2000X_P39R7.ADS` (application binary `awg.app`) and
confirmed against an SDG2122X running 2.01.01.39R7. Everything here is *in addition to*
PG02-E05C; Appendix B covers the documented set.

Provenance is marked throughout: **bench** = observed on the instrument, **firmware** =
found in the binary only, **both** = found in firmware and confirmed on the instrument.
A longer firmware write-up is published at https://github.com/JaredCabot/sdg2000x-firmware;
nothing here depends on it.

### The status model and error queue

The single most useful omission from the guide. All **bench**-confirmed:

```
SYST:ERR?     ->  0,"No error"          FIFO, standard SCPI, survives across sessions
*ESR?         ->  32 after an error     self-clears on read
*CLS          ->  clears queue and registers
*STB?  *TST?  *SRE?  *ESE?              all answer
```

Use it as a capability test — far better than waiting for a query to time out:

```python
while "No error" not in dev.query("SYST:ERR?"):
    pass                                  # drain: the queue outlives sessions
dev.write(candidate + " ZZQQ")            # bogus arg so a real command can't execute
exists = "-113" not in dev.query("SYST:ERR?")
```

Send the **write form with a bogus argument** and stop on the first timeout. A header with no
query form (`Clear_fcnt?`, `DEL_STORE_FILE?`, `ReadFLASH?`, `PAraCoPy?`) times out *harmlessly*
— writes and the error queue keep working — but the timeout desynchronises the session, so a
loop that carries on through one reports every later header as present. Two sessions here did
exactly that and had to be thrown away.

Channel-prefixed probing *does* work — `C1:NOTAREALHEADER`, `C1:PRODuct` and `C1:BAND` all
answer `-113` while `C1:BSWV` answers cleanly and `C9:BSWV` gives `-113`. One session
suggested otherwise; that session was faulty.

**Never probe `C1:WVDT:BLOCK`.** With a non-block argument it leaves the parser waiting for
block data and consuming every subsequent command: writes keep succeeding, every read times
out, and nothing short of a physical USB re-plug recovers it — not `dev.clear()`, not
reopening the session. It is the single cause of every interface lockup found here, and it was
misattributed twice (to `viClear`, then to read timeouts) before a controlled test isolated
it.

The cause is a two-line bug in `scpi_ch1_build_in_wavedata_block` (`0x004d0744`): it calls
`SCPI_ParamArbitraryBlock(ctx, &ptr, &len, FALSE)`, **discards the return value**, and then
runs `std::string::assign(ptr, len)` where `ptr` is NULL and `len` was never initialised. The
copy walks into unmapped memory and kills the task that answers reads. Writes still land
because they are accepted lower down in the USBTMC stack. `0x004d07e0` is the same code for
CH2. Sent *correctly* the command is harmless and works: see the storage table below.

Codes seen in practice: `-113` undefined header (also for bad channel prefixes `C3:`/`C0:`),
`-108` parameter not allowed, `-101` invalid character, `-200` execution error, `0` no error.
Those five are all that ever appear. The firmware carries the complete SCPI-99 message table —
58 messages, listed in the supplement PDF — but nothing in the parameter path reaches it: a
missing parameter, `FRQ,abc`, `FRQ,1000QQ`, `FRQ,1E999`, `FRQ,-5000`, `LOAD,"abc"` and
`INVT ON,ON,ON,ON` all answer `0,"No error"`.

### Identification

| Command | Response | Notes |
|---|---|---|
| `PRODuct?` | `PROD MODEL,SDG2000X,BAND,120MHZ` | **both.** `BAND` is **not** the installed bandwidth despite the name — it is the *current waveform's* maximum frequency, and follows whichever channel was set last. On a 120 MHz unit: SINE/NOISE/DC → 120MHZ, SQUARE/PULSE → 25MHZ, RAMP → 1MHZ, ARB → 20MHZ. Nothing else queries this, but don't use it to identify the model. |
| `MD5_PR?` | `SDG2000X` | **both.** Product string alone. No hash despite the name. |
| `MD5_SRLN?` | `<serial>` | **both.** Serial number alone. |
| `MCBD?` | a 16-char code | **both.** `scpi_get_bandwidth_update_string_cb` — the bandwidth authorisation string, registered among `LICENSE`, `LICENSE_KEY` and `LCISL?`. Constant, unrelated to the serial. Don't send the set form. |
| `SRTIme?` | `1787837427` | **both.** A POSIX timestamp; the observed value matched the observation date. |

`MODEL?` and `BAND?` exist as response prefixes inside `PRODuct` but are **not** registered as
top-level headers.

### System and display

| Command | Response | Notes |
|---|---|---|
| `SCPI_UPDATE_UI ON\|OFF` / `?` | `ON` | **both.** The `Utility > System > SCPI UPUI` setting, which the user manual presents as front-panel-only. Decides whether SCPI writes redraw the screen. It does **not** affect command timing: a `BSWV` write cost 45.1 ms with it ON and 45.2 ms OFF. |
| `Screen_capture_png ON\|OFF` / `?` | `Screen_capture_png ON` | **both.** PNG vs BMP for screen captures. |
| `SCREEN_SHOT_TYPE <type>` / `?` | `PNG` | **both.** Same setting as a bare enum. `PNG` and `BMP` work; `JPG`, `0`, `1`, `2` are accepted in silence and change nothing. |
| `SCREEN_SHOT` | — | **both.** Captures the screen to internal storage as `Local/screen.png` or `screen.bmp` per `SCREEN_SHOT_TYPE`. **No USB drive needed.** Fixed name, so each capture overwrites the last (7,156 B as PNG, 391,734 B as BMP). |
| `SCDP` | a 391,734-byte BMP | **both.** Returns the screen **over the interface**, no file involved: 480x272, 24-bit, uncompressed. Registered as a query under a name with no `?`, so *write* `SCDP` then read. `SCDP?` answers `-113`. Use a big chunk size. |
| `VNC_PORT <port>` / `?` | `5900` | **both.** The VNC server port (5900–5999). |
| `Freq_com_switch ON\|OFF` / `?` | `Freq_com_switch ON` | **both.** The frequency-compensation option of the phase-mode menu — effectively the third member of `MODE`, which the guide documents without it. |

### Diagnostics

| Command | Response | Notes |
|---|---|---|
| `BOARD_TEST?` | `DAC,pass,FPGA,pass` | **both.** Runs the board self-test and returns a verdict per subsystem — the *only* part of `Utility > Test/Cal > SelfTest` reachable remotely. Safe to run; exercises hardware, so not mid-measurement. |
| `led?` | `MOD,OFF,SWEEP,OFF,BURST,OFF,...` | **both.** Lit state of each front-panel lamp: MOD, SWEEP, BURST, PARAMETER, UTILITY, STORE_RECACLL (the firmware's own misspelling), WAVEFORM, OUTPUT_CH1, OUTPUT_CH2. A cheap read-back of which mode the instrument thinks it is in. |
| `IQSP` / `IQSP?` | 17 NUL bytes | **both.** `scpi_get_iq_support_string_cb` — the I/Q support string. Empty here; no I/Q hardware, and nothing else in the firmware reads it. |
| `LCISL?` | `-200` | **both.** Recognised, not executable here. |
| `k7dump ON\|OFF` / `k7dump?` | empty | **both.** The Kintex-7 FPGA register dump switch (`drv_if_main_t::set_k7fpga_dump_switch`); `k7dump?` returns the buffer. Both forms accepted cleanly, but the buffer stays empty with the switch on — the facility is gated by the `SIGL_DEBUG=ON` build flag. A bad parameter goes to a debug stream, not the error queue. |

### Storage and waveforms

| Command | Notes |
|---|---|
| `DEL_STORE_FILE <name>.bin` | **both.** **Deletes a stored user waveform.** A user waveform is a pair, `<name>.bin` plus `<name>.info`, and this removes only the `.bin`, orphaning the `.info` invisibly (`STL? USER` lists neither member by name). **Prefer `MMEMory:DELete`**, which works on this model and deletes exactly what you name. **The `.bin` extension is required**: `DEL_STORE_FILE mywave` is accepted with a clean error queue and deletes nothing; `DEL_STORE_FILE mywave.bin` works. Exactly the opposite of `ARWV NAME`, which rejects `.bin` with `-101`. |
| `Clear_fcnt` | **both.** Clears the frequency counter's statistics — the counter menu's Clear softkey. Added in firmware 2.01.01.37R8 and never documented. |
| `C1:WVDT:BLOCK` / `C2:WVDT:BLOCK` | **both.** The block-transfer form of `WVDT`. The payload is the ordinary parameter list (`WVNM` ... `WAVEDATA`) wrapped as an IEEE 488.2 definite-length block; the handler unwraps it and calls the same routine as `C1:WVDT`, so the forms are equivalent and there is no reason to prefer it. **Get the block header wrong and you lose the interface** (see above). |
| `WaVePaRameter?` / `WaVeDaTa?` | **both.** Long spellings of `WVPR?` and `WVDT?`, sharing their handlers. **Queries, not writes.** `WaVeDaTa? USER,<name>` returns the same 65,606-byte response as `WVDT?`, with the same spurious `-108`. No channel prefix: `C1:WaVePaRameter?` gives `-113`. |
| `C<n>:DcUFAmplifier ON\|OFF` / `?` | `C1:DcUFAmplifier,OFF` | **both.** The DC final amplifier switch (`cfg_bswv_main_t::set_dc_final_amplifier_switch`). Registered with a `C#:` wildcard. Default OFF. |

The firmware implements `DEL_STORE_FILE` by interpolating your name into
`rm -rf /usr/bin/siglent/usr/usr/<name>`, i.e. the parameter reaches a shell. Pass plain
alphanumeric/underscore names — which is all the instrument's file manager supports anyway —
and reject anything else if you build the name from user input or a directory listing.

### Aliases

Convenience rather than capability, all **both**-confirmed. The un-prefixed forms act on CH1.

| Alias | Equivalent to |
|---|---|
| `BaSicWaVe` / `BaSicWaVe?` | `BaSic_WaVe`, and usable with no channel prefix |
| `INVERT` / `INVERT?` | `INVerT` (response still says `C1:INVT`) |
| `ROSCILLATOR?` | `ROSCillator?` |
| `NumBerForMat?` | `NumBer_ForMat?` |
| `SCREEN_SAVE` / `?` | `SCreen_SaVe` |
| `SystemConFiG` / `?` | `Sys_CFG` |
| `PAraCoPy` | `ParaCoPy` (the guide's spelling differs from the firmware's) |

### The MMEMory subsystem

The Programming Manual marks all of `MMEMory` as SDG7000A-only. **On the SDG2000X it is fully
functional**, with the syntax given in 3.46 working unchanged, quoted paths included. Every
command below was exercised on a dummy file and verified by listing the directory before and
after.

| Command | Form | Result |
|---|---|---|
| `MMEMory:CATalog? "Local"` | query | free, used, then one quoted `name,type,size` per entry |
| `MMEMory:CATalog:DATA:ARBitrary? "Local"` | query | answers |
| `MMEMory:CATalog:STATe:XMLanguage? "Local"` | query | answers |
| `MMEMory:COPY "src","dst"` | write | copies; returns a spurious `-108` |
| `MMEMory:MOVE "src","dst"` | write | moves; returns a spurious `-108` |
| `MMEMory:DELete "path"` | write | deletes, clean |
| `MMEMory:MDIRectory "Local/dir"` | write | creates the directory, clean |
| `MMEMory:RDIRectory "Local/dir"` | write | removes it, clean |
| `MMEMory:SAVE:XML` | write | accepted; not exercised |
| `MMEMory:LOAD:XML` | write | accepted; not exercised |
| `MMEMory:TRANsfer` | write | accepted; not exercised |
| `MMEMory:CFIle` | write | accepted; not exercised |

Two details matter. **`MMEMory:CATalog?` returns nothing at all without its path parameter**,
leaving `-200,"Execution error"` in the queue — which is exactly what makes the subsystem look
unimplemented if you probe it bare. With the parameter it answers on one line: free space, used
space, then a quoted triple per entry.

```
86528000,258048,"CAN_D_DATA.bin,BIN,65536","RS232_CLK.info,INFO,152","mydir",...
```

A **file** is `"name,type,size"`; a **subdirectory** is a bare quoted name with no type and no
size, which is easy to drop if you parse on a fixed field count. A path that **does not exist**
answers `0,0` with an empty error queue, and `MDIRectory` / `RDIRectory` on a nonexistent path
report nothing either, so an empty listing is the only signal that a path was wrong.

And **`COPY` and `MOVE` do the work while reporting `-108,"Parameter not allowed"`.** The
operation succeeds; the error is spurious. Do not treat a non-empty queue as failure here.

This subsystem is the better way to manage instrument storage: it is the only route to a
directory listing with sizes and free space, the only way to create or remove directories, and
`MMEMory:DELete` deletes exactly the file named, which `DEL_STORE_FILE` does not.

**There is no undo.** `MMEMory:DELete` removes whatever path it is given. Back a library up with
`WVDT? USER,<name>` first.

**A `"` in a filename breaks every path operation.** All the handlers above strip every double
quote from their path argument (via `sdg_scpi_cmd_t::sdg_eraser_string_character(path, "\"")` at
`0x4cb5c0`) before touching the filesystem, and the tokeniser also drops `"` from unquoted
parameters, so **no SCPI escape can name a file whose name contains a `"`**. Such files (created
off-instrument, e.g. from a USB drive — `"` is legal on the instrument's Linux filesystem) list
and play fine but cannot be deleted, moved or renamed remotely. Worse, the strip makes
`MMEMory:DELete "Local/""x"".bin"` collapse to `Local/x.bin` and delete the *un-quoted*
namesake — a wrong-file hazard. Delete such files from the front panel instead. This is a
firmware bug; there is no driver-side fix.

### Undocumented parameters on documented commands

| Command | Parameter | Values | Source |
|---|---|---|---|
| `FreqCouNTer` | `TYPE` | `SLOW` / `FAST` | **both** — in every `FCNT?` response |
| `FreqCouNTer` | `DEF` | (action) | **both** — restores counter defaults; the query afterwards returns only `FCNT STATE,OFF` |
| `OUTPut` | `POWERON_STATE` | `ON` / `OFF` | **bench** — in every `OUTP?` response |
| `BaSic_WaVe` | `MAX_OUTPUT_AMP` | 1–20 Vpp | **bench** — in every `BSWV?` response; applies to both channels |
| `SweepWaVe` | `IDLE_FREQ` | `START_FREQ` / `STOP_FREQ` / `ZERO_FREQ` | **both** |
| `SweepWaVe` | `STEPNUM` | integer | **both** |
| `CASCADE` | `SYNC_PHASE` | **not implemented** | **both** — accepted, never in `CASCADE?` (which does carry `DELAY`) |
| `COUPling` | `DELAY` | **not implemented** | **both** — accepted, never in `COUP?` |
| `SampleRATE` | `INTER` | `LINE`/`HOLD`/`SINC`/`SINC27`/`SINC13` | firmware — silently ignored on this model |

Also worth knowing: `SWWV?`'s `SYM` field returns uninitialised garbage unless `DIR,UP_DOWN` is
set, and built-in arb indices **0 and 1 do work** (`Sine`, `Noise`) despite the guide's stated
range of 2–198. Index 67, which the guide calls `NA`, is **`Radar`** — confirmed by `STL? BUILDIN` on the
instrument, and shipped in the firmware as `70_radar_ram.bin`.

### Commands not to send

Present in the firmware, deliberately never exercised. Each writes flash, alters calibration,
or reconfigures hardware, and none has a documented parameter syntax:

```
ClearFLASH      DAC_SAVE      RESETADC      DRV_RECONFIG_PHASE
```

Named from the symbol table: `DAC_SAVE` is `scpi_save_time_base_cali_cb`, `RESETADC` is
`scpi_reset_ad9122`, `DRV_RECONFIG_PHASE` is `scpi_drp_dynamic_reconfig_phase_test_cb`. Note
that **`DACC`/`DAC_CODE` are `scpi_set/get_time_base_cali_cb`** — the time-base trim, not a DAC
output code, whatever the mnemonic suggests. The query forms are safe and returned `48153`.

(`MMEMory:DELete`, `MOVE` and `COPY` were on this list in an earlier draft. They have since been
exercised on a dummy file and are documented above; they touch stored files only, never flash or
calibration.)

`DACC?` and `DAC_CODE?` *are* safe to read — both answer, returning `48153` on the unit
tested. Only their set forms were left alone.

`ReadFLASH` and `ReadFLASHBLocK` are recognised and are read operations by name, but were not
exercised either. Calibration lives in the filesystem at `/usr/bin/siglent/usr/cali/`,
`cali.bin`, `cali.tar.gz` and `firmdata0/cali_date`; the service manual is clear that there is
no user calibration path and a failing unit goes back for service. Corrupting that storage
destroys the factory calibration and there is no second copy.

### Firmware package format

The SDG2000X firmware ships as a Siglent `.ADS` update container. That format —
its 112-byte header, the obfuscation transform, the non-standard two-key 3DES
layer, the ZIP container, and a reference decoder — is documented and decoded in
a separate project, https://github.com/JaredCabot/siglent-ads-format.

Two points matter from the SCPI side: you can inspect or extract a firmware
release before installing it, and the 216 built-in waveform tables come out of it
as plain 32,768-byte `.bin` files in exactly the layout `WVDT` expects (see
Storage and waveforms, above).

### `awg.app` has a full symbol table

The application binary is stripped of its `.symtab`, which makes it look opaque, but it ships a
`.dynsym` with **40,601 defined symbols** carrying addresses and C++ mangled names. So you never
have to guess what a command does:

```bash
readelf --dyn-syms -W awg.app | awk '$7!="UND"'
```

Command registration goes through two functions, `0x2cc0c8` and `0x2cc1f4`, both called as
`reg(name_ptr, handler_ptr, 1)` with the pointers built by `movw`/`movt` pairs. Walk the `.text`
section with capstone, track those pairs, and every `bl` to either address yields a
`(command string, handler address)` pair; look the handler up in `.dynsym` and it has a name.
Function boundaries come free from `.ARM.exidx`.

That method is what turned `MCBD` into `scpi_set_bandwidth_update_string_cb`, `k7dump` into
`drv_if_main_t::set_k7fpga_dump_switch`, and `DACC` into `scpi_set_time_base_cali_cb` rather
than the DAC write its mnemonic implies. **Presence in this table does not mean the command is
registered on the SDG2000X** — the binary is shared across SDG families and carries the whole
IQ and SDG7000A command set. Always confirm on the instrument with the `-113` oracle.

## Appendix G: Python driver and CLI

Save as `sdg2000x.py`. Needs Python 3 and PyVISA (any backend) for VISA resources; raw sockets need nothing extra.

```python
#!/usr/bin/env python3
"""Minimal driver and CLI for the Siglent SDG2000X arbitrary waveform generator.

Handles the model-specific quirks that trip people up: header-prefixed query
responses (this model has no CHDR), unit suffixes on returned values, the
mode-enable-before-parameters ordering, silent clamping of out-of-range values,
the error queue's blind spots, and the raw-binary arbitrary waveform transfer.

Verified against an SDG2122X on firmware 2.01.01.39R7.

Transports, in order of preference when auto-detecting:
  * PyVISA (NI-VISA or pyvisa-py)   USB0::...::INSTR  or  TCPIP0::<ip>::INSTR
  * Raw socket                      host:5025
  * Linux kernel usbtmc             /dev/usbtmc0

Usage as a library:

    from sdg2000x import SDG2000X
    with SDG2000X() as sdg:                      # auto-detects
        print(sdg.idn)
        sdg.set_load(1, 50)
        sdg.basic_wave(1, WVTP='SINE', FRQ=1e6, AMP=2)
        sdg.output(1, True)

Usage from a shell:

    python sdg2000x.py --idn
    python sdg2000x.py --send 'C1:BSWV WVTP,SINE,FRQ,1e6,AMP,2' --send 'C1:OUTP ON'
    python sdg2000x.py --query 'C1:BSWV?'
    python sdg2000x.py --resource TCPIP0::192.168.1.50::INSTR --idn
"""

from __future__ import annotations

import argparse
import math
import re
import socket
import struct
import sys
import time

TERM = "\n"
_MOD_TYPES = ("AM", "DSBAM", "FM", "PM", "PWM", "ASK", "FSK", "PSK")
# Unit suffixes actually observed in responses. Sa/s and the bare B on LENGTH
# only show up in SRATE? and WVDT? and are easy to miss.
_UNIT_RE = re.compile(
    r"^(-?[\d.]+(?:[eE][-+]?\d+)?)\s*"
    r"(HZ|Hz|Sa/s|Vrms|Vpp|dBm|dBc|dB|ppm|deg|S|V|B|%)?$")


class SDGError(RuntimeError):
    pass


# --------------------------------------------------------------------------- transports


class _VisaTransport:
    def __init__(self, resource=None, backend=""):
        import pyvisa

        rm = pyvisa.ResourceManager(backend)
        if resource is None:
            resource = self._discover(rm)
        self.dev = rm.open_resource(resource)
        self.dev.timeout = 5000
        self.dev.write_termination = TERM
        self.dev.read_termination = TERM
        self.resource = resource

    @staticmethod
    def _discover(rm):
        candidates = list(rm.list_resources())
        # Prefer anything that identifies as an SDG2xxxX.
        for res in candidates:
            if not (res.startswith("USB") or res.startswith("TCPIP")):
                continue
            try:
                dev = rm.open_resource(res)
                dev.timeout = 2000
                dev.write_termination = TERM
                dev.read_termination = TERM
                idn = dev.query("*IDN?")
                dev.close()
                if "SDG2" in idn.upper():
                    return res
            except Exception:
                continue
        raise SDGError(
            "No SDG2000X found. Resources seen: %s" % (candidates or "none")
        )

    def write(self, text):
        self.dev.write(text)

    def write_raw(self, data):
        self.dev.write_raw(data)

    def read(self):
        return self.dev.read()

    def read_raw(self):
        return self.dev.read_raw()

    def set_timeout(self, ms):
        self.dev.timeout = ms

    def set_chunk_size(self, n):
        self.dev.chunk_size = n

    def close(self):
        self.dev.close()


class _SocketTransport:
    def __init__(self, host, port=5025, timeout=5.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.resource = "%s:%d" % (host, port)

    def write(self, text):
        self.sock.sendall((text + TERM).encode())

    def write_raw(self, data):
        self.sock.sendall(data)

    def read(self):
        return self.read_raw().decode(errors="replace").strip()

    def read_raw(self):
        chunks = []
        while True:
            chunk = self.sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            if chunk.endswith(b"\n"):
                break
        return b"".join(chunks)

    def set_timeout(self, ms):
        self.sock.settimeout(ms / 1000.0)

    def set_chunk_size(self, n):
        pass

    def close(self):
        self.sock.close()


class _UsbtmcTransport:
    def __init__(self, path="/dev/usbtmc0"):
        self.f = open(path, "r+b", buffering=0)
        self.resource = path

    def write(self, text):
        self.f.write((text + TERM).encode())

    def write_raw(self, data):
        self.f.write(data)

    def read(self):
        return self.read_raw().decode(errors="replace").strip()

    def read_raw(self):
        return self.f.read(4 * 1024 * 1024)

    def set_timeout(self, ms):
        pass

    def set_chunk_size(self, n):
        pass

    def close(self):
        self.f.close()


# --------------------------------------------------------------------------- driver


class SDG2000X:
    """Thin wrapper over one SDG2000X session."""

    def __init__(self, resource=None, host=None, device=None, backend="", settle=0.0):
        self.settle = settle
        if host:
            self.t = _SocketTransport(host)
        elif device:
            self.t = _UsbtmcTransport(device)
        else:
            try:
                self.t = _VisaTransport(resource, backend)
            except Exception as exc:
                if resource:
                    raise
                try:
                    self.t = _UsbtmcTransport()
                except Exception:
                    raise SDGError("Could not open a session: %s" % exc)
        self.idn = self.query("*IDN?")
        if "SDG2" not in self.idn.upper():
            print(
                "warning: connected instrument reports %r, which is not an SDG2000X; "
                "the SCPI dialect differs across SDG families" % self.idn,
                file=sys.stderr,
            )

    # ---- plumbing

    def write(self, cmd):
        # No settle delay by default: USBTMC writes are flow-controlled and
        # nothing is dropped, verified with 100 unpaced writes landing in order.
        self.t.write(cmd)
        if self.settle:
            time.sleep(self.settle)

    def query(self, cmd):
        self.t.write(cmd)
        return self.t.read().strip()

    def sync(self):
        """Block until the instrument has finished everything sent so far."""
        return self.query("*OPC?")

    def error(self):
        """Pop one entry from the error queue. '0,"No error"' when clean.

        The queue is real on this model despite the programming guide never
        mentioning it, but it only catches unknown headers (-113), disallowed
        parameters (-108), invalid characters (-101) and execution errors
        (-200). Unknown *parameter names*, unrecognised enum values and every
        kind of range clamping are accepted silently, so a clean queue is not
        evidence that a setting took. Use set_and_verify() for that.
        """
        return self.query("SYST:ERR?")

    def errors(self, limit=30):
        """Drain and return every queued error. Call at startup: the queue
        persists across sessions and may hold entries from whatever ran last.
        """
        out = []
        for _ in range(limit):
            e = self.error()
            if e.startswith("0,") or "No error" in e:
                break
            out.append(e)
        return out

    def supports(self, command, bogus="ZZQQ"):
        """True if the instrument's parser recognises `command`.

        Sends the command with a deliberately bogus argument and checks the
        error queue: -113 means the header is unknown, anything else means it
        was parsed. The bogus argument keeps a real command from executing.

        Probe the write form, NEVER the query form. A query to a header with no
        query form times out, and the timeout itself wedges the USBTMC endpoint:
        every later write fails with VI_ERROR_IO, and neither dev.clear() nor
        reopening the session recovers it -- only a physical USB re-plug does.

        Also note this cannot decide a channel-prefixed header: C3:/C0: give
        -113, but C1:<anything> is accepted silently, so only the prefix is
        validated. Probe without a channel prefix.

        This tests the *header*, not the effect. See set_and_verify().
        """
        self.errors()
        self.write(command if " " in command else "%s %s" % (command, bogus))
        return "-113" not in self.error()

    def close(self):
        try:
            self.t.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- response parsing

    @staticmethod
    def parse(response):
        """Turn 'C1:BSWV WVTP,SINE,FRQ,1000HZ,...' into a dict of native values.

        The SDG2000X cannot suppress command headers, so every query response
        carries one. Values arrive with unit suffixes glued on.
        """
        header, _, body = response.partition(" ")
        if not body:
            body, header = header, ""
        parts = [p.strip() for p in body.split(",") if p.strip() != ""]
        out = {}
        prefix = ""
        i = 0
        # A header with a single bare value and no pairs at all, e.g.
        # 'MODE PHASE-LOCKED', 'LAGG EN', 'SCFG USER', 'C1:CMBN OFF'.
        if len(parts) == 1:
            return {"VALUE": _coerce(parts[0])}
        # A leading bare state, e.g. 'C1:OUTP ON,LOAD,HZ,PLRT,NOR'
        if parts and parts[0] in ("ON", "OFF"):
            out["STATE"] = parts[0]
            i = 1
        # Only MDWV responses carry a bare modulation-type token, and only there
        # is it safe to treat one as a marker: 'AM', 'FM' and 'PM' are also the
        # names of built-in arbitrary waveforms and appear as ARWV *values*.
        is_mdwv = header.upper().endswith("MDWV")
        while i < len(parts):
            key = parts[i]
            # Bare markers advance by one and resync the walk. Real firmware
            # puts the modulation type *after* STATE, not first as the
            # programming guide's example shows:
            #   C1:MDWV STATE,ON,AM,MDSP,SINE,SRC,INT,FRQ,100HZ,DEPTH,100,CARR,...
            # Missing that shifts every subsequent pair by one.
            if is_mdwv and key in _MOD_TYPES:
                out["TYPE"] = key
                i += 1
                continue
            # 'CARR' switches the rest into the carrier namespace, which matters
            # because MDWV and SWWV/BTWV responses carry both a modulation FRQ
            # and a carrier FRQ.
            if key == "CARR":
                prefix = "CARR_"
                i += 1
                continue
            if i + 1 >= len(parts):
                break
            out[prefix + key] = _coerce(parts[i + 1])
            i += 2
        return out

    def query_dict(self, cmd):
        return self.parse(self.query(cmd))

    # ---- output

    def output(self, ch, on=True):
        self.write("C%d:OUTP %s" % (ch, "ON" if on else "OFF"))

    def output_both(self, on=True):
        self.write("OUT_BOTHCH %s" % ("ON" if on else "OFF"))

    def set_load(self, ch, load):
        """load is ohms (50..100000) or the string 'HZ' for high impedance.

        Set this before setting any amplitude: the instrument computes output
        voltage from the assumed load, so changing it afterwards silently
        changes every voltage already entered.
        """
        self.write("C%d:OUTP LOAD,%s" % (ch, load))

    def set_polarity(self, ch, invert=False):
        self.write("C%d:OUTP PLRT,%s" % (ch, "INVT" if invert else "NOR"))

    # ---- basic waveform

    def basic_wave(self, ch, **params):
        """e.g. basic_wave(1, WVTP='SINE', FRQ=1e6, AMP=2, OFST=0)

        Every parameter goes in one command deliberately. A BSWV write costs
        about 45 ms on this instrument no matter how little it changes, so four
        separate writes cost ~194 ms where one combined write costs ~60 ms.
        """
        self.write("C%d:BSWV %s" % (ch, _pairs(params)))

    def get_basic_wave(self, ch):
        return self.query_dict("C%d:BSWV?" % ch)

    def set_and_verify(self, ch, tol=1e-3, **params):
        """Set basic-wave parameters and check the instrument kept them.

        Out-of-range values are clamped silently with no error, so this is the
        only reliable way to know an instrument actually did what you asked.
        Returns a dict of {param: (requested, actual)} for anything that differs.
        """
        self.basic_wave(ch, **params)
        actual = self.get_basic_wave(ch)
        mismatches = {}
        for key, want in params.items():
            got = actual.get(key)
            if got is None:
                continue
            if isinstance(want, (int, float)) and isinstance(got, (int, float)):
                if want == 0:
                    ok = abs(got) <= tol
                else:
                    ok = abs(got - want) <= tol * abs(want)
            else:
                ok = str(got).upper() == str(want).upper()
            if not ok:
                mismatches[key] = (want, got)
        return mismatches

    # ---- modes (STATE,ON must precede every other parameter)

    def modulation(self, ch, mtype, **params):
        self.write("C%d:MDWV STATE,ON" % ch)
        self.write("C%d:MDWV %s" % (ch, mtype))
        for key, val in params.items():
            if key.startswith("CARR_"):
                self.write("C%d:MDWV CARR,%s,%s" % (ch, key[5:], _fmt(val)))
            else:
                self.write("C%d:MDWV %s,%s,%s" % (ch, mtype, key, _fmt(val)))

    def modulation_off(self, ch):
        self.write("C%d:MDWV STATE,OFF" % ch)

    def sweep(self, ch, **params):
        self.write("C%d:SWWV STATE,ON" % ch)
        for key, val in params.items():
            if key.startswith("CARR_"):
                self.write("C%d:SWWV CARR,%s,%s" % (ch, key[5:], _fmt(val)))
            else:
                self.write("C%d:SWWV %s,%s" % (ch, key, _fmt(val)))

    def sweep_off(self, ch):
        self.write("C%d:SWWV STATE,OFF" % ch)

    def burst(self, ch, **params):
        self.write("C%d:BTWV STATE,ON" % ch)
        for key, val in params.items():
            if key.startswith("CARR_"):
                self.write("C%d:BTWV CARR,%s,%s" % (ch, key[5:], _fmt(val)))
            else:
                self.write("C%d:BTWV %s,%s" % (ch, key, _fmt(val)))

    def burst_off(self, ch):
        self.write("C%d:BTWV STATE,OFF" % ch)

    def trigger(self, ch, mode="burst"):
        """Fire a manual trigger. Only valid when that mode's TRSR is MAN."""
        self.write("C%d:%s MTRIG" % (ch, "BTWV" if mode == "burst" else "SWWV"))

    # ---- arbitrary waveforms

    def arb_builtin(self, ch, index):
        """Select a built-in arbitrary waveform, index 2-198."""
        self.write("C%d:BSWV WVTP,ARB" % ch)
        self.write("C%d:ARWV INDEX,%d" % (ch, index))

    def arb_recall(self, ch, name):
        """Select a previously uploaded user waveform by name.

        Strips any '.bin' first: ARWV? reports the name with the extension
        appended, but feeding that back is rejected with -101 Invalid character.
        """
        if name.lower().endswith(".bin"):
            name = name[:-4]
        self.write("C%d:BSWV WVTP,ARB" % ch)
        self.write("C%d:ARWV NAME,%s" % (ch, name))

    def upload_arb(self, ch, name, samples, freq=1000.0, ampl=4.0, offset=0.0,
                   phase=0.0, normalise=True, recall=True):
        """Upload a waveform and optionally select it.

        `samples` is a sequence of floats. With normalise=True (default) they
        are scaled so the largest magnitude maps to full scale, which uses the
        whole 16-bit DAC range; with normalise=False they are treated as being
        already in -1.0..+1.0 and are clipped rather than allowed to wrap
        (an int16 overflow turns a peak into a full-negative spike).

        The wire format is raw little-endian signed 16-bit codewords appended
        after 'WAVEDATA,', so this must go out as bytes via write_raw.
        """
        vals = list(samples)
        if not vals:
            raise SDGError("no samples given")
        if len(vals) < 2 or len(vals) > 8 * 1024 * 1024:
            raise SDGError("waveform must be 2 to 8388608 points, got %d" % len(vals))
        if normalise:
            peak = max(abs(v) for v in vals) or 1.0
            vals = [v / peak for v in vals]
        codes = [max(-32768, min(32767, int(round(v * 32767)))) for v in vals]
        payload = struct.pack("<%dh" % len(codes), *codes)

        self.t.set_timeout(60000)
        self.t.set_chunk_size(20 * 1024 * 1024)
        header = ("C%d:WVDT WVNM,%s,FREQ,%g,AMPL,%g,OFST,%g,PHASE,%g,WAVEDATA,"
                  % (ch, name, freq, ampl, offset, phase)).encode()
        self.t.write_raw(header + payload + b"\n")
        time.sleep(0.2)
        if recall:
            self.arb_recall(ch, name)
        return len(codes)

    def download_arb(self, name, expected_bytes=None, timeout=15.0):
        """Read a stored user waveform back as a list of int16 codewords.

        A single read_raw() returns only the first fragment of the response
        (104 bytes of an 8192-byte payload in testing), so this loops until the
        expected length arrives or the deadline passes.

        The query also queues a spurious -108 "Parameter not allowed" on
        firmware 2.01.01.39R7 even though it returns correct data, so the error
        queue is drained afterwards to stop it poisoning a later check.
        """
        self.t.set_timeout(60000)
        self.t.set_chunk_size(20 * 1024 * 1024)
        self.t.write("WVDT? USER,%s" % name)
        time.sleep(0.5)
        buf = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                buf += self.t.read_raw()
            except Exception:
                break
            if expected_bytes and len(buf) >= expected_bytes + 60:
                break
            if buf.endswith(b"\n") and expected_bytes is None and len(buf) > 64:
                break
        pos = buf.find(b"WAVEDATA,")
        if pos < 0:
            raise SDGError("no WAVEDATA in response: %r" % buf[:120])
        payload = buf[pos + 9:]
        if payload.endswith(b"\n"):
            payload = payload[:-1]
        payload = payload[:len(payload) - (len(payload) % 2)]
        self.t.set_timeout(5000)
        self.errors()          # absorb the spurious -108 this query always queues
        return list(struct.unpack("<%dh" % (len(payload) // 2), payload))

    def truearb(self, ch, sample_rate):
        """Point-for-point playback at a set rate. Period = points / rate."""
        self.write("C%d:SRATE MODE,TARB" % ch)
        self.write("C%d:SRATE VALUE,%g" % (ch, sample_rate))

    def dds(self, ch):
        self.write("C%d:SRATE MODE,DDS" % ch)

    def store_list(self, what=None):
        return self.query("STL?" + (" " + what if what else ""))

    def screenshot(self, path=None):
        """Grab the screen over the interface as an uncompressed 24-bit BMP.

        SCDP is registered as a query under a name with no question mark, so it
        is written and then read; SCDP? answers -113. The image is 480x272,
        391,734 bytes, and no file is written on the instrument. The
        alternative, SCREEN_SHOT, writes Local/screen.png or screen.bmp there
        instead, under a fixed name that each capture overwrites.
        """
        self.t.set_timeout(20000)
        self.t.set_chunk_size(4 * 1024 * 1024)
        self.t.write("SCDP")
        buf = self.t.read_raw()
        if buf[:2] != b"BM":
            raise SDGError("SCDP did not return a BMP (got %r)" % buf[:8])
        size = struct.unpack_from("<I", buf, 2)[0]
        buf = buf[:size]
        if path:
            with open(path, "wb") as fh:
                fh.write(buf)
        return buf

    def dc_final_amplifier(self, ch, on=None):
        """The undocumented DC final amplifier switch. Default OFF.

        Registered with a C#: channel wildcard; the query answers
        'C1:DcUFAmplifier,OFF'.
        """
        if on is not None:
            self.write("C%d:DcUFAmplifier %s" % (ch, "ON" if on else "OFF"))
        return self.query("C%d:DcUFAmplifier?" % ch).split(",")[-1].strip()

    # ---- file management (MMEMory)
    #
    # The programming guide marks MMEMory as SDG7000A-only. It is wrong: the
    # whole subsystem works on the SDG2000X with the documented syntax. Two
    # quirks are handled here. MMEMory:CATalog? returns nothing at all without
    # its path argument (leaving -200 in the queue), and COPY and MOVE do the
    # work and then report a spurious -108, so their queue must be drained
    # rather than believed.

    def catalog(self, path="Local"):
        """Directory listing. Returns (free_bytes, used_bytes, [(name, type, size)]).

        A file is listed as "name,type,size"; a subdirectory is listed as a
        bare quoted name with no type or size, and is reported here as
        (name, "DIR", None). A path that does not exist answers "0,0" with an
        empty error queue, so an empty listing is the only signal of a bad
        path.
        """
        resp = self.query('MMEMory:CATalog? "%s"' % path)
        parts = [p.strip() for p in resp.split(",")]
        free = int(parts[0]) if parts and parts[0].isdigit() else None
        used = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        entries, rest = [], resp.split(",", 2)[2] if resp.count(",") >= 2 else ""
        for chunk in re.findall(r'"([^"]*)"', rest):
            f = [x.strip() for x in chunk.split(",")]
            if len(f) == 3:
                entries.append((f[0], f[1], int(f[2]) if f[2].isdigit() else f[2]))
            elif len(f) == 1 and f[0]:
                entries.append((f[0], "DIR", None))
        return free, used, entries

    @staticmethod
    def _check_path(*paths):
        """Guard against the firmware's quote-stripping bug.

        Every MMEMory path handler erases all '"' from its argument before the
        filesystem call, so a name containing a '"' is unaddressable and, worse,
        a delete of it silently hits the un-quoted namesake. There is no SCPI
        escape, so refuse rather than act on the wrong file.
        """
        for p in paths:
            if '"' in p:
                raise SDGError(
                    "path %r contains a double quote; the instrument strips it "
                    "and would act on the wrong file. Delete this file from the "
                    "front panel instead." % p)

    def mmem_copy(self, src, dst):
        """Copy a file. Succeeds but reports -108; the error is drained here."""
        self._check_path(src, dst)
        self.write('MMEMory:COPY "%s","%s"' % (src, dst))
        self.errors()

    def mmem_move(self, src, dst):
        """Move/rename a file. Succeeds but reports -108; the error is drained here."""
        self._check_path(src, dst)
        self.write('MMEMory:MOVE "%s","%s"' % (src, dst))
        self.errors()

    def mmem_delete(self, path):
        """Delete exactly the file named. No undo.

        Preferred over DEL_STORE_FILE, which removes only the .bin of a user
        waveform and silently orphans the matching .info.
        """
        self._check_path(path)
        self.write('MMEMory:DELete "%s"' % path)

    def mmem_mkdir(self, path):
        self._check_path(path)
        self.write('MMEMory:MDIRectory "%s"' % path)

    def mmem_rmdir(self, path):
        self._check_path(path)
        self.write('MMEMory:RDIRectory "%s"' % path)

    def delete_waveform(self, name, path="Local"):
        """Remove a stored user waveform, both members of the pair."""
        base = name[:-4] if name.lower().endswith(".bin") else name
        for member in (base + ".bin", base + ".info"):
            self.mmem_delete("%s/%s" % (path, member))
            self.errors()

    # ---- misc

    def counter(self, on=True, **params):
        self.write("FCNT STATE,%s" % ("ON" if on else "OFF"))
        if params:
            self.write("FCNT %s" % _pairs(params))

    def read_counter(self):
        return self.query_dict("FCNT?")

    def protection(self, on=None):
        """Over-voltage protection. VOLTPRT? answers a bare 'ON'/'OFF'.

        Note VOLTSTAT? and CURRPRT, which the programming guide lists for this
        model, return -113 Undefined header on real hardware, so the trip state
        cannot be polled over SCPI at all.
        """
        if on is not None:
            self.write("VOLTPRT %s" % ("ON" if on else "OFF"))
        return self.query("VOLTPRT?")

    def reset(self):
        """Factory reset. Takes 2-3 s; note the reset load is HiZ, not 50 ohm."""
        self.write("*RST")
        time.sleep(3.0)

    def safe_shutdown(self):
        """Leave the instrument in a state that cannot damage anything."""
        for ch in (1, 2):
            try:
                self.output(ch, False)
            except Exception:
                pass


# --------------------------------------------------------------------------- helpers


def _coerce(raw):
    m = _UNIT_RE.match(raw)
    if m:
        try:
            val = float(m.group(1))
            return int(val) if val.is_integer() and "." not in m.group(1) else val
        except ValueError:
            pass
    return raw


def _fmt(val):
    if isinstance(val, float):
        return repr(val) if abs(val) < 1e15 else "%g" % val
    return str(val)


def _pairs(params):
    return ",".join("%s,%s" % (k, _fmt(v)) for k, v in params.items())


def sine(n, cycles=1):
    """Convenience generator for a normalised sine of n points."""
    return [math.sin(2 * math.pi * cycles * i / n) for i in range(n)]


# --------------------------------------------------------------------------- CLI


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Talk to a Siglent SDG2000X.",
        epilog="With no transport option, a USB/LAN VISA resource is auto-detected, "
               "falling back to /dev/usbtmc0.",
    )
    p.add_argument("--resource", help="VISA resource string")
    p.add_argument("--host", help="IP address, uses raw socket port 5025")
    p.add_argument("--device", help="usbtmc character device, e.g. /dev/usbtmc0")
    p.add_argument("--backend", default="", help="PyVISA backend, e.g. @py")
    p.add_argument("--idn", action="store_true", help="print *IDN? and exit")
    p.add_argument("--send", action="append", default=[], metavar="CMD",
                   help="send a command; repeatable, sent in order")
    p.add_argument("--query", action="append", default=[], metavar="CMD",
                   help="send a query and print the response; repeatable")
    p.add_argument("--parse", action="store_true",
                   help="print query responses as parsed key/value pairs")
    p.add_argument("--list", action="store_true", help="list VISA resources and exit")
    p.add_argument("--errors", action="store_true", help="drain and print the error queue")
    args = p.parse_args(argv)

    if args.list:
        import pyvisa
        for r in pyvisa.ResourceManager(args.backend).list_resources():
            print(r)
        return 0

    with SDG2000X(resource=args.resource, host=args.host, device=args.device,
                  backend=args.backend) as sdg:
        if args.idn or not (args.send or args.query or args.errors):
            print(sdg.idn)
        if args.errors:
            errs = sdg.errors()
            print("\n".join(errs) if errs else '0,"No error"')
        for cmd in args.send:
            sdg.write(cmd)
        for cmd in args.query:
            resp = sdg.query(cmd)
            if args.parse:
                for k, v in sdg.parse(resp).items():
                    print("%-16s %s" % (k, v))
            else:
                print(resp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
