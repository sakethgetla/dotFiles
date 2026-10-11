#!/usr/bin/env python3
"""Linux key remapper for the X-Bows Lite keyboard (USB 320f:5055, Evision chip).

Protocol (reverse-engineered from the vendor's Windows driver X-BOWS_Lite.exe):
  64-byte output/input reports with report ID 0x04 on the vendor interface (usage page 0xFF1C).
    [0]    0x04 report id
    [1:3]  checksum, little endian = sum(packet[3:64]) & 0xffff
    [3]    command
    [4]    payload length (<= 0x38)
    [5:7]  offset, little endian
    [7]    status in replies (0xff / 0xfe = error)
    [8:]   payload
  Commands: 0x01 begin, 0x02 end, 0x03 device info (0x22 bytes, [5] = key count),
            0x07 read the *factory default* keymap, 0x09 write the active keymap
            (offset = layer << 9), 3 bytes per key: [0x20, modifier bits, HID usage].
  The active keymap cannot be read back, so every write sends the full map:
  factory defaults + the layout file's changes.
"""
import argparse
import glob
import os
import select
import sys
import time

VID, PID = 0x320F, 0x5055
REPORT_ID = 0x04
CHUNK = 0x38

CMD_BEGIN = 0x01
CMD_END = 0x02
CMD_INFO = 0x03
CMD_READ_DEFAULTS = 0x07
CMD_WRITE_KEYMAP = 0x09


# --- key names -------------------------------------------------------------------------------

HID_NAMES = {0x00: "none"}
for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"):
    HID_NAMES[0x04 + i] = c
for i, c in enumerate("1234567890"):
    HID_NAMES[0x1E + i] = c
HID_NAMES.update({
    0x28: "enter", 0x29: "esc", 0x2A: "backspace", 0x2B: "tab", 0x2C: "space",
    0x2D: "minus", 0x2E: "equal", 0x2F: "lbracket", 0x30: "rbracket", 0x31: "backslash",
    0x32: "nonus_hash", 0x33: "semicolon", 0x34: "quote", 0x35: "grave", 0x36: "comma",
    0x37: "dot", 0x38: "slash", 0x39: "capslock",
    0x46: "printscreen", 0x47: "scrolllock", 0x48: "pause", 0x49: "insert", 0x4A: "home",
    0x4B: "pageup", 0x4C: "delete", 0x4D: "end", 0x4E: "pagedown", 0x4F: "right",
    0x50: "left", 0x51: "down", 0x52: "up", 0x53: "numlock",
    0x54: "kp_slash", 0x55: "kp_asterisk", 0x56: "kp_minus", 0x57: "kp_plus", 0x58: "kp_enter",
    0x63: "kp_dot", 0x64: "nonus_backslash", 0x65: "menu", 0x67: "kp_equal",
})
for i in range(12):
    HID_NAMES[0x3A + i] = f"f{i + 1}"
    HID_NAMES[0x68 + i] = f"f{i + 13}"
for i in range(9):
    HID_NAMES[0x59 + i] = f"kp_{i + 1}"
HID_NAMES[0x62] = "kp_0"

ALIASES = {
    "escape": "esc", "return": "enter", "bksp": "backspace", "bs": "backspace",
    "caps": "capslock", "del": "delete", "ins": "insert", "pgup": "pageup", "pgdn": "pagedown",
    "ctrl": "lctrl", "control": "lctrl", "shift": "lshift", "alt": "lalt", "altgr": "ralt",
    "gui": "lgui", "win": "lgui", "super": "lgui", "meta": "lgui", "cmd": "lgui",
    "lwin": "lgui", "rwin": "rgui", "lsuper": "lgui", "rsuper": "rgui",
    "app": "menu", "apps": "menu", "compose": "menu", "prtsc": "printscreen", "print": "printscreen",
    "-": "minus", "=": "equal", "[": "lbracket", "]": "rbracket", "\\": "backslash",
    ";": "semicolon", "'": "quote", "`": "grave", ",": "comma", ".": "dot", "/": "slash",
    "period": "dot", "tilde": "grave", "apostrophe": "quote",
}
NAME_TO_HID = {v: k for k, v in HID_NAMES.items()}

# Modifier bits used in the middle byte for combos like ctrl+c.
MOD_BITS = {"lctrl": 0x01, "lshift": 0x02, "lalt": 0x04, "lgui": 0x08,
            "rctrl": 0x10, "rshift": 0x20, "ralt": 0x40, "rgui": 0x80}

