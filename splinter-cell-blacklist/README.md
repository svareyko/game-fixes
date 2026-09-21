# Splinter Cell Blacklist — 30-Minute Crash Fix

**Fixes the crash to desktop that comes after roughly half an hour of play** — every
session, at almost the same minute, with no error message. The cause is a leak in the
game's online login code; the fix changes one 4-byte pointer in the executable.

```
Faulting application name: Blacklist_DX11_game.exe
Exception code: 0xc0000005
Fault offset: 0x00422c5c
```

*Splinter Cell Blacklist · crash after 30 minutes · crash to desktop · CTD with no error
message · 0xC0000005 · Blacklist_DX11_game.exe · Blacklist_game.exe · fault offset
0x00422c5c · Rendez-Vous · Uplay / Ubisoft Connect login · offline mode*

[Русская версия](README.ru.md) · [How the fix works](docs/how-it-works.md)

> ## Status: verified in the binary, not yet confirmed by play
>
> The fix was applied on 2026-09-04 to both executables of game build `603495` and
> checked with a disassembler. What is still missing is the real test: **a session
> longer than 30 minutes without the crash.** Until that is done, read it as "should
> work", not as "works". The full list is in [Status](#status).

---

## Is this your crash?

Tick these off. If most of them match, this fix is for you.

- [ ] The game closes to the desktop with **no error window at all**.
- [ ] It happens **27 to 29 minutes after you start the game** — nearly the same minute
      in every session. The recorded crashes came at 28:19, 27:04, 28:34 and 28:35.
- [ ] There is no stutter, freeze or slowdown before it. One moment you play, the next
      you look at the desktop.
- [ ] It does not matter which mission you play or what you are doing at that moment.
- [ ] Nothing points at the video card: no flicker, no "display driver stopped
      responding" message around the crash.

### Confirm it in Windows Event Viewer

Windows writes down every crash, and the record shows whether it is this bug.

1. Press `Win + R`, type `eventvwr.msc`, press Enter.
2. Open **Windows Logs → Application**.
3. Find the **Error** entry with the source **Application Error** (Event ID 1000) made
   at the time of the crash, and read its text:

```
Faulting application name: Blacklist_DX11_game.exe, ...
Faulting module name: Blacklist_DX11_game.exe, ...
Exception code: 0xc0000005
Fault offset: 0x00422c5c
```

On a non-English Windows the labels are translated; the numbers are the same.

Exception code `0xc0000005` together with fault offset `0x00422c5c` is this bug.

Two honest remarks:

* All four recorded crashes were on the DirectX 11 executable. `Blacklist_game.exe`
  (DirectX 9) has the same defect at different addresses, so its fault offset is
  different, and I never recorded it. For DX9, go by the timing.
* The game has about a hundred places that would crash the same way once the leak has
  done its work. In every recorded crash it was the same one, but if your offset differs
  and the timing fits, it may still be this bug.

`check.bat` from this repository tells you whether your executable contains the defect —
every untouched copy of build `603495` does. Whether it is *your* crash is decided by
the timing and the Event Viewer record.

## What actually goes wrong

For its online operations the game keeps a small pool of 20 "result holder" objects.
One step of the online login sequence — proxy detection — takes a holder every time it
runs and never gives it back: the function that should return it is an empty stub.

The game walks through that step again and again in the background, about once every
85 seconds in the recorded sessions. After 20 passes the pool is empty, the next request
receives a null pointer, the game uses it without looking, and Windows ends the process.
Twenty passes of 85 seconds is 28 minutes.

The fix points the broken step at the correct "return the holder" function. That
function is already in the game — the neighbouring login step uses it for exactly the
same job. One pointer changes, 4 bytes, and no new code is added.

Full analysis with disassembly: **[docs/how-it-works.md](docs/how-it-works.md)**.

## Supported game versions

| Game version | Edition | Executable | Status |
|---|---|---|---|
| `SC6_pcbranch_V2425.0_C603495` (build `603495`) | Ubisoft Connect | `Blacklist_DX11_game.exe` (DirectX 11) | affected — fix available |
| the same | the same | `Blacklist_game.exe` (DirectX 9) | affected — fix available |

The tool patches both executables in one go, so it does not matter which one you start.

It keeps no list of addresses. It finds the two login steps by their class names inside
the executable and **refuses to write anything** unless all of this is true: the broken
step really has the empty stub, the donor function has the expected shape, and both steps
use the same pool. It never guesses. On a game version I have not seen, the same checks
decide: if they pass, the defect is the same and so is the fix; if not, nothing is touched.

