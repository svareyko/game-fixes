import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.storage.loot.LootTable;

import java.util.Optional;

/**
 * Self-test: checks the rule by which a block gets its loot table.
 *
 * The question this test exists for: does an item drop when one of our torches is
 * broken - the standing one and the wall one. The answer hangs on a rule that is
 * far from obvious: Properties.setId sets ONLY the id, and the loot table key is
 * derived from that id. If the rule were different, the loot table file would sit
 * in the wrong place and a broken torch would drop nothing - silently, no log error.
 *
 * The rule is not read out of bytecode, it is checked on live vanilla blocks:
 * take the real torch from the game and look at the key it ended up with. Along
 * the way, check that the vanilla WALL torch has the very same key - that is
 * the scheme MetalTorchMod repeats through overrideLootTable.
 */
public class SelfTest {

    private static int failures = 0;

    private static void check(boolean ok, String what) {
        System.out.println((ok ? "  ok   " : "  FAIL ") + what);
        if (!ok) {
            failures++;
        }
    }

    private static Optional<ResourceKey<LootTable>> lootOf(Block block) {
        return block.getLootTable();
    }

    public static void main(String[] args) {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();

        Optional<ResourceKey<LootTable>> torch = lootOf(Blocks.TORCH);
        Optional<ResourceKey<LootTable>> wallTorch = lootOf(Blocks.WALL_TORCH);

        check(torch.isPresent(), "the vanilla torch has a loot table");
        if (torch.isEmpty()) {
            System.exit(1);
        }

        Identifier key = torch.get().identifier();
        System.out.println("  vanilla torch      -> " + key);
        System.out.println("  vanilla wall torch -> "
                + wallTorch.map(k -> k.identifier().toString()).orElse("NONE"));

        // This is the rule that yields the path of our file:
        // data/<namespace>/loot_table/<path>.json
        check("minecraft".equals(key.getNamespace()) && "blocks/torch".equals(key.getPath()),
                "the key is derived as <namespace>:blocks/<block id>");

        check(wallTorch.isPresent() && wallTorch.get().equals(torch.get()),
                "the wall torch points at the table of the standing torch - the scheme this mod repeats");

        // For our torches the rule gives the paths below. build.py checks that the
        // files exist; what matters here is that the path comes from the same rule.
        for (String metal : new String[]{"iron", "gold"}) {
            System.out.println("  expecting file: data/metaltorch/loot_table/blocks/"
                    + metal + "_torch.json");
        }

        if (failures > 0) {
            System.out.println("  failures: " + failures);
            System.exit(1);
        }
        System.out.println("  self-test passed");
    }
}
