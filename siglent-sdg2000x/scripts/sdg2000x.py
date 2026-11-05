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
