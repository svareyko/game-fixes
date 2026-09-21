package hamster.client;

import net.minecraft.core.Direction;
import net.minecraft.client.renderer.blockentity.state.BlockEntityRenderState;

public class HamsterWheelRenderState extends BlockEntityRenderState {
    public float spinDegrees;
    public Direction facing = Direction.NORTH;
}
