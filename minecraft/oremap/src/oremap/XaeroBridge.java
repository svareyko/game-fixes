package oremap;

import net.minecraft.client.Minecraft;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;

import xaero.common.minimap.waypoints.Waypoint;
import xaero.hud.minimap.BuiltInHudModules;
import xaero.hud.minimap.module.MinimapSession;
import xaero.hud.minimap.waypoint.WaypointColor;
import xaero.hud.minimap.waypoint.WaypointVisibilityType;
import xaero.hud.minimap.waypoint.thirdparty.ThirdPartyWaypointManager;
import xaero.hud.minimap.waypoint.thirdparty.ThirdPartyWaypoints;
import xaero.hud.minimap.world.MinimapDimensionHelper;
import xaero.hud.minimap.world.container.MinimapWorldContainer;
import xaero.hud.minimap.world.container.MinimapWorldRootContainer;
import xaero.hud.path.XaeroPath;

import java.util.List;

/**
 * The only place where the mod touches Xaero.
 *
 * Xaero has no public API, but it has a subsystem of third-party waypoints
 * (xaero.hud.minimap.waypoint.thirdparty) that it uses itself for Waystones
 * compatibility. Waypoints in it live in memory only, and every source has an
 * Identifier of its own.
 *
 * Since there is no contract, everything is wrapped in try/catch(Throwable): on
 * a mismatch with a future Xaero version the mod has to switch itself off, not
 * crash the game. On top of that fabric.mod.json names the minimap version the
 * mod was written against (as "recommends", so it never blocks the game).
 */
public final class XaeroBridge {

    private static final Identifier ORIGIN_DIAMOND =
            Identifier.fromNamespaceAndPath(OreMap.MOD_ID, "diamond");
    private static final Identifier ORIGIN_DEBRIS =
            Identifier.fromNamespaceAndPath(OreMap.MOD_ID, "ancient_debris");

    /** Set on the very first error: from then on the mod stays silent until the game is restarted. */
    private static boolean broken;

    public static boolean isBroken() {
        return broken;
    }

    private static Identifier originOf(OreMap.Target target) {
        return target == OreMap.Target.DIAMOND ? ORIGIN_DIAMOND : ORIGIN_DEBRIS;
    }

    private static WaypointColor colorOf(OreMap.Target target) {
        return target == OreMap.Target.DIAMOND ? WaypointColor.AQUA : WaypointColor.DARK_RED;
    }

    /**
     * Replaces the whole waypoint set of one type.
     *
     * A replacement, not point edits: ThirdPartyWaypoints.remove(String) saves
     * Xaero's config to disk on every call (verified in the bytecode), and add()
     * calls remove() itself when the waypoint is already registered. So the only
     * cheap way is clearOrigin() (pure in-memory work) and putting everything back.
     */
    public static void replaceAll(Minecraft mc, OreMap.Target target,
                                  List<OreScanner.Vein> veins) {
        if (broken) {
            return;
        }
        try {
            ThirdPartyWaypointManager manager = managerFor(mc);
            if (manager == null) {
                return;
            }
            Identifier origin = originOf(target);
            manager.clearOrigin(origin);

            ThirdPartyWaypoints waypoints = manager.get(origin);
            if (waypoints == null) {
                return;
            }
            // The switch is handed to Xaero the way it does it for Waystones itself:
            // then the key turns off both the markers on the map and the lines in
            // the waypoint list. It has to be checked every time: the object is
            // created anew together with the session.
            if (!waypoints.hasEnabledStateGetter()) {
                waypoints.setEnabledStateGetter(() -> OreMap.markersVisible);
            }

            WaypointColor color = colorOf(target);
            int rank = 0;
            for (OreScanner.Vein vein : veins) {
                // World Map draws the name as a caption next to the icon (WaypointRenderer
                // calls both getSymbol and getName), so the depth goes right here.
                String name = OreMap.markerName(target, vein.size, vein.y);
                Waypoint waypoint = new Waypoint(vein.x, vein.y, vein.z,
                        name, target.initials, color);
                // WORLD_MAP_LOCAL - the waypoint is visible on the world map but does
                // not clutter the minimap and does not become a beacon in the middle
                // of the screen.
                waypoint.setVisibility(WaypointVisibilityType.WORLD_MAP_LOCAL);
                // The identifier is the position in the list, NOT the coordinates.
                // The reason is in Xaero's bytecode: add() puts an entry into
                // renderInfoOverrides, clear() does not touch that map, and RootConfigIO
                // saves it into the config.txt of the world. With coordinate-based ids
                // every new vein would add a line to the file for good - it would grow
                // by megabytes per session. The position in the list keeps the set of
                // identifiers bounded by the number of markers.
                waypoints.add(Integer.toString(rank++), waypoint);
            }
        } catch (Throwable t) {
            fail(t);
        }
    }

    /** Removes all waypoints of the mod. Called when the markers are switched off and when the gate forbids working here. */
    public static void clearAll(Minecraft mc) {
        if (broken) {
            return;
        }
        try {
            ThirdPartyWaypointManager manager = managerFor(mc);
            if (manager == null) {
                return;
            }
            manager.clearOrigin(ORIGIN_DIAMOND);
            manager.clearOrigin(ORIGIN_DEBRIS);
        } catch (Throwable t) {
            fail(t);
        }
    }

    /**
     * The third-party waypoint manager of the current dimension.
     *
     * Xaero's session is created anew for every connection and world change, and
     * third-party waypoints live in memory only - so the container is fetched again
     * every time, and the mod puts the whole waypoint set back.
     */
    private static ThirdPartyWaypointManager managerFor(Minecraft mc) {
        if (!mc.isSameThread() || mc.level == null) {
            return null;
        }
        MinimapSession session = BuiltInHudModules.MINIMAP.getCurrentSession();
        if (session == null) {
            return null;
        }
        MinimapWorldRootContainer root = session.getWorldManager().getAutoRootContainer();
        if (root == null) {
            return null;
        }
        ResourceKey<Level> dimension = mc.level.dimension();
        MinimapDimensionHelper helper = session.getDimensionHelper();
        XaeroPath path = root.getPath().resolve(helper.getDimensionDirectoryName(dimension));
        MinimapWorldContainer container = root.addSubContainer(path);
        if (container == null) {
            return null;
        }
        return container.getThirdPartyWaypointManager();
    }

    private static void fail(Throwable t) {
        broken = true;
        System.out.println("[" + OreMap.MOD_ID + "] could not hand the markers to Xaero, "
                + "the mod is switched off until the game is restarted. Most likely the minimap "
                + "was updated and its internal classes moved.");
        t.printStackTrace();
    }

    private XaeroBridge() {
    }
}
