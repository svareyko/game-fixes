package oremap;

import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ServerData;

import java.util.Locale;

/**
 * Where the mod is allowed to work.
 *
 * It is made for single-player worlds and for a server that runs at home and is
 * reached over the local network. On public servers a mod like this counts as
 * an X-ray cheat, so there it silently switches itself off.
 *
 * The check is an allow-list, not a block-list: not "forbid the known bad
 * addresses" but "allow only what is certainly local". Whatever is not
 * recognised as local counts as public.
 */
public final class Gate {

    /** The result of the last check - so that the log gets one line, not one per tick. */
    private static Boolean lastVerdict;
    private static String lastReason = "";

    public static boolean allowed(Minecraft mc) {
        boolean verdict = compute(mc);
        if (lastVerdict == null || lastVerdict != verdict) {
            lastVerdict = verdict;
            System.out.println("[" + OreMap.MOD_ID + "] "
                    + (verdict ? "enabled: " : "disabled: ") + lastReason);
        }
        return verdict;
    }

    /** A human-readable verdict for the /oremap status command. */
    public static String describe(Minecraft mc) {
        boolean verdict = allowed(mc);
        return (verdict ? "allowed" : "NOT ALLOWED") + " — " + lastReason;
    }

    /** Reset when the world is left, so that the verdict is computed and logged again. */
    public static void reset() {
        lastVerdict = null;
        lastReason = "";
    }

    private static boolean compute(Minecraft mc) {
        // Single player, "Open to LAN" included - the server is run by this very client.
        if (mc.hasSingleplayerServer()) {
            lastReason = "single-player world (integrated server)";
            return true;
        }
        ServerData server = mc.getCurrentServer();
        if (server == null) {
            lastReason = "the server is unknown";
            return false;
        }
        // A server found by the automatic LAN discovery.
        if (server.isLan()) {
            lastReason = "the server was discovered on the local network";
            return true;
        }
        if (server.isRealm()) {
            lastReason = "Realms is a public server";
            return false;
        }
        String host = hostOf(server.ip);
        if (isLocalHost(host)) {
            lastReason = "local address " + host;
            return true;
        }
        lastReason = "public server " + host + " - ore is not shown";
        return false;
    }

    /** Strips the port and the IPv6 brackets: "192.168.0.10:25565" -> "192.168.0.10". */
    static String hostOf(String ip) {
        if (ip == null) {
            return "";
        }
        String s = ip.trim();
        if (s.startsWith("[")) {                      // [::1]:25565
            int close = s.indexOf(']');
            return close > 0 ? s.substring(1, close) : s.substring(1);
        }
        int colon = s.indexOf(':');
        if (colon >= 0 && s.indexOf(':', colon + 1) < 0) {   // exactly one colon - it is the port
            s = s.substring(0, colon);
        }
        return s;
    }

    /**
     * Whether the address is local. The name is deliberately NOT resolved: a DNS
     * answer can change, and quietly switching on at a public server because of
     * an accidental resolution is not acceptable.
     */
    static boolean isLocalHost(String host) {
        if (host == null || host.isEmpty()) {
            return false;
        }
        String h = host.toLowerCase(Locale.ROOT);

        if (h.equals("localhost") || h.equals("::1") || h.equals("0:0:0:0:0:0:0:1")) {
            return true;
        }
        // Home suffixes handed out by routers and mDNS.
        if (h.endsWith(".local") || h.endsWith(".lan") || h.endsWith(".home")
                || h.endsWith(".internal") || h.endsWith(".localdomain")) {
            return true;
        }
        // A bare machine name without dots is always a name on the local network (MY-PC and the like).
        if (h.indexOf('.') < 0 && h.indexOf(':') < 0) {
            return true;
        }
        if (isPrivateIPv4(h)) {
            return true;
        }
        return isPrivateIPv6(h);
    }

    static boolean isPrivateIPv4(String h) {
        String[] parts = h.split("\\.");
        if (parts.length != 4) {
            return false;
        }
        int[] o = new int[4];
        for (int i = 0; i < 4; i++) {
            try {
                o[i] = Integer.parseInt(parts[i]);
            } catch (NumberFormatException e) {
                return false;
            }
            if (o[i] < 0 || o[i] > 255) {
                return false;
            }
        }
        if (o[0] == 10) {                                   // 10.0.0.0/8
            return true;
        }
        if (o[0] == 127) {                                  // 127.0.0.0/8
            return true;
        }
        if (o[0] == 192 && o[1] == 168) {                   // 192.168.0.0/16
            return true;
        }
        if (o[0] == 172 && o[1] >= 16 && o[1] <= 31) {      // 172.16.0.0/12
            return true;
        }
        if (o[0] == 169 && o[1] == 254) {                   // 169.254.0.0/16, link-local
            return true;
        }
        return false;
    }

    static boolean isPrivateIPv6(String h) {
        if (h.indexOf(':') < 0) {
            return false;
        }
        // fc00::/7 - unique local, fe80::/10 - link-local
        return h.startsWith("fc") || h.startsWith("fd") || h.startsWith("fe8")
                || h.startsWith("fe9") || h.startsWith("fea") || h.startsWith("feb");
    }

    private Gate() {
    }
}
