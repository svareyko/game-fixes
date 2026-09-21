package hamster.client;

import com.mojang.blaze3d.vertex.PoseStack;
import hamster.HamsterMod;
import hamster.HamsterWheelBlock;
import hamster.HamsterWheelBlockEntity;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.client.renderer.blockentity.BlockEntityRendererProvider;
import net.minecraft.client.renderer.blockentity.state.BlockEntityRenderState;
import net.minecraft.client.renderer.feature.ModelFeatureRenderer;
import net.minecraft.client.renderer.state.level.CameraRenderState;
import net.minecraft.core.Direction;
import net.minecraft.resources.Identifier;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/**
 * Draws the spinning rim of the wheel. The static frame is an ordinary JSON block
 * model that the game draws itself; only what spins ends up here.
 *
 * The matrix is left alone: in 26.2 a block entity renderer receives it already
 * set up (the vanilla BellRenderer does not touch it either). The rotation for the
 * facing of the block and the spin of the rim are both done inside the model.
 */
public class HamsterWheelRenderer
        implements BlockEntityRenderer<HamsterWheelBlockEntity, HamsterWheelRenderState> {

    private static final Identifier TEXTURE =
            Identifier.fromNamespaceAndPath(HamsterMod.MOD_ID, "textures/entity/hamster_wheel.png");

    private static final int NO_OVERLAY = net.minecraft.client.renderer.texture.OverlayTexture.NO_OVERLAY;

    /**
     * The OUTLINE colour, NOT the colour of the model.
     *
     * The submitModel overload that takes a plain Identifier lays out its three ints
     * as light, overlay and - AFTER the sprite - the outline colour; the model colour
     * itself is hard-wired there as -1 (checked in the OrderedSubmitNodeCollector
     * bytecode). The first version passed -1 here, a white outline, and the wheel glowed
     * with a contour through walls, like an entity hit by a spectral arrow.
     * Zero means no outline; EntityRenderState.NO_OUTLINE is exactly that.
     */
    private static final int NO_OUTLINE = 0;

    private final HamsterWheelModel model;

    public HamsterWheelRenderer(BlockEntityRendererProvider.Context context) {
        this.model = new HamsterWheelModel(context.bakeLayer(HamsterClient.WHEEL_LAYER));
    }

    @Override
    public HamsterWheelRenderState createRenderState() {
        return new HamsterWheelRenderState();
    }

    @Override
    public void extractRenderState(HamsterWheelBlockEntity wheel, HamsterWheelRenderState state,
                                   float partialTick, Vec3 cameraPos,
                                   ModelFeatureRenderer.CrumblingOverlay crumbling) {
        BlockEntityRenderState.extractBase(wheel, state, crumbling);
        state.spinDegrees = wheel.spinDegrees(partialTick);
        BlockState block = wheel.getBlockState();
        state.facing = block.hasProperty(HamsterWheelBlock.FACING)
                ? block.getValue(HamsterWheelBlock.FACING)
                : Direction.NORTH;
    }

    @Override
    public void submit(HamsterWheelRenderState state, PoseStack poseStack,
                       SubmitNodeCollector collector, CameraRenderState cameraState) {
        this.model.setupAnim(state);
        collector.submitModel(this.model, state, poseStack, TEXTURE,
                state.lightCoords, NO_OVERLAY, NO_OUTLINE, state.breakProgress);
    }
}
