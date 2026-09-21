package hamster;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.biome.v1.BiomeModifications;
import net.fabricmc.fabric.api.biome.v1.BiomeSelectors;
import net.fabricmc.fabric.api.creativetab.v1.CreativeModeTabEvents;
import net.fabricmc.fabric.api.object.builder.v1.entity.FabricEntityType;
import com.mojang.serialization.Codec;
import net.minecraft.core.Registry;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.SpawnPlacementTypes;
import net.minecraft.world.entity.animal.Animal;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.SpawnEggItem;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.levelgen.Heightmap;

import java.util.Set;

/**
 * The common part of the mod: registers the entity, the spawn egg and natural spawning.
 *
 * Built with plain javac, without Gradle and Loom - Minecraft 26.x ships
 * UNobfuscated, so the remapping that Loom exists for is a no-op here.
 * Details are in docs/how-it-works.md.
 *
 * The client part (model, renderer) lives in hamster.client and has an entry
 * point of its own: on a dedicated server those classes are never loaded.
 */
public class HamsterMod implements ModInitializer {

    public static final String MOD_ID = "hamster";

    public static Identifier id(String path) {
        return Identifier.fromNamespaceAndPath(MOD_ID, path);
    }

    public static final ResourceKey<EntityType<?>> HAMSTER_KEY =
            ResourceKey.create(Registries.ENTITY_TYPE, id("hamster"));

    public static final EntityType<Hamster> HAMSTER = Registry.register(
            BuiltInRegistries.ENTITY_TYPE,
            HAMSTER_KEY,
            FabricEntityType.Builder.createMob(
                            Hamster::new,
                            MobCategory.CREATURE,
                            builder -> builder
                                    .defaultAttributes(Hamster::createAttributes)
                                    .spawnPlacement(SpawnPlacementTypes.ON_GROUND,
                                            Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                                            Animal::checkAnimalSpawnRules))
                    .sized(0.5F, 0.4F)
                    .eyeHeight(0.28F)
                    .clientTrackingRange(8)
                    .build(HAMSTER_KEY));

    public static final ResourceKey<Item> SPAWN_EGG_KEY =
            ResourceKey.create(Registries.ITEM, id("hamster_spawn_egg"));

    public static final Item SPAWN_EGG = Registry.register(
            BuiltInRegistries.ITEM,
            SPAWN_EGG_KEY,
            new SpawnEggItem(new Item.Properties()
                    .spawnEgg(HAMSTER)
                    .setId(SPAWN_EGG_KEY)));

    // --- hamster in the pocket ------------------------------------------------

    /**
     * The colour variant that travels with the item. Stored as a number, just like on
     * the entity, so the order of the HamsterVariant values must never change.
     */
    public static final DataComponentType<Integer> HAMSTER_VARIANT = Registry.register(
            BuiltInRegistries.DATA_COMPONENT_TYPE,
            id("variant"),
            DataComponentType.<Integer>builder()
                    .persistent(Codec.INT)
                    .networkSynchronized(ByteBufCodecs.VAR_INT)
                    .build());

    public static final ResourceKey<Item> HAMSTER_ITEM_KEY =
            ResourceKey.create(Registries.ITEM, id("hamster"));

    public static final Item HAMSTER_ITEM = Registry.register(
            BuiltInRegistries.ITEM,
            HAMSTER_ITEM_KEY,
            new HamsterItem(new Item.Properties()
                    .stacksTo(1)          // exactly one animal fits in a hand
                    .setId(HAMSTER_ITEM_KEY)));

    public static final ResourceKey<EntityType<?>> THROWN_HAMSTER_KEY =
            ResourceKey.create(Registries.ENTITY_TYPE, id("thrown_hamster"));

    /** A projectile, not a creature: category MISC, like the snowball. */
    public static final EntityType<ThrownHamster> THROWN_HAMSTER = Registry.register(
            BuiltInRegistries.ENTITY_TYPE,
            THROWN_HAMSTER_KEY,
            EntityType.Builder.<ThrownHamster>of(ThrownHamster::new, MobCategory.MISC)
                    .sized(0.25F, 0.25F)
                    .clientTrackingRange(4)
                    .updateInterval(10)
                    .build(THROWN_HAMSTER_KEY));

    // --- the wheel ------------------------------------------------------------

    public static final ResourceKey<Block> HAMSTER_WHEEL_KEY =
            ResourceKey.create(Registries.BLOCK, id("hamster_wheel"));

    public static final Block HAMSTER_WHEEL = Registry.register(
            BuiltInRegistries.BLOCK,
            HAMSTER_WHEEL_KEY,
            new HamsterWheelBlock(BlockBehaviour.Properties.of()
                    .strength(1.0F, 1.0F)
                    .sound(SoundType.WOOD)
                    .noOcclusion()
                    .setId(HAMSTER_WHEEL_KEY)));

    public static final ResourceKey<Item> HAMSTER_WHEEL_ITEM_KEY =
            ResourceKey.create(Registries.ITEM, id("hamster_wheel"));

    public static final Item HAMSTER_WHEEL_ITEM = Registry.register(
            BuiltInRegistries.ITEM,
            HAMSTER_WHEEL_ITEM_KEY,
            new BlockItem(HAMSTER_WHEEL, new Item.Properties()
                    .useBlockDescriptionPrefix()
                    .setId(HAMSTER_WHEEL_ITEM_KEY)));

    /**
     * The block entity exists only for the renderer of the spinning rim: whether the
     * wheel is occupied lives in the block state, there is nothing for it to save.
     */
    public static final BlockEntityType<HamsterWheelBlockEntity> HAMSTER_WHEEL_ENTITY = Registry.register(
            BuiltInRegistries.BLOCK_ENTITY_TYPE,
            id("hamster_wheel"),
            new BlockEntityType<>(HamsterWheelBlockEntity::new, Set.of(HAMSTER_WHEEL)));

    /** Key of the vanilla "spawn eggs" tab: the field in CreativeModeTabs is private. */
    private static final ResourceKey<CreativeModeTab> SPAWN_EGGS_TAB =
            ResourceKey.create(Registries.CREATIVE_MODE_TAB, Identifier.parse("minecraft:spawn_eggs"));

    private static final ResourceKey<CreativeModeTab> FUNCTIONAL_BLOCKS_TAB =
            ResourceKey.create(Registries.CREATIVE_MODE_TAB, Identifier.parse("minecraft:functional_blocks"));

    @Override
    public void onInitialize() {
        // Plains, sunflower plains and meadows: open grassland suits a small rodent.
        // Weight 10 with groups of 2-4 - the weight pigs and chickens have in plains.
        BiomeModifications.addSpawn(
                BiomeSelectors.includeByKey(Biomes.PLAINS, Biomes.SUNFLOWER_PLAINS, Biomes.MEADOW),
                MobCategory.CREATURE, HAMSTER, 10, 2, 4);

        CreativeModeTabEvents.modifyOutputEvent(SPAWN_EGGS_TAB)
                .register(output -> output.accept(SPAWN_EGG));
        CreativeModeTabEvents.modifyOutputEvent(FUNCTIONAL_BLOCKS_TAB)
                .register(output -> output.accept(HAMSTER_WHEEL_ITEM));
        CreativeModeTabEvents.modifyOutputEvent(SPAWN_EGGS_TAB)
                .register(output -> output.accept(HAMSTER_ITEM));

        MonsterFear.register();
    }
}
