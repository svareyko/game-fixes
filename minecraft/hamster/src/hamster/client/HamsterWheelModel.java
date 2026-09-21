package hamster.client;

import net.minecraft.client.model.Model;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.util.Mth;

/**
 * The spinning rim of the wheel. Drawn by a block entity renderer on top of the
 * static frame, which is an ordinary JSON block model.
 *
 * Two deliberate decisions:
 *
 * 1. The rim is SYMMETRIC about the centre of the block along all three axes. In
 *    26.2 a block entity renderer receives the matrix already set up (BellRenderer
 *    does not touch it at all), and the bytecode did not tell reliably which way
 *    the Y axis points in that space. A symmetric part with its pivot in the
 *    centre of the block sits correctly in either case - a flip along Y cannot be
 *    seen on a ring.
 *
 * 2. The rotation for the facing of the block is done INSIDE the model, by turning
 *    the root part around its pivot, not by transforming the PoseStack. That way
 *    there is no guessing which units the matrix works in: the pivot of the root
 *    is in the centre of the block anyway.
 */
public class HamsterWheelModel extends Model<HamsterWheelRenderState> {

    private static final int SEGMENTS = 8;
    private static final float RADIUS = 6.0F;

    private final ModelPart pivot;
    private final ModelPart wheel;

    public HamsterWheelModel(ModelPart root) {
        super(root, RenderTypes::entityCutout);
        // root here is the root of the baked mesh; our pivot node lies below it.
        this.pivot = root.getChild("pivot");
        this.wheel = this.pivot.getChild("wheel");
    }

    public static LayerDefinition createLayer() {
        MeshDefinition mesh = new MeshDefinition();
        // The root pivot is the centre of the block: 8/16 along every axis.
        PartDefinition pivot = mesh.getRoot()
                .addOrReplaceChild("pivot", CubeListBuilder.create(), PartPose.offset(8.0F, 8.0F, 8.0F));
        PartDefinition wheel = pivot.addOrReplaceChild("wheel", CubeListBuilder.create(), PartPose.ZERO);

        for (int i = 0; i < SEGMENTS; i++) {
            float angle = (float) (2.0 * Math.PI * i / SEGMENTS);
            // A tread segment: first moved up by the radius, then rotated around
            // the Z axis - that is how the ring is formed.
            wheel.addOrReplaceChild("segment_" + i,
                    CubeListBuilder.create().texOffs(0, 0)
                            .addBox(-2.5F, -RADIUS - 1.0F, -2.5F, 5, 2, 5),
                    PartPose.rotation(0.0F, 0.0F, angle));
            // A spoke towards the centre.
            wheel.addOrReplaceChild("spoke_" + i,
                    CubeListBuilder.create().texOffs(22, 0)
                            .addBox(-0.5F, -RADIUS, -0.5F, 1, 6, 1),
                    PartPose.rotation(0.0F, 0.0F, angle));
        }

        return LayerDefinition.create(mesh, 32, 16);
    }

    @Override
    public void setupAnim(HamsterWheelRenderState state) {
        this.resetPose();
        this.pivot.yRot = -state.facing.toYRot() * Mth.DEG_TO_RAD;
        this.wheel.zRot = state.spinDegrees * Mth.DEG_TO_RAD;
    }
}
