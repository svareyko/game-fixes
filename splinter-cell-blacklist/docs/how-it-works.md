# How the fix works

**Read this when:** you want to know what exactly is broken in the game and why a 4-byte
change fixes it, or you are porting the fix to another game version.
**Not this, for:** installing, checking or removing the fix → [README](../README.md).
**Sections:** [The crash](#the-crash) ·
[The faulting instruction](#the-faulting-instruction) ·
[Why null is a legal value there](#why-null-is-a-legal-value-there) ·
[Where the null comes from](#where-the-null-comes-from) ·
[How the pool works](#how-the-pool-works) ·
[The defect](#the-defect) ·
[Proof from the memory dump](#proof-from-the-memory-dump) ·
[What the patch changes](#what-the-patch-changes) ·
[How the tool finds the place](#how-the-tool-finds-the-place) ·
[Why this is safe](#why-this-is-safe) ·
[All eight states audited](#all-eight-states-audited) ·
[What the patch does not do](#what-the-patch-does-not-do) ·
[What was ruled out](#what-was-ruled-out) ·
[Not verified](#not-verified) ·
[Porting to a new game version](#porting-to-a-new-game-version)

This is a reference document — jump to the section you need.

Everything below was derived from the shipping executable `Blacklist_DX11_game.exe`
(game version `SC6_pcbranch_V2425.0_C603495`, Ubisoft Connect, 32-bit), from four crash
reports, one minidump and one full memory dump of a crashed session.

All addresses are **virtual addresses**. The image base is `0x00400000`, relocations are
stripped and ASLR is off, so an address is the same number in the file, in a debugger and
in a crash dump. The *fault offset* that Windows reports is relative to the image base:
`0x00422C5C` + `0x00400000` = `0x00822C5C`.

`Blacklist_game.exe`, the DirectX 9 executable, carries the same defect at different
addresses; they are listed in [What the patch changes](#what-the-patch-changes).

## The crash

```
Exception code   0xC0000005  (access violation, reading address 0x00000000)
Fault offset     0x00422C5C  ->  VA 0x00822C5C
Faulting module  Blacklist_DX11_game.exe
WER bucket       22645ae42018a2885a5e49021f17ce34
```

Four recorded crashes agree in every field, down to the offset. Time from process start
to the crash: **28:19, 27:04, 28:34, 28:35**. The same offset four times means that one
and the same instruction fails, not "wherever it happens to break".

The run time comes from the Windows Error Reporting file `Report.wer`: the last two
groups of its `AppSessionGuid` are the FILETIME of the process start, in memory byte
order.

## The faulting instruction

`0x00822C30` is slot `[0]` — the per-frame tick — of the virtual function table at
`0x029BD504`. RTTI (Complete Object Locator at `0x02D80F24`) names the class:

```
.?AVStateLoggingInToRdv@nsOnlineConnection@@
```

That is `nsOnlineConnection::StateLoggingInToRdv`, the state that logs in to Quazal
Rendez-Vous, Ubisoft's online service. The state machine has eight states:
`StateOffline`, `StatePlatformNetworkStart`, `StateProxyDetection`, `StateSetLocale`,
`StateVerifyingServerVersion`, `StateLoggingInToRdv`, `StateOnline`,
`StateLoggingOutFromRdv`. The tick of the current state is called every frame from the
state machine at `0x0081EA60` (the call is `0x0081EBFF call eax`).

```asm
00822C30  push ebp                       ; function start; only the prologue follows:
          ...                            ; SEH frame, stack cookie, push esi/edi
00822C57  8B F1        mov  esi, ecx     ; esi = this
00822C59  8B 46 34     mov  eax, [esi+0x34]
00822C5C  80 38 00     cmp  byte ptr [eax], 0    ; <-- HERE, eax == 0
00822C5F  0F 85 ...    jne  0x00822D96           ; "holder is empty" -> normal exit
00822C65  8B 40 1C     mov  eax, [eax+0x1C]
00822C68  85 C0        test eax, eax
00822C6A  0F 84 ...    je   0x00822D96           ; the same normal exit
```

Between the function entry and the faulting instruction there is not a single `test` or
`cmp` on `eax`.

The exception record and the registers from the dump:

```
ExceptionCode        0xC0000005
ExceptionAddress     0x00822C5C
ExceptionInformation [0, 0]          ; 0 = read, accessed address = 0
Eip = 0x00822C5C
Eax = 0x00000000     ; the dereferenced pointer
Ecx = Esi = 0x489D7158   ; this
Edx = 0x029BD504     ; vtable of StateLoggingInToRdv - the object type, confirmed at run time
```

The important part: `this` is alive, `mov eax, [esi+0x34]` ran without a fault, and the
value it read is **exactly zero**, not garbage. That closes "memory corruption",
"use after free" and "uninitialised pointer" — each of them would produce a garbage
address, not `0`.

## Why null is a legal value there

The field at `+0x34` holds the result of an asynchronous operation (a `NetResult`
holder). The rest of the class treats `NULL` as a normal value and checks for it:

* slot `[7]` = `0x00780FB0` is nothing but `mov dword ptr [ecx+0x34], 0 / ret`; it is
  called when the state is registered;
* slot `[9]`, leaving the state, = `0x00822DB0` starts with
  `cmp dword ptr [ecx+0x34], 0 / je` — **the null check is there**; the release helper
  `0x0080EAC0` writes the zero itself on its success path (`0x0080EB1E`);
* the request sender `0x0086EEA0` also provides for a zero (`0x0086F012`).

**Only slot `[0]`, the tick, has no check.** The safe way out is even written already:
`0x00822D96`, the target of both regular checks in that function.

The twin class `StateLoggingOutFromRdv` has the same unguarded idiom (slot `[0]` =
`0x00822F80`, dereference at `0x00822FAC`, its own exit `0x0082308E`). No crash was ever
observed there.

So the tick is where the game falls over, but it is not where the null is made.

## Where the null comes from

`StateLoggingInToRdv::Enter` (slot `[8]`, `0x0089AD00`) asks a pool for a holder:

```asm
0089AEB0  mov  ecx, dword ptr [0x3383DF8]   ; the pool; ecx is not changed until the call
0089AEB6  mov  eax, dword ptr [ecx+0x18]
0089AEB9  cmp  byte ptr [eax+0x414], 0      ; precondition
          ...
0089AEFB  call 0x00829450                   ; Alloc(this = the pool)
          ...
0089AF09  mov  dword ptr [esi+0x34], eax    ; the result goes into this+0x34, unchecked
```

`Alloc` starts by comparing the free counter `[edi+0xF4]` with zero; when nothing is free
it jumps (`jbe`) straight to its exit with `eax = 0`.

The full memory dump (2 052 376 570 bytes, `Memory64List`, 7062 ranges, 1955 MB of
process memory) shows exactly that situation:

```
state object 0x489D7158
  +0x10 status    = 0            ; not 4 (error): Enter took its normal path
  +0x14           = 0
  +0x30 owner     = 0x48A1A1B0
  +0x34 holder    = 0            ; NULL

pool = [0x03383DF8] = 0x489D3718
  +0xF4  free     = 0            ; <-- this is it
  +0x124 busy     = 20
  [pool+0x18]+0x414 = 0x01       ; the precondition Enter tests at 0x0089AEB9 held
```

Status `0` together with the precondition byte `0x01` means that `Enter` reached
`0x0089AEFB call 0x00829450`, and `Alloc` returned `NULL` because nothing was free.

A minidump is useless for this: the heap is not in it, so neither the state object nor
the pool can be read. It takes a full dump (`MiniDumpWithFullMemory`).

## How the pool works

Inside the pool object there are three lists with the same layout,
`{allocator 0x034DC108, tag, head, tail, count}`, `0x14` bytes each:

| Offset | Head | Tail | Count | Meaning |
|---|---|---|---|---|
| `+0xE4` | `0x489D3804` | `0x489D3804` | **0** | free — head equals tail equals the sentinel inside the pool itself, so the list is empty |
| `+0xFC` | `0x489D381C` | `0x489D381C` | 0 | released, waiting to go back to "free" — empty |
| `+0x114` | `0x001C5418` | `0x001C4038` | **20** | busy |

The busy list was walked to the end: circular, doubly linked, sentinel `0x489D3834`,
exactly 20 nodes `{next, prev, obj}`, objects `0x489D38A8` … `0x489D3BA0`. The number 20
is fixed when the pool is built (around `0x0088CFC5`, `mov [ebp-0x10], 0x14`); the pool
never grows.

The life cycle of a holder:

* `Alloc` `0x00829450` takes it from "free" and puts it into "busy";
* `Free` `0x0080EAC0` takes it from "busy", puts it into "released" and writes zero into
  the owner's field (`0x0080EB1E mov dword ptr [edi], 0`);
* `0x0083AEA0`, called on every update from `0x00887220`, moves "released" back to
  "free".

So the pool itself works. A holder comes back if, and only if, somebody calls `Free`.

All twenty busy holders look the same:

```
[obj+0x00] discriminator = 0
[obj+0x14]               = 0          ; the holder's own field, zeroed by Alloc
[obj+0x1C] pointer       = non-null   ; -> an object with the vtable 0x029C5FDC
```

By RTTI the object behind `+0x1C` is `.?AUNetResultProxy@@`. Its result code — the field
`+0x14`, returned by vtable slot `[3]` = `0x00803DC0`, `mov eax, [ecx+0x14] / ret` — is
`0x80000001` in all twenty. The tick treats that value as a failure: it passes the
`test eax, 0xD0000000` filter, matches none of the special codes and ends in the branch
that sets the state status to 4. These are therefore not twenty operations still waiting
for an answer. They are twenty **finished** operations whose holders nobody returned.

## The defect

`nsOnlineConnection::StateProxyDetection`:

| | |
|---|---|
| `Enter`, slot `[8]` = `0x00883BF0` | `mov ecx, [0x3383DF8] / call 0x829450 (Alloc) / mov [esi+0x34], eax` — takes a holder from the pool and stores it in `this+0x34`, with no null check |
| `Exit`, slot `[9]` = `0x00775C40` | `ret 4` — **does nothing at all** |

The twin state `StatePlatformNetworkStart` (`Enter` `0x00837930` — the same pool, the
same field `+0x34`) has a real `Exit` in slot `[9]`, at `0x00822C10`:

```asm
00822C10  83 C1 34           add  ecx, 0x34            ; &this->m_holder
00822C13  51                 push ecx
00822C14  8B 0D F8 3D 38 03  mov  ecx, [0x03383DF8]    ; the pool
00822C1A  E8 A1 BE FE FF     call 0x0080EAC0           ; Free
00822C1F  C2 04 00           ret  4
```

Every pass through `StateProxyDetection` therefore uses up one slot of twenty for good.
When the pool is empty `Alloc` hands out `NULL`, and the first caller dereferences it.
In all four recorded crashes that caller was the tick of `StateLoggingInToRdv`.

Twenty slots in about 28 minutes is one lost holder every 85 seconds or so. What drives
that rhythm was not traced to the end. The dump shows twenty identical failed
operations, which fits a login attempt that fails and is tried again on a timer, each
attempt passing through proxy detection once.

## Proof from the memory dump

The states live in an array inside the controller `0x48A1A1B0`, `0x40` bytes apart:

| Address | Class | `+0x34` (holder) |
|---|---|---|
| `0x489D70D8` | `StatePlatformNetworkStart` | `0` — its `Exit` ran and released the holder |
| `0x489D7118` | `StateProxyDetection` | `0x489D39C0` — **holds it and will never let go** |
| `0x489D7158` | `StateLoggingInToRdv` | `0` — this is where it crashed |

`Free` zeroes the owner's field, so the zero in `StatePlatformNetworkStart` proves that
slot `[9]` **is called** and does its job where there is a job in it.

Of the 20 busy holders 19 are orphans: nothing in the whole process memory points at
them except the pool's own busy-list node. The twentieth is the one that
`StateProxyDetection` holds right now.

## What the patch changes

One dword in `.rdata`: slot `[9]` in the vtable of `StateProxyDetection` is pointed at
the `Exit` of `StatePlatformNetworkStart`. Not a byte of new code — the function is
already in the executable and already does this job for the neighbouring state.

| | `Blacklist_DX11_game.exe` | `Blacklist_game.exe` (DX9) |
|---|---|---|
| vtable of `StateProxyDetection` | `0x029BD4AC` | `0x0297FEA4` |
| vtable of `StatePlatformNetworkStart` | `0x029BD44C` | `0x0297FE44` |
| slot `[9]`, VA | `0x029BD4D0` | `0x0297FEC8` |
| slot `[9]`, file offset | `0x025BB6D0` | `0x0257EAC8` |
| before | `40 5C 77 00` = `0x00775C40`, the shared empty stub `ret 4` | `F0 3E A1 00` = `0x00A13EF0`, the same kind of stub |
| after | `10 2C 82 00` = `0x00822C10`, `Exit` of `StatePlatformNetworkStart` | `50 E0 AB 00` = `0x00ABE050` |
| pool global | `0x03383DF8` | `0x032B5DC8` |
| SHA-256 before | `c52b3d0927591e477424f389ff0b1314a300938e19ce61a7b0a7bc09f81c2c89` | `7fcd3a18d4dcc692719984b07268bd42764108e7df37049f1490f20929f9925d` |
| SHA-256 after | `4bb836c18c34135b73b682045825ad60c19f83888c5522b49e2ffd9c0eb8d7c1` | `690f721db38a36aa8c7b7c0fe99dd2a20b5078fa64a3418afac5ef75144ba635` |

In each file exactly 3 bytes differ from the backup, because the fourth byte of the dword
happens to be `00` both before and after.

`patches/603495/patch_pool_leak.json` is the machine-readable copy of this table. The
tool does not read it; it is the record of what a correct result looks like on this
build.

## How the tool finds the place

`patch_pool_leak.py` stores no addresses. It finds both vtables through RTTI:

```
type name ".?AV<class>@nsOnlineConnection@@"
  -> TypeDescriptor            (starts 8 bytes before the name)
  -> Complete Object Locator   (its field +12 points at the TypeDescriptor, its signature is 0)
  -> vtable                    (starts right after the dword that points at the locator)
```

The new value is read from slot `[9]` of the donor, not taken from a constant. That is
why the same script patches the DX9 executable, where everything sits elsewhere, and why
it survives a game update for as long as the classes keep their names.

It refuses to write when:

* a class is not found through RTTI, or is found more than once — the type name, the
  locator and the vtable must each be unique;
* the donor's `Exit` does not have the shape
  `83 C1 34 51 8B 0D <pool> E8 <rel32> C2 04 00`;
* `Enter` of the two states does not reference the same pool, or that pool is not the one
  in the donor's `Exit`;
* the function that slot `[9]` points at now is not the stub `C2 04 00` — the state is
  then reported as `UNKNOWN` and the file is left alone.

`apply` makes the backup `<exe>.orig` unless one exists, writes the dword, stores offset,
both values and both SHA-256 sums in `<exe>.pool-leak-patch.json`, then reads the file
back from disk and runs the whole analysis again; anything but `patched` is an error.
`revert` restores the 4 bytes from that note, or, if the note is missing, copies the
backup over the executable.

## Why this is safe

* **`Free` is robust.** With `*pHolder == 0` it returns at once; with a pointer that is
  not in the busy list it walks to the sentinel and returns without changing anything.
  Even a call on a field that was never filled is harmless.
* **Exactly one dword changes.** Checked with a disassembler on the real game files: the
  other 15 slots of the vtable are byte for byte the same.
* **Donor and patient match.** `Enter` of both states does the same thing — the same
  global pool, the same field `+0x34` — and the tool verifies this before it writes.
* **Fully reversible.** `revert` puts the original dword back and the SHA-256 equals the
  original again. Run on a copy: `apply` → second `apply` (does nothing) → `revert` →
  `c52b3d09…f81c2c89`.

## All eight states audited

After patching, every class of the state machine was examined: `Enter` (slot `[8]`) and
`Exit` (slot `[9]`) disassembled in full, with the real function bounds, and every direct
call collected. The sign of a leak is an `Enter` that calls `Alloc` `0x00829450` with an
`Exit` that does not call `Free` `0x0080EAC0`.

| State | `Enter` takes from the pool | `Exit` releases | Verdict |
|---|---|---|---|
| `StateLoggingInToRdv` | yes | yes (`0x00822DB0`) | fine |
| `StateLoggingOutFromRdv` | yes | yes (`0x008230B0`) | fine |
| `StatePlatformNetworkStart` | yes | yes (`0x00822C10`) | fine |
| `StateProxyDetection` | yes | yes (`0x00822C10`) — **after the patch** | fine |
| `StateOffline` | no | empty stub | harmless |
| `StateVerifyingServerVersion` | no | empty stub | harmless |
| `StateOnline` | no | — | harmless |
| `StateSetLocale` | no | — | harmless |

Nobody leaks any more. Two states keep an empty `Exit`, but they never touch the pool,
so for them that is correct.

The audit covers this state machine only. The pool is shared by about 106 places in the
online subsystem, and in principle something outside the state machine could leak as
well. Nothing points that way: in the dump the only holder with a living owner belonged
to `StateProxyDetection`.

## What the patch does not do

It removes the leak. It does not add null checks to the other users of the pool: of 123
call sites of `Alloc` at least 105 pass this same global pool, and not one checks the
result. If the pool ever runs dry for another reason, the game will crash again — just
somewhere else.

Two alternatives were considered and dropped:

* **A null check in the crashing tick.** It would treat one site out of about 106. And
  with an empty pool the login state would then sit there forever: the states have no
  timeout (slot `[1]` of all eight is the stub `0x00775BF0`, `fldz / ret`, that is 0.0).
  The bytes were worked out but never written to the game files, and with the leak gone
  the pool no longer runs dry.
* **A bigger pool.** It only moves the crash further away.

For reference: the idiom `mov eax, [esi+0x34] / cmp byte ptr [eax], 0` occurs in `.text`
85 times — it is the inlined accessor of the whole `NetResult` family. Patching all of
them would be pointless and risky.

## What was ruled out

| Suspect | Verdict |
|---|---|
| Memory corruption, use after free, garbage pointer | Refuted by measurement: `Eax = 0`, `ExceptionInformation = [0, 0]`, `Edx` is a valid vtable, `this` is alive. |
| Third-party modules: overlays, anti-cheat, hooks, cracks, proxy DLLs | Excluded. The executable's signature is valid (`CN=UBISOFT ENTERTAINMENT INC.`), there are no substitute `dinput8` / `d3d9` / `dxgi` / `winmm` / `version` / `xinput` DLLs in the game folder, and no third-party frames on the crash stack. The overlay and capture DLLs that were loaded changed versions between the crashes; the fault offset did not move. |
| Video driver, TDR, WHEA, sleep and wake-up | Excluded: the Windows `System` log is empty around every crash, and no graphics code is on the path to the fault. |
| DNS, firewall, proxy, LSP | Excluded as the cause: nothing blocks the game, and the network cannot make the `+0x34` field invalid. |
| Ubisoft's online configuration service answering with nothing | Refuted by a live check: asked with the identifier taken from the executable, the service returns a complete configuration. |
| 32-bit address space pressure, `RADAR_PRE_LEAK_WOW64` | Not involved. Private commit was 1.49 GB, and the executable is `LARGE_ADDRESS_AWARE` (`Characteristics = 0x0123`), so its limit is 4 GB. Windows' leak diagnosis fired in minute 3, the crash came in minute 28. |
| "The pool never takes objects back by design" | Refuted: `0x0083AEA0` moves released holders back to the free list on every update. The pool works; what does not work is the `Exit` of one state. |

## Not verified

* **In game.** The patch has been on both executables since 2026-09-04 and is verified in
  the binary. A session longer than 30 minutes without the crash has not been played
  yet. If the crash ever returns with the patch in place, a full memory dump settles it
  in a minute: read the pool pointer at `[0x03383DF8]` and its free counter at `+0xF4`.
  With the patch working, that counter must not fall to zero.
* **The 85-second rhythm** — see [The defect](#the-defect).
* **Offline mode of Ubisoft Connect** as a workaround. The login state machine most
  likely does not start then. Not tested; it costs multiplayer and cloud saves.
* **The `offline` command-line switch.** It exists: `0x00871BD7` sets the byte
  `[this+0x444]` when the command line contains `offline`, and `Enter` of
  `StateLoggingInToRdv` reads it at `0x0089AD2E`. The branch it takes, `0x0089AD38`,
  produces the same result `0x40000000` and the same status 4 as an ordinary login
  failure and never reaches `Alloc`. Whether the state machine still passes through
  proxy detection with the switch set — and so still leaks — was not checked.
* **The DX9 executable in play.** The defect and the patch are confirmed in the file; no
  crash was ever recorded on it, because every recorded session used DX11.
* **Multiplayer and other online features.**

## Porting to a new game version

The tool needs no table for a new version: if the classes keep their names and the three
preconditions hold, `apply` simply works. What a new version does need is the same
verification this one had.

```
python patch_pool_leak.py scan
```

prints, for each executable, the vtables of `StateProxyDetection`,
`StatePlatformNetworkStart` and `StateLoggingInToRdv` and what slot `[9]` of each points
at. On an untouched build `603495`:

```
    StateProxyDetection          vtable 0x029BD4AC  slot[9] = 0x00775C40 (empty stub)
    StatePlatformNetworkStart    vtable 0x029BD44C  slot[9] = 0x00822C10
    StateLoggingInToRdv          vtable 0x029BD504  slot[9] = 0x00822DB0
```

Then:

1. `python patch_pool_leak.py check` must show `ORIGINAL (leak present)` for each
   executable. That line appears only when all the preconditions from
   [How the tool finds the place](#how-the-tool-finds-the-place) hold.
2. `python patch_pool_leak.py apply`.
3. **Verify with a disassembler** that slot `[9]` of `StateProxyDetection` now holds the
   address of the donor's `Exit` and that the rest of the vtable is untouched. "The
   script reported success" is not verification.
4. Write the values down in `patches/<build>/patch_pool_leak.json`, next to the existing
   one. The build number is `main=` under `[changelist]` in `version.ini` in the game
   folder.
5. Delete backups left from the previous version (`*.exe.orig`,
   `*.exe.pool-leak-patch.json` next to the executables) **before** `apply`, or the tool
   keeps the stale backup.

If the tool refuses, the developers have changed this code. Start again from a fresh
crash record: fault offset → the function that contains it → its vtable and class name
through RTTI → compare `Enter` and `Exit` of every state of the machine. The state whose
`Enter` calls `Alloc` while its `Exit` never calls `Free` is the leak.
