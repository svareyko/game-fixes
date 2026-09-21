#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cossacks: Back to War (Steam appid 4850) - desktop resolution, cut-off menu, mission crash.

Three independent changes. Details and reasoning: README.md and docs/how-it-works.md.

  1. csemu.dll @ signature "80 7C 24 17 03 75"  (game file, one byte)
     Lifts the "EDID must be exactly version 1.3" requirement (jne -> jb).
     Without it the shim switches itself off and the game changes the REAL
     desktop resolution - windows on every monitor get rearranged.
     VERIFIED IN GAME.

  2. HIGHDPIAWARE compatibility flag for dmcr.exe  (HKCU registry, no game file touched)
     The game is not DPI aware. The shim renders the frame at the real monitor
     resolution (3840x2160 on a 4K display), while Windows treats the surface as
     logical and blows it up 1.5 times more (display scaling set to 150 percent),
     showing only the top-left two thirds. That is why the bottom of the menu
     is cut off.

  3. dmcr.exe @ signature "3A C3 75 14 C7 05 9C FF 7F 00 00 04 00 00" (one byte)
     Removes the silent fallback to 1024x768 for resolutions that are not in the
     shim's mode list. Needed ONLY to set a resolution the list does not have.
     Applied automatically when it is really needed.

HARD ENGINE CEILING: height <= 2047, width <= 4064.
The screen tile grid at 0x00680DB8 is a 128x128 array of words with a row stride
of 128 (0x00465660 shl eax,7), and bounds are checked only against the number of
tiles on screen (0x00465650, 0x00465658). Rows = height/16. At a height of 2160
there are 135 rows, the write runs past the end of the array and overwrites the
map buffer pointers at 0x00688DB8/0x00688DBC - the game crashes while loading
a mission, at 0x00463F55.

Usage:
    python patch.py status
    python patch.py apply                  # 1024x768, the safest choice
    python patch.py apply --res 2560x1440  # sharper; adds the dmcr.exe patch
    python patch.py revert

