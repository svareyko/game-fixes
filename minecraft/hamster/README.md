# Hamsters — a Fabric mod for Minecraft 26.2

**Adds hamsters to Minecraft.** Tame them with seeds, breed them, carry one in your
pocket, throw it at a creeper, and build a hamster wheel that drives redstone.

*Minecraft 26.2 · Fabric · hamster mod · tameable pet · pet in the inventory · hamster
wheel · comparator signal · kills creepers · zombies and skeletons run away*

[Русская версия](README.ru.md) · [How it works](docs/how-it-works.md) ·
[Other mods in this repository](../README.md)

---

## What the mod adds

- **A hamster** — a small tameable animal, a quarter of a block in size, in **five
  colours**: golden, grey, white, panda and black. Three hearts of health.
- **Where they live:** Plains, Sunflower Plains and Meadows, in groups of 2–4.
- **A pet that does things:** follows you, sits on command, breeds, fits into your
  inventory and can be thrown.
- **A creeper remedy:** a thrown hamster kills a creeper outright — and lands unharmed.
- **A scarecrow:** zombies and skeletons are afraid of hamsters and run away from them.
- **A hamster wheel** — a block hamsters run in by themselves. While one is running,
  a comparator next to the wheel gives a full redstone signal.
- A **Hamster Spawn Egg** for Creative mode.

Everything is in the game language: English and Russian are included.

### How to play with a hamster

| You want to | Do this |
|---|---|
| **Tame** | Hold any seeds and right-click a wild hamster. Every seed has a 1 in 3 chance: hearts mean success, smoke means try again. A freshly tamed hamster sits down |
| **Make it sit / follow** | Right-click your hamster with an empty hand |
| **Heal** | Feed seeds to your hurt hamster: +1 heart per seed |
| **Breed** | Feed seeds to two tamed, healthy hamsters. The baby takes the colour of one parent and is born tame |
| **Pick up into the inventory** | **Sneak** and right-click **your own tamed** hamster with an **empty hand** |
| **Put it back** | Hold the hamster and right-click **a block** — it appears there, awake and yours |
| **Throw** | Hold the hamster and right-click **without aiming at a block** — into the air or at a mob |

"Any seeds" means Wheat Seeds, Melon Seeds, Pumpkin Seeds, Beetroot Seeds, Torchflower
Seeds and Pitcher Pods — the same things chickens eat.

If the pick-up gesture is refused, the game says why in the line above the hotbar:
*"Tame the hamster with seeds first"* or *"This hamster is not yours"*.

### Throwing, and creepers

