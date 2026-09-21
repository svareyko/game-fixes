package hamster.client;

import hamster.HamsterMod;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.rendering.v1.BlockEntityRendererRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.EntityRendererRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.ModelLayerRegistry;
import net.minecraft.client.model.geom.ModelLayerLocation;
import net.minecraft.client.renderer.entity.ThrownItemRenderer;

/**
 * The client part: model layers and renderers. Never loaded on a dedicated server -
 * it is a separate entry point in fabric.mod.json.
 */
public class HamsterClient implements ClientModInitializer {

    public static final ModelLayerLocation ADULT_LAYER =
            new ModelLayerLocation(HamsterMod.id("hamster"), "main");
    public static final ModelLayerLocation BABY_LAYER =
            new ModelLayerLocation(HamsterMod.id("hamster_baby"), "main");
    public static final ModelLayerLocation WHEEL_LAYER =
            new ModelLayerLocation(HamsterMod.id("hamster_wheel"), "main");

    @Override
    public void onInitializeClient() {
        ModelLayerRegistry.registerModelLayer(ADULT_LAYER, HamsterModel::createBodyLayer);
        ModelLayerRegistry.registerModelLayer(BABY_LAYER, HamsterModel::createBabyLayer);
        EntityRendererRegistry.register(HamsterMod.HAMSTER, HamsterRenderer::new);
        // A flying hamster is drawn with its own item icon - like a snowball.
        EntityRendererRegistry.register(HamsterMod.THROWN_HAMSTER, ThrownItemRenderer::new);

        ModelLayerRegistry.registerModelLayer(WHEEL_LAYER, HamsterWheelModel::createLayer);
        BlockEntityRendererRegistry.register(HamsterMod.HAMSTER_WHEEL_ENTITY, HamsterWheelRenderer::new);
    }
}
