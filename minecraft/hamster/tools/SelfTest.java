import hamster.HamsterVariant;
import hamster.client.HamsterModel;
import hamster.client.HamsterRenderState;
import hamster.client.HamsterWheelModel;
import hamster.client.HamsterWheelRenderState;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.builders.LayerDefinition;

import java.util.List;

/**
 * A self-test of the models that runs without starting the game.
 *
 * It catches exactly what the compiler lets through and the game answers with a
 * crash the very first time a hamster comes into view: a typo in the name of a
 * model part. getChild throws at run time, and without this test the only way to
 * learn about it would be the log of a crashed game.
 *
 * It works because baking a model is pure work on data: neither OpenGL nor a
 * running game is involved. For the same reason hamster.HamsterMod must NOT be
 * touched here: its static initialisation registers things in the game registries.
 */
public class SelfTest {

    private static int failures = 0;

    private static void check(boolean ok, String what) {
        System.out.println((ok ? "  ok   " : "  FAIL ") + what);
        if (!ok) {
            failures++;
        }
    }

    public static void main(String[] args) {
        // The wheel model pulls in RenderTypes, and that one pulls in the game
        // registries. The vanilla tests bring them up in exactly this way. The
        // hamster model does not need it, but it does no harm either: the mod is
        // still NOT registered here, hamster.HamsterMod still must not be touched.
        try {
            net.minecraft.SharedConstants.tryDetectVersion();
            net.minecraft.server.Bootstrap.bootStrap();
            check(true, "game registries bootstrapped");
        } catch (Throwable e) {
            check(false, "could not bootstrap the registries: " + e);
        }

        for (String which : new String[]{"adult", "baby"}) {
            LayerDefinition layer = which.equals("adult")
                    ? HamsterModel.createBodyLayer()
                    : HamsterModel.createBabyLayer();
            ModelPart root;
            HamsterModel model;
            try {
                root = layer.bakeRoot();
                model = new HamsterModel(root);      // this is where typos in getChild surface
            } catch (RuntimeException e) {
                check(false, which + ": the model could not be built - " + e);
                continue;
            }

            for (String part : new String[]{"body", "head",
                    "leg_front_left", "leg_front_right", "leg_back_left", "leg_back_right"}) {
                boolean present;
                try {
                    present = root.getChild(part) != null;
                } catch (RuntimeException e) {
                    present = false;
                }
                check(present, which + ": part " + part);
            }

            List<ModelPart> all = root.getAllParts();
            check(all.size() >= 7, which + ": parts in the model " + all.size() + " (at least 7 expected)");

            // Both poses have to pass without exceptions: in the game setupAnim is
            // called every frame, and a failure here would mean a black screen.
            HamsterRenderState state = new HamsterRenderState();
            state.walkAnimationPos = 3.0F;
            state.walkAnimationSpeed = 1.0F;
            state.yRot = 25.0F;
            state.xRot = -10.0F;
            try {
                model.setupAnim(state);
                state.sitting = true;
                model.setupAnim(state);
                check(true, which + ": the running animation and the sitting pose ran");
            } catch (RuntimeException e) {
                check(false, which + ": setupAnim failed - " + e);
            }
        }

        // The wheel: the same check as for the hamster. A typo in a part name here
        // would crash the client at the first glance at a placed block.
        try {
            ModelPart wheelRoot = HamsterWheelModel.createLayer().bakeRoot();
            HamsterWheelModel wheelModel = new HamsterWheelModel(wheelRoot);
            ModelPart pivot = wheelRoot.getChild("pivot");
            ModelPart wheel = pivot.getChild("wheel");
            check(wheel.getAllParts().size() >= 16,
                    "wheel: parts of the rim " + wheel.getAllParts().size() + " (at least 16 expected)");
            HamsterWheelRenderState wheelState = new HamsterWheelRenderState();
            wheelState.spinDegrees = 123.0F;
            wheelState.facing = net.minecraft.core.Direction.EAST;
            wheelModel.setupAnim(wheelState);
            check(true, "wheel: the model was built and the animation ran");
        } catch (RuntimeException e) {
            check(false, "wheel: " + e);
        }

        check(HamsterVariant.count() == HamsterVariant.values().length, "the variant counter matches");
        for (HamsterVariant v : HamsterVariant.values()) {
            String path = v.texture().getPath();
            check(path.equals("textures/entity/hamster/" + v.id() + ".png")
                            && v.texture().getNamespace().equals("hamster"),
                    "texture path of the variant " + v.id());
        }

        if (failures > 0) {
            System.out.println("  failures: " + failures);
            System.exit(1);
        }
        System.out.println("  self-test passed");
    }
}
