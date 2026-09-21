package metaltorch;

import net.minecraft.resources.Identifier;

/**
 * The metal added to a torch.
 *
 * The colour belongs to the sparks and to the torch itself, NOT to the light.
 * Light in Minecraft has no colour: a block only has a brightness of 0..15. The
 * vanilla torch gives 14, a metal torch 15 - the engine's ceiling, nothing above.
 *
 * The values may be reordered freely: names leave this class, not ordinals.
 */
public enum MetalTorch {

    /**
     * Iron - almost white, with a barely noticeable cold tint.
     *
     * Copper is deliberately NOT here: 26.2 already has a vanilla Copper Torch
     * (light 14, copper nugget + coal + stick). One of our own would put two items
     * with the same name into the recipe book, a single light level apart.
     */
    IRON("iron", 0xF0F4F8, "minecraft:iron_ingot"),

    /** Gold - a rich warm yellow. */
    GOLD("gold", 0xFFD24A, "minecraft:gold_ingot");

    private final String id;
    private final int colour;
    private final String ingredient;

    MetalTorch(String id, int colour, String ingredient) {
        this.id = id;
        this.colour = colour;
        this.ingredient = ingredient;
    }

    public String id() {
        return id;
    }

    /** Packed RGB: it tints the sparks and the texture. */
    public int colour() {
        return colour;
    }

    public String ingredient() {
        return ingredient;
    }

    public String standingName() {
        return id + "_torch";
    }

    public String wallName() {
        return id + "_wall_torch";
    }

    public Identifier standingId() {
        return MetalTorchMod.id(standingName());
    }

    public Identifier wallId() {
        return MetalTorchMod.id(wallName());
    }
}
