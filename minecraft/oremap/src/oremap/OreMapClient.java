package oremap;

import com.mojang.blaze3d.platform.InputConstants;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.command.v2.ClientCommands;
import net.fabricmc.fabric.api.client.command.v2.FabricClientCommandSource;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientChunkEvents;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientLevelEvents;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keymapping.v1.KeyMappingHelper;

import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.chunk.status.ChunkStatus;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;

/**
 * The entry point.
 *
 * By default the mod is off and does nothing: it does not scan, holds no data
 * and does not touch Xaero. It is switched on with the /oremap on command or
 * with the K key. Switching it off frees everything again - that is not "hide
 * the markers" but "stop working".
 *
 * The command is not there for decoration: a key can go unnoticed, be taken by
 * somebody else's binding or be pressed while the map screen is open, when the
 * game does not give the keyboard to the mod. The command always works, and
 * /oremap status shows where the chain breaks instead of leaving it to guesses.
 *
 * While it is on, chunks are not scanned right in the load handler: the
 * integrated server hands over the whole batch at once, ignoring the limit on
 * its size, and at renderDistance=32 that is 65 chunks per tick when a chunk
 * border is crossed and thousands when a world is entered. So chunks are put
 * into a queue, and a limited number per tick is taken from it, the ones
 * nearest to the player first.
 */
public final class OreMapClient implements ClientModInitializer {

    private final OreScanner scanner = new OreScanner();

    /** Chunks waiting to be scanned. Kept as keys, not references: holding a
     *  LevelChunk would get in the way of unloading. */
    private final LinkedHashSet<Long> pending = new LinkedHashSet<>();

    private ClientLevel boundLevel;
    private int tickCounter;
    private boolean hadMarkers;
    private KeyMapping toggleKey;

    /** How many markers went to Xaero at the last rebuild - for /oremap status. */
    private final int[] lastPublished = new int[OreMap.Target.values().length];

    /** Set when the mod is switched on: the chunks that are already loaded have to be processed. */
    private boolean needFullSweep;

    @Override
    public void onInitializeClient() {
        // K rather than O: O is a popular key, in the test setup another mod already
        // had its own screen bound to it. In 26.2 a key press reaches ALL mappings
        // bound to the key (KeyMapping.click goes through forAllKeyMappings), so the
        // conflict did not break the mod, but there is no point in opening somebody
        // else's screen together with toggling the markers.
        toggleKey = KeyMappingHelper.registerKeyMapping(new KeyMapping(
                "key.oremap.toggle", InputConstants.Type.KEYSYM,
                InputConstants.KEY_K, KeyMapping.Category.MISC));

        ClientCommandRegistrationCallback.EVENT.register((dispatcher, registry) ->
                dispatcher.register(ClientCommands.literal(OreMap.MOD_ID)
                        .then(ClientCommands.literal("on").executes(ctx -> {
                            setEnabled(true);
                            say(ctx.getSource(), "ore markers are on");
                            return 1;
                        }))
                        .then(ClientCommands.literal("off").executes(ctx -> {
                            setEnabled(false);
                            say(ctx.getSource(), "ore markers are off");
                            return 1;
                        }))
                        .then(ClientCommands.literal("status").executes(ctx -> {
                            report(ctx.getSource());
                            return 1;
                        }))
                        .executes(ctx -> {
                            report(ctx.getSource());
                            return 1;
                        })));

        ClientChunkEvents.CHUNK_LOAD.register((level, chunk) -> {
            // Rebinding happens here and not only in the tick: the chunks of a new
            // world arrive before the end of the tick, and without this their
            // results were wiped.
            rebind(level);
            if (!OreMap.markersVisible || !enabled(level)) {
                return;
            }
            pending.add(chunk.getPos().pack());
        });

        ClientChunkEvents.CHUNK_UNLOAD.register((level, chunk) -> {
            pending.remove(chunk.getPos().pack());
            scanner.forget(chunk.getPos());
        });

        // A world change arrives here as well - whichever handler sees it first does the rebinding.
        ClientLevelEvents.AFTER_CLIENT_LEVEL_CHANGE.register((mc, level) -> rebind(level));

        ClientTickEvents.END_CLIENT_TICK.register(this::onTick);

        System.out.println("[" + OreMap.MOD_ID + "] loaded: markers for diamonds and netherite "
                + "on Xaero's world map. OFF by default. Switch on: "
                + "the /oremap on command or the K key. State: /oremap status. "
                + "Works only in single player and on the local network.");
    }

