package metaltorch;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.creativetab.v1.CreativeModeTabEvents;
import net.minecraft.core.Direction;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.StandingAndWallBlockItem;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.state.BlockBehaviour;

import java.util.ArrayList;
import java.util.List;

/**
 * Torches with a metal core: iron and gold.
 *
 * WHAT MATTERS ABOUT BRIGHTNESS. Light in Minecraft is colourless and an integer:
 * a block only has a level of 0..15. The vanilla torch gives 14, a metal torch 15.
 * That is the engine's ceiling - there is nothing to make it "even brighter" with.
 * The colour lives in the torch itself and in its sparks, not in the light around.
 *
 * Every metal is TWO blocks, exactly like the vanilla torch: a standing one and
 * a wall one. One item serves both; StandingAndWallBlockItem picks the block to
 * place depending on where the player clicked.
 */
public class MetalTorchMod implements ModInitializer {

    public static final String MOD_ID = "metaltorch";

    /** The ceiling of the engine. The vanilla torch is 14. */
    public static final int LIGHT_LEVEL = 15;

    public static Identifier id(String path) {
        return Identifier.fromNamespaceAndPath(MOD_ID, path);
    }

    /** Same order as MetalTorch: handy both for the creative tab and for checks. */
    public static final List<Item> TORCH_ITEMS = new ArrayList<>();

    static {
        for (MetalTorch metal : MetalTorch.values()) {
            register(metal);
        }
    }

    private static void register(MetalTorch metal) {
        ResourceKey<Block> standingKey = ResourceKey.create(Registries.BLOCK, metal.standingId());
        ResourceKey<Block> wallKey = ResourceKey.create(Registries.BLOCK, metal.wallId());

        Block standing = Registry.register(BuiltInRegistries.BLOCK, standingKey,
                new MetalTorchBlock(metal.colour(), torchProperties().setId(standingKey)));
        Block wall = Registry.register(BuiltInRegistries.BLOCK, wallKey,
                new MetalWallTorchBlock(metal.colour(),
                        torchProperties().overrideLootTable(standing.getLootTable())
                                .setId(wallKey)));

        ResourceKey<Item> itemKey = ResourceKey.create(Registries.ITEM, metal.standingId());
        Item item = Registry.register(BuiltInRegistries.ITEM, itemKey,
                new StandingAndWallBlockItem(standing, wall, Direction.DOWN,
                        new Item.Properties().useBlockDescriptionPrefix().setId(itemKey)));
        TORCH_ITEMS.add(item);
    }

    /**
     * The properties of the vanilla torch plus our light level.
     *
     * The wall variant receives the loot table of the standing one: both have
     * to drop the same item, exactly like the vanilla torch - otherwise nothing
     * at all drops from a wall.
     */
    private static BlockBehaviour.Properties torchProperties() {
        return BlockBehaviour.Properties.of()
                .noCollision()
                .instabreak()
                .lightLevel(state -> LIGHT_LEVEL)
                .sound(SoundType.WOOD);
    }

    private static final ResourceKey<CreativeModeTab> FUNCTIONAL_BLOCKS_TAB =
            ResourceKey.create(Registries.CREATIVE_MODE_TAB,
                    Identifier.parse("minecraft:functional_blocks"));

    @Override
    public void onInitialize() {
        CreativeModeTabEvents.modifyOutputEvent(FUNCTIONAL_BLOCKS_TAB).register(output -> {
            for (Item item : TORCH_ITEMS) {
                output.accept(item);
            }
        });
    }
}
