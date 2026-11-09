---
name: "siglent-sds2000x-hd"
description: "Operate, program (SCPI over USB/LAN), capture waveforms from, verify and service the Siglent SDS2000X HD 12-bit oscilloscopes (SDS2104X/2204X/2354X/2504X HD): triggers, decode, MSO, FFT, power, Bode, AWG."
---

# Siglent SDS2000X HD: operation, remote control and service

The SDS2000X HD is a 4-channel, 12-bit oscilloscope family: SDS2104X HD
(100 MHz), SDS2204X HD (200 MHz), SDS2354X HD (350 MHz) and SDS2504X HD
(500 MHz). 2 GSa/s, 200 Mpts/ch, 10.1 in 1024 x 600 touch screen, optional
16 digital channels, optional 25 MHz single-channel AWG, serial trigger and
decode, power analysis and Bode plot.

Sources:

| Short ref | Document | Use it for |
|---|---|---|
| UM | SDS2000X HD Series User Manual EN01B (302 pp.) | Front panel, every menu, behaviour |
| PG | SDS Series Programming Guide EN11G (855 pp.) | SCPI. Multi-model guide; SDS2000X HD support needs firmware 1.2.0.2 or later |
| QS | SDS2000X HD Quick Start EN01C | Short form of the UM; self-cal and Quick Cal notes |
| SM | SDS2000X HD Service Manual EN01A | Performance verification, disassembly, board test points |
| DS | SDS2000X HD Datasheet EN01A (not one of the four manuals; fetched from a distributor copy) | Specifications the manuals defer to the datasheet. A newer EN02B exists; figures may have moved |

Page references are printed page numbers ("PG p.482", "UM p.73").

Nothing here has been checked on a real instrument yet. The PG covers ten
model families, and many of its tables lost their row layout in text
extraction; where an SDS2000X HD value had to be reconstructed this file says
so. Anything marked UNVERIFIED is a lead to test. When the bench disagrees with
this file, believe the bench and update the skill.

## Contents

1. Instrument at a glance
2. Things that bite
3. Connecting
4. SCPI conventions, synchronisation and errors
5. Front panel and touch screen
6. Vertical system
7. Horizontal, acquisition, sequence, history, zoom
8. Triggering
9. Serial trigger and decode
10. Digital channels (MSO)
11. Measurements, cursors, counter, DVM
12. Math and FFT
13. Search, navigate, mask test, histogram
14. Power analysis and Bode plot
15. Reference waveforms, memory waveforms, save and recall
16. Display
17. Waveform generator (AWG)
18. Reading waveform data
19. System, LAN, options, firmware, self-cal
20. Performance verification
21. Service and troubleshooting
22. Python driver
23. Recipes
24. Manual discrepancies

## 1. Instrument at a glance

| Item | Value | Source |
|---|---|---|
| Channels | 4 analog + EXT trigger; 16 digital with SDS2000HD-16LA and the SPL2016 probe | UM p.34-35, 64 |
| ADC | 12 bit | DS |
| Sample rate | 2 GSa/s interleaved, 1 GSa/s non-interleaved | DS, SM p.28 |
| Memory | 200 Mpts/ch interleaved, 100 Mpts/ch non-interleaved; 20 / 10 Mpts in Average and ERES (DS) | UM p.73, DS |
| Update rate | up to 100,000 wfm/s normal, 500,000 wfm/s sequence | DS, UM p.77 |
| Sequence / History | up to 80,000 segments / frames, 2 µs minimum trigger interval | UM p.77, 80 |
| V/div | 0.5 mV to 10 V/div at 1 MΩ; 0.5 mV to 1 V/div at 50 Ω (1X probe) | DS |
| Vertical range | 8 divisions | UM p.40 |
| Bandwidth limits | 20 MHz, 200 MHz (hardware) | UM p.60-61 |
| Input | 1 MΩ ±2% ∥ 16 pF ±2 pF, or 50 Ω ±1%. Max 400 Vpk (DC+AC, DC to 10 kHz) at 1 MΩ; 5 Vrms at 50 Ω | DS, SM p.46 |
| DC gain accuracy | Spec ±0.5% (5 mV to 10 V/div), ±1.5% (0.5 to 4.95 mV/div) (DS). PV limit ±0.6% (5.8 mV to 10 V/div), ±1.5% (1 to 4.45 mV/div) (SM p.28-32) | DS, SM |
| Offset accuracy | ±(0.5% of offset + 0.5% of full scale + 1 mV) | SM p.33 |
| Timebase | 1 ns/div to 1000 s/div; ±2 ppm initial, ±0.5 ppm first-year aging | DS |
| Channel skew | ≤ 100 ps | SM p.45 |
| Trigger level range | ±4.1 div about screen centre (channels); EXT ±0.61 V; EXT/5 ±3.05 V | PG p.492, DS |
| Holdoff | 8 ns to 30 s, or 1 to 10^8 events | PG |
| Digital | 500 MSa/s, 50 Mpts/ch, two threshold groups D0-D7 and D8-D15, -10 to +10 V | DS, UM p.69 |
| AWG (option FG) | 1 ch, 25 MHz, 125 MSa/s, 14 bit, 16 kpts arb, ±1.5 V into 50 Ω (±3 V Hi-Z) | DS, UM p.271 |
| FFT | up to 2 Mpts (2^21) | UM p.198 |
| Display | 10.1 in TFT, 1024 x 600, capacitive multi-touch | DS |
| I/O | USB 2.0 host x2 front, x1 rear; USB 2.0 device (USBTMC); 10/100 LAN; EXT trig in; Aux Out; AWG out | UM p.34-35 |
| Power | 100-240 V 50/60 Hz, 120 W max | SM p.9 |
| Environment | 0 to 50 °C operating; 5-90% RH at 30 °C, 50% at 40 °C; ≤ 3000 m | SM p.7 |

Model-dependent analog figures (DS, typical): rise time 1 / 1.7 / 3.5 ns and
noise 65 / 55 / 50 µVrms at 1 mV/div 50 Ω for the 350 / 200 / 100 MHz models.

**Interleaving.** Channels pair as CH1/CH2 and CH3/CH4. If only one channel
of each pair is on, that channel runs at 2 GSa/s with 200 Mpts. If both
channels of a pair are on, the pair drops to 1 GSa/s and 100 Mpts. So CH1 + CH3
is still interleaved; CH1 + CH2 is not. The UM calls these "single-channel" and
"dual-channel" mode (UM p.73), the SM "interleaving" and "non-interleaving"
(SM p.28). On the 500 MHz model a ~350 MHz anti-aliasing filter switches in
automatically whenever the rate is ≤ 1 GSa/s (UM p.42).

Front panel (UM p.34): C1-C4 BNC, probe comp (1 kHz, 0-3 V square) and ground
lug, 2 x USB host, digital probe connector, power key (orange = standby,
white = on, SM p.57). Rear (UM p.35): EXT TRIG, Aux Out (trigger out by
default; pass/fail pulse when mask test is on), WaveGen output, LAN, USB
device, USB host, AC inlet. The BNC shells are at chassis (earth) potential
(SM p.10). There is no 10 MHz reference input or output.

Options (UM, DS):

| Option | Unlocks |
|---|---|
| SDS2000HD-FG | Built-in AWG (hardware is fitted, licence-locked). Also required for the external SAG1021I |
| SDS2000HD-16LA | 16 digital channels (needs the SPL2016 probe) |
| SDS2000HD-PA | Power analysis |
| -I2S, -1553B, -FlexRay, -CANFD, -SENT, -Manch (DS names) | Serial protocols beyond the standard I2C, SPI, UART, CAN, LIN |
| BW1T2, BW1T3, BW1T5, BW2T3, BW2T5, BW3T5 (DS names) | Bandwidth upgrades (100/200/350 to 200/350/500 MHz) |

Licences go in at Utility > Menu > Software Options (type, key, Install, then
reboot, QS p.34), or from a licence file in the root of a USB stick. An
uninstalled "Temporary" licence works up to 30 times (UM p.292). Decoding
digital channels needs both 16LA and the protocol licence (UM p.65).

## 2. Things that bite

1. **12-bit data needs WORD transfers.** `:WAVeform:WIDTh` defaults to BYTE
   (the preamble's COMM_TYPE default is 0 = byte, PG p.754),
   which throws away the low bits. Send `:WAV:WIDT WORD` before
   `:WAV:DATA?`. Words are signed int16, LSB first by default, left-aligned
   with the low bits zero-filled. Scale with the preamble's `code_per_div`
   (offset 0xA4), never a hard-coded 25, 30 or 7680 (PG p.753, 758).

2. **Only `*IDN?`, `*OPC?` and `*RST` are documented** (PG p.29). There is no
   documented error queue, `*CLS`, `*ESR?` or `*STB?`. Out-of-range numbers are
   generally clamped without complaint (`:ACQ:SRAT`, `:TIM:SCAL`, zoom, gate
   cursors). After any setting that matters, read it back. `:SYSTem:ERRor?`,
   `*ESR?` and the legacy `INR?` (used in the PG's own C# example) are worth
   trying, UNVERIFIED.

3. **Query precision defaults to 3 significant digits.** `:FORMat:DATA` sets
   how many digits NR3 replies carry: SINGle = 7, DOUBle = 14, CUSTom,<1-64>
   (PG p.34). At the default, `:TRIG:FREQ?` gives "1.00E+07" for a 9.99998 MHz
   signal. Send `:FORM:DATA DOUB` once after connecting.

4. **The status strings are mixed case, with an apostrophe.**
   `:TRIGger:STATus?` returns `Arm`, `Ready`, `Auto`, `Trig'd`, `Stop` or
   `Roll` (PG p.483). Compare exactly, or upper-case both sides.

5. **`*OPC?` blocks the interface** until pending operations finish (PG p.30)
   and the PG never says that it waits for an acquisition. For a single shot,
   send `:TRIG:MODE SINGle` and poll `:TRIG:STAT?` until it reads `Stop`. This
   is what the PG's C# example does (PG p.827-828).

6. **Settings with two sources of truth.** Serial trigger settings and decode
   settings are completely separate (UM p.117). Changing the decode baud rate
   does not change the trigger's. Copy with `:DECode:BUS<n>:COPY FROMtrigger`
   (trigger to decode) or `TOTRigger` (decode to trigger), and copy again after
   every change. The PG's own example for COPY describes the direction
   backwards (PG p.143); trust the parameter definitions.

7. **Thresholds and levels are limited to ±4.1 divisions of the channel's
   current scale and offset** (`[-4.1*vdiv - offset, 4.1*vdiv - offset]`). This
   applies to trigger levels, decode thresholds, search levels and the counter
   level. Set V/div and offset first, then the level. Values outside are
   clamped or rejected, the PG does not say which.

8. **Interleaving changes memory and rate.** Turning on the second channel of a
   pair (CH1+CH2 or CH3+CH4) halves sample rate and memory. `:ACQ:MDEPth`
   accepts only the tokens for the current mode: `20k|200k|2M|20M|200M` when
   interleaved, `10k|100k|1M|10M|100M` when not (PG p.40). Set channels first,
   then memory depth. Changing V/div or the interleave mode also triggers a
   background ADC calibration that briefly interrupts acquisition (QS p.34).

9. **While running, analysis uses only the on-screen record.** Measurements,
   math, decode and search ignore samples outside the screen until you press
   Stop, even in Fixed Memory mode (UM p.76).

10. **Average and ERES are unavailable in sequence mode** (PG p.47), limit
    memory depth (PG p.41; 20/10 Mpts per the DS), and ERES cuts bandwidth:
    3 bits leaves 0.007 x Fs (UM p.75).

11. **`:CHANnel<n>:SCALe?` is probe-scaled** (PG p.58), and so are offsets
    and levels you send. Set `:CHAN<n>:PROBe` before scale, offset and trigger
    level. The waveform preamble's V/div and offset exclude the probe; multiply
    by the probe factor at 0x148 to get probe-tip volts.

12. **Passive probes need 1 MΩ.** At 50 Ω a 10X probe reads nothing useful,
    and the 50 Ω input is not a high-power input (UM p.62; 5 Vrms max per
    the DS). Do not switch a channel with a live high-voltage signal to 50 Ω
    from a script.

13. **Hex fields go as decimal, and "don't care" is one past the maximum.**
    `:TRIG:CAN:ID 125935441` for 0x7819F51. Data bytes: 256 = 0xXX. IIC address
    1024, CAN 11-bit ID 2048, 29-bit ID 536870912, LIN ID 64, FlexRay ID 2048
    (PG p.640-712).

14. **Misprinted enumerations.** BITorder is printed `{LSM|MSB}`; send `LSB`.
    `:TRIGger:TYPE` and `:SEARch:MODE` take `PULSE` (not the `PULSe` subsystem
    name). Manchester polarity is printed `PULarity`; send `POLarity`. SPI latch
    edge is `:TRIGger:SPI:LATChedge`, not `...:SPI:CLK:LATChedge` (PG p.653,
    484, 228, 661).

15. **Some queries take arguments.** `:TRIG:PATT:LEV? C2` and
    `:TRIG:DEL:LEV? C2` return `C2,<value>`; `:MEAS:SIMP:VAL? PKPK`;
    `:MEAS:ADV:P1:STAT? MEAN`. Several queries return the word `OFF` instead of
    a number when statistics are off (`:COUN:STAT:VAL?`,
    `:MEAS:ADV:P<n>:STAT?`). The PG does not say what an invalid measurement
    returns: guard every float() conversion.

16. **Remote does not lock the panel unless you ask.** `:SYSTem:REMote ON`
    locks keys and touch screen; `OFF` releases them (PG p.467). A script that
    crashes with REMote ON leaves the scope locked until it is cleared.

17. **File paths are not checked against the type.** `:SAVE:...` never infers
    the format from the extension. A path with no prefix goes to `U-disk0/`.
    Prefixes: `local/`, `net_storage/`, `U-disk0/`, `U-disk1/` (PG p.407-413).
    `:RECall:SERase` deletes every user file stored inside the scope (PG p.397).

18. **Firmware updates must not lose power.** A power cut during an upgrade can
    leave the scope unable to boot (UM p.294). Recovery is by a Siglent USB
    recovery package (SM p.57).

19. **Documented defaults are almost absent.** The PG states no defaults for
    triggers, decode or counter. Set every parameter a measurement depends on.

## 3. Connecting

USB: rear USB Device port (type B). It enumerates as USBTMC with Siglent's
vendor ID 0xF4EC (PG p.813 example `USB0::0xF4EC::0xEE38::<serial>::INSTR`; the
product ID 0xEE38 is an example, so enumerate rather than hard-code). On
Windows install NI-VISA (the Run-Time Engine is enough, PG p.19) or use
pyvisa-py with libusb.

LAN: Utility > Menu > I/O > LAN Config, DHCP or static IP, mask, gateway and
DNS (UM p.289-290). SCPI equivalents take quoted strings:
`:SYST:COMM:LAN:TYPE STATIC`, `:SYST:COMM:LAN:IPAD "192.168.1.50"`,
`:SYST:COMM:LAN:SMAS "255.255.255.0"`, `:SYST:COMM:LAN:GAT "192.168.1.1"`,
`:SYST:COMM:LAN:MAC?` (PG p.455-458).

| Protocol | Address | Notes |
|---|---|---|
| VXI-11 (VISA) | `TCPIP0::<ip>::INSTR` (also `TCPIP::<ip>::inst0::INSTR`) | PG examples use both |
| Raw socket | TCP port 5025 | Commands end with `\n`. Replies end with `\n`; binary blocks end with `0A 0A` |
| Telnet | TCP port 5024 | Prompt `SCPI>`; quit with Ctrl+] then `quit` (PG p.24) |
| Web | `http://<ip>` | Live remote screen, screenshot, BIN/CSV waveform download, bin-to-CSV converter, firmware upgrade (UM p.299). Password up to 20 bytes: Utility > Menu > I/O > Web Server |
| VNC | port 5900-5999 | `:SYST:COMM:VNCPort 5901`. Give each Siglent instrument its own port (UM p.290) |
| LXI | LXI 1.5 (Device Spec 2016) | LAN Reset restores DHCP, ping, mDNS and clears the web password (UM p.289) |

Emulation: Utility > Menu > I/O > Emulation set to "Tektronix" switches the
SCPI set to a Tek-compatible one (UM p.291). Leave it at Siglent for anything
in this file.

PyVISA setup that suits waveform transfers (PG p.837):

```python
import pyvisa
rm = pyvisa.ResourceManager()            # or ResourceManager('@py')
sds = rm.open_resource("TCPIP0::192.168.1.50::INSTR")
sds.timeout = 10000                      # ms, per read; a 10 Mpt WORD piece is 20 MB (~2 s on 100M LAN)
sds.chunk_size = 20 * 1024 * 1024
sds.write_termination = "\n"
# Leave read_termination unset: with it set, VISA stops binary reads at the
# first 0x0A byte inside the waveform. Strip text replies yourself.
print(sds.query("*IDN?").strip())  # Siglent Technologies,SDS2354X HD,<serial>,<firmware>
sds.write(":FORMat:DATA DOUBle")
```

`*IDN?` returns `Siglent Technologies,<model>,<serial>,<firmware>` (PG p.30).
Parse by comma, and match the model on "SDS2" and "HD" rather than an exact
string (whether there is a space before "HD" is not documented).

The PG's Python socket example sleeps 1 s and does one `recv(4096)` (PG
p.833). That is fine for `*IDN?` and fails on any waveform; read binary
replies by the block header (section 18).