Author: bombuilder.by  (https://bombuilder.by)
"""

import argparse
import os
import re
import shutil
import sys

APPID = "4850"
MODE_DAT = "mode.dat"
EXE = "dmcr.exe"

MAX_W, MAX_H = 4064, 2047          # ceiling of the 128x128 tile grid
LAYERS_KEY = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
DPI_FLAG = "HIGHDPIAWARE"

PATCHES = {
    "csemu.dll": dict(
        sig=bytes.fromhex("807c24170375"),
        pos=5, orig=0x75, new=0x72,
        what="EDID: accept version 1.3 and newer, not only 1.3 (jne -> jb)",
    ),
    "dmcr.exe": dict(
        sig=bytes.fromhex("3ac37514c7059cff7f0000040000"),
        pos=2, orig=0x75, new=0xEB,
        what="do not reset the resolution to 1024x768 (jne -> jmp)",
    ),
}


# --- locating the installed game --------------------------------------------
def steam_libraries():
    for base in (r"C:\Program Files (x86)\Steam",
                 os.path.expandvars(r"%ProgramFiles(x86)%\Steam")):
        vdf = os.path.join(base, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            with open(vdf, encoding="utf-8", errors="replace") as f:
                return [p.replace("\\\\", "\\")
                        for p in re.findall(r'"path"\s+"([^"]+)"', f.read())]
    return []


def find_game_dir(explicit=None):
    if explicit:
        return explicit
    for lib in steam_libraries():
        manifest = os.path.join(lib, "steamapps", "appmanifest_%s.acf" % APPID)
        if not os.path.isfile(manifest):
            continue
        with open(manifest, encoding="utf-8", errors="replace") as f:
            m = re.search(r'"installdir"\s+"([^"]+)"', f.read())
        if m:
            d = os.path.join(lib, "steamapps", "common", m.group(1), "bin")
            if os.path.isdir(d):
                return d
    return None


# --- patching files ---------------------------------------------------------
def locate(data, spec):
    """Offset of the byte to patch. Refuses when the match is ambiguous:
    silently patching the wrong address is worse than refusing to work."""
    sig, pos = spec["sig"], spec["pos"]
    alt = sig[:pos] + bytes([spec["new"]]) + sig[pos + 1:]
    a = [m.start() for m in re.finditer(re.escape(sig), data)]
    b = [m.start() for m in re.finditer(re.escape(alt), data)]
    if len(a) + len(b) != 1:
        raise SystemExit(
            "REFUSED: the signature was found %d time(s) (original) and %d time(s) (patched), "
            "exactly one match was expected. The game was probably updated - "
            "see README.md." % (len(a), len(b)))
    return (a or b)[0] + pos


def disasm(data, off, name):
    """Verifies the result with a disassembler. Decoding starts at the
    beginning of the signature - that is known to be an instruction boundary."""
    spec = PATCHES[name]
    pos = spec["pos"]
    start = off - pos
    chunk = data[start:start + len(spec["sig"]) + 2]
    # csemu.dll: imagebase 0x10000000, .text VA 0x1000 / RA 0x400
    # dmcr.exe : imagebase 0x00400000, RA == VA for .text/.rdata/.data
    va = (0x10000000 + start - 0x400 + 0x1000) if name == "csemu.dll" else (0x400000 + start)
    try:
        import capstone
    except ImportError:
        return "    bytes %s (capstone is not installed)" % chunk.hex(" ")
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    return "\n".join("    %08x  %-22s %s %s" % (i.address, i.bytes.hex(), i.mnemonic, i.op_str)
                     for i in md.disasm(chunk, va))


def patch_state(bindir, name):
    data = open(os.path.join(bindir, name), "rb").read()
    off = locate(data, PATCHES[name])
    return data, off, data[off]


def set_patch(bindir, name, want):
    spec = PATCHES[name]
    path = os.path.join(bindir, name)
    data, off, cur = patch_state(bindir, name)
    target = spec["new"] if want else spec["orig"]
    if cur == target:
        print("  %-10s already %s" % (name, "patched" if want else "original"))
    else:
        if cur not in (spec["orig"], spec["new"]):
            raise SystemExit("REFUSED: %s offset 0x%X holds 0x%02X, expected 0x%02X or 0x%02X."
                             % (name, off, cur, spec["orig"], spec["new"]))
        backup = path + ".orig"
        if not os.path.isfile(backup):
            shutil.copy2(path, backup)
            print("  backup -> %s" % os.path.basename(backup))
        buf = bytearray(data)
        buf[off] = target
        try:
            with open(path, "wb") as f:
                f.write(buf)
        except PermissionError:
            raise SystemExit(
                "REFUSED: %s is in use by another process - most likely the game is still running\n"
                "(that includes an open BugTrap crash report window).\n"
                "Close the game and try again. To check: tasklist | findstr /i \"dmcr csbtw\"" % name)
        print("  %-10s 0x%X: 0x%02X -> 0x%02X  (%s)" % (name, off, cur, target, spec["what"]))
    check = open(path, "rb").read()
    if check[off] != target:
        raise SystemExit("REFUSED: the byte in %s does not match after writing." % name)
    print(disasm(check, off, name))


# --- DPI flag in the registry (does not touch game files) -------------------
def dpi_get(exe_path):
    import winreg
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, LAYERS_KEY)
        v, _ = winreg.QueryValueEx(k, exe_path)
        return v
    except OSError:
        return None


def dpi_set(exe_path, want):
    import winreg
    cur = dpi_get(exe_path)
    has = bool(cur) and DPI_FLAG in cur
    if has == want:
        print("  DPI flag   already %s" % ("set" if want else "cleared"))
        return
    k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, LAYERS_KEY, 0, winreg.KEY_ALL_ACCESS)
    if want:
        # keep layers set by somebody else, if there were any
        parts = [p for p in (cur or "~").split() if p and p != "~" and p != DPI_FLAG]
        val = " ".join(["~"] + parts + [DPI_FLAG])
        winreg.SetValueEx(k, exe_path, 0, winreg.REG_SZ, val)
        print("  DPI flag   set: %s" % val)
    else:
        parts = [p for p in (cur or "").split() if p and p != "~" and p != DPI_FLAG]
        if parts:
            winreg.SetValueEx(k, exe_path, 0, winreg.REG_SZ, " ".join(["~"] + parts))
            print("  DPI flag   cleared, other layers kept")
        else:
            try:
                winreg.DeleteValue(k, exe_path)
                print("  DPI flag   cleared, registry value deleted")
            except OSError:
                print("  DPI flag   there was no registry value")


# --- mode.dat ---------------------------------------------------------------
def read_mode(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="ascii", errors="replace") as f:
        return [int(p) for p in f.read().split() if re.fullmatch(r"-?\d+", p)]


def monitor_native():
    """Native resolution of the primary monitor from its EDID - the same way csemu does it."""
    try:
        import winreg
    except ImportError:
        return None
    best = None
    try:
        disp = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum\DISPLAY")
    except OSError:
        return None
    for i in range(winreg.QueryInfoKey(disp)[0]):
        mk = winreg.OpenKey(disp, winreg.EnumKey(disp, i))
        for j in range(winreg.QueryInfoKey(mk)[0]):
            try:
                dp = winreg.OpenKey(mk, winreg.EnumKey(mk, j) + r"\Device Parameters")
                edid, _ = winreg.QueryValueEx(dp, "EDID")
            except OSError:
                continue
            if len(edid) < 128:
                continue
            h = ((edid[58] & 0xF0) << 4) | edid[56]
            v = ((edid[61] & 0xF0) << 4) | edid[59]
            if 640 <= h <= 8192 and 480 <= v <= 8192:
                best = (h, v)
    return best


def best_fit(native):
    """The maximum the engine can handle on this monitor.
    The width is the native one (if it fits), the height is the largest
    multiple of 16 within the ceiling. The shim stretches the frame to the
    native resolution."""
    if not native:
        return None
    nw, nh = native
    w = min(nw, (MAX_W // 32) * 32)
    h = min(nh, (MAX_H // 16) * 16)
    return w, h


def check_limits(w, h):
    """Ceiling of the engine's tile grid. Going above it means memory corruption
    and a crash while loading a mission, not just a distorted picture."""
    rows, cols = h // 16, w // 32
    if h > MAX_H or w > MAX_W:
        raise SystemExit(
            "REFUSED: %dx%d is above the engine ceiling (width <= %d, height <= %d).\n"
            "The tile grid at 0x00680DB8 is a 128x128 array; %dx%d needs %d columns "
            "and %d rows.\nThe write would run past the end of the array and overwrite the map "
            "buffer pointers (0x00688DBC) -\nthe game would crash while loading a mission, "
            "at 0x00463F55. See README.md."
            % (w, h, MAX_W, MAX_H, w, h, cols, rows))
    return rows, cols


# --- commands ---------------------------------------------------------------
def cmd_status(bindir):
    print("Game folder: %s\n" % bindir)
    for name in PATCHES:
        data, off, cur = patch_state(bindir, name)
        spec = PATCHES[name]
        state = {spec["orig"]: "ORIGINAL", spec["new"]: "PATCHED"}.get(cur, "UNKNOWN")
        print("%-10s %-10s offset 0x%X, byte 0x%02X, backup %s"
              % (name, state, off, cur,
                 "present" if os.path.isfile(os.path.join(bindir, name + ".orig")) else "NONE"))
        print("           %s" % spec["what"])
        print(disasm(data, off, name))
    exe = os.path.join(bindir, EXE)
    v = dpi_get(exe)
    print("\nDPI flag (HKCU\\...\\AppCompatFlags\\Layers):")
    print("   %s" % (("set: %s" % v) if v and DPI_FLAG in v else ("other layers only: %s" % v) if v else "NOT SET"))
    nat = monitor_native()
    print("Native monitor resolution (EDID): %s" % ("%dx%d" % nat if nat else "not detected"))
    m = read_mode(os.path.join(bindir, MODE_DAT))
    if m and len(m) >= 2:
        w, h = m[0], m[1]
        rows, cols = h // 16, w // 32
        ok = "within limits" if (w <= MAX_W and h <= MAX_H) else "ABOVE THE CEILING - the game will crash"
        print("mode.dat: %s" % " ".join(map(str, m)))
        print("   missions are rendered at %dx%d -> grid of %d columns x %d rows (%s, maximum 127x127)"
              % (w, h, cols, rows, ok))
    else:
        print("mode.dat: file not found")
    bf = best_fit(nat)
    if bf:
        print("Engine ceiling: %dx%d. Maximum for this monitor: %dx%d"
              % (MAX_W, MAX_H, bf[0], bf[1]))
    print("\nThe game menu is always rendered at 1024x768 (0x004b2375 -> RealLx/RealLy),")
    print("mode.dat does not affect the menu - only missions.")


def cmd_apply(bindir, res):
    native = monitor_native()
    m = re.fullmatch(r"(\d+)x(\d+)", res)
    if not m:
        raise SystemExit("The resolution is given as WIDTHxHEIGHT, for example 1024x768 or 2560x1440.")
    w, h = int(m.group(1)), int(m.group(2))
    rows, cols = check_limits(w, h)
    in_list = bool(native) and ((w, h) == native or (w, h) == (1024, 768))

    print("Game files:")
    set_patch(bindir, "csemu.dll", True)          # always needed
    set_patch(bindir, "dmcr.exe", not in_list)    # only for modes outside the shim's list

    print("\nRegistry:")
    dpi_set(os.path.join(bindir, EXE), True)

    mp = os.path.join(bindir, MODE_DAT)
    fields = read_mode(mp) or [1024, 768, 85, 0, 0, 0, 7, 6, 1, 0]
    while len(fields) < 10:
        fields.append(0)
    if os.path.isfile(mp) and not os.path.isfile(mp + ".orig"):
        shutil.copy2(mp, mp + ".orig")
        print("\n  backup -> mode.dat.orig")
    old = "%dx%d" % (fields[0], fields[1])
    fields[0], fields[1] = w, h
    with open(mp, "w", encoding="ascii", newline="") as f:
        f.write(" ".join(map(str, fields)))
    print("\nmode.dat: %s -> %dx%d   (grid %dx%d, ceiling 127x127)" % (old, w, h, cols, rows))
    if native and (w, h) != native:
        print("  the shim will stretch %dx%d to %dx%d, the desktop resolution is not changed" % (w, h, native[0], native[1]))
    if not in_list:
        print("\n  WARNING: %dx%d is not in the shim's mode list. Do not open the\n"
              "  in-game Options screen - this mode is not there, so the game silently\n"
              "  switches to the first mode of the list (%s) and writes it to mode.dat\n"
              "  on exit. If that mode is above the engine ceiling, the next mission\n"
              "  will crash. Fix: run apply again."
              % (w, h, ("%dx%d" % native) if native else "native"))
    print("\nDone. Start the game through Steam.")


def same_file_but_for_the_patch(path, backup):
    """True if `backup` is `path` give or take the one patched byte."""
    with open(path, "rb") as f:
        cur = f.read()
    with open(backup, "rb") as f:
        old = f.read()
    return len(cur) == len(old) and sum(1 for x, y in zip(cur, old) if x != y) <= 1


def cmd_revert(bindir, force=False):
    for name in list(PATCHES) + [MODE_DAT]:
        p = os.path.join(bindir, name)
        b = p + ".orig"
        if not os.path.isfile(b):
            print("No backup for %s - skipping." % name)
            continue
        # A backup of an older game file must never overwrite a newer one: check before writing.
        # mode.dat is the player's own settings file, any backup of it is fine.
        if name in PATCHES and os.path.isfile(p) and not force and not same_file_but_for_the_patch(p, b):
            print("REFUSED %s: the backup does not belong to this file - the game was probably\n"
                  "        updated or repaired since. Nothing was written. Delete %s.orig by hand.\n"
                  "        (--force overrides this.)" % (name, name))
            continue
        shutil.copy2(b, p)
        os.remove(b)
        print("Restored %s" % name)
    dpi_set(os.path.join(bindir, EXE), False)


def main():
    ap = argparse.ArgumentParser(description="Cossacks: Back to War - desktop resolution, menu, mission crash")
    ap.add_argument("action", choices=["status", "apply", "revert"])
    ap.add_argument("--dir", help=r"path to ...\Cossacks Back to War\bin")
    ap.add_argument("--res", default="1024x768",
                    help="mission resolution, WIDTHxHEIGHT (default 1024x768; "
                         "ceiling %dx%d)" % (MAX_W, MAX_H))
    ap.add_argument("--force", action="store_true",
                    help="revert even if a backup does not match the current game file")
    a = ap.parse_args()

    bindir = find_game_dir(a.dir)
    if not bindir or not os.path.isfile(os.path.join(bindir, "csemu.dll")):
        raise SystemExit("Could not find the game. Pass the path: --dir \"...\\Cossacks Back to War\\bin\"")

    {"status": lambda: cmd_status(bindir),
     "apply": lambda: cmd_apply(bindir, a.res),
     "revert": lambda: cmd_revert(bindir, a.force)}[a.action]()


if __name__ == "__main__":
    sys.exit(main())
