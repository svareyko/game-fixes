import oremap.Gate;
import oremap.OreMap;
import oremap.OreScanner;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;

/**
 * A self-check of the mod's logic that does not start the game.
 *
 * It checks the two things everything rests on:
 *   1. address classification - the border between the local network and public
 *      servers; a mistake here means the X-ray quietly switching on where it must not;
 *   2. grouping blocks into veins - it decides whether a vein gets one marker or
 *      eight.
 *
 * Both parts are pure: they do not touch a running client, so they run under a
 * plain java with the game jar on the classpath.
 */
public class SelfTest {

    private static int failures;

    public static void main(String[] args) throws Exception {
        testAddresses();
        testClustering();
        testMarkerNames();
        if (failures > 0) {
            System.out.println("checks FAILED: " + failures);
            System.exit(1);
        }
        System.out.println("all checks passed");
    }

    // --- addresses -----------------------------------------------------------

    private static void testAddresses() throws Exception {
        Method hostOf = Gate.class.getDeclaredMethod("hostOf", String.class);
        Method isLocal = Gate.class.getDeclaredMethod("isLocalHost", String.class);
        hostOf.setAccessible(true);
        isLocal.setAccessible(true);

        // local - the mod has to work
        localYes(hostOf, isLocal, "192.168.0.10:25565", "192.168.0.10");
        localYes(hostOf, isLocal, "192.168.0.10", "192.168.0.10");
        localYes(hostOf, isLocal, "10.0.0.5", "10.0.0.5");
        localYes(hostOf, isLocal, "172.16.0.1", "172.16.0.1");
        localYes(hostOf, isLocal, "172.31.255.255", "172.31.255.255");
        localYes(hostOf, isLocal, "127.0.0.1:25565", "127.0.0.1");
        localYes(hostOf, isLocal, "localhost", "localhost");
        localYes(hostOf, isLocal, "MY-PC", "MY-PC");
        localYes(hostOf, isLocal, "my-pc:25565", "my-pc");
        localYes(hostOf, isLocal, "nas.local", "nas.local");
        localYes(hostOf, isLocal, "[::1]:25565", "::1");
        localYes(hostOf, isLocal, "fe80::1", "fe80::1");

        // public - the mod has to stay silent
        localNo(hostOf, isLocal, "mc.example.net:25565", "mc.example.net");
        localNo(hostOf, isLocal, "play.example.org", "play.example.org");
        localNo(hostOf, isLocal, "8.8.8.8", "8.8.8.8");
        localNo(hostOf, isLocal, "172.32.0.1", "172.32.0.1");     // right past the edge of 172.16/12
        localNo(hostOf, isLocal, "172.15.0.1", "172.15.0.1");     // right before it
        localNo(hostOf, isLocal, "11.0.0.1", "11.0.0.1");
        // the important case: an address that only STARTS like a local one
        localNo(hostOf, isLocal, "192.168.0.10.evil.com", "192.168.0.10.evil.com");
        localNo(hostOf, isLocal, "10.0.0.5.attacker.net", "10.0.0.5.attacker.net");
        localNo(hostOf, isLocal, "localhost.example.com", "localhost.example.com");
        localNo(hostOf, isLocal, "", "");
    }

    private static void localYes(Method hostOf, Method isLocal, String input, String host)
            throws Exception {
        check(input, hostOf, isLocal, host, true);
    }

    private static void localNo(Method hostOf, Method isLocal, String input, String host)
            throws Exception {
        check(input, hostOf, isLocal, host, false);
    }

    private static void check(String input, Method hostOf, Method isLocal,
                              String expectedHost, boolean expectedLocal) throws Exception {
        String actualHost = (String) hostOf.invoke(null, input);
        boolean actualLocal = (Boolean) isLocal.invoke(null, actualHost);
        boolean ok = actualHost.equals(expectedHost) && actualLocal == expectedLocal;
        if (!ok) {
            failures++;
            System.out.println("  FAIL  " + input
                    + " -> host=" + actualHost + " (expected " + expectedHost + ")"
                    + ", local=" + actualLocal + " (expected " + expectedLocal + ")");
        }
    }

