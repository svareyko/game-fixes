#!/usr/bin/env python3
"""
Splinter Cell Blacklist - NetResult pool leak fix (crash to desktop after about 28 minutes).

THE BUG
    nsOnlineConnection::StateProxyDetection takes an object from the NetResult pool in
    Enter (vtable slot [8]) and stores the pointer at this+0x34, but its Exit (slot [9])
    does NOTHING: the slot points at a shared empty stub, `ret 4`. The twin states with
    exactly the same Enter have a real Exit in slot [9], and that Exit calls Free.
    As a result every pass through ProxyDetection permanently uses up one slot of twenty.
    After about 28 minutes the pool is empty, Alloc returns NULL, and the first caller
    (usually StateLoggingInToRdv) dereferences the null pointer -> 0xC0000005.

WHAT THE PATCH DOES
    It changes ONE dword in .rdata: slot [9] in the vtable of StateProxyDetection is
    pointed at the same Exit that StatePlatformNetworkStart already uses.
    Not a single byte of new code is added - the function is already in the binary.

    Neither the vtable nor the function is looked up by a hardcoded address: both are
    found through RTTI, so the patch survives a game update as long as the classes keep
    their names.

Commands:
    python patch_pool_leak.py            show what would be done (read-only)
    python patch_pool_leak.py apply      make a backup and patch
    python patch_pool_leak.py revert     restore the original
    python patch_pool_leak.py scan       lookup details (for new game versions)

Options:
    --dir <path>    game install folder instead of auto-detection through the registry
    --exe <path>    one specific exe
    --force         revert even though the file is not the one the backup was made from
                    (only after you have checked by hand that it is safe)

Requires Python 3.8+ and nothing else.

Author: bombuilder.by  (https://bombuilder.by)
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXE_NAMES = ("Blacklist_DX11_game.exe", "Blacklist_game.exe")
EXE_SUBDIR = os.path.join("src", "SYSTEM")
UPLAY_APP_ID = "91"

BROKEN = "StateProxyDetection"        # the state whose Exit is empty
DONOR = "StatePlatformNetworkStart"   # the state with a correct Exit and the same Enter
NAMESPACE = "nsOnlineConnection"
EXIT_SLOT = 9

NOOP_STUB = b"\xC2\x04\x00"           # ret 4 - the body of the empty stub

# The correct Exit: add ecx,0x34 / push ecx / mov ecx,[imm32] / call rel32 / ret 4
EXIT_SHAPE = re.compile(rb"\x83\xC1\x34\x51\x8B\x0D(....)\xE8(....)\xC2\x04\x00", re.S)
# Enter: mov ecx,[imm32] / call rel32 / ... / mov [esi+0x34], eax
ENTER_GLOBAL = re.compile(rb"\x8B\x0D(....)\xE8....", re.S)


def load(path):
    with open(path, "rb") as f:
        return bytearray(f.read())


def sha256(d):
    return hashlib.sha256(bytes(d)).hexdigest()


def hx(b):
    return " ".join("%02X" % c for c in b)


class PE:
    def __init__(self, d):
        self.d = d
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        if d[pe:pe + 4] != b"PE\0\0":
            raise ValueError("not a PE file")
        if struct.unpack_from("<H", d, pe + 4)[0] != 0x14C:
            raise ValueError("expected a 32-bit x86 PE")
        nsec = struct.unpack_from("<H", d, pe + 6)[0]
        optsz = struct.unpack_from("<H", d, pe + 20)[0]
        self.image_base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
        self.secs = []
        o = pe + 24 + optsz
        for i in range(nsec):
            b = o + i * 40
            nm = d[b:b + 8].rstrip(b"\0").decode("ascii", "replace")
            vsz, va, rsz, praw = struct.unpack_from("<IIII", d, b + 8)
            self.secs.append((nm, va, vsz, praw, rsz))

    def sec_of_va(self, va):
        rva = va - self.image_base
        for s in self.secs:
            if s[1] <= rva < s[1] + max(s[2], s[4]):
                return s
        return None

    def va2off(self, va):
        s = self.sec_of_va(va)
        if not s:
            return None
        return s[3] + (va - self.image_base - s[1])

    def off2va(self, off):
        for nm, va, vsz, praw, rsz in self.secs:
            if praw <= off < praw + rsz:
                return self.image_base + va + (off - praw)
        return None

    def u32_va(self, va):
        o = self.va2off(va)
        return None if o is None else struct.unpack_from("<I", self.d, o)[0]

    def find_dword(self, value):
        """All file offsets where this dword occurs; callers keep only the hits inside a section."""
        pat = struct.pack("<I", value)
        out, off = [], 0
        while True:
            i = self.d.find(pat, off)
            if i < 0:
                break
            out.append(i)
            off = i + 1
        return out


def find_vtable(pe, cls, ns):
    """Finds the vtable of a class through RTTI. Returns (vtable_va, type_descriptor_va)."""
    name = (".?AV%s@%s@@" % (cls, ns)).encode()
    hits = [m.start() for m in re.finditer(re.escape(name) + rb"\x00", bytes(pe.d))]
    if len(hits) != 1:
        raise SystemExit("Type name %s found %d times - expected 1." % (name.decode(), len(hits)))
    td_va = pe.off2va(hits[0] - 8)     # the TypeDescriptor starts 8 bytes before the name
    if td_va is None:
        raise SystemExit("The type descriptor of %s lies outside every section." % cls)

    cols = []
    for off in pe.find_dword(td_va):
        col_va = pe.off2va(off - 12)   # pTypeDescriptor sits at COL+12
        if col_va is None:
            continue
        if pe.u32_va(col_va) != 0:     # the COL signature is 0 on 32-bit
            continue
        cols.append(col_va)
    if len(cols) != 1:
        raise SystemExit("For %s: found %d Complete Object Locators - expected 1." % (cls, len(cols)))
    col_va = cols[0]

    vts = []
    for off in pe.find_dword(col_va):
        vt_va = pe.off2va(off + 4)     # the vtable starts right after the pointer to the COL
        if vt_va is not None:
            vts.append(vt_va)
    if len(vts) != 1:
        raise SystemExit("For %s: found %d vtables - expected 1." % (cls, len(vts)))
    return vts[0], td_va


def func_bytes(pe, va, n):
    o = pe.va2off(va)
    return None if o is None else bytes(pe.d[o:o + n])


def analyse(exe):
    d = load(exe)
    pe = PE(d)
    vt_broken, _ = find_vtable(pe, BROKEN, NAMESPACE)
    vt_donor, _ = find_vtable(pe, DONOR, NAMESPACE)
    slot_va = vt_broken + EXIT_SLOT * 4
    slot_off = pe.va2off(slot_va)
    cur = pe.u32_va(slot_va)
    donor_exit = pe.u32_va(vt_donor + EXIT_SLOT * 4)

    # the donor's Exit must have the expected shape
    db = func_bytes(pe, donor_exit, 0x18) or b""
    m = EXIT_SHAPE.match(db)
    if not m:
        raise SystemExit(
            "The donor's Exit (%s, 0x%08X) does not have the expected shape - not patching.\n  bytes: %s"
            % (DONOR, donor_exit, hx(db)))
    donor_pool = struct.unpack("<I", m.group(1))[0]

    # Enter of both states must reference the same global pool
    pools = {}
    for cls, vt in ((BROKEN, vt_broken), (DONOR, vt_donor)):
        enter = pe.u32_va(vt + 8 * 4)
        eb = func_bytes(pe, enter, 0x20) or b""
        mm = ENTER_GLOBAL.search(eb)
        pools[cls] = (enter, struct.unpack("<I", mm.group(1))[0] if mm else None)
    if pools[BROKEN][1] != pools[DONOR][1] or pools[BROKEN][1] != donor_pool:
        raise SystemExit(
            "Enter of %s and Enter of %s reference different pools (%s / %s, the donor's Exit: 0x%08X) -\n"
            "swapping Exit would be wrong. Not patching."
            % (BROKEN, DONOR, pools[BROKEN][1], pools[DONOR][1], donor_pool))

    stub = func_bytes(pe, cur, 3)
    if cur == donor_exit:
        state = "patched"
    elif stub == NOOP_STUB:
        state = "original"
    else:
        state = "unknown"

    return dict(d=d, pe=pe, vt_broken=vt_broken, vt_donor=vt_donor, slot_va=slot_va,
                slot_off=slot_off, cur=cur, donor_exit=donor_exit, state=state,
                stub=stub, pool=donor_pool, enters=pools, digest=sha256(d))


def report(exe, a):
    print("  file        %s" % exe)
    print("  sha256      %s" % a["digest"])
    print("  vtable %-26s 0x%08X" % (BROKEN, a["vt_broken"]))
    print("  vtable %-26s 0x%08X" % (DONOR, a["vt_donor"]))
    print("  shared pool 0x%08X  (Enter of both states references it)" % a["pool"])
    print("  slot [9]    VA 0x%08X  =  file 0x%08X" % (a["slot_va"], a["slot_off"]))
    print("  now         0x%08X%s" % (a["cur"],
          ("   (empty stub, ret 4)" if a["stub"] == NOOP_STUB else "")))
    print("  donor       0x%08X   Exit of %s" % (a["donor_exit"], DONOR))
    print("  state       %s" % {"original": "ORIGINAL (leak present)",
                                "patched": "PATCHED",
                                "unknown": "UNKNOWN"}[a["state"]])


def install_dir_from_registry():
    try:
        import winreg
    except ImportError:
        return None
    for root, path in ((0x80000002, r"SOFTWARE\WOW6432Node\Ubisoft\Launcher\Installs\%s" % UPLAY_APP_ID),
                       (0x80000002, r"SOFTWARE\Ubisoft\Launcher\Installs\%s" % UPLAY_APP_ID)):
        try:
            with winreg.OpenKey(root, path) as k:
                v = winreg.QueryValueEx(k, "InstallDir")[0]
                if v:
                    return os.path.normpath(v)
        except OSError:
            continue
    return None


def find_exes(explicit_dir=None, explicit_exe=None):
    if explicit_exe:
        if not os.path.isfile(explicit_exe):
            raise SystemExit("No such file: %s" % explicit_exe)
        return [os.path.abspath(explicit_exe)]
    root = explicit_dir or install_dir_from_registry()
    if not root:
        raise SystemExit("Could not find the game installation. Pass the game folder with --dir.")
    sysdir = os.path.join(root, EXE_SUBDIR)
    found = [os.path.join(sysdir, n) for n in EXE_NAMES
             if os.path.isfile(os.path.join(sysdir, n))]
    if not found:
        raise SystemExit("%s contains none of: %s" % (sysdir, ", ".join(EXE_NAMES)))
    return found


def sidecar(exe):
    return exe + ".pool-leak-patch.json"


def cmd_check(exes):
    for exe in exes:
        print("")
        report(exe, analyse(exe))
    print("")
    print("Read-only check - nothing was changed. To apply:  python patch_pool_leak.py apply")


def cmd_apply(exes):
    changed = 0
    for exe in exes:
        print("")
        a = analyse(exe)
        report(exe, a)
        if a["state"] == "patched":
            print("  -> already patched, nothing to do")
            continue
        if a["state"] != "original":
            print("  -> state not recognised, leaving the file alone")
            continue

        backup = exe + ".orig"
        if not os.path.isfile(backup):
            shutil.copy2(exe, backup)
            print("  backup      created: %s" % backup)
        else:
            print("  backup      already exists: %s" % backup)

        d, off = a["d"], a["slot_off"]
        before = bytes(d[off:off + 4])
        d[off:off + 4] = struct.pack("<I", a["donor_exit"])
        with open(exe, "wb") as f:
            f.write(bytes(d))

        with open(sidecar(exe), "w", encoding="utf-8") as f:
            json.dump({"offset": off, "va": a["slot_va"],
                       "original": before.hex(), "patched": struct.pack("<I", a["donor_exit"]).hex(),
                       "sha256_before": a["digest"], "sha256_after": sha256(d)}, f, indent=1)

        chk = analyse(exe)
        print("  before      %s  (0x%08X)" % (hx(before), a["cur"]))
        print("  after       %s  (0x%08X)" % (hx(chk.__getitem__("d")[off:off + 4]), chk["cur"]))
        print("  verify      state on disk: %s" % chk["state"])
        print("  sha256      %s" % chk["digest"])
        if chk["state"] != "patched":
            raise SystemExit("The write could not be verified!")
        changed += 1
    print("")
    print("Done. Files changed: %d" % changed)


def differing_offsets(a, b, limit=8):
    """Offsets where two equally long byte strings differ; stops after `limit` hits."""
    out = []
    for i in range(len(a)):
        if a[i] != b[i]:
            out.append(i)
            if len(out) >= limit:
                break
    return out


STALE = ("  -> REFUSED: this is not the file the %s was made from - the game was\n"
         "     probably updated or repaired since. Nothing was written. A freshly updated\n"
         "     game is already unpatched: delete the leftover *.orig and *.pool-leak-patch.json\n"
         "     next to the exe and run the check again.  (--force overrides this.)")


def cmd_revert(exes, force=False):
    for exe in exes:
        print("")
        print("  file        %s" % exe)
        sc = sidecar(exe)
        if os.path.isfile(sc):
            with open(sc, encoding="utf-8") as f:
                info = json.load(f)
            d = load(exe)
            off = info["offset"]
            # Never write into a file we do not recognise: after a game update the same offset
            # belongs to something else, and four stale bytes there corrupt the new exe.
            digest = sha256(d)
            if digest == info.get("sha256_before"):
                os.remove(sc)
                print("  -> already original, removed the leftover %s" % os.path.basename(sc))
                continue
            if digest != info.get("sha256_after"):
                still_patched = bytes(d[off:off + 4]) == bytes.fromhex(info["patched"])
                if not (force and still_patched):
                    print(STALE % "patch record")
                    continue
            d[off:off + 4] = bytes.fromhex(info["original"])
            with open(exe, "wb") as f:
                f.write(bytes(d))
            os.remove(sc)
            a = analyse(exe)
            print("  restored from %s" % os.path.basename(sc))
            print("  state       %s, sha256 %s" % (a["state"], a["digest"]))
            continue
        backup = exe + ".orig"
        if os.path.isfile(backup):
            # Same rule for the full backup: it must be this very file, give or take the one dword.
            cur, old = load(exe), load(backup)
            diff = differing_offsets(cur, old) if len(cur) == len(old) else None
            if diff == []:
                print("  -> already identical to the backup, nothing to do")
                continue
            if (diff is None or diff[-1] - diff[0] >= 4) and not force:
                print(STALE % "backup")
                continue
            shutil.copy2(backup, exe)
            a = analyse(exe)
            print("  restored from %s" % backup)
            print("  state       %s, sha256 %s" % (a["state"], a["digest"]))
        else:
            print("  -> neither the sidecar nor a backup exists, skipping")


def cmd_scan(exes):
    for exe in exes:
        print("")
        print("  %s" % exe)
        d = load(exe)
        pe = PE(d)
        for cls in (BROKEN, DONOR, "StateLoggingInToRdv"):
            try:
                vt, td = find_vtable(pe, cls, NAMESPACE)
            except SystemExit as e:
                print("    %-28s %s" % (cls, e))
                continue
            slot = pe.u32_va(vt + EXIT_SLOT * 4)
            body = func_bytes(pe, slot, 3)
            tag = " (empty stub)" if body == NOOP_STUB else ""
            print("    %-28s vtable 0x%08X  slot[9] = 0x%08X%s" % (cls, vt, slot, tag))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="check",
                    choices=["check", "apply", "revert", "scan"])
    ap.add_argument("--dir")
    ap.add_argument("--exe")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    exes = find_exes(a.dir, a.exe)
    if a.command == "revert":
        cmd_revert(exes, force=a.force)
    else:
        {"check": cmd_check, "apply": cmd_apply, "scan": cmd_scan}[a.command](exes)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print("ERROR: %s" % e)
        sys.exit(1)
