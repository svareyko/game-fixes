package hamster.client;

import net.minecraft.client.model.EntityModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.MeshTransformer;
import net.minecraft.client.model.geom.builders.PartDefinition;
import net.minecraft.util.Mth;

/**
 * The hamster model. Ten boxes, a 64x32 texture.
 *
 * Model coordinate system: the Y axis points DOWN, zero of the root part is on the
 * ground under the mob. That is why the whole body uses negative Y. The UV layout
 * matches the texture generator tools/textures.py one to one: change one - change
 * the other too, or the texture will slide across the faces.
 *
 * The animations are not copied from the rabbit or another small vanilla mob but
 * kept simple: the legs swing like a pendulum driven by walkAnimationPos, the head
 * turns after the player, and in the sitting pose the rear is lowered.
 */
public class HamsterModel extends EntityModel<HamsterRenderState> {

    private static final float BABY_SCALE = 0.65F;

    private final ModelPart head;
    private final ModelPart legFrontLeft;
    private final ModelPart legFrontRight;
    private final ModelPart legBackLeft;
    private final ModelPart legBackRight;
    private final ModelPart body;

    public HamsterModel(ModelPart root) {
        super(root);
        this.body = root.getChild("body");
        this.head = root.getChild("head");
        this.legFrontLeft = root.getChild("leg_front_left");
        this.legFrontRight = root.getChild("leg_front_right");
        this.legBackLeft = root.getChild("leg_back_left");
        this.legBackRight = root.getChild("leg_back_right");
    }

    public static LayerDefinition createBodyLayer() {
        MeshDefinition mesh = new MeshDefinition();
        PartDefinition root = mesh.getRoot();

        root.addOrReplaceChild("body",
                CubeListBuilder.create()
                        .texOffs(0, 0).addBox(-3.5F, -6.0F, -1.0F, 7, 5, 7)
                        .texOffs(10, 13).addBox(-0.5F, -4.5F, 6.0F, 1, 1, 1),
                PartPose.offset(0.0F, 24.0F, 0.0F));

        // The head turns around the neck, so its pivot sits at its rear bottom edge.
        root.addOrReplaceChild("head",
                CubeListBuilder.create()
                        .texOffs(28, 0).addBox(-3.0F, -1.0F, -5.0F, 6, 5, 5)
                        .texOffs(50, 0).addBox(-1.5F, 1.5F, -6.0F, 3, 2, 1)
                        .texOffs(50, 4).addBox(-2.5F, -2.5F, -4.6F, 2, 2, 1)
                        .texOffs(50, 4).addBox(0.5F, -2.5F, -4.6F, 2, 2, 1),
                PartPose.offset(0.0F, 18.5F, -1.0F));

        CubeListBuilder leg = CubeListBuilder.create()
                .texOffs(0, 13).addBox(-1.0F, 0.0F, -1.0F, 2, 1, 2);
        root.addOrReplaceChild("leg_front_left", leg, PartPose.offset(-2.5F, 23.0F, 0.0F));
        root.addOrReplaceChild("leg_front_right", leg, PartPose.offset(2.5F, 23.0F, 0.0F));
        root.addOrReplaceChild("leg_back_left", leg, PartPose.offset(-2.5F, 23.0F, 5.0F));
        root.addOrReplaceChild("leg_back_right", leg, PartPose.offset(2.5F, 23.0F, 5.0F));

        return LayerDefinition.create(mesh, 64, 32);
    }

    /** The baby is the same mesh scaled down: no need to draw a separate one. */
    public static LayerDefinition createBabyLayer() {
        return createBodyLayer().apply(MeshTransformer.scaling(BABY_SCALE));
    }

    @Override
    public void setupAnim(HamsterRenderState state) {
        this.resetPose();

        if (state.inWheel) {
            // In the wheel the hamster runs on the spot: the phase comes from time, not
            // from distance walked - there is no distance, walkAnimationSpeed is zero.
            float phase = state.ageInTicks * 1.1F;
            float swing = Mth.cos(phase) * 1.45F;
            this.legFrontLeft.xRot = swing;
            this.legFrontRight.xRot = -swing;
            this.legBackLeft.xRot = -swing;
            this.legBackRight.xRot = swing;
            // A forward lean and a bouncing body: on an animal a quarter of a block in
            // size the legs alone cannot be seen, the run reads from the body.
            this.body.xRot = -0.22F;
            this.body.y += Mth.abs(Mth.sin(phase)) * 0.6F;
            this.head.y += Mth.abs(Mth.sin(phase)) * 0.4F;
            return;
        }

        if (state.sitting) {
            // Sitting: rear on the ground, front legs stretched out, head higher.
            this.body.xRot = -0.35F;
            this.body.y += 1.0F;
            this.head.y -= 0.5F;
            this.legBackLeft.xRot = -1.2F;
            this.legBackRight.xRot = -1.2F;
            return;
        }

        this.head.yRot = state.yRot * Mth.DEG_TO_RAD;
        this.head.xRot = state.xRot * Mth.DEG_TO_RAD;

        // The legs swing like a pendulum. The amplitude is small: a hamster has short
        // legs, a wide swing would look like a horse.
        float swing = Mth.cos(state.walkAnimationPos * 1.4F) * 0.9F * state.walkAnimationSpeed;
        this.legFrontLeft.xRot = swing;
        this.legFrontRight.xRot = -swing;
        this.legBackLeft.xRot = -swing;
        this.legBackRight.xRot = swing;

        // A slight bob of the body while running - otherwise the gait looks like sliding.
        this.body.y += Mth.abs(Mth.sin(state.walkAnimationPos * 1.4F)) * 0.3F * state.walkAnimationSpeed;
    }
}
