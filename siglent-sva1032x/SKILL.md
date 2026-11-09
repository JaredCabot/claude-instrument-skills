---
name: "siglent-sva1032x"
description: "Operate, program (SCPI over USB/LAN) and verify the Siglent SVA1032X/SVA1000X spectrum and vector network analyzer - VNA S11/S21, cal, DTF, TG, MA/EMI modes, PV, service."
---

# Siglent SVA1032X: operation and remote control

The SVA1032X is a 9 kHz to 3.2 GHz spectrum analyzer with a built-in tracking
generator, a vector network analyzer mode (full one-port S11, one-path S21),
distance-to-fault, modulation analysis and EMI pre-compliance modes. It is the
SSA3032X Plus hardware with the VNA added: the two service manuals carry the
same performance tests, so the spectrum-analyzer material here applies to both.

Sources:

| Document | Code | Use it for |
|---|---|---|
| User Manual SSA3000X Plus / SSA3000X-R / SVA1000X | UM0703P-E02E | Front panel, every menu, presets, system messages |
| Programming Guide (same families) | PG0703P_E02B | SCPI, all modes |
| SVA1032X Service Manual | SM0701X-E01B | Specs, performance verification, disassembly |
| SVA1000X Service Manual (SVA1015X) | SM0701X-E01A | 1.5 GHz model specs |
| SSA3015X/3021X/3032X Plus Service Manuals | E01A | Sibling hardware, same PV method |
| SSA3075X Plus Service Manual | E01A | 7.5 GHz sibling; explains the PG figures that are not SVA1032X limits |
| Quick Guide SSA3000X / SSA3000X Plus / SSA3000X-R / SVA1000X | QG0703P-E02D | Short form of the UM; adds which modes are SVA-only and EasyVSA |
| SSA/SVA/SHA IVI-C Programming Guide | E01A, Aug 2022 | IVI-C driver (SA mode only) |

The user manual, quick guide and programming guide cover the whole SVA1000X
family (SVA1015X and SVA1032X) plus the SSA3000X Plus (the quick guide also the
older SSA3000X), and the SVA1032X service manual is specific to this model. The
programming guide also carries figures from the 7.5 GHz SSA3075X Plus (EMI
frequency ranges to 7.5 GHz, for example); those are not SVA1032X limits. Some
UM tables print SVA1015X (1.5 GHz) values. Wherever the documents differ, this
skill gives the SVA1032X figures and says which source they come from.

Section 16 records what was checked on a reference unit (firmware 3.2.2.6.3R16), over USB in VNA mode. Items marked
VERIFIED come from that session. Read section 16 before sending anything to
the instrument: running the calibration over SCPI froze it so hard that it had
to be unplugged. Where the manuals disagree with each other the conflict is
listed in "Manual discrepancies". Treat anything marked UNVERIFIED as a lead
to test, and when a result on the bench contradicts this file, believe the
bench and update the skill.

## Contents

1. Instrument at a glance
2. Things that bite
3. Connecting
4. SCPI conventions and synchronisation
5. VNA mode
6. Distance-to-fault mode
7. Spectrum analyzer mode (with TG)
8. Modulation analyzer mode
9. EMI measurement mode
10. System, files, presets, options, firmware
11. IVI-C driver
12. Performance verification
13. Service, troubleshooting and system messages
14. Python driver
15. Manual discrepancies
16. Bench findings (verified on a reference unit)

## 1. Instrument at a glance

| Item | SVA1032X |
|---|---|
| SA frequency range | 9 kHz to 3.2 GHz |
| RBW / VBW | 1 Hz to 1 MHz in 1-3-10 steps; V/R ratio 0.001 to 1000 |
| Tracking generator | 100 kHz to 3.2 GHz, -20 to 0 dBm, flatness ±3 dB |
| VNA | 100 kHz to 3.2 GHz (PG ranges), 101 to 751 points (default 201), IFBW default 10 kHz, up to 4 traces |
| VNA measurements | S11 (full one-port OSL cal) and S21 (response-through normalisation). No S12/S22 |
| Phase noise | < -95 dBc/Hz at 10 kHz offset, 1 GHz carrier |
| DANL (preamp on, 1 Hz normalised) | -156 dBm 10 to 200 MHz, -161 dBm typ |
| Reference | 10 MHz, < 1 ppm initial accuracy |
| Display | 10.1 in, 1024 x 600, multi-touch |
| Power | 100 to 240 V 50/60 Hz, or 100 to 120 V 400 Hz |

Front panel connectors:

| Connector | Role | Limit |
|---|---|---|
| TG SOURCE / VNA PORT 1 (N female) | TG output; S11 port; S21 source | Reverse DC ≤ 50 V |
| RF INPUT / VNA PORT 2 (N female) | SA input; S21 receiver | ≤ +30 dBm continuous RF, ≤ 50 V DC |
| USB Host (type A) | Flash drive, Siglent USB-GPIB adapter, mouse/keyboard, Siglent ECal module | |
| 3.5 mm earphone | AM/FM demod audio | Turn volume to 0 before inserting |

Rear panel: USB Device (USBTMC remote control), LAN, 10 MHz REF IN (status bar
shows "Ext Ref" when locked; falls back to internal automatically), 10 MHz REF
OUT, TRIGGER IN (TTL 0 to 5 V, threshold about 1.5 V), Kensington slot, AC inlet
with fuse.

Modes (Mode key; the Mode key backlight is lit in any mode other than SA):
Spectrum Analyzer (default), Vector Network Analyzer, Distance-To-Fault,
Modulation Analyzer, EMI Measurement. VNA and Distance-To-Fault exist only on
the SVA1000X series, so SSA3000X Plus material never covers them. The Real-Time
Spectrum Analyzer chapters in the manuals are for the SSA3000X-R only. Each mode
has its own Preset.

Options. The reference SVA1032X has every option licensed, so all of the following
are available on it and nothing in this skill needs gating on an option check.
The names are the ones `:SYSTem:LKEY` takes and `:SYSTem:OPTions?` reports:

| Option | What it unlocks | Section |
|---|---|---|
| `VNA` | Vector Network Analyzer mode: S11, S21, Smith/polar/phase/group delay, cal, port extension | 5 |
| `DTF` | Distance-To-Fault mode (DTF and CAT views) | 6 |
| `TG` | Tracking generator in SA mode, normalisation | 7 |
| `Meas` | Advanced measurement kit in SA mode: Channel Power, ACPR, OBW, T-Power, TOI, Spectrum Monitor, CNR, Harmonics | 7 |
| `DMA` | Modulation Analyzer mode: AM/FM/PM and ASK/FSK/MSK/PSK/QAM | 8 |
| `EMI` | EMI Measurement mode, EMI filter and quasi-peak detector (QP also usable in SA mode) | 9 |

The PG's option list has no separate key for analog demodulation; on this
model the Modulation Analyzer mode covers both analog and digital. On another
unit, check `:SYSTem:OPTions?` before using a mode, and remember a new licence
takes effect only after a reboot. On firmware 3.2.2.6.3R16 this unit's
`:SYSTem:OPTions?` returns `Meas,EMI,TG,REFL,,AM,WDMA,,VNA,RTSA,` (VERIFIED),
which does not use the PG's names: there is no `DTF` or `DMA` entry, and
`REFL`, `AM`, `WDMA` and `RTSA` appear instead. Compare against that string,
not the PG's six names; if entries go missing, reload the licences with
System > System Info > Load Option or `:SYSTem:LKEY`.

Environment: 0 to 40 °C operating; ≤ 80 % RH up to 35 °C, ≤ 60 % from 35 to
40 °C; below 3 km; at least 10 cm of clear air at the sides, top and back.
Warm up 30 minutes before any accuracy-critical work.

## 2. Things that bite

1. **Select the mode before anything else.** Each mode has its own command
   tree, and the same header can mean different things in different modes.
   `:CORRection:RVELocity:COAX` takes 0.1 to 1 in VNA mode but 10 to 100 (per
   cent) in DTF mode. `:SENSe:BWIDth` is RBW in SA mode, a query-only IFBW in VNA
   mode, a query-only EQBW in MA mode and the meter RBW in EMI mode. Send
   `:INSTrument VNA` (or SA, DTF, MA), then `*OPC?`, then configure.

2. **The VNA is a one-port, one-path design.** S11 gets a full OSL calibration
   that removes directivity, source match and reflection tracking. S21 gets only
   a thru normalisation, so S21 still carries the port 1 source match and port 2
   load match errors, and there is no isolation term. The PG's entry for the
   calibration-type query notes "Enhanced Response Not added yet", but
   firmware 3.2.2.6.3R16 has Calibrate > Enhanced Response on the panel
   (VERIFIED). It asks for OPEN, SHORT and LOAD on port 1, then THRU, and
   corrects port 1's source match on S21. Port 2's load match stays
   uncorrected, and it is poor: about -5 dB return loss in VNA mode (VERIFIED,
   section 16). For better S21 on poorly matched DUTs, put a good 6 to 10 dB
   pad on the port-2 cable (and ideally port 1) and include it in the cal; the
   pad improves the effective match by twice its value at the cost of dynamic
   range. To measure S22 or S12, turn the DUT round. Measure S11 and S22 with
   the far end of the DUT in a load, not into port 2.

3. **A calibration belongs to the stimulus it was taken at.** The status flag
   top left reads `Cor` (calibrated, blue), `Off` (correction off, grey), `---`
   (no cal data) or `C?` (sweep range changed since calibration; recalibrate).
   UM table 3-1 also lists `C!` without explaining it; the quick guide's
   version of the table has only `Cor`, `Off` and `C?`.
   Calibrate with the same point count you will measure with. One-port cal is
   only offered while the trace measures S11; response-through only while it
   measures S21. After a front-panel cal, `:SENSe:CORRection:COLLect:METHod:TYPE?`
   still returns `NONE` even with `Cor` showing (VERIFIED), so that query
   cannot confirm a cal. Check the flag, or measure a standard.

4. **The user manual's VNA numbers are SVA1015X numbers.** Its VNA tables give
   10 MHz to 1.5 GHz and default stop 1.5 GHz, footnoted "different models
   have different values"; its DTF stop distance of up to 34 m is the same
   1.5 GHz figure without a footnote. The programming guide, written against a
   3.2 GHz unit, gives 100 kHz to 3.2 GHz, and the DTF distance limit scales
   with span (section 6). On an SVA1032X expect the PG figures, and read back.

5. **`:CALCulate:DATA:FDATa?` returns frequency, value pairs.** The array is
   2 x points long, but on firmware 3.2.2.6.3R16 with a scalar format (log mag,
   phase) each pair is (frequency in Hz, value), not the real and imaginary
   parts the PG describes (VERIFIED). That also gives the frequency axis
   directly: with 751 points from 1475 to 1675 MHz the frequencies came back as
   1475000000, 1475266667, ... What Smith and polar formats return is still
   UNVERIFIED; check whether they give triplets before relying on them. The
   first three points of every sweep read badly (a corrected load read -25 and
   -29 dB there against -35 to -40 dB elsewhere), so drop them.

6. **IFBW is fixed at 10 kHz; source power is settable.** On firmware
   3.2.2.6.3R16 the panel's BW > IFBW is greyed out at 10 kHz, and
   `:SENSe1:BWIDth 1 kHz`, `:SENSe1:BWIDth:RESolution 1000`, `:BWIDth 1000` and
   `:SENSe1:BANDwidth 1000` are all accepted with `*ESR?` 0 and ignored
   (VERIFIED). `:SOURce1:POWer -15` works and reads back (VERIFIED). Averaging
   (`[:SENSe]:AVERage:COUNt`, `:STATe`) is accepted and reads back.

7. **No error queue is documented.** The PG has no `:SYSTem:ERRor?`. Use
   `*ESR?` (destructive read; bit 2 query error, 3 device error, 4 execution
   error, 5 command error) after a command you care about, and read the value
   back. Out-of-range numbers are generally clamped, and unsupported commands
   can be silently ignored with `*ESR?` 0 (the IFBW commands above), so a
   read-back is the only proof a setting took.

