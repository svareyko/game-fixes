# How Metal Torches works

Design notes for modders: how two small blocks are put together on Minecraft 26.2, and
the places where the game pushed back. Everything about the vanilla game below was read
from the 26.2 client itself — its data files and its disassembly — not from documentation
written for older versions.

*recipe works but is missing from the recipe book · advancement/recipes · recipe_unlocked ·
TorchBlock SimpleParticleType · WallTorchBlock codec · overrideLootTable · wall torch drops
nothing · Fabric mod without Gradle and Loom · Minecraft 26 unobfuscated*

**Read this when:** you want to change the mod, port it to another game version, or borrow
one of the techniques.
**Not this, for:** installing, recipes, light levels, FAQ → [README](../README.md).
**Sections:** [1 The files](#1-the-files) · [2 Two blocks, one item](#2-two-blocks-one-item) ·
[3 Light level 15, and no colour](#3-light-level-15-and-no-colour) ·
[4 Tinted sparks](#4-tinted-sparks) · [5 The codec wrinkle](#5-the-codec-wrinkle) ·
[6 The wall torch and its drops](#6-the-wall-torch-and-its-drops) ·
[7 The recipe that was missing from the recipe book](#7-the-recipe-that-was-missing-from-the-recipe-book) ·
[8 Resources are generated](#8-resources-are-generated) ·
[9 Building with plain javac](#9-building-with-plain-javac) ·
[10 What the build verifies](#10-what-the-build-verifies) ·
[11 Differences from the vanilla torch](#11-differences-from-the-vanilla-torch) ·
[12 Adding a metal](#12-adding-a-metal) ·
[13 Porting to another Minecraft version](#13-porting-to-another-minecraft-version)

[Русская версия](how-it-works.ru.md)

## 1. The files

| File | Job |
|---|---|
| `src/metaltorch/MetalTorch.java` | the enum of metals: id, colour, recipe ingredient |
| `src/metaltorch/MetalTorchBlock.java` | the standing torch |
| `src/metaltorch/MetalWallTorchBlock.java` | the wall torch |
| `src/metaltorch/MetalTorchMod.java` | registers blocks and items, fills the creative tab. Entry point `main` |
| `resources/fabric.mod.json` | the mod manifest, written by hand |
| `resources/assets`, `resources/data` | written by the generator, never by hand |
| `tools/resources.py` | generator: textures, models, blockstates, loot tables, recipes, unlock advancements, language files |
| `tools/SelfTest.java` | build-time check of the loot table rule on live vanilla blocks |
| `tools/ValidateMod.java` | build-time check of `fabric.mod.json` by Fabric Loader's own parser |
| `build.py` | the build: classpath, `javac`, checks, jar |

Four classes, no mixins, no access wideners, no config.

## 2. Two blocks, one item

A torch in Minecraft is **two blocks**: the standing one and the wall one, which has a
`facing` property and a tilted model. The mod repeats that for every metal and registers
a single item for the pair:

```java
Block standing = Registry.register(BuiltInRegistries.BLOCK, standingKey,
        new MetalTorchBlock(metal.colour(), torchProperties().setId(standingKey)));
Block wall = Registry.register(BuiltInRegistries.BLOCK, wallKey,
        new MetalWallTorchBlock(metal.colour(),
                torchProperties().overrideLootTable(standing.getLootTable()).setId(wallKey)));

Item item = Registry.register(BuiltInRegistries.ITEM, itemKey,
        new StandingAndWallBlockItem(standing, wall, Direction.DOWN,
                new Item.Properties().useBlockDescriptionPrefix().setId(itemKey)));
```

* `StandingAndWallBlockItem` is the vanilla class behind the torch item. It decides which
  of the two blocks to place from the face the player clicked; `Direction.DOWN` says the
  standing variant is supported from below.
* `useBlockDescriptionPrefix()` makes the item take its name from the block's translation
  key, so the language files carry `block.metaltorch.*` keys only.
* Both classes extend the vanilla `TorchBlock` / `WallTorchBlock`. What a torch can stand
  on, when it pops off and how it is placed all lives in the vanilla parents and is not
  rewritten.
* Registration runs in a static initialiser of the entry point class, so it happens when
  Fabric loads the mod — before the registries freeze. `onInitialize()` only adds the
  items to the vanilla **Functional Blocks** tab through Fabric API
  (`CreativeModeTabEvents.modifyOutputEvent`). That call is the reason Fabric API is a
  dependency.

The order of the enum values may change freely: block names leave the mod, ordinals
do not.

## 3. Light level 15, and no colour

```java
BlockBehaviour.Properties.of().noCollision().instabreak().lightLevel(state -> 15).sound(SoundType.WOOD)
```

The engine stores light as one small number per block position, 0..15. There is no
channel for a colour, so a block can only be *brighter*, never *yellow*. The vanilla torch
is 14, and 15 is the top of the scale — the mod has nowhere further to go. The table of
levels, read from the live game, is in the [README](../README.md#light-levels).

The colour of a metal (`0xF0F4F8` iron, `0xFFD24A` gold) therefore goes into the only two
places that can show it: the texture and the particles.

## 4. Tinted sparks

The obvious plan — hand the torch a coloured flame particle — does not compile. Both
vanilla constructors insist on a particle type *without parameters*:

```
protected TorchBlock(SimpleParticleType, BlockBehaviour.Properties)
protected WallTorchBlock(SimpleParticleType, BlockBehaviour.Properties)
```

A coloured particle is a `DustParticleOptions` — a particle *with* parameters, not a
`SimpleParticleType`. So the mod passes the vanilla `ParticleTypes.FLAME` to satisfy the
constructor and then overrides `animateTick` completely, so that particle is never used:

```java
level.addParticle(ParticleTypes.SMOKE, x, y, z, 0.0, 0.0, 0.0);
DustParticleOptions spark = new DustParticleOptions(colour, 0.7F);   // packed RGB, scale
for (int i = 0; i < 2; i++) {
    level.addParticle(spark,
            x + (random.nextDouble() - 0.5) * 0.12,
            y + random.nextDouble() * 0.12,
            z + (random.nextDouble() - 0.5) * 0.12,
            0.0, 0.0, 0.0);
}
```

Smoke as on an ordinary torch, plus two dust sparks per animation tick — one looks poor,
three already flicker too much. There is **no vanilla flame particle** at all: the "flame"
you see is the bright top of the texture plus the sparks.

Where the particles appear:

| Variant | Position |
|---|---|
| standing | block centre, `y + 0.7` — the vanilla values |
| wall | `y + 0.7 + 0.22`, and 0.27 from the block centre towards the wall (`FACING.getOpposite()`) — the vanilla values, because the model is the vanilla `template_torch_wall`. Up to 1.1.0 the `+ 0.22` was missing and the sparks started below the tip |

`emit(...)` is a static method shared by both block classes; the wall class only computes
a different position.

## 5. The codec wrinkle

Every block class in 26.2 has to return its `MapCodec`. The two vanilla parents declare
that method differently:

```
TorchBlock:      public MapCodec<? extends TorchBlock> codec()
WallTorchBlock:  public MapCodec<WallTorchBlock>       codec()     // invariant
```

With `? extends` the subclass may narrow the return type to `MapCodec<MetalTorchBlock>`.
With the invariant declaration it may not — the compiler rejects it. That is why two
almost identical classes differ here: `MetalWallTorchBlock.CODEC` is typed by the
**parent** (`MapCodec<WallTorchBlock>`), and its getter and constructor lambda carry casts.

Both codecs store the colour next to the block properties (`Codec.INT.fieldOf("colour")`),
so an instance can be rebuilt from data.

## 6. The wall torch and its drops

The most dangerous spot in the mod: get it wrong and a torch broken off a wall drops
**nothing** — no crash and no hint of the reason.

The wall torch has **no loot table file of its own**. It points at the table of the
standing torch. Vanilla does exactly the same. The client jar contains
`data/minecraft/loot_table/blocks/torch.json` and no `wall_torch.json`, and the
disassembly of `net.minecraft.world.level.block.Blocks` shows how the game builds its own
wall blocks: a private helper `wallVariant(base, copyName)` starts the properties with
`overrideLootTable(base.getLootTable())` and, when asked to, also copies the name with
`overrideDescription(base.getDescriptionId())`.

The mod does the first half by hand: `overrideLootTable(standing.getLootTable())`.
It does not copy the name — the wall block has its own language key instead.

Where does the standing torch's table come from? `Properties.setId(key)` sets **only the
id**; the loot table key is derived from it as `<namespace>:blocks/<block id>`. That puts
the files here:

```
data/metaltorch/loot_table/blocks/iron_torch.json
data/metaltorch/loot_table/blocks/gold_torch.json
```

This rule was not taken from reading bytecode and hoping. **Every build checks it on the
live vanilla blocks**: `tools/SelfTest.java` boots the game's registries
(`SharedConstants.tryDetectVersion()` + `Bootstrap.bootStrap()`, no window, no OpenGL),
asks the real `Blocks.TORCH` and `Blocks.WALL_TORCH` for their loot table keys and prints:

```
ok   the vanilla torch has a loot table
vanilla torch      -> minecraft:blocks/torch
vanilla wall torch -> minecraft:blocks/torch          <- the same key
ok   the key is derived as <namespace>:blocks/<block id>
ok   the wall torch points at the table of the standing torch - the scheme this mod repeats
```

If a game update changes the rule, the build fails instead of the torches silently
dropping nothing. The build also refuses a stray `*_wall_torch.json` loot table: that file
would mean somebody "fixed" the scheme without understanding it.

The self-test never touches the mod's own classes — loading `MetalTorchMod` would try to
register blocks into registries that are already frozen.

## 7. The recipe that was missing from the recipe book

**Symptom.** The first version of the mod shipped a recipe file and nothing else. The recipe loaded and
**worked** — lay the items out in the grid by hand and the torches came out. But the
recipe book never showed it. The log was completely clean: no error, no warning, the
data pack loaded, and the `Loaded N recipes` line had even grown by the number of new
recipes.

**Cause.** The recipe book lists only **unlocked** recipes, and a recipe is unlocked by a
separate *advancement* file. Vanilla ships one for every recipe it has; the torch's own is
`data/minecraft/advancement/recipes/decorations/torch.json`.

**Fix.** One advancement per recipe under `data/<namespace>/advancement/recipes/`:

```json
{
  "parent": "minecraft:recipes/root",
  "criteria": {
    "has_ingredient": {
      "trigger": "minecraft:inventory_changed",
      "conditions": { "items": [ { "items": "minecraft:iron_ingot" } ] }
    },
    "has_the_recipe": {
      "trigger": "minecraft:recipe_unlocked",
      "conditions": { "recipe": "metaltorch:iron_torch" }
    }
  },
  "requirements": [ [ "has_the_recipe", "has_ingredient" ] ],
  "rewards": { "recipes": [ "metaltorch:iron_torch" ] }
}
```

Either criterion is enough (one inner list = OR): the player picked up the key ingredient,
or already has the recipe. The reward unlocks it. The `decorations` sub-folder mirrors
where vanilla keeps its torch; it is a convention.

**How to tell next time.** Compare `Loaded N recipes` in the log with a run without the
mod. If it grew, the recipes parsed fine and the problem is unlocking, not the recipe JSON.

The recipe itself is shapeless, `4 × minecraft:torch + 1 ingot → 4 torches`, category
`misc`. The build now refuses a jar in which a metal has a recipe but no unlock file.

## 8. Resources are generated

Two metals need **22 files**: per metal one texture, two block models, two blockstates,
an item model, an item definition, a loot table, a recipe and an unlock advancement, plus
two language files. They differ in a single word, and editing them by hand is how typos
are born. `tools/resources.py write` produces all of them.

| What | How |
|---|---|
| models | wrappers over the vanilla templates `minecraft:block/template_torch` and `template_torch_wall`. The torch has no geometry of its own; only the texture changes |
| wall blockstate | the four `facing` rotations of vanilla `wall_torch` (east 0, south 90, west 180, north 270) |
| texture | 16×16, drawn pixel by pixel with Pillow. The vanilla template uses only the strip x 7..9, y 6..16, so everything is drawn strictly inside it: the stick, a metal ring, the flame shaded from the metal's colour (×0.55 at the ring up to ×1.45 at the tip). Pixels outside the strip would show on the item icon only |
| item | `items/<id>.json` → `models/item/<id>.json` with parent `minecraft:item/generated` and the block texture as `layer0` |
| language files | `block.metaltorch.<id>_torch` and `..._wall_torch` for English and Russian, plus `modmenu.descriptionTranslation.metaltorch` so Mod Menu shows a translated description. The English description is copied from `fabric.mod.json`, its only home |

Two safety nets are built in:

* **The generator checks itself against the Java enum.** It parses `MetalTorch.java` and
  refuses to write anything if the ids, colours or ingredients disagree with its own table.
* **The generator owns its directories** (`OWNED_DIRS`). It writes them completely, so it
  also deletes whatever it did not write this time. Without that, a removed metal leaves
  its files behind and they silently travel into the jar — which nearly happened when the
  copper torch was dropped.

The output is deterministic: a second run with the same Pillow version rewrites every
file byte for byte.

## 9. Building with plain javac

There is no Gradle and no Loom, and that is a consequence of the game, not a taste.

**Why it is possible.** Minecraft 26.x ships **unobfuscated**: the client jar carries real
names such as `net.minecraft.world.level.block.TorchBlock`. Mojang stopped publishing
mappings as of 26.1, Yarn was never released for 26.2, and fabric-intermediary for 26.2 is
an empty stub. The names in the source are the names in the jar. Remapping — the main job
of Loom — has nothing left to do, so `javac` against the installed game is a complete
build, and it needs no network.

**What `build.py build` does:**

1. **Classpath from the profile manifest.** The list of libraries is read from the version
   manifest of the profile (`<name>.json`), **not** by walking the `libraries` folder. That
   folder also holds jars of other installations — several `authlib`, `datafixerupper` and
   `asm` versions side by side. Walk it, and all of them land on the classpath, file order
   picks the winner, compilation still succeeds — and then the self-test dies with
   `NoSuchMethodError` inside vanilla code. The manifest lists exactly the versions the
   game starts with.
2. Libraries that carry OS `rules` and are absent from disk are skipped — those are
   natives for other operating systems. A missing library *without* rules means a broken
   installation, and the build stops.
3. The jars are copied into **one flat directory** in the system temp folder and passed as
   `-cp dir/*`: a classpath written out as a string runs into the 32767-character limit of
   the Windows command line. The client is copied as `AAA-minecraft.jar` so that it sorts
   before libraries carrying the same packages.
4. Fabric API is a container: the real modules sit inside it under `META-INF/jars/`. They
   are extracted into the same directory.
5. `javac --release 25 -proc:none -encoding UTF-8`, then the checks of the next section,
   then a plain zip: `resources/` plus the classes.

**What it costs.** The build depends on how the launcher lays out an installation (see
the limitation in the [README](../README.md#building-from-source)); there is no dependency
management and no IDE project; and every game version needs a rebuild against that
version. For four classes this is a good trade. For a large mod it is not.

## 10. What the build verifies

The build does not end with "the script ran without errors" — it checks the result.

| Check | What it catches |
|---|---|
| every `net/minecraft/**` reference in the compiled classes (`javap -c`) exists in the client jar | compiling against the wrong game version: a libraries folder can hold another client, and `javac` resolves from it without a word |
| `tools/SelfTest.java` on live vanilla blocks | a change in the loot table rule of section 6 |
| ten named files per metal are in the jar | a forgotten resource. The game does not crash: the block turns into a purple-and-black cube, the recipe just does not exist |
| every `.json` in the jar parses | a broken file that the game swallows silently |
| both language files carry both block keys of every metal | a raw translation key instead of a name |
| no `*_wall_torch.json` loot table | a misunderstanding of section 6 |
| the entry point class is inside the jar | a jar Fabric cannot start |
| `fabric.mod.json` goes through `ModMetadataParser` of fabric-loader itself; any warning fails the build | a manifest the game would reject or complain about — judged by the very code that reads it at start-up |

## 11. Differences from the vanilla torch

Known, and listed so nobody has to rediscover them:

| | Vanilla torch | Metal torch |
|---|---|---|
| light level | 14 | 15 |
| flame | `FLAME` particle | none; tinted `DustParticleOptions` sparks |
| wall variant, particle height | `y + 0.7 + 0.22` | the same since 1.1.1 (`y + 0.7` before). **Not checked in game** |
| piston behaviour | `pushReaction(PushReaction.DESTROY)`: a piston pops the torch off as an item | the same since 1.1.1. Before that nothing was set, so the default `NORMAL` applied and a piston would have slid the torch along. **Not checked in game** |
| name of the wall block | copied from the standing block (`overrideDescription`) | its own language key with the same text |

## 12. Adding a metal

1. **Check that vanilla does not already have that torch.** This is how copper was caught:
   26.2 has `minecraft:copper_torch`. The quick test is whether the client jar contains
   `data/minecraft/loot_table/blocks/<name>_torch.json`.
2. Add a value to `MetalTorch.java`: id, colour `0xRRGGBB`, ingredient.
3. Add the same line to `METALS` in `tools/resources.py`, with the two display names.
4. `python tools/resources.py write` — it refuses to work if the two lists disagree.
5. Add the metal's id to the list printed by `tools/SelfTest.java` (cosmetic: it only
   prints the expected paths).
6. `python build.py build`.

Removing a metal is the same in reverse; the generator clears the leftover files itself.
Blocks of a removed metal vanish from existing worlds, like the blocks of any removed mod.

## 13. Porting to another Minecraft version

1. Install that version with Fabric and Fabric API, start it once, point
   `MC_PROFILE_DIR` at its profile folder.
2. Change `"minecraft"` in `resources/fabric.mod.json` (and `"java"` / `--release` in
   `build.py` if the game moved to a newer Java).
3. `python build.py build` and read what fails:
   * `javac` errors — a class or method moved. The usual suspects are the ones this
     document names: the `TorchBlock` constructors, `codec()`, `DustParticleOptions`,
     `Properties.overrideLootTable`, `StandingAndWallBlockItem`, the creative tab event of
     Fabric API;
   * the reference check — you are compiling against a different client than you think;
   * the self-test — the loot table rule changed; fix the path in the generator to match
     what the test prints.
4. Check the data formats against the new client jar: open its own `torch` recipe, loot
   table, unlock advancement and `items/torch.json`, and compare them with what the
   generator writes. Data formats change between versions more often than code does.
5. Then check in game what no build can check: the recipe book, a torch broken off a wall,
   the particles.
