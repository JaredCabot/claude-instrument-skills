# SDG2000X front-panel operation

For when someone is standing at the instrument, or when a remote task has no SCPI equivalent
and has to be done through `VKEY` or by hand.

## Panels

**Front:** power button, USB Host port (flash drives, USB-GPIB adapter), 4.3" 24-bit resistive
touchscreen, numeric keypad, rotary knob, left/right arrow keys, waveform-selection buttons,
mode/auxiliary function keys, six menu softkeys down the right edge mapping 1:1 to on-screen
labels, a channel-switch key, and per-channel `Output` buttons with BNC outputs.

**Rear:** `Counter` BNC (frequency-meter input, 1 MΩ), `Aux In/Out` BNC (external trigger in,
trigger out, sync out, external modulation in), `10MHz In/Out` BNC (reference clock),
chassis ground terminal, IEC C13 mains inlet, `USB Device` port (USBTMC — this is the one for
PC control), `LAN` port.

The BNC shells are tied to chassis/safety ground. The instrument cannot float.

## Key behaviours worth knowing

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

## Setting up a basic output

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

## Harmonic mode

A sub-function of the Sine carrier. `Type` = Odd / Even / Custom, `Order` up to 16, amplitude in
Vpp or dBc relative to the fundamental, plus per-harmonic phase. The screen shows both a
time-domain preview and a bar chart of the harmonic amplitudes. Mixing odd and even harmonics
requires `Custom`.

## Arbitrary waveforms

`Waveforms > Page 1/2 > Arb`. Choose `DDS` (1 µHz–20 MHz, frequency-driven) or `TrueArb`
(sample-rate driven, 1 µSa/s–75 MSa/s, point-for-point). Data source is either a built-in
waveform — organised into categories: commonly used, mathematical, engineering, window
functions, trigonometric, square waves, medical, modulation, filters, demonstrations — or a
stored waveform, which opens the file manager for you to pick and `Recall`.

## Modulation

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

## Sweep

`Sweep` button. Linear, Log, or Step. Direction Up, Down, or Up-and-down (linear only, with a
settable symmetry so the up and down halves can differ). Trigger source Internal (free-running),
External (CMOS edge on Aux In, rising or falling), or Manual (on-screen button).

Start/Stop and Center/Span are two views of the same range. `Trig Out` emits a pulse at the
start of each sweep (internal and manual triggering only). With external or manual triggering
the frequency returns to the idle frequency — selectable as start, end, or start point — and
holds there between sweeps. Log sweep is frequency-only.

## Burst

`Burst` button. `NCycle` emits a set number of carrier cycles per trigger (or `Infinite` for a
continuous carrier after one trigger); `Gated` follows a gate signal with selectable polarity.

Internal triggering uses `Burst Period` as the repetition rate. Manual triggering adds a
`Burst Counter` — the number of bursts emitted per button press. `Trig Delay` has a
hardware-limited minimum. `Trig Out` can align to the rising or falling edge.

## Channel copy, coupling and tracking

`Utility > CH Copy Coupling`. Three mutually exclusive features:

- **Channel Copy** — one-shot copy of all parameters, CH1⇒CH2 or CH2⇒CH1.
- **Channel Coupling** — frequency, amplitude and/or phase coupled by a deviation or a ratio,
  so changing one channel drags the other. Both channels must be on basic waveforms.
- **Track** — CH2 becomes a live mirror of CH1; the UI locks to CH1 and you cannot switch.

`Trigger CH` (single or dual) makes a manual trigger fire both channels at once. Only valid in
burst manual-trigger mode, and mutually exclusive with Track.

## Output setup

`Utility > Output Setup`: `Load` (HighZ, or 50 Ω–100 kΩ), `Polarity` (Normal/Invert — note the
sync output is *not* inverted with the waveform), `EqPhase` (realign both channels at their
current settings), `Wave Combine` (output CH1, or CH1+CH2 summed, on each connector),
`Amplitude` (a maximum-output ceiling applied to both channels immediately), and `Power-on State`
(requires PowerOn Setting to be Last or Custom).

## Utility tree

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

## Phase mode

Under `Utility > Page 1/3 > Clock`:

- **Phase Locked** — both DDS engines reset on any frequency change, so the CH1–CH2 phase
  difference stays fixed. Phase is settable only in this mode.
- **Independent Channel** — no reset; the phase relationship drifts randomly and the phase
  parameter is hidden entirely.
- **Frequency Compensation** — corrects the frequency control word so integer-multiple channel
  frequencies don't drift apart from rounding error.

## Counter

`Utility > Counter`. Displays Frequency/Period, positive and negative pulse width, and duty.
`RefFreq` sets the reference for the ppm deviation reading. `TrigLev` defaults to 0 V, range
−3 V to +1.5 V. Under `Setup`: `HFR` (high-frequency rejection, default off), `Mode` (AC/DC
coupling), `Type` (Slow = more samples/more accurate, Fast = fewer/quicker).

Rule of thumb: HFR **on** below 250 kHz, **off** above — and the full 200 MHz range needs it off.

## Store / Recall

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

## Self test and touch calibration

`Utility > Test/Cal > SelfTest`:

- **ScrTest** — full-screen red/green/blue for dead pixels and scratches. `7` cycles colours,
  `8` exits.
- **KeyTest** — rotate each knob and press each button, watching the on-screen counter and
  highlights. Exit with `8` pressed three times.
- **LEDTest** — `7` steps through each button LED, `8` exits.
- **BoardTest** — internal chip self-check; everything should read `Pass`. A failure means a
  hardware fault needing service.

`TouchCal` recalibrates the touchscreen by tapping four corner targets in sequence.

## Multi-device synchronisation

Master `10MHz Out` → each slave's `10MHz In`, with slaves set to external clock. Master's
`Trig/Sync` → each slave's `Trig/Sync`, splitting where needed. Set the same output frequency
everywhere, enable outputs, trigger sync from the master. Expect a fixed phase offset from
cable propagation delay — use matched cables and the "compensate for slave delay" setting
(`CASCADE ... DELAY,<0–25 µs>` over SCPI) to null it.