8. **Port 2 is the spectrum analyzer front end.** It survives +30 dBm and
   50 V DC, but the SA's 1 dB compression spec is only "> -5 dBm" at the mixer
   with 0 dB input attenuation, and the PG offers no VNA receiver attenuator.
   When measuring an amplifier's S21, start at the lowest TG level (-20 dBm) and
   add an external attenuator after the DUT if its gain would push port 2
   towards -10 dBm. That -10 dBm figure is a margin chosen from the SA
   compression spec, not a published VNA limit.

9. **The PG's Python socket example hangs as written.** It calls `recv()`
   straight after `connect()` on port 5025, waiting for a banner. Raw SCPI ports
   normally send nothing until queried; use a socket timeout and do not read
   before you have written a query. Telnet (5024) is the port with a prompt.

10. **Remote locks the panel.** While under remote control the status bar shows
    Remote and keys are locked. Esc returns the instrument to local. The same
    field reads Upgrade during a firmware update. When editing a value, Esc
    clears the entry; a second Esc leaves the entry.

11. **Documented defaults are unreliable.** The PG and UM disagree on many
    defaults (marker couple, marker discrete, TG level, peak threshold, DTF
    window, demod time...). Never rely on a default in a script; set every
    parameter the measurement depends on.

## 3. Connecting

USB: connect a USB A-B cable to the rear USB Device port. The instrument
enumerates as USBTMC with no setting on the instrument. On Windows install
NI-VISA (or use pyvisa-py with libusb). Siglent's USB vendor ID is 0xF4EC.
A unit enumerates as `USB0::0xF4EC::0x1301::<serial>::0::INSTR`: product ID 0x1301, and the serial starts SSA3 because the SVA shares the SSA3000X Plus hardware. Enumerate and match on `*IDN?` rather than hard-coding the string; the VISA list may also hold other instruments and a GPIB bus, and opening the wrong resource can raise
errors such as VI_ERROR_NCIC.

LAN: System > Interface > LAN, choose DHCP or Static. Static settings take
effect only after pressing Apply. The SCPI LAN commands mention an "APPLy"
command that the PG never defines, so change a static address from the front
panel. Protocols:

| Protocol | Address | Notes |
|---|---|---|
| VXI-11 (VISA) | `TCPIP0::<ip>::INSTR` | In NI-MAX leave "LAN Device Name" blank or the connection fails |
| Raw socket | port 5025 | Newline-terminated SCPI, use for scripts |
| Telnet | port 5024 | Interactive |
| Web control | `http://<ip>` | HTML5 browser; remote panel, screenshot, firmware update |
| VNC | port 5900 to 5999 | System > Interface > Web Server sets port, password, view-only; reopen VNC after changing |

GPIB: plug the Siglent USB-GPIB adapter into the front USB Host port, set the
address under System > Interface > GPIB.

PC software: EasySpectrum (Windows, needs NI-VISA) for remote display, building
limit and correction files, and EMI pre-scan reports. EasyVSA (named in the
quick guide) records the raw RF data from Modulation Analyzer mode to the PC.
LabVIEW, MATLAB, VB and VC++ examples in the PG only show `*IDN?` over USBTMC
and TCP/IP.

```python
import pyvisa
rm = pyvisa.ResourceManager()            # ResourceManager('@py') for pyvisa-py
for r in rm.list_resources():
    try:
        d = rm.open_resource(r, timeout=2000)
        d.read_termination = d.write_termination = "\n"
        if "SVA1" in d.query("*IDN?").upper():
            sva = d
            break
    except Exception:
        pass
```

`*IDN?` returns manufacturer, model, serial and firmware (PG example:
`Siglent,SVA1015,1234567890,100.01.01.06.01`). Match on "SVA1", and parse the
fields by comma rather than by position past the model.

## 4. SCPI conventions and synchronisation

- Hierarchical, colon-separated, case-insensitive. Short form is the capital
  letters: `:DISPlay:WINDow:TRACe:Y:DLINe:STATe?` = `:DISP:WIND:TRAC:Y:DLIN:STAT?`.
- `[...]` nodes are optional: `:POWer:ATTenuation?` and
  `:SENSe:POWer:RF:ATTenuation?` are the same command.
- Booleans accept `ON|OFF|1|0`; queries answer `0|1`.
- Frequencies and times accept unit suffixes (`0.2 GHz`, `5 ms`) and are
  returned as plain Hz or s.
- Enumerations are returned in short form (`POS`, `DELT`, `MLOG`).
- VNA commands carry an optional channel number `[ch]` for E5071C compatibility.
  Only channel 1 exists: `:SENSe1:FREQuency:STARt` = `:FREQuency:STARt`.
- Strings (IP addresses, cal kit names, file names) go in double quotes.

IEEE 488.2 commands: `*IDN?`, `*RST` (preset suited to remote use), `*CLS`,
`*ESE`, `*ESR?`, `*OPC`/`*OPC?`, `*SRE` (default 255), `*STB?`, `*WAI`, `*TRG`
(restart current sweep), `*TST?`.

Sweep control, the same in SA, VNA, DTF and MA modes:

| Command | Effect |
|---|---|
| `:INITiate:CONTinuous OFF\|ON` | Single or continuous sweep |
| `:INITiate[:IMMediate]` (= `:INITiate:RESTart`) | Start/restart a sweep |
| `*OPC?` | Returns 1 when pending operations, including the sweep, are done |
| `ABORt` | Stop now, reset sweep/trigger; continuous restarts, single goes idle |
| `:INITiate:PAUSe` / `:INITiate:RESume` | SA: pause at end of sweep / resume |

The reliable acquisition pattern is single sweep, start, wait:

```
:INITiate:CONTinuous OFF
:INITiate:IMMediate
*OPC?            -> 1   (set the I/O timeout longer than the sweep, with averaging included)
:CALCulate:DATA:FDATa?   or   :TRACe:DATA? 1
```

Trace data format: `:FORMat[:TRACe][:DATA] ASCii|REAL,32|REAL,64` (also
`REAL32`, and `REAL` meaning 64-bit). Binary comes as an IEEE definite-length
block in the current Y unit; the byte order is not documented, so check it
against an ASCII read of the same trace before trusting it. ASCII is comma
separated; tolerate a trailing comma.

## 5. VNA mode

### Front panel workflow

1. Mode > Vector Network Analyzer. Preset gives S11, Log Mag, 201 points,
   IFBW 10 kHz, correction off, Z0 50 Ω, velocity factor 0.66.
2. Frequency / Span: start, stop, centre, span (min 100 Hz; no zero span).
   Sweep > Points (101 to 751). Sweep > Single or Continue.
3. Meas Setup > Meas: S11 or S21. Format: see the table below.
4. Meas Setup > Calibration:
   - Cal Kit: F503ME (Siglent N 50 Ω 3 GHz), 85032F (Keysight N 50 Ω 9 GHz),
     85032B/E, or User. Choose the gender of the standards. A kit with polarised
     connectors needs the standard class definitions to match the standards you
     actually use.
   - Calibrate > 1-Port Cal (trace measuring S11): the wizard asks for OPEN,
     SHORT and LOAD on port 1.
   - Calibrate > Response Through (trace measuring S21): connect port 1 to port
     2 through the thru adapter; the reference plane moves to the adapter ends.
   - Ecal: the optional Siglent electronic cal module on the USB host port.
   - Correction: on/off. Calibration data is saved automatically as user cal.
   - Port Extensions, System Z0, Velocity Factor (0.1 to 1, default 0.66).
5. Amplitude (Scale): Auto Scale (active trace), Auto Scale All, Scale/div
   (0.1 to 1000 dB), Ref Level (-1000 to 1000), Ref Position (0 to 10 div,
   5 = centre).
6. Trace: Num of Traces (1 to 4; each trace has its own parameter and format),
   Display (Data, Memory, Data & Mem, Off), Data -> Mem, Trace Hold (Max, Min,
   Off, Restart), Math (Data/Mem, Data*Mem, Data-Mem, Data+Mem, Off; needs
   Data -> Mem first; one math function at a time), Average (1 to 999,
   default 100 counts when on).
7. Marker: up to 4 per trace including the reference marker R (the UM and
   quick guide screen tables say 6; check on the unit). Normal, Delta, Off,
   Discrete (snap to measured points instead of interpolating), Couple (move
   markers on all traces together), All Off. Peak: Peak, Valley, Peak -> CF,
   Valley -> CF, Cont Peak, Cont Valley. Marker Fn: N dB BW (default -3 dB,
   range ±100 dB), which gives filter bandwidth directly.
8. File > Save Type CAL stores the calibration; STA stores the setup; TRC and
   CSV store trace data.

Status bar: `Cor`/`Off`/`---`/`C?` calibration flag, `P` when port extension is
on, `[M]` or `[D&M]` beside a trace showing memory display.

### Formats

| Format | SCPI token | Marker readout |
|---|---|---|
| Log magnitude (dB) | `MLOGarithmic` | dB |
| Linear magnitude | `MLINear` | unitless |
| Phase (±180°, plus expanded phase) | `PHASe` | deg, expanded deg |
| Group delay (s) | `GDELay` | s |
| SWR | `SWR` | (1+ρ)/(1-ρ) |
| Smith, Lin/Phase | `SLINear` | lin, deg |
| Smith, Log/Phase | `SLOGarithmic` | dB, deg |
| Smith, Real/Imag | `SCOMplex` | re, im |
| Smith, R+jX | `SMITh` | Ω, Ω, and L (upper half) or C (lower half) |
| Smith, G+jB | `SADMittance` | S, S, and C or L |
| Polar, Lin/Phase | `PLINear` | lin, deg |
| Polar, Log/Phase | `PLOGarithmic` | dB, deg |
| Polar, Real/Imag | `POLar` | re, im |

Smith R+jX converts reactance to a component value at the marker frequency:
L = X / (2πf) above the real axis, C = 1 / (2πf|X|) below it. G+jB does the
same from susceptance: C = B / (2πf), L = 1 / (2πf|B|).

Useful relations: return loss RL = -20 log10|Γ|; VSWR = (1+|Γ|)/(1-|Γ|);
Z = Z0 (1+Γ)/(1-Γ); mismatch loss = -10 log10(1-|Γ|²).

### Port extension

Moves the reference plane past a fixture or cable that was not in the
calibration. The UM says it compensates delay "and other possible losses",
but the menu only has delay and length, so in practice it corrects phase
and not loss.
Port length = port delay x c0 x velocity factor, c0 = 299 792 458 m/s.
Settings: Extensions on/off, Delay Port1/2, Length Port1/2, Auto Open Port1
(leave the fixture end open and let the instrument fit the delay).

### Measurement recipes

**Do not run the calibration steps below over SCPI** (section 16): on
firmware 3.2.2.6.3R16 the SVA locked up after the LOAD acquisition. Set the
stimulus over SCPI, calibrate from the front panel, then read data over SCPI.
The command sequences are kept for reference only.

S11 of an antenna or cable, calibrated at the end of the test cable:

```
:INSTrument VNA
*OPC?
:SENSe:FREQuency:STARt 100 MHz
:SENSe:FREQuency:STOP 3 GHz
:SENSe:SWEep:POINts 401
:CALCulate:PARameter1:DEFine S11
:SENSe:CORRection:COLLect:CKIT:LABel:CATalog?      -> list of kit names
:SENSe:CORRection:COLLect:CKIT:LABel "F503ME"
:SENSe:CORRection:COLLect:CKIT:GENDer Male
:SENSe:CORRection:COLLect:METHod:SOLT1 1
    (connect OPEN)   :SENSe:CORRection:COLLect:OPEN 1    *OPC?
    (connect SHORT)  :SENSe:CORRection:COLLect:SHORt 1   *OPC?
    (connect LOAD)   :SENSe:CORRection:COLLect:LOAD 1    *OPC?
:SENSe:CORRection:COLLect:SAVE
:SENSe:CORRection:COLLect:METHod:TYPE?             -> "SOLT1" (PG prints a leading space; strip it)
:CALCulate:FORMat SWR                               (or MLOG for return loss)
:CALCulate:MARKer1:STATe ON
:CALCulate:MARKer1:MINimize                         (best match)
:CALCulate:MARKer1:X?   :CALCulate:MARKer1:Y?
```