A thrown hamster flies like a snowball. **Wherever it lands — on a creeper, on another
mob, on the ground — the hamster appears at that spot alive, unharmed and tamed by
whoever threw it.** The throw itself never hurts the pet; just mind what is at the
landing spot, see the [FAQ](#faq).

If it hits a **creeper**, the creeper dies. It counts as your own kill: gunpowder and
experience drop as usual, and the creeper does **not** explode. No other creature takes
any damage from a hamster.

### Zombies and skeletons

Zombies and skeletons within 8 blocks of **any** hamster — wild or tamed — stop what
they are doing and run away. The same goes for their relatives: husks, drowned, zombie
villagers, zombified piglins, strays, wither skeletons, bogged and parched. Further
away than 8 blocks monsters behave as always.

### The hamster wheel

Crafting — eight Sticks around one Iron Nugget, gives one wheel:

```
Stick   Stick        Stick
Stick   Iron Nugget  Stick
Stick   Stick        Stick
```

| | |
|---|---|
| How it works | A hamster finds a free wheel within 8 blocks by itself, climbs in and runs for 20 seconds. Wild hamsters do it too |
| Redstone | While a hamster is running, a **Redstone Comparator** reading the wheel outputs signal strength **15**; an empty wheel gives 0 |
| Afterwards | The hamster gets out and ignores wheels for about a minute, so that one hamster does not occupy a wheel forever |
| Who will not use it | Babies, hamsters told to sit, and hamsters that are swimming |
| One at a time | One wheel holds one hamster |

In Creative mode the wheel is in the **Functional Blocks** tab, the spawn egg and the
hamster item are in **Spawn Eggs**.

## What you need

| | |
|---|---|
| Minecraft | **Java Edition 26.2** (any 26.2.x). Other versions are not supported — the mod refuses to load on them |
| Mod loader | **Fabric Loader 0.19.0 or newer** |
| Library mod | **Fabric API** for 26.2 |
| Java | 25 — the launcher installs it together with Minecraft 26.2, nothing to do |

**Client or server? Both.** The mod adds new animals, items and a block, so every side
of the game has to know them:

- **Single player** — install it on your PC, that is all.
- **Multiplayer** — the server **and every player** need the mod. The same goes for
  "Open to LAN": the host and everyone who joins.

## Install

**1. Install Fabric Loader for Minecraft 26.2.** Download the installer from
[fabricmc.net/use/installer](https://fabricmc.net/use/installer/), run it, choose
Minecraft version **26.2**, press *Install*. A new Fabric profile appears in the
launcher. If your launcher can create a Fabric 26.2 profile by itself, that is the
same thing.

**2. Download Fabric API.** Get the file for game version 26.2 from
[modrinth.com/mod/fabric-api](https://modrinth.com/mod/fabric-api).

**3. Download the mod.** Get **`hamster-0.5.0.jar`** from the
[release page](https://github.com/svareyko/game-fixes/releases/tag/hamster-0.5.0).

**4. Put both `.jar` files into the `mods` folder of the game directory.** Do not unzip
them. With the official launcher the folder is:

| System | Folder |
|---|---|
| Windows | `%APPDATA%\.minecraft\mods` — press `Win + R`, paste this line, press Enter |
| macOS | `~/Library/Application Support/minecraft/mods` |
| Linux | `~/.minecraft/mods` |

If there is no `mods` folder yet, create it. Some launchers keep a separate game
directory for every profile — then open the directory of your Fabric profile from the
launcher and use the `mods` folder inside it.

**5. Close the game if it was open, and start it with the Fabric profile.**

### How to check that it loaded

Any one of these is enough:

- Open a Creative world, open the inventory, go to the search tab and type `hamster`.
  You should see three items: **Hamster Spawn Egg**, **Hamster** and **Hamster Wheel**.
- In a world with cheats enabled run `/summon hamster:hamster` — a hamster appears.
- Open `logs/latest.log` in the game directory. Near the top, in the list that starts
  with `Loading ... mods:`, there is the line `- hamster 0.5.0`.
- If you use [Mod Menu](https://modrinth.com/mod/modmenu), the mod list in the main
  menu shows **Hamsters**.

If the game stops at start with the window *Incompatible mods found!* and asks you to
install `fabric-api`, step 2 was skipped or the file is for another game version.

### Will hamsters appear in a world I already have?

**Yes, there is no need to create a new world.** But not everywhere at once:

| Where | When |
|---|---|
| Chunks nobody has visited yet | Right away, when the terrain is generated |
| Places already explored | Gradually. The game tries to spawn animals only once every 20 seconds, and all animals share one small limit — where cows and sheep already fill it, there is no room for newcomers |
| Right now | Use the spawn egg in Creative mode |

The fastest way to meet wild hamsters is to walk into plains or meadows you have not
been to. Around a built-up base it is easier to bring a pair and breed them.

## Uninstall

Close the game and delete `hamster-0.5.0.jar` from the `mods` folder. Fabric API can
stay, other mods use it too.

**Think about your world first.** Hamsters, hamster wheels and hamsters carried in an
inventory belong to the mod. Without the mod the game does not know what they are and
drops them as it loads those places — and they do not come back if you install the
mod again later. If you may want them back, make a copy of the world before you start
the game without the mod: *Singleplayer → select the world → Edit → Make Backup*.

Nothing else is touched: the mod changes no vanilla blocks, items or world generation,
and zombies and skeletons simply stop caring about hamsters that no longer exist.

## Things that stop the mod from working

- **A game update.** The mod is built for 26.2 only. On 26.3 or newer Fabric Loader
  refuses to start the game, shows *Incompatible mods found!* and names this mod.
  Remove the jar or look for a newer release here.
- **Starting the game with a non-Fabric profile.** The vanilla profile ignores the
  `mods` folder entirely. Worlds opened that way lose their hamsters, see *Uninstall*.

When a newer version of the mod comes out, replace the old file: keep only one
`hamster-*.jar` in `mods`.

## FAQ

**Do my friends need the mod too?**
Yes. Everyone who joins a world with hamsters needs it, and so does the server.

**Nothing happens when I sneak and click a hamster.**
Your hand has to be empty, and the hamster has to be tamed by you. Otherwise the game
tells you the reason above the hotbar. Without sneaking the same click makes the
hamster sit — that is why sneaking is required.

**I cannot breed them.**
Both hamsters have to be tamed and at full health. A hurt hamster eats the seed to
heal, a wild one takes it as a taming attempt.

**Will the creeper blow up when the hamster hits it?**
No. It dies on the spot, like from a sword — a creeper explodes only when it ignites.

**Can my hamster die from being thrown?**
Not from the throw: the flight and the hit do no damage to it. But the hamster appears
exactly where it hit, and from then on it is an ordinary animal. Thrown at a high wall
it falls down from there, thrown into lava it stands in lava, and thrown into the void
it never lands at all.

**What does the hamster remember while it is in my pocket?**
Its colour and its name (from a Name Tag). It comes out as a healthy adult that belongs
to whoever let it out. Known flaw: a **thrown** hamster loses its custom name — put a
named hamster down on a block instead.

**The wheel keeps spinning, but there is no hamster in it.**
Break the wheel and place it again. The wheel can be left "occupied" when the hamster
vanished in the middle of a run — for example the area was unloaded because you walked
away or left the game, or the hamster died. This was found by reading the code and has
not been reproduced in game yet.

**In Creative mode the hamster in my hand never runs out.**
Correct — Creative mode does not use items up, so every click makes one more hamster.

**Does it conflict with other mods?**
It should not. The mod uses no mixins and patches no game classes: everything goes
through Fabric API. It replaces no vanilla textures or models.

**Why do hamsters sound like rabbits?**
The mod has no sounds of its own and borrows the rabbit's, played less often.

**Can I put it into a modpack?**
Yes, the [MIT licence](../../LICENSE) allows it.

## Status

Version **0.5.0**, for Minecraft 26.2.

**Verified in game on 2026-09-20:** taming and breeding with seeds, the five colours,
following the owner and sitting on command, picking up into the inventory while
sneaking, throwing, a thrown hamster killing a creeper as a normal kill and landing
unharmed, zombies and skeletons running away, the wheel and its comparator signal.

**Not verified:**

- A dedicated server. The mod is written to run there — all client classes sit behind
  a separate entry point — but nobody has tried it yet.
- The relatives of zombies and skeletons listed above. They are covered because their
  classes inherit from the two that were tested.
- Removing the mod from a world that has hamsters in it. The *Uninstall* section
  describes what Minecraft normally does with content of a missing mod.
- The two known flaws from the FAQ — the wheel that stays "occupied" and the name lost
  by a thrown hamster — come from reading the code and have not been reproduced in game.

The jar on the release page was rebuilt after the in-game test to change its metadata
only: author, licence, links and an English description. Its compiled classes are
byte-for-byte identical to the tested build.

Found a bug, or it works for you on a server? Please
[open an issue](https://github.com/svareyko/game-fixes/issues) either way.

## Building from source

For maintainers; players do not need this.

```
python build.py build        build build/hamster-<version>.jar
python build.py install      build and copy the jar into <profile>/mods (close the game first)
python build.py uninstall    remove hamster-*.jar from <profile>/mods
```

There is no Gradle and no Loom: Minecraft 26.x ships unobfuscated, so plain `javac`
against the files of an installed game is enough — the reasoning is in
[docs/how-it-works.md](docs/how-it-works.md#why-plain-javac-is-enough). You need:

- **Python 3.8 or newer.** Only for the texture tools also `pip install pillow numpy`.
- **An installed Minecraft 26.2 with Fabric Loader and Fabric API**, started at least
  once. Nothing is downloaded, the script compiles against what is on disk.
- **A JDK 25 or newer.** The script looks for `javac` in the Java runtime bundled with
  the game, then in `JAVA_HOME`, then on `PATH`.

Tell the script where the game is:

| Setting | Meaning | Where it comes from, in this order |
|---|---|---|
| profile folder | The folder one Fabric installation runs from. It holds `<name>.jar` (the 26.2 client, named after the folder), `<name>.json` (the version manifest with the complete list of libraries) and `mods/` with Fabric API in it. `install` copies the mod into its `mods/` | environment variable `MC_PROFILE_DIR`, then `PROFILE_DIR` in `build_local.py`. Without either the script stops and explains this |
| game directory | The folder with `libraries/` and `runtime/` | `GAME_DIR` in `build_local.py`, then environment variable `MC_GAME_DIR`, then `%APPDATA%/.minecraft` |

`build_local.py` is an optional file next to `build.py` that is never committed. A
minimal one:

```python
PROFILE_DIR = r"<path to the profile folder>"
```

It may also define `after_mods_changed(mods_dir, mod_id)`, which `install` and
`uninstall` call when they are done — a hook for whatever your launcher needs.

The script has only ever been run against a launcher that keeps each profile in one
self-contained folder like the one described above. The official launcher splits it:
its Fabric version JSON points to the vanilla one through `inheritsFrom`, the client
jar lies in another version folder and `mods/` is in the game directory. `build.py`
does not follow `inheritsFrom` — for that layout it needs work.

The textures are generated by code, not drawn in an editor:

```
python tools/textures.py write      regenerate every PNG under resources/
python tools/textures.py preview    render all colour variants into build/preview.png
```

What the build checks before it hands you a jar, and how the mod is put together:
[docs/how-it-works.md](docs/how-it-works.md).

## Author

Made by **[bombuilder.by](https://bombuilder.by)**.

The model, the textures and the code were made from scratch for this mod; nothing is
taken from other mods.

## License

[MIT](../../LICENSE).

## Disclaimer

NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.

Minecraft is a trademark of Mojang Synergies AB. This project is not affiliated with
the Fabric project either. The repository contains no game code. Provided as-is,
without warranty.
