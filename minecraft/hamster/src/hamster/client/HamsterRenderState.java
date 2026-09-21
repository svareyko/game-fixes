package hamster.client;

import hamster.HamsterVariant;
import net.minecraft.client.renderer.entity.state.LivingEntityRenderState;

/**
 * A snapshot of the hamster for rendering. In 26.x the renderer does not hold the
 * entity itself: data is first copied here and then drawn. So everything the
 * model and the texture choice need has to live in this class.
 */
public class HamsterRenderState extends LivingEntityRenderState {
    public HamsterVariant variant = HamsterVariant.GOLDEN;
    public boolean sitting;
    /** Running in a wheel: the legs move on the spot instead of following walkAnimationPos. */
    public boolean inWheel;
    public float ageInTicks;
}
