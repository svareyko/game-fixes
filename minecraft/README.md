# Minecraft mods (Fabric, Minecraft 26.2)

Three small mods, each one written because nothing ready-made existed for Minecraft 26.2.
They are independent: install one or all.

[Русская версия](README.ru.md)

| Mod | What it adds | Where it must be installed | State |
|---|---|---|---|
| [hamster/](hamster/) — **Pocket Hamsters** 0.5.1 | Tameable hamsters in five colours: they follow you, sit on command, can be carried in the inventory and thrown (a thrown hamster finishes a creeper and lands unharmed). Zombies and skeletons keep away from them. Plus a hamster wheel that feeds a comparator | client **and** server | verified in game as 0.5.0 (then called *Hamsters*); the two fixes of 0.5.1 (a wheel frees itself when its hamster is gone, a thrown hamster keeps its name) are not played yet |
| [metaltorch/](metaltorch/) — **Metal Torches** 1.1.1 | An iron torch (almost white flame) and a gold torch (yellow), light level 15 — one more than a vanilla torch, the engine's maximum | client **and** server | verified in game as 1.1.0; the two corrections of 1.1.1 (pistons, spark height on a wall) are not played yet |
| [oremap/](oremap/) — **Ore Map** 0.5.0 | Puts markers for diamond ore and ancient debris, with their depth, on Xaero's World Map. Off until you switch it on. Works only in single player and on LAN / private-network servers — it keeps itself off on public ones | client only; needs **both** Xaero's Minimap and Xaero's World Map | markers on the map were play-tested in an early build; what was added later is self-tested only — see the mod's README |

## What every mod needs

- **Minecraft 26.2** with **[Fabric Loader](https://fabricmc.net/use/installer/) 0.19.0 or newer**
- **[Fabric API](https://modrinth.com/mod/fabric-api)** for 26.2
- Java 25 — the launcher installs it together with the game

## Install

1. Install Fabric for Minecraft 26.2 with the [Fabric installer](https://fabricmc.net/use/installer/)
   and start the game once with the *fabric-loader* profile, then close it.
2. Open the game folder: press **Win + R**, type `%APPDATA%\.minecraft`, press Enter. Inside there
   is a folder called `mods` (create it if it is missing). Some launchers keep a separate game
   folder per profile — their settings show the path.
3. Download the `.jar` of the mod from the [Releases](https://github.com/svareyko/game-fixes/releases)
   page — the file is called like the mod, for example `hamster-0.5.1.jar` — and
   [Fabric API](https://modrinth.com/mod/fabric-api), and put both into `mods`.
4. Start the game. In the main menu the mod list (with [Mod Menu](https://modrinth.com/mod/modmenu)
   installed) shows the mod.

Mods marked *client and server* add new blocks, items or mobs: on a multiplayer server they must
be installed on the server and on every player's computer. *Client only* mods are installed just
on your own computer.

To remove a mod, delete its `.jar` from `mods`. Each mod's README says what then happens to the
things it added to your world.

## Built without Gradle

Minecraft 26.x ships unobfuscated, so the usual toolchain (Loom and mappings) has nothing left to
do. Each mod builds with plain `javac` through its own `build.py`, against the game you already
have installed; every build runs a self-test and a validator. Details are in `docs/how-it-works.md`
of each mod.

## Author and license

Made by **[bombuilder.by](https://bombuilder.by)**. [MIT](../LICENSE). Models and textures were
drawn from scratch for these mods.

**NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.**
Xaero's Minimap and World Map are separate mods by their own author and are not included.
