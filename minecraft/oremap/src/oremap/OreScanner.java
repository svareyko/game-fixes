package oremap;

import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.LevelHeightAccessor;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.chunk.LevelChunkSection;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Scans loaded chunks and groups the blocks it finds into veins.
 *
 * What keeps it cheap is three cut-offs, from the cheapest to the most expensive:
 *   1. section.hasOnlyAir()            - free, removes most sections;
 *   2. section.maybeHas(IS_TARGET)     - a check against the palette of the section,
 *                                        O(palette size) instead of 4096 lookups;
 *   3. a full 16x16x16 walk            - only for the sections that survived the first two.
 * Measured on a real world: the full walk is needed for about 3 sections out of 24 per chunk.
 */
public final class OreScanner {

    /** A vein that was found: one marker per cluster, not one per block. */
    public static final class Vein {
        public final OreMap.Target target;
        public final int x;
        public final int y;
        public final int z;
        public final int size;

        Vein(OreMap.Target target, int x, int y, int z, int size) {
            this.target = target;
            this.x = x;
            this.y = y;
            this.z = z;
            this.size = size;
        }

        public double distSqTo(double px, double py, double pz) {
            double dx = x + 0.5 - px;
            double dy = y + 0.5 - py;
            double dz = z + 0.5 - pz;
            return dx * dx + dy * dy + dz * dz;
        }
    }

    /** What was found, broken down by chunk - so that it is dropped together with the chunk. */
    private final Map<Long, List<Vein>> byChunk = new HashMap<>();

    public void clear() {
        byChunk.clear();
    }

    public int chunkCount() {
        return byChunk.size();
    }

    /** How many veins of this type were found in total - for the /oremap status command. */
    public int veinCount(OreMap.Target target) {
        int n = 0;
        for (List<Vein> list : byChunk.values()) {
            for (Vein v : list) {
                if (v.target == target) {
                    n++;
                }
            }
        }
        return n;
    }

    public void forget(ChunkPos pos) {
        byChunk.remove(pos.pack());
    }

    /**
     * Scans one chunk. Call it from the client thread only: the palette of a
     * section is not thread-safe without acquire/release, and the walk is cheap
     * enough that moving it to a separate thread is pointless.
     */
    public void scan(LevelHeightAccessor level, LevelChunk chunk) {
        LevelChunkSection[] sections = chunk.getSections();
        int minSectionY = level.getMinSectionY();
        ChunkPos pos = chunk.getPos();
        int baseX = pos.getMinBlockX();
        int baseZ = pos.getMinBlockZ();

        List<int[]> hits = null;    // {x, y, z, ordinal of the target}

        for (int i = 0; i < sections.length; i++) {
            LevelChunkSection section = sections[i];
            if (section == null || section.hasOnlyAir()) {
                continue;
            }
            if (!section.maybeHas(OreMap.IS_TARGET)) {
                continue;
            }
            int sectionBaseY = (minSectionY + i) << 4;
            for (int y = 0; y < 16; y++) {
                for (int z = 0; z < 16; z++) {
                    for (int x = 0; x < 16; x++) {
                        BlockState state = section.getBlockState(x, y, z);
                        OreMap.Target target = OreMap.targetOf(state);
                        if (target == null) {
                            continue;
                        }
                        if (hits == null) {
                            hits = new ArrayList<>();
                        }
                        hits.add(new int[]{baseX + x, sectionBaseY + y, baseZ + z, target.ordinal()});
                    }
                }
            }
        }

        if (hits == null) {
            byChunk.remove(pos.pack());
            return;
        }
        byChunk.put(pos.pack(), cluster(hits));
    }

    /**
     * Groups neighbouring blocks into veins: a breadth-first walk over the 26 neighbours.
     * A vein of eight diamond blocks must give one marker, not eight.
     *
     * A vein that lies across a chunk border gives two markers - one in each chunk.
     * That is a deliberate trade-off: this way unloading a chunk leaves no dangling markers.
     */
    private static List<Vein> cluster(List<int[]> hits) {
        Map<Long, int[]> byPos = new HashMap<>();
        for (int[] h : hits) {
            byPos.put(key(h[0], h[1], h[2]), h);
        }
        Set<Long> seen = new HashSet<>();
        List<Vein> veins = new ArrayList<>();

        for (int[] start : hits) {
            long startKey = key(start[0], start[1], start[2]);
            if (!seen.add(startKey)) {
                continue;
            }
            ArrayDeque<int[]> queue = new ArrayDeque<>();
            queue.add(start);
            // The representative of the vein is its minimal corner, so that it does not depend on the walk order.
            int minX = start[0];
            int minY = start[1];
            int minZ = start[2];
            int size = 0;

            while (!queue.isEmpty()) {
                int[] cur = queue.poll();
                size++;
                if (cur[1] < minY || (cur[1] == minY && (cur[0] < minX
                        || (cur[0] == minX && cur[2] < minZ)))) {
                    minX = cur[0];
                    minY = cur[1];
                    minZ = cur[2];
                }
                for (int dx = -1; dx <= 1; dx++) {
                    for (int dy = -1; dy <= 1; dy++) {
                        for (int dz = -1; dz <= 1; dz++) {
                            if (dx == 0 && dy == 0 && dz == 0) {
                                continue;
                            }
                            long k = key(cur[0] + dx, cur[1] + dy, cur[2] + dz);
                            int[] neighbour = byPos.get(k);
                            // Only blocks of the same ore type count as neighbours.
                            if (neighbour == null || neighbour[3] != cur[3] || !seen.add(k)) {
                                continue;
                            }
                            queue.add(neighbour);
                        }
                    }
                }
            }
            veins.add(new Vein(OreMap.Target.values()[start[3]], minX, minY, minZ, size));
        }
        return veins;
    }

    private static long key(int x, int y, int z) {
        return ((long) (x & 0x3FFFFFF) << 38) | ((long) (z & 0x3FFFFFF) << 12) | (y & 0xFFF);
    }

    /**
     * The veins of the given type nearest to the player, no farther than the radius and no more than the limit.
     * Without it thousands of markers pile up at renderDistance=32.
     */
    public List<Vein> nearest(OreMap.Target target, double px, double py, double pz,
                              int radius, int limit) {
        double maxSq = (double) radius * radius;
        List<Vein> out = new ArrayList<>();
        for (List<Vein> list : byChunk.values()) {
            for (Vein v : list) {
                if (v.target == target && v.distSqTo(px, py, pz) <= maxSq) {
                    out.add(v);
                }
            }
        }
        out.sort(Comparator.comparingDouble(v -> v.distSqTo(px, py, pz)));
        return out.size() > limit ? out.subList(0, limit) : out;
    }
}