## 4. SCPI conventions, synchronisation and errors

- Tree syntax with `:` separators. Short form is all the capitals of each
  keyword: `:CHANnel1:SCALe?` = `:CHAN1:SCAL?`. A few short forms are odd:
  `:HISTORy` is `HISTOR`, `:MTESt` is `MTES` (PG p.328, 384).
- Watch collisions: `FUNC1:INT...` is INTegrate and `FUNC1:INTE...` is
  INTErpolate. Use long forms in code (PG p.314-316).
- Numbers: NR1 integer, NR3 like `5.00E-02`. Unit suffixes are accepted in
  places (`100MHz`, `9600bps`). Some enumerations carry units as part of the
  token: `:TRIG:VID:FRAT 50Hz`, UART `BAUD 115200bps`.
- Strings in double quotes. The scope **converts strings to upper case** and a
  `"` cannot be escaped inside one (PG p.27). Labels are therefore upper case.
- Booleans: send `ON|OFF`. Replies are `ON|OFF`. LIN error enables use `0|1`.
- Enumerations come back in long mixed case: `RISing`, `SINGle`, `FIFTy`.
- The scope accepts several commands per line separated by `;` (used in the
  PG's examples, UNVERIFIED for long chains).
- Sources: `C1-C4` analog, `D0-D15` digital, `F1`, `F2` math (the QS EN01C
  shows F1-F4, so newer firmware may have four), `Z1-Z4` zoomed channels
  (only while zoom is on), `ZF<x>`, `M<m>` memory waveforms, `REFA-REFD`.

Acquisition control:

| Command | Effect |
|---|---|
| `:TRIGger:RUN` / `:TRIGger:STOP` | Run / stop (no query) |
| `:TRIGger:MODE {AUTO\|NORMal\|SINGle\|FTRIG}` | FTRIG forces one frame regardless of trigger |
| `:TRIGger:STATus?` | `Arm`, `Ready`, `Auto`, `Trig'd`, `Stop`, `Roll` |
| `:ACQuire:CSWeep` | Clear Sweeps: resets averages, persistence, statistics, pass/fail counts |
| `:ACQuire:NUMACq?` | Acquisitions since the last change of any setting |
| `:AUToset` | Autoset (forces Edge trigger, UM p.91; unreliable below ~100 Hz, PG p.33) |
| `*RST` | Default setup, like the Default key |

Reliable single-shot pattern:

```
:TRIGger:MODE SINGle
poll :TRIGger:STATus?  until it returns Stop     (timeout > expected wait)
:WAVeform:SOURce C1 ... :WAVeform:DATA?
```

After `SINGle` the status passes through `Arm` (pre-trigger buffer filling)
and `Ready` before `Trig'd` and `Stop`. Poll no faster than every 50-100 ms.
For averaging, wait until `:ACQ:NUMAC?` reaches the average count.

## 5. Front panel and touch screen

Screen (UM p.39-45): menu bar on top; grid of 8 vertical x 10 horizontal
divisions; channel descriptor boxes (C1-C4, D, F1-F2, Ref) along the bottom
showing coupling/impedance, V/div, offset, bandwidth icon (20M, 200M,
anti-alias, full) and probe factor; timebase box (delay, s/div, points, Sa/s);
trigger box (source, coupling, mode, level, type, slope); dialog box on the
right. Touching a descriptor opens a quick dialog; touching again opens the
full dialog. Menu style is Embedded (grid shrinks) or Floating (dialog
overlays): Display > Menu, or `:DISPlay:MENU {EMBedded|FLOating}`.

Numeric fields: first touch assigns the field to the Universal knob; second
touch opens the keypad, which has unit keys and Max, Min, Default buttons.

Gestures: drag horizontally to move in time, vertically to move a trace;
pinch horizontally for timebase, vertically for V/div (switches to fine);
drag cursors; drag the cursor readout to move both; draw a box starting at
about 45° to create a zone-trigger zone or histogram region. USB mouse and
keyboard work everywhere.

Keys and knobs (UM p.50-54):

| Control | Turn | Push / press |
|---|---|---|
| C1-C4 | | Off to on; on but inactive to active; active to off |
| Digital, Math, Ref | | Turn on and open dialog; again to turn off |
| Vertical scale (shared) | V/div of the active trace | Coarse / fine |
| Vertical position (shared) | Offset of active trace | Offset to zero |
| Horizontal scale | s/div | Zoom on; then toggle main/zoom window |
| Horizontal position | Trigger delay | Delay to zero |
| Zoom, Roll | | Toggle |
| Trigger Setup | | Trigger dialog |
| Auto / Normal / Single | | Trigger mode. **Single twice = force trigger** |
| Trigger level | Level | Level to 50%; in Slope or Window toggles upper/lower |
| Run/Stop | | Green run, red stop |
| Auto Setup | | Autoset (Edge trigger forced) |
| Cursors + knob | Move selected cursor | Next cursor |
| Universal knob | Highlighted parameter (default: intensity) | Select |
| Measure | | Measurements on/off and dialog |
| Save (print) | | Screenshot, or the type set in Utility > Save Button |
| Touch | | Touch screen on/off (lit = on) |
| Default | | Factory setup, or the saved custom default |
| Clear Sweeps | | Clears persistence, statistics, averages, pass/fail counts |
| WaveGen | | AWG dialog; lit when output is on |
| Quick Action | | User-assigned action (first press opens setup) |

Front-panel LEDs Ready and Trig'd follow the trigger state. The power key is
orange in standby, white when on (SM p.57); it does not disconnect mains
(SM p.6).

Language: Utility > Menu > System Setting > Language, or
`:SYSTem:LANGuage ENGLish` (also SCHinese, TCHinese, FRENch, JAPanese,
KORean, DEUTsch, ESPan, RUSSian, ITALiana, PORTuguese).

## 6. Vertical system

Channel dialog (UM p.58-63):

| Setting | Options | SCPI |
|---|---|---|
| On/off | | `:CHANnel<n>:SWITch {ON\|OFF}` |
| Trace visible | Acquisition continues while hidden | `:CHANnel<n>:VISible {ON\|OFF}` |
| Coupling | DC, AC (5 Hz -3 dB, DS), GND | `:CHANnel<n>:COUPling {DC\|AC\|GND}` |
| BW limit | Full, 200 MHz, 20 MHz (UM p.60-61) | `:CHANnel<n>:BWLimit {FULL\|200M\|20M}` |
| Probe | 1X, 10X, 100X, custom 1E-6 to 1E6, Probe Check | `:CHANnel<n>:PROBe {DEFault\|VALue,<x>}`; query returns the ratio only |
| Impedance | 1 MΩ, 50 Ω | `:CHANnel<n>:IMPedance {ONEMeg\|FIFTy}` |
| V/div | 0.5 mV to 10 V (1 MΩ), to 1 V (50 Ω), x probe | `:CHANnel<n>:SCALe <NR3>` |
| Offset | See table below | `:CHANnel<n>:OFFSet <NR3>` |
| Unit | V, A | `:CHANnel<n>:UNIT {V\|A}` |
| Deskew | ±100 ns | `:CHANnel<n>:SKEW <s>` |
| Invert | Display and maths only | `:CHANnel<n>:INVert {ON\|OFF}` |
| Label | Up to 20 chars, upper-cased | `:CHANnel<n>:LABel:TEXT "VOUT"` and `:CHANnel<n>:LABel ON` (query gives ON/OFF, not the text) |
| Vertical reference | What stays put when V/div changes | `:CHANnel:REFerence {OFFSet\|POSition}` (global) |

Offset range by V/div at 1X (DS): 1 MΩ: ±1.6 V (0.5-5 mV/div), ±4 V
(5.1-10 mV), ±8 V (10.2-20 mV), ±16 V (20.5-100 mV), ±80 V (102-200 mV),
±160 V (205 mV-1 V), ±400 V (1.02-10 V/div). 50 Ω: ±1.6 V, ±4 V, ±8 V as
above, then ±10 V (20.5 mV-1 V/div).

The quick dialog has Copy (copy this channel's settings to another channel)
and Apply To (make this channel the source of Trigger, FFT, Simple Measure,
Cursor, Search, DVM or Counter); the full channel dialog's Apply To adds
Histogram, Mask Test and AWG (UM p.59-61). A 10X probe with a sense pin sets
attenuation automatically. Fine V/div uses more of the ADC range and gives the
best vertical accuracy (UM p.59).

Deskew: probe one signal with both channels, then set the skew. One inch of
coax is roughly 100 ps (UM p.62). A deskewed trigger source does not move the
trigger marker.

## 7. Horizontal, acquisition, sequence, history, zoom

Timebase (UM p.71): applies to all traces except FFT. Delay 0 is screen
centre.

| SCPI | Notes |
|---|---|
| `:TIMebase:SCALe <s/div>` | 1 ns to 1000 s/div in 1-2-5 steps. Read back: it snaps |
| `:TIMebase:DELay <s>` | Range [-5000 div x scale, +5 div x scale] (PG p.473) |
| `:TIMebase:REFerence {DELay\|POSition}` | DELay keeps the delay time and zooms about screen centre; POSition keeps the trigger at its grid position |
| `:TIMebase:REFerence:POSition <0-100>` | Horizontal reference point in % of screen |
| `:TIMebase:WINDow {ON\|OFF}` | Zoom on/off |
| `:TIMebase:WINDow:SCALe`, `:WINDow:DELay` | Zoom s/div (≤ main) and position; both clamp |

Acquire dialog (Acquire > Menu, UM p.72-76):

| Setting | Options | SCPI |
|---|---|---|
| Interpolation | Sinc (sin x/x), linear (X) | `:ACQuire:INTerpolation {ON\|OFF}` (ON = sinc) |
| Acq mode | Fast (default), Slow (lower update rate) | `:ACQuire:AMODe {FAST\|SLOW}` |
| Acquisition | Normal, Peak, Average 4-1024 (PG lists to 8192), ERES 0.5-3 bits | `:ACQuire:TYPE {NORMal\|PEAK\|AVERage,<n>\|ERES,<bits>}` |
| Memory management | Auto, Fixed Sample Rate, Fixed Memory | `:ACQuire:MMANagement {AUTO\|FSRate\|FMDepth}` |
| Max memory depth | Interleaved 20k-200M; non-interleaved 10k-100M | `:ACQuire:MDEPth 20M` (token) |
| Sample rate | Settable only in FSRate | `:ACQuire:SRATe <NR3>` (clamps) |
| Display mode | YT, XY (C1 = X, C2 = Y), Roll | `:ACQuire:MODE {YT\|XY\|ROLL}` |
| Sequence | Segment count | `:ACQuire:SEQuence {ON\|OFF}`, `:ACQuire:SEQuence:COUNt <n>` |

Read-backs: `:ACQuire:POINts?` (points of the current waveform, NR3) and
`:ACQuire:SRATe?`.

`:ACQuire:RESolution` (8/10 bit) is documented for the SDS2000X Plus only.
Do not use it on the HD. The PG's AVERage list goes to 8192; the DS gives
4-1024 for the HD. Expect 1024 to be the ceiling and read back
(UNVERIFIED).

Memory management: Auto keeps the highest rate allowed by the chosen maximum
depth, Fs = points / (10 x s/div). Fixed Sample Rate keeps Fs and lets depth
follow s/div. Fixed Memory keeps depth and lets Fs follow s/div; at fast
timebases the record is longer than the screen, so stop and zoom out to see
it all. Full rate is available at full memory for timebases below 10 ms/div
(UM p.73). The best update rate comes with the shortest records.

Acquisition types: Peak keeps min and max per interval and catches pulses
down to 200 ps (UM p.74). Average is done in hardware, needs a repetitive
signal and a stable trigger, and resets on Clear Sweeps. ERES is a hardware
boxcar filter that needs neither; its -3 dB bandwidth is 0.25, 0.115, 0.055,
0.028, 0.014, 0.007 x Fs for 0.5 to 3 bits.

Roll (UM p.76): only at ≥ 50 ms/div; delay is disabled; zoom works after
Stop; Run/Stop freezes, the next Run clears and restarts.

Sequence (Acquire > Sequence, UM p.77-79): splits memory into up to 80,000
segments (the maximum shrinks with record length; 74,403 at 100 ns/div),
minimum 2 µs between triggers. Nothing is displayed until every segment is
captured; then all segments are overlaid. Step through them in History, which
adds timestamps. Use Single trigger mode.

History (Analysis > History, UM p.80-82): stores up to 80,000 past frames
automatically, with µs timestamps (AcqTime absolute from the RTC, or Delta T).

| SCPI | Notes |
|---|---|
| `:HISTORy {ON\|OFF}` | Short form `HISTOR` |
| `:HISTORy:FRAMe <n>` | Select frame; waveform queries then read that frame |
| `:HISTORy:LIST {ON[,TIME\|DELTa]\|OFF}` | Frame list |
| `:HISTORy:PLAY {BACKWards\|PAUSe\|FORWards}`, `:HISTORy:INTERval <1e-6..1 s>` | Playback |
| `:HISTORy:TIME?` | Timestamp of current frame, `hh:mm:ss.uuuuuu` string |

Zoom (UM p.83): main window top third, zoom window bottom two thirds. With
the zoom window active the knobs set zoom scale and position. Zoomed traces
Z1-Z4 can feed measurements, math, mask test and histogram.

## 8. Triggering

All triggering is digital (UM p.90). Modes: Auto (free-runs after a timeout),
Normal, Single. Press Single twice to force. States: Arm (pre-trigger buffer
filling, triggers ignored), Ready, Trig'd. If a rare but valid trigger looks
unstable in Auto, its repetition period is longer than the Auto timeout: use
Normal (UM p.89).

`:TRIGger:TYPE {EDGE|SLOPe|PULSE|VIDeo|WINDow|INTerval|DROPout|RUNT|PATTern|QUALified|NEDGe|DELay|SHOLd|IIC|SPI|UART|CAN|LIN|FLEXray|CANFd|IIS|M1553|SENT|A429}`
(PG p.484). On the HD there is no 1553B, SENT data, ARINC 429 or USB trigger
in practice: the UM has no 1553B trigger section, and `:TRIGger:SENT` has only
SOURce and THReshold.

Source support (UM p.106):

| Type | C1-C4 | D0-D15 | EXT, EXT/5, AC Line |
|---|---|---|---|
| Edge | yes | yes | yes |
| Pulse, Interval, Dropout, Pattern, Qualified, Nth Edge, Delay, Setup/Hold, Serial | yes | yes | no |
| Slope, Video, Window, Runt | yes | no | no |

Zone trigger: C1-C4 only.

Shared sub-commands, `<T>` = trigger type keyword (PG p.485-638):

| Pattern | Values (SDS2000X HD) | Present on |
|---|---|---|
| `:TRIGger:<T>:SOURce` | `C<n>`, `D<d>`; Edge also `EX`, `EX5`, `LINE` | all but Pattern, Qualified, Delay, Setup/Hold (own source commands) |
| `:TRIGger:<T>:LEVel <V>` | ±4.1 div of source scale/offset | Edge, Pulse, Video, Interval, Dropout, Nth Edge |
| `:TRIGger:<T>:HLEVel`, `:LLEVel` | HLEV ≥ LLEV | Slope, Window, Runt |
| `:TRIGger:<T>:COUPling` | `DC\|AC\|LFREJect\|HFREJect` | Edge, Slope, Pulse, Window, Interval, Dropout, Runt |
| `:TRIGger:<T>:NREJect` | `ON\|OFF` (adds hysteresis) | those plus Nth Edge |
| `:TRIGger:<T>:HOLDoff` | `OFF\|EVENts\|TIME` | Edge, Slope, Pulse, Window, Interval, Dropout, Runt, Pattern, Nth Edge |
| `:TRIGger:<T>:HLDTime` | 8 ns to 30 s | same |
| `:TRIGger:<T>:HLDEVent` | 1 to 100,000,000 | same |
| `:TRIGger:<T>:HSTart` | `LAST_TRIG\|ACQ_START` | same |
| `:TRIGger:<T>:LIMit` | `LESSthan\|GREATerthan\|INNer\|OUTer` | Slope, Pulse, Interval, Runt, Pattern, Qualified (delay types), Delay, Setup/Hold |
| `:TRIGger:<T>:TLOWer`, `:TUPPer` | 2 ns to 20 s; TUPPer minimum 3 ns for Pattern, Qualified, Delay | same |
| `:TRIGger:<T>:SLOPe` | `RISing\|FALLing` (Edge adds `ALTernate`) | Edge, Slope, Interval, Dropout, Nth Edge, Delay, Setup/Hold |
| `:TRIGger:<T>:POLarity` | `POSitive\|NEGative` | Pulse, Runt |

LESSthan uses TUPPer only; GREATerthan uses TLOWer only; INNer and OUTer use
both, with TLOWer ≤ TUPPer. Set LIMit first, and order writes so the pair never
crosses. Holdoff Events counts N qualifying events: holdoff 3 fires on the 4th
edge (UM p.107). HSTart ACQ_START starts holdoff at the first point that meets
the condition; LAST_TRIG at the previous trigger.

Trigger coupling applies to C1-C4, EXT and EXT/5 only. HFREJect is a low-pass,
LFREJect a high-pass (UM p.108).

Per-type specifics:

| Type | Unique commands and behaviour |
|---|---|
| Edge | `:TRIG:EDGE:SOUR {C<n>\|D<d>\|EX\|EX5\|LINE}`; `:TRIG:EDGE:IMPedance {ONEMeg\|FIFTy}` for EX/EX5 only; AC Line sets its own level |
| Slope | Time between crossing LLEVel and HLEVel; source analog only; `:TRIG:SLOP:SLOP {RISing\|FALLing}` |
| Pulse | Fires at the end of the pulse; `POLarity`, `LIMit`, `TLOWer`/`TUPPer` are the width |
| Video | `STANdard {NTSC\|PAL\|P720L50\|P720L60\|P1080L50\|P1080L60\|I1080L50\|I1080L60\|CUSTom}`, `SYNC {SELect\|ANY}`, `LINE <n>`, `FIELd {1\|2}` (interlaced only). Custom: `FRATe {25Hz\|30Hz\|50Hz\|60Hz}`, `LCNT 300-2000`, `FCNT {1\|2\|4\|8}`, `INTerlace {1\|2\|4\|8}`. Sync must be > 1/2 div. No coupling or holdoff |
| Window | `TYPE {ABSolute\|RELative}`; absolute uses HLEVel/LLEVel, relative CLEVel (centre) and DLEVel (half-width). Analog only |
| Interval | Time between two like edges, fires on the second |
| Dropout | `TIME <s>`, `TYPE {EDGE\|STATe}`: EDGE = no same-direction edge for TIME; STATe = no opposite edge for TIME |
| Runt | Positive runt crosses LLEVel but not HLEVel; analog only; LIMit qualifies runt width |
| Pattern | `:TRIG:PATT:INPut H,L,X,...` in order C1..C4 then D0..D15 (20 values); `:TRIG:PATT:LEVel C2,<V>` (query `:TRIG:PATT:LEV? C2` returns `C2,<V>`); `LOGic {AND\|OR\|NAND\|NOR}`; LIMit on pattern duration. All X = never triggers |
| Qualified | `TYPE {STATe\|STATE_DLY\|EDGE\|EDGE_DLY}[,{LOW\|HIGH\|RISing\|FALLing}]`; `QSource`, `QLEVel` (qualifier); `ESource`, `ELEVel`, `ESLope` (edge). LIMit only for the _DLY types |
| Nth Edge | `EDGE <1-65535>`, `IDLE <8 ns-20 s>`; fires on the Nth edge after an idle period |
| Delay | Source A is a pattern list `:TRIG:DEL:SOUR H,L,X,...` (same order as Pattern) with `LEVel C<n>,<V>` per channel; source B `SOURce2`, `LEVel2`, `SLOPe2`; LIMit on the A-to-B delay |
| Setup/Hold | `TYPE {SETup\|HOLD}`, `CSource`, `CTHReshold`, `SLOPe` (clock); `DSource`, `DTHReshold`; `LEVel {LOW\|HIGH}` is the data state, not a voltage |

UM wording conflicts on Pattern (fires on false-to-true, UM p.90; on the
falling edge of the combined signal, UM p.101) and Window (UM p.90 vs p.98).
Test before relying on the edge.

Zone trigger (Trigger > Zone, UM p.110): up to two rectangular zones drawn on
screen, each Intersect or Not Intersect; with both on, both must be satisfied.
It qualifies acquisitions that already met the hardware trigger. The PG has no
zone trigger commands.

Hardware trigger counter: the top-right frequency readout comes from the
trigger path, with 7 digits. `:TRIGger:FREQuency?` reads it (send
`:FORM:DATA CUST,7` first). It does not depend on sample rate, unlike the Freq
measurement, which is wrong below 2 samples per cycle (UM p.188).

## 9. Serial trigger and decode

Standard: I2C, SPI, UART, CAN, LIN. Licensed: FlexRay, CAN FD, I2S,
MIL-STD-1553B, SENT, Manchester. The UM also documents CAN XL and SpaceWire
decode (UM p.153-162). Manchester, CAN XL, SpaceWire and 1553B are decode
only. Two buses (Bus1, Bus2) decode at once. ARINC 429 and USB 2.0 appear in
the PG's enumerations but have no commands and are not offered on the HD.

Front panel: Trigger Setup > Type Serial > protocol, then signals (source and
threshold per line), BusConfig (rate, format) and the trigger condition.
Decode: Analysis > Decode, choose Bus1/Bus2, protocol, signals, Protocol
Config, display format (Binary, Decimal, Hex, ASCII) and the result list (1-7
lines). **Protocol Copy** copies settings between trigger and decode; nothing
syncs automatically. A red dot at the end of a bus segment means hidden
content: zoom in. The Time column is the frame start relative to the trigger.

Decode commands (PG p.136-238):

| Command | Notes |
|---|---|
| `:DECode {ON\|OFF}` | Master switch |
| `:DECode:BUS<n> {ON\|OFF}` | n = 1, 2 |
| `:DECode:BUS<n>:PROTocol {IIC\|SPI\|UART\|CAN\|LIN\|FLEXray\|CANFd\|IIS\|M1553\|SENT\|MANChester}` | Use the full `MANChester` |
| `:DECode:BUS<n>:FORMat {BINary\|DECimal\|HEX\|ASCii}` | Also the format of result queries |
| `:DECode:BUS<n>:COPY {FROMtrigger\|TOTRigger}` | FROM = trigger to decode |
| `:DECode:LIST {OFF\|D1\|D2}`, `:DECode:LIST:LINE <1-7>`, `:DECode:LIST:SCRoll <n>` | On-screen list |
| `:DECode:LIST<n>:RESult?` | Full list: header row then one LF-terminated row per frame, comma separated, with index and time |
| `:DECode:BUS<n>:RESult?` | What is drawn on the bus: `;`-separated, no time column, **truncated when the screen is busy**. Prefer LIST |

LIST result example (UART, PG p.141):
```
UART, Time, Rx, Rx Err, Tx, Tx Err
1,-93.7501us,0x4C, , ,
2,-93.7501us, , ,0x4C,
5,85.4178us,,Less Length, ,
```
Times carry engineering suffixes (`us`, `ms`); empty fields are blank or a
single space. Parse leniently.

Per-protocol decode settings (`:DECode:BUS<n>:<proto>:...`):

| Protocol | Commands |
|---|---|
| IIC | `SCLSource`, `SCLThreshold`, `SDASource`, `SDAThreshold`, `RWBit {ON\|OFF}` (include R/W bit in the address: 0x4E write shows as 0x9C) |
| SPI | `CLKSource/CLKThreshold`, `MISOSource/MISOThreshold`, `MOSISource/MOSIThreshold` (`DIS` allowed), `CSSource/CSThreshold`, `NCSSource/NCSThreshold`, `CSTYpe {CS\|NCS\|TIMeout,<100 ns-5 ms>}`, `LATChedge {RISing\|FALLing}`, `DLENgth <4-32>`, `BITorder {LSB\|MSB}` |
| UART | `RXSource/RXTHreshold`, `TXSource/TXTHreshold` (`DIS` allowed), `BAUD {600bps\|1200bps\|2400bps\|4800bps\|9600bps\|19200bps\|38400bps\|57600bps\|115200bps\|CUSTom,<300-20000000>}`, `DLENgth <5-8>`, `PARity {NONE\|ODD\|EVEN\|MARK\|SPACe}`, `STOP {1\|1.5\|2}`, `IDLE {LOW\|HIGH}`, `BITorder` |
| CAN | `SOURce`, `THReshold`, `BAUD {5kbps\|10kbps\|20kbps\|50kbps\|100kbps\|125kbps\|250kbps\|500kbps\|800kbps\|1Mbps\|CUSTom,<5000-1000000>}` |
| LIN | `SOURce`, `THReshold`, `BAUD {600bps...19200bps\|CUSTom,<n>}` |
| FLEXray | `SOURce`, `THReshold`, `BAUD {2500kbps\|5Mbps\|10Mbps\|CUSTom,<1e6-2e7>}` |
| CANFd | `SOURce`, `THReshold`, `BAUDNominal {10kbps\|25kbps\|50kbps\|100kbps\|250kbps\|1Mbps\|CUSTom,<1e4-1e6>}`, `BAUDData {500kbps\|1Mbps\|2Mbps\|5Mbps\|8Mbps\|10Mbps\|CUSTom,<1e5-1e7>}` |
| IIS | `BCLKSource/BCLKThreshold`, `WSSource/WSTHreshold`, `DSource/DTHReshold`, `AVARiant {I2S\|LJ\|RJ}`, `LATChedge`, `LCH {LOW\|HIGH}` (WS level for left), `SBIT <0-31>`, `DLENgth <1-32>`, `BITorder`, `ANNotate {ALL\|LEFT\|RIGHt}` |
| M1553 | `SOURce` (C<n> only), `UTHReshold`, `LTHReshold` (LTH ≤ UTH; raise UTH first) |
| SENT | `SOURce`, `THReshold`, `CLOCk <500 ns-300 µs>` (tick), `TOLerance <1-25 %>`, `LENGth <3-8 nibbles>`, `FORMat {NIBBles\|FSIGnal\|SSERial\|ESERial}`, `CRC {ON\|OFF}` (ON = 2010, OFF = 2008), `PPULse {ON\|OFF}`, `IDLE` |
| MANChester | `SOURce`, `THReshold`, `BAUD <500-5000000>` (bare integer), `POLarity {RISing\|FALLing}` (edge that means 1), `IDLE`, `IBITs <2-32>`, `STARt <1-32>`, `SSIZe`, `HSIZe`, `TSIZe <0-32>`, `WSIZe <2-8>`, `DSIZe <1-255>`, `DISPlay {WORD\|BIT}`, `BITorder` |

Serial trigger commands (`:TRIGger:<proto>:...`, PG p.639-745). They carry their
own sources, thresholds and rates with the same names as decode, plus:

| Protocol | Condition and fields |
|---|---|
| IIC | `CONDition {STARt\|STOP\|RESTart\|NACK\|EEPRom\|7ADDRess\|10ADDRess\|DLENgth}`, `ADDRess <0-1023, 1024 = X>`, `ALENgth {7BIT\|10BIT}`, `DATA`, `DAT2 <0-255, 256 = X>`, `DLENgth <1-12 bytes>`, `RWBit {WRITe\|READ\|ANY}`, `LIMit {EQUal\|GREaterthan\|LESSthan}` (EEPROM) |
| SPI | `TTYPe {MISO\|MOSI}`, `DLENgth <4-96 bits>`, `DATA 1,0,X,...` (command only, MSB first, count = DLENgth; set DLENgth first), `CSTYpe`, `LATChedge`, `BITorder` |
| UART | `TTYPe {RX\|TX}`, `CONDition {STARt\|STOP\|DATA\|ERRor}`, `DATA <0-255, 256 = X>`, `LIMit`, `BAUD`, `DLENgth`, `PARity`, `STOP`, `IDLE`, `BITorder` |
| CAN | `CONDition {STARt\|REMote\|ID\|ID_AND_DATA\|ERRor}`, `IDLength {11BITS\|29BITS}`, `ID`, `DATA`, `DAT2`, `BAUD` |
| LIN | `CONDition {BReak\|ID\|ID_AND_DATA\|DATA_ERROR}`, `ID <0-63, 64 = X>`, `DATA`, `DAT2`, `ERRor:CHECksum`, `ERRor:PARity`, `ERRor:SYNC {0\|1}`, `ERRor:ID`, `ERRor:DLENgth <1-8>`, `STANdard {0\|1}` (Rev 1.3 / 2.x, for checksum) |
| FLEXray | `CONDition {TSS\|FRAMe\|SYMBol\|ERRor}`, `FRAMe:ID <0-2047, 2048 = X>`, `FRAMe:CYCLe <0-63>`, `FRAMe:COMPare {ANY\|EQUal\|GREaterthan\|LESSthan}`, `FRAMe:REPetition {1\|2\|4\|8\|16\|32\|64}` (with EQUal) |
| CANFd | `FTYPe {BOTH\|CAN\|CANFd}`, `CONDition` as CAN, `ID`, `IDLength`, `DATA`, `DAT2`, `BAUDNominal`, `BAUDData` |
| IIS | `CONDition {DATA\|MUTE\|CLIP\|GLITch\|RISing\|FALLing}`, `CHANnel {LEFT\|RIGHT}`, `COMPare`, `VALue`, `DLENgth`, `AVARiant`, `LCH`, `LATChedge`, `BITorder` |
| SENT | `SOURce`, `THReshold` only; set conditions from the panel |

Front-panel-only trigger items (not in the PG): CAN FD ISO and BRS selection
and stuff-bit errors, SENT fast/slow channel conditions, I2S mute/clip
durations (1-64 frames), FlexRay header indicators and error types (UM
p.118-150).

Decode notes from the UM (p.117-162): SPI CS mode needs a complete CS edge on
screen; with Clock Timeout, set the timeout longer than the gap between clock
pulses and shorter than the gap between frames. I2C EEPROM condition looks for
control byte 1010xxx. CAN lists show Type D (data) or R (remote); 11/29-bit IDs
are detected automatically. SpaceWire needs a Sync Mode (Auto, Nulls, Pattern,
Manual) because packets have no start character.

## 10. Digital channels (MSO)

Needs SDS2000HD-16LA and the SPL2016 probe (click it in right side up; squeeze
both sides to remove). 16 channels in two threshold groups. Digital
acquisition runs at up to 500 MSa/s with 50 Mpts/ch (DS); turning digital on
can lower the analog memory depth (PG p.41).

| Setting | SCPI (PG p.239-254) |
|---|---|
| Digital on/off | `:DIGital {ON\|OFF}` |
| Channel on/off | `:DIGital:D<d> {ON\|OFF}` (d = 0-15) |
| Active channel (for knobs) | `:DIGital:ACTive D5` |
| Threshold, D0-D7 / D8-D15 | `:DIGital:THReshold1`/`THReshold2 {TTL\|CMOS\|LVCMOS33\|LVCMOS25\|CUSTom,<V>}`, custom -10 to +10 V (reconstructed range) |
| Height, position | `:DIGital:HEIGht <4-8 div>`, `:DIGital:POSition <div>` |
| Label | `:DIGital:LABel<d> "SDA"` (8 chars) |
| Deskew | `:DIGital:SKEW <±100 ns>` |
| Rate, points | `:DIGital:SRATe?`, `:DIGital:POINts?` |
| Buses 1 and 2 | `:DIGital:BUS<n>:MAP D0,D1,...` (LSB first; the count sets the width), `:DIGital:BUS<n>:FORMat {BINary\|DECimal\|UDECimal\|HEX}`, `:DIGital:BUS<n>:DISPlay {ON\|OFF}`, `:DIGital:BUS<n>:DEFault` |

Front panel: Digital key or `+ > Digital`. In the bus map, `Bit.0[D15]` means
bus bit 0 comes from D15 (UM p.70). Horizontal cursors and most horizontal
measurements work on digital traces.

## 11. Measurements, cursors, counter, DVM

### Measurements (Measure key, UM p.171-188; PG p.334-372)

Simple mode shows every basic parameter of one source. Advanced mode holds up
to 12 chosen parameters, each with its own sources, plus statistics, histogram,
trend and track. Display style M1 (up to 5 with statistics and histogram) or
M2 (up to 12, no histogram).

Per-frame values: mean-type parameters use the whole frame; period-type
parameters accumulate every occurrence but display only the first. Use
statistics or Track to see the spread within a frame (UM p.171).

| Command | Notes |
|---|---|
| `:MEASure {ON\|OFF}`, `:MEASure:MODE {SIMPle\|ADVanced}` | |
| `:MEASure:SIMPle:SOURce <src>`, `:MEASure:SIMPle:ITEM <item>,{ON\|OFF}`, `:MEASure:SIMPle:VALue? <item\|ALL>`, `:MEASure:SIMPle:CLEar` | ITEM is command only |
| `:MEASure:ADVanced:LINenumber <1-12>` | Slots shown |
| `:MEASure:ADVanced:P<n> {ON\|OFF}`, `:P<n>:TYPE <item>`, `:P<n>:SOURce1 <src>`, `:P<n>:SOURce2 <src>` | SOURce2 for two-source items (C<n> or F<x> only) |
| `:MEASure:ADVanced:P<n>:VALue?` | NR3 |
| `:MEASure:ADVanced:P<n>:STATistics? {ALL\|CURRent\|MEAN\|MAXimum\|MINimum\|STDev\|COUNt}` | Returns `OFF` when statistics are off |
| `:MEASure:ADVanced:P<n>:SHIStory? [<count>]` | `Count=5,4.2235E+00,...`; needs a finite MAXCount |
| `:MEASure:ADVanced:STATistics {ON\|OFF}`, `:STATistics:MAXCount <0-1024>` (0 = unlimited), `:STATistics:AIMLimit <n>` (1-25000 per frame), `:STATistics:RESet`, `:STATistics:HISTOGram {ON\|OFF}` | AIM limit applies only when the count is unlimited; with a finite count only the first period-type value per frame is counted |
| `:MEASure:ADVanced:STYLe {M1\|M2}`, `:MEASure:ADVanced:CLEar`, `:MEASure:RDISplay {EMBedded\|FLOating}` | |
| `:MEASure:GATE {ON\|OFF}`, `:MEASure:GATE:GA <s>`, `:GB <s>` | Gate in seconds within ±5 div of the screen; GA ≤ GB (clamps) |
| `:MEASure:THReshold:SOURce <src>`, `:TYPE {PERCent\|ABSolute}`, `:PERCent <hi>,<mid>,<lo>` (integers, 1-99), `:ABSolute <hi>,<mid>,<lo>` (V) | Per source. Select the source first |
| `:MEASure:ASTRategy {AUTO\|MANual}`, `:ASTRategy:TOP {HISTogram\|MAX}`, `:BASE {HISTogram\|MIN}` | Top/base method |
| `:MEASure:DITMe<n>:EDGE1/EDGE2 <index, -1 = last>`, `:SLOPe1/2 {RISing\|FALLing}`, `:THReshold1/2 {UPPer\|MIDDle\|LOWer}` | Delta-time items DTIMe1-4 |

Item mnemonics (PG p.343-345):

| Group | Items |
|---|---|
| Vertical | PKPK, MAX, MIN, AMPL, TOP, BASE, LEVELX (level at trigger), MEAN, CMEAN (first cycle), STDEV, VSTD (cycle), RMS, CRMS, MEDIAN, CMEDIAN, OVSP (rise overshoot), OVSN (fall overshoot), RPRE, FPRE (preshoot), ULOWer |
| Horizontal | PER, FREQ, TMAX, TMIN, PWID, NWID, DUTY, NDUTY, WID (burst width), NBWID, DELAY (trigger to first edge), TIMEL (trigger to each rising edge), RISE, FALL (user thresholds), CCJ |
| Fixed-threshold edges | RISE10T90, FALL90T10 (advanced only); RISE20T80, FALL80T20 (simple only) |
| Area and counts | PAREA, NAREA, AREA, ABSAREA, PACArea, NACArea, ACArea, ABSACArea, CYCLES, REDGES, FEDGES, EDGES, PPULSES, NPULSES, PSLOPE, NSLOPE |
| Two-source (advanced only) | PHA, SKEW, FRR, FRF, FFR, FFF (first edge of A to first edge of B), LRR, LRF, LFR, LFF (first of A to last of B), TSR, TSF (setup), THR, THF (hold), DTIMe1-4 |

Threshold-dependent items: PER, FREQ, widths, duties, DELAY, TIMEL, RISE,
FALL, CCJ, counts and all two-source items. Absolute thresholds depend on
scale, offset and probe: set those first. A threshold outside the waveform
invalidates the result (UM p.188).

Tools: Trend (value over time), Track (value against time within one frame,
capped by AIM limit), Measure Cursor (cursors mark the measured points).

### Cursors (UM p.163-170; PG p.77-135)

Modes Manual (X, Y or X+Y), Track (X cursors move, Y follow the waveform) and
Measure. Sources C1-C4, math, reference, histogram. Display M1 (labels on the
cursors) or M2 (one movable box). X reference Fixed Delay (value fixed) or
Fixed Position (screen position fixed); Y reference Fixed Offset or Fixed
Position. Push the cursor knob to cycle X1, X2, X1-X2.

The PG has two command sets and does not say which the HD uses (PG p.77):

Single group (try first):
```
:CURSor ON
:CURSor:MODE MANual,XY          (TRACk | MANual,{X|Y|XY} | MEASure)
:CURSor:SOURce1 C1
:CURSor:X1 -1.0E-06 ; :CURSor:X2 1.0E-06        (s, within the screen)
:CURSor:Y1 0.5 ; :CURSor:Y2 -0.5                 (V)
:CURSor:XDELta?  :CURSor:IXDelta?  :CURSor:YDELta?
:CURSor:MITem PKPK,C1            (Measure mode)
:CURSor:XREFerence {DELay|POSition}  :CURSor:YREFerence {OFFSet|POSition}  :CURSor:TAGStyle {FIXed|FOLLowing}
```

Multiple cursors (newer form): `:CURSor:MANual:X<n> ON`, `...:X<n>:SOURce`,
`:POSition`, `:DTCursor {MX<m>|TRACK<t>|NONE}`, `:DVALue`, `:DFOLlow`
(only after DTCursor is set), `:COLor {DEFault|DELTa|CUSTom,"#rrggbb"}`,
`:LABel`; the same for `:CURSor:MANual:Y<n>`, `:CURSor:TRACk<n>` (plus
`:TRACk<n>:VALue?`), `:CURSor:MEASure<n>:MITem`, and `:CURSor:XY:X<n>` /
`:XY:Y<n>` (XY display mode only). COLor queries return a hex string.

Delta sign conventions are inconsistent in the PG (XDELta "X2-X1", IXDelta
1/(X1-X2)); check on the unit.

### Counter (Analysis > Counter, UM p.229; PG p.63-76)

Its own function with its own source and level; the top-right readout always
follows the trigger source instead. Modes Frequency, Period, Totalizer; source
C1-C4; 7 digits. Runs while acquisition is stopped.

```
:COUNter ON
:COUNter:SOURce C1
:COUNter:MODE FREQuency                   (FREQuency | PERiod | TOTalizer)
:COUNter:LEVel 0.0                        (±4.1 div)
:COUNter:CURRent?                         -> 1.000000E+03 with :FORM:DATA CUST,7
:COUNter:STATistics ON ; :COUNter:STATistics:VALue?   -> cur,mean,min,max,stdev,count  (or OFF)
:COUNter:TOTalizer:SLOPe RISing ; :COUNter:TOTalizer:RESet
:COUNter:TOTalizer:GATE ON ; :GATE:TYPE {LEVel|AEDGe} ; :GATE:SLOPe ; :GATE:LEVel
```

Statistics work only in Frequency and Period. The totalizer gate source is
fixed in pairs: C1 and C2 gate each other, C3 and C4 gate each other (UM p.231).

### DVM (Analysis > DVM, UM p.224; PG p.270-277)

3-digit voltmeter on C1-C4, asynchronous to acquisition (works while stopped).
`:DVM ON`, `:DVM:SOURce C1`, `:DVM:MODE {DCavg|DCRMs|ACRMs|PKPK|AMPLitude}`,
`:DVM:ARANge {ON|OFF}`, `:DVM:HOLD {ON|OFF}`, `:DVM:ALARm {ON|OFF}` (beep on
overrange), `:DVM:CURRent?` (NR3, may be un-normalised like `0.98E+00`). The
panel adds bar, histogram and trend displays.

## 12. Math and FFT

Math traces F1, F2 (UM p.189; QS shows F1-F4). Operators (UM p.190-206, PG
p.322):

| Group | `:FUNCtion<x>:OPERation` token |
|---|---|
| Arithmetic | ADD, SUBTract, MULTiply, DIVision (two sources) |
| One source | IDENtity, NEGation, ABSolute, SIGN, SQRT (negative gives 0), EXP (e^x), TEN (10^x), LN, LOG (lg; negative gives 0) |
| Calculus | DIFF (`:FUNCtion<x>:DIFF:DX <n>`, 4 to record length), INTegrate (`:FUNCtion<x>:INTegrate:GATE {ON\|OFF}`, `:FUNCtion<x>:INTegrate:OFFSet <NR3>` to stop DC ramp, range ±100 display pixels; gate positions `:FUNCtion:GVALue <A>,<B>`) |
| Averaging | AVERage (`:FUNCtion<x>:AVERage:NUM`), ERES (`:FUNCtion<x>:ERES:BITS 0.5-3.0`), MAXHold, MINHold (`:...:SWeeps <0 = unlimited>`) |
| Resample | INTErpolate (`:FUNCtion<x>:INTErpolate:COEF {2\|5\|10\|20}`) |
| Filter | FILTer (`:FUNCtion<x>:FILTer:TYPe {LPASs\|HPASs\|BPASs\|BREJect}`, `:LFRequency`, `:HFRequency` (HF only for BP/BR)) |
| Spectrum | FFT |

Setup: `:FUNCtion<x>:SOURce1 C1`, `:SOURce2 C2`, `:FUNCtion<x> ON`,
`:FUNCtion<x>:SCALe`, `:POSition`, `:INVert`, `:LABel:TEXT`. Sources C<n>,
Z<n>, F<x> (not itself), M<m>. Math Average and ERES are software and slower
than the acquisition modes of the same name. The Formula Editor (UM p.206,
e.g. F1 = (C1 + C1) * C2) has no SCPI command.

Units: + and - keep V or A (U if mixed); x gives V², A² or W; / gives none, Ω
or S; d/dt V/s; ∫ V·s.

FFT (UM p.198-205; PG p.286-310):

| Item | Values | SCPI |
|---|---|---|
| Points | 1k to 2M (2^10-2^21) | `:FUNCtion<x>:FFT:POINts 2M` |
| Window | Rectangle, Hanning, Hamming, Blackman, Flattop | `:FFT:WINDow {RECTangle\|HANNing\|HAMMing\|BLACkman\|FLATtop}` |
| Mode | Normal, Max-Hold, Average 4-1024 | `:FFT:MODE {NORMal\|MAXHold\|AVERage,<n>}`, `:FFT:RESET` |
| Unit | dBVrms, Vrms, dBm (dBm uses the load) | `:FFT:UNIT {DBVrms\|Vrms\|DBm}`, `:FFT:LOAD <1-1e6 Ω>` (dBm only) |
| Vertical | Scale (0.1-20 dB/div, 1 mV-10 V/div), reference level | `:FFT:SCALe`, `:FFT:RLEVel` |
| Horizontal | Centre/span or start/stop | `:FFT:HCENter <Hz>`, `:FFT:SPAN <Hz>`, `:FFT:HSCale?` |
| Autoset | Full span, centre on peak, normal | `:FFT:AUToset {SPAN\|PEAK\|NORMal}` |
| Display | Split, full screen, exclusive | `:FUNCtion:FFTDisplay {SPLit\|FULL\|EXCLusive}` (global) |
| Peaks (up to 10) / markers (up to 8) | Threshold, excursion, sort | `:FFT:SEARch {OFF\|PEAK\|MARKer}`, `:SEARch:THReshold`, `:SEARch:EXCursion`, `:SEARch:PORDer {AMPLitude\|FREQuency}`, `:SEARch:MARKer<n> {NPeak\|NAMPlitude\|<Hz>}`, `:SEARch:MARKer<n>:SHOW`, `:SEARch:MON {PEAK\|HARMonics}`, `:SEARch:TABLe`, `:SEARch:RESult?` |

`:FUNCtion1:FFT:SEARch:RESult?` returns
`Peaks,1,9.536743E+02,2.231755E+00;2,3.099442E+03,-8.056905E+00;...` (type
word on the first record only, records end in `;`). Set UNIT before scale,
level, threshold and excursion, whose ranges follow the unit.

FFT sample rate: if the record has more points than the FFT maximum, the scope
decimates and uses the first 2 Mpts, so FFT Sa can be well below the
acquisition Sa (2 GSa/s, 10 Mpts: decimate by 4, 500 MSa/s). The Sa, Curr
(points), Δf and Avg readouts show what was used (UM p.199). Only Max works as
an automatic measurement on FFT; use peaks, markers or cursors. Window choice:
Flattop for amplitude (< 0.1 dB error), Rectangle for resolution (3.9 dB
scalloping), Hanning/Hamming in between, Blackman for low leakage (UM p.200).

## 13. Search, navigate, mask test, histogram

Search (Analysis > Search, UM p.210; PG p.414-451) marks events in the
record with white triangles. Up to 1000 events in YT (unlimited in Roll while
running). Types and SCPI:

```
:SEARch ON
:SEARch:MODE {EDGE|SLOPe|PULSE|INTerval|RUNT}
:SEARch:EDGE:SOURce C1 ; :SEARch:EDGE:SLOPe {RISing|FALLing|ALTernate} ; :SEARch:EDGE:LEVel 1.65
:SEARch:PULSe:POLarity ; :LEVel ; :LIMit {LESSthan|GREATerthan|INNer|OUTer} ; :TLOWer ; :TUPPer   (2 ns-20 s)
:SEARch:SLOPe:... and :SEARch:RUNT:... use HLEVel/LLEVel (analog sources only)
:SEARch:COUNt?            events on screen
:SEARch:EVENt?            index of the event at screen centre (stopped)
:SEARch:COPY {FROMtrigger|TOTRigger|CANCel}
```

Navigate (Analysis > Navigate, UM p.213): step by time (play at low, medium,
high speed), by search event (needs Search on and acquisition stopped; front
panel ◀ ▶ keys step events), or by history frame (with Stop on Search Event).
No SCPI.

Mask test (Analysis > Mask Test, UM p.218; PG p.383-393):

```
:MTESt ON                               enable
:MTESt:SOURce C1                        (C<n>, or Z<n> while zoomed)
:MTESt:MASK:CREate 0.32,0.32            X and Y margin, 0.08-4.00 div, around the current trace
:MTESt:MASK:LOAD EXTernal,"U-disk0/SIGLENT/test.msk"     (.msk or .smsk)
:MTESt:TYPE {ALL_IN|ALL_OUT|ANY_IN|ANY_OUT}
:MTESt:FUNCtion:SOF ON                  stop on fail
:MTESt:FUNCtion:FTH ON                  failures to History
:MTESt:FUNCtion:COF ON                  screenshot on fail (to SIGLENT/ on USB)
:MTESt:FUNCtion:BUZZer ON
:MTESt:IDISplay ON
:MTESt:OPERate ON                       start (separate from enable)
:MTESt:COUNt?                           FAIL,38176,PASS,5617,TOTAL,43793
:MTESt:RESet
```

Turning pass/fail on repurposes the rear Aux Out as the pass/fail pulse
output. Up to 14,000 tests per second (DS). Masks made with Create Mask
cannot be opened in the Mask Editor (UM p.222). The editor draws polygons by
touch or coordinates.

Histogram (Analysis > Histogram, UM p.232): horizontal, vertical or both,
inside a region drawn by gesture or set numerically; source C1-C4 (Z1-Z4
with zoom). Statistics: sum, peak, max, min, pk-pk, mean, median, mode, bin
width, sigma. No SCPI in the PG; the cursor source `HISTOGram` can read it.

## 14. Power analysis and Bode plot

### Power analysis (Analysis > Power Analysis; option SDS2000HD-PA; UM p.237-254)

Use a differential probe for voltage, a current probe, and the DF2001A
deskew fixture. No SCPI in the PG.

| Analysis | What it gives | Setup notes |
|---|---|---|
| Power Quality | P, S, Q, PF, phase; Vrms, Vpeak, V crest; Irms, Ipeak, I crest | V and I sources, number of cycles |
| Current Harmonics | First 40 harmonics, limit, margin, pass/fail, THD | Line Auto/50/60/400 Hz; IEC 61000-3-2 class A/B/C/D; bar or table |
| Inrush Current | Peak inrush at switch-on | Expected current 100 mA-500 A sets trigger (I/20) and scale (I/3); max input 1 V-1 kV sets V scale |
| Switching Loss | Power and energy over switching periods | Deskew first; voltage and current reference %; conduction model Waveform, Rds(on) or Vce(sat) |
| Slew Rate | dV/dt, dI/dt | |
| Modulation | Trend of gate-drive width, duty, period, frequency | |
| Output Ripple | Ripple, mean, min, max, σ | |
| Turn On / Turn Off | Time from input 10% to output 90% (on), input 10% to output 10% (off) | AC or DC input; duration 5 ns-20 s sets the timebase |
| Transient Response | Settling time after a load step | Output V and I, stable band, overshoot, low/high current |
| PSRR | Input/output ripple ratio vs frequency | Drives a generator like the Bode plot; hard to measure below -60 dB |
| Power Efficiency | Pout/Pin | Needs all four channels (Vin, Iin, Vout, Iout) |
| SOA | V-I trajectory against a safe-operating mask | V, I, P limits from the device datasheet; deskew first |

The setup values (expected current, max voltage, duration) overwrite V/div,
trigger level and timebase. Deskew procedure (UM p.243): demagnetise and zero
the current probe; on the DF2001A use the small loop for CP4020, CP4050,
CP4070(A) and CP5030 (two versions listed, 50 and 100 MHz), the large loop for
CP5150 and CP5500, and set switch S1 to match; differential probe on J7
(signal) and J6 (earth); power the fixture from USB; Signal > Auto Deskew.
Repeat after any probe, channel or temperature change.

### Bode plot (Analysis > Bode Plot, UM p.255-262)

Drives a Siglent SDG generator (LAN shown in the UM's Interface field) or the
SAG1021I USB module to sweep a DUT and plots gain and phase. Frequency range
10 Hz to 120 MHz (DS). The UM names only the SDG and the SAG1021I as sources;
whether the built-in FG can drive the sweep is not stated (UNVERIFIED; check
the Interface list).

- Connection: DUT input channel (C1 in the UM screenshot) and output
  channels DUT Output 1-3; channel gain Auto (re-ranges V/div during the
  sweep) or Hold; interface LAN needs Set IP, then Save, then Test.
- Sweep: Simple (fixed amplitude) or Vari-Level (up to four amplitude
  profiles edited by nodes); Continue or Single; frequency Linear (centre,
  span) or Decade (start, stop); points (50 in the screenshot); amplitude (2 V
  shown, unit Vpp or dB with reference level); offset; load (50 Ω shown).
- Display: gain as Vout (Vpp, Vrms, dBV, dBu, dBm, arbitrary dB) or Vout/Vin
  (linear or log); phase in degrees or radians; Auto-Set scaling; cursors.
- Data list saved and recalled as .csv on USB.
- Measurements (up to 5): UF, LF (upper and lower -3 dB), BW, GM (gain
  margin), PM (phase margin).

No Bode commands are in the PG. For scripted frequency response, drive the
generator yourself (the `siglent-sdg2000x` skill) and read `:MEAS:ADV`
amplitude and phase items here.

## 15. Reference waveforms, memory waveforms, save and recall

Reference (Ref key, UM p.208; PG p.399-405): four slots REFA-REFD in
non-volatile memory, source C1-C4 or math.

```
:REFA:DATA SAVE,C1        store C1 in REFA
:REFA:DATA LOAD           show       :REFA:DATA UNLoad   hide
:REFA:DATA:SOURce?        :REFA:DATA:SCALe <V/div>   :REFA:DATA:POSition <V>
:REFA:LABel:TEXT "GOLDEN" ; :REFA:LABel ON
```

Memory waveforms M<m> (PG p.373-382): import a channel, math trace or a .bin
file, with its own vertical and horizontal scale.
`:MEMory1:IMPort C1` or `:MEMory1:IMPort "U-disk0/SIGLENT/c1.bin"`,
`:MEMory1:SWITch ON`, `:MEMory1:VERTical:SCALe`, `:POSition`,
`:MEMory1:HORizontal:SCALe`, `:POSition`, `:SYNC {ON|OFF}` (follow the
source's timebase). The QS lists M1-M4 as math sources, so expect four slots
(QS p.29).

Save and recall (Utility > Save/Recall, UM p.276; PG p.394-413):

| Type | Extension | Recall? | SCPI |
|---|---|---|---|
| Setup | .xml | yes | `:SAVE:SETup INTernal,<1-10>` or `EXTernal,"<path>.xml"`; `:RECall:SETup INTernal,<n>` / `EXTernal,"<path>"` |
| Reference | .ref | yes, into REFA-D | `:SAVE:REFerence "<path>.ref",C1`; `:RECall:REFerence REFA,"<path>.ref"` |
| Image | .bmp, .jpg, .png | no | `:SAVE:IMAGe "<path>",{BMP\|JPG\|PNG},{OFF\|ON}[,{MON\|MOFF}]` (ON = inverted, white background; MON includes menus) |
| Binary | .bin | no (import as memory) | `:SAVE:BINary "<path>.bin",{C<n>\|Z<n>\|F<x>\|M<m>\|D0_D15\|ZD0_ZD15}` (source required) |
| CSV | .csv | no | `:SAVE:CSV "<path>.csv",<src>,{OFF\|ON}` (ON adds the settings header). Digital as `DIGital` (bus) or `D0_D15` (bits) |
| MATLAB | .mat | no | `:SAVE:MATLab "<path>.mat",<src>` (no FFT) |
| Default key | | | `:SAVE:DEFault {CUSTom\|FACTory}` makes the current or factory setup the Default key's |
| Factory | | | `:RECall:FDEFault` |

Paths: `local/SIGLENT/...` (internal), `U-disk0/...`, `U-disk1/...`,
`net_storage/...`. No prefix means U-disk0. Internal setup n is the file
`SDS0000n.xml`. For deep records save .bin and convert on the PC with the
FileConverter tool from the web page or file manager; CSV of 200 Mpts is slow
and huge (UM p.277). Default file names are `SDS2xx4XHD_<type>_<n>`, and the
default folder is `\SIGLENT\`.

Screenshot over the bus: `:PRINt? PNG` (or BMP; optional `,INVerted`) returns
the image. The PG example writes the raw reply straight to a file, so it is
apparently not wrapped in a block header (PG p.853, UNVERIFIED for PNG). Check
the first bytes (`BM` or `\x89PNG`) and strip anything before them.

USB sticks: flash type, FAT32 (SM p.59). The front Save key does Utility >
Save Button: screenshot by default, or any save type.

Network storage (Utility > Menu > I/O > Net Storage, UM p.290): SMB share
mounted as a drive (default I:), optional anonymous Guest login, auto-connect.
SCPI: `:SYSTem:NSTorage "//10.0.0.5/scope","user","pass",0,1,1,1,0`
(path, user, password, anonymous, auto-connect, remember path, remember user,
remember password), `:SYSTem:NSTorage:CONNect`, `:DISConnect`,
`:STATus?` (PG p.464).

## 16. Display

Display > Menu (UM p.263; PG p.255-269):

| Setting | SCPI |
|---|---|
| Vectors / dots | `:DISPlay:TYPE {VECTor\|DOT}` |
| Colour grade | `:DISPlay:COLor {ON\|OFF}` |
| Persistence | `:DISPlay:PERSistence {OFF\|100MS\|200MS\|500MS\|1S\|5S\|10S\|30S\|INFinite}` |
| Clear | `:DISPlay:CLEar` |
| Grid | `:DISPlay:GRIDstyle {FULL\|LIGHt\|NONE}` |
| Intensity, graticule, backlight | `:DISPlay:INTensity`, `:GRATicule`, `:BACKlight` (0-100) |
| Menu style, auto-hide | `:DISPlay:MENU {EMBedded\|FLOating}`, `:DISPlay:MENU:HIDE {OFF\|3S\|5S\|10S\|30S\|60S}`, `:DISPlay:HIDemenu` (hide now) |
| Axis labels | `:DISPlay:AXIS {ON\|OFF}`, `:AXIS:MODE {FIXed\|MOVing}`, `:AXIS:POSition {LEFT\|MIDDle\|RIGHt}` |

LED brightness (10-100%) and trace colours (HSL/RGB per trace) are panel-only.
`:DISPlay:TRANsparence` is for SHS handhelds only.

## 17. Waveform generator (AWG)

Option SDS2000HD-FG. Rear WaveGen BNC, one channel. Open with the WaveGen key
or Utility > Wave Gen; pressing the key does not turn the output on, touch
Output (UM p.272). DS: 25 MHz sine, 10 MHz square/pulse (1-99% duty, < 24 ns
edges), 300 kHz ramp, 5 MHz arb, noise, DC; 125 MSa/s, 14 bit, 16 kpts;
amplitude to 3 Vpp into 50 Ω (6 Vpp Hi-Z); offset ±1.5 V / ±3 V; 50 Ω output.
45 built-in arbs in tabs Common, Math, Engine, Window, Trigo; user arbs in
Stored, made with EasyWaveX.

Settings: output load (must match the real load, or amplitude and offset are
wrong), over-voltage protection (output turns off when the port sees more than
4 V ± 0.5 V), Zero Adjust (auto on CH1 only: connect the AWG to CH1 and run
it; manual on other channels to a mean within ±1 mV), Sync Out (CMOS, ≤ 10 MHz,
documented for the external SAG1021I only).

The WGEN commands are SDG syntax, not the colon tree, and always use `C1`
(PG p.764-773):

```
C1:BSWV WVTP,SINE,FRQ,1000,AMP,1,OFST,0      WVTP {SINE|SQUARE|RAMP|PULSE|NOISE|ARB|DC}
C1:BSWV DUTY,25          (square, pulse)     C1:BSWV SYM,50  (ramp)    C1:BSWV WIDTH,1e-6  (pulse)
C1:BSWV STDEV,0.1,MEAN,0  (noise)
C1:BSWV?    -> C1:BSWV WVTP,SINE,FRQ,100HZ,PERI,0.01S,AMP,2V,OFST,0V,HLEV,1V,LLEV,-1V,PHSE,0
C1:ARWV INDEX,2   or   C1:ARWV NAME,StairUp
STL? [BUILDIN|USER]     list of stored waves: M<idx>, <name>, ...
C1:OUTP ON          C1:OUTP LOAD,50   (or LOAD,HZ)     C1:OUTP? -> C1:OUTP ON,LOAD,HZ,PLRT,NOR
C1:SYNC ON          VOLTPRT ON        (over-voltage protection)
```

Replies carry unit suffixes (`100HZ`, `2V`). The ARWV index-to-name map
differs by model: read it with `STL?`. Polarity is NOR only. For wider
coverage of this syntax see the `siglent-sdg2000x` skill; the scope's
generator supports only the commands listed here.

## 18. Reading waveform data

Commands (PG p.746-763):

| Command | Notes |
|---|---|
| `:WAVeform:SOURce {C<n>\|F<x>\|D<d>}` | Selects the source for both PREamble? and DATA? |
| `:WAVeform:WIDTh {BYTE\|WORD}` | **WORD on the HD** (ADC > 8 bit) |
| `:WAVeform:BYTeorder {LSB\|MSB}` | Order of the two bytes of a WORD point. Default LSB |
| `:WAVeform:STARt <n>` | First point to send (integer, 0-based) |
| `:WAVeform:POINt <n>` | Points to send; 0 appears to mean "all" (used that way in the PG's sequence example) |
| `:WAVeform:INTerval <n>` | Send every nth point |
| `:WAVeform:MAXPoint?` | Largest piece one DATA? can return (SDS2000X Plus example: 10000000). Query it |
| `:WAVeform:PREamble?` | 346-byte binary descriptor in a block |
| `:WAVeform:DATA?` | Data in a definite-length block `#N<N digits><data>` followed by `0A 0A` |
| `:WAVeform:SEQuence <frame>,<start>` | Sequence mode: frame index (1-based), or 0 = all frames starting at `<start>` |

Block parsing: find the first `#`. The reply can carry a prefix before it (the
PG's worked example puts the first sample at byte 17, which fits a legacy
`DAT2,` header), so never assume byte 0. Then
`ndig = int(buf[i+1])`, `nbytes = int(buf[i+2:i+2+ndig])`, data =
`buf[i+2+ndig : i+2+ndig+nbytes]`. Ignore the trailing `0A 0A`, and never
`rstrip()` binary data (a data byte can be 0x0A).

Preamble offsets (bytes after the 11-byte `#9nnnnnnnnn` header; all
little-endian):

| Offset | Type | Field |
|---|---|---|
| 0x00 | char[16] | "WAVEDESC" |
| 0x20 | int16 | comm_type: 0 = BYTE, 1 = WORD |
| 0x22 | int16 | comm_order: 0 = LSB, 1 = MSB |
| 0x24 | int32 | descriptor length (346) |
| 0x3C | int32 | bytes in the data array (analog only) |
| 0x4C | char[16] | "Siglent SDS" |
| 0x74 | int32 | number of points (analog only; per frame in sequence) |
| 0x84 | int32 | first point (= WAV:STARt) |
| 0x88 | int32 | data interval (= WAV:INTerval) |
| 0x90 | int32 | read_frames: frames in this transfer (sequence) |
| 0x94 | int32 | sum_frames: frames acquired (sequence) |
| 0x9C | float32 | vertical gain, V/div, **without probe factor** |
| 0xA0 | float32 | vertical offset, V, **without probe factor** |
| 0xA4 | float32 | code_per_div |
| 0xAC | int16 | ADC bits (12 here) |
| 0xAE | int16 | sequence frame index |
| 0xB0 | float32 | sample interval, s (FFT: Hz per bin) |
| 0xB4 | float64 | horizontal offset = trigger delay, s |
| 0x144 | int16 | timebase enum (below) |
| 0x146 | int16 | coupling: 0 DC, 1 AC, 2 GND |
| 0x148 | float32 | probe attenuation |
| 0x14E | int16 | BW limit: 0 off, 1 20M, 2 200M |
| 0x158 | int16 | source: 0 = C1 ... 3 = C4 |

In sequence mode the preamble block also carries 16 bytes per frame after the
346-byte descriptor: float64 seconds, then uint8 minutes, hours, days, months,
then int16 year, then 2 padding bytes (PG p.821-822, 848-850).

Timebase enum (PG p.756): 0 = 200 ps, 1 = 500 ps, 2 = 1 ns, then 1-2-5 up to
38 = 1000 s. The PG's digital and sequence examples use a second list that
starts at 100 ps (everything shifted by one), and says enumerations differ by
model. Do not trust the enum: read `:TIMebase:SCALe?` (with `:FORM:DATA
DOUB`) and use the enum only as a cross-check.

Conversion (PG p.758-761, with the probe factor from the examples):

```
volts[i] = code[i] * (vdiv / code_per_div) * probe - offset * probe
time[i]  = delay - tdiv * 10 / 2 + (first_point + i * data_interval) * sample_interval
```

`code` is the signed value: int8 in BYTE mode, int16 in WORD mode (left
aligned, low bits zero; divide by the preamble's code_per_div, which is
already in those units). Horizontal grid is 10 divisions. The PG's examples
always start at 0 with interval 1; the `first_point` and `data_interval` terms
follow from the field definitions (UNVERIFIED). In Fixed Memory mode at fast
timebases the record is longer than the screen; check that
`points * sample_interval ≈ 10 * tdiv` before trusting the time formula, and
otherwise centre the record on the screen centre (UNVERIFIED).

Large records: if points exceed `:WAV:MAXPoint?`, set `:WAV:POINt <max>` and
read in pieces with `:WAV:STARt 0, max, 2*max, ...`. Send integers; the PG's
own Python sends floats like `10000000.0` (PG p.839).

Digital channels (`:WAV:SOUR D0`): one bit per point, LSB of each byte is the
earliest sample, the last byte zero-padded. The PG says the block header gives
the point count (2500) while the block holds 313 bytes; read what the
transport delivers and cut to `points` samples. The preamble's point fields
are "analog only": take the count from `:DIGital:POINts?`.

Math and FFT (`:WAV:SOUR F1`): time-domain math converts like an analog
channel. FFT data is 8 bytes per bin, float32 real then float32 imaginary. In
Normal mode the value is |re + j·im| in Vrms; in Max-Hold and Average the real
part already holds the magnitude. Bin frequency = i x sample_interval field.
dBVrms = 20·log10(v); dBm = 10·log10(v²/R/1 mW) with R from `:FFT:LOAD?`
(PG p.844).

Sequence (`:ACQ:SEQ ON`): after the capture, `:WAV:SEQ <k>,0` selects frame k
(1-based) for an ordinary read. `:WAV:SEQ 0,<start>` returns as many frames
as fit, back to back, each `points` (0x74) long; loop `start = 1, 1 +
read_frames, ...` until `sum_frames` are read, re-reading the preamble each
time for that slice's timestamps. Outside sequence mode `:WAV:SEQ?` reports
frame 4294967295 (PG p.763).

History frames: select with `:HISTORy:FRAMe <n>`, then read as usual.

The PG's Python examples do not run as printed (dict unpacked into seven
names, smart quotes, undefined variables, an FFT script that indexes an
undefined enum). Use the driver in section 22.

## 19. System, LAN, options, firmware, self-cal

| Command | Notes |
|---|---|
| `:SYSTem:REMote {ON\|OFF}` | Lock or unlock panel and touch screen |
| `:SYSTem:TOUCh {ON\|OFF}`, `:SYSTem:BUZZer {ON\|OFF}` | |
| `:SYSTem:DATE <YYYYMMDD>`, `:SYSTem:TIME <hhmmss>` | Integers, 24 h. Time zone is panel-only |
| `:SYSTem:SSAVer {OFF\|1MIN\|5MIN\|10MIN\|30MIN\|60MIN}` | Screen saver |
| `:SYSTem:PON {ON\|OFF}` | Power on when mains is applied |
| `:SYSTem:REBoot`, `:SYSTem:SHUTdown` | |
| `:SYSTem:SELFCal`, `:SYSTem:SELFCal?` | Start self-cal; poll for `DONE` (or `DOING`). Disconnect all inputs first |
| `:SYSTem:EDUMode {AUTOSet\|MEASure\|CURSor},{ON\|OFF}` | Education lock; ON means the function is allowed |
| `:SYSTem:COMMunicate:LAN:...`, `:SYSTem:COMMunicate:VNCPort` | Section 3 |
| `:SYSTem:NSTorage ...` | Section 15 |
| `:SYSTem:LANGuage <lang>` | Section 5 |
| `:SYSTem:CLOCk {EXT\|IN_ON\|IN_OFF}` | 10 MHz reference; the HD has no reference connector, so expect an error or no effect |
| `:SYSTem:MENU {ON\|OFF}` | Only for models with a menu switch |

System info: Utility > Menu > System Info (firmware, hardware, serial,
options). Auto power-on: Utility > Menu > System Setting > Auto Power On.
Reference position for knobs (Fixed Delay / Fixed Position, Fixed Offset /
Fixed Position): Utility > Menu > System Setting > Reference Pos, same as
`:TIMebase:REFerence` and `:CHANnel:REFerence`.

Firmware (UM p.293-294): copy the `.ads` file to a FAT32 USB stick, Utility >
Menu > Maintenance > Upgrade, browse, Upgrade, then Reboot. The web page can
also upgrade. Never remove power during an upgrade. The SDS2000X HD needs
1.2.0.2 or later for the PG's command set.

Self-calibration (SM p.16, UM p.297): warm up at least 30 minutes (QS says
20), disconnect every input, Utility > Menu > Maintenance > Self Calibration >
Continue. The scope ignores input until finished. Repeat when ambient changes
by more than 5 °C, or monthly, or outside 23 ± 5 °C (QS p.33). Factory
calibration is done at 23 ± 2 °C.

Quick Cal (Maintenance > Quick Cal, default off) re-runs an ADC calibration
whenever ADC temperature moves 3 °C, interrupting acquisition. Leave it off
for long captures and rare-event monitoring. A V/div or interleave change
always triggers the same background ADC calibration regardless (QS p.34).

Self Test (Maintenance > Self Test): screen colours (Single steps, Run/Stop
exits), keyboard and knobs (Run/Stop three times exits), LEDs.

Developer Options (Maintenance) is "for internal development by Siglent";
nothing else is documented.

## 20. Performance verification

From SM chapter 5. Equipment: Fluke 9500B calibrator with at least two 9530
active heads (the only equipment the SM names). Warm up scope and
calibrator 30 minutes; self-cal first if ambient has moved more than 5 °C.
Record every reading in the test record.

Interleave mode matters for several tests: "non-interleaving" = both CH1 and
CH2 (and/or CH3 and CH4) on; "interleaving" = only one of each pair.

### 5.1 DC gain accuracy

Non-interleaved, 500 µs/div, Max Mem Depth 1M, 1 MΩ, position 0 V, measure
Mean. At each V/div apply nine DC levels, compute Verror = Vmean - Vset, and
take the slope of Verror against Vset (Excel `LINEST`): that slope is the gain
error. Then repeat interleaved at 100 µs/div, 2M, for all scales ≤ 1 V/div.

Levels: scale x [-3.75, -2.8125, -1.875, -0.9375, 0, 0.9375, 1.875, 2.8125,
3.75] above 5 mV/div; scale x [-3, -2.25, -1.5, -0.75, 0, 0.75, 1.5, 2.25, 3]
from 1 to 5 mV/div; and [-3, -2.25, -1.5, -0.888, 0, 0.888, 1.5, 2.25, 3] mV
at 1 mV/div.

Scales tested (V/div; limit ±0.6% unless noted): 10, 8.9, 7.1, 5.7, 4.5,
3.55, 2.85, 2.25, 1.8, 1.42, 1.02, 1.00, 0.86, 0.69, 0.55, 0.435, 0.345, 0.275,
0.22, 0.172, 0.138, 0.102, 0.100, 0.086, 0.069, 0.054, 0.0435, 0.0345, 0.0275,
0.022, 0.0172, 0.0138, 0.0082, 0.0070, 0.0058; ±1.5% at 4.45, 3.55, 2.80,
2.55, 1.76, 1.40, 1.00 mV/div. The odd values look like the edges of the
internal gain ranges (an inference; the SM does not say), so test them all.
SM Table 4 prints ±6.75 mV extremes at 2.55 mV/div (3 x 2.25), where its own
rule gives ±7.65 mV; follow the rule.

```python
import numpy as np
def gain_error(vset, vmeas):
    verr = np.asarray(vmeas) - np.asarray(vset)
    return np.polyfit(vset, verr, 1)[0]          # = Excel LINEST slope; 0.0036 means 0.36 %
```

SM example: nine points at 1 mV/div give 0.36% (SM p.27).

### 5.2 Offset accuracy

5 ms/div, 2M, 1 MΩ, measure Mean. At each scale set the channel offset to
each value below and the calibrator to minus that value (so the trace sits at
centre). Offset error = Vmean - Vset; the LINEST slope over five points is the
gain component (limit ±0.5%). Then offset 0 V with the calibrator off: Vzero
must be within the full-scale component, 0.5% x 8 div x scale + 1 mV.

| V/div | Offsets | Full-scale limit |
|---|---|---|
| 2 V | -200, -100, 0, 100, 200 V | ±81 mV |
| 500 mV | -160, -80, 0, 80, 160 V | ±21 mV |
| 200 mV | -80, -40, 0, 40, 80 V | ±9 mV |
| 50 mV | -16, -8, 0, 8, 16 V | ±3 mV |
| 20 mV | -8, -4, 0, 4, 8 V | ±1.8 mV |
| 10 mV | -4, -2, 0, 2, 4 V | ±1.4 mV |
| 2 mV | -1.6, -0.8, 0, 0.8, 1.6 V | ±1.08 mV |

### 5.3 DC measurement accuracy

Not tested separately: ±(gain accuracy x |Vset + offset| + offset accuracy).
Example 1 V/div, ±3 V, offset 0: limits 2.944 to 3.056 V (SM p.36).

### 5.4 Bandwidth

50 Ω at scope and calibrator, Max Mem Depth 2M, about 1 µs/div, measure
Stdev. Calibrator sine at 6 x V/div peak-to-peak; record Stdev at 1 MHz as
reference and at each frequency point; dB = 20·log10(Vstdev / Vref). Scales
10, 100, 200, 500 mV and 1 V/div. Frequency points step by about x1.145 from
1 MHz (1.00, 1.14, 1.31, 1.50, 1.72, 1.97, 2.25, 2.57, 2.95, 3.37, 3.86, 4.42,
5.06, 5.79, 6.63, 7.59, 8.69, 9.94, 11.38, 13.03, 14.91, 17.07, 19.54, 22.36,
25.60, 29.30, 33.54, 38.39, 43.94, 50.30, 57.58, 65.90, 75.44, 86.35, 98.84,
113.14, 129.51, 148.24, 169.68, 194.23, 222.33, 254.49, 291.30, 333.44,
381.67, 436.88, 500.08, 572.42, 655.22, 750.00 MHz), stopping at the model's
limit. The 100 and 200 MHz models' lists also include 100.00 and 200.00 MHz,
and the 200 MHz model's ends at 350.00 MHz (SM Table 11, p.37-38):

| Model | Up to | Response limits (dB, relative to 1 MHz) |
|---|---|---|
| SDS2104X HD | 200 MHz | ≤ 11M ±0.5; ≤ 34M ±0.8; ≤ 68M -1.2/+1.0; ≤ 101M -3.0/+1.0; ≤ 200M -65/-2.0 |
| SDS2204X HD | 350 MHz | ≤ 21M ±0.5; ≤ 68M ±0.8; ≤ 136M -1.2/+1.0; ≤ 201M -3.0/+1.0; ≤ 300M -65/+3.0 |
| SDS2354X HD | 500 MHz | ≤ 36M ±0.5; ≤ 118M ±0.8; ≤ 236M -1.2/+1.0; ≤ 351M -3.0/+1.0; ≤ 500M -5.5/+3.0 |
| SDS2504X HD | 750 MHz | ≤ 51M ±0.5; ≤ 168M ±0.8; ≤ 334M -1.2/+1.0; ≤ 501M -3.0/-1.0; ≤ 750M -65/-2.0 |

Read "-3.0/+1.0 up to the rated bandwidth" as the pass criterion. The
SDS2504X HD band to 501 MHz is printed (-3.0, -1.0), which would fail a flat
response anywhere from 334 to 501 MHz; it may be a misprint for (-3.0, +1.0)
(UNVERIFIED). The SM does not say which interleave state to use. On the
SDS2504X HD the ~350 MHz anti-alias filter is in whenever the channel's pair
is non-interleaved (UM p.42), so test that model with only one channel of the
pair on; on the other models either state should pass.

### 5.5 Timebase accuracy

10 MHz sine, 600 mV, 100 mV/div, 1 ms/div, 2 Mpts. The trigger frequency
readout (top right) must read 9.999980 to 10.000020 MHz (|error| < 20 Hz,
2 ppm). Add aging for older units (0.5 ppm first year, DS). Over SCPI:
`:FORM:DATA CUST,7` then `:TRIG:FREQ?`.

### 5.6 Trigger level (channels)

50 Ω both ends, 2 kHz 800 mV sine, 50 µs/div, 100 mV/div, DC coupling, Edge,
level +300, 0, -300 mV, rising then falling. Measure `Level@x` (LEVELX);
error = set level - reading, limit ±20 mV.

### 5.7 EXT trigger level

1 MΩ both ends, CH1 and EXT driven together with 1 kHz sine of 8 x V/div.
EXT: CH1 at 150 mV/div, level ±450 mV and 0, limit |error| < 45 mV. EXT/5: CH1
at 345 mV/div, level ±1035 mV and 0, limit < 103.5 mV. Read Level@x on CH1.

### 5.8 Trigger sensitivity

Channels: 50 Ω, AC coupling, 100 mV/div, 50 mV (as measured) sine. At 10 MHz
(50 ns/div) find a level where the trigger counter reads ≥ 9.9 MHz; at the
rated bandwidth (2 ns/div) ≥ 99% of it. Both slopes.

EXT (50 Ω): 200 mVpp at 10 MHz, level within ±100 mV; 500 mVpp at 300 MHz
within ±250 mV. EXT/5: 1 Vpp at 10 MHz within ±500 mV; 1.5 Vpp at 300 MHz
within ±750 mV. Counter ≥ 99% of the applied frequency.

### 5.9 Channel skew

Calibrator Aux > Skew function, 50 Ω, 1 kHz, 0.6 V into two channels;
100 mV/div, 2 ns/div, trigger on one of them; Skew measurement. Limit
|skew| ≤ 100 ps. Repeat for each pair.

### 5.10 Input impedance

Calibrator resistance and capacitance measurement functions.

| Input | Setting | Limit |
|---|---|---|
| CH, AC 1 MΩ, 100 mV/div | resistance | 1.176 to 1.224 MΩ |
| CH, AC 1 MΩ, 200 mV and 2 V/div; DC 1 MΩ | resistance | 0.98 to 1.02 MΩ |
| CH, 50 Ω (AC or DC) | resistance | 49.5 to 50.5 Ω |
| CH, 1 MΩ | capacitance | 14 to 18 pF |
| EXT 1 MΩ / 50 Ω | resistance | 0.98-1.02 MΩ / 49.5-50.5 Ω |

The 1.2 MΩ reading in AC 1 MΩ at 100 mV/div is expected (SM p.46).

Interface checks (SM p.18-24): USB host (stick shows "USB flash drive
detected"), USB device and LAN (NI-MAX VISA Test Panel `*IDN?`), Pass/Fail out
(mask test C1, All In, Mask X = Y = 0.32 div, Create; move the trace out of
the mask and look for pulses on Aux Out with a second scope).

Automation outline for the DC tests (calibrator control is up to the bench):

```
:CHAN1:IMP ONEM ; :CHAN1:SCAL <v/div> ; :CHAN1:OFFS 0
:TIM:SCAL 5E-4 ; :ACQ:MMAN FMD ; :ACQ:MDEP 1M        (non-interleaved: also :CHAN2:SWIT ON)
:MEAS ON ; :MEAS:MODE ADV ; :MEAS:ADV:P1:TYPE MEAN ; :MEAS:ADV:P1:SOUR1 C1
:MEAS:ADV:STAT ON ; :MEAS:ADV:STAT:RES        then wait for COUNt ≥ 16
:MEAS:ADV:P1:STAT? MEAN
```

Use the statistics mean rather than one VALue? reading to average out noise.

## 21. Service and troubleshooting

### Hardware

Disassembly (SM ch.6; tools: screwdrivers, antistatic gloves, hex-nut tool or
long-nose pliers). Wait three minutes after unplugging; work on an ESD mat;
run an external fan over the heat sinks when the cover is off.

1. Handle (two PM4x8 under the handle) and feet (four PWM3x8 each).
2. Rear cover: six PWM3x6.
3. Rear metal cover: the BNC nut, then eight screws.
4. Back chassis module: eight PM3x6; unplug cables from the mainboard as it
   lifts.
5. Power supply (four PM3x6), fan (four PB5x30), I/O board (three PM3x6).
6. Front panel: peel the channel overlay sticker, four PM3x6 under it; unplug
   the side cable; seven screws round the front chassis; lift and unplug the
   middle cable.
7. Probe interface board (one PM3x6 and its cable), four front BNC nuts, then
   thirteen PM3x6 to free the mainboard.
8. Knobs pull off; six PC3x6 hold the keyboard; then the rubber keypad.

Power supply (SM p.62): test it in place on the frame. Unplug CN2 (low-voltage
output). CN2 pins 1-2 = +12.6 V ±0.2 V no load (12.2-12.8 V full load), pins
3-4 = common. SVR1 trims the output. Mains is on the heat sink.

Acquisition board revision C (SDY8.007.278C) rails (SM p.64):

| TP | Net | Spec |
|---|---|---|
| TP10 / TP11 | VCC12V6_A / _B | 12.2-12.8 V |
| TP12 | VCC3V3_PWR | 3.3 ±0.2 V |
| TP17 | DVCC1V0 | 1.0 ±0.05 V |
| TP19 | DVCC1V8 | 1.8 ±0.09 V |
| TP21 | DVCC1V5 | 1.5 ±0.075 V |
| TP29 | DVCC2V5 | 2.5 ±0.125 V |
| TP30 | DVCC3V3_MSO | 2.85 ±0.1 V (as printed) |
| TP34 | DVCC5V_USB | 5.0 ±0.3 V |
| TP37 | DVCC3V3 | 3.3 ±0.2 V |
| TP14 | AVCC5V_D | 5.0 ±0.3 V |
| TP39 | AVCC6V | 6.5 ±0.3 V |
| TP42 | AVCC5V | 5.0 ±0.2 V |
| TP43 | AVCC3V3_PLL | 3.3 ±0.2 V |
| TP44 | AVCC3V3 | 3.3 ±0.2 V |
| TP45 / TP48 | AVCC1V9_ADC1 / _ADC2 | 1.9 ±0.1 V |
| TP46 | AVCC12V | 11.5 ±0.5 V |
| TP49 | AVCC8V | 8.0 ±0.5 V |
| TP108 | AVEE-6V | -6.0 ±0.2 V |

Relays click at power-up when the board is alive. Clocks (SM p.68): 10 MHz
±2 ppm TCXO at TP103, acquisition-clock reference TP104, PLL lock detect R772
(high = locked, not a clock), ACQ FPGA reference TP105 (LVCMOS25); 33.333 MHz
CPU reference TP95; 24 MHz USB controllers TP96, TP97, USB hub TP98, ACQ FPGA
async TP99; 25 MHz Ethernet TP100, CPLD TP101, SMP FPGA TP102, MMB FPGA TP13.
All LVCMOS33 or LVCMOS25.

LCD (SM p.70): connector J8. Pin 7 LCD ON (PWM brightness, normally high),
LVDS data pairs on pins 8/10, 11/13, 16/18, clock 19/21. If the signals are
active and the screen is dark, replace the panel; if stuck with the cable
unplugged, replace the acquisition board; otherwise the panel or LCDI board.

Fault flow (SM p.61): power supply, then acquisition (main) board, then LCD.
Required kit: DMM ±0.1% (SDM3065X or 34401A) and a 200 MHz scope.

### General problems (SM ch.7, UM p.300)

| Symptom | Checks |
|---|---|
| Dark screen | Power key colour: orange = standby (press it), none = no mains or blown fuse (factory replacement) |
| Stuck on logo | Remove USB devices and power-cycle; then power-cycle pressing Math repeatedly during boot; then wait 10 minutes and update firmware; then Siglent's USB recovery package |
| Sampled but no trace | Probe and cable; trace Visible; running and Trig'd or Auto; sensible s/div; Default, then Auto Setup |
| Baseline drifts | Fan running; vertical position works; self-cal |
| Trace with nothing connected | Power-cycle; update firmware |
| Amplitude wrong | Probe factor matches the probe; self-cal with inputs open |
| Unstable display | Trigger source is the signal's channel; aliasing (raise the sample rate); right trigger type; holdoff |
| Nothing after Run/Stop | Normal or Single with the level outside the signal: use Auto or set level to 50% |
| Touch dead | Touch key lit? Restart |
| USB stick not seen | Flash type, FAT32, works elsewhere; restart and reinsert |

Warranty: 3 years (probes and accessories 1 year, repairs 90 days) (SM p.12).

## 22. Python driver

Save as `sds2000xhd.py`. Standard library only for sockets; PyVISA only for a
VISA resource string. Tested against a mock server that follows the PG's
formats (12-bit left-aligned words, `DAT2,` prefix or none, 0x0A bytes inside
blocks, digital header giving points not bytes, sequence slices with
timestamps, FFT complex pairs). Not yet run against a real SDS2000X HD.

```python
#!/usr/bin/env python3
"""Driver and CLI for the Siglent SDS2000X HD oscilloscopes.

Written from the SDS Series Programming Guide EN11G and the SDS2000X HD user
and service manuals. Tested only against a mock server, not a real scope.

    python sds2000xhd.py 192.168.1.50 --idn
    python sds2000xhd.py 192.168.1.50 --query ":TRIG:STAT?"
    python sds2000xhd.py 192.168.1.50 --single --capture C1 c1.csv
    python sds2000xhd.py 192.168.1.50 --capture D0 d0.csv
    python sds2000xhd.py 192.168.1.50 --fft F1 fft.csv
    python sds2000xhd.py 192.168.1.50 --sequence C1 seq.csv
    python sds2000xhd.py 192.168.1.50 --screenshot screen.png
    python sds2000xhd.py USB0::0xF4EC::...::INSTR --idn     (any VISA resource)

A bare host or host:port uses a raw socket (port 5025); anything containing
"::" goes through PyVISA.
"""
from __future__ import annotations

import argparse
import math
import socket
import struct
import sys
import time

# ---------------------------------------------------------------- transports


class SocketIO:
    """Raw SCPI over TCP port 5025, newline terminated."""

    def __init__(self, host: str, port: int = 5025, timeout: float = 10.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.timeout = timeout
        self._buf = b""

    def write(self, cmd: str) -> None:
        self.sock.sendall(cmd.encode("ascii") + b"\n")

    def _recv(self, timeout: float | None = None) -> bytes:
        self.sock.settimeout(self.timeout if timeout is None else timeout)
        chunk = self.sock.recv(1 << 20)
        if not chunk:
            raise ConnectionError("instrument closed the socket")
        return chunk

    def read(self) -> str:
        self._buf = self._buf.lstrip(b"\n")
        while b"\n" not in self._buf:
            self._buf += self._recv()
            self._buf = self._buf.lstrip(b"\n")
        line, self._buf = self._buf.split(b"\n", 1)
        return line.decode("ascii", "replace").strip()

    def read_block(self, lenient: bool = False) -> bytes:
        """Read an IEEE 488.2 definite-length block, return the payload.

        lenient: stop when the scope goes quiet even if fewer bytes than the
        header promised have arrived (digital channels, PG p.760)."""
        while b"#" not in self._buf:
            self._buf += self._recv()
        i = self._buf.index(b"#")
        while len(self._buf) < i + 2:
            self._buf += self._recv()
        ndig = int(self._buf[i + 1:i + 2])
        while len(self._buf) < i + 2 + ndig:
            self._buf += self._recv()
        n = int(self._buf[i + 2:i + 2 + ndig])
        start = i + 2 + ndig
        while len(self._buf) < start + n:
            try:
                self._buf += self._recv(1.0 if lenient else None)
            except socket.timeout:
                if not lenient:
                    raise
                break
        data = self._buf[start:start + n]
        rest = self._buf[start + n:]
        if lenient and len(data) < n:
            if data.endswith(b"\n\n"):
                data = data[:-2]
            rest = b""
        self._buf = rest
        self._drain_newlines()
        return data

    def _drain_newlines(self) -> None:
        """Swallow the 0A 0A that follows a block (PG p.758)."""
        deadline = time.time() + 0.3
        while len(self._buf) < 2 and time.time() < deadline:
            try:
                self._buf += self._recv(0.1)
            except socket.timeout:
                break
        self._buf = self._buf.lstrip(b"\n")

    def read_raw(self, idle: float = 1.0) -> bytes:
        """Everything until the scope goes quiet (for :PRINt?)."""
        out, self._buf = self._buf, b""
        while True:
            try:
                out += self._recv(idle if out else None)
            except socket.timeout:
                return out

    def set_timeout(self, seconds: float) -> None:
        self.timeout = seconds

    def close(self) -> None:
        self.sock.close()


class VisaIO:
    """PyVISA transport. read_termination stays None so that binary reads do
    not stop at a 0x0A byte inside the data."""

    def __init__(self, resource: str, timeout: float = 10.0):
        import pyvisa  # only needed for VISA resources

        self.rm = pyvisa.ResourceManager()
        self.dev = self.rm.open_resource(resource)
        self.dev.write_termination = "\n"
        self.dev.read_termination = None
        self.dev.chunk_size = 20 * 1024 * 1024
        self.set_timeout(timeout)

    def write(self, cmd: str) -> None:
        self.dev.write(cmd)

    def read(self) -> str:
        return self.dev.read_raw().decode("ascii", "replace").strip()

    def read_block(self, lenient: bool = False) -> bytes:
        raw = self.dev.read_raw()
        i = raw.index(b"#")
        ndig = int(raw[i + 1:i + 2])
        n = int(raw[i + 2:i + 2 + ndig])
        start = i + 2 + ndig
        data = raw[start:start + n]
        if lenient and len(data) < n and data.endswith(b"\n\n"):
            data = data[:-2]
        return data

    def read_raw(self, idle: float = 1.0) -> bytes:
        return self.dev.read_raw()

    def set_timeout(self, seconds: float) -> None:
        self.dev.timeout = int(seconds * 1000)

    def close(self) -> None:
        self.dev.close()


def open_io(address: str, timeout: float = 10.0):
    if "::" in address:
        return VisaIO(address, timeout)
    host, _, port = address.partition(":")
    return SocketIO(host, int(port or 5025), timeout)


# ---------------------------------------------------------------- preamble

# Timebase enums printed in the PG (p.756, and p.841/847 starting at 100 ps). Used only as a cross-check.
_TDIV_A = [200e-12, 500e-12] + [m * 10.0 ** e for e in range(-9, 3) for m in (1, 2, 5)] + [1000.0]
_TDIV_B = [100e-12] + _TDIV_A

_FIELDS = {  # name: (offset, struct format)  -- PG p.754-755, little-endian
    "comm_type": (0x20, "<h"), "comm_order": (0x22, "<h"), "desc_len": (0x24, "<i"),
    "data_bytes": (0x3C, "<i"), "points": (0x74, "<i"), "first_point": (0x84, "<i"),
    "data_interval": (0x88, "<i"), "read_frames": (0x90, "<i"), "sum_frames": (0x94, "<i"),
    "vdiv": (0x9C, "<f"), "offset": (0xA0, "<f"), "code_per_div": (0xA4, "<f"),
    "adc_bits": (0xAC, "<h"), "frame_index": (0xAE, "<h"), "interval": (0xB0, "<f"),
    "delay": (0xB4, "<d"), "tdiv_enum": (0x144, "<h"), "coupling": (0x146, "<h"),
    "probe": (0x148, "<f"), "bw_limit": (0x14E, "<h"), "source": (0x158, "<h"),
}


def parse_preamble(block: bytes) -> dict:
    if not block.startswith(b"WAVEDESC"):
        raise ValueError("preamble does not start with WAVEDESC")
    p = {k: struct.unpack_from(fmt, block, off)[0] for k, (off, fmt) in _FIELDS.items()}
    desc = p["desc_len"] or 346
    stamps = []
    for j in range((len(block) - desc) // 16):  # sequence timestamps, PG p.847
        s, mi, h, d, mo, y = struct.unpack_from("<d4Bh", block, desc + 16 * j)
        stamps.append((y, mo, d, h, mi, s))
    p["timestamps"] = stamps
    return p


# ---------------------------------------------------------------- instrument


class SDS2000XHD:
    def __init__(self, address: str, timeout: float = 10.0):
        self.io = open_io(address, timeout)
        self.io.write(":FORMat:DATA DOUBle")  # 14-digit NR3 replies (default is 3)

    # basic I/O
    def write(self, cmd: str) -> None:
        self.io.write(cmd)

    def query(self, cmd: str) -> str:
        self.io.write(cmd)
        return self.io.read()

    def qfloat(self, cmd: str) -> float:
        r = self.query(cmd)
        try:
            return float(r)
        except ValueError:
            raise ValueError(f"{cmd} returned {r!r}") from None

    def idn(self) -> str:
        return self.query("*IDN?")

    def close(self) -> None:
        self.io.close()

    # acquisition
    def status(self) -> str:
        return self.query(":TRIGger:STATus?")

    def single(self, timeout: float = 30.0, poll: float = 0.1) -> None:
        """Arm one acquisition and wait for Stop (PG p.827-828 method)."""
        self.write(":TRIGger:MODE SINGle")
        time.sleep(poll)
        t_end = time.time() + timeout
        while time.time() < t_end:
            if self.status().strip().upper() == "STOP":
                return
            time.sleep(poll)
        raise TimeoutError("no trigger within %.1f s" % timeout)

    # waveform transfer
    def preamble(self, source: str) -> dict:
        self.write(f":WAVeform:SOURce {source}")
        self.write(":WAVeform:PREamble?")
        return parse_preamble(self.io.read_block())

    def _tdiv(self, p: dict) -> float:
        tdiv = self.qfloat(":TIMebase:SCALe?")
        e = p["tdiv_enum"]
        known = [t[e] for t in (_TDIV_A, _TDIV_B) if 0 <= e < len(t)]
        if known and not any(math.isclose(tdiv, k, rel_tol=1e-6) for k in known):
            print(f"note: TIM:SCAL? {tdiv:g} matches neither enum list ({known})", file=sys.stderr)
        return tdiv

    def _read_codes(self, npts: int, word: bool) -> list[int]:
        maxp = int(self.qfloat(":WAVeform:MAXPoint?"))
        self.write(f":WAVeform:POINt {min(npts, maxp)}")
        codes: list[int] = []
        start = 0
        while start < npts:
            self.write(f":WAVeform:STARt {start}")
            self.write(":WAVeform:DATA?")
            raw = self.io.read_block()
            if word:
                codes.extend(struct.unpack("<%dh" % (len(raw) // 2), raw[: len(raw) // 2 * 2]))
            else:
                codes.extend(struct.unpack("%db" % len(raw), raw))
            if not raw:
                break
            start += maxp
        return codes[:npts]

    def capture(self, source: str):
        """Return (times, values) for C<n>, F<x> (time-domain math) or D<d>."""
        src = source.upper()
        if src.startswith("D"):
            return self.capture_digital(src)
        self.write(":WAVeform:INTerval 1")
        p = self.preamble(src)
        word = p["adc_bits"] > 8
        self.write(":WAVeform:WIDTh WORD" if word else ":WAVeform:WIDTh BYTE")
        self.write(":WAVeform:BYTeorder LSB")
        codes = self._read_codes(p["points"], word)
        k = p["vdiv"] * p["probe"] / p["code_per_div"]
        off = p["offset"] * p["probe"]
        volts = [c * k - off for c in codes]
        tdiv = self._tdiv(p)
        t0 = p["delay"] - tdiv * 10 / 2
        if not math.isclose(p["points"] * p["interval"], 10 * tdiv, rel_tol=0.05):
            print("note: record length differs from the screen width; the time axis "
                  "assumes it starts at the left edge (UNVERIFIED)", file=sys.stderr)
        times = [t0 + i * p["interval"] for i in range(len(volts))]
        return times, volts

    def capture_digital(self, source: str):
        npts = int(self.qfloat(":DIGital:POINts?"))
        p = self.preamble(source)
        self.write(":WAVeform:DATA?")
        raw = self.io.read_block(lenient=True)
        bits = [(b >> n) & 1 for b in raw for n in range(8)][:npts]
        tdiv = self._tdiv(p)
        t0 = p["delay"] - tdiv * 10 / 2
        return [t0 + i * p["interval"] for i in range(len(bits))], bits

    def capture_fft(self, func: str = "F1"):
        """Return (freqs, values in the FFT unit). PG p.844."""
        n = func.upper().lstrip("F")
        unit = self.query(f":FUNCtion{n}:FFT:UNIT?").upper()
        mode = self.query(f":FUNCtion{n}:FFT:MODE?").upper()
        load = self.qfloat(f":FUNCtion{n}:FFT:LOAD?") if unit == "DBM" else 50.0
        p = self.preamble("F" + n)
        self.write(":WAVeform:DATA?")
        raw = self.io.read_block()
        freqs, vals = [], []
        for i in range(len(raw) // 8):
            re, im = struct.unpack_from("<ff", raw, 8 * i)
            v = math.hypot(re, im) if mode.startswith("NORM") else re
            if unit == "DBVRMS":
                v = 20 * math.log10(max(v, 1e-30))
            elif unit == "DBM":
                v = 10 * math.log10(max(v * v / load / 1e-3, 1e-30))
            freqs.append(i * p["interval"])
            vals.append(v)
        return freqs, vals

    def capture_sequence(self, source: str):
        """Return list of (timestamp, times, volts) for every sequence frame."""
        src = source.upper()
        self.write(f":WAVeform:SOURce {src}")
        self.write(":WAVeform:STARt 0")
        self.write(":WAVeform:POINt 0")
        self.write(":WAVeform:SEQuence 0,1")
        p = self.preamble(src)
        word = p["adc_bits"] > 8
        self.write(":WAVeform:WIDTh WORD" if word else ":WAVeform:WIDTh BYTE")
        self.write(":WAVeform:BYTeorder LSB")
        tdiv = self._tdiv(p)
        t0 = p["delay"] - tdiv * 10 / 2
        k = p["vdiv"] * p["probe"] / p["code_per_div"]
        off = p["offset"] * p["probe"]
        per, total = p["points"], p["sum_frames"]
        frames, start = [], 1
        while start <= total:
            self.write(f":WAVeform:SEQuence 0,{start}")
            ps = self.preamble(src)
            self.write(":WAVeform:DATA?")
            raw = self.io.read_block()
            n = len(raw) // 2 if word else len(raw)
            codes = struct.unpack(("<%dh" if word else "%db") % n, raw[: n * (2 if word else 1)])
            got = max(1, min(ps["read_frames"], n // per))
            for j in range(got):
                seg = codes[j * per:(j + 1) * per]
                ts = ps["timestamps"][j] if j < len(ps["timestamps"]) else None
                frames.append((ts, [t0 + i * p["interval"] for i in range(len(seg))],
                               [c * k - off for c in seg]))
            start += got
        return frames

    def screenshot(self, fmt: str = "PNG") -> bytes:
        self.write(f":PRINt? {fmt}")
        raw = self.io.read_raw()
        for magic in (b"\x89PNG", b"BM"):
            i = raw.find(magic)
            if i >= 0:
                return raw[i:]
        return raw


# ---------------------------------------------------------------- CLI


def _write_csv(path: str, header: str, cols) -> None:
    with open(path, "w", newline="") as f:
        f.write(header + "\n")
        for row in zip(*cols):
            f.write(",".join("%.9g" % v for v in row) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("address")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--idn", action="store_true")
    ap.add_argument("--send", action="append", default=[])
    ap.add_argument("--query", action="append", default=[])
    ap.add_argument("--single", action="store_true", help="arm Single and wait for Stop first")
    ap.add_argument("--capture", nargs=2, metavar=("SRC", "CSV"))
    ap.add_argument("--fft", nargs=2, metavar=("FUNC", "CSV"))
    ap.add_argument("--sequence", nargs=2, metavar=("SRC", "CSV"))
    ap.add_argument("--screenshot", metavar="FILE")
    a = ap.parse_args(argv)

    s = SDS2000XHD(a.address, a.timeout)
    try:
        if a.idn:
            print(s.idn())
        for c in a.send:
            s.write(c)
        for q in a.query:
            print(s.query(q))
        if a.single:
            s.single()
        if a.capture:
            t, v = s.capture(a.capture[0])
            _write_csv(a.capture[1], "time_s,value", (t, v))
            print(f"{len(v)} points -> {a.capture[1]}")
        if a.fft:
            f, v = s.capture_fft(a.fft[0])
            _write_csv(a.fft[1], "freq_hz,value", (f, v))
            print(f"{len(v)} bins -> {a.fft[1]}")
        if a.sequence:
            frames = s.capture_sequence(a.sequence[0])
            with open(a.sequence[1], "w") as fh:
                fh.write("frame,time_s,volts\n")
                for j, (_, t, v) in enumerate(frames, 1):
                    for ti, vi in zip(t, v):
                        fh.write("%d,%.9g,%.9g\n" % (j, ti, vi))
            print(f"{len(frames)} frames -> {a.sequence[1]}")
        if a.screenshot:
            with open(a.screenshot, "wb") as fh:
                fh.write(s.screenshot("PNG" if a.screenshot.lower().endswith("png") else "BMP"))
    finally:
        s.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

When it first meets a real scope, check: the code_per_div the preamble reports
(and that a 1 V calibrator step reads 1 V), whether `:WAV:MAXPoint?` and
`:WAV:POINt` behave as assumed, whether the "record longer than screen" note
fires in Fixed Memory mode, and whether the timebase enum note fires.

## 23. Recipes

Each assumes `import time` and `s = SDS2000XHD("192.168.1.50")` from section
22. Read back anything that matters.

Single-shot capture of a 3.3 V logic edge on C1 at full rate:

```python
for c in ("*RST", ":CHANnel2:SWITch OFF", ":CHANnel1:SWITch ON",
          ":CHANnel1:PROBe VALue,10", ":CHANnel1:IMPedance ONEMeg",
          ":CHANnel1:SCALe 1", ":CHANnel1:OFFSet -1.65",
          ":TIMebase:SCALe 20E-9", ":TIMebase:DELay 0",
          ":ACQuire:MMANagement AUTO", ":ACQuire:MDEPth 200M",
          ":TRIGger:TYPE EDGE", ":TRIGger:EDGE:SOURce C1",
          ":TRIGger:EDGE:SLOPe RISing", ":TRIGger:EDGE:LEVel 1.65"):
    s.write(c)
s.single(timeout=10)
t, v = s.capture("C1")
print(s.query(":ACQuire:SRATe?"), len(v))     # expect 2.0E+09 with C2 and C4 off
```

Rise time with statistics:

```python
for c in (":MEASure ON", ":MEASure:MODE ADVanced", ":MEASure:ADVanced:P1 ON",
          ":MEASure:ADVanced:P1:TYPE RISE10T90", ":MEASure:ADVanced:P1:SOURce1 C1",
          ":MEASure:ADVanced:STATistics ON", ":MEASure:ADVanced:STATistics:MAXCount 100",
          ":TRIGger:MODE NORMal", ":MEASure:ADVanced:STATistics:RESet"):
    s.write(c)
while float(s.query(":MEASure:ADVanced:P1:STATistics? COUNt")) < 100:
    time.sleep(0.2)
print(s.query(":MEASure:ADVanced:P1:STATistics? MEAN"),
      s.query(":MEASure:ADVanced:P1:STATistics? STDev"))
```

UART on C1 (3.3 V, 115200 8N1), trigger on byte 0x55, read the decode list:

```python
for c in (":DECode ON", ":DECode:BUS1 ON", ":DECode:BUS1:PROTocol UART",
          ":DECode:BUS1:UART:RXSource C1", ":DECode:BUS1:UART:RXTHreshold 1.65",
          ":DECode:BUS1:UART:TXSource DIS", ":DECode:BUS1:UART:BAUD 115200bps",
          ":DECode:BUS1:UART:DLENgth 8", ":DECode:BUS1:UART:PARity NONE",
          ":DECode:BUS1:UART:STOP 1", ":DECode:BUS1:UART:IDLE HIGH",
          ":DECode:BUS1:FORMat HEX", ":DECode:BUS1:COPY TOTRigger",
          ":TRIGger:TYPE UART", ":TRIGger:UART:TTYPe RX",
          ":TRIGger:UART:CONDition DATA", ":TRIGger:UART:LIMit EQUal",
          ":TRIGger:UART:DATA 85", ":DECode:LIST D1"):
    s.write(c)
s.single()
s.write(":DECode:LIST1:RESult?")
rows = s.io.read_raw().decode(errors="replace").splitlines()   # LF-separated rows
```

`:DECode:LIST1:RESult?` is multi-line, so read it raw (until the scope goes
quiet) rather than with a single-line read.

FFT with a peak table:

```python
for c in (":FUNCtion1:OPERation FFT", ":FUNCtion1:SOURce1 C1", ":FUNCtion1 ON",
          ":FUNCtion1:FFT:POINts 2M", ":FUNCtion1:FFT:WINDow FLATtop",
          ":FUNCtion1:FFT:UNIT DBVrms", ":FUNCtion1:FFT:MODE AVERage,16",
          ":FUNCtion1:FFT:HCENter 5E6", ":FUNCtion1:FFT:SPAN 10E6",
          ":FUNCtion1:FFT:SEARch PEAK", ":FUNCtion1:FFT:SEARch:THReshold -80"):
    s.write(c)
time.sleep(3)
peaks = s.query(":FUNCtion1:FFT:SEARch:RESult?").rstrip(";").split(";")
f, db = s.capture_fft("F1")
```

Mask test for 10,000 frames:

```python
for c in (":MTESt ON", ":MTESt:SOURce C1", ":MTESt:MASK:CREate 0.2,0.2",
          ":MTESt:TYPE ALL_IN", ":MTESt:FUNCtion:FTH ON", ":MTESt:RESet",
          ":TRIGger:MODE NORMal", ":MTESt:OPERate ON"):
    s.write(c)
while True:
    r = s.query(":MTESt:COUNt?").split(",")          # FAIL,n,PASS,n,TOTAL,n
    if int(r[5]) >= 10000:
        break
    time.sleep(0.5)
s.write(":MTESt:OPERate OFF")
```

Burst capture in sequence mode (500 bursts, 1 µs window each):

```python
for c in (":TIMebase:SCALe 100E-9", ":ACQuire:SEQuence ON",
          ":ACQuire:SEQuence:COUNt 500", ":ACQuire:TYPE NORMal"):
    s.write(c)
s.single(timeout=60)
frames = s.capture_sequence("C1")     # [(timestamp, t, v), ...]
```

Screen capture: `open("scr.png", "wb").write(s.screenshot("PNG"))`.

Frequency response without the Bode application: step an SDG generator (see
the `siglent-sdg2000x` skill) and read amplitude and phase here:
`:MEAS:ADV:P1:TYPE AMPL` on C1 and C2, `:MEAS:ADV:P3:TYPE PHA` with SOURce1
C1 and SOURce2 C2; set the timebase to show about five cycles at each
frequency, and use statistics means.

## 24. Manual discrepancies

| Topic | Conflict | Use |
|---|---|---|
| Math traces | UM and DS: F1-F2; QS EN01C: F1-F4 | Query `:FUNC3?`; treat F3/F4 as firmware-dependent |
| Model list | UM model table (p.11) and DS EN01A list three models; the 500 MHz model appears only in UM text (p.42) and file names; SM lists all four | Four models; the 500 MHz one may be a BW-upgraded unit |
| Warm-up | SM and UM 30 min; QS 20 min | 30 min |
| Self-cal interval | SM, UM: after > 5 °C change; QS: outside 23 ± 5 °C or monthly | Either condition |
| Average count | PG `:ACQ:TYPE` lists up to 8192; DS 4-1024 | Read back |
| Auto Setup low limit | UM 100 Hz; SM 20 Hz; PG 100 Hz | Manual setup below 100 Hz |
| Roll | UM p.52 "recommended" above 50 ms/div; UM p.76 "only" at ≥ 50 ms/div | ≥ 50 ms/div |
| Pattern trigger edge | UM p.90 false-to-true; UM p.101 true-to-false | Test |
| Window trigger | UM p.90 on leaving the window; UM p.98 on crossing either level | Test |
| SPI data length | Trigger 4-96 bits; decode 4-32 bits | As stated per function |
| `:DECode:BUS<n>:COPY` | Example text says decode to trigger for FROMtrigger | FROMtrigger = trigger to decode |
| `:DECode:LIST<n>:RESult?` | Example shows the BUS query | Use LIST |
| BITorder | Printed `{LSM\|MSB}` | LSB |
| `:TRIGger:SPI:LATChedge` | Syntax box adds `:CLK:` | No CLK node |
| Manchester polarity | Printed `PULarity` | POLarity |
| `:TRIGger:PULse:RUNT`, `:SEARch:PULse:RUNT` | Misprints for `RUNT:TUPPer` | `:TRIGger:RUNT:TUPPer` |
| CAN IDLength | Syntax `IDLENgth`, examples `IDL` | Send `IDLength` in full |
| `:SYSTem:TIME` | "8-digit", example 6 digits | hhmmss |
| `:SYSTem:DATE` | Example 20191220 vs reply 20190819 | YYYYMMDD |
| Timebase enum | Two lists (200 ps first, 100 ps first) | `:TIM:SCAL?` |
| Digital block header | Says points (2500) for a 313-byte block | Read leniently, cut to points |
| Waveform probe factor | p.758 formula omits it; examples apply it | Multiply by 0x148 |
| VIDeo LCNT table | 800 lines at 4:1 gives line 300 | 200 |
| AWG Sync Out, upgrade | Written for the external SAG1021I | Built-in may lack Sync Out |
| Bandwidth PV, SDS2504X HD | ≤ 501 MHz band printed (-3.0, -1.0) | Probably (-3.0, +1.0) |
| DC gain levels, 2.55 mV/div | Table 4 uses 3 x 2.25 mV; the rule gives 3 x 2.55 mV | ±7.65 mV |
| DVCC3V3_MSO (TP30) | Net named 3.3 V, spec 2.85 ±0.1 V | Measure and compare with a known-good board |
| Power analysis | "Power Efficiency only on 4-channel models"; all HD models have four | Available |
| I2C UM | "Date Length", 0xXX note copied from address | Data 0xXX = don't care |
| UART UM | 5-8 data bits but mentions a 9th bit as parity | Parity Mark/Space for 9-bit protocols |
| Hold vs asynchronous DVM | DVM said to run while stopped, Hold "stops acquisition" | Hold freezes the reading |