S21 of a filter, normalised through a thru:

```
:CALCulate:PARameter1:DEFine S21
:SENSe:CORRection:COLLect:METHod:THRU 1,2
    (connect THRU)   :SENSe:CORRection:COLLect:THRU 1,2   *OPC?
:SENSe:CORRection:COLLect:SAVE
:CALCulate:FORMat MLOGarithmic
:CALCulate:MARKer1:STATe ON
:CALCulate:MARKer1:MAXimum
```

The front panel N dB BW marker function gives the -3 dB bandwidth; the PG
documents no VNA-mode SCPI for it (the SA-mode
`:CALCulate:MARKer1:BANDwidth:NDB` / `:RESult?` may work, UNVERIFIED).

Two traces, S21 magnitude and phase:

```
:CALCulate:PARameter:COUNt 2
:CALCulate:PARameter1:DEFine S21
:CALCulate:PARameter1:SELect
:CALCulate:FORMat MLOGarithmic
:CALCulate:PARameter2:DEFine S21
:CALCulate:PARameter2:SELect
:CALCulate:FORMat PHASe
```

Component impedance: calibrate S11 at the cable end, fit the fixture, run
Auto Open Port1 with the fixture open, insert the part, format `SMITh`, read
R, X and L or C from the marker. Reactance accuracy is best near 50 Ω; very
small or very large impedances sit at the edge of the chart where small Γ
errors become large Z errors.

Reading data and saving Touchstone:

```
:FORMat:DATA ASCii
:CALCulate:PARameter1:SELect
:CALCulate:FORMat POLar                 (pairs become Re, Im)
:INITiate:CONTinuous OFF
:INITiate:IMMediate
*OPC?
:CALCulate:SELected:DATA:FDATa?         -> re1,im1,re2,im2,...
```

The PG describes the FDATa pairs as real and imaginary parts. With a scalar
format the second value of each pair is expected to be 0, as on the E5071C
(UNVERIFIED). Prove the complex path once by measuring the SHORT after an
S11 cal: every point should read close to -1 + j0 at low frequency. The memory
trace reads back the same way with `:CALCulate:SELected:DATA:FMEMory?`, and both
FDATa and FMEMory accept writes of a full 2 x points array.

### VNA SCPI reference

| Command | Parameters / range | Notes |
|---|---|---|
| `[:SENSe[1]]:FREQuency:STARt` | 100 kHz to 3.1999999 GHz | default 100 kHz |
| `[:SENSe[1]]:FREQuency:STOP` | 100.01 kHz to 3.2 GHz | default 3.2 GHz |
| `[:SENSe[1]]:FREQuency:CENTer` | 100.05 kHz to 3.19999995 GHz | |
| `[:SENSe[1]]:FREQuency:SPAN` | 100 Hz to 3.1999 GHz | |
| `[:SENSe[1]]:SWEep:POINts` | 101 to 751 | default 201 |
| `[:SENSe[1]]:BWIDth[:RESolution]?` | query only | IFBW, Hz |
| `:INITiate[1][:IMMediate]`, `:INITiate[1]:CONTinuous`, `ABORt` | | |
| `:DISPlay:WINDow[1]:TRACe<n>:Y[:SCALe]:AUTO` | | Auto scale trace n |
| `:DISPlay:WINDow[1]:TRACe<n>:Y[:SCALe]:RLEVel` | -1000 to 1000 (dB, or s for delay) | |
| `:DISPlay:WINDow[1]:TRACe<n>:Y[:SCALe]:PDIVision` | 0.1 to 1000 | per division |
| `:DISPlay:WINDow[1]:TRACe<n>:Y[:SCALe]:RPOSition` | 0 to 10 | default 5 |
| `:CALCulate[1]:PARameter<n>:DEFine` | `S11\|S21` | |
| `:CALCulate[1]:PARameter<n>:SELect` | | Make trace n active |
| `:CALCulate[1]:PARameter:COUNt` | 1 to 4 | |
| `:CALCulate[1][:SELected]:FORMat` | tokens in the format table | |
| `:DISPlay:WINDow[1]:TRACe<n>:STATe` | bool | data trace shown |
| `:DISPlay:WINDow[1]:TRACe<n>:MEMory[:STATe]` | bool | memory trace shown |
| `:TRACe<n>:HOLD` | `OFF\|MAX\|MIN` | |
| `:CALCulate[1][:SELected]:MATH:MEMorize` | | Data -> Mem |
| `:CALCulate[1][:SELected]:MATH:FUNCtion` | `DIVide\|MULtiply\|SUBtract\|ADD\|OFF` | |
| `:CALCulate[1][:SELected]:DATA:FDATa[?]` | 2 x points floats | formatted data |
| `:CALCulate[1][:SELected]:DATA:FMEMory[?]` | 2 x points floats | memory |
| `:FORMat[:TRACe][:DATA]` | `ASCii\|REAL,32\|REAL,64` | |
| `[:SENSe]:AVERage:TRACe<n>:COUNt` / `:STATe` | 1 to 999 / bool | per trace; STATe without n sets all |
| `[:SENSe[1]]:AVERage:COUNt` / `:STATe` | 1 to 999 / bool | all traces |
| `:CALCulate[1]:MARKer<m>:STATe` | bool | m = 1..7 per PG header |
| `:CALCulate[1]:MARKer<m>:MODE` | `POSition\|DELTa\|OFF` | |
| `:CALCulate[1]:MARKer<m>:X` / `:Y?` | 100 kHz to 3.2 GHz | marker must be on |
| `:CALCulate[1][:SELected]:MARKer:REFerence[:STATe]` | bool | Marker R; ON turns other markers to Delta |
| `:CALCulate[1][:SELected]:MARKer:DISCrete` | bool | |
| `:CALCulate[1][:SELected]:MARKer:COUPle` | bool | |
| `:CALCulate:MARKer:AOFF` | | all markers of current trace off |
| `:CALCulate:MARKer<m>:MAXimum` / `:MINimize` | | peak / valley on current trace |
| `:CALCulate:MARKer<m>:CPSearch` / `:CVSearch` | bool | continuous peak / valley |
| `:CALCulate:MARKer<m>[:SET]:STARt\|STOP\|CENTer` | | marker -> start/stop/centre |
| `:CALCulate:MARKer<m>:DELTa[:SET]:SPAN` | | delta marker -> span |
| `[:SENSe[1]]:CORRection:RVELocity:COAX` | 0.1 to 1 | velocity factor |
| `[:SENSe[1]]:CORRection:COLLect:CKIT:LABel` | `"F503ME"`, `"85032F"`, `"85036B/E"`, `"User1"`, `"User2"` | quoted |
| `[:SENSe]:CORRection:COLLect:CKIT:GENDer` | `Male\|Female` | |
| `[:SENSe[1]]:CORRection:COLLect:CKIT:LABel:CATalog?` | | installed kits |
| `[:SENSe[1]]:CORRection:COLLect:METHod:SOLT1 1` | | start one-port cal |
| `[:SENSe[1]]:CORRection:COLLect:METHod[:RESPonse]:THRU 1,2` | | start response-thru cal |
| `[:SENSe[1]]:CORRection:COLLect[:ACQuire]:OPEN\|SHORt\|LOAD 1` | | measure a standard on port 1 |
| `[:SENSe[1]]:CORRection:COLLect[:ACQuire]:THRU 1,2` | | measure the thru |
| `[:SENSe[1]]:CORRection:COLLect:SAVE` | | finish and apply the cal |
| `[:SENSe[1]]:CORRection:COLLect:CLEar` | | delete cal data |
| `[:SENSe[1]]:CORRection:COLLect:METHod:TYPE?` | `"NONE"`, `"SOLT1"`, `"RESPT"` | |
| `[:SENSe[1]]:CORRection:EXTension[:STATe]` | bool | port extension |
| `[:SENSe[1]]:CORRection:EXTension:PORT1\|2:TIME` | s | port delay |
| `[:SENSe[1]]:CORRection:EXTension:AUTO:PORT 1,ON` | | Auto Open, port 1 only |

There is no documented SCPI for correction on/off or System Z0. The E5071C
`:SENSe1:CORRection:STATe ON` is the form to try (UNVERIFIED).

## 6. Distance-to-fault mode

DTF sweeps S11 over a band and transforms it to reflection versus distance, so a
connector, kink, water ingress or a damaged antenna shows as a peak at its
distance along the cable. The Y axis is VSWR.

Span sets both reach and resolution (UM formulas, VF = velocity factor):

- Maximum distance (m) = 7.68 x 10^10 x VF / span (Hz)
- Resolution (m) = 1.5 x 10^8 x VF / span (Hz)

7.68 x 10^10 = 512 x 1.5 x 10^8 (512 times c/2), consistent with a 512-step
transform. Examples at VF 0.66:

| Span | Max distance | Resolution |
|---|---|---|
| 3.1999 GHz (full) | 15.8 m | 3.1 cm |
| 1.5 GHz | 33.8 m | 6.6 cm |
| 1 GHz | 50.7 m | 9.9 cm |
| 200 MHz | 253 m | 0.50 m |

To size the sweep for a cable of length L: span ≤ 7.68e10 x VF / L, using a
margin of 10 to 20 % on L, then check the resolution is good enough. Keep the
band inside what the cable and antenna were designed for if their in-band
behaviour is what you are testing.

Workflow:

1. Mode > Distance-To-Fault. Preset: correction on, averaging on (10), Hamming
   window, VF 0.66, metres.
2. Set start/stop frequency. Meas Setup: Start Distance (0 to stop - 0.2 m),
   Stop Distance, Unit (Meter/Feet), Velocity Factor, Cable Atten (dB/m,
   compensates peak heights for cable loss along the line; UM range 0 to
   5 dB/m), Window (Off, Rectangular, Hamming; Hamming lowers side lobes so
   the amplitude axis is more trustworthy, rectangular gives the sharpest
   distance resolution).
3. Calibrate OSL at the point where the cable under test connects (Calibration >
   Calibrate, or Ecal; choose the Cal Kit first). `C?` means the band changed.
4. Connect the cable. The screen shows Peak Value and Peak Distance for the
   worst reflection without any marker work; use Peak (marker max) and further
   markers for the others. A far-end open or short is a useful landmark to
   confirm VF: adjust VF until the marker lands on the known length.

DTF mode has no points setting in either manual, so reach and resolution are
controlled by span and velocity factor only.

The measurement type `CAT` (alongside `DTF`) is the frequency-domain view; the
PG gives it its own amplitude ranges (Ref 0.5 to 100, Scale 0.1 to 10).

DTF SCPI:

