# Ore Map — diamond and netherite markers on Xaero's World Map

**A small client-side Fabric mod for Minecraft 26.2.** It looks through the chunks your
game has already loaded, finds diamond ore and ancient debris, and puts them on
[Xaero's World Map](https://modrinth.com/mod/xaeros-world-map) as markers with the depth
in the name:

```
Diamonds x8 Y-59
Netherite Y15
```

*Minecraft 26.2 · Fabric · Xaero's Minimap · Xaero's World Map · diamond ore waypoints ·
ancient debris waypoints · netherite finder · ore markers on the map · single player and LAN only*

[Русская версия](README.ru.md) · [How it works](docs/how-it-works.md) ·
[Other mods of this repository](../README.md)

> **Single player and your own local network only.** On a public server a mod like this
> is an X-ray cheat, so it checks where you are and **switches itself off** everywhere
> except single-player worlds and servers on the local network. The exact rule is in
> [Where it works](#where-it-works-and-where-it-refuses).

---

## What it does

- Marks veins of **diamond ore** and **ancient debris** on Xaero's World Map.
- **One marker per vein**, not per block. The name holds the ore, the number of blocks
  and the depth: `Diamonds x8 Y-59` is a vein of eight blocks whose lowest block is at
  Y -59. The marker points exactly at that lowest block.
- Diamonds are aqua markers with the letter `D`, ancient debris is dark red with `N`.
- A mined-out vein drops off the map within about a second.
- **Off by default.** While it is off it does nothing at all: no scanning, no memory,
  no markers. You switch it on when you go mining and off when you are done.
- Markers are shown **on the big World Map only**. They do not clutter the minimap and
  do not hang in the world as beacons. That is deliberate.

No ready-made mod did this for Minecraft 26.2, which is why this one exists.

### Exactly which blocks

| Marker | Blocks |
|---|---|
| `Diamonds` | `minecraft:diamond_ore`, `minecraft:deepslate_diamond_ore` |
| `Netherite` | `minecraft:ancient_debris` |

Nothing else. Blocks of different types never merge into one vein, even when they touch.

### How far it looks

**It is a radar around you, not a treasure map.** Your game only knows the chunks the
server has sent it — the ones within your render distance. The mod cannot see further,
and no client-side mod can.

| Limit | Value |
|---|---|
| Where ore is searched | when you switch it on: the 23×23 chunks around you; after that: every chunk the game loads while the mod is on |
| Markers are shown within | **160 blocks** of you, measured in a straight line, height included |
| Markers per ore type | at most **80**, the nearest ones win |
| How often the set is refreshed | once a second |
| After switching on | the area around you fills in within about two seconds, nearest first |

Because the 160 blocks include height, standing on the surface shortens your sideways
reach: from Y 64 a diamond vein at Y -54 is already 118 blocks below you, so you see
about 108 blocks to each side. Down in the caves you get the full 160.

**One gap to know about.** Chunks that were already loaded but lay outside those 23×23
when you switched the mod on are not looked at until the game loads them again. With a
large render distance, a long walk in one direction can take you into such an area and
new markers stop appearing. Type `/oremap off` and `/oremap on` — that sweeps around
your new position.

## How to use it

Open chat and type:

```
/oremap on        switch the markers on
/oremap off       switch them off and free everything
/oremap status    what is going on right now
```

Then open Xaero's World Map (key `M` unless you changed it).

There is also a key: **`K`** toggles the markers, and a line above the hotbar confirms
it. You can rebind it in Options → Controls → Key Binds → Miscellaneous →
*Toggle ore markers*.

**The command is the reliable way, the key is a shortcut.** Minecraft delivers key
presses to a mod only while no screen is open. With the map, the inventory or any menu
open, `K` goes to that screen and nothing happens — which looks like "the mod is broken".
The command has no such trap.

The mod starts switched off every time you launch the game; the choice is not saved.

### When nothing shows up — `/oremap status`

```
[Ore Map] markers: ON (switch with /oremap on, /oremap off or the K key)
[Ore Map] working here: allowed — single-player world (integrated server)
[Ore Map] link to Xaero: ok
[Ore Map] chunks with ore: 212, in the scan queue: 0
[Ore Map] Diamonds: veins found 640, sent to the map 37
[Ore Map] Netherite: veins found 0, sent to the map 0
[Ore Map] marker radius 160 blocks, cap 80 per type; markers are on the world map only
```

(The numbers are an example.) Read it top to bottom, it shows at which step things
stopped:

| Line | If it says | It means |
|---|---|---|
| `markers` | `off` | you have not switched it on — it is off after every game start |
| `working here` | `NOT ALLOWED — …` | you are on a server the mod treats as public; the reason follows |
| `link to Xaero` | `BROKEN` | Xaero's Minimap is missing or was updated and changed inside; the error is in `logs/latest.log` |
| `veins found` | `0` | there is no such ore in the loaded chunks (no ancient debris in the Overworld, for example) |
| `sent to the map` | `0` while veins are found | every vein is farther than 160 blocks — go deeper or closer |

The chat messages and marker names are in English. Only the name of the key in the
controls screen is translated (English and Russian).

## Where it works and where it refuses

The check is an **allow-list**: only what is certainly local is allowed, everything that
is not recognised counts as public. It is evaluated in this order:

| # | Situation | Result |
|---|---|---|
| 1 | A single-player world, including one you opened with **Open to LAN** | **works** |
| 2 | The game cannot tell which server this is | off |
| 3 | A world the game found by itself on the local network — the multiplayer screen lists it as **LAN World** | **works** |
| 4 | Realms | off |
| 5 | Any other server: decided by the **address you typed** into the server entry | see below |

For rule 5 the port is dropped and the rest is compared as text:

| Address | Result |
|---|---|
| `localhost`, `::1`, `0:0:0:0:0:0:0:1` | **works** |
| `10.x.x.x`, `127.x.x.x`, `192.168.x.x`, `172.16.x.x`–`172.31.x.x`, `169.254.x.x` | **works** — private and link-local IPv4 |
| IPv6 starting with `fc`, `fd`, `fe8`, `fe9`, `fea`, `feb` | **works** — unique local and link-local IPv6 |
| a bare machine name without dots, such as `my-pc` or `MY-PC:25565` | **works** — such a name only exists on a local network |
| a name ending in `.local`, `.lan`, `.home`, `.internal`, `.localdomain` | **works** |
| everything else — `mc.example.net`, `8.8.8.8`, `192.168.0.10.evil.com` | **off**, the reason goes to the log |

The name is deliberately **never looked up in DNS**: an answer can change, and quietly
switching on at a public server because of one lookup is not acceptable. A name that
merely *starts* like a local address (`192.168.0.10.evil.com`, `localhost.example.com`)
is treated as public.

On a server where the mod is off, `/oremap on` still answers "ore markers are on", but
nothing is scanned and nothing appears. `/oremap status` tells you why, and the log gets
a line such as `[oremap] disabled: public server mc.example.net - ore is not shown`.

### Fair play

The gate keeps the mod off public servers, but it cannot read a server's rules.
**Do not use it anywhere such mods are forbidden**, and do not use it against people who
have not agreed to it — that includes a home server you share with friends. If in doubt,
ask the server owner. Removing or weakening the gate to use the mod on public servers is
cheating, and it is not what this mod is for.

## What you need

| | Version | Why |
|---|---|---|
| Minecraft Java Edition | **26.2** (any 26.2.x) | the jar refuses to load on anything else |
| [Fabric Loader](https://fabricmc.net/use/installer/) | 0.19.0 or newer | |
| [Fabric API](https://modrinth.com/mod/fabric-api) | any build for 26.2 | required |
| [Xaero's Minimap](https://modrinth.com/mod/xaeros-minimap) | 26.4.0 or newer | the markers are handed to it |
| [Xaero's World Map](https://modrinth.com/mod/xaeros-world-map) | 1.44.0 or newer | the map the markers are drawn on |
| Java | 25 | comes with Minecraft 26.2 |

**You need both of Xaero's mods.** The mod talks to Xaero's Minimap, which stores the
markers, and the markers are made visible on the World Map only. The mod file declares
them as *recommended*, not *required*: a missing one does not block the game from
starting (Fabric Loader only prints a warning), but the mod then has nothing to show.
What exactly happens in the game without them has not been tested. Developed and tested
with Xaero's Minimap 26.4.2 and Xaero's World Map 1.45.0.

**Client-side only.** Nothing has to be installed on the server, and other players do
not need it. Whoever wants the markers installs it on their own game.

Xaero's Minimap and Xaero's World Map are separate products by their own author. They
are not included here and are not part of this repository — download them from their
official pages.

## Install

**1. Get Minecraft 26.2 running with Fabric.** If you do not have a Fabric profile yet:
download the installer from [fabricmc.net](https://fabricmc.net/use/installer/), run it,
choose Minecraft version 26.2, press *Install*. Start the game once with the new
`fabric-loader-…-26.2` profile and close it again.

**2. Download the three mods this one needs** — Fabric API, Xaero's Minimap, Xaero's
World Map (links in the table above). On each page pick the file for **Fabric** and
**26.2**.

**3. Download `oremap-0.5.0.jar`** from
<https://github.com/svareyko/game-fixes/releases/tag/oremap-0.5.0>.

**4. Put all four `.jar` files into the `mods` folder.**

| System | Folder |
|---|---|
| Windows | press `Win+R`, paste `%APPDATA%\.minecraft\mods`, press Enter |
| Linux | `~/.minecraft/mods` |
| macOS | `~/Library/Application Support/minecraft/mods` |

If the folder does not exist, create it. If your launcher keeps a separate game folder
for every profile, use the `mods` folder of the profile you play.

**5. Start the game with the Fabric profile.**

### How to check that it worked

1. Open a single-player world and type `/oremap status`. If the game answers with the
   `[Ore Map]` lines shown above, the mod is loaded. If it says *Unknown or incomplete
   command*, the jar is not in the right `mods` folder or you started a profile without
   Fabric.
2. Go underground — below Y 16 is where diamonds are — and type `/oremap on`.
3. Open Xaero's World Map. Within a couple of seconds aqua `D` markers with names such
   as `Diamonds x4 Y-57` appear around you.

The log (`logs/latest.log`) has a line starting with `[oremap] loaded:` on every start.

## Uninstall

Delete `oremap-0.5.0.jar` from the `mods` folder. That is all.

**What happens to the markers.** They are temporary by design: they live in memory only
and are never written into your Xaero waypoint files. They disappear when you type
`/oremap off`, when you leave the world, and for good when you remove the mod. Your own
waypoints are never touched. The mod writes nothing into your worlds and has no config
file of its own. (One harmless leftover is possible in Xaero's own per-world settings
file — see [Waypoint lifetime](docs/how-it-works.md#5-waypoint-lifetime).)

## Things that silently stop it working

- **A Minecraft update.** The jar only loads on 26.2. On 26.3 Fabric Loader will refuse
  it and tell you so; the mod has to be rebuilt for the new version.
- **An update of Xaero's Minimap.** The mod uses internal classes of Xaero's mod, because
  there is no public API for this. Xaero's mods update often, and an update may move
  those classes. The mod is built to **switch itself off instead of crashing the game**:
  `/oremap status` then shows `link to Xaero: BROKEN`. Going back to the previous
  minimap version brings the markers back.
- **A launcher that manages the `mods` folder for you** may remove files it does not
  know when a profile is reinstalled or re-synced.

## FAQ

**Is this a cheat?**
On a public server — yes, seeing ore through stone is X-ray, and that is exactly why the
mod refuses to work there. In your own single-player world it is your game and your
rules. See [Fair play](#fair-play).

**Can it show ore on the whole map?**
No. Your game only receives the chunks around you, so there is nothing to show beyond
them. Walk, and the markers move with you.

**I pressed `K` and nothing happened.**
Keys reach the mod only while no screen is open. Close the map, press `K`, look for the
message above the hotbar — or simply use `/oremap on`.

**Why are there no markers on the minimap?**
On purpose: dozens of markers would bury the minimap and fill the screen with beacons.
If you want them there anyway, remove the `setVisibility(...)` line in
[`XaeroBridge.java`](src/oremap/XaeroBridge.java) and build the mod yourself.

**One vein has two markers.**
It lies across a chunk border. Veins are grouped per chunk, so that unloading a chunk
never leaves a marker behind.

**I mined part of a vein and the number in the name did not change.**
The marker is removed when the lowest block of the vein is gone; the block count is
refreshed only when the chunk is scanned again.

**Can it mark iron, gold, emeralds…?**
Not as downloaded. The list of blocks is one short method, `targetOf` in
[`OreMap.java`](src/oremap/OreMap.java) — change it and build the mod yourself.

**We play over a virtual LAN (Hamachi, Radmin VPN, Tailscale…) and it says NOT ALLOWED.**
Those tools hand out addresses outside the private ranges (`25.x.x.x`, `26.x.x.x`,
`100.x.x.x`), so the gate treats them as public. The player who hosts the world still
gets the markers — for them it is a single-player world.

**My home server runs Paper and the markers are wrong.**
Server software with an anti-X-ray feature hides or fakes ore in the data it sends to
every client. The mod can only show what your game received. Vanilla and Fabric servers
send the real blocks.

**Does it work with JourneyMap, VoxelMap or another map mod?**
No, only with Xaero's. Xaero's Better PVP, which bundles the same minimap, has not been
tried.

**Does it slow the game down?**
While off it costs nothing. While on, a chunk takes 14–50 microseconds to scan
(measured on a real world) and at most 16 chunks are scanned per tick, so entering a
world at render distance 32 does not turn into thousands of scans in a single tick.
Details in [How it works](docs/how-it-works.md#2-the-scanner).

## Status

Honestly, what has been checked and how:

**Verified in game** — 2026-09-06, an early build of version 0.2.0, a single-player
world, Minecraft 26.2, Xaero's Minimap 26.4.2 and World Map 1.45.0:

- the markers appear on Xaero's World Map;
- they do not appear on the minimap — confirmed as the wanted behaviour.

In that build the markers were on from the start. **Everything added later has not been
verified step by step:** off by default (later 0.2.0), the `/oremap` command and the `K`
key instead of `O` (0.3.0), the depth in the marker name (0.5.0). Version 0.5.0 has been
switched on in single-player worlds since then, and the game log shows the switch and no
error from the Xaero link — but nobody sat down and ticked these features off one by one.

**Never tested in game:**

- a mined-out vein disappearing from the map;
- ancient debris markers in the Nether;
- joining a LAN server from a second computer — the part of the gate that lets local
  addresses and machine names through;
- staying silent on a public server — covered only by the self-test of the address rules;
- starting the game without Xaero's mods installed;
- the released jar itself: the builds that were played have the same code, but their chat
  messages and marker names were in Russian. The English texts have only been compiled
  and self-tested.

**Checked automatically on every build**, and any failure stops the build:

- the sources compile against the real Minecraft 26.2 client jar;
- every Minecraft and Xaero class the mod refers to exists in the installed game and
  minimap (22 and 14 classes);
- a self-test of the pure logic: 22 address cases for the gate, including the traps
  `192.168.0.10.evil.com` and `localhost.example.com` and the edges of `172.16.0.0/12`;
  vein grouping; marker names;
- `fabric.mod.json` is parsed by Fabric Loader's own parser with zero warnings.

If you try one of the untested items, an issue with the result — either way — is
genuinely useful.

## Building from source

There is no Gradle and no Loom here, and that is not a shortcut: Minecraft 26.x ships
**unobfuscated**, so there is nothing to remap, and plain `javac` is enough. The build
compiles against the game you have installed; nothing is downloaded.

You need Python 3.8 or newer and an installed Minecraft 26.2 with Fabric Loader, Fabric
API and Xaero's Minimap. The JDK is taken from the game's own Java 25 runtime (it ships
`javac`); if it is not found, from `JAVA_HOME`, then from `PATH` — that one has to be
JDK 25 or newer.

Tell the build where the game is. It needs the **profile folder**: a folder that contains
the client jar named after the folder (`<name>/<name>.jar`) and a `mods` folder with
Fabric API and Xaero's Minimap. Launchers that keep every profile in its own folder
under `versions/<name>` already have exactly that. Either set an environment variable:

```
set MC_PROFILE_DIR=<game folder>\versions\<name>
python build.py build
```

(on Linux and macOS: `export MC_PROFILE_DIR=...`)

or create a file `build_local.py` next to `build.py` (it is ignored by git):

```python
PROFILE_DIR = r"<game folder>\versions\<name>"
```

With the official launcher those pieces live in different places, so make such a folder
by hand: create `26.2\`, copy `versions\26.2\26.2.jar` into it, add a `mods` folder with
the Fabric API and Xaero's Minimap jars, and point `MC_PROFILE_DIR` at it.

If the game is not in `%APPDATA%\.minecraft`, also set `MC_GAME_DIR` (or `GAME_DIR` in
`build_local.py`): the game libraries and the Java runtime are taken from there.

| Command | What it does |
|---|---|
| `python build.py build` | compiles, runs every check listed under [Status](#status), writes `build/oremap-<version>.jar` |
| `python build.py install` | builds, then copies the jar into `<profile>/mods`, removing older `oremap-*.jar`. Close the game first |
| `python build.py uninstall` | removes `oremap-*.jar` from `<profile>/mods` |

For another Minecraft version: change the range in
[`resources/fabric.mod.json`](resources/fabric.mod.json) and run the build — the reference
check lists every class that moved. See
[Porting](docs/how-it-works.md#8-porting-to-a-new-minecraft-or-xaero-version).

## Author

Made by **[bombuilder.by](https://bombuilder.by)**.

Works, or does not? Either way, open an
[issue](https://github.com/svareyko/game-fixes/issues) — reports about new versions of
Xaero's mods are what keeps this mod alive. Attach `logs/latest.log` and the output of
`/oremap status`.

## License

[MIT](../../LICENSE).

## Disclaimer

NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.

Minecraft is a trademark of Mojang Synergies AB. Xaero's Minimap and Xaero's World Map
are separate products by their own author; this mod is not affiliated with or endorsed
by them, and they are not included. This repository contains no game code and no code
from Xaero's mods. Provided as-is, without warranty.