    private static void say(FabricClientCommandSource source, String text) {
        source.sendFeedback(Component.literal("[Ore Map] " + text));
    }

    private void report(FabricClientCommandSource source) {
        for (String line : status(source.getClient())) {
            say(source, line);
        }
    }

    /** The single place that switches the mod on and off - for the key and for the command. */
    private void setEnabled(boolean on) {
        OreMap.markersVisible = on;
        needFullSweep = on;
        System.out.println("[" + OreMap.MOD_ID + "] ore markers "
                + (on ? "ON" : "OFF"));
    }

    /**
     * The detailed state. It is there so that a "does not work" complaint shows
     * at which step things stopped instead of leaving it to guesses: switched off,
     * forbidden by the gate, the link to Xaero broke, nothing found, or found but
     * not handed over.
     */
    private List<String> status(Minecraft mc) {
        List<String> out = new ArrayList<>();
        out.add("markers: " + (OreMap.markersVisible ? "ON" : "off")
                + " (switch with /oremap on, /oremap off or the K key)");
        out.add("working here: " + Gate.describe(mc));
        out.add("link to Xaero: " + (XaeroBridge.isBroken()
                ? "BROKEN, stack trace in logs/latest.log" : "ok"));
        out.add("chunks with ore: " + scanner.chunkCount()
                + ", in the scan queue: " + pending.size());
        for (OreMap.Target target : OreMap.Target.values()) {
            out.add(target.label + ": veins found " + scanner.veinCount(target)
                    + ", sent to the map " + lastPublished[target.ordinal()]);
        }
        out.add("marker radius " + OreMap.MARKER_RADIUS + " blocks, cap "
                + OreMap.MAX_MARKERS_PER_TARGET + " per type; markers are on the world map only");
        return out;
    }

    private boolean enabled(ClientLevel level) {
        return level != null && !XaeroBridge.isBroken()
                && Gate.allowed(Minecraft.getInstance());
    }

    /** Returns true if the world changed and the state was reset. */
    private boolean rebind(ClientLevel level) {
        if (level == boundLevel) {
            return false;
        }
        boundLevel = level;
        forgetEverything();
        Gate.reset();
        // The world changed while the mod stayed on - so the chunks of the new
        // world that have already arrived must be processed by hand.
        needFullSweep = OreMap.markersVisible;
        return true;
    }

    private void forgetEverything() {
        scanner.clear();
        pending.clear();
        hadMarkers = false;
        Arrays.fill(lastPublished, 0);
    }

    private void onTick(Minecraft mc) {
        while (toggleKey != null && toggleKey.consumeClick()) {
            setEnabled(!OreMap.markersVisible);
            if (mc.player != null) {
                mc.player.sendOverlayMessage(Component.literal("[Ore Map] ore markers "
                        + (OreMap.markersVisible ? "on" : "off")));
            }
        }

        ClientLevel level = mc.level;
        // Rebinding has to come before the gate check: otherwise the verdict for the
        // new world would be computed on top of the state left from the previous one.
        rebind(level);
        if (level == null || mc.player == null || XaeroBridge.isBroken()) {
            return;
        }

        // Switched off or not allowed here - clean up and do nothing else.
        if (!OreMap.markersVisible || !Gate.allowed(mc)) {
            if (hadMarkers) {
                XaeroBridge.clearAll(mc);
                forgetEverything();
            }
            return;
        }

        Player player = mc.player;
        double px = player.getX();
        double py = player.getY();
        double pz = player.getZ();

        // Just switched on - the chunks around are already loaded, but their load
        // events are long gone. Queue them by hand, otherwise the map would stay
        // empty until the player walks into new places.
        if (needFullSweep) {
            needFullSweep = false;
            enqueueAround(px, pz);
        }

        drainPending(level, px, pz);

        if (++tickCounter < OreMap.REBUILD_INTERVAL_TICKS) {
            return;
        }
        tickCounter = 0;

        for (OreMap.Target target : OreMap.Target.values()) {
            List<OreScanner.Vein> veins = scanner.nearest(target, px, py, pz,
                    OreMap.MARKER_RADIUS, OreMap.MAX_MARKERS_PER_TARGET);
            veins = validate(level, veins);
            XaeroBridge.replaceAll(mc, target, veins);
            lastPublished[target.ordinal()] = veins.size();
        }
        hadMarkers = true;
    }

