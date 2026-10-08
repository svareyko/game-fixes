# game-fixes

Fixes, patches and small mods for PC games. Each one was investigated down to the actual cause —
a crash dump, a disassembly, the site's own code — and each one can be undone.

[Русская версия](README.ru.md)

| Folder | What it is | State |
|---|---|---|
| [mapgenie/](mapgenie/) | **MapGenie Tweaks** — a userscript for the interactive maps on mapgenie.io: remembers the marker categories you chose (per map) and removes the ads. One-click install into Tampermonkey | verified on the live site |
| [cossacks-back-to-war/](cossacks-back-to-war/) | **Cossacks: Back to War** (Steam) on a modern PC: the game no longer switches the real desktop resolution and scrambles windows across monitors, the main menu is no longer cut off, no crash on mission load at high resolutions | all three verified in game |
| [splinter-cell-blacklist/](splinter-cell-blacklist/) | **Splinter Cell Blacklist**: the crash to desktop after about half an hour of play — a leaking object pool in the online login state machine, fixed by changing one value in a vtable | patch applied and checked with a disassembler, awaiting confirmation in play |
| [stalker-2/](stalker-2/) | **S.T.A.L.K.E.R. 2**: `DXGI_ERROR_DEVICE_HUNG` / "GPU Crash dump Triggered" a few minutes into play on an RTX 5090 — traced with the NVIDIA driver's own crash dump and Direct3D 12 DRED to the game's async compute work; a game setting stops it | workaround verified in one play session; root cause narrowed down, not proven |
| [minecraft/](minecraft/) | Three **Fabric mods for Minecraft 26.2**: hamsters, metal torches, diamond and ancient-debris markers on Xaero's map | see each mod |

Published separately: **[ready-or-not-crash-fix](https://github.com/svareyko/ready-or-not-crash-fix)** —
the host crash in Ready or Not co-op (since fixed by the developers themselves).

## How to use

Every folder has its own `README.md` written for players, not programmers: how to recognise the
problem, what you need, installation step by step, how to check it worked, how to undo it.

- **The userscript** installs with one click from its README.
- **The Minecraft mods** are downloads on the [Releases](https://github.com/svareyko/game-fixes/releases) page.
- **The game patches** are small Python scripts with `apply.bat` / `check.bat` / `revert.bat` next
  to them. [Download this repository as a ZIP](https://github.com/svareyko/game-fixes/archive/HEAD.zip),
  unpack it anywhere, open the folder of your game and follow its README. You need
  [Python 3](https://www.python.org/downloads/) (tick *Add python.exe to PATH* during setup).

## What to expect from a patch here

- **It checks before it writes.** A patcher compares the bytes it is about to change with what it
  expects and refuses to touch a version it does not know. A game update moves code around; a patch
  silently applied to the wrong place is worse than no patch.
- **It makes a backup first**, and `revert` brings the original back.
- **`check.bat` changes nothing** — it only reports what it found and what `apply` would do.
- **Nothing is sent anywhere.** No telemetry, no network access, no installers. Plain source you can read.
- **Game files are never redistributed here.** You patch your own copy.
- A game update or "verify integrity of game files" restores the original files and removes a
  patch. That is normal; run the patcher again — it will tell you whether the new version is supported.

Each README says honestly what was verified in the game and what was only verified on paper.

## How it works

The technical write-ups — root cause, addresses, bytes before and after, why the change is safe,
how to port it to a new game version — live in `docs/how-it-works.md` of each folder.

## Author

Made by **[bombuilder.by](https://bombuilder.by)**.

## License

[MIT](LICENSE) — use it, change it, ship it; just keep the copyright notice.

## Disclaimer

Unofficial fan-made fixes. Not affiliated with, endorsed by or connected to the developers or
publishers of any of these games, to Mojang or Microsoft, or to MapGenie. All game titles and
trademarks belong to their respective owners. You use everything here at your own risk.
