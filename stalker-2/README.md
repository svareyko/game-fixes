# S.T.A.L.K.E.R. 2 — GPU crash `DXGI_ERROR_DEVICE_HUNG` on an RTX 5090 (Async Compute)

The game drops to the desktop after a few minutes of play — again and again in the same area —
with a "GPU crash" report. The driver itself is fine afterwards. On the PC below this was traced to the
game's own GPU work running on the async compute queue; **turning Async Compute off in the game's
graphics settings stopped the crashes**.

[Русская версия](README.ru.md) · [How it was found](docs/how-it-works.md)

## Is this you?

All of these at the same moment:

- The game closes and the Unreal crash reporter opens with **`GPU Crash dump Triggered`**.
- `Stalker2.log` (in `%LOCALAPPDATA%\Stalker2\Saved\Logs\` or in the crash folder
  `%LOCALAPPDATA%\Stalker2\Saved\Crashes\UECC-Windows-…\`) ends with:

  ```
  LogD3D12RHI: Error: GPU crash detected:
      - Device 0 Removed: DXGI_ERROR_DEVICE_HUNG
  ```

  The copy in the crash folder is UTF-16: open it in Notepad, not in a tool that expects UTF-8.
- Windows Event Viewer → *Windows Logs* → *System*: three to five errors **`nvlddmkm`, Event ID 153**
  (`Error occurred on GPUID: …`) within about ten seconds, followed by a warning **`Display`, Event ID 4101**:
  *Display driver nvlddmkm stopped responding and has successfully recovered.*

It is **not** this problem if the log says `EXCEPTION_ACCESS_VIOLATION` (that is an ordinary game crash)
or if the whole PC freezes and needs a reset.

How it looked here: five crashes in a row, each 2–10 minutes after loading a save, four of them in
**Rostok**; earlier, one after six hours of play at the Chemical Plant. Selling items to a trader and
running around during an Emission looked like triggers at first; they were not — loading a save and
walking around Rostok was enough.

## Versions

| | Seen on |
|---|---|
| Game | 2.0.6 (Unreal Engine 5.5.4), with the DLC |
| NVIDIA driver | 616.92 (the same GPU fault was also seen in another Unreal Engine 5 game on 616.56 and 616.64) |
| GPU | GeForce RTX 5090 — other cards untested |

## Fix: turn Async Compute off

1. Start the game, open **Options → Graphics**.
2. Find **Async Compute** and set it to **Off**. (The exact wording may differ with the game's language.)
3. Apply, then restart the game so the change takes effect from the start of a session.

That is all — no files are changed.

**Side effect:** with Async Compute off, textures and details in the distance may flicker — appear and
disappear. Performance drops a little.

### Undo

Set **Async Compute** back to **On**.

### What the fix does *not* survive

Nothing resets it except you: it is a normal in-game setting and is stored with your other settings.

## Experimental: keep Async Compute, switch off only one pass

**Not verified yet.** If the flicker bothers you, this keeps Async Compute on and moves only one
part of the work — Nanite's main-pass culling, the most likely culprit — back to the graphics queue.

1. Close the game.
2. Open `%LOCALAPPDATA%\Stalker2\Saved\Config\Windows\` (paste it into the Explorer address bar).
3. Create a text file named `Engine.ini` (or open the existing one) and add:

   ```ini
   [SystemSettings]
   r.Nanite.AsyncComputeMainPassCullingAndBinning=0
   ```

   If the file already has a `[SystemSettings]` section, add only the second line under it.
4. Save, then **right-click the file → Properties → tick Read-only → OK**. Without this the game deletes
   the file after reading it at startup.
5. Start the game and set **Async Compute** back to **On**.

If the game still crashes, go back to the plain fix above. To undo: untick Read-only, remove the line
(or delete the file if you created it for this).

## Help find the cause

If you hit this crash, these lines make the next crash report say what the GPU was doing at that
moment (Direct3D 12 "DRED"). Add them to the same `Engine.ini` under `[SystemSettings]`, keep the file
read-only, and look for `DRED:` lines at the end of `Stalker2.log` after the crash:

```ini
r.GPUCrashDebugging=1
r.GPUCrashDebugging.Breadcrumbs=1
r.D3D12.DRED=1
```

They cost a few percent of frame rate; remove them when you are done. The NVIDIA driver also writes
its own dump right after the crash: `C:\ProgramData\NVIDIA Corporation\nvtopps\nct\NV_dmp_<N>.nv-gpudmp`
plus a `.json` next to it. There are several numbered slots — copy the newest one before the next
crash.

## The PC it happened on

| | |
|---|---|
| GPU | ASUS ROG Astral GeForce RTX 5090 LC OC, 32 GB, VBIOS 98.02.2E.40.EA, PCIe 5.0 ×16 |
| CPU | Intel Core Ultra 9 285K |
| Motherboard | ASUS ROG MAXIMUS Z890 EXTREME, BIOS 3305 |
| Memory | 96 GB DDR5 (2 × 48 GB), XMP, 6200 MT/s |
| OS | Windows 10 Pro 22H2 (build 19045) |
| Driver | NVIDIA 616.92 |
| Displays | five 3840 × 2160 monitors: four on the RTX 5090, one on the CPU's integrated graphics |
| Game settings | 2560 × 1440 borderless window, DLSS (DLAA, 100 %), DLSS Frame Generation on, Reflex on |

The card itself was tested on the same evening, right after three crashes in 18 minutes: a 16-minute
video-memory test (memtest_vulkan) and a 30-minute FurMark 2 run with its artifact scanner at the
600 W power limit — no errors, no driver resets, 64 °C at most.

## State

- **Async Compute off:** no crash in the first play session after the change, in the same place where
  the game had crashed every 2–10 minutes. One session — promising, not yet proven over weeks.
- **The `r.Nanite…=0` variant:** not tested in play yet.
- **Root cause:** narrowed down, not proven. See [how it was found](docs/how-it-works.md).

## Questions

**Is my graphics card broken?** On this PC the stress and memory tests were clean, and the crash
followed a place in the game rather than load or temperature. That points to software — the game, the
driver or the two together — not to a failing card. It does not prove the card is perfect.

**Does Frame Generation or Reflex cause it?** Not directly: the crash happened inside the game's own
list of draw commands, not in the frame generation step. See the technical write-up.

## Author

Made by **[bombuilder.by](https://bombuilder.by)**.

## Disclaimer

Unofficial. Not affiliated with, endorsed by or connected to GSC Game World or NVIDIA.
S.T.A.L.K.E.R. 2 and all related trademarks belong to their owners. Everything here is at your own risk.
