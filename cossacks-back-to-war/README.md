# Cossacks: Back to War — display and mission-crash fix

**Three fixes for the Steam version on modern monitors:** the game stops switching your
real desktop resolution (and scrambling the windows on every monitor), the main menu gets
its bottom items back, and missions stop crashing on load at high resolutions.

*Cossacks: Back to War · Steam · resolution changes on launch · desktop switches to 1024x768 ·
windows moved to another monitor · multi-monitor · main menu cut off · bottom menu items
missing · menu zoomed in · crash on mission load · crash when loading a map ·
ACCESS_VIOLATION 0x00463F55 · LoadOptionalTable · high resolution · 4K · 3840x2160 ·
EDID 1.4 · DPI scaling · csemu.dll · dmcr.exe · mode.dat*

[Русская версия](README.ru.md) · [How the fix works](docs/how-it-works.md)

---

## Three problems, three fixes

They look like one problem ("the game runs in the wrong resolution"), but the causes are
independent. The tool applies all three in one go.

| | What you see | Why | Fix |
|---|---|---|---|
| **1** | On launch the whole desktop drops to 1024x768; windows on every monitor get moved and resized | the game's DirectDraw helper `csemu.dll` accepts only monitors that report EDID version 1.3 and gives up on 1.4 | one byte in `csemu.dll` |
| **2** | The main menu is zoomed in, its bottom items are off screen | the game is not DPI aware, so Windows enlarges the finished frame once more by your display scaling | `HIGHDPIAWARE` compatibility flag for `dmcr.exe` — registry only, no game file touched |
| **3** | Crash while a mission loads, access violation at `0x00463F55` | a frame taller than 2047 pixels overflows a fixed 128x128 tile grid and wipes the map buffer pointers | keep the mission resolution under the engine ceiling in `mode.dat` |

## Is this your problem?

### 1. The desktop resolution changes when the game starts

- [ ] The moment the game starts, the **whole desktop** switches to a low resolution.
- [ ] With several monitors, windows on **all** of them get resized, moved or piled onto
      another monitor — and stay that way after you quit.
- [ ] Your monitor is a reasonably modern one. The helper only understands monitors that
      report EDID version 1.3; many current monitors report 1.4.

### 2. The main menu is cut off

- [ ] The main menu looks **zoomed in** — the top-left part of the picture fills the screen.
- [ ] The **bottom menu items are missing**. At 150% scaling you see about four and a half
      of the six.
- [ ] Windows display scaling is above 100% (Settings → System → Display → Scale).
- [ ] Changing the resolution inside the game changes nothing about it.

### 3. The game crashes while a mission loads

- [ ] The menu works; the crash comes **when a mission or a random map starts loading**.
- [ ] The crash window (BugTrap) reports an **access violation at `0x00463F55`** in
      `dmcr.exe` and names the function `LoadOptionalTable()+1013`.
- [ ] The mission resolution is taller than 2047 pixels — typically 3840x2160 on a 4K
      monitor. It is the first two numbers in the file `mode.dat` in the game's `bin` folder.
- [ ] It happens every time, at the same place.

## What actually goes wrong

**1.** The game is from 2002 and draws in 256 colours. Modern Windows has no 256-colour
screen modes, so the Steam release ships a helper, `csemu.dll`, that stands in for
DirectDraw: the game draws its small frame, the helper stretches it onto your normal
desktop, and **the desktop resolution is never touched**. To learn the monitor's
resolution the helper reads its EDID — the monitor's electronic name tag — and accepts it
only if the tag says version 1.3 *exactly*. A monitor that says 1.4 makes the helper
switch itself off, and the game falls back to really changing the screen mode to 1024x768.
The data it reads is laid out identically in 1.4, so the fix is "1.3 **or newer**".

**2.** The game never tells Windows that it can handle a high-DPI screen. The helper
renders a full-size frame (3840x2160 on a 4K display), but Windows treats the window of
such an old program as "logical" pixels and enlarges it once more by your scaling factor.
At 150% a 3840x2160 frame becomes 5760x3240, and only its top-left 3840x2160 fits on the
screen. The cure is the standard Windows compatibility setting *Override high DPI scaling
behavior: Application* — the tool sets it for `dmcr.exe` in your user registry.

**3.** The engine keeps a table of the map tiles that are on screen: a fixed array of
128 x 128 cells, one row per 16 pixels of height, one column per 32 pixels of width. It
checks how many tiles the *screen* has, never how big the *array* is. At a height of 2160
it needs 135 rows; everything from row 128 on is written past the end of the array, right
over the pointers to the map buffers that sit behind it. The next mission load copies the
map to a wiped pointer and crashes.