| Command | Parameters | Notes |
|---|---|---|
| `[:SENSe]:FREQuency:STARt\|STOP\|CENTer\|SPAN` | as VNA | |
| `:CALCulate:PARameter:DEFine` | `DTF\|CAT` | |
| `:CALCulate:TRANsform:DISTance:STARt` | 0 to 33.8 m | |
| `:CALCulate:TRANsform:DISTance:STOP` | 0.2 to 34 m | PG range; looks like the 1.5 GHz model's limit, real limit follows the span formula |
| `:CALCulate:TRANsform:DISTance:UNIT` | `METers\|FEET` | |
| `:CORRection:RVELocity:COAX` | 10 to 100 (per cent) | 66 = 0.66 |
| `:CORRection:LOSS:COAX` | cable attenuation | PG range -1000 to 10000, unit not stated |
| `:CALCulate:TRANsform:DISTance:WINDow` | `OFF\|RECT\|HAMM` | |
| `:DISPlay:WINDow:TRACe:Y[:SCALe]:AUTO\|RLEVel\|PDIVision` | DTF: ref -10 to 10, scale 0.01 to 10 | |
| `DISP:WINDow:TRACe:STATe`, `DISP:WINDow:TRACe:MEMory[:STATe]` | bool | |
| `:CALCulate[:SELected]:MATH:MEMorize` | | |
| `[:SENSe]:AVERage:COUNt` / `:STATe` | 1 to 999 / bool | |
| `:CALCulate:MARKer1..4:STATe\|MODE\|X\|Y?` | X in m (DTF) or Hz (CAT) | |
| `:CALCulate:MARKer1..4:MAXimum\|MINimize\|CPSearch\|CVSearch` | | |
| `:CALCulate[:SELected]:MARKer:AOFF` | | |
| `[:SENSe]:CORRection:COLLect:METHod:SOLT1 1`, `...:OPEN\|SHORt\|LOAD 1`, `...:SAVE`, `...:CLEar`, `...:METHod:TYPE?` | | OSL cal, as VNA |
| `:INITiate[:IMMediate]`, `:INITiate:CONTinuous`, `ABORt` | | |

No DTF trace-data query is documented; read peaks with markers, or try
`:CALCulate:DATA:FDATa?` (UNVERIFIED).

## 7. Spectrum analyzer mode (with TG)

### Coupling rules

- f_center = (f_start + f_stop)/2, span = f_stop - f_start. Non-zero span
  100 Hz to full; span 0 = zero span (time domain, X axis is time).
- Max reference level: Ref ≤ ATT - PA - 20 dBm (ATT input attenuation, PA
  preamp gain). Attenuator auto follows ref level and preamp.
- RBW auto tracks span; VBW auto tracks RBW via V/R ratio. Pick V/R 1 to 3 for
  CW, 10 for pulses, 0.1 for noise.
- Sweep time auto is the shortest valid time for span/RBW/VBW. A manual time
  shorter than that shows UNCAL and the readings are out of spec. Sweep Rule
  Speed (default) or Accuracy.
- Sweep mode Auto/Sweep/FFT: FFT is used for RBW 1 Hz to 10 kHz, swept for
  30 Hz to 1 MHz. Turning the TG on forces swept mode.
- Filter type Gauss (-3 dB, default) or EMI (-6 dB, RBW 200 Hz, 9 kHz, 120 kHz,
  1 MHz only). Quasi-peak detection needs the EMI filter.
- Units dBm, dBmV, dBuV, dBuA, V, W. The 75 Ω input setting only changes the
  maths; use a real 75-to-50 Ω matching pad.
- Ref Offset (±100 dB) and Freq Offset (±100 GHz) change readouts only.

### Detectors, traces, averaging

Detectors per trace: Pos Peak (default), Neg Peak, Sample (noise), Normal
(Rosenfell; alternates max/min), Average, Quasi-Peak (CISPR 16, needs EMI
filter; dwell set by QPD Dwell Time, default 50 ms). Traces A to D (yellow,
purple, light blue, green): Clear Write, Max Hold, Min Hold, View, Average
(1 to 999), Blank. Average type: Log Power (video, best for CW near noise),
Power (RMS, complex signals), Voltage (AM/pulse envelopes). Trace math:
Power Diff X-Y+offset, Power Sum, Log Offset X+offset, Log Diff X-Y-Ref.

Noise marker normalises to 1 Hz: Power average: reading - 10 log10(RBW);
Voltage: + 1.05 dB; Log power: + 2.5 dB. Use Sample or Average detector and a
non-averaged trace type for the most accurate result.

### Tracking generator and scalar network analysis

The TG output follows the sweep (centre frequency in zero span), -20 to 0 dBm,
with a level offset that changes only the readout. Normalisation:

1. TG on, connect TG SOURCE to RF INPUT through the cables you will use, wait
   one full sweep.
2. TG > Store Ref (copies the trace to the reference trace D).
3. Normalize on: the reference is subtracted each sweep and the Y unit becomes
   dB. Norm Ref Level and Norm Ref Pos (0 % bottom, 100 % top) move the trace.
4. Insert the DUT. Changing frequency or sweep time shows UNCAL: store the
   reference again.

This is scalar only. For phase, delay or a calibrated match use VNA mode.

### Markers, peak search, limits

Up to 8 markers: Normal, Delta (pair "1Δ2" with fixed reference "2+"), Fixed,
Off, Relative To, Marker Table. Marker -> CF, CF Step, Start, Stop, Ref Level,
ΔM -> Span, ΔM -> CF. Marker Fn: Noise Marker, N dB BW, Freq Counter (marker 1
only, 0.01 Hz readout), Read Out (Frequency, Period, ΔTime). Peak: Peak -> CF,
Next, Next Left/Right, Peak-Peak, Cont Peak, Peak Table (16 peaks), search
config (threshold, excursion, max/min). Signal Track follows a drifting signal
(< 3 dB amplitude change) and switches off in zero span, with TG on, in single
sweep or View, or with Cont Peak.

Limit 1 (default upper) and Limit 2 (default lower), line or up to 100 points,
X offset, Y offset, Fail-to-stop, Buzzer, X axis frequency or time (changing it
deletes the points). Amplitude correction: four tables, applied in any
combination, positive values added.

### Measurements (Meas key, advanced measurement option)

Channel Power, ACPR, Occupied BW (% or dBc method, plus transmit frequency
error), T-Power (zero span, peak/average/RMS between start and stop lines),
TOI (automatic), Spectrum Monitor (waterfall), CNR, Harmonics (up to the 10th;
fundamental must be above -50 dBm). The Reflection measurement with an
external bridge is SSA-only; on the SVA use VNA mode.

### SA SCPI reference (compact)

Frequency and span: `[:SENSe]:FREQuency:CENTer|STARt|STOP|SPAN|OFFSet`,
`:CENTer:STEP[:INCRement]`, `:CENTer:STEP:AUTO`, `:CENTer:SET:STEP`,
`:SPAN:FULL|ZERO|PREVious|HALF|DOUBle`, `[:SENSe]:FREQuency:TUNE:IMMediate`
(Auto Tune).

Amplitude: `:DISPlay:WINDow:TRACe:Y[:SCALe]:RLEVel` (dBm -100 to 30),
`[:SENSe]:POWer[:RF]:ATTenuation` (0 to 51 dB) and `:AUTO`,
`[:SENSe]:POWer[:RF]:GAIN[:STATe]` (preamp), `:DISPlay:WINDow:TRACe:Y:SCALe:RLEVel:OFFSet`,
`:UNIT:POWer DBM|DBMV|DBUV|DBUA|V|W`, `:DISPlay:WINDow:TRACe:Y[:SCALe]:SPACing LINear|LOGarithmic`,
`:DISPlay:WINDow:TRACe:Y[:SCALe]:PDIVision`, `[:SENSe]:CORRection:IMPedance[:INPut][:MAGNitude] OHM50|OHM75`.

Corrections: `[:SENSe]:CORRection:OFF`, `:CSET:ALL[:STATe]`,
`:CSET<1-4>[:STATe]`, `:CSET<n>:ADD f,a,f,a...`, `:CSET<n>:DELete <index>`,
`:CSET<n>:ALL:DELete`, `:CSET<n>:DATA[?]`.

Sweep: `[:SENSe]:SWEep:MODE AUTO|FFT|SWEep`, `[:SENSe]:SWEep:TIME` (450 µs to
1500 s) and `:AUTO`, `[:SENSe]:SWEep:SPEed NORMal|ACCUracy`,
`[:SENSe]:SWEep:COUNt` (1 to 99999, single-sweep count),
`[:SENSe]:QPD:DWELl:TIME`, `:INITiate...`, `ABORt`.

Trigger: `:TRIGger[:SEQuence]:SOURce IMMediate|VIDeo|EXTernal`,
`:TRIGger[:SEQuence]:VIDeo:LEVel` (-300 to 50 dBm),
`:TRIGger[:SEQuence]:RFBurst:SLOPe POSitive|NEGative` (external edge).

Bandwidth: `[:SENSe]:BWIDth[:RESolution]` (1 Hz to 1 MHz, rounds up to the next
step) and `:AUTO`, `[:SENSe]:BWIDth:VIDeo` and `:AUTO`,
`[:SENSe]:BWIDth:VIDeo:RATio` (0.001 to 1000 in 1-3 steps), `:RATio:CONfig?` (auto state),
`[:SENSe]:FILTer:TYPE EMI|GAUSS`.

Trace: `:TRACe<1-4>:MODE WRITe|MAXHold|MINHold|VIEW|BLANk|AVERage`,
`:TRACe[:DATA]? 1|2|3|4` (also A to D, or `:TRACe2:DATA?`),
`:FORMat[:TRACe][:DATA]`, `:CALCulate[:SELected]:MATH:FUNCtion OFF|PDIF|PSUM|LOFF|LDIF`,
`:TRACe:MATH:X|Y|Z A|B|C|D`, `:TRACe:MATH:OFFSet`,
`[:SENSe]:DETector:TRACe<n>[:FUNCtion] NEGative|POSitive|SAMPle|AVERage|NORMAL|QUASi`,
`[:SENSe]:AVERage:TYPE LOGPower|POWer|VOLTage`, `[:SENSe]:AVERage:TRACe<n>:COUNt`,
`[:SENSe]:AVERage:TRACe<n>?` (current count), `[:SENSe]:AVERage:TRACe<n>:CLEar`.

Markers (n = 1 to 8): `:CALCulate:MARKer<n>:STATe|MODE POSition|DELTa|FIXed|OFF|TRACe|X|Y?`,
`:RELative:TO:MARKer`, `:CALCulate:MARKer:AOFF`, `:CALCulate:MARKer:TABLe`,
`:CALCulate:MARKer<n>[:SET]:STARt|STOP|CENTer|STEP|RLEVel`,
`:CALCulate:MARKer<n>:DELTa[:SET]:SPAN|CENTer`,
`:CALCulate:MARKer:PEAK:SEARch:MODE MAXimum|MINimum`, `:PEAK:SORT FREQuency|AMPLitude`,
`:PEAK:THReshold`, `:PEAK:EXCursion`, `:PEAK:TABLe`, `:CALCulate:PEAK:TABLe?`,
`:CALCulate:MARKer<n>:CPEak`, `:MAXimum`, `:MAXimum:NEXT|LEFT|RIGHt`, `:CPSearch` (peak-peak),
`:CALCulate:MARKer<n>:FUNCtion OFF|FCOunt|NOISe|NDB`, `:CALCulate:MARKer:FCOunt[:STATe]`,
`:CALCulate:MARKer:FCOunt:X?`, `:CALCulate:MARKer<n>:BANDwidth:NDB` and `:RESult?`,
`:CALCulate:MARKer<n>:X:READout FREQuency|TIME|PERiod`, `:CALCulate:MARKer:TRCKing[:STATe]`.

Limits: `:CALCulate:LLINe:TEST:STARt|STOP`, `:TEST:STATe?`, `:CALCulate:LLINe<1|2>:STATe|TYPE UPPer|LOWer|MODE LINE|POINt|Y`,
`:DATA x,a{,x,a}`, `:ADD x,a`, `:DELete <n>`, `:ALL:DELete`, `:OFFSet:X|Y`,
`:CALCulate:LLINe:CONTrol:DOMain FREQuency|TIME`, `:CONTrol:BEEP`, `:CALCulate:LLINe:FAIL?` (PASS|FAIL),
`:CALCulate:LLINe:FAIL:STOP`.