    /**
     * Queues the square of chunks around the player - exactly the one markers can
     * reach the map from at all (MARKER_RADIUS). Chunks that are not loaded drop
     * out when the queue is drained.
     */
    private void enqueueAround(double px, double pz) {
        int radius = (OreMap.MARKER_RADIUS >> 4) + 1;
        int cx = ((int) Math.floor(px)) >> 4;
        int cz = ((int) Math.floor(pz)) >> 4;
        for (int dx = -radius; dx <= radius; dx++) {
            for (int dz = -radius; dz <= radius; dz++) {
                pending.add(new ChunkPos(cx + dx, cz + dz).pack());
            }
        }
    }

    /**
     * Drains the queue: no more than SCANS_PER_TICK chunks per tick, the nearest first.
     * Otherwise entering a world at renderDistance=32 would put thousands of scans into one tick.
     */
    private void drainPending(ClientLevel level, double px, double pz) {
        if (pending.isEmpty()) {
            return;
        }
        int playerChunkX = ((int) Math.floor(px)) >> 4;
        int playerChunkZ = ((int) Math.floor(pz)) >> 4;

        // A single pass over the queue that picks the nearest. Cheaper than sorting everything.
        List<Long> picked = new ArrayList<>(OreMap.SCANS_PER_TICK);
        long[] bestDist = new long[OreMap.SCANS_PER_TICK];
        for (long key : pending) {
            int dx = ChunkPos.getX(key) - playerChunkX;
            int dz = ChunkPos.getZ(key) - playerChunkZ;
            long dist = (long) dx * dx + (long) dz * dz;
            int at = picked.size();
            if (at < OreMap.SCANS_PER_TICK) {
                picked.add(key);
                bestDist[at] = dist;
            } else {
                int worst = 0;
                for (int i = 1; i < at; i++) {
                    if (bestDist[i] > bestDist[worst]) {
                        worst = i;
                    }
                }
                if (dist < bestDist[worst]) {
                    picked.set(worst, key);
                    bestDist[worst] = dist;
                }
            }
        }

        for (long key : picked) {
            pending.remove(key);
            LevelChunk chunk = level.getChunkSource()
                    .getChunk(ChunkPos.getX(key), ChunkPos.getZ(key), ChunkStatus.FULL, false);
            if (chunk != null) {
                scanner.scan(level, chunk);
            }
        }
    }

    /**
     * Drops the veins that are no longer there.
     *
     * The only source of scanning is the arrival of a whole chunk, and ordinary
     * mining of a block does not come with such a packet. Without this check a
     * mined-out vein would stay on the map as a marker until the end of the
     * session, and the player would dig towards it a second time. The
     * representative block of the vein is checked; if it is gone, the chunk is
     * queued for a rescan - the same check catches mining by another player on a
     * LAN server, and creepers and lava too.
     */
    private List<OreScanner.Vein> validate(ClientLevel level, List<OreScanner.Vein> veins) {
        List<OreScanner.Vein> alive = new ArrayList<>(veins.size());
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
        for (OreScanner.Vein vein : veins) {
            pos.set(vein.x, vein.y, vein.z);
            if (OreMap.targetOf(level.getBlockState(pos)) == vein.target) {
                alive.add(vein);
            } else {
                pending.add(new ChunkPos(vein.x >> 4, vein.z >> 4).pack());
            }
        }
        return alive;
    }
}