Fix 1 makes fix 3 necessary: once the helper works again, the game offers your monitor's
native resolution, and on a 4K monitor that is exactly the one that crashes.

Full disassembly and reasoning: **[docs/how-it-works.md](docs/how-it-works.md)**.

## Which resolution to choose

Two facts first.

* **The menu always runs at 1024x768**, whatever you choose. That is hard-coded in the
  game. Your choice only affects missions.
* **The engine cannot go above 4064x2047.** Real 4K (3840x2160) is out of reach: the grid
  is fixed at 128x128, the row length of 128 is baked into the code, and other data sits
  right behind the array. A byte patch cannot change that. The tool **refuses** to write
  anything above the ceiling and tells you why.

Whatever you pick, the desktop resolution stays as it is: the game renders its frame at
the chosen size and the helper stretches it over the whole screen. A smaller number means
a softer picture with bigger units — not a smaller window.

| Your monitor | Type this | What you get |
|---|---|---|
| up to 2047 pixels tall and 4064 wide — 1920x1080, 2560x1440, 3440x1440 … | your monitor's own resolution | pixel-perfect; it is one of the two modes in the game's own list, so the in-game Options screen stays safe |
| 4K, 3840x2160 | `2560x1440` | exact 16:9, **verified in game** |
| | `3584x2016` | the largest mode without distortion; calculated, not yet tried in game |
| | `3840x2032` | the maximum: full width, picture stretched vertically by 6.3%; calculated, **not yet verified in game** |
| any | `1024x768` — just press Enter | the safe default: the game's classic resolution, stretched to fill the screen |

