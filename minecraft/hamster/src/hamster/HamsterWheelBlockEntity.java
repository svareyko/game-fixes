package hamster;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Holds only the rotation angle of the rim, and only on the client.
 *
 * Nothing is saved to disk and nothing is synchronised: whether the wheel is
 * occupied lives in the block state, and the angle is purely decorative - starting
 * it from zero after coming back into the world costs nothing.
 */
public class HamsterWheelBlockEntity extends BlockEntity {

    /** Degrees per tick while the wheel is occupied. 18 is about one turn per second. */
    private static final float SPIN_PER_TICK = 18.0F;

    private float spin;
    private float spinPrev;

    public HamsterWheelBlockEntity(BlockPos pos, BlockState state) {
        super(HamsterMod.HAMSTER_WHEEL_ENTITY, pos, state);
    }

    public static void clientTick(Level level, BlockPos pos, BlockState state, HamsterWheelBlockEntity be) {
        be.spinPrev = be.spin;
        if (state.getValue(HamsterWheelBlock.OCCUPIED)) {
            be.spin += SPIN_PER_TICK;
            if (be.spin >= 360.0F) {
                be.spin -= 360.0F;
                be.spinPrev -= 360.0F;
            }
        }
    }

    /** The angle interpolated between ticks - otherwise the rotation stutters. */
    public float spinDegrees(float partialTick) {
        return spinPrev + (spin - spinPrev) * partialTick;
    }
}
