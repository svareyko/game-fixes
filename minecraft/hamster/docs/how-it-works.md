# How the Pocket Hamsters mod works

**Read this when:** you want to change the mod, port it to another Minecraft version,
or borrow a technique for a mod of your own.

**Not this, for:** what the mod does in the game, how to install and remove it →
[../README.md](../README.md); the build commands and how to point the script at your
game → [Building from source](../README.md#building-from-source).

**Sections:** this is a reference, meant to be read one section at a time — the
sections do not depend on each other.
[Why plain javac is enough](#why-plain-javac-is-enough) ·
[What the build verifies](#what-the-build-verifies) ·
[Source map](#source-map) ·
[The entity](#the-entity) ·
[Spawning, and worlds that already exist](#spawning-and-worlds-that-already-exist) ·
[Colour variants](#colour-variants) ·
[Model and textures](#model-and-textures) ·
[The wheel](#the-wheel) ·
[Hamster in the pocket](#hamster-in-the-pocket) ·
[Throwing and the creeper](#throwing-and-the-creeper) ·
[Monsters fear hamsters](#monsters-fear-hamsters) ·
[Known rough edges](#known-rough-edges) ·
[Porting to a new game version](#porting-to-a-new-game-version)

Everything below is about Minecraft **26.2**, Fabric Loader 0.19 and version **0.5.1**
of the mod. Class and method names are the real ones from the game jar: 26.x is not
obfuscated. Where a statement says "checked in the bytecode", it was read with `javap`
from the 26.2 client, not taken from a forum.

## Why plain javac is enough

There is no Gradle and no Loom in this project. Minecraft 26.x ships **unobfuscated**:
Mojang stopped publishing mappings with 26.1, Yarn has no 26.2 release, and
`fabric-intermediary` for 26.2 is an empty stub. Loom's main job — remapping — is a
no-op here. What remains of a build is "call `javac` with the right classpath and zip
the result", and `build.py` does exactly that, against the files of the installed
game, without any network access:

1. assemble the classpath;
2. `javac --release 25 -proc:none` over `src/`;
3. check every `net/minecraft/**` reference against the client jar;
4. run the model self-test;
5. zip `resources/` and the classes into `build/hamster-<version>.jar`;
6. check the resources inside the finished jar;
7. let fabric-loader's own parser read `fabric.mod.json`.

A `fabric.mod.json` written by hand replaces what Loom would generate. There are no
mixins and no access wideners, so nothing else needs processing.

### The classpath comes from the profile manifest

`build_classpath()` reads the library list from the version manifest of the profile
(`<profile>/<profile>.json`) and does **not** walk the `libraries` folder. That is not
pedantry. `libraries` is shared by every version and profile the launcher has ever
installed, so it can hold three different `authlib`, two `datafixerupper`, four `asm`.
Walk the folder and all of them land on the classpath; which one wins is decided by
file order. Compilation still passes — and then the self-test dies with a
`NoSuchMethodError` deep inside vanilla code. The manifest lists exactly the versions
the game itself starts with.

Other details of that function that are there for a reason:

| Detail | Reason |
|---|---|
| Libraries that have `rules` in the manifest may be missing on disk | They are natives for other operating systems, the launcher never downloads them. A missing library **without** rules means a broken installation, and the build refuses to go on |
| The client jar is copied as `AAA-minecraft.jar` | With `-cp folder/*` the order is up to the file system, and the client has to come before libraries that carry the same packages |
| A folder of copied jars instead of one long `-cp` string | A list of some 140 full paths can run into the Windows command line limit of 32 767 characters; `-cp folder/*` never does |
| Fabric API is unpacked | The file in `mods/` is a jar of jars: the real modules lie in `META-INF/jars/` and are extracted next to the other libraries |
| The folder lives in the system temp directory | It is around 130 MB and is rebuilt from the game files on every run |

The compiler is taken from the Java runtime bundled with the game — the same Java 25
the mod will run on — then from `JAVA_HOME`, then from `PATH`.

## What the build verifies

The build does not stop at "the script ran without errors". It checks the result:

| Check | What it catches |
|---|---|
| Every `net/minecraft/**` reference found by `javap` in the compiled classes must exist in the client jar | A build against the wrong game version: `libraries` can hold the client of another version, and `javac` silently resolves `net.minecraft` from there |
| `tools/SelfTest.java` bakes both models, looks up every part by name and runs `setupAnim` | A typo in a model part name. `getChild` throws at run time — the game would crash the first time a hamster comes into view |
| `verify_resources` reads the list of variants from `HamsterVariant.java` and looks for the textures in the jar | A texture that was never generated — a purple-and-black checkerboard instead of a hamster |
| `tools/textures.py write` compares its `BOXES` with `HamsterModel.java` and `HamsterWheelModel.java` | A UV layout that drifted away from the model — the texture would land on the wrong faces |
| `verify_resources` parses every JSON in the jar | A broken file: the game swallows it silently and the block turns into a purple cube |
| `verify_resources` compares the blockstate file with all combinations of `facing` × `occupied` | A missing combination — "model not found" in the log and a purple cube in the world |
| `fabric.mod.json` goes through `ModMetadataParser` of fabric-loader itself, any warning fails the build | Metadata the game would not accept. The judge is the code that reads it at start-up, not our own idea of the format |

The self-test brings up the game registries first (`SharedConstants.tryDetectVersion()`
and `Bootstrap.bootStrap()`), the same way the vanilla tests do. The wheel model needs
that: it pulls in `RenderTypes`, which reaches into the registries. No OpenGL and no
window are involved — baking a model is pure work on data.

The mod itself is **not** registered in the test. `hamster.HamsterMod` must not be
touched there: its static initialiser registers things, and after `bootStrap()` the
registries are frozen. For the same reason `HamsterVariant` deliberately spells the
namespace `"hamster"` as a literal instead of using `HamsterMod.MOD_ID` — otherwise
loading the enum would drag `HamsterMod` in.

A side effect: the bootstrap starts the game's logging, which writes `logs/latest.log`
into the current directory. The folder is git-ignored.

## Source map

| File | Job |
|---|---|
| `src/hamster/HamsterMod.java` | Entry point `main`: registers the entity, the items, the block, the block entity, the data component, natural spawning and the creative tabs |
| `src/hamster/Hamster.java` | The entity: behaviour goals, food, taming, breeding, picking up |
| `src/hamster/HamsterVariant.java` | Colour variants and texture paths |
| `src/hamster/HamsterItem.java` | The hamster as an item: releasing and throwing |
| `src/hamster/ThrownHamster.java` | The projectile: kills a creeper, releases the animal |
| `src/hamster/MonsterFear.java` | Zombies and skeletons avoid hamsters |
| `src/hamster/HamsterWheelBlock.java` | The wheel block: facing, occupied flag, comparator output |
| `src/hamster/HamsterWheelBlockEntity.java` | Rotation angle of the rim on the client; on the server, the watchdog that frees a wheel whose hamster is gone |
| `src/hamster/UseWheelGoal.java` | The "run in the wheel" behaviour goal |
| `src/hamster/client/HamsterClient.java` | Entry point `client`: model layers and renderers |
| `src/hamster/client/HamsterModel.java` | Geometry and animation of the hamster |
| `src/hamster/client/HamsterRenderer.java`, `HamsterRenderState.java` | Texture choice by variant; the render-state snapshot |
| `src/hamster/client/HamsterWheelModel.java` | The rim: 8 tread segments and 8 spokes |
| `src/hamster/client/HamsterWheelRenderer.java`, `HamsterWheelRenderState.java` | Drawing the spinning rim |
| `tools/textures.py` | Generates every PNG and checks itself against the Java models |
| `tools/preview.py` | Isometric software render of the model, to look at it without the game |
| `tools/SelfTest.java`, `tools/ValidateMod.java` | The two checks the build runs on the JVM |
| `resources/` | `fabric.mod.json`, blockstate, block and item models, textures, language files, recipe, loot table |

The client classes live in `hamster.client` behind an entry point of their own, so a
dedicated server never loads them. `"environment": "*"` — the mod is needed on both
sides, because it adds registry content.

## The entity

`Hamster` extends the vanilla `TamableAnimal`. With readable game code the honest way
to write a pet is to read how the cat and the wolf do it and keep only the setup of
one's own: goals, food, variant.

| Priority | Goal |
|---|---|
| 0 | `FloatGoal` |
| 1 | `PanicGoal` 1.5 |
| 2 | `SitWhenOrderedToGoal` |
| 3 | `BreedGoal` |
| 4 | `TemptGoal` on the item tag `minecraft:chicken_food` |
| 5 | `UseWheelGoal` — see [The wheel](#the-wheel) |
| 6 | `FollowOwnerGoal` 1.2, start at 6 blocks, stop at 2 |
| 7 | `WaterAvoidingRandomStrollGoal` |
| 8, 9 | `LookAtPlayerGoal`, `RandomLookAroundGoal` |

- **Food** is the vanilla tag `minecraft:chicken_food`, so any seed a datapack adds to
  the tag works too.
- **Taming** is a 1 in 3 roll per seed (entity events 7 and 6 give hearts and smoke).
  For a wild hamster a seed is always a taming attempt, so only tamed hamsters reach
  the vanilla breeding code in `super.mobInteract`.
- **Synched data:** the variant as an `int` and an `in wheel` flag that the client
  needs for the running animation. Of these only the variant is saved (`"Variant"`);
  owner and sitting state are saved by `TamableAnimal` itself.
- **Attributes:** 6 health, speed 0.3, tempt range 10, scale 0.5.
- **Sounds** are the rabbit's, with the ambient interval raised to 600 ticks.

### Size is an attribute, not geometry

The type is registered as 0.5 × 0.4 and then scaled by `Attributes.SCALE` = 0.5, which
gives a 0.25 × 0.2 hitbox. `LivingEntity.getScale()` reads exactly this attribute, and
it multiplies **both the rendering and the hitbox** with one number; its range is
0.0625..16 and it is synchronised to the client. Shrinking the boxes of the model
instead was not an option: box sizes are whole texture pixels, halves would wreck the
UV layout.

One thing does not follow the scale: **the shadow**. `EntityRenderer` copies
`shadowRadius` into the render state as is, so `HamsterRenderer` passes 0.125 by hand.
Change `SCALE` — change the shadow too.

## Spawning, and worlds that already exist

`BiomeModifications.addSpawn` for Plains, Sunflower Plains and Meadow: category
`CREATURE`, weight 10, groups of 2–4. For scale, the vanilla plains list has sheep 12,
pig 10, chicken 10, cow 8, horse 5, donkey 1. The placement rule is the ordinary
`Animal::checkAnimalSpawnRules` on `MOTION_BLOCKING_NO_LEAVES`, registered through
`FabricEntityType.Builder.createMob` together with the default attributes.

**An existing world does not have to be recreated.** `addSpawn` does not edit saved
chunks, it edits the biome definition that the game reads from the registry every time
a world is loaded. But hamsters arrive at different speeds, checked in the bytecode:

- `ServerChunkCache` enables spawning of persistent animals only when
  `gameTime % 400 == 0` — once every **20 seconds**; the flag goes into
  `NaturalSpawner.getFilteredSpawningCategories`.
- `MobCategory.CREATURE` has a cap of **10**, scaled by loaded chunks
  (`cap × chunks / 289`, 289 being a 17 × 17 area), and the cap is shared by all
  animals. Around an old base cows and sheep have already used it up.
- New chunks are not subject to this: animals are placed there during world generation.

## Colour variants

`HamsterVariant` is an enum: `golden`, `grey`, `white`, `panda`, `black`. The variant is
stored **as a number** — in the entity data, in the save file and in the item
component — so the order of the constants is part of the save format. A new variant
goes **at the end**; inserting one in the middle recolours every hamster that already
lives in a world. `byId` uses `floorMod`, so a number written by another version never
crashes, it just wraps around.

To add a variant: a palette in `PALETTES` in `tools/textures.py`, a constant at the end
of the enum, `python tools/textures.py write`. The build then checks that the texture
made it into the jar.

## Model and textures

Ten boxes, one 64 × 32 texture. The geometry is described **twice**:
`HamsterModel.createBodyLayer()` for the game and `BOXES` in `tools/textures.py` for
the generator — the generator needs the unfolded UV layout, the game needs coordinates
relative to the pivot of each part. `textures.py write` compares the `texOffs` offsets
and the box sizes with the `.java` files and refuses to work when they differ, so the
two cannot drift apart silently.

The coordinate systems differ: in Python Y points **up** from the ground, in Java
**down** (zero of the root part is on the ground under the mob). Conversion:
`mc_y = -(y0 + h)`.

- Whatever the generator does not paint stays transparent. The base render type of
  entity models in 26.2 is `RenderTypes.entityCutout`, which discards such pixels.
- The baby is the same mesh through `MeshTransformer.scaling(0.65)`.
- The animations are deliberately simple: legs as a pendulum on `walkAnimationPos`, the
  head follows the look angles, a lowered rear when sitting. In the wheel the phase
  comes from **time**, because there is no distance walked and `walkAnimationSpeed` is
  zero; the body leans forward and bounces, because on an animal this small the legs
  alone cannot be seen.
- In 26.x a renderer no longer holds the entity: `extractRenderState` copies what the
  model needs into `HamsterRenderState` (variant, sitting, in wheel, age in ticks).

The textures are drawn by code from a handful of palette colours. Nothing comes from
other mods or from vanilla textures.

## The wheel

### State lives in the block state

Whether the wheel is occupied is a **block state property** (`occupied`, next to
`facing`), not a field of the block entity. The block state reaches the client for
free, the client spins the rim from it, and the comparator reads the same value:
`getAnalogOutputSignal` returns 15 or 0. The block entity holds no data of its own —
nothing of it is saved or synchronised. On the client it carries the renderer and the
rotation angle; on the server its ticker is the watchdog that frees a wheel whose
hamster is gone, see [The watchdog](#the-watchdog-a-wheel-frees-itself).

### The goal

`UseWheelGoal`, flags `MOVE`, `JUMP`, `LOOK`, updated every tick:

| Phase | What happens |
|---|---|
| `canUse` | Not a baby, not told to sit, not in water, cooldown over. Scans ±8 blocks horizontally and ±3 vertically for the nearest wheel with `occupied=false` |
| walking | Pathfinds to the wheel; gives up after 300 ticks |
| `enter` | Within 1.4 blocks (`REACH`): checks the block state **again** instead of trusting its memory, claims the wheel (`Hamster.wheelPos`), sets the `in wheel` flag and then `occupied=true` |
| running | 400 ticks. Every tick: zero velocity, position pinned to the centre of the block at height 0.19, heading re-applied. Ends early if the wheel no longer says `occupied` |
| `stop` | Clears `occupied`, the claim and the flag and starts a cooldown of 600 — otherwise one hamster would own the wheel forever |

The cooldown is counted down inside `canUse`, and an idle goal is asked `canUse` only
from `GoalSelector.tick()`, which `Mob.serverAiStep` runs on **every second** game tick
(on the other ticks only `tickRunningGoals` runs — checked in the bytecode). So 600
means about a minute, not half of one. The walking and running counters live in
`tick()`, and with `requiresUpdateEveryTick()` those are real ticks: 15 and 20 seconds.

Height 0.19 is the inner edge of the rim: the wheel centre is at 0.5, the inner radius
is 5/16, so the track is at 0.5 − 0.31.

### The watchdog: a wheel frees itself

Up to 0.5.0 the `occupied` flag could outlive the hamster. The goal clears it in
`stop()`, and the game calls `stop()` only from `GoalSelector.tick()` and
`removeAllGoals` (which `removeGoal` goes through). A hamster that vanishes in the middle
of a run never gets there — checked in the bytecode:

| How the hamster vanishes | Why its `stop()` never runs |
|---|---|
| Picked up into the inventory | `Hamster.mobInteract` calls `discard()`: the entity is removed, its goals are not stopped |
| Killed outright | `LivingEntity.aiStep` skips `serverAiStep` while `isImmobile()`, which is `isDeadOrDying()`; 20 ticks later `tickDeath` removes the body |
| Unloaded with its chunk, or the world closed | `PersistentEntitySectionManager.unloadEntity` calls the final `setRemoved(UNLOADED_TO_CHUNK)` directly — not even `remove()` |

Such a wheel gave signal 15 for good, kept spinning, and no hamster would enter it. Since
0.5.1 the wheel checks for itself, in two parts:

- **The claim.** `Hamster.wheelPos` is a plain field: the wheel the hamster runs in, or
  null. `enter()` sets it **before** it sets `occupied=true`, `stop()` clears it. It is
  neither saved nor synchronised, on purpose: after a reload no run is in progress, so no
  hamster may claim a wheel.
- **The watchdog.** `HamsterWheelBlockEntity.serverTick` returns at once unless the wheel
  is occupied. Otherwise, once a second (`getGameTime() % 20 == 0`; the beacon throttles
  its own check the same way with `% 80`), it asks
  `Level.hasEntities(HAMSTER, box, h -> h.isAlive() && pos.equals(h.getWheelPos()))` and,
  when nothing matches, sets `occupied=false` with flag 3 — that notifies the
  neighbours, the comparator among them, and the client.

| Detail | Reason |
|---|---|
| The claim has to name **this** wheel, "a hamster nearby" is not enough | Two wheels side by side must not keep each other occupied |
| The box is the block grown by `REACH` (1.4) on every side, so it reaches 1.9 from the centre | On the tick it climbs in, the hamster is still up to `REACH` from the centre — it is pinned into the rim only from the next tick — and `ServerLevel.tick` runs entities before block entities, so the watchdog can look on that very tick |
| The claim is set before the block state | Whatever the watchdog sees as occupied already has its claimant |
| `isAlive()` | A dying hamster lies in the world for 20 more ticks; it should not hold the wheel meanwhile |
| The ticker is attached to every wheel and returns early | A ticker that depends on the state, like the campfire's, would work too: `LevelChunk` resolves the ticker again on chunk load (`registerAllBlockEntitiesAfterLevelLoad`) and on every state change that keeps the block entity (`setBlockState` → `updateBlockEntityTicker`). Wheels are few, and one property read per tick is not worth a second moving part |
| Nothing in `Entity.remove()` | Touching the world while a chunk unloads is asking for trouble, and the unload does not go through `remove()` anyway, see the table above |
| `getGameTime()` works in every dimension | The Nether and the End read the clock of the overworld through `DerivedLevelData` |

**After a reload** nothing of a run is left. Neither the claim nor the `in wheel` flag is
saved — `Entity.saveWithoutId` writes no synchronised data by itself, and `Hamster` adds
only `Variant`. A hamster saved in the middle of a run comes back standing where it ran,
with no claim, and its wheel frees itself within a second; the hamster may then climb in
again. Wheels left stuck by 0.5.0 heal the same way: the block entity is saved with the
chunk although it carries no data (`LevelChunk.getBlockEntityNbtForSaving`), so it is
back after loading and gets its ticker.

**Chunks that are loaded but not simulated.** At the edge of the simulation distance there
is a ring of chunks at level 32: `ChunkLevel.isBlockTicking` is true there and
`isEntityTicking` is not. Block entities tick, entities do not, so a hamster running in a
wheel there is frozen mid-run, claim set. The watchdog still finds it: the entity sections
of such a chunk are `TRACKED`, `Visibility.isAccessible()` is true for them, and
`EntitySectionStorage` skips only inaccessible sections. So the wheel stays occupied —
which is true, the hamster is in it — and the run goes on when the player comes back.

**The goal trusts the block state.** The other way round, a hamster keeps running only
while its wheel says `occupied`. If the flag is cleared under it — by a debug stick or a
command — it gets out instead of sharing the wheel with the next hamster.

### Rendering the rim

The static frame is an ordinary JSON block model that the game draws itself. The
spinning rim is drawn by a block entity renderer, and two things took time there.

**The matrix is left alone.** In 26.2 a block entity renderer receives the `PoseStack`
already set up — the vanilla `BellRenderer` does nothing to it, `ChestRenderer` only
turns it for the facing. Which way Y points in that space could not be told reliably
from the bytecode: the bell's pivot `(8, 12, 8)` is equally plausible with Y up and
with Y down plus a flip. So the rim is **symmetric** about the centre of the block
along all three axes, and its pivot is exactly the centre — `PartPose.offset(8, 8, 8)`.
Either way the part lands in the middle of the block, and a flip cannot be seen on a
ring. The turn for the facing is done **inside the model**, by rotating the root part
around its own pivot, not through the `PoseStack` — no guessing which units the
matrix uses.

**A texture without an atlas.** `submitModel` has an overload that takes a plain
`Identifier` instead of a `SpriteId`. The `SpriteId` route would mean registering the
texture in an atlas under `assets/minecraft/atlases/` — a file that resource packs like
to replace. The plain overload needs nothing but the PNG.

### Pitfall: the wheel glowed through walls

Symptom: the rim had a white outline and was visible through buildings, like an entity
hit by a spectral arrow.

The cause is the argument order. That `Identifier` overload has three `int`s, and the
last one is **not the model colour** but the **outline colour**; the model colour is
hard-wired inside. The bytecode of the overload in `OrderedSubmitNodeCollector`, where
it forwards to the main method:

```
iload 5      -> light
iload 6      -> overlay
iconst_m1    -> model colour, hard-wired to -1
aconst_null  -> sprite
iload 7      -> OUTLINE colour - this is where our -1 used to go
```

`EntityRenderState` has an `outlineColor` field and a `NO_OUTLINE` constant for the
same thing. The value to pass is **0**.

### Pitfall: the hamster stood across the wheel

The first version turned the hamster to the wheel's `FACING`, and it stood facing the
viewer — from the side it looked like "jumped in and just stands there". `FACING` is the
side from which the **face** of the rim is seen; running goes **across** that. With
`facing=north` the plane of the wheel lies along X, so the hamster has to look east or
west: hence `+ 90` degrees in `UseWheelGoal.faceAlongWheel`. The heading is re-applied
every tick, not only on entry — otherwise any trifle knocks it off, such as being pushed
by a second hamster.

## Hamster in the pocket

Only **your own tamed** hamster can be picked up, and only **while sneaking** with an
empty hand. The sneak check is not pedantry: a plain right click makes a pet sit, and
without the check there would be no way to simply ask a hamster to sit.

The item does **not** store the whole animal, only the colour variant — one number in
the mod's own data component `hamster:variant` (`Codec.INT`, synchronised as a var-int).
Serialising the entire entity is possible, but in 26.x that means `ValueInput` /
`ValueOutput` and fiddling with tags for data a pocket pet does not need. The name
travels through the vanilla `CUSTOM_NAME` component. Both ways out of the pocket — put
down (`useOn`) and thrown (`ThrownHamster`) — restore the colour and the name through one
helper, `HamsterItem.applyStack`, the reverse of `HamsterItem.of`. Up to 0.5.0 each path
unpacked the stack by itself, and the throw forgot the name. Everything else is recreated
on release: full health, an adult, and the owner is whoever lets it out. A released
hamster gets `setPersistenceRequired()` — it is a pet, not a random animal from the
plains.

### Pitfall: a gesture that fails silently

In 0.4.0 the pick-up gesture did **exactly nothing** on a wild hamster: the branch sat
inside `if (isTame())`, and on an untamed animal the code never got there. From the
outside that is indistinguishable from a broken feature, and it was reported as one.

Before fixing it, it was worth making sure that dispatch was not the culprit — in 26.2
the path of a click on an entity is longer than it used to be. Checked in the bytecode:
with an empty hand **nothing intercepts the click** before our code.

| Step | What it does with an empty hand |
|---|---|
| `Player.interactOn` | Calls `Entity.interact(Player, InteractionHand, Vec3)` — the signature that carries the hit location |
| `Mob.checkAndHandleImportantInteractions` | Name tag and spawn egg; an empty hand passes |
| `super.interact` → `Entity.interact` | **Sneaking** goes into the leash logic, but when the player leads no mobs the list is empty and the result is `PASS` |
| `Mob.mobInteract` | Called — our code |

So the mechanics were intact and a condition was simply not met. The fix is in the
behaviour, not in dispatch: the branch moved **before** the tameness check and now
answers in the line above the hotbar — "tame the hamster with seeds first" or "this
hamster is not yours".

The rule taken from this: **a gesture that can fail has to say why.** A silent refusal
cannot be told from a defect, and sorting it out costs an evening of reading bytecode
instead of one line of text in the game.

## Throwing and the creeper

The game already tells "put down" from "throw", nothing had to be invented: a right
click **on a block** calls `useOn` (release), and when there is no block under the
crosshair it calls `use` (throw). Aiming at a creeper ends up in the second branch,
which is exactly what is wanted.

`ThrownHamster` extends `ThrowableItemProjectile`, with the snowball's speed 1.5 and
inaccuracy 1.0, and is drawn with the item icon by the vanilla `ThrownItemRenderer` —
no model of its own.

- `onHit` always releases the animal at the point of impact, with the colour and the
  name from the thrown stack (`HamsterItem.applyStack`), tamed by the thrower,
  persistent. The projectile has the whole stack to give: `ThrowableItemProjectile`
  keeps `copyWithCount(1)` of it, components included, and saves it as `Item` — so the
  name survives even a world saved while the hamster was in flight. The throw as such
  never costs the pet. What follows is ordinary game physics: released high up a wall
  it falls from there, and a projectile that never hits anything — thrown into the
  void — never releases it.
- `onHitEntity` on a `Creeper` deals twice the creeper's maximum health through
  `damageSources().thrown(projectile, owner)` — the source a snowball uses. The player
  is the attacker, so loot and experience drop as for any kill. The creeper does not
  explode: an explosion comes from ignition, not from death.
- No other entity takes damage.

## Monsters fear hamsters

`MonsterFear` adds the vanilla `AvoidEntityGoal` — radius 8, speeds 1.0 and 1.25 — to
every `Zombie` and `AbstractSkeleton`, **without mixins**: Fabric's
`ServerEntityEvents.ENTITY_LOAD` hands over each mob as it is loaded, and the goal is
added to that instance. Individual instances are changed, not game classes, so other
mods are not affected.

- The field `Mob.goalSelector` is protected, but there is a **public**
  `Mob.getGoalSelector()` next to it — no access widener and no reflection needed. It
  pays to look for such an accessor before building a workaround.
- The priority is **1**, above the melee attack of both mobs. That is deliberate: a
  hamster should really drive them off, not make a zombie back away reluctantly while
  still hitting. Outside the radius the goal never triggers.
- In 26.2 `Zombie` is the parent of `Drowned`, `Husk`, `ZombieVillager` and
  `ZombifiedPiglin`; `AbstractSkeleton` is the parent of `Skeleton`, `Stray`,
  `WitherSkeleton`, `Bogged` and `Parched`. All of them are covered.

## Known rough edges

| What | State |
|---|---|
| The vanilla `AgeableMobRenderer` is `@Deprecated` | More than two dozen vanilla renderers of 26.2 still extend it — the rabbit's, the cat's and the wolf's among them |
| Fabric's `EntityRendererRegistry` and `BlockEntityRendererRegistry` are `@Deprecated` | They work on 26.2 |
| `Entity.hurt(DamageSource, float)`, used for the creeper, is `@Deprecated` | It works on 26.2; the server-side entry point next to it is `hurtServer(ServerLevel, DamageSource, float)` |
| The sounds are the rabbit's | There are none of our own; a rabbit squeak suits a hamster well enough |
| The baby is the adult mesh at 0.65 | A separate baby model is not worth it at this size |

The `@Deprecated` marks (`javac -Xlint:deprecation` lists them) are a reason to look
again at the next game update, not now: this is the working API of 26.2.

## Porting to a new game version

1. Point `build.py` at a profile of the new version and change `"minecraft"` in
   `resources/fabric.mod.json` (and `--release` plus `"java"` if the game moved to a
   newer Java).
2. Run `python build.py build`. Compile errors show renamed or moved API. If it
   compiles, `verify_references` still names every `net/minecraft` class the new client
   no longer has, and the self-test shows whether the models still bake.
3. Look at the places that depend on details of one version rather than on stable API:

| Place | What to re-check |
|---|---|
| `HamsterWheelRenderer.submit` | The parameter order of the `submitModel` overload — read its bytecode again, see [the outline pitfall](#pitfall-the-wheel-glowed-through-walls) |
| `HamsterWheelModel` | Whether block entity renderers still receive a ready `PoseStack` |
| `HamsterWheelBlockEntity.serverTick` | That a hamster frozen in a chunk which ticks blocks but not entities is still found by `Level.hasEntities`, and that a block entity without data is still saved with its chunk and gets its ticker back on load — see [the watchdog](#the-watchdog-a-wheel-frees-itself) |
| `Hamster.mobInteract` | The dispatch chain in [the table above](#pitfall-a-gesture-that-fails-silently), sneaking in particular |
| `MonsterFear` | Where `Zombie` and `AbstractSkeleton` live (in 26.2: `monster.zombie` and `monster.skeleton`) and that `getGoalSelector()` is still public |
| `HamsterMod` | The identifiers of the creative tabs (`minecraft:spawn_eggs`, `minecraft:functional_blocks`) — the fields in `CreativeModeTabs` are private, so the keys are spelled out |
| `tools/SelfTest.java` | How the vanilla tests bootstrap the registries |
| Deprecated API | The classes and the method listed under [Known rough edges](#known-rough-edges) |

4. Test in the game. The self-test proves that the models bake, not that a hamster
   looks right.
