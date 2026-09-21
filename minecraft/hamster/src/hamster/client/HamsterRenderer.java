package hamster.client;

import hamster.Hamster;
import net.minecraft.client.renderer.entity.AgeableMobRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.Identifier;

public class HamsterRenderer extends AgeableMobRenderer<Hamster, HamsterRenderState, HamsterModel> {

    public HamsterRenderer(EntityRendererProvider.Context context) {
        super(context,
                new HamsterModel(context.bakeLayer(HamsterClient.ADULT_LAYER)),
                new HamsterModel(context.bakeLayer(HamsterClient.BABY_LAYER)),
                // The shadow does not inherit Attributes.SCALE: EntityRenderer copies
                // shadowRadius into the render state as is. So this is half of the
                // former 0.25 - to match the same 0.5 scale.
                0.125F);
    }

    @Override
    public HamsterRenderState createRenderState() {
        return new HamsterRenderState();
    }

    @Override
    public void extractRenderState(Hamster hamster, HamsterRenderState state, float partialTick) {
        super.extractRenderState(hamster, state, partialTick);
        state.variant = hamster.getVariant();
        state.sitting = hamster.isInSittingPose();
        state.inWheel = hamster.isInWheel();
        state.ageInTicks = hamster.tickCount + partialTick;
    }

    @Override
    public Identifier getTextureLocation(HamsterRenderState state) {
        return state.variant.texture();
    }
}
