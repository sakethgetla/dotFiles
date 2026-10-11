# X-Bows Lite key remapper (Linux)

Remaps keys on the **X-Bows Lite** keyboard (USB `320f:5055`, "Evision X-BOWS Ergonomic Keyboard",
Evision VS11K09A chip) from Linux. The vendor's configuration software only runs on Windows.
The remap is stored **in the keyboard's own memory**, so it works on any computer and in BIOS, with no daemon.

- `xbows.py`: the tool (Python 3, standard library only)
- `mac.layout`: Mac layout (left space = Ctrl, middle Ctrl = Cmd, middle Shift = Esc)
- `my.layout`: **my current layout**. This file is the source of truth (see "Gotchas")
- `70-xbows.rules`: udev rule so the tool runs without sudo

## Quick start

```sh
cd ~/me/dotFiles/keyboardLayouts/xbowsLite
./xbows.py apply -n my.layout   # preview
./xbows.py apply my.layout      # write to the keyboard
./xbows.py reset                # factory default layout
./xbows.py dump                 # factory default layout with slot numbers
./xbows.py info                 # raw device info
```

To change a key, add a line to `my.layout` and run `apply`. Then **test by typing**, because the keyboard can't report what it's doing.

### One-time setup on a new machine

```sh
sudo cp 70-xbows.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger --subsystem-match=hidraw
```

The rule gives the logged-in user access (`TAG+="uaccess"`, an ACL that logind manages) to the keyboard's
`/dev/hidraw*` nodes, which are otherwise root-only. Side effect: any process running as you can read raw HID
from this keyboard. Without the rule, use `sudo ./xbows.py ...`.

## Current layout (`my.layout`)