Measurements: `:INSTrument:MEASure OFF|ACPR|CHPower|OBW|TPOWer|SPECtrogram|TOI|HARMonics|CNR`,
then: ACPR `[:SENSe]:ACPRatio:BWIDth:INTegration`, `:OFFSet:BWIDth`, `:OFFSet[:FREQuency]`,
`:MEASure:ACPRatio:MAIN?|LOWer?|LOWer:POWer?|UPPer?|UPPer:POWer?`;
CHP `[:SENSe]:CHPower:BWIDth:INTegration`, `:CHPower:FREQuency:SPAN:POWer`,
`:MEASure:CHPower?` (power, density), `:CHPower:CHPower?`, `:CHPower:DENSity?`;
OBW `[:SENSe]:OBWidth:METHod PERCent|DBC`, `:PERCent` (10 to 99.99), `:XDB`,
`:MEASure:OBWidth?`, `:OBWidth:OBWidth?`, `:OBWidth:CENTroid?`, `:OBWidth:OBWidth:FERRor?`;
T-Power `[:SENSe]:TPOWer:FREQuency:CENTer`, `:LLIMit`, `:RLIMit`, `:MEASure:TPOWer?`;
Spectrogram `[:SENSe]:SPECtrogram:STATe RUN|PAUSe`, `:RESTart`;
TOI `:MEASure:TOI?`, `:MEASure:TOI:IP3?`;
CNR `[:SENSe]:CNRatio:BANDwidth:INTegration|NOISe`, `:OFFSet`, `:MEASure:CNRatio?|CARRier?|NOISe?`;
Harmonics `[:SENSe]:HARMonics:FREQuency:FUNDamental` (10 MHz to 1.6 GHz) and `:AUTO`,
`:FREQuency:STEP` and `:AUTO`, `:NUMBer` (2 to 10), `:SELect` (0 = all).

TG: `:OUTPut[:STATe]`, `:SOURce:POWer[:LEVel][:IMMediate][:AMPLitude]` (-20 to 0 dBm),
`:SOURce:CORRection:OFFSet`, `:CALCulate:NTData[:STATe]` (normalise),
`:DISPlay:WINDow:TRACe:Y[:SCALe]:NRLevel|NRPosition`, `:TRACe:COPY:REF` (store ref),
`:DISPlay:WINDow:NTTRace[:STATe]` (show ref trace).

Demod: `[:SENSe]:DEMod AM|FM|OFF`, `:DEMod:TIME` (5 ms to 1000 s),
`:DEMod:EPHone`, `:DEMod:VOLume` (0 to 10).

Example, peak of a signal:

```
:INSTrument SA
:FREQuency:CENTer 100 MHz
:FREQuency:SPAN 1 MHz
:BWIDth 1 kHz
:INITiate:CONTinuous OFF
:INITiate:IMMediate
*OPC?
:CALCulate:MARKer1:STATe ON
:CALCulate:MARKer1:MAXimum
:CALCulate:MARKer1:X?
:CALCulate:MARKer1:Y?
```

## 8. Modulation analyzer mode (`:INSTrument MA`)

The raw RF data can be recorded to a PC with Siglent's EasyVSA software.
Analog AM/FM/PM and digital ASK, 2/4/8/16FSK, MSK, BPSK, QPSK, 8PSK, DBPSK,
DQPSK, D8PSK, π/4 DQPSK, π/8 D8PSK, OQPSK, 16 to 256QAM. Symbol rate 1 ksps to
2.5 Msps, 4 to 16 points/symbol, measurement length 16 to 4096 symbols.

Filter rule (transmitter -> measure filter / reference filter): Root Nyquist ->
Root Nyquist / Nyquist; Nyquist -> Off / Nyquist; Gauss -> Off / Gauss; Half
Sine -> Off / Half Sine. Alpha/BT 0 to 1 (default 0.35), filter length 2 to 128.

Custom presets: PDC (π/4 PSK 21 ksps, RRC/RC 0.5), GSM (MSK 270.833 ksps,
Gauss 0.3), TETRA (π/4 PSK 18 ksps, 0.35), DECT (2FSK 1.152 Msps, Gauss 0.5),
PHS (π/4 PSK 192 ksps, 0.5), NADC (π/4 PSK 24.3 ksps, 0.35).

Analog: IFBW 60 kHz to 1.2 MHz in fixed steps; for AM keep IFBW > 2 x
modulation frequency, for FM IFBW > 2 x (deviation + modulation frequency).
EqLPF Off or IFBW/6 down to IFBW/2000.

SCPI: `[:SENSe]:FREQuency:CENTer` (0 to 3.2 GHz), `:CENTer:STEP`,
`[:SENSe]:FREQuency:SPAN?` (read-only, derived), `[:SENSe]:POWer[:RF]:ATTenuation` and `:AUTO`,
`:TRACe<n>:Y[:SCALe]:RLEVel|PDIVision`, `:TRACe<n>[:Y]:AUToscale`,
`[:SENSe]:BWIDth?` (EQBW), `[:SENSe]:DDEMod:FFT:WINDow:TYPE RECT|HAMM|HANN|FLAT|BLAC`,
`:CALCulate:PARameter:COUNt`, `:DISPlay:LAYout rows,cols` (1,2 not supported),
`:TRACe<n>:DATA:NAME TIME|SPECtrum|MTIMe|MSPEctrum|RTIMe|RSPEctrum|MERRor|PERRor|EVTime|EVSPectrum|SYMSerrs`,
`:TRACe<n>:FORMat[:Y] MLOG|MLINear|REAL|IMAGinary|IQ|CONStln|IEYE|QEYE|WPHAse|UWPHase|TRELlis`,
`:TRACe:COPY A,B`, `:TRACe:DEMod:EYE:LENGth` (2 to 40), `:TRACe:DEMod:TABLe:FORMat BINary|HEXadecimal`,
markers `:TRACe<n>:MARKer<m>:ENABle|TYPE|X|Y?|REFerence`, `:CALCulate[:SELected]:MARKer:COUPle`,
`[:SENSe]:DDEMod:MODulation ASK2|MSK|BPSK|QPSK|PSK8|DBPSK|DQPSK|DPSK8|OQPSK|PI4DQ|PI8D8|QAM16|QAM32|QAM64|QAM128|QAM256|FSK2|FSK4|FSK8|FSK16`,
`[:SENSe]:ADEMod:STYLe AM|FM`, `:DDEMod[:FORMat]:SRATe` (no `:SENSe` in the PG header),
`[:SENSe]:DDEMod[:FORMat]:SYMBol:POINts`, `:RLENgth`, `[:SENSe]:DDEMod:FILTer[:MEASurement]|:REFerence OFF|RRCosine|RCOSine|GAUSsian|HSIN`,
`[:SENSe]:STATistic:STATe`, `[:SENSe]:AVERage[:STATe]`, `:AVERage:COUNt` (1 to 1000),
`:CALCulate:RESTart`, trigger `:TRIGger[:SEQuence]:SOURce IMMediate|RFBurst|EXTernal`
(RFBurst not for MSK/PSK/QAM), `:TRIGger[:SEQuence]:RF:LEVel`, `:RFBurst:SLOPe`.

`:READ:DDEMod?` returns, comma separated:
ASK: err rms %, err peak %, symbol of peak, carrier power, carrier offset, ASK depth.
FSK: err rms %, err peak %, symbol of peak, carrier power, carrier offset, FSK deviation.
MSK/PSK/QAM: EVM rms %, EVM peak %, symbol of EVM peak, mag err rms %, mag err
peak %, symbol, phase err rms °, phase err peak °, symbol, frequency error Hz,
IQ offset, SNR (MER) dB, quadrature error °, gain imbalance dB.

## 9. EMI measurement mode

Three windows: scan spectrum, meters (three detectors at one frequency), signal
list. The CISPR 16-2-3 flow is scan, then peak search into the signal list,
then a final zero-span measurement of each listed signal with the final
detectors and dwell. Sequence choices: Scan Only (default), Search Only, Scan
Search & Measure, Scan & Search, Search & Meas, Meas (re-measure current, all
or marked signals). Nothing scans until Start Sequence is pressed, even in
continuous mode; meters pause while a sequence runs.

Bands (Span > Select Band): CISPR A 9 to 150 kHz, B 150 kHz to 30 MHz, C 30 to
300 MHz (preset), B&C 150 kHz to 300 MHz, D 300 MHz to 1 GHz. RBW 200 Hz,
9 kHz, 120 kHz, 1 MHz (-6 dB). Sweep points = span / (RBW / RBW-per-step) + 1,
RBW/Step 0.1 to 3. Detectors Peak, Quasi-Peak, EMI Average (preset traces A, B,
C). Up to three limits with margin (-40 to 0 dB, preset -6) and built-in
standard LIM files (Limit > Load Std Lim). Preset units dBuV, X axis log.

The PG's `:INSTrument` list has no EMI value. Select EMI mode from the front
panel, or try `:INSTrument EMI` and confirm with `:INSTrument?` (UNVERIFIED).

SCPI: `[:SENSe]:FREQuency:CENTer` (meter frequency), `:MIDSpan`, `:STARt`,
`:STOP`, `:SPAN`, `[:SENSe]:FSCan:RANGe CISA|CISB|CISC|CISBC|CISD`,
`:DISPlay:WINDow:TRACe:X[:SCALe]:SPACing LOG|LIN`,
`:DISPlay:FSCan:VIEW:WINDow:TRACe:Y[:SCALe]:RLEVel|PDIVision`, attenuator, preamp,
`:UNIT:POWer`, `:INITiate2:CONTinuous` (scan single/continuous),
`:INITiate:CONTinuous` (meters), `[:SENSe]:SWEep:COUNt`, `[:SENSe]:FSCan:SCAN:PRBW` and `:AUTO`,
`[:SENSe]:FSCan:SCAN:POINts?`, `[:SENSe]:FSCan:SCAN:BWIDth[:RESolution]` and `:AUTO`,
`[:SENSe]:BWIDth[:RESolution]` (meter RBW 200 Hz/9 kHz/120 kHz),
`:TRACe<1-3>:FSCan:TYPE WRITe|MAXHold|MINHold|VIEW|BLANk|AVERage`,
`[:SENSe]:DETector:TRACe<1-3>[:FUNCtion] POSitive|QPEak|EAVerage`,
`:TRACe<1-3>:FSCan[:DATA]?`, markers `:CALCulate:FSCan:MARKer<1-6>:STATe|MODE|TRACe|REFerence|X|Y?`,
`[:SET]:SLISt` (marker to list), `[:SET]:METer` (meter to marker), `:TO:METer` (marker to meter),
`:CALCulate:FSCan:MARKer<n>:MAXimum`, `:CALCulate:MARKer<n>:MAXimum:LEFT|RIGHt`,
`:CALCulate:MARKer:PEAK:THReshold|EXCursion`, limits `:CALCulate:LLINe:TEST`,
`:CALCulate:LLINe<1-3>:STATe|Y|DATA|ADD|DELete|ALL:DELete`, `:CALCulate:LLINe<1|2>:MODE`,
`:CALCulate:FSCan:LLINe<1-3>:MARGin` and `:STATe`, `:CALCulate:FSCan:LLINe<1-3>:TRACe`,
`:CALCulate:LLINe:FAIL?`, sequence `[:SENSe]:FSCan:SEQuence SCAN|SEARch|SSAMeasure|SASearch|SAMeasure|REMeasure`,
`[:SENSe]:FSCan:SCAN:TIME` (dwell 1 ms to 10 s), meters `:DISPlay:METer<1-3>[:STATe]`,
`[:SENSe]:METer<1-3>:DETector POSitive|QPEak|EAVerage`, `:DETector:DWELl`,
`:CALCulate:METer<1-3>:LIMit[:DATA]|:STATe|:ULLine LIMit1|LIMit2|LIMit3` (no short form for LIMit1),
signal list `:CALCulate:SLISt:MARK:SIGNal <n>`, `:MARK:CLEar:SIGNal <n>`, `:MARK:ALL`,
`:MARK:CLEar:ALL`, `:DELete:SIGNal <n>`, `:DELete:ALL`,
`:SORT:TYPE FREQuency|DAMPlitude|DLDelta|TIME`, `:SORT:ORDer ASCending|DESCending`.
The PG documents no command to start a sequence; use the panel or web control.

