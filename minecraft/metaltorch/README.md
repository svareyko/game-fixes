# Metal Torches — iron and gold torches for Minecraft 26.2 (Fabric)

**Adds two torches with a metal core.** The iron torch burns almost white, the gold torch
a warm yellow. Both give **light level 15** against 14 of the vanilla torch — the
brightest a block can be in Minecraft.

*Minecraft 26.2 · Fabric mod · iron torch · gold torch · brighter torch · light level 15 ·
white torch · yellow torch · a torch that lights one block further*

[Русская версия](README.ru.md) · [How it works](docs/how-it-works.md) ·
[Other mods in this repository](../README.md)

> ## Read this first: the light itself is not coloured
>
> Light in Minecraft has **no colour**. A block has a brightness from 0 to 15 and
> nothing else. A gold torch does not fill the room with yellow light: what is tinted
> is the torch itself and the sparks above it. The light around it is the same neutral
> light every torch gives. Coloured lighting is a job for shaders, not for a block mod.

---

## What the mod adds

| Torch | Flame and sparks | Light level | Recipe |
|---|---|---|---|
| **Iron Torch** | almost white, with a barely noticeable cold tint | 15 | 4 torches + 1 iron ingot → 4 iron torches |
| **Gold Torch** | warm yellow | 15 | 4 torches + 1 gold ingot → 4 gold torches |

Everything else is what you already know from the vanilla torch, because the behaviour
is inherited from it:

* one item for the floor and for the wall — the game picks the variant by where you click;
* breaks instantly, by hand or with any tool, and drops itself;
* smokes like a normal torch; on top of the smoke it throws small sparks of its own colour;
* sits in the creative inventory on the **Functional Blocks** tab, at the very end.

In game the items are called *Iron Torch* and *Gold Torch*. A Russian translation is
included and switches on together with the game language.

## Recipes

Both recipes are **shapeless**: put the five items into a crafting table in any
arrangement. The 2×2 grid of the inventory is too small — five items need the table.

```
4 × Torch  +  1 × Iron Ingot   →   4 × Iron Torch
4 × Torch  +  1 × Gold Ingot   →   4 × Gold Torch
```

Four torches per ingot on purpose: one ingot for a single torch would be ruinous.
Only the ordinary torch is accepted as the base, not the soul torch and not the copper torch.

The recipes appear in the **recipe book** as soon as the matching ingot lands in your
inventory — the same way the game unlocks its own recipes.

## Light levels

| Block | Light level |
|---|---|
| Soul torch | 10 |
| Torch | 14 |
| Copper torch (vanilla, new in 26.2) | 14 |
| **Iron Torch, Gold Torch** | **15** |
| Lantern, glowstone | 15 |

The vanilla numbers were read out of Minecraft 26.2 itself, not from a wiki.

**15 is the ceiling of the engine — nothing can be brighter.** Light loses one level
per block of distance, so a metal torch reaches exactly **one block further** than a
vanilla torch. Hostile mobs spawn only in complete darkness (block light 0), so the
area a torch keeps safe grows by that one block in every direction too. It is one
level, not "twice as bright", and no mod can promise more.

## Why there is no copper torch

Deliberately. Minecraft 26.2 already has a vanilla `minecraft:copper_torch` (a copper
nugget over coal or charcoal over a stick, light level 14). A copper torch from this mod
would put **two items called "Copper Torch"** into the recipe book and the creative
inventory, one light level apart. Copper is left to the vanilla game.

## Supported game versions

| Minecraft | Status |
|---|---|
| **26.2** | supported — built against it and verified in game |
| anything else | not supported. The mod declares `"minecraft": ">=26.2 <26.3"`, and Fabric refuses to start with it on another version instead of crashing later |

