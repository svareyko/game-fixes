# How Ore Map works

**Read this when:** you want to know how the mod works inside, change what it marks, or
port it to a new Minecraft or Xaero version.
**Not this, for:** installing and using the mod, the list of requirements, what is
verified in game → [../README.md](../README.md).
**Sections:** [1 What the client knows](#1-what-the-client-knows) ·
[2 The scanner](#2-the-scanner) · [3 Vein grouping](#3-vein-grouping) ·
[4 The bridge to Xaero's mod](#4-the-bridge-to-xaeros-mod) ·
[5 Waypoint lifetime](#5-waypoint-lifetime) · [6 The gate](#6-the-gate) ·
[7 Pitfalls found](#7-pitfalls-found) ·
[8 Porting](#8-porting-to-a-new-minecraft-or-xaero-version) · [9 The build](#9-the-build)

The sections are independent — read the one you need.
[Русская версия](how-it-works.ru.md).

Everything below was read from the mod's sources and from the bytecode of the installed
game and mods with `javap`: the Minecraft 26.2 client, Fabric API 0.157.0+26.2, Xaero's
Minimap 26.4.2 and Xaero's World Map 1.45.0. Version numbers matter here, because half of
this document describes internals of somebody else's mod.

| File | Responsibility |
|---|---|
| [`src/oremap/OreMapClient.java`](../src/oremap/OreMapClient.java) | entry point: the chunk queue, handlers for chunk load and unload, world change and tick, the key, the `/oremap` command |
| [`src/oremap/OreScanner.java`](../src/oremap/OreScanner.java) | walking chunk sections and grouping blocks into veins |
| [`src/oremap/XaeroBridge.java`](../src/oremap/XaeroBridge.java) | the only place that touches Xaero |
| [`src/oremap/Gate.java`](../src/oremap/Gate.java) | whether the mod may work here |
| [`src/oremap/OreMap.java`](../src/oremap/OreMap.java) | constants, the list of blocks, the marker name format |
| [`tools/SelfTest.java`](../tools/SelfTest.java) | the self-test run by every build |
| [`tools/ValidateMod.java`](../tools/ValidateMod.java) | runs `fabric.mod.json` through Fabric Loader's own parser |
| [`build.py`](../build.py) | the build: `javac`, four checks, the jar |

## 1. What the client knows

The mod reads nothing but the client's own memory. It sends no packets and writes nothing
into the world.

The data is there because a vanilla server sends whole chunks: the packet carries the
full block array of every section, buried blocks included, with no filtering by
visibility. In the 26.2 client `ClientboundLevelChunkPacketData.extractChunkData` walks
`LevelChunk.getSections()` and writes each section unconditionally.

The same fact sets the hard limit. The client only has the chunks within the render
distance, so a "treasure map" of the whole world is impossible from the client side —
what comes out is a radar around the player. Server software with an anti-X-ray feature
changes the premise: it hides or fakes ore in the chunk data, and the mod will show
whatever the client was told.

## 2. The scanner

`OreScanner.scan` walks the sections of one chunk. It stays cheap because of three
cut-offs, from free to expensive:

1. `LevelChunkSection.hasOnlyAir()` — free, removes most sections;
2. `LevelChunkSection.maybeHas(Predicate<BlockState>)` — a check **against the palette**
   of the section, `O(palette size)` instead of 4096 block lookups;
3. the full 16×16×16 walk — only for sections that survived the first two.

Measured on a real world save (1200 chunks, 28,800 sections): the first cut-off removes
60% of the sections, the second removes 64% of the rest, and the full walk is needed for
about 3.4 sections per chunk. That is 14–50 microseconds per chunk — cheap per chunk, but
not when chunks arrive in batches.

**Scanning runs on the client thread, on purpose.** The palette of a section is not
thread-safe without `acquire()`/`release()`, and at this price a worker thread is not
worth its synchronisation.

**But not at the moment a chunk arrives.** The integrated server hands over the whole
batch at once, ignoring the limit on its size: at render distance 32 that is 65 chunks in
one tick when a chunk border is crossed, and thousands when a world is entered. So the
load handler only puts the chunk key into a queue (`LinkedHashSet<Long>` — keys, not
`LevelChunk` references, which would get in the way of unloading). Every tick
`drainPending` takes at most `SCANS_PER_TICK` chunks from it, the ones nearest to the
player first, so markers appear around the player and not in random order. Picking the
nearest is a single pass over the queue, cheaper than sorting all of it.

**Switching on sweeps what is already loaded.** At that moment the chunks around the
player are loaded, but their load events are long gone. `enqueueAround` queues the square
of chunks that markers can reach the map from at all — `(MARKER_RADIUS >> 4) + 1` = 11
chunks each way, 529 chunks. At 16 per tick that is about 1.7 seconds. Chunks that are
not loaded drop out when the queue is drained (`getChunk(..., ChunkStatus.FULL, false)`
returns null). The same sweep runs after a world change while the mod stays on.

**Known gap: the sweep runs once.** Chunks that were loaded before the mod was switched
on and lie outside that square never produce a load event, so they are not scanned until
the game loads them again. At a render distance above 11 chunks that leaves a ring of
unscanned chunks around the place where the mod was switched on; walk into it and no new
markers appear. Switching the mod off and on sweeps around the new position. A fix would
be to repeat `enqueueAround` when the player has moved a few chunks away from the last
sweep centre — queued keys are a set, so it would cost little.

| Setting in `OreMap.java` | Value | Why |
|---|---|---|
| `MARKER_RADIUS` | 160 blocks | at render distance 32 the client holds thousands of chunks; without a radius the map turns into a mush. The distance is three-dimensional, from the player to the representative block of the vein |
| `MAX_MARKERS_PER_TARGET` | 80 | also the cap on the number of lines the mod adds to Xaero's waypoint list, so it is well below what performance allows |
| `SCANS_PER_TICK` | 16 | see above |
| `REBUILD_INTERVAL_TICKS` | 20 (one second) | the player moves, so the set of "nearest" changes even without new chunks |

Off means "not working", not "hidden": no chunk is queued or scanned, the marker set is
not rebuilt, the collected data is dropped, and Xaero holds no marker of the mod. While
the mod is not needed it costs nothing.

## 3. Vein grouping

A vein of eight diamond blocks has to give one marker, not eight. `OreScanner.cluster` is
a breadth-first walk over the 26 neighbours of each block, inside one chunk.

- **The representative of a vein is its minimal corner**: the lowest Y, then the lowest
  X, then the lowest Z. That makes the position of the marker independent of the walk
  order — the self-test feeds the same blocks in reverse and expects the same result.
- The representative is also the block the marker points at and the block whose Y goes
  into the name, and it serves as the sign that the vein is still there
  ([section 5](#5-waypoint-lifetime)).
- Blocks of different types never merge, even when they touch.
- **A vein across a chunk border gives two markers**, one per chunk. That is a deliberate
  trade-off: results are stored per chunk, so unloading a chunk can never leave a
  dangling marker.
- Positions are packed into one `long` for the hash maps: 26 bits of X, 26 bits of Z,
  12 bits of Y.

The name is built by `OreMap.markerName` — a separate method so that the self-test checks
the format, not the eye:

```
Diamonds Y-54          a single block
Diamonds x8 Y-59       a vein of eight blocks
Netherite Y15
Netherite x3 Y8
```

The depth goes into the **name**, not the symbol. World Map draws both
(`xaero.map.mods.gui.WaypointRenderer` calls `getSymbol` and `getName`), but the symbol
only has room for one or two characters — that is where `D` and `N` stay. The name is
drawn as a caption next to it.

## 4. The bridge to Xaero's mod

Xaero's mods have no public API. They do have a subsystem of third-party waypoints,
`xaero.hud.minimap.waypoint.thirdparty`, which Xaero's Minimap uses itself for Waystones
compatibility (`xaero.hud.compat.mods.SupportWaystones`). Waypoints in it live in memory
only, and every source has an `Identifier` of its own. The mod registers two sources,
`oremap:diamond` and `oremap:ancient_debris`.

The path to the manager of the current dimension:

```
BuiltInHudModules.MINIMAP.getCurrentSession()
  -> MinimapSession.getWorldManager().getAutoRootContainer()
  -> root.getPath().resolve(session.getDimensionHelper().getDimensionDirectoryName(dim))
  -> root.addSubContainer(path).getThirdPartyWaypointManager()
```

Xaero's session is created anew for every connection and world change, so nothing is
cached: the container is fetched again on every rebuild.

**What it depends on.** Fourteen classes of Xaero's Minimap, none of them a promised API:

```
xaero.common.minimap.waypoints.Waypoint
xaero.hud.minimap.BuiltInHudModules
xaero.hud.minimap.module.MinimapSession
xaero.hud.minimap.waypoint.WaypointColor
xaero.hud.minimap.waypoint.WaypointVisibilityType
xaero.hud.minimap.waypoint.thirdparty.ThirdPartyWaypointManager
xaero.hud.minimap.waypoint.thirdparty.ThirdPartyWaypoints
xaero.hud.minimap.world.MinimapDimensionHelper
xaero.hud.minimap.world.MinimapWorldManager
xaero.hud.minimap.world.container.MinimapWorldContainer
xaero.hud.minimap.world.container.MinimapWorldRootContainer
xaero.hud.module.HudModule
xaero.hud.module.ModuleSession
xaero.hud.path.XaeroPath
```

`Waypoint` still lives in the old `xaero.common` package while everything around it has
moved to `xaero.hud` — the mod is visibly in the middle of a reorganisation, so expect
breakage on minor updates, not only on a new game version. Nothing from Xaero's World Map
is referenced: it reads the waypoints from the minimap mod and draws them.

**Failing safely.** Every call into Xaero is wrapped in `try/catch (Throwable)`. On the
first error the mod prints an explanation and the stack trace into the log, sets a
`broken` flag and stays silent until the game is restarted; `/oremap status` reports
`link to Xaero: BROKEN`. For the same reason `fabric.mod.json` declares Xaero's mods as
`recommends` (`xaerominimap >= 26.4.0`, `xaeroworldmap >= 1.44.0`) and not `depends`: a
missing or incompatible minimap must not keep the game from starting. An offline probe —
loading the compiled classes with every Xaero jar removed from the classpath — shows that
`XaeroBridge` links and initialises without Xaero's classes, so a missing minimap can
only surface inside the guarded calls. In the running game this has not been tested.

**The switch.** Xaero gives third-party mods no toggle of their own; a source can only be
turned off through `ThirdPartyWaypoints.setEnabledStateGetter`, which Xaero sets for
Waystones itself. The mod does the same with `() -> OreMap.markersVisible`, so the key
turns off both the markers on the map and the lines in the waypoint list. The getter is
checked on every rebuild, because the object is recreated together with the session. The
flag is `volatile`: Xaero reads it while rendering.

**Visibility.** Every waypoint gets `WaypointVisibilityType.WORLD_MAP_LOCAL`: visible on
the World Map, absent from the minimap, no beacon in the world. This was checked in game
and is the wanted behaviour. To put the markers on the minimap as well, remove the
`setVisibility` call in `XaeroBridge`.

Colours: `WaypointColor.AQUA` for diamonds, `WaypointColor.DARK_RED` for ancient debris.

## 5. Waypoint lifetime

Four decisions, each forced by something found in Xaero's bytecode or in the game.

**The whole set is replaced, there are no point edits.**
`ThirdPartyWaypoints.remove(String)` ends with
`MinimapWorldManagerIO.getRootConfigIO().save(root)` — it writes Xaero's config to disk on
every call — and `add()` calls `remove()` itself when the waypoint object is already
registered. Removing mined-out veins one by one would mean a disk write per vein. So once
a second the mod calls `ThirdPartyWaypointManager.clearOrigin()` — pure in-memory work, it
ends in three `clear()` calls on collections — and puts the whole set back.

**The waypoint id is the position in the list, not the coordinates.** This one is not
obvious. `add()` puts an entry into the `renderInfoOverrides` map, `clear()` does **not**
touch that map, and `RootConfigIO.save` writes every entry into the world's `config.txt`
as a `third-party-waypoint:…` line. With ids built from coordinates every new vein would
add a line to that file for good: it would grow by megabytes per session and survive
restarts. Ids `0`…`79` keep the set bounded by the number of markers.

The price: if you change how one particular marker is displayed in Xaero's interface
(hide it, recolour it), the setting sticks to the slot, not to the vein, and the next
rebuild hands it to another vein. For markers that are reshuffled once a second anyway
this is acceptable.

So the worst the mod can leave behind is up to 80 inert `third-party-waypoint:…:oremap:…`
lines per ore type and dimension in Xaero's per-world `config.txt`, written only if
Xaero happens to save that file while markers exist. On the install this was checked on,
after weeks of use, the file contained none. The markers themselves are never saved.

**A mined-out vein is dropped.** The only event scanning can rely on is the arrival of a
whole chunk; ordinary mining of a block does not come with such a packet. So before every
publication `validate` looks at the representative block of each vein, and if it is no
longer the expected ore, the vein is left out and its chunk is queued for a rescan. The
same check catches mining by another player on a LAN server, creepers and lava. A vein
that lost other blocks keeps its old size in the name until its chunk is rescanned.
(Not tested in game — see the Status section of the README.)

**A world change rebinds everything, in three places.** Chunks of a new world arrive
before the end of the tick in which the world changed, so rebinding only in the tick
handler lost the chunks around both ends of a portal for the rest of the session.
`rebind` is therefore called from the chunk load handler, from
`ClientLevelEvents.AFTER_CLIENT_LEVEL_CHANGE` and from the tick — whichever sees the new
world first resets the state — and always **before** the gate is asked, so that the
verdict for the new world is not computed on top of what the previous one left.

## 6. The gate

`Gate.allowed` decides whether the mod works here. It is an allow-list: only what is
certainly local passes, anything unrecognised counts as public. The order, from
`Gate.compute`:

| # | Condition | Verdict |
|---|---|---|
| 1 | `Minecraft.hasSingleplayerServer()` | allowed — a single-player world, "Open to LAN" included, because the server is run by this very client |
| 2 | `Minecraft.getCurrentServer() == null` | refused — the server is unknown |
| 3 | `ServerData.isLan()` | allowed — the server was found by LAN discovery |
| 4 | `ServerData.isRealm()` | refused |
| 5 | `Gate.isLocalHost(Gate.hostOf(ServerData.ip))` | allowed if local, otherwise refused with the reason logged |

`hostOf` drops the port and the IPv6 brackets: `192.168.0.10:25565` → `192.168.0.10`,
`[::1]:25565` → `::1`. A string with more than one colon is taken as a bare IPv6 address
and left alone. `isLocalHost` then works on the lower-cased text:

| Accepted | How it is recognised |
|---|---|
| `localhost`, `::1`, `0:0:0:0:0:0:0:1` | exact match |
| names ending in `.local`, `.lan`, `.home`, `.internal`, `.localdomain` | suffixes handed out by home routers and mDNS |
| a bare name with no dot and no colon (`my-pc`) | such a name only resolves on a local network |
| `10.0.0.0/8`, `127.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`, `169.254.0.0/16` | four decimal octets, each 0–255, compared numerically |
| IPv6 starting with `fc`, `fd` (`fc00::/7`) or `fe8`, `fe9`, `fea`, `feb` (`fe80::/10`) | only if the text contains a colon |

**The name is never resolved.** A DNS answer can change, and the mod must not quietly
switch on at a public server because a name happened to resolve into a private range
once. The price is that a public name pointing at your home server is refused — use the
LAN address.

**The traps the self-test pins down.** `192.168.0.10.evil.com` and `10.0.0.5.attacker.net`
start like private addresses but are public names: the IPv4 check demands exactly four
numeric parts. `localhost.example.com` is not `localhost`. `172.15.0.1` and `172.32.0.1`
sit right outside `172.16.0.0/12`, `172.16.0.1` and `172.31.255.255` right inside. The
empty string is public.

The verdict is cached only for logging: the log gets one `[oremap] enabled: …` or
`[oremap] disabled: …` line per change, not one per tick. `Gate.reset` is called on every
world change. When the gate refuses, the tick handler clears the markers at Xaero, drops
everything collected and does nothing else.

What the gate does not know is the rules of a particular server. That part stays with the
player — see "Fair play" in the README.

## 7. Pitfalls found

**The classpath trap.** A `libraries` folder shared by several installed versions can
hold client jars of another Minecraft (1.21.11 was what was met) and of Forge. If the
classpath is collected by simply walking the folder, `javac` silently takes
`net.minecraft` from there: the compilation passes and the mod falls apart in the game.
`build.py` drops everything with `1.21`, `forge` or `/v1/objects/` in its path and any
`client.jar`, and puts exactly one client jar on the classpath. The trap is not
theoretical: the very first build failed on `ChunkPos.toLong()`, which 26.2 does not
have — `ChunkPos` became a record with `pack()`. With a polluted classpath that error
would have gone unnoticed. If your `libraries` folder holds other versions under other
names, extend `BAD_MARKERS`.

**A key binding is dead while a screen is open.** Minecraft handles key mappings only
when no screen is open. Open the World Map or any menu and the press goes to the screen;
the confirmation is drawn on the HUD, which is hidden as well, so from the outside it
looks like "the mod does not work". That is why the command is the primary control.

**A key conflict was the wrong suspect.** The first version used `O`, and another mod had
its own screen on the same key. It turned out not to matter for delivery: in 26.2
`KeyMapping.MAP` is a `Map<Key, List<KeyMapping>>` and `click()` goes through
`forAllKeyMappings`, so every mapping on the key receives the press. The real problem was
the previous pitfall — `O` opened that other screen, and with a screen open toggling
stops working. The key moved to the free `K`.

**Chunks arrive in batches**, not one per tick — see [section 2](#2-the-scanner).

**Chunks of a new world arrive before the tick notices the world changed** — see
[section 5](#5-waypoint-lifetime).

**Coordinate-based waypoint ids grow Xaero's `config.txt` forever**, and **`remove()`
writes to disk on every call** — both in [section 5](#5-waypoint-lifetime).

**Up to 240 lines in the waypoint list with no way to turn them off.** An early version
allowed more markers per type and had no switch, so the player's own waypoints drowned in
automatic ones. Fixed with `setEnabledStateGetter`, a cap of 80 per type and off by
default.

**`/oremap status` counts chunks with ore, not chunks scanned.** `OreScanner` stores
results per chunk and forgets a chunk without hits, so `chunkCount()` is the number of
chunks that contain at least one marked block.

## 8. Porting to a new Minecraft or Xaero version

The mod is pinned to `minecraft >=26.2 <26.3` in
[`resources/fabric.mod.json`](../resources/fabric.mod.json); on 26.3 it will not load.

1. Install the new game version with Fabric Loader, Fabric API and both of Xaero's mods.
2. Change the `minecraft` range (and the `recommends` versions) in `fabric.mod.json`.
3. Run `python build.py build`. The compiler shows what changed in Minecraft and Fabric
   API. The reference check then lists every `net/minecraft/**` and `xaero/**` class the
   mod refers to that no longer exists — that is how a Xaero reorganisation shows up
   before the game is even started.
4. For what moved inside Xaero's mod, open the new jar with `javap -p -c` and walk the
   chain from [section 4](#4-the-bridge-to-xaeros-mod) again. Re-check the three facts of
   [section 5](#5-waypoint-lifetime): whether `remove()` still saves to disk, whether
   `clear()` still leaves `renderInfoOverrides` alone, whether `clearOrigin()` is still
   memory-only.
5. Test in game what no build can: the markers on the World Map, none on the minimap,
   `/oremap status`, a mined-out vein disappearing, a second computer joining over LAN.

A mod compiled for one version is not obfuscated and needs no refmap: 26.2 ships with
Mojang's own names, and Xaero's classes are not obfuscated either. What breaks the mod is
classes that move, not names that get scrambled.

## 9. The build

**No Gradle and no Loom, and that is not cutting corners.** Minecraft 26.x ships
**unobfuscated**: Mojang stopped publishing `client_mappings` with 26.1 (1.21.11 still
has them, 26.1 and 26.2 do not), Yarn never came out for 26.2, and `fabric-intermediary`
for 26.2 is a stub with an empty `mappings.tiny`. Loom's main job, remapping, is a no-op
here. `javac` and a hand-written `fabric.mod.json` are enough, everything needed is on
disk already, and the build needs no network.

`build.py build` checks its own result, and any failed check fails the build:

1. **Compilation against the real 26.2 client** — not against mappings, but against the
   very jar the game starts. The classpath is a flat folder of jars in the system's
   temporary directory, passed as `-cp <folder>/*`: a list of a few hundred paths does
   not fit into the 32,767 characters of a Windows command line. Nested jars of Fabric
   API and of Xaero's Minimap (`META-INF/jars/`) are unpacked into the same folder.
2. **A reference check with the disassembler.** `javap -c` over every class of the mod,
   all references to `net/minecraft/**` and `xaero/**` are extracted, and each one is
   looked up in the client jar and in the installed minimap. It catches both a
   compilation against the wrong game version and internal Xaero classes that moved.
   Currently: 22 references to Minecraft, 14 to Xaero.
3. **A self-test of the pure logic** ([`tools/SelfTest.java`](../tools/SelfTest.java))
   without starting the game: 22 address cases for the gate, vein grouping (a 2×2×2 cube
   gives one marker of size 8, a lone block its own, debris touching a diamond vein stays
   separate, the representative does not depend on the input order) and marker names
   including the edge levels `Y0` and `Y-64`.
4. **The manifest is validated by Fabric Loader's own parser**
   (`ModMetadataParser.parseMetadata`): the judge is not our reading of the JSON but the
   code that will read it when the game starts. Zero warnings are required.

What none of this proves is that markers are really drawn in a running game. That needs a
person — see the Status section of the README.

How to point the build at your game: "Building from source" in the
[README](../README.md#building-from-source).