## 10. System, files, presets, options, firmware

| SCPI | Function |
|---|---|
| `:INSTrument[:SELect] SA\|MA\|DTF\|VNA` | Mode |
| `:SYSTem:TIME hhmmss` / `:SYSTem:DATE yyyymmdd` | Clock |
| `:SYSTem:COMMunicate:LAN:TYPE STATIC\|DHCP`, `:IPADdress "a.b.c.d"`, `:GATeway`, `:SMASk` | LAN |
| `:SYSTem:LANGuage SCHINESE\|ENGLISH` | Language |
| `:SYSTem:PON:TYPE DFT\|LAST\|USER` | Power-on state |
| `:SYSTem:PRESet:TYPE DFT\|LAST\|USER`, `:SYSTem:PRESet` | Preset |
| `:SYSTem:PRESet:USER1..7:SAVE\|LOAD` | User setups |
| `:SYSTem:FDEFault` | Factory reset |
| `:SYSTem:LKEY "VNA","<16-char key>"` | Install option (reboot after) |
| `:SYSTem:OPTions?` | Installed options |
| `:SYSTem:CONFigure:SYSTem?` | System information string |
| `:SYSTem:RESTart`, `:SYSTem:POWer:OFF` | Reboot, power off |
| `:MMEMory:STORe STA\|TRC\|COR\|CSV\|LIM\|JPG\|BMP\|PNG,"name"` | Save |
| `:MMEMory:LOAD STA\|TRC\|COR\|LIM,"name"` | Load |
| `:MMEMory:DELete "name"` | Delete file or folder |
| `:DISPlay:WINDow:TRACe:GRATicule:GRID:BRIGhtness 0..100` | Grid |
| `:DISPlay:WINDow:TRACe:Y:DLINe[:STATe]` | Display line |

File types: STA (setup, ASCII), TRC (visible traces with scaling, ASCII;
recalling one rescales the display to match), COR (amplitude correction),
CAL (VNA calibration; front panel only, no SCPI type), CSV (setup plus data for
spreadsheets), LIM (limit lines), PIC (JPG/BMP/PNG screenshots). With a USB drive
present, saving goes to the drive first. The Save key saves a PNG screenshot by
default (File > Save Type changes it); Display > Screenshot toggles inverse
colours (traces keep their colours). The PG documents no screen-dump query, but
the undocumented `:HCOPy:SDUMp:DATA?` works on firmware 3.2.2.6.3R16
(VERIFIED): it returns a 1024 x 600, 24-bit BMP of 1 843 254 bytes. One
`read_raw()` returns only part of it, so read the total size from bytes 2 to 5
of the BMP header and keep calling `read_raw()` until it has all arrived (a 30 s
timeout is enough). `screenshot()` in section 14 does this. The alternative is
`:MMEMory:STORe PNG,"x.png"`, then collecting the file by USB drive or through
the web interface.

Front panel only: Reset & Clear (factory state plus erase of all user data),
Power on Line (auto-start on mains), Auto Cal (after 30 min warm-up, self-
calibrates whenever internal temperature moves more than 2 °C; off by
default), self tests (screen colours: Preset steps, ← exits; keyboard: ← four
times exits; key backlight; touch), touch on/off and Touch Assistant, power
saving, annotations (up to ten, lost on mode change or power off), date format.

Mode presets (UM tables 8-4 and 8-5): VNA preset S11 Log Mag, 201
points, IFBW 10 kHz, 1 trace, averaging off (100), marker couple on,
discrete off, correction off, Z0 50, VF 0.66, port extensions off. DTF preset
averaging on (10), Hamming, VF 0.66, metres, correction on.

Options: System > System Info > Load Option, type the key, or load the .lic
file through File > Load. System Info shows model, serial, Host ID (needed when
buying an option), software and hardware versions.

Firmware: unzip the package, put the .ADS file in the root of a USB stick,
System > System Info > Firmware Update, select it, Load. It takes several
minutes and reboots; the status bar shows Upgrade meanwhile. Do not interrupt
power or pull the stick: an interrupted update loses system data and Siglent
treats it as out of warranty. The web interface can also update firmware.

## 11. IVI-C driver

Siglent's IVI-C driver (ssa.dll / ssa_64.dll, ssa.lib, ssa.h) covers SA mode
only (`SSA_ATTR_INSTRUMENT_MODE` has one value, SA = 1). It needs NI-VISA full
(15.5 or later) and the NI IVI Compliance Package, and SVA1000X firmware
3.2.2.5.0 or later. Functions follow the IviSpecAn pattern:
`ssa_ConfigureFrequencyStartStop/CenterSpan/Offset`, `ssa_ConfigureLevel`,
`ssa_ConfigureSweepCoupling`, `ssa_ConfigureAcquisition`,
`ssa_ConfigureTraceType`, `ssa_Initiate`, `ssa_AcquisitionStatus`,
`ssa_ReadYTrace`/`ssa_FetchYTrace`, `ssa_QueryTraceSize`, marker functions
(`ssa_ConfigureMarkerEnabled`, `ssa_MarkerSearch`, `ssa_QueryMarker`,
`ssa_SetInstrumentFromMarker`, `ssa_MakeMarkerDelta`), TG
(`ssa_ConfigureTrackingGenerator`, `ssa_ConfigureNormalize`), CHP/ACPR/OBW
configure and read functions, plus the `ssa_Set/GetAttributeViInt32/ViReal64/ViString/ViBoolean`
family. Enumerations from the guide: sweep mode 2 = FFT; units dBm 1, dBmV 2,
dBuV 3, V 4, W 5; detector average 2, max peak 3, min peak 4, sample 5,
normal 6. Its RBW list runs to 10 MHz because it also serves bigger models;
the SVA1032X stops at 1 MHz. For VNA work use SCPI directly.

## 12. Performance verification

The service manuals contain verification tests for the SA and TG only. There is
no VNA or DTF verification and no adjustment procedure. For calibration the
UM says to contact Siglent or a paid service from an authorised measurement
agency.
Warm up the analyzer and test gear for 30 minutes; 20 to 30 °C. Lock the
generators to the analyzer's 10 MHz where the setup shows it.

Test equipment (SM table 3-1): two RF generators 9 kHz to 3.2 GHz (R&S SMB100A),
a 100 MHz function generator with counter (Siglent SDG1050) referenced to an
OCXO, a 6 GHz power meter (R&S NRP-Z91), 50 MHz low-pass filter, 6 GHz power
divider, 6 GHz N-N and SMA-N cables, BNC cables, a 50 Ω load. The SSA3032X Plus
manual, which uses the same tests, names a Siglent SDG2122X for the function
generator and counter (its counter input is the rear Counter BNC). Separate
skills in the same collection cover the SDG2000X (`siglent-sdg2000x`), an HP 8648
as the RF generator (`hp8648-gpib`) and an Agilent E4418B/E4419B as the power
meter (`agilent-epm-power-meter`), if they are installed.

| Test | SVA1032X spec | Method |
|---|---|---|
| Absolute amplitude | ±0.4 dB at -20 dBm, preamp off; ±0.6 dB at -40 dBm, preamp on | 50 MHz through a divider to power meter and RF IN. CF 50 MHz, span 1 MHz, ATT 20 dB, RBW = VBW = 1 kHz, 10 averages, peak detector. Error = P(meter) - P(marker) |
| Frequency response (re 50 MHz) | ±0.8 dB (±0.4 typ) preamp off; ±1.2 dB (±0.6 typ) preamp on | Same setup. Reference at 50 MHz, then 100 kHz, 1 MHz, 10 MHz, 100 MHz, 1 GHz, 3 GHz. Response = abs((A_SA - P_SA) - (A_PM - P_PM)) |
| DANL (1 Hz normalised), preamp off | -107 dBm 0.1 to 1 MHz; -132 dBm 1 to 10 MHz; -137 dBm 10 to 200 MHz; -135 dBm 0.2 to 1.5 GHz; -126 dBm 1.5 to 3.2 GHz | 50 Ω load on RF IN, ATT 0 dB, sample detector, > 50 averages, peak-search the noise. Test points 500.5 kHz, 5.005 MHz, 50.005 MHz, 500.005 MHz, 2.500005 GHz |
| DANL, preamp on | -132, -148, -156, -155, -145 dBm for the same bands (typ -137, -154, -161, -158, -149) | Same |
| Phase noise at 1 GHz | < -95 dBc/Hz at 10 kHz, < -96 at 100 kHz, < -115 at 1 MHz | -20 dBm at 1 GHz, ATT 0, 100 averages. 10 kHz: span 30 kHz, RBW 1 kHz, sample. 100 kHz: span 220 kHz, RBW 1 kHz, average detector. 1 MHz: span 3 MHz, RBW 10 kHz, average detector. Peak, delta marker at the offset, noise marker; result = P2 - P1 |
| TOI | IIP3 ≥ +10 dBm | Two -20 dBm tones 1000 and 1000.1 MHz via divider, CF 1 GHz, span 1 MHz, RBW 10 kHz, ATT 0, 100 averages. Δ = delta-marker reading from tone to 3rd-order product (999.9 and 1000.2 MHz), a negative number; IIP3 = -20 dBm - Δ/2 |
| Frequency accuracy | < 1 ppm at 10 MHz | Count REF OUT with an OCXO-referenced counter |
| 1 dB compression | > -5 dBm at the mixer | 50 MHz at -25 dBm plus 53 MHz at -5 dBm (levels set on the power meter through the divider). CF 50 MHz, span 100 kHz, ref -25 dBm, ATT 0, RBW 1 kHz, sweep rule Accuracy. P1 with 50 MHz alone, P2 with both on. The SM gives no pass rule; P1 - P2 < 1 dB is the implied one |
| Second harmonic | < -65 dBc at -30 dBm mixer level | 50 MHz -30 dBm through a 50 MHz LPF. Span 10 kHz, ref -30 dBm, ATT 0, RBW 300 Hz, VBW 10 Hz, Accuracy. Measure at 50 and 100 MHz |
| Input attenuator error | < ±0.5 dB re 20 dB | 50 MHz, generator levels P-30...P0 found on the power meter. Span 10 kHz, ref 0 dBm, RBW 1 kHz, VBW 10 Hz. Reference: ATT 20 dB with -10 dBm in. Then for each ATT of 0 to 30 dB apply (ATT - 30) dBm; ΔP = marker - input level; error = ΔP(ATT) - ΔP(20 dB) |
| TG | 100 kHz to 3.2 GHz, -20 to 0 dBm, flatness ±3 dB | TG to RF IN with an N-N cable, full span, ref 0 dBm, auto RBW/VBW. Peak max < level + 3 dB and min (Peak type Min) > level - 3 dB at 0, -10, -20 dBm |

The DANL table is labelled "RBW = 1 Hz" but the method uses RBW 10 Hz and
VBW 1 Hz. Either use the noise marker, which normalises to 1 Hz, or subtract
10 log10(RBW) from the marker reading before comparing.

SVA1015X differences (SM0701X-E01A): 9 kHz to 1.5 GHz; TG 5 MHz to 1.5 GHz
(not 100 kHz); preamp-on absolute amplitude ±0.5 dB; preamp-on frequency
response ±0.9 dB (±0.5 typ); DANL specified at RBW 10 Hz in bands 0.1 to 1 MHz,
1 to 10 MHz, 10 MHz to 1 GHz, 1 to 1.5 GHz (preamp off -91, -114, -118,
-111 dBm; preamp on -110, -137, -140, -132 dBm); phase noise typ
-99/-98/-120 dBc/Hz, measured in one setup (span 50 kHz, RBW 100 Hz, sample);
IIP3 ≥ +8 dBm with the same 1000/1000.1 MHz tones. Its record table's 500.5 and
1000.5 MHz product frequencies are a copy error; the products are at 999.9 and
1000.2 MHz.