The mod is compiled directly against the classes of 26.2, so a build for another version
means recompiling — see [Building from source](#building-from-source).

## What you need

| | Version | Where to get it |
|---|---|---|
| Minecraft: Java Edition | 26.2 | your launcher |
| Fabric Loader | 0.19.0 or newer | [fabricmc.net/use/installer](https://fabricmc.net/use/installer/) |
| **Fabric API** | any build for 26.2 | [modrinth.com/mod/fabric-api](https://modrinth.com/mod/fabric-api) |
| Java | 25 or newer | comes with the game, nothing to install |

Verified with Fabric Loader 0.19.3 and Fabric API 0.157.0+26.2.

Fabric API is **not optional**: the mod uses it to put the torches into the creative
inventory, and Fabric will not start the game without it.

## Single player, LAN and servers

The mod adds blocks and items, so it is needed on **both sides**
(`"environment": "*"` in `fabric.mod.json`):

| How you play | Who needs the mod |
|---|---|
| Single player | you |
| "Open to LAN" | you and everyone who joins |
| Dedicated Fabric server | the server and every player |

A game without the mod does not know what `metaltorch:iron_torch` is, so everybody who
enters a world with these torches needs the same jar. Multiplayer was not tested
separately — see [Status](#status).

## Install

**1. Install Fabric for Minecraft 26.2**, if you do not have it yet. Download the
installer from [fabricmc.net/use/installer](https://fabricmc.net/use/installer/), run it,
choose Minecraft version **26.2**, press **Install**. A new Fabric profile appears in the
launcher.

**2. Download Fabric API** for 26.2 from
[modrinth.com/mod/fabric-api](https://modrinth.com/mod/fabric-api). It is a `.jar` file;
do not unpack it.

**3. Download `metaltorch-1.1.0.jar`** from the release page:
<https://github.com/svareyko/game-fixes/releases/tag/metaltorch-1.1.0>

**4. Open the `mods` folder.** Press `Win + R`, paste the line below and press Enter:

```
%APPDATA%\.minecraft\mods
```

If Windows says the folder does not exist, open `%APPDATA%\.minecraft` instead and
create a folder named `mods` there. (Linux: `~/.minecraft/mods`. macOS:
`~/Library/Application Support/minecraft/mods`.)

> Some launchers keep a separate `mods` folder for every profile. If yours has a button
> like "Open mods folder", use it — that is the folder the game really reads.

**5. Put both jars into `mods`**: `fabric-api-….jar` and `metaltorch-1.1.0.jar`.

**6. Close the game if it was running, then start it with the Fabric profile.**

That is it. Nothing to configure.

## How to check that it loaded

Any one of these is enough:

* **Creative inventory** → tab **Functional Blocks** → scroll to the end: *Iron Torch* and
  *Gold Torch* are the last two items. Or type `torch` into the search tab.
* **Survival**: pick up an iron ingot, open a crafting table, open the recipe book and
  search for `torch` — the *Iron Torch* recipe is there.
* **With cheats on**: `/give @s metaltorch:iron_torch` hands you one.
* **The log**: open `logs\latest.log` in the game folder. Near the top Fabric lists what
  it loaded, and the list has to contain this line:

```
	- metaltorch 1.1.0
```

If the game shows a Fabric window instead of starting, read it — it names the problem
in plain words. The two usual ones: *"requires fabric-api"* (step 2 was skipped) and
*"requires minecraft 26.2"* (the profile runs another game version).

## Uninstall

Close the game and delete `metaltorch-1.1.0.jar` from the `mods` folder. No other file
was created anywhere: the mod has no config and writes nothing to disk.

**What happens to torches you already placed.** A game without the mod no longer knows
these blocks and items. When you open the world, placed iron and gold torches
**disappear**, and the ones lying in inventories and chests are removed. The rest of the
world is untouched. Once the game saves those chunks, putting the mod back does not
bring the torches back.

So, before you remove the mod from a world you care about:

1. replace the metal torches with ordinary ones where the light matters — dark spots
   are where monsters spawn;
2. make a copy of the world folder (`saves\<world name>`).

**The same thing happens without uninstalling**, if you open the world with a profile
that does not have the mod — a vanilla profile, or another mods folder. A backup of the
world is the only undo.

This is how Minecraft treats the content of any removed mod. It was not tested
separately for this one — see [Status](#status).

## FAQ

**Why is the light not coloured? I expected yellow light from the gold torch.**
Because Minecraft cannot do it. The lighting engine stores one number per block, the
brightness from 0 to 15, and no colour at all. The mod tints what can be tinted: the
flame on the torch and the sparks above it. Real coloured lighting exists only in shader
packs.

**Is it much brighter than a normal torch?**
By one level: 15 instead of 14. The light reaches one block further. That is the maximum
the game allows — the same level as a lantern or glowstone.

**Does it keep monsters away better?**
A little. Monsters spawn where block light is 0, and a metal torch pushes that border
one block further out. Your torch grid can be slightly wider, no more than that.

**Where is the copper torch?**
In the vanilla game — see [Why there is no copper torch](#why-there-is-no-copper-torch).

**The recipe is not in my recipe book.**
The game unlocks a recipe when its key ingredient enters your inventory: an iron ingot
for the iron torch, a gold ingot for the gold one. If you already carried ingots when you
installed the mod, drop one and pick it up again. The recipe itself works even before it
is unlocked — put the five items into the crafting table by hand.

**Will it work on 1.21, 26.1 or 26.3?**
No. It is built against 26.2 and says so in its metadata; Fabric will refuse to load it
elsewhere. Another version needs a rebuild.

**Forge, NeoForge, Quilt?**
Fabric only. Forge and NeoForge will not load it. Quilt was not tried.

**Will it get along with my other mods and with shaders?**
It should: the torches use the vanilla torch models and vanilla particles, and the mod
changes nothing in the game's own code (no mixins). Only a modest set of other mods was
running next to it during testing, so if you find a conflict, please open an issue.

**Does it touch my world or my settings?**
Only by what you place yourself. No world generation, no config file, no network traffic.

## Status

Honestly, what is known and what is not.

**Verified in game on 2026-09-20** — version 1.1.0, Minecraft 26.2, Fabric Loader 0.19.3,
Fabric API 0.157.0+26.2:

* both recipes are visible in the recipe book;
* a torch placed on a wall breaks and drops as an item.

**Verified by every build**, without starting the game:

* every Minecraft class the mod refers to exists in the 26.2 client;
* the rule that gives the wall torch its drops holds on the live vanilla blocks;
* all ten resource files of every metal are in the jar and every JSON parses;
* `fabric.mod.json` passes Fabric Loader's own parser without a warning.

**About the published jar.** The 1.1.0 build that was played is not byte-for-byte the jar
on the release page. For publication three files inside it changed: `fabric.mod.json`
(English description, author, licence, links) and the two language files (a description
line for Mod Menu). The compiled classes and every other resource are byte-identical to
the verified build — this was compared entry by entry.

**Not verified:**

* multiplayer — a LAN world or a dedicated server;
* removing the mod from a world with placed torches (described above as the game's
  general behaviour);
* pistons: the vanilla torch is declared "destroyed when pushed", this mod does not set
  that flag, so a piston may treat a metal torch differently from a vanilla one;
* Quilt, and long-term play in general.

If something does not work for you, open an issue and attach `logs\latest.log`.

## Building from source

You do not need this to play — the jar on the release page is ready. This is for people
who want to change the mod or rebuild it for another game version.

There is **no Gradle and no Loom**. Minecraft 26.x ships unobfuscated, so there is
nothing to remap: plain `javac` against the installed game is enough, and the build needs
no network. The reasoning is in [docs/how-it-works.md](docs/how-it-works.md#9-building-with-plain-javac).

You need:

* **Python 3.8+**;
* **a JDK 25**. The script looks into the game's own runtime folder first, then
  `JAVA_HOME`, then `PATH`;
* **Minecraft 26.2 with Fabric installed and started at least once**, with Fabric API in
  its `mods` folder;
* Pillow (`python -m pip install pillow`) — only if you regenerate the textures.

Tell the script where the game is. It builds against one **profile folder** — the folder
of one game installation that contains `<name>.jar` (the client), `<name>.json` (the
version manifest with every library the game starts with) and `mods/`:

```
:: cmd
set MC_PROFILE_DIR=%APPDATA%\.minecraft\versions\<name>
python build.py build

# PowerShell
$env:MC_PROFILE_DIR = "$env:APPDATA\.minecraft\versions\<name>"
python build.py build
```

| Setting | Meaning | Default |
|---|---|---|
| `MC_PROFILE_DIR` | the profile folder described above | none — the script stops and explains |
| `MC_GAME_DIR` | the game directory; `libraries/` and `runtime/` are taken from it | `%APPDATA%\.minecraft` |
| `build_local.py` | optional file next to `build.py` that sets `PROFILE_DIR = ...` and/or `GAME_DIR = ...` once, instead of the variables. Ignored by git | — |

If both are given: `MC_PROFILE_DIR` wins over `PROFILE_DIR`, and `GAME_DIR` wins over
`MC_GAME_DIR`.

| Command | What it does |
|---|---|
| `python build.py build` | compiles, runs every check, writes `build/metaltorch-<version>.jar` |
| `python build.py install` | the same, then copies the jar into the profile's `mods/`, replacing older versions of this mod. Close the game first |
| `python build.py uninstall` | removes the mod's jar from the profile's `mods/` |
| `python tools/resources.py write` | regenerates textures, models, recipes, loot tables and language files |
| `python tools/resources.py preview` | draws the textures enlarged into `build/torches.png` |

**A limitation you should know.** The script expects a self-contained profile: one
manifest that lists *all* libraries, with the client jar and `mods/` next to it. Some
launchers lay out an installation exactly like that. The official launcher does not — its
Fabric profile inherits the libraries from the vanilla version folder and keeps `mods/`
in the game directory — and the script was not adapted to that layout or tested with it.

## Author

Made by **[bombuilder.by](https://bombuilder.by)**.

Works, or does not? Either way, [open an issue](https://github.com/svareyko/game-fixes/issues) —
reports from other setups are what the "not verified" list above is waiting for.

## License

[MIT](../../LICENSE). Do what you like with the code and the textures; keep the copyright
notice.

## Disclaimer

**NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.**

Minecraft is a trademark of Mojang AB; all trademarks belong to their owners. Fabric is a
project of its own contributors, and this mod is not affiliated with it either. The
repository contains no game
code and no game assets: the textures are drawn by the mod's own generator, the models
only refer to the vanilla torch templates by name, and the mod is compiled against the
copy of the game installed on your own computer. Provided as-is, without warranty.