KEY_TYPE = 0x20  # entry type for "standard keyboard key"


def norm(name):
    n = name.strip().lower()
    return ALIASES.get(n, n)


def encode_key(spec):
    """'capslock' -> (0x20, 0, 0x39); 'ctrl+c' -> (0x20, 0x01, 0x06); 'raw:aa,bb,cc' -> raw."""
    spec = spec.strip()
    if spec.lower().startswith("raw:"):
        parts = [int(p, 16) for p in spec[4:].replace(" ", "").split(",")]
        if len(parts) != 3 or any(not 0 <= p <= 0xFF for p in parts):
            raise ValueError(f"raw entry needs 3 hex bytes: {spec!r}")
        return tuple(parts)
    parts = [norm(p) for p in spec.split("+")]
    *mods, key = parts
    if key in MOD_BITS:  # a bare modifier key is stored as its bit with no usage code
        mods, key = mods + [key], "none"
    if key not in NAME_TO_HID:
        raise ValueError(f"unknown key name: {key!r}")
    modbits = 0
    for m in mods:
        if m not in MOD_BITS:
            raise ValueError(f"unknown modifier: {m!r} in {spec!r}")
        modbits |= MOD_BITS[m]
    return (KEY_TYPE, modbits, NAME_TO_HID[key])


def describe(entry):
    t, m, c = entry
    if t == KEY_TYPE and c in HID_NAMES:
        mods = [n for n, b in MOD_BITS.items() if m & b]
        return "+".join(mods + [HID_NAMES[c]] if c or not mods else mods)
    return f"raw:{t:02x},{m:02x},{c:02x}"


# --- device I/O ------------------------------------------------------------------------------

class ProtocolError(Exception):
    pass


def find_hidraw():
    for path in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            uevent = open(os.path.join(path, "device", "uevent")).read()
            desc = open(os.path.join(path, "device", "report_descriptor"), "rb").read()
        except OSError:
            continue
        if f"HID_ID=0003:{VID:08X}:{PID:08X}" not in uevent:
            continue
        if b"\x06\x1c\xff" in desc:  # vendor usage page 0xFF1C = config interface
            return "/dev/" + os.path.basename(path)
    return None


class Keyboard:
    def __init__(self, path=None):
        path = path or find_hidraw()
        if not path:
            raise SystemExit("X-Bows Lite (320f:5055) config interface not found. Is it plugged in?")
        try:
            self.fd = os.open(path, os.O_RDWR)
        except PermissionError:
            raise SystemExit(f"No permission to open {path}. Install the udev rule "
                             "(see README.md) or run with sudo.")
        self.path = path
        self.chunk = CHUNK

    def close(self):
        os.close(self.fd)

    def _drain(self):
        while select.select([self.fd], [], [], 0)[0]:
            os.read(self.fd, 64)

    def transfer(self, cmd, length=0, offset=0, payload=b""):
        pkt = bytearray(64)
        pkt[0] = REPORT_ID
        pkt[3] = cmd
        pkt[4] = length
        pkt[5] = offset & 0xFF
        pkt[6] = (offset >> 8) & 0xFF
        pkt[8:8 + len(payload)] = payload
        csum = sum(pkt[3:]) & 0xFFFF
        pkt[1], pkt[2] = csum & 0xFF, csum >> 8
        for attempt in range(3):
            self._drain()
            os.write(self.fd, bytes(pkt))
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                if not select.select([self.fd], [], [], deadline - time.monotonic())[0]:
                    break
                resp = os.read(self.fd, 64)
                if len(resp) >= 8 and resp[0] == REPORT_ID and resp[3] == cmd:
                    if resp[7] in (0xFF, 0xFE):
                        raise ProtocolError(f"command 0x{cmd:02x} rejected (status 0x{resp[7]:02x})")
                    return resp
        raise ProtocolError(f"no reply to command 0x{cmd:02x}")

    def begin(self):
        self.transfer(CMD_BEGIN)

    def end(self):
        time.sleep(0.01)
        self.transfer(CMD_END)

    def info(self):
        size = 0x22
        out = bytearray()
        for off in range(0, size, self.chunk):
            n = min(self.chunk, size - off)
            out += self.transfer(CMD_INFO, n, off)[8:8 + n]
        return bytes(out)

    def read_defaults(self, nkeys):
        size = nkeys * 3
        out = bytearray()
        for off in range(0, size, self.chunk):
            n = min(self.chunk, size - off)
            out += self.transfer(CMD_READ_DEFAULTS, n, off)[8:8 + n]
        return bytes(out)

    def write_keymap(self, data, layer=0):
        for off in range(0, len(data), self.chunk):
            part = data[off:off + self.chunk]
            self.transfer(CMD_WRITE_KEYMAP, len(part), (layer << 9) + off, part)