Only the Ubisoft Connect edition was tested. The tool does not care where the game was
bought, only what is inside the executable — for a Steam or retail copy run `check.bat`
and read what it says.

<details>
<summary>How to check your version manually</summary>

* **Game version** — open `version.ini` in the game folder with Notepad. The line
  `name=` should read `SC6_pcbranch_V2425.0_C603495`, and under `[changelist]` you
  should see `main=603495`.
* **File hashes** of the untouched executables of build `603495`, both in `src\SYSTEM`
  inside the game folder:

| File | Size | SHA-256 |
|---|---|---|
| `Blacklist_DX11_game.exe` | 49 309 712 bytes | `c52b3d0927591e477424f389ff0b1314a300938e19ce61a7b0a7bc09f81c2c89` |
| `Blacklist_game.exe` | 48 957 456 bytes | `7fcd3a18d4dcc692719984b07268bd42764108e7df37049f1490f20929f9925d` |

</details>

## What you need

* **Windows** and Splinter Cell Blacklist installed.
* **Python 3.8 or newer** — [python.org/downloads](https://www.python.org/downloads/).
  During installation tick **"Add python.exe to PATH"**. Nothing else to install.

## Install

**1. Close the game and Ubisoft Connect.** Fully — check the icon near the clock too.

**2. Download this repository.** On the
[repository page](https://github.com/svareyko/game-fixes) press the green `Code` button →
`Download ZIP`, unzip it anywhere (Desktop is fine) and open the
`splinter-cell-blacklist` folder inside.

**3. Double-click `apply.bat`.**

That is it. For each of the two executables the window prints something like:

```
  file        C:\Program Files (x86)\Ubisoft\...\src\SYSTEM\Blacklist_DX11_game.exe
  sha256      c52b3d0927591e477424f389ff0b1314a300938e19ce61a7b0a7bc09f81c2c89
  vtable StateProxyDetection        0x029BD4AC
  vtable StatePlatformNetworkStart  0x029BD44C
  shared pool 0x03383DF8  (Enter of both states references it)
  slot [9]    VA 0x029BD4D0  =  file 0x025BB6D0
  now         0x00775C40   (empty stub, ret 4)
  donor       0x00822C10   Exit of StatePlatformNetworkStart
  state       ORIGINAL (leak present)
  backup      created: C:\Program Files (x86)\Ubisoft\...\Blacklist_DX11_game.exe.orig
  before      40 5C 77 00  (0x00775C40)
  after       10 2C 82 00  (0x00822C10)
  verify      state on disk: patched
  sha256      4bb836c18c34135b73b682045825ad60c19f83888c5522b49e2ffd9c0eb8d7c1
```

and at the very end:

```
Done. Files changed: 2
```

What matters: **`verify      state on disk: patched`** under each file, and
**`Files changed: 2`**.

> Prefer a terminal? `python patch_pool_leak.py apply` does the same thing.
> `check.bat` inspects without changing anything.

The tool leaves two files next to each executable. `*.exe.orig` is the full untouched
backup. `*.exe.pool-leak-patch.json` is a tiny note of which 4 bytes were changed, so
that the change can be undone exactly.

### If something goes wrong

* **`ERROR: [Errno 13] Permission denied`** — the game sits in a protected folder such
  as `C:\Program Files (x86)`. Right-click `apply.bat` → **Run as administrator**.
* **`Could not find the game installation`** — the tool reads the game folder from the
  registry entry that Ubisoft Connect makes. If it is not there, tell it the folder
  yourself. Open the `splinter-cell-blacklist` folder in Explorer, type `cmd` into the
  address bar, press Enter, and run (with your own path):

  ```
  python patch_pool_leak.py apply --dir "C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\games\Tom Clancy's Splinter Cell Blacklist"
  ```

  The game folder is the one that contains `version.ini` and the `src` folder.
* **`state       UNKNOWN`, or a refusal that says `not patching` or `expected 1`** —
  your executable is not what this fix was made for. Nothing was written. Please open an
  issue and paste the whole output.

## How to check that it worked

1. Double-click **`check.bat`**. It changes nothing. Both files must show
   `state       PATCHED`.
2. Play for longer than 30 minutes. That is the real proof — and the one I still owe,
   see [Status](#status).

## Uninstall

Double-click **`revert.bat`**, or:

```
python patch_pool_leak.py revert
```

It puts the original 4 bytes back, using the `*.pool-leak-patch.json` note that `apply`
left next to the executable. If the note is gone, it copies the `*.exe.orig` backup over
the executable instead. Afterwards the file is byte for byte the original again. The
`*.exe.orig` backups stay where they are; delete them if you want the 94 MB back.

**After a game update or "Verify files" there is nothing to revert.** They have already
replaced the executable with a clean one. `revert` notices that: it compares the file with
the one the note and the backup were made from, and if they do not match it prints
`REFUSED` and writes nothing. Simply delete the leftovers from `src\SYSTEM` in the game
folder:

```
Blacklist_DX11_game.exe.orig
Blacklist_DX11_game.exe.pool-leak-patch.json
Blacklist_game.exe.orig
Blacklist_game.exe.pool-leak-patch.json
```

If you lost the backup: Ubisoft Connect → the game → **Properties → Local files →
Verify files**. That also brings back the original.

## Things that silently undo the patch

- **A game update** through Ubisoft Connect.
- **Verify files** in Ubisoft Connect.
- **Reinstalling** the game.

This is normal and expected. Nothing breaks; you are simply back to the unpatched game
and the crash. Delete the leftover `*.orig` and `*.pool-leak-patch.json` files listed
above — otherwise `apply` keeps the old backup instead of making a fresh one — and run
`apply.bat` again.

## FAQ

**Is this a cheat? Will I get banned?**
It changes no gameplay value; it makes one login step return an object it borrowed. I
found no anti-cheat module in the game process — but that is an observation, not a
promise from Ubisoft. One thing to know: any change to the executable makes its digital
signature invalid. I did not test multiplayer. Use your own judgement.

**Does it change gameplay?**
No. The only code that behaves differently runs when the online login sequence leaves
its proxy detection step, and all it does is hand a holder back to the pool — exactly
what the neighbouring login steps already do.

**Does playing offline help instead?**
I do not know. Switching Ubisoft Connect to offline mode may keep the login sequence from
running at all, which would avoid the leak, but I have not tested it, and it costs
cloud saves and multiplayer. The executable also understands an `offline` command-line
switch; I did not test that either.

**Is it safe?**
It makes a backup before touching anything, checks three separate conditions before
writing, reads the file back afterwards to confirm the result, and is fully reversible.
The reasoning is in [docs/how-it-works.md](docs/how-it-works.md#why-this-is-safe).
That said — this is an unofficial binary patch. Use at your own risk.

**Shouldn't Ubisoft fix this?**
Yes; on their side it is a one-line fix. For a game released in 2013 I would not wait
for it, so here is a patch.

**I still crash.**
Look at the Event Viewer record again. With the same fault offset, run `check.bat` —
an update or a file verification may have undone the patch. With a different offset it
is a different code path or a different bug; please open an issue with the exception
code and the fault offset.

## Status

| What | State |
|---|---|
| Root cause | found in the executable and confirmed by a full memory dump of a crashed session: the pool had 0 free holders and 20 busy ones |
| Patch applied to `Blacklist_DX11_game.exe` and `Blacklist_game.exe`, build `603495` | done on 2026-09-04 |
| Checked with a disassembler on the real game files | yes — only the one vtable slot changed (3 bytes differ from the backup), the other 15 slots of the table are byte for byte the same |
| `apply` → `apply` again → `revert` | run on a copy: the second `apply` does nothing, `revert` brings back the original SHA-256 |
| **Confirmed in game** | **not yet.** The success criterion is a session longer than 30 minutes without the crash |
| DirectX 9 executable | the same defect was found and patched by the same tool; no crash was ever recorded on it, all four were on DX11 |
| Multiplayer and other online features | not tested |

If you try it, reporting back either way is genuinely useful.

## For maintainers — a new game version

```
python patch_pool_leak.py scan
```

It prints the vtables of the three login states and what their slot `[9]` points at,
found through RTTI and not through stored addresses. The checklist for a new version is
in [docs/how-it-works.md](docs/how-it-works.md#porting-to-a-new-game-version).

## Author

Made by **[bombuilder.by](https://bombuilder.by)**.

Helped, or still crashing? Either way, [open an issue](https://github.com/svareyko/game-fixes/issues) —
the in-game confirmation this fix still needs can come from you.

## Disclaimer

Not affiliated with, endorsed by, or supported by Ubisoft. Tom Clancy's Splinter Cell
Blacklist, Uplay and Ubisoft Connect are trademarks of their respective owners. This
repository contains no game code — only a small script that edits 4 bytes in your own
local copy. Provided as-is, without warranty.