| Physical key | Slot | Default | Now |
|---|---|---|---|
| Left spacebar | @29 | Space | **Super** (lgui) |
| Middle Shift | @41 | `d0 a2 04` (shift) | **Escape** |
| Middle Ctrl | @35 | `d0 a2 03` (did nothing) | **Right Ctrl** (rctrl, so keyd doesn't turn it into Alt) |

Everything else is factory default.

**`mac.layout`:** left spacebar → Ctrl (`rctrl`), middle Ctrl → Super/Cmd (`lgui`), middle Shift → Escape.
Switch with `./xbows.py apply mac.layout`, and switch back with `./xbows.py apply my.layout`. Only one layout is
stored on the keyboard at a time, so it stays in whichever layout was applied last, even on another computer.

## Gotchas (read these first)

1. **The active layout cannot be read back.** Command 0x07 returns the *factory default* map, not what's
   active. So `dump` always shows defaults, and there's no way to verify a write except by typing.
2. **Every `apply` replaces the whole layout** with factory defaults + the layout file's changes.
   Anything set elsewhere (e.g. the Windows driver) is wiped. Keep *all* remaps in `my.layout`.
   Removing a line and re-applying reverts that key.
3. **keyd runs after the keyboard.** `/etc/keyd/default.conf` (applies to all keyboards, `[ids] *`) has:
   ```
   capslock = esc
   esc = capslock
   leftalt = leftcontrol
   leftcontrol = leftalt
   ```
   So a key the keyboard sends as Left Ctrl comes out as **Alt**, and that's why Left Ctrl seems "broken"
   while Right Ctrl works. When a key misbehaves, check keyd first: `sudo keyd monitor` shows what
   keyd receives and sends. keyd doesn't touch Super (lgui), so the space→Super remap passes through.
4. **Middle keys and the right spacebar are special.** Their factory value is `d0 a2 xx`, not a normal key
   code. The factory middle Ctrl (`d0 a2 03`) did **nothing** on Linux, so don't assume a `d0 a2 xx` default
   works. Give these keys an explicit value in `my.layout`. Overwriting one with a normal key works (verified).
   When remapping to Ctrl, use `rctrl`: keyd turns `lctrl` into Alt.
5. Fn (@71, `a0 01 00`) is probably the Fn key, but I haven't tested it. The manual says Fn combos can't be changed.

## Slot map (physical position → slot number)

Slots are a 16×6 matrix, ordered column by column: `slot = column*6 + row`. Names are the factory defaults.
Empty cells are unused (`none`). Slots 96–169 are unused padding (96–125 `20 00 00`, 126–169 `00 00 00`).

| row | c0 | c1 | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | c10 | c11 | c12 | c13 | c14 | c15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 esc | 6 f1 | 12 f2 | 18 f3 | 24 f4 | 30 f5 | 36 | 42 f6 | 48 f7 | 54 f8 | 60 f9 | 66 f10 | 72 f11 | 78 f12 | 84 delete | 90 printscreen |
| 1 | 1 grave | 7 1 | 13 2 | 19 3 | 25 4 | 31 5 | 37 | 43 6 | 49 7 | 55 8 | 61 9 | 67 0 | 73 minus | 79 equal | 85 backspace | 91 |
| 2 | 2 tab | 8 q | 14 w | 20 e | 26 r | 32 t | 38 | 44 y | 50 u | 56 i | 62 o | 68 p | 74 lbracket | 80 rbracket | 86 backslash | 92 pageup |
| 3 | 3 capslock | 9 a | 15 s | 21 d | 27 f | 33 g | 39 mid-bksp | 45 h | 51 j | 57 k | 63 l | 69 semicolon | 75 quote | 81 | 87 enter | 93 pagedown |
| 4 | 4 lshift | 10 z | 16 x | 22 c | 28 v | 34 b | 40 mid-enter | 46 n | 52 m | 58 comma | 64 dot | 70 slash | 76 rshift | 82 | 88 up | 94 |
| 5 | 5 lctrl | 11 lgui | 17 lalt | 23 | 29 space (left) | 35 mid-ctrl | 41 mid-shift | 47 | 53 right-space | 59 | 65 ralt | 71 fn? | 77 rctrl | 83 left | 89 down | 95 right |

Special slots, verified by probing (each one temporarily typed a digit):

| Slot | Factory value | Physical key |
|---|---|---|
| @39 | `d0 a2 01` | middle Backspace |
| @40 | `d0 a2 02` | middle Enter |
| @35 | `d0 a2 03` | middle Ctrl |
| @41 | `d0 a2 04` | middle Shift |
| @53 | `d0 a2 05` | right spacebar |
| @29 | `20 00 2c` | left spacebar (plain Space) |

**Finding an unknown key fast:** write a temporary layout that maps the candidate slots to `1`, `2`, `3`…,
press the key in a text editor, and see which digit appears. Then re-apply `my.layout`.

## Layout file syntax

```
# comment
<from> = <to>
```

- `<from>`: `@N` (slot number, preferred) or a key name. A name is looked up in the factory default layout
  and must match exactly one slot.
- `<to>`: key name, combo (`ctrl+c`, `lshift+lalt`), or `raw:aa,bb,cc` (3 hex bytes).

Key names: `a`–`z`, `0`–`9`, `f1`–`f24`, `esc`, `tab`, `capslock`, `enter`, `backspace`, `space`, `delete`,
`insert`, `home`, `end`, `pageup`, `pagedown`, `up`/`down`/`left`/`right`, `minus`, `equal`, `lbracket`,
`rbracket`, `backslash`, `semicolon`, `quote`, `grave`, `comma`, `dot`, `slash`, `printscreen`, `scrolllock`,
`pause`, `menu`, `numlock`, `kp_0`–`kp_9`, `kp_*` operators, `lctrl` `lshift` `lalt` `lgui` `rctrl` `rshift`
`ralt` `rgui`, `none`.
Aliases: `ctrl` `shift` `alt` (left), `altgr`, `win`/`super`/`gui`/`meta`/`cmd` (= lgui), `caps`, `del`, `ins`,
`pgup`, `pgdn`, `bksp`, `escape`, `return`, `prtsc`, `app`, and punctuation characters (`-` `=` `[` `]` `\` `;` `'` `` ` `` `,` `.` `/`).

## Protocol reference

Reverse-engineered from the vendor's `X-BOWS_Lite.exe` (v1.0.0.0, 2021) and confirmed on the device.

**Interfaces:** interface 0 = boot keyboard. Interface 1 = mouse/consumer/system plus the **vendor
collection** (usage page `0xFF1C`, usage `0x92`, report ID 4, 63-byte in/out). `xbows.py` picks the hidraw
node whose report descriptor contains `06 1c ff`.

**Packet** (64 bytes, written to and read from hidraw; reply has the same layout):

| Byte | Meaning |
|---|---|
| 0 | report ID `0x04` |
| 1–2 | checksum, LE: `sum(pkt[3:64]) & 0xffff` |
| 3 | command (the reply echoes it) |
| 4 | payload length, max `0x38` (56) wired; `0x18` in wireless/dongle mode |
| 5–6 | byte offset, LE |
| 7 | status in reply: `0xff` / `0xfe` = error |
| 8… | payload |

**Commands:**

| Cmd | Purpose |
|---|---|
| `0x01` | begin (send before reads/writes) |
| `0x02` | end / commit (driver sleeps 10 ms before it) |
| `0x03` | device info, 0x22 bytes. `[5]` = key slot count (`0xaa` = 170). Mine: `aa 55 00 00 06 aa 18 00 02 … 0f 32 00 50 00 02 …` |
| `0x07` | read **factory default** keymap, 170×3 bytes |
| `0x09` | write active keymap. Offset = `layer<<9 + off`. Driver only allows layer 0 |
| `0x1b` | read slot→LED index table (not a keymap) |
| `0x05`/`0x06` | read/write config (lighting etc.) |
| `0x0b`, `0x12`, `0x15`, `0x17`, `0x1a`, `0x1c` | other (macros/lighting, not decoded) |
| `0xaa` | wireless-dongle link check (unused when wired) |

**Keymap entry** (3 bytes per slot): `[type, modifier bits, HID usage]`
- type `0x20` = standard key. Modifier bits: `01` LCtrl, `02` LShift, `04` LAlt, `08` LGui, `10` RCtrl,
  `20` RShift, `40` RAlt, `80` RGui.
- A bare modifier key is the bit with usage 0: Left Shift = `20 02 00`, *not* `20 00 e1`.
- Combo: Ctrl+C = `20 01 06`.
- `d0 a2 xx` = special middle keys / right space (see above). `a0 01 00` = probably Fn. In the driver's JSON, the
  `Assignment` field is these 3 bytes as an int (e.g. `0x200029` = Esc).

**Official driver's save sequence:** info (3) → begin (1) → write keymap (9) in 56-byte chunks → end (2).
It reads defaults with begin → info → 0x07 → 0x1b → end.

### Reverse-engineering notes (for next time)

- The installer is NSIS: `7z x X-BOWS_Lite.exe app.7z`, then `7z x app.7z`. The real program is
  `X-BOWS_Lite.exe` (32-bit, MFC + DuiLib). The vendor's PDF manual has no protocol details.
- Disassembled with Python `capstone` + `pefile` in a venv. Interesting addresses (image base 0x400000):
  - `0x470f60` transfer(): copies into 64-byte buffer, write, read reply, checks the echoed byte 3
  - `0x471b90` … `0x473df0` one function per command, all built the same way
  - `0x497650` save keymap (cmd 9). `0x485c20` read sequence (cmds 7 + 0x1b)
  - `0x474080` chunk size setter: wired 0x38, dongle 0x18
- Uses `HidD_SetOutputReport`/`WriteFile` (output reports, not feature reports). On Linux, plain
  `write()`/`read()` on hidraw works.
- Device data templates are in `app/DefaultData/*.json` (KeyList `Assignment` ints).
- **jlquinn/xbows-driver** (GitHub) is for a *different* X-Bows (`1ea7:0907`), with a different protocol
  (CRC-16/CCITT, command in byte 0, no report ID). It doesn't work with the Lite. Its `doc/spec.md` has
  a good usbmon/Wireshark capture guide if something ever needs sniffing from a Windows VM.

## Troubleshooting

- `No permission to open /dev/hidrawN`: udev rule missing, or you're not on the local seat (ssh). Use sudo.
- `config interface not found`: keyboard unplugged, or it's in wireless mode with a different PID.
- `no reply to command`: replug the keyboard and retry.
- Key does the wrong thing: check keyd (`sudo keyd monitor`) before blaming the keyboard.
- Something is badly wrong: `./xbows.py reset` (factory layout), then `apply my.layout`.
