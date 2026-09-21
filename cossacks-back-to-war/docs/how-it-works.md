# How the fix works

**Read this when:** you want to know why each of the three problems happens, which bytes
change and why that is safe, or you have to find the patch sites again after a game update.

**Not this, for:** installing, checking or undoing the fix → [README.md](../README.md).

**Sections:** [1 The binaries](#1-the-binaries) ·
[2 How the picture reaches the screen](#2-how-the-picture-reaches-the-screen) ·
[3 Problem 1: the EDID version check](#3-problem-1-the-edid-version-check) ·
[4 Problem 2: the menu and DPI virtualization](#4-problem-2-the-menu-and-dpi-virtualization) ·
[5 Problem 3: the crash and the engine ceiling](#5-problem-3-the-crash-and-the-engine-ceiling) ·
[6 The second byte: resolutions outside the list](#6-the-second-byte-resolutions-outside-the-list) ·
[7 The mode.dat file](#7-the-modedat-file) ·
[8 Why each change is safe](#8-why-each-change-is-safe) ·
[9 What the patcher does](#9-what-the-patcher-does) ·
[10 Porting to a new game version](#10-porting-to-a-new-game-version) ·
[11 If it still crashes: the BugTrap report](#11-if-it-still-crashes-the-bugtrap-report) ·
[12 Address reference](#12-address-reference)

This is a reference document. It is meant to be read one section at a time.

## 1. The binaries

Everything below was derived from the shipping binaries of the Steam release, app id
`4850`, build id `2684`, and from one crash report of the game itself.

| File | Role | Size | SHA-256, untouched | Image base |
|---|---|---|---|---|
| `dmcr.exe` | the game | 2 016 008 | `3923b0ff3ae8da0584f29ae2bbf2e2deb030e57df11d37fb6fb55fa5ceb4acd6` | `0x00400000` |
| `csemu.dll` | DirectDraw shim shipped with the game | 357 056 | `45a032b08b484b95aecc9e9e438a310b427e0082e14b31d5f2e8410f68f177a7` | `0x10000000` |

All addresses are **virtual addresses** at those image bases — what a crash report shows.

Address to file offset:

* `dmcr.exe` — for `.text`, `.rdata` and `.data` the file offset equals the RVA, so
  `offset = VA − 0x400000`. `.rsrc` is the exception (RVA `0x22e6000`, file offset
  `0x1ba000`), and everything above VA `0x5ba000` is zero-initialised data that does not
  exist in the file.
* `csemu.dll` — `.text` starts at RVA `0x1000` and file offset `0x400`, so
  `offset = VA − 0x10000000 − 0xC00`.

Variable names come from the export table of `dmcr.exe` itself. It exports 552 names, and
that is a far better source of labels than guessing.

## 2. How the picture reaches the screen

The game is from 2002 and renders into an 8-bit, 256-colour buffer through DirectDraw.
Modern Windows has no 8-bit screen modes: a 32-bit probe calling `DirectDrawCreate` and
`EnumDisplayModes` against the system `ddraw.dll` gets 32 bpp modes only.

So the Steam release ships its own shim, **`csemu.dll`**. `dmcr.exe` imports
`DirectDrawCreate` from it, and the shim loads the real DirectDraw **explicitly from the
system folder** (`GetSystemDirectoryA` + `"\DDRAW.DLL"`, `0x100010b7`). That is why
dropping a wrapper such as cnc-ddraw into the game folder does nothing — nobody loads it.

| `csemu.dll` function | Address | What it does |
|---|---|---|
| native mode | `0x100017f0` | reads the EDID of the primary monitor and takes the first Detailed Timing Descriptor |
| `EnumDisplayModes` | `0x100026c0` | synthesises **exactly two** 8 bpp modes: the native one and 1024x768 |
| `SetDisplayMode` | `0x100027f0` | sets the real mode to **native, 32 bpp** and stretches the game's frame in software |

The whole point of the shim is **not to change the desktop resolution**: the game draws its
own small frame, and the frame is stretched onto the mode that is already set. The frame
goes out through `Blt` with `lpDestRect = NULL` and `lpSrcRect = NULL` (`0x1000314a`) —
the whole frame onto the whole surface, no cropping, no letterboxing.

### The menu is always 1024x768

This one fact explains most of the confusion: **`mode.dat` has no effect on the menu.**

```asm
004b2375  bf 00 04 00 00        mov edi, 0x400              ; 1024
004b237a  b8 00 03 00 00        mov eax, 0x300              ; 768
004b2386  89 3d b8 a1 65 00     mov [0x65a1b8], edi         ; ?RealLx@@3HA
004b238c  a3 b4 a1 65 00        mov [0x65a1b4], eax         ; ?RealLy@@3HA
```

That is straight-line code **before** `mode.dat` is even opened (`0x004b2425`). And it is
`RealLx`/`RealLy` that go to the graphics layer:

```asm
0044ff49  mov edx, [0x65a1b4]            ; RealLy
0044ff54  push 8                         ; 8 bpp
0044ff56  push edx
0044ff57  mov edx, [0x65a1b8]            ; RealLx
0044ff5f  push edx
0044ff61  call dword ptr [ecx + 0x54]    ; csemu::SetDisplayMode(RealLx, RealLy, 8)
```

The values from `mode.dat` live in a **different** pair, `[0x7fff9c]` / `[0x7ffeec]`. They
are copied into `RealLx`/`RealLy` only when a mission starts (`0x0048a8dc`, `0x0048aee4`),
and 1024x768 is forced back on return to the menu.

Mind the names: `[0x7fff9c]` is **not** `ScrWidth`. The real `?ScrWidth@@3HA` is
`0x65a990` and `?ScrHeight@@3HA` is `0x65a99c`.

A side effect worth knowing: `0x004b28a9` calls `ClipCursor(0, 0, RealLx−1, RealLy−1)`, so
in the menu the mouse is confined to a 1024x768 rectangle.

## 3. Problem 1: the EDID version check

The native-mode function validates the EDID block before it trusts it:

```asm
10001835  81 7c 24 04 00 ff ff ff   cmp dword ptr [esp+4], 0xFFFFFF00   ; header, bytes 0..3
1000183d  75 de                     jne 0x1000181d                       ; -> fail
1000183f  81 7c 24 08 ff ff ff 00   cmp dword ptr [esp+8], 0x00FFFFFF   ; header, bytes 4..7
10001847  75 d4                     jne 0x1000181d
10001849  80 7c 24 16 01            cmp byte ptr [esp+0x16], 1          ; byte 18: version
1000184e  75 cd                     jne 0x1000181d
10001850  80 7c 24 17 03            cmp byte ptr [esp+0x17], 3          ; byte 19: revision
10001855  75 c6                     jne 0x1000181d                       ; rejects 1.4  <-- here
```

It accepts EDID **version 1.3 exactly**. A monitor that reports 1.4 fails the check, and
the chain runs like this:

1. parsing fails → the shim stores `[this+0x20] = 0`, "no native mode";
2. `EnumDisplayModes` then falls through to the system `ddraw.dll`, which offers 32 bpp only;
3. the game's enumeration callback accepts 8 bpp only (`0x0044fc69`), so it gets no mode;
4. `SetDisplayMode` bypasses the stretching path and sets the **real screen mode to
   1024x768**.

That is the desktop switching resolution, and on a multi-monitor setup it is every window
on every monitor being rearranged.

### The patch

`csemu.dll`, file offset `0xC55`, VA `0x10001855`:

| | Bytes | Instruction |
|---|---|---|
| before | `75 c6` | `jne 0x1000181d` — fail unless the revision is exactly 3 |
| after | `72 c6` | `jb  0x1000181d` — fail only when the revision is below 3 |

One byte, `0x75` → `0x72`. Signature used to find it: `80 7C 24 17 03 75`.

The Detailed Timing Descriptor did **not** change between EDID 1.3 and 1.4 — it is the same
bytes 54–71. On top of that, 1.4 *requires* the first descriptor to be the preferred mode,
so the code reads exactly what it was written to read; the check simply predates 1.4
becoming common. `jb` keeps rejecting everything older than 1.3. The resolution itself is
decoded the classic way: width `((b58 & 0xF0) << 4) | b56`, height `((b61 & 0xF0) << 4) | b59`.

### What the patch does not relax

The parser has more conditions, and the patch leaves them alone: the 8-byte header, the
version byte being `1`, and bit 1 of the feature byte (EDID byte 24):

```asm
10001864  8a 44 24 1c      mov al, [esp+0x1c]        ; byte 24: feature support
...
10001876  a8 02            test al, 2                ; bit 1: preferred timing mode flag
10001878  74 03            je  0x1000187d
1000187a  80 0e 02         or  byte ptr [esi], 2
...
1000188b  f6 06 02         test byte ptr [esi], 2
1000188e  74 8d            je  0x1000181d            ; -> fail when the bit is clear
```

EDID 1.3 requires that bit to be set; in 1.4 its meaning changed and a monitor may leave it
clear. Such a monitor would still be rejected after the patch. This follows from the code
and has **not** been seen on real hardware.

### Checking your monitor

Windows keeps the EDID of every monitor it has seen under
`HKLM\SYSTEM\CurrentControlSet\Enum\DISPLAY\<monitor id>\<instance>\Device Parameters\EDID`.
Byte 18 is the version, byte 19 the revision. In PowerShell:

```powershell
Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY' -Recurse -ErrorAction SilentlyContinue |
  Where-Object PSChildName -eq 'Device Parameters' | ForEach-Object {
    $e = (Get-ItemProperty $_.PSPath -Name EDID -ErrorAction SilentlyContinue).EDID
    if ($e) { '{0}  EDID {1}.{2}' -f ($_.PSParentPath -replace '.*DISPLAY\\'), $e[18], $e[19] }
  }
```

The list includes monitors that are no longer connected.

## 4. Problem 2: the menu and DPI virtualization

### What it was not

The first theory — "the menu is laid out for 1024x768 and scaled by screen width, so on a
16:9 screen the bottom falls off" — is **wrong**, and an experiment shows it: changing the
game resolution from 3840x2160 to 2880x2160 did not move a single pixel. It could not: the
menu was drawn at 1024x768 both times (section 2).

The layout is a set of constants (`0x0048552c` … `0x004856df`): x = `0x4c`, y = 140, 222,
304, 386, 468, 550 — a step of 82 — over the background `INTERFACE\BACKGROUND_MAIN_MENU.BMP`,
which is exactly 1024x768. The last item ends at 630 of 768. By the game's own layout **all
six items fit**, and the shim stretches the whole frame without cropping (section 2).

So the cropping happens **outside both binaries**.

### What it is

The numbers from a screenshot, taken on a 3840x2160 display at 150% scaling, give exactly
one factor — **1.5**, the Windows scaling:

| Measured | Predicted with a factor of 1.5 | Observed |
|---|---|---|
| visible menu items | 768 · (2/3) = 512 rows → (512 − 140) / 82 = 4.54 | "about 4.5" |
| height of the background's header | 68 · (2160 / 768) · 1.5 = 287 px | ≈ 288 px |

`dmcr.exe` was built without a manifest — `.rsrc` holds ICON, GROUP_ICON and VERSION only,
and there is no `dpiAware` string anywhere — so the process is **DPI unaware**. The shim,
however, takes the resolution straight from the EDID, past the virtualization, and renders
an honest 3840x2160 frame. Windows treats the surface of such a process as logical and
stretches it again by 1.5, to 5760x3240, of which only the top-left 3840x2160 land on the
screen. Hence both the magnification and the missing bottom and right.

### The fix

A compatibility flag. No game file is touched:

```
HKCU\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers
  "<full path to dmcr.exe>" = "~ HIGHDPIAWARE"
```

It is exactly what the checkbox *Override high DPI scaling behavior → Application* in the
exe's Properties does. `patch.py` sets and removes it by itself and preserves any other
layers already present in the value.

## 5. Problem 3: the crash and the engine ceiling

The crash is an `ACCESS_VIOLATION` at `0x00463F55`. BugTrap labels it
`LoadOptionalTable()+1013`, and the label is **false**: the real
`?LoadOptionalTable@@YAXHPAD@Z` starts at `0x00463B60` and ends at `0x00463BD8`. What
crashes is an unnamed smoothing function that starts at `0x00463E50`.

```asm
00463f39  mov ecx, [0xac13ac]      ; map size N            = 268
00463f3f  mov esi, [0x6d0ad8]      ; source                = 0x0B377FE8
00463f45  imul ecx, ecx
00463f48  mov edi, [0x688dbc]      ; destination           = 0x00000000   <-- NULL
00463f55  rep movsd                ; ACCESS_VIOLATION
```

### What it was not

"`malloc` returned NULL and nobody checked" is **wrong**. Had the allocation at
`0x004c20c4` returned NULL, the branch at `0x004c20d0` would only have skipped the zeroing,
while `0x004c20f7` → `0x004c20fd mov edi, edx` → `0x004c2113 rep stosd` run
unconditionally — the crash would have happened right there, with ESI = `0x40`. The dump
has ESI = `0x0B377FE8`. The pointer was **overwritten by an unrelated write**.

### What it is

The on-screen tile grid at `0x00680DB8`:

```asm
00465650  3b 0d e0 0b 6d 00          cmp ecx, [0x6d0be0]      ; columns - checked
00465656  7f 1a                      jg  0x465672
00465658  3b 05 e4 0b 6d 00          cmp eax, [0x6d0be4]      ; rows    - checked
0046565e  7f 12                      jg  0x465672
00465660  c1 e0 07                   shl eax, 7               ; row stride is HARD-CODED: 128 words
00465663  03 c1                      add eax, ecx
0046566a  66 89 0c 45 b8 0d 68 00    mov word ptr [eax*2 + 0x680db8], cx
```

The bounds are checked **against the number of tiles on screen, never against the size of
the array**. Rows and columns are computed in `0x0048a160`, right after a resolution change
(`[0xfe6fe4]` / `[0xfe6fe0]`, with copies in `[0x6d0be4]` / `[0x6d0be0]`):

```asm
0048a428  mov edx, [0x65a1b8]      ; RealLx
0048a433  sar ecx, 5               ; COLS = width / 32
0048a436  test dl, 0x1f
0048a439  mov [0xfe6fe4], eax      ; ROWS = height / 16, NOT rounded up
0048a444  je  +7
0048a446  inc ecx                  ; COLS is rounded UP
```

There are four write paths into the grid: `0x00465917` and `0x00465940` with base
`0x680db8`, `0x00465972` and `0x004659a1` with base `0x680eb8`. The second base is shifted
by exactly one row (`0x680eb8 − 0x680db8 = 0x100` = 128 words), but the check there is made
against `y+1` (`0x00465993 cmp edx, [0xfe6fe4]`, with `edx = y+1`), so there is no real
shift. In all four paths the effective row is ≤ ROWS and the column is ≤ COLS.

### Deriving the ceiling

* The array is 128 x 128 words = `0x8000` bytes and ends at `0x00688DB8`.
* The highest index that still fits is row 127, column 127: offset
  `2 · (127·128 + 127) = 32766 < 0x8000`. The array was sized for exactly that.
* The row index may equal ROWS, so ROWS must be ≤ 127. ROWS = height / 16 rounded down →
  **height ≤ 127·16 + 15 = 2047**.
* The column index may equal COLS, so COLS must be ≤ 127. COLS = width / 32 rounded up →
  **width ≤ 127·32 = 4064**.

And right behind the array lie the pointers to the map buffers:

| Address | What | Reached by |
|---|---|---|
| `0x00688DB8` | | row 128, x = 0 |
| `0x00688DBC` | **destination map buffer** | row 128, **x = 2** |
| `0x00688DC0` | | row 128, x = 4 |

`0x680DB8 + 2 · (128·128 + 2) = 0x00688DBC` — precisely the pointer that turned out to be
zero. The fog-of-war table follows.

| Frame height | Grid rows | Result |
|---|---|---|
| 768 | 48 | fine |
| 1440 | 90 | fine, **verified in game** |
| 2032 | 127 | the limit; the maximum for a 2160-line monitor |
| 2047 | 127 | the limit |
| 2048 | 128 | memory corruption |
| **2160** | **135** | **memory corruption → crash, reproduced** |

This also explains why switching 3840 → 2880 changed nothing about the crash either: only
the width changed (120 → 90 columns), the height stayed 2160, and the same bytes were
overwritten. It is most likely also why the game can work on a 4K display until the
resolution is touched: with no `mode.dat` it asks `GetSystemMetrics`, and a DPI-unaware
process on a 3840x2160 display at 150% scaling is told 2560x1440 — 90 rows.

### The most a 3840x2160 monitor can get

**Real 4K is out of reach.** The grid is fixed at 128x128, the stride of 128 is baked into
the `shl eax, 7`, and the map buffer pointers sit right behind the array. The nearest modes:

| Resolution | Grid | Proportions | Pixels compared with 4K |
|---|---|---|---|
| **3840x2032** | 120x127 | width 1:1, stretched vertically by 6.3% | 94% |
| 3584x2016 | 112x126 | exactly 16:9, no distortion | 87% |
| 2560x1440 | 80x90 | exactly 16:9, no distortion | 44% |

`3840x2032` takes the native width pixel for pixel and sits against the height limit; the
shim stretches 2032 → 2160, so the picture is 6.3% taller than it should be. If that is
visible, `3584x2016` gives exact proportions for 7% fewer pixels.

**The fix** is to keep the height in `mode.dat` at or below 2047. `patch.py` refuses to
write anything above the ceiling and explains why. What is verified in game and what is
only calculated: [README, Status](../README.md#status).

## 6. The second byte: resolutions outside the list

At start-up the game looks the `mode.dat` resolution up in the list of enumerated modes —
the two the shim synthesises — and silently falls back to 1024x768 when it is not there:

```asm
004b24df  8b 35 ec fe 7f 00         mov esi, [0x7ffeec]            ; height from mode.dat
004b24e5  8b 3d bc a1 65 00         mov edi, [0x65a1bc]            ; number of enumerated modes
004b24eb  32 c0                     xor al, al                     ; found = 0
004b24ed  33 c9                     xor ecx, ecx
004b24ef  3b fb                     cmp edi, ebx                   ; ebx = 0
004b24f1  7e 1d                     jle 0x4b2510                   ; empty list -> reset
004b24f3  39 14 8d e8 97 65 00      cmp [ecx*4 + 0x6597e8], edx    ; widths;  edx = [0x7fff9c]
004b24fa  75 0b                     jne 0x4b2507
004b24fc  39 34 8d 68 98 65 00      cmp [ecx*4 + 0x659868], esi    ; heights
004b2503  75 02                     jne 0x4b2507
004b2505  b0 01                     mov al, 1                      ; found = 1
004b2507  41                        inc ecx
004b2508  3b cf                     cmp ecx, edi
004b250a  7c e7                     jl  0x4b24f3
004b250c  3a c3                     cmp al, bl
004b250e  75 14                     jne 0x4b2524                   ; found -> keep      <-- here
004b2510  c7 05 9c ff 7f 00 00 04 00 00   mov dword ptr [0x7fff9c], 0x400   ; 1024
004b251a  c7 05 ec fe 7f 00 00 03 00 00   mov dword ptr [0x7ffeec], 0x300   ; 768
004b2524  ...
```

The two tables are filled by the enumeration callback at `0x0044fc69`: 8 bpp only, width of
800 or more, 32 entries at most.

### The patch

`dmcr.exe`, file offset `0xB250E`, VA `0x004b250e`:

| | Bytes | Instruction |
|---|---|---|
| before | `75 14` | `jne 0x4b2524` — keep the resolution only when it is in the list |
| after | `eb 14` | `jmp 0x4b2524` — always keep it |

One byte, `0x75` → `0xEB`. Signature: `3A C3 75 14 C7 05 9C FF 7F 00 00 04 00 00`.

It is needed **only** to run a mission resolution that the list does not have — 2560x1440
on a 4K monitor, for instance. `patch.py` applies it exactly then, and puts the original
byte back when you later choose the native mode or 1024x768.

### The in-game Options trap

The Options screen shows the same two modes. When `mode.dat` holds anything else, the
screen cannot find it in the list, resets the index to 0 (`0x00484761`), silently selects
mode 0 — the native one (`0x00484a87`) — and writes it to `mode.dat` on exit
(`0x004b2a70`). On a 4K monitor the next mission then crashes. Running `apply` again cures
it. With 1024x768 or the native mode there is no trap: both are in the list.

## 7. The mode.dat file

Ten numbers separated by spaces, in the game's `bin` folder. The first two are the width
and height of the **mission** (not of the menu); the other eight are sound and other
settings and are never touched.

```
1024 768 85 0 0 0 7 6 1 0
```

* The game **rewrites the file on every normal exit** (`0x004b2a1a` … `0x004b2a76`).
* With the file missing or zeroed it takes `GetSystemMetrics` instead (`0x004b24a2`).
* The file is read at `0x004b2448`; the list check of section 6 follows at `0x004b250e`.

## 8. Why each change is safe

**`csemu.dll`, `jne` → `jb`.** The behaviour changes for one input only: an EDID whose
revision byte is above 3. For revision 3 the branch is not taken either way, for anything
below 3 it is taken either way. The data read afterwards — the first Detailed Timing
Descriptor — has the same layout in 1.4, and 1.4 guarantees that it is the preferred mode.
No instruction is moved and no length changes.

**`dmcr.exe`, `jne` → `jmp`.** It removes one fallback and nothing else: the two stores
that overwrite the resolution with 1024x768. The empty-list path at `0x004b24f1` still
jumps straight to those stores, so a broken enumeration still ends in 1024x768. What the
fallback used to guarantee — that the resolution is one from the list — the shim does not
need: it stretches the frame it is given onto the native mode, verified in game with
2560x1440 on a 3840x2160 display. What the fallback never guaranteed is the limit that
matters, the tile grid, and that one `patch.py` enforces itself before it writes anything.

**The DPI flag.** A documented Windows compatibility layer, stored per user, touching no
game file, identical to ticking the checkbox in the exe's Properties. Removing the value
undoes it completely.

**`mode.dat`.** A plain settings file the game rewrites anyway. Only the first two numbers
change, and the patcher refuses values above 4064x2047.

**The patcher refuses to guess.** It locates each site by signature and requires exactly
one match, counting the original and the patched form together. It checks that the byte is
one of the two known values, makes a backup before the first write, re-reads the file
afterwards, and prints the disassembly of the patched site so you can see where the jump
lands. "The script finished without errors" is not verification; the listing is.

### Residual risk

`3840x2032` is exactly on the limit by the code — 127 rows of 127 — and has not been run
in game. If it crashes at `0x00463F55`, some write path reaches one row further than the
four that were checked. Fall back to `3584x2016` (126 rows) and report it.

## 9. What the patcher does

`python patch.py status | apply [--res WxH] | revert`, plus `--dir <bin folder>` to skip
the Steam lookup.

**`apply`**

1. Parses `WIDTHxHEIGHT` and checks the ceiling. A refusal here happens **before anything
   is written**.
2. Reads the native resolution from the EDID blocks in the registry and decides whether the
   requested mode is in the shim's list — native or 1024x768.
3. `csemu.dll` — always patched.
4. `dmcr.exe` — patched when the mode is **not** in the list, restored to the original byte
   when it is.
5. Adds `HIGHDPIAWARE` to the compatibility layers of `dmcr.exe`, keeping any others.
6. Reads `mode.dat` (or starts from `1024 768 85 0 0 0 7 6 1 0`), backs it up to
   `mode.dat.orig` once, and replaces the first two numbers.

**`revert`** copies every existing `.orig` back over its file, deletes the backup, and
removes `HIGHDPIAWARE` — deleting the registry value when nothing else is left in it.
For the two binaries it checks first that the backup belongs to the file it is about to
overwrite: same size, and no more than the one patched byte of difference. Otherwise it
prints `REFUSED` and writes nothing (`--force` overrides) — a backup of an older game file
must never land on top of a newer one. `mode.dat` is the player's own settings file and is
restored unconditionally.

**`status`** writes nothing: patch state and disassembly of both sites, the flag, the
native resolution, `mode.dat` with its grid size, and the maximum for the monitor.

Known limits of the tool, stated plainly:

* **`apply` does not refresh an old backup.** A backup is taken only when no `.orig` exists
  yet. After a real game update delete the stale `csemu.dll.orig` and `dmcr.exe.orig` before
  applying again; `revert` refuses to use them, so without that you would have no backup of
  the new files.
* **"Native resolution" is the last valid EDID found in the registry**, not necessarily
  that of the primary monitor — the shim itself does pick the primary one (`0x10001660`).
  With identical monitors it is the same thing. With different ones the tool may misjudge
  whether a mode is in the list: at worst `dmcr.exe` stays unpatched and the game falls
  back to 1024x768. The ceiling check does not depend on it.
* **Steam is looked up in its default folder only**; libraries on other drives are found
  from there. Otherwise pass `--dir`.

## 10. Porting to a new game version

Run `status` first. Both sites are found **by signature**, not by offset, so a rebuilt
binary keeps working as long as these instructions survive. When a signature is found zero
times or more than once, the tool refuses, and the sites have to be found again by hand.

**`csemu.dll`.** Look for the EDID header constants — the instruction bytes
`81 7C 24 ?? 00 FF FF FF` followed by `81 7C 24 ?? FF FF FF 00`. The version and revision
checks come right after: `80 7C 24 ?? 01 75 ??`, then `80 7C 24 ?? 03 75 ??`. The byte to
change is the `75` after the compare with 3.

**`dmcr.exe`.** Look for the pair of stores `C7 05 <addr> 00 04 00 00` (1024) and
`C7 05 <addr> 00 03 00 00` (768) preceded by `3A C3 75 14` (`cmp al, bl` / `jne +0x14`),
just after the loop over the two mode tables. There are other 1024/768 pairs in the
executable — the menu's at `0x004b2375` loads registers instead. The absolute address inside
the signature (`9C FF 7F 00`) moves whenever the data layout moves.

Put the new values into `PATCHES` at the top of `patch.py`: `sig`, `pos` (index of the byte
inside the signature), `orig`, `new`. If section offsets changed, fix the VA arithmetic in
`disasm()` too, otherwise the listing shows wrong addresses. The patch itself works on file
offsets and is not affected.

**The ceiling** — `MAX_W, MAX_H = 4064, 2047` — is not discovered at run time. It is a
property of this build, and on a new one three things need re-checking:

1. the row stride is still 128 — `shl eax, 7` in front of
   `mov word ptr [eax*2 + <grid>], cx` (`C1 E0 07` … `66 89 0C 45`);
2. the grid still has room for 128 rows — something else starts `0x8000` bytes after its base;
3. ROWS is still height / 16 rounded down and COLS width / 32 rounded up (`0x0048a160`).

Then apply and **verify with a disassembler** that the jumps land where intended.

## 11. If it still crashes: the BugTrap report

The game ships `BugTrap.dll`. On a crash it assembles a full report in the temp folder and
**deletes it the moment the crash window is closed**.

While the window is still open, copy out of `%TEMP%`:

* the archive `CossacksBackToWar_error_report_*.zip`;
* the folder whose name starts with `TEMP`.

Inside are `errorlog.xml` (registers, stack, modules, environment) and `crashdump.dmp`, a
minidump of tens of megabytes. The minidump holds the global variables at the moment of the
crash — the real resolution, the buffer sizes, the state of the shim — which is exactly
what sections 5 and 12 need.

Two things to know:

* **The BugTrap window keeps the game process alive** and `dmcr.exe` locked. While it is
  open, no patch can be written. `tasklist | findstr /i "dmcr csbtw"` shows what is left.
* **Look before you share.** `errorlog.xml` contains your computer name, your user name,
  all your IP addresses and your environment variables.

## 12. Address reference

`dmcr.exe`:

| Address | What |
|---|---|
| `0x0044fc69` | mode enumeration callback, accepts 8 bpp only |
| `0x0044fd3e` | check "is there a 1024x768x8 mode", otherwise `Loading error` |
| `0x0044ff61` | call to `csemu::SetDisplayMode(RealLx, RealLy, 8)` |
| `0x0048a160` | recomputes the on-screen tile grid |
| `0x00463E50` | the smoothing function — **where it crashes** |
| `0x00465650` | write into the grid at `0x680DB8` with no array bounds check |
| `0x004c2010` | map buffer allocator; `[0x688dbc]` is written at `0x004c20f7` |
| `0x004b2375` | hard-coded 1024x768 for the menu |
| `0x004b2448` | reads `mode.dat` |
| `0x004b24a2` | fallback through `GetSystemMetrics` |
| `0x004b250e` | "is the resolution in the list" check, otherwise reset to 1024x768 — **patch site** |
| `0x004b2a2d` | saves `mode.dat` on exit |
| `0x00484700` | in-game Options, the mode list |
| `0x0048552c` | main menu item layout, hard-coded constants |

Variables:

| Address | Name / meaning |
|---|---|
| `0x65a1b8` | `?RealLx@@3HA` — real frame width |
| `0x65a1b4` | `?RealLy@@3HA` — real frame height |
| `0x65a990` | `?ScrWidth@@3HA` |
| `0x65a99c` | `?ScrHeight@@3HA` |
| `0x7fff9c` / `0x7ffeec` | the pair from `mode.dat` (**not** ScrWidth / ScrHeight) |
| `0x6597e8` / `0x659868` | widths / heights of the enumerated modes, 32 entries each |
| `0x65a1bc` | number of enumerated modes |
| `0x680DB8` | on-screen tile grid, 128x128 words |
| `0x688DBC` | pointer to the destination map buffer — what the overflow hits |
| `0xfe6fe0` / `0xfe6fe4` | grid columns / rows |
| `0xac13ac` | map size N |
| `0x5aca88` | map size class, N = 134 << (class − 1) |

`csemu.dll`:

| Address | What |
|---|---|
| `0x10001090` | loads the system `DDRAW.DLL` |
| `0x10001200` | the `DirectDrawCreate` export |
| `0x10001660` | picks the primary monitor through `EnumDisplayDevices` |
| `0x100017f0` | EDID parser |
| `0x10001855` | **patch site** |
| `0x10001c90` | sets up the stretch factors |
| `0x100026c0` | `EnumDisplayModes` — synthesises the two 8 bpp modes |
| `0x100027f0` | `SetDisplayMode` — sets the real screen mode |
| `0x1000314a` | `Blt` with `NULL` rectangles — stretches the frame over the whole screen |