    // --- marker names --------------------------------------------------------

    private static void testMarkerNames() {
        // The depth has to get into the name - it is what World Map draws next to the icon.
        name(OreMap.Target.DIAMOND, 1, -54, "Diamonds Y-54");
        name(OreMap.Target.DIAMOND, 8, -59, "Diamonds x8 Y-59");
        name(OreMap.Target.DEBRIS, 1, 15, "Netherite Y15");
        name(OreMap.Target.DEBRIS, 3, 8, "Netherite x3 Y8");
        // the edge levels of the world: 0 and the very bottom
        name(OreMap.Target.DIAMOND, 1, 0, "Diamonds Y0");
        name(OreMap.Target.DIAMOND, 2, -64, "Diamonds x2 Y-64");
    }

    private static void name(OreMap.Target target, int size, int y, String expected) {
        String actual = OreMap.markerName(target, size, y);
        if (!expected.equals(actual)) {
            failures++;
            System.out.println("  FAIL  marker name: got \"" + actual
                    + "\", expected \"" + expected + "\"");
        }
    }

    // --- grouping into veins -------------------------------------------------

    @SuppressWarnings("unchecked")
    private static void testClustering() throws Exception {
        Method cluster = OreScanner.class.getDeclaredMethod("cluster", List.class);
        cluster.setAccessible(true);

        int diamond = OreMap.Target.DIAMOND.ordinal();
        int debris = OreMap.Target.DEBRIS.ordinal();

        List<int[]> hits = new ArrayList<>();
        // a 2x2x2 diamond vein with its corner at (100,10,100) - has to give ONE marker of size 8
        for (int dx = 0; dx < 2; dx++) {
            for (int dy = 0; dy < 2; dy++) {
                for (int dz = 0; dz < 2; dz++) {
                    hits.add(new int[]{100 + dx, 10 + dy, 100 + dz, diamond});
                }
            }
        }
        // a lone diamond far away - a marker of its own
        hits.add(new int[]{200, 20, 200, diamond});
        // debris RIGHT NEXT to the diamond vein but in a cell of its own - another type,
        // so a marker of its own. Two blocks cannot share one position.
        hits.add(new int[]{102, 11, 101, debris});

        List<OreScanner.Vein> veins = (List<OreScanner.Vein>) cluster.invoke(null, hits);

        if (veins.size() != 3) {
            failures++;
            System.out.println("  FAIL  got " + veins.size() + " veins, expected 3");
            return;
        }
        OreScanner.Vein big = null;
        OreScanner.Vein lone = null;
        OreScanner.Vein neth = null;
        for (OreScanner.Vein v : veins) {
            if (v.target == OreMap.Target.DEBRIS) {
                neth = v;
            } else if (v.size == 8) {
                big = v;
            } else {
                lone = v;
            }
        }
        if (big == null || big.x != 100 || big.y != 10 || big.z != 100) {
            failures++;
            System.out.println("  FAIL  the 2x2x2 vein was not grouped or its representative is not in the corner: " + big);
        }
        if (lone == null || lone.size != 1 || lone.x != 200) {
            failures++;
            System.out.println("  FAIL  the single block was handled wrongly");
        }
        if (neth == null || neth.size != 1) {
            failures++;
            System.out.println("  FAIL  the debris was grouped with the diamond vein - types must not mix");
        }
        // the representative of a vein must not depend on the order of the input
        List<int[]> shuffled = new ArrayList<>(hits);
        java.util.Collections.reverse(shuffled);
        List<OreScanner.Vein> again = (List<OreScanner.Vein>) cluster.invoke(null, shuffled);
        OreScanner.Vein bigAgain = null;
        for (OreScanner.Vein v : again) {
            if (v.target == OreMap.Target.DIAMOND && v.size == 8) {
                bigAgain = v;
            }
        }
        if (bigAgain == null || big == null
                || bigAgain.x != big.x || bigAgain.y != big.y || bigAgain.z != big.z) {
            failures++;
            System.out.println("  FAIL  the representative of the vein depends on the order of the input");
        }
    }
}
