# Connecting to an SDG2000X

Four transports, in rough order of how often they are the right answer: USB (USBTMC), LAN
(VXI-11), LAN (raw socket), LAN (Telnet). GPIB exists via an optional adapter. Everything
below carries the same SCPI payload — only the plumbing differs.

## Contents

- [USB / USBTMC](#usb--usbtmc)
- [Finding the resource string](#finding-the-resource-string)
- [Linux without VISA](#linux-without-visa)
- [pyvisa-py: VISA-compatible, no NI install](#pyvisa-py-visa-compatible-no-ni-install)
- [LAN](#lan)
- [GPIB](#gpib)
- [Session hygiene that actually matters](#session-hygiene-that-actually-matters)
- [Other languages](#other-languages)
- [Shell one-liners](#shell-one-liners)
- [Troubleshooting a connection](#troubleshooting-a-connection)

## USB / USBTMC

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

## Finding the resource string

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

## Linux without VISA

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

## pyvisa-py: VISA-compatible, no NI install

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

## LAN

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

## GPIB

Requires the optional Siglent USB-GPIB adapter: its USB end goes into the instrument's **front**
USB Host port, its GPIB end into the controller's card. Address defaults to 18, settable 1–30
under `Utility > Interface > GPIB`, stored non-volatile and shown at power-on. Resource string
`GPIB0::18::INSTR`. There is no native GPIB connector on this instrument.

## Session hygiene that actually matters

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

## Other languages

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

## Shell one-liners

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
python scripts/sdg2000x.py --send 'C1:BSWV WVTP,SINE,FRQ,1e6,AMP,2'
python scripts/sdg2000x.py --query 'C1:BSWV?'
python scripts/sdg2000x.py --resource TCPIP0::192.168.1.50::INSTR --query '*IDN?'
```

## Troubleshooting a connection

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
other queries. See the parsing notes in `SKILL.md`.

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
that is the only test that distinguishes them. See `scpi-reference.md` for the full account.

**Everything works but the script is slow.** Each `BSWV` write costs about 45 ms on this
instrument regardless of what it changes, while a query round trip is about 4 ms. Combine
parameters into a single `BSWV` command rather than issuing one per parameter, and drop any
`sleep()` calls between writes — USBTMC writes are flow-controlled, so nothing is lost by
sending them back to back.

**A LAN query raises `UnicodeDecodeError`.** `SYST:COMM:LAN:GAT?` returns bytes that are not
valid UTF-8 on firmware 2.01.01.39R7, and the IP and subnet queries return malformed strings.
This is a firmware bug, not your code. Read the network settings from the front panel.