The SSA3075X Plus manual uses the same procedures with 7.5 GHz limits (TG -40 to
0 dBm, IIP3 +14 dBm, 1 dB compression > 0 dBm, RBW to 3 MHz). Do not apply those
limits to an SVA1032X.

For a VNA sanity check the manuals give nothing; a practical substitute is to
calibrate S11, then measure the cal kit's own standards and a known
attenuator terminated in a load (expect return loss near twice the pad value
plus the load's), and normalise S21 and measure a characterised attenuator.

When automating PV, set every
parameter explicitly (section 2, item 11), use single sweeps with `*OPC?`, and
read markers rather than eyeballing.

## 13. Service, troubleshooting and system messages

Disassembly (SM chapter 4, qualified staff only): disconnect mains and wait at
least three minutes for capacitors to discharge (LCD and power supply carry
hazardous voltage); ESD mat and strap. Tools: multi-bit screwdriver, antistatic
gloves, a hex nut tool or long-nose pliers for the BNC nuts. Order: rear panel
(screws, then press the front panel and slide off); front panel (face down,
six rear screws and four in the feet); rear metal cover (screws, three rear
BNC nuts, unplug the mains and fan cables from the power supply; the cover
edge is sharp); main boards on the metal shelf (RF board, TG board, digital
board); LCD and keyboard (silicone keypad, four display screws, six channel
board screws, seven keyboard screws, keyboard-to-channel-board cable). Module
list: rear panel, front panel, rear metal cover, front metal cover, power
supply, main boards, keyboard, display. Reassemble in reverse.

Functional checks: at power-on some keys light for about 6 s, then the boot
screen. USB host: a flash drive icon appears top right (a LAN icon appears
there when a cable is connected). USB device and LAN: `*IDN?` from NI-MAX.

Troubleshooting (UM 10.2, repeated in the quick guide):

| Symptom | Check |
|---|---|
| Power key stays dark | Mains, cord, fuse (use the specified fuse) |
| Screen dark | Fan running: LCD cable may be loose. Fan not running: start-up failure. Return to Siglent |
| Keys dead or wrong | System > Self Test > Keyboard; touch on in Display > Touch Settings; remote lock (Esc) |
| Trace not updating | Trace in View, trigger not met, limit test with fail-stop, single sweep, very long sweep time, long demod time, EMI sequence not scanning |
| Wrong results | Connections, settings suited to the signal, warm-up and temperature, Correction on in SA/VNA, calibration due |

System messages (UM table 10-1), by number: 1 sweep time out of range;
2 RBW out of range; 3 sweep time fixed in FFT mode; 4-9 undefined marker,
marker function, delta pair, readout, trace or detector type; 10 Scale/Div not
settable in linear; 11 marker is off; 12 marker is not delta; 13 readout must
be time; 14 undefined math type; 15 XML attribute import error; 16 X scale must
be linear in zero span; 17 scale must be log when normalising; 18 cannot go
linear while normalised; 19 no peak found; 20 IMD products out of range; 21
auto tune failed; 22/23 external reference plugged in/out; 24 reference PLL
unlock; 25 signal not stable enough to track; 26 RBW out of range for QP scan;
150/151 LAN cable in/out; 152 IP conflict; 153 IP invalid; 154 netmask invalid;
155 gateway invalid; 183 S21 normalisation done; 184 VNA auto calibration done;
400 load configuration failed (file error); 600-604 firmware upgrade failed
(version, RAM, file, verify, unzip); 605 licence invalid; 606 ADC overload.

Warranty per UM: three years on the instrument, one year on accessories.

## 14. Python driver

Save as `sva1032x.py`. Tested only against a mock socket server. Works over
PyVISA (`USB0::...::INSTR`, `TCPIP0::<ip>::INSTR`) or a raw socket
(`<ip>` or `<ip>:5025`) with no dependencies.

```python
#!/usr/bin/env python3
"""Minimal driver and CLI for the Siglent SVA1032X (SVA1000X family).

Written from Siglent PG0703P_E02B / UM0703P_E02E. Not yet run against a
real instrument: anything marked UNVERIFIED follows the E5071C-style
convention the programming guide claims compatibility with.

    python sva1032x.py 192.168.1.50 --idn
    python sva1032x.py 192.168.1.50 --send ":INST VNA" --query ":INST?"
    python sva1032x.py 192.168.1.50 --s11 1e6 1e9 401 out.s1p
    python sva1032x.py 192.168.1.50 --sa-trace 1 trace.csv
"""
from __future__ import annotations

import argparse
import socket
import sys
import time


class SocketIO:
    """Raw SCPI over TCP port 5025, newline terminated."""

    def __init__(self, host: str, port: int = 5025, timeout: float = 10.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.timeout = timeout
        self._buf = b""

    def write(self, cmd: str) -> None:
        self.sock.sendall(cmd.encode("ascii") + b"\n")

    def read(self) -> str:
        while b"\n" not in self._buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("instrument closed the socket")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return line.decode("ascii", "replace").strip()

    def set_timeout(self, seconds: float) -> None:
        self.timeout = seconds
        self.sock.settimeout(seconds)

    def close(self) -> None:
        self.sock.close()


class VisaIO:
    def __init__(self, resource: str, timeout: float = 10.0):
        import pyvisa  # imported here so socket use needs no pyvisa

        self.rm = pyvisa.ResourceManager()
        self.dev = self.rm.open_resource(resource)
        self.dev.write_termination = "\n"
        self.dev.read_termination = "\n"
        self.dev.chunk_size = 1 << 20
        self.set_timeout(timeout)

    def write(self, cmd: str) -> None:
        self.dev.write(cmd)

    def read(self) -> str:
        return self.dev.read().strip()

    def set_timeout(self, seconds: float) -> None:
        self.timeout = seconds
        self.dev.timeout = int(seconds * 1000)

    def close(self) -> None:
        self.dev.close()


class SVA:
    MODES = ("SA", "VNA", "DTF", "MA")  # documented :INSTrument values

    def __init__(self, target: str, timeout: float = 10.0):
        if "::" in target:
            self.io = VisaIO(target, timeout)
        else:
            host, _, port = target.partition(":")
            self.io = SocketIO(host, int(port or 5025), timeout)
        self.idn = self.query("*IDN?")
        if "SVA1" not in self.idn.upper():
            print(f"warning: not an SVA1000X: {self.idn}", file=sys.stderr)

    # -- basic I/O ------------------------------------------------------
    def write(self, cmd: str) -> None:
        self.io.write(cmd)

    def query(self, cmd: str) -> str:
        self.io.write(cmd)
        return self.io.read()

    def query_float(self, cmd: str) -> float:
        return float(self.query(cmd).split(",")[0])

    def query_floats(self, cmd: str) -> list[float]:
        return [float(v) for v in self.query(cmd).split(",") if v.strip()]

    def opc(self, timeout: float = 60.0) -> None:
        """Block until pending operations finish (*OPC? returns 1)."""
        old = self.io.timeout
        self.io.set_timeout(timeout)
        try:
            self.query("*OPC?")
        finally:
            self.io.set_timeout(old)

    def esr(self) -> int:
        """Standard event register; bits 2..5 = query/device/exec/command error."""
        return int(float(self.query("*ESR?")))

    def checked(self, cmd: str) -> None:
        """Write, then fail loudly if *ESR? shows an error bit."""
        self.esr()  # clear
        self.write(cmd)
        e = self.esr()
        if e & 0b0011_1100:
            raise RuntimeError(f"{cmd!r} -> *ESR? = {e}")

    def mode(self, name: str) -> None:
        name = name.upper()
        if self.query(":INSTrument?").upper().startswith(name):
            return
        self.write(f":INSTrument {name}")
        self.opc(60)
        time.sleep(1.0)  # mode switch rebuilds the UI; be generous

    def close(self) -> None:
        self.io.close()

    # -- VNA ------------------------------------------------------------
    def vna_setup(self, start: float, stop: float, points: int = 201,
                  param: str = "S11", fmt: str = "MLOGarithmic") -> None:
        self.mode("VNA")
        self.write(f":SENSe:FREQuency:STARt {start}")
        self.write(f":SENSe:FREQuency:STOP {stop}")
        self.write(f":SENSe:SWEep:POINts {points}")
        self.write(f":CALCulate:PARameter1:DEFine {param}")
        self.write(":CALCulate:PARameter1:SELect")
        self.write(f":CALCulate:FORMat {fmt}")

    def vna_freqs(self) -> list[float]:
        f1 = self.query_float(":SENSe:FREQuency:STARt?")
        f2 = self.query_float(":SENSe:FREQuency:STOP?")
        n = int(self.query_float(":SENSe:SWEep:POINts?"))
        return [f1 + i * (f2 - f1) / (n - 1) for i in range(n)]

    def single_sweep(self, timeout: float = 120.0) -> None:
        self.write(":INITiate:CONTinuous OFF")
        self.write(":INITiate:IMMediate")
        self.opc(timeout)

    def vna_fdata(self, trace: int = 1) -> list[tuple[float, float]]:
        """Formatted data as (frequency Hz, value) pairs.

        VERIFIED for scalar formats on firmware 3.2.2.6.3R16. Drop the first
        three points of each sweep; they read badly.
        """
        self.write(f":CALCulate:PARameter{trace}:SELect")
        self.write(":FORMat:DATA ASCii")
        v = self.query_floats(":CALCulate:SELected:DATA:FDATa?")
        return list(zip(v[0::2], v[1::2]))

    def vna_complex(self, trace: int = 1) -> list[complex]:
        """Complex S-parameter via POLar (Real/Imag) format. UNVERIFIED.

        Scalar formats return (frequency, value) pairs on this firmware, so
        POLar may return (frequency, re, im) triplets. Check the length of the
        raw array before trusting this.
        """
        self.write(f":CALCulate:PARameter{trace}:SELect")
        old = self.query(":CALCulate:FORMat?")
        self.write(":CALCulate:FORMat POLar")
        self.single_sweep()
        data = [complex(re, im) for re, im in self.vna_fdata(trace)]
        self.write(f":CALCulate:FORMat {old}")
        return data

    def cal_one_port(self, *args, **kwargs) -> None:
        """Do NOT calibrate over SCPI on this firmware.

        On 2026-11-03 (fw 3.2.2.6.3R16) OPEN and SHORT acquired in 0.6 s each,
        then *OPC? after ':SENSe:CORRection:COLLect:LOAD 1' never returned, the
        instrument stopped answering even *IDN? after a device clear, and the
        front panel and power key froze until it was unplugged. Run the cal
        from the front panel instead.
        """
        raise RuntimeError("Calibrate from the front panel; SCPI cal froze the SVA (section 16)")

    def cal_thru(self, *args, **kwargs) -> None:
        """Do NOT calibrate over SCPI on this firmware; see cal_one_port."""
        raise RuntimeError("Calibrate from the front panel; SCPI cal froze the SVA (section 16)")

    def screenshot(self, path: str) -> None:
        """Save the screen as a BMP via the undocumented :HCOPy:SDUMp:DATA?.

        VERIFIED on fw 3.2.2.6.3R16 over USBTMC (PyVISA). The 1.8 MB image
        arrives over several reads.
        """
        import struct
        if not isinstance(self.io, VisaIO):
            raise RuntimeError("screenshot() is only verified over VISA")
        dev = self.io.dev
        old = dev.timeout
        dev.timeout = 30000
        try:
            dev.write(":HCOPy:SDUMp:DATA?")
            buf = bytearray(dev.read_raw())
            total = struct.unpack("<I", bytes(buf[2:6]))[0]
            while len(buf) < total:
                buf += dev.read_raw()
        finally:
            dev.timeout = old
        with open(path, "wb") as fh:
            fh.write(buf[:total])

    def save_s1p(self, path: str, freqs: list[float], s11: list[complex],
                 z0: float = 50.0) -> None:
        with open(path, "w", newline="\n") as fh:
            fh.write(f"! {self.idn}\n# HZ S RI R {z0:g}\n")
            for f, s in zip(freqs, s11):
                fh.write(f"{f:.6f} {s.real:.9e} {s.imag:.9e}\n")

    # -- DTF ------------------------------------------------------------
    def dtf_peak(self) -> tuple[float, float]:
        """Run one DTF sweep and return (distance, value) of the worst peak."""
        self.single_sweep()
        self.write(":CALCulate:MARKer1:STATe ON")
        self.write(":CALCulate:MARKer1:MAXimum")
        return (self.query_float(":CALCulate:MARKer1:X?"),
                self.query_float(":CALCulate:MARKer1:Y?"))

    # -- SA -------------------------------------------------------------
    def sa_trace(self, trace: int = 1) -> tuple[list[float], list[float]]:
        self.write(":FORMat:DATA ASCii")
        y = self.query_floats(f":TRACe:DATA? {trace}")
        f1 = self.query_float(":SENSe:FREQuency:STARt?")
        f2 = self.query_float(":SENSe:FREQuency:STOP?")
        n = len(y)
        x = [f1 + i * (f2 - f1) / (n - 1) for i in range(n)] if n > 1 else [f1]
        return x, y


def _cli() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="VISA resource or host[:port]")
    ap.add_argument("--idn", action="store_true")
    ap.add_argument("--send", action="append", default=[])
    ap.add_argument("--query", action="append", default=[])
    ap.add_argument("--s11", nargs=4, metavar=("START", "STOP", "POINTS", "FILE"))
    ap.add_argument("--sa-trace", nargs=2, metavar=("TRACE", "FILE"))
    a = ap.parse_args()
    sva = SVA(a.target)
    try:
        if a.idn:
            print(sva.idn)
        for c in a.send:
            sva.write(c)
        for q in a.query:
            print(sva.query(q))
        if a.s11:
            f1, f2, n, path = a.s11
            sva.vna_setup(float(f1), float(f2), int(n), "S11")
            s = sva.vna_complex(1)
            sva.save_s1p(path, sva.vna_freqs(), s)
            print(f"wrote {len(s)} points to {path}")
        if a.sa_trace:
            t, path = a.sa_trace
            x, y = sva.sa_trace(int(t))
            with open(path, "w") as fh:
                fh.write("freq_hz,level\n")
                fh.writelines(f"{f:.3f},{v}\n" for f, v in zip(x, y))
            print(f"wrote {len(y)} points to {path}")
    finally:
        sva.close()


if __name__ == "__main__":
    _cli()
```

The first bench session (2026-11-03, section 16) answered: `*IDN?` and
`:INSTrument?` (returns `SA`, `VNA`); the FDATa format for scalar traces;
`:SENSe1:BWIDth` (ignored) and `:SOURce1:POWer` (works). Still open: what
Smith and polar formats return from FDATa (and so whether `vna_complex` and
`--s11` work); whether `:CALCulate:DATA:FDATa?` answers in DTF mode; whether
`:SENSe1:CORRection:STATe` is accepted; REAL,32 byte order against ASCII.
Record the answers in this skill.

## 15. Manual discrepancies

| Topic | UM0703P-E02E | PG0703P_E02B / other | Take |
|---|---|---|---|
| VNA frequency range | 10 MHz to 1.5 GHz (footnoted model-dependent) | 100 kHz to 3.2 GHz | PG for SVA1032X |
| VNA preset start | 100 kHz in preset table, 10 MHz in range table | 100 kHz | 100 kHz |
| VNA markers per trace | 4 incl. R (section 3.4.1); 6 (table 1-4, also in the quick guide) | headers MARKer1 to 7 | Check on unit |
| VNA cal status codes | Cor, Off, ---, C?, C! (table 3-1) | Quick guide: Cor, Off, C? | `C!` meaning unknown |
| Marker Discrete default | Off (preset) | ON | Set explicitly |
| Marker Couple default | On (preset) | OFF | Set explicitly |
| Cal kit list | F503ME, 85032F, 85032B/E, User | F503ME, 85032F, 85036B/E, User1, User2 | Query `CKIT:LABel:CATalog?` |
| Velocity factor | 0.1 to 1 (VNA and DTF menus) | VNA 0.1 to 1; DTF 10 to 100 | Mode-dependent units |
| DTF window default | Off (4.2.6), Hamming (preset) | HAMM | Hamming |
| DTF stop distance | 0.2 to 34 m, default 34 or 30.39 m | 0.2 to 34 m, default 30.6 m | Limited by span formula |
| DTF cable attenuation | 0 to 5 dB/m | -1000 to 10000 | Use dB/m within 0 to 5 |
| DTF averaging default | On, 10 | STATe OFF, COUNt 100 | Set explicitly |
| DTF meas type default | | "REFLcoe" (not a documented token) | Set `DTF` or `CAT` |
| DTF ref / scale default | 0 / 10 | 1 / 5 | Set explicitly |
| VNA centre / stop default | 750.05 MHz / 1.5 GHz | 1.60005 GHz / 3.2 GHz | PG for SVA1032X |
| MA attenuator auto | Auto, 20 dB | AUTO default 0 | Set explicitly |
| `METHod:THRU` | Response through | "2-port TRL calibration" | It is response-through |
| VNA IFBW | Menu item, default 10 kHz | Query only | Set on panel |
| SA attenuator | 0 to 31 dB | 0 to 51 dB | Model-dependent; read back |
| SA ref level | -200 to 20 dBm | -100 to 30 dBm | Read back |
| SA scale/div | 0.1 to 20 dB | 1 to 10 dB | Read back |
| SA sweep time | 900 µs to 1.5 ks | 450 µs to 1500 s | Read back |
| TG level default | -20 dBm | 0 dBm | Set explicitly (start low) |
| Peak threshold / excursion | -140 dBm / 15 dB | -160 dBm / 0 dB | Set explicitly |
| Signal track default | Off | ON | Set explicitly |
| Demod time default | 5 s | 5 ms | Set explicitly |
| EMI scan RBW | 200 Hz, 9k, 120k, 1M | adds 100 Hz, 300 Hz, 1k, 3k, 10k, 30k, 100k, 300k | Read back |
| EMI mode select | Mode key | not in `:INSTrument` list | Front panel |
| Reflection meas (SA) | described with external bridge | "SSA only, SVA not supported" | Use VNA mode |
| Socket example | | `recv()` before any query | Use timeouts |
| PG header typos | | `MARKer[1]..7STATe` missing colon, `PARameter[1]2\|3\|4` missing bar | Send the regular form `:CALC:MARK1:STAT`, `:CALC:PAR2:DEF` |
| Power line | 100-240 V 50/60 Hz or 100-120 V 400 Hz | SM: 50/60/440 Hz | 400 Hz at 100-120 V |
| 7.5 GHz figures | | PG EMI ranges to 7.5 GHz; IVI RBW list to 10 MHz | SSA3075X Plus values (its SM: 9 kHz to 7.5 GHz, RBW to 3 MHz, TG -40 to 0 dBm); SVA1032X stops at 3.2 GHz and RBW 1 MHz |

## 16. Bench findings (verified on a reference unit)

Unit: SVA1032X, firmware 3.2.2.6.3R16, all options
licensed, locked to an external 10 MHz reference. Session: 2026-11-03, VNA
mode, PyVISA over USBTMC, measuring an HP 58514A GPS L1
filter with an HP 85032B kit and two HP 8120-8862 cables (N male free ends).

### The SCPI calibration freeze

The one-port cal was started over SCPI with kit 85032B/E, `:SENSe:CORRection:COLLect:METHod:SOLT1 1`,
16x averaging on and continuous sweep. OPEN and SHORT acquisitions each
returned `*OPC?` in 0.6 s with `*ESR?` 0. After `:SENSe:CORRection:COLLect:LOAD 1`
the `*OPC?` never returned (120 s VISA timeout), `*IDN?` timed out even after a
USB device clear, and the screen froze. The power key did nothing; the SVA had
to be unplugged. The cal data was lost.

So: set the stimulus and traces over SCPI, run every calibration from the
front panel (Meas Setup > Calibration > Calibrate), and use SCPI only to read
data. Front-panel 1-Port Cal, Response Through and Enhanced Response all
worked. Whether averaging or the continuous sweep contributed is unknown; do
not try to find out on a unit that matters.

### Commands checked

| Command | Result on 3.2.2.6.3R16 |
|---|---|
| `*IDN?` | `Siglent Technologies,SVA1032X,<serial>,3.2.2.6.3R16` |
| `:SYSTem:OPTions?` | `Meas,EMI,TG,REFL,,AM,WDMA,,VNA,RTSA,` |
| `:INSTrument VNA` then `*OPC?` | Works; allow about 5 s before configuring. `:INSTrument?` returns `VNA` or `SA` |
| `:SENSe:FREQuency:STARt/STOP`, `:SENSe:SWEep:POINts` | Work and read back |
| `:SOURce1:POWer` | Works and reads back (-15 and -10 dBm tried) |
| IFBW (`:SENSe1:BWIDth`, `:BWIDth:RESolution`, `:BWIDth`, `:BANDwidth`) | Accepted with `*ESR?` 0, ignored; IFBW stays 10 kHz and is greyed out on the panel |
| `:SENSe:AVERage:COUNt`, `:STATe` | Work and read back |
| `:CALCulate:PARameter:COUNt`, `:PARameter<n>:DEFine`, `:SELect`, `:CALCulate:FORMat` | Work and read back |
| `:SENSe:CORRection:COLLect:CKIT:LABel:CATalog?` | `F503ME,F503FE,F603ME,F603FE,F504MS,F504FS,F604MS,F604FS,85032F,85032B/E,85033D/E,User1,User2` |
| `:SENSe:CORRection:COLLect:CKIT:LABel`, `:GENDer` | Work and read back; gender is the gender of the standards |
| `:SENSe:CORRection:COLLect:METHod:TYPE?` | `NONE` after front-panel cals, even with `Cor` showing |
| `:SENSe:CORRection:COLLect:OPEN 1`, `SHORt 1` | Acquire in 0.6 s |
| `:SENSe:CORRection:COLLect:LOAD 1` | Froze the instrument (above) |
| `:CALCulate:SELected:DATA:FDATa?` | (frequency Hz, value) pairs for log mag and phase |
| `:HCOPy:SDUMp:DATA?` | 1024 x 600 BMP, 1 843 254 bytes, over several reads |
| `:SYSTem:COMMunicate:LAN:IPADdress?` | `"192.168.1.140"`, static (example) |

### Measured performance

| Item | Result |
|---|---|
| Corrected load after 1-port cal (85032B female load, 1475 to 1675 MHz) | -38.9 dB mean, -39.3 dB at 1575 MHz, worst -35 dB (first three points excluded) |
| Corrected bare N(m) cable end (open) | 0.02 dB mean, -0.04 to +0.14 dB |
| Response-thru, thru re-measured | 0.00 +/- 0.02 dB, +/- 0.3 degrees |
| Port-2 match in VNA mode, measured as S11 through the thru | -4.4 to -6.5 dB across 1475 to 1675 MHz, about -5 dB (single slow swing, consistent with the reflection being at the port) |
| Sweep, 751 points, 10 kHz IFBW, no averaging | Under 1 s |

With port 2 at about -5 dB, a DUT whose output match is -12 dB can show up to
about +/-1 dB of uncorrected S21 error. Forward and reverse sweeps of a
reciprocal DUT agreed within 0.1 dB on the 58514A, so the real error was
smaller, but a pad on port 2 is the fix.

### Screen

The Calibrate menu marks finished cals with an asterisk (`*1-Port Cal`,
`*Response Through`) and also lists Open Cal, Short Cal and Enhanced Response.
The calibration flag shows once, at the top left of the graticule. The status
bar shows `Ext Ref` when locked and `Remote` or `Local`.