So far only `2560x1440` on a 3840x2160 monitor has actually been played; every other row
follows from the code. See [Status](#status).

Not sure what your monitor is? Run `check.bat`. Its last lines say, for example:

```
Native monitor resolution (EDID): 3840x2160
Engine ceiling: 4064x2047. Maximum for this monitor: 3840x2032
```

> **Stay out of the in-game Options screen if you typed a resolution of your own.** The
> game's list has only two entries: your monitor's native mode and 1024x768. Anything else
> is not in the list, so the Options screen silently switches to the first entry — the
> native mode — and saves it on exit. On a 4K monitor that means the next mission crashes.
> The cure is to run `apply.bat` again. With your native resolution or 1024x768 there is no
> such trap — but on a 4K monitor never *pick* the native 3840x2160 there, for the same reason.

## Supported game versions

| Version | Status |
|---|---|
| Steam, app id `4850`, build id `2684` | supported — developed and verified on it |
| any other build or edition | untested |

The tool does not trust version numbers. It finds both patch sites by **code signature**
and **refuses to write anything** unless each signature is found exactly once.

<details>
<summary>How to check your version manually</summary>

* **Steam build id** — open `steamapps\appmanifest_4850.acf` in your Steam library folder
  with Notepad and look for `"buildid"`.
* **File hashes** of the untouched files in the game's `bin` folder:
  `csemu.dll` — 357 056 bytes, SHA-256
  `45a032b08b484b95aecc9e9e438a310b427e0082e14b31d5f2e8410f68f177a7`;
  `dmcr.exe` — 2 016 008 bytes, SHA-256
  `3923b0ff3ae8da0584f29ae2bbf2e2deb030e57df11d37fb6fb55fa5ceb4acd6`.
</details>

## What you need

* **Windows** and Cossacks: Back to War installed through Steam.
* **Python 3.8 or newer** — [python.org/downloads](https://www.python.org/downloads/).
  During installation tick **"Add python.exe to PATH"**. Nothing else to install.
* Optional: `pip install capstone` makes the tool show the patched instructions as
  disassembly instead of raw bytes. It works the same without it.

## Install

**1. Close the game.** Fully — including a crash report window if one is still open.

**2. Download this repository.** Green `Code` button → `Download ZIP` → unzip anywhere
(Desktop is fine) and open the folder `cossacks-back-to-war`.

**3. Double-click `apply.bat`.** It finds the game through Steam by itself and asks one
question — the mission resolution:

```
Which resolution should MISSIONS run in? The menu is always 1024x768.

  Just press Enter = 1024x768, the safe choice that works on every monitor.
  Or type your own = WIDTHxHEIGHT, for example 2560x1440.

Resolution, then Enter:
```

Press Enter, or type a value from the table above. The window then prints something like:

```
Game files:
  backup -> csemu.dll.orig
  csemu.dll  0xC55: 0x75 -> 0x72  (EDID: accept version 1.3 and newer, not only 1.3 (jne -> jb))
    10001850  807c241703             cmp byte ptr [esp + 0x17], 3
    10001855  72c6                   jb 0x1000181d
  ...

Registry:
  DPI flag   set: ~ HIGHDPIAWARE

mode.dat: 3840x2160 -> 2560x1440   (grid 80x90, ceiling 127x127)
  the shim will stretch 2560x1440 to 3840x2160, the desktop resolution is not changed

  WARNING: 2560x1440 is not in the shim's mode list. Do not open the
  in-game Options screen - ...

Done. Start the game through Steam.
```

The last line is what matters: **`Done.`** The `WARNING` is expected whenever you type a
resolution of your own — it is the Options trap described above. Anything that starts with
`REFUSED` means nothing was changed, and the message says why.

**4. Start the game through Steam** as usual.

> Prefer a terminal? `python patch.py apply --res 2560x1440` does the same thing, and
> `apply.bat 2560x1440` skips the question. Changing your mind later is just running it
> again with another value.

### What exactly gets changed

| What | Where | Backup |
|---|---|---|
| one byte, `75` → `72` | `csemu.dll` in the game's `bin` folder | `csemu.dll.orig` next to it |
| one byte, `75` → `EB` — **only** when the resolution you chose is not in the game's own list | `dmcr.exe` | `dmcr.exe.orig` |
| the first two numbers, width and height | `mode.dat` | `mode.dat.orig` |
| compatibility flag `HIGHDPIAWARE` for `dmcr.exe` | registry of your Windows user: `HKCU\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers` | — |

## Check that it worked

Double-click **`check.bat`**. It changes nothing and prints the current state:

```
csemu.dll  PATCHED    offset 0xC55, byte 0x72, backup present
...
DPI flag (HKCU\...\AppCompatFlags\Layers):
   set: ~ HIGHDPIAWARE
Native monitor resolution (EDID): 3840x2160
mode.dat: 2560 1440 85 0 0 0 7 6 1 0
   missions are rendered at 2560x1440 -> grid of 80 columns x 90 rows (within limits, maximum 127x127)
Engine ceiling: 4064x2047. Maximum for this monitor: 3840x2032
```

Three things to look for: **`csemu.dll  PATCHED`**, **`set: ~ HIGHDPIAWARE`** and
**`within limits`**. `dmcr.exe` may say `ORIGINAL` — that is correct when your resolution
is in the game's own list.

Then in the game: the desktop keeps its resolution and the windows stay where they were;
the main menu shows all six items; a mission loads.

## Uninstall

Double-click **`revert.bat`**, or:

```
python patch.py revert
```

It puts `csemu.dll`, `dmcr.exe` and `mode.dat` back from the `.orig` backups, deletes the
backups, and removes the `HIGHDPIAWARE` flag (other compatibility flags you may have set
for the exe are kept).

**After a real game update, do not run `revert`.** The update already replaced the files
with clean ones, and the `.orig` backups belong to the *old* version — restoring them
would put old files into a new game. Delete `csemu.dll.orig` and `dmcr.exe.orig` by hand
and run `apply.bat` again.

If you lost the backups: Steam → Cossacks: Back to War → Properties → Installed Files →
**Verify integrity of game files** restores the original `csemu.dll` and `dmcr.exe`. The
DPI flag can be removed by hand: right-click `dmcr.exe` → Properties → Compatibility →
Change high DPI settings → untick *Override high DPI scaling behavior*.

## Things that silently undo the fix

- **A game update, "Verify integrity of game files" in Steam, or a reinstall** bring back
  the original `csemu.dll` and `dmcr.exe`. Run `apply.bat` again — after a real update,
  delete the old `.orig` backups first, see [Uninstall](#uninstall).
- **The in-game Options screen**, when you typed a resolution of your own — see the warning
  above. Run `apply.bat` again.
- **Changing the primary monitor.** The helper reads the EDID of the primary display, so
  the "native" resolution changes with it. The patches keep working; run `apply.bat` again
  to set the resolution.
- **Moving the game to another folder, another Windows user, reinstalling Windows.** The
  DPI flag is stored per user and is tied to the full path of `dmcr.exe`. It survives game
  updates, but not these. Run `apply.bat` again.

The game itself rewrites `mode.dat` on every normal exit — with the values it is running
with, so normally nothing changes.

## FAQ

**Can I have real 4K?**
No. 3840x2160 needs 135 tile rows and the engine has room for 128. The closest you can
get is `3840x2032`; see [Which resolution to choose](#which-resolution-to-choose).

**Missions crash again after I opened the in-game Options.**
That is the trap described above: the game switched to the native resolution by itself.
Run `apply.bat` again.

**I am stuck in a menu with no buttons.**
`Alt+F4`, or `Alt+Tab` and close the window.

**`REFUSED: ... is in use by another process`.**
The game is still running. An open BugTrap crash window counts: it keeps the process
alive and the files locked. Close it and try again. `tasklist | findstr /i "dmcr csbtw"`
in a terminal shows whether anything is left.

**`Could not find the game`.**
The tool looks for Steam itself in its default folder, `C:\Program Files (x86)\Steam`, and
finds game libraries on other drives from there. If Steam is installed somewhere else, open
a terminal in this folder and pass the game's `bin` folder yourself — copy the path from
the Explorer address bar:

```
python patch.py apply --res 2560x1440 --dir "<Steam library>\steamapps\common\Cossacks Back to War\bin"
```

The same `--dir` works with `status` and `revert`.

**`REFUSED: the signature was found 0 time(s)`.**
Your game files differ from the supported build, so the tool did not touch them. Please
open an issue with the build id; see
[Porting to a new game version](docs/how-it-works.md#10-porting-to-a-new-game-version).

**The "Native monitor resolution" line shows the wrong monitor.**
The tool reads the EDID blocks that Windows keeps in the registry and takes the last valid
one, which may belong to another monitor, even one that is no longer connected. With
identical monitors it makes no difference. Otherwise ignore the "maximum" it prints and
work it out yourself: width up to 4064, height up to 2047, and not more than your screen.
If missions then run at 1024x768 although you typed something else, this is the reason —
please open an issue.

**Can't I just drop a DirectDraw wrapper (cnc-ddraw, dgVoodoo …) into the game folder?**
Not for this. `csemu.dll` loads the real DirectDraw by its full path from the Windows
system folder, so a `ddraw.dll` placed next to the game is never loaded by it.

**Is this a cheat? Does it change gameplay?**
No. One byte in the display helper, one byte in the start-up resolution check, a Windows
compatibility flag and two numbers in a settings file. Multiplayer was not tested with it.

**Is it safe?**
It backs up every file before touching it, checks the byte it is about to replace,
refuses to work when a signature is missing or ambiguous, and re-reads and disassembles
the result after writing. See
[Why each change is safe](docs/how-it-works.md#8-why-each-change-is-safe). That said —
this is an unofficial binary patch. Use at your own risk.

**It still crashes.**
Do not close the crash window yet — the report is deleted the moment you do. See
[If it still crashes](docs/how-it-works.md#11-if-it-still-crashes-the-bugtrap-report).

## Status

All three fixes are **verified in game** (2026-09-07 … 2026-09-09), on a 3840x2160
display at 150% scaling whose EDID reports version 1.4, with several monitors attached:

* fix 1 — the game starts, the desktop resolution and the window layout stay untouched;
* fix 2 — the main menu is shown in full;
* fix 3 — the crash was reproduced at a height of 2160, and missions load without it at
  2560x1440.

Resolutions:

* **`2560x1440` is verified in game.**
* **`3840x2032`**, the maximum for a 3840x2160 monitor, **is calculated but not yet
  verified in game.** By the code it sits exactly on the limit — 127 rows of 127 possible.
  If it crashes at `0x00463F55`, some write path reaches one row further than the four
  that were checked: fall back to `3584x2016` and please open an issue.
* **`3584x2016`** is the largest mode without aspect distortion. It comes from the same
  calculation (126 rows) and has not been run in game either.

Verified by reading the code, and cross-checked: the menu is always 1024x768; the overflow
above a height of 2047 lands exactly on the map buffer pointer at `0x00688DBC`; the
ceiling is 4064x2047 and all four write paths into the grid agree with it.

## For maintainers — a new game version

Nothing is hard-coded by offset: both patch sites are found by code signature, so a rebuilt
executable keeps working as long as those few instructions survive. When they do not, the
tool refuses. How to find the sites again, and what the engine ceiling depends on:
[Porting to a new game version](docs/how-it-works.md#10-porting-to-a-new-game-version).

## Author

Made by **[bombuilder.by](https://bombuilder.by)**.

Helped, or still broken? Either way, open an issue — above all if you ran `3840x2032`
or `3584x2016`: one confirmed mission load turns "calculated" into "verified".

## Disclaimer

Not affiliated with, endorsed by, or supported by GSC Game World or any publisher of the
game. Cossacks: Back to War and related names are trademarks of their respective owners.
This repository contains no game code — only a small script that changes two bytes in your
own local copy, one settings file and one Windows compatibility flag. Provided as-is,
without warranty.
