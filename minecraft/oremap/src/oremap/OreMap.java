package oremap;

import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

import java.util.function.Predicate;

/**
 * Shared constants and settings.
 *
 * The mod is client-side: it walks the chunks that are already loaded, finds
 * diamond ore and ancient debris and hands them to Xaero's map as third-party
 * waypoints. No networking, no packets, nothing is written into the world.
 */
public final class OreMap {

    public static final String MOD_ID = "oremap";

    /** What we look for. */
    public enum Target {
        DIAMOND("Diamonds", "D"),
        DEBRIS("Netherite", "N");

        public final String label;
        public final String initials;

        Target(String label, String initials) {
            this.label = label;
            this.initials = initials;
        }
    }

    /**
     * The radius in blocks beyond which waypoints are not shown. The limit is not
     * cosmetic: at renderDistance=32 the client holds thousands of chunks in
     * memory, and without it the map turns into a mush of waypoints.
     */
    public static final int MARKER_RADIUS = 160;

    /**
     * A hard cap on the number of waypoints per ore type - the nearest ones win.
     * It is also the cap on the number of lines the mod adds to Xaero's waypoint
     * list, which is why it is well below what performance would allow.
     */
    public static final int MAX_MARKERS_PER_TARGET = 80;

    /**
     * How many chunks are taken from the queue per tick. The integrated server
     * hands over the whole batch at once, so without a limit entering a world at
     * renderDistance=32 would put thousands of scans into a single tick.
     */
    public static final int SCANS_PER_TICK = 16;

    /**
     * Whether waypoints are shown. **Off by default** - the mod is switched on on
     * demand with the /oremap on command or with a key (K, rebindable in the
     * controls screen under "Miscellaneous").
     *
     * Off does not mean "hidden", it means "not working": chunks are not scanned,
     * the queue is not drained, the waypoint set is not rebuilt, memory is freed.
     * So the mod costs nothing while it is not needed.
     *
     * The value is also handed to Xaero through setEnabledStateGetter - in case a
     * waypoint somehow survives the clean-up, Xaero still will not show it.
     * volatile: it is read from Xaero's code during rendering.
     */
    public static volatile boolean markersVisible = false;

    /** How often the waypoint set at Xaero is rebuilt, in ticks (20 ticks = 1 second). */
    public static final int REBUILD_INTERVAL_TICKS = 20;

    /**
     * The waypoint name. World Map draws it next to the icon, so the depth goes
     * right here: "Diamonds x8 Y-54". Y is the level of the lowest block of the
     * vein, that is exactly the point the waypoint points at.
     *
     * Kept separate so that the format can be checked by a test without starting the game.
     */
    public static String markerName(Target target, int size, int y) {
        return target.label + (size > 1 ? " x" + size : "") + " Y" + y;
    }

    /**
     * The blocks that make up a vein of one type. Diamond and debris are kept
     * apart so that each goes to Xaero as a waypoint source of its own.
     */
    public static Target targetOf(BlockState state) {
        Block b = state.getBlock();
        if (b == Blocks.DIAMOND_ORE || b == Blocks.DEEPSLATE_DIAMOND_ORE) {
            return Target.DIAMOND;
        }
        if (b == Blocks.ANCIENT_DEBRIS) {
            return Target.DEBRIS;
        }
        return null;
    }

    /**
     * The predicate for LevelChunkSection.maybeHas - a check against the palette
     * of the section instead of going through 4096 blocks. It is what makes the
     * scanning cheap.
     */
    public static final Predicate<BlockState> IS_TARGET = state -> targetOf(state) != null;

    private OreMap() {
    }
}
