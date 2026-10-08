# How it was found — S.T.A.L.K.E.R. 2 GPU crash with Async Compute

**Read this when:** you want the evidence behind the [README](../README.md), want to check whether your
crash is the same, or want to dig further.
**Sections:** 1 What the crash looks like · 2 The NVIDIA driver's dump · 3 What the GPU was doing (DRED) ·
4 What it means · 5 What was ruled out · 6 Open questions · 7 Collecting the same data

[Русская версия](how-it-works.ru.md)

## 1. What the crash looks like

Game 2.0.6 (Unreal Engine 5.5.4), NVIDIA driver 616.92, RTX 5090. Every crash had the same shape:

| Source | What it shows |
|---|---|
| Crash reporter, `CrashContext.runtime-xml` | `CrashType = GPUCrash`, `ErrorMessage = GPU Crash dump Triggered` |
| `Stalker2.log` | `GPU crash detected: Device 0 Removed: DXGI_ERROR_DEVICE_HUNG`; video memory in use about 10 GB of a 31 GB budget — not an out-of-memory case |
| System event log | three to five `nvlddmkm` Event ID 153 within ~10 s, then `Display` Event ID 4101 (Windows' timeout detection and recovery, TDR, reset the GPU) and a `LiveKernelEvent 141` report |
| CPU-side crash | none: the report is the engine's own reaction to the lost device, not a fault in game code |

`DXGI_ERROR_DEVICE_HUNG` is only what Direct3D reports after Windows has already reset the GPU. The
reason for the reset has to come from elsewhere — sections 2 and 3.

| When | Seconds after start | Where |
|---|---|---|
| day 1 | 21 403 (≈ 6 h) | Chemical Plant |
| day 2, three crashes in 18 minutes | 568 · 271 · 248 | Garbage, Rostok, Rostok |
| day 3 | 126 · 138 | Rostok, Rostok (the second one with no trading at all, during an Emission) |

## 2. The NVIDIA driver's dump

After every such reset the driver writes `C:\ProgramData\NVIDIA Corporation\nvtopps\nct\NV_dmp_<N>.nv-gpudmp`
and a small `NV_dmp_<N>.json`. Slots are numbered and were filled in order (`_0`, `_1`, … `_5`); the
engine does not need any setting for this.

The `.nv-gpudmp` is an NVIDIA Nsight Aftermath crash dump. It can be decoded without Nsight Graphics:
the game ships the Aftermath library itself
(`Engine\Binaries\ThirdParty\NVIDIA\NVaftermath\Win64\GFSDK_Aftermath_Lib.x64.dll`), and its
`GFSDK_Aftermath_GpuCrashDump_CreateDecoder` / `…GenerateJSON` functions turn the dump into JSON.

All six dumps from this game say the same about the fault:

| Field | Value |
|---|---|
| Device state | `Error_DMA_PageFault` — an addressing fault, not a timeout |
| Faulting GPU virtual address | **`0`** |
| MMU fault type | "The MMU returned an unknown reason" |
| Reset | engine reset, no adapter reset |
| Event markers | none |

The faulting shader is a **compute shader**, and it comes in two variants:

| Size | Start address | Hash in the `.json` | Seen |
|---|---|---|---|
| 57 856 bytes | `0x200419c00` | `0xd3dec00000000001` | 3 times here (driver 616.92); also twice in Ready or Not (Unreal Engine 5.3.2) on drivers 616.56 and 616.64 — the `.json` byte for byte the same |
| 42 752 bytes | `0x200474b00` | `0x00000000d3d55001` | 3 times here, with two or three trap addresses in the `.json` instead of one |

The same shader at the same GPU address in two different games and on three driver versions cannot
be game content. Both hashes look synthetic (`d3d…`) and both shaders sit at the very start of the
shader heap — most likely shaders of the driver itself, run while it processes the game's commands.
This last point is an inference, not verified.

## 3. What the GPU was doing (DRED)

Direct3D 12 Device Removed Extended Data records which commands of which command list the GPU had
finished. The engine prints it into `Stalker2.log` when `r.D3D12.DRED=1` is set (see the README).
Without it the log says `DRED: No command list found with active outstanding operations` — which only
means nothing was being tracked, not that nothing was running.

Two crashes with DRED on:

**Case A** (shader 57 856 bytes):

```
DRED: Commandlist "(null)" on CommandQueue "3D Queue (GPU 0)", 378 completed of 1084
    Op: 377, DrawIndexedInstanced - LAST COMPLETED
    Op: 378 … 398, DrawIndexedInstanced
DRED: No PageFault data.
```

No other queue had unfinished work.

**Case B** (shader 42 752 bytes), loading a save and walking around Rostok:

```
DRED: Commandlist "(null)" on CommandQueue "3D Queue (GPU 0)", 594 completed of 1131
    Op: 593, ExecuteIndirect - LAST COMPLETED      (121 ExecuteIndirect in a row around it)
DRED: Commandlist "(null)" on CommandQueue "Compute Queue (GPU 0)", 1 completed of 9
    Op: 0, BeginCommandList - LAST COMPLETED
    Op: 1, Dispatch / 2, ResourceBarrier / 3, Dispatch / …
```

The graphics queue stopped in the middle of a run of `ExecuteIndirect` draws while the async compute
queue had started its list and not finished even the first `Dispatch`.

## 4. What it means

1. **The GPU stopped inside the game's own command lists.** Not in another program, not in the
   desktop compositor, and not in DLSS Frame Generation — frame generation runs at present time, not
   as part of a long list of the game's draws. Reflex and Frame Generation may still affect timing.
2. **A read from address zero.** A compute shader — most likely one the driver runs on the game's
   behalf — read GPU address 0. `ExecuteIndirect` takes its arguments, which can include GPU addresses,
   from a buffer the GPU fills itself. If that buffer is read before it has been written, the
   addresses in it are zero.
3. **Case B shows exactly that pair:** the graphics queue consuming `ExecuteIndirect` arguments, the
   async compute queue producing work. In Unreal Engine 5 this is what Nanite does: with
   `r.Nanite.AsyncComputeMainPassCullingAndBinning` the main-pass culling and binning run on the async
   compute queue and write the indirect arguments the graphics queue then draws with. A missing or
   broken synchronisation between the two queues — in the game, the engine or the driver — would
   produce this fault.
4. **Why Async Compute off helps:** all compute work then runs on the graphics queue, in order, and
   the cross-queue dependency disappears.

Points 2–4 are a hypothesis that fits both DRED cases; the culprit pass is not proven.

## 5. What was ruled out on this PC

| Suspect | Check | Result |
|---|---|---|
| Video memory | memtest_vulkan 0.5.0, 16 min, 25.4 of 32 GB, right after three crashes | 0 errors |
| Shader units, power delivery | FurMark 2.10.2 (Vulkan), 30 min, 2560 × 1440, artifact scanner on, up to 594 W of a 600 W limit | 0 artifacts, 0 driver resets, 64 °C max, clocks steady 2656–2738 MHz, no throttling |
| Overheating, throttling | `nvidia-smi` straight after a crash | 40 °C, no thermal or power slowdown recorded |
| Running out of video memory | `Stalker2.log` at each crash | about 10 GB used of a 31 GB budget |
| Mods | the two Russian voice-over mods installed were listed by file name | only voice lines (`VO_…`), no meshes, items or data |
| Saving the game | save file times against crash times | no pattern |
| Trading | a crash after loading a save made after the sale, with no trading | not the trigger |
| PCIe link | `nvidia-smi`, event log | PCIe 5.0 ×16, no WHEA hardware errors around the crashes |

## 6. Open questions

- **Which pass exactly.** The `r.Nanite.AsyncComputeMainPassCullingAndBinning=0` variant from the
  README would confirm the Nanite theory if the game stops crashing with Async Compute on.
- **Other cards.** Seen on one RTX 5090. Whether other RTX 50 cards, older cards or other drivers are
  affected is unknown.
- **Not everything on this PC is explained.** The same machine had a few driver resets with no game
  running at all; those left no dump, and this write-up does not cover them.
- **The engine's own Aftermath** (`r.GPUCrashDebugging.Aftermath=1`) did not switch on in this game
  build (`RHI.Aftermath=false` in the crash context), so no event markers were available.

## 7. Collecting the same data

1. Add the DRED lines from the README to `%LOCALAPPDATA%\Stalker2\Saved\Config\Windows\Engine.ini` and
   make the file **read-only** — the game deletes it after reading it at startup.
2. After a crash, copy the crash folder from `%LOCALAPPDATA%\Stalker2\Saved\Crashes\` and the newest
   `NV_dmp_<N>.*` from `C:\ProgramData\NVIDIA Corporation\nvtopps\nct\`.
3. In the crash folder, `CrashContext.runtime-xml` should now say `RHI.DRED = true` and
   `RHI.DREDHasBreadcrumbData = true`; the `DRED:` lines are at the end of `Stalker2.log` (UTF-16).