def read_device():
    """Returns (device info, factory default keymap)."""
    kb = Keyboard()
    try:
        kb.begin()
        info = kb.info()
        keymap = kb.read_defaults(info[5])
        kb.end()
    finally:
        kb.close()
    return info, keymap


def entries(raw):
    return [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]


# --- layout file -----------------------------------------------------------------------------

def parse_layout(path, defaults):
    """Lines: `<from> = <to>`. <from> is `@N` (position from `dump`) or a key name, looked up
    in the factory default layout.  # starts a comment."""
    base = entries(defaults)
    changes = {}
    for lineno, line in enumerate(open(path), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" not in line:
            raise SystemExit(f"{path}:{lineno}: expected `from = to`")
        src, dst = (s.strip() for s in line.split("=", 1))
        try:
            target = encode_key(dst)
            if src.startswith("@"):
                positions = [int(src[1:])]
                if not 0 <= positions[0] < len(base):
                    raise ValueError(f"position {positions[0]} out of range 0..{len(base) - 1}")
            else:
                want = encode_key(src)
                positions = [i for i, e in enumerate(base) if e == want]
                if not positions:
                    raise ValueError(f"no key sends {src!r} in the default layout; use @N")
                if len(positions) > 1:
                    raise ValueError(f"{src!r} is on several positions {positions}; use @N")
        except ValueError as e:
            raise SystemExit(f"{path}:{lineno}: {e}")
        for p in positions:
            changes[p] = target
    return changes


# --- commands --------------------------------------------------------------------------------

def cmd_info(args):
    info, _ = read_device()
    print(f"device: {find_hidraw()}")
    print("info:", info.hex(" "))
    print(f"keys: {info[5]}")


def cmd_dump(args):
    _, defaults = read_device()
    print("# factory default layout (the active layout cannot be read from the keyboard)")
    for i, e in enumerate(entries(defaults)):
        print(f"@{i:<4} {describe(e):<20} {bytes(e).hex(' ')}")


def write_keymap(new):
    kb = Keyboard()
    try:
        nkeys = kb.info()[5]
        if nkeys * 3 != len(new):
            raise SystemExit(f"keyboard reports {nkeys} keys but layout has {len(new) // 3}")
        kb.begin()
        kb.write_keymap(new)
        kb.end()
    finally:
        kb.close()
    print("written (the keyboard accepted every packet; it has no way to read the layout back)")


def cmd_apply(args):
    _, defaults = read_device()
    changes = parse_layout(args.layout, defaults)
    new = bytearray(defaults)
    for p, e in sorted(changes.items()):
        new[p * 3:p * 3 + 3] = bytes(e)
    base = entries(defaults)
    diff = [i for i, e in enumerate(entries(new)) if e != base[i]]
    print("full layout will be replaced: factory defaults plus these changes")
    for i in diff:
        print(f"  @{i:<4} {describe(base[i]):<20} -> {describe(tuple(new[i * 3:i * 3 + 3]))}")
    if not diff:
        print("  (none: this resets the keyboard to its default layout)")
    if args.dry_run:
        print("dry run, nothing written")
        return
    write_keymap(bytes(new))


def cmd_reset(args):
    _, defaults = read_device()
    write_keymap(defaults)


def main():
    ap = argparse.ArgumentParser(description="X-Bows Lite key remapper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info", help="show device info").set_defaults(fn=cmd_info)
    sub.add_parser("dump", help="print the factory default keymap with positions").set_defaults(fn=cmd_dump)
    p = sub.add_parser("apply", help="write factory defaults + the changes in a layout file")
    p.add_argument("layout")
    p.add_argument("-n", "--dry-run", action="store_true")
    p.set_defaults(fn=cmd_apply)
    sub.add_parser("reset", help="write the factory default layout").set_defaults(fn=cmd_reset)
    args = ap.parse_args()
    try:
        args.fn(args)
    except ProtocolError as e:
        raise SystemExit(f"error: {e}")


if __name__ == "__main__":
    main()
