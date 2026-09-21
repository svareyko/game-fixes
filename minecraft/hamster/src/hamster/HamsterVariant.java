package hamster;

import net.minecraft.resources.Identifier;
import net.minecraft.util.RandomSource;

/**
 * Colour variant of a hamster. Stored in the synched entity data as a number, so
 * the order of the values must never change: hamsters that already live in a world
 * would change colour. New variants go at the end only.
 */
public enum HamsterVariant {
    GOLDEN("golden"),
    GREY("grey"),
    WHITE("white"),
    PANDA("panda"),
    BLACK("black");

    private static final HamsterVariant[] ALL = values();

    private final String id;
    private final Identifier texture;

    HamsterVariant(String id) {
        this.id = id;
        // The namespace is written as a literal instead of HamsterMod.MOD_ID on
        // purpose: otherwise loading this enum would pull in the HamsterMod class,
        // whose static initialisation registers things in the game registries.
        // The self-test (tools/SelfTest.java), which exercises the model without
        // starting Minecraft, would then fail: there the registries are frozen.
        this.texture = Identifier.fromNamespaceAndPath(
                "hamster", "textures/entity/hamster/" + id + ".png");
    }

    public String id() {
        return id;
    }

    public Identifier texture() {
        return texture;
    }

    public static int count() {
        return ALL.length;
    }

    /** Deliberately tolerant of any number: data on disk may come from another version. */
    public static HamsterVariant byId(int raw) {
        return ALL[Math.floorMod(raw, ALL.length)];
    }

    public static HamsterVariant random(RandomSource random) {
        return ALL[random.nextInt(ALL.length)];
    }
}
