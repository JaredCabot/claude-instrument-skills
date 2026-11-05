# Arbitrary waveforms on the SDG2000X

Three distinct things get called "arbitrary waveform" here and confusing them wastes hours:

1. **Built-in waveforms** — 197 shapes baked into the instrument, selected by index
   (`C1:ARWV INDEX,26`). Nothing is transferred.
2. **User waveforms stored on the instrument** — uploaded once by name, then recalled by name
   (`C1:ARWV NAME,mywave`). This is what `WVDT` writes.
3. **Waveform files on a USB stick or made in EasyWaveX** — `.bin`, `.csv`, `.dat` loaded
   through the front-panel file manager.

## Playback modes: DDS vs TrueArb

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

## Uploading waveform data over SCPI

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

The bundled `scripts/sdg2000x.py` wraps all of this in `upload_arb()`, including scaling a
float array in −1…+1 to codewords and clipping instead of wrapping — worth reusing, because a
value that overflows int16 wraps from +full-scale to −full-scale and produces a waveform with
violent spikes that looks like a hardware fault.

**Verified on an SDG2122X (firmware 2.01.01.39R7):** a 4096-point sine uploaded in about
0.5 s, left the error queue clean, appeared immediately in `STL? USER`, and read back
byte-identical.

### Things that go wrong here

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

## Reading a waveform back

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
single trailing `\n`). `scripts/sdg2000x.py` implements this as `download_arb()`.

One more firmware wrinkle: **`WVDT? USER,<name>` queues a spurious
`-108,"Parameter not allowed"` even when it succeeds and returns correct data.** It is the only
command in normal use that does this. Drain the error queue after a readback, or a later
`SYST:ERR?` check will report a failure that never happened. *(verified)*
`WVDT? M<n>` fetches a built-in waveform (M0–M196, 32 KB each) in the same shape. Always
`read_raw()`, never `read()` — the binary will contain bytes that are not valid UTF-8.

`STL?`, `STL? BUILDIN` and `STL? USER` list what is stored. Empty user slots read `EMPTY`.

## File formats

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

## EasyWaveX

Siglent's free PC editor. Connects over USB or LAN, offers twelve standard shapes, freehand and
line drawing, point/coordinate entry with connect and smooth options, and equation entry, then
sends the result to a chosen channel. It also exports CSV, which is often the most convenient
path: draw in EasyWaveX or generate in Python, save CSV, load from a USB stick.

For anything scriptable, generating the array yourself and using `WVDT` is faster and
reproducible; EasyWaveX earns its place for one-off shapes you want to draw by eye.

## A worked example: two synchronised digital patterns

A common real task — a clock on CH1 and a data pattern on CH2, locked together:

1. Generate both patterns as arrays of the same length, at the same sample rate.
2. Upload each with `WVDT` and recall with `ARWV NAME,...`.
3. Put both channels in TrueArb at the same rate: `C1:SRATE MODE,TARB,VALUE,<rate>` and the
   same for `C2`.
4. Lock them: `MODE PHASELOCKED`, then `COUP FCOUP,ON,FRAT,1`.
5. `EQPHASE` to align, then enable both outputs with `OUT_BOTHCH ON`.

Use TrueArb, not DDS — DDS interpolation will round the edges of a digital pattern and destroy
the timing relationship you are trying to create.
