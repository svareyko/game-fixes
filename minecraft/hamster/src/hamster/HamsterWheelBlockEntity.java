package hamster;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

/**
 * The block entity of the wheel. Holds no data: nothing is saved to disk and nothing
 * is synchronised - whether the wheel is occupied lives in the block state.
 *
 * On the client it keeps the rotation angle of the rim. That angle is purely
 * decorative: starting it from zero after coming back into the world costs nothing.
 *
 * On the server it is the watchdog of the occupied flag, see {@link #serverTick}.
 */
public class HamsterWheelBlockEntity extends BlockEntity {

    /** Degrees per tick while the wheel is occupied. 18 is about one turn per second. */
    private static final float SPIN_PER_TICK = 18.0F;

    /** How often an occupied wheel looks for its hamster: once a second. */
    private static final long WATCH_INTERVAL = 20L;

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

    /**
     * Frees the wheel when its hamster is gone.
     *
     * UseWheelGoal clears the flag in stop(), and the game calls stop() only from the
     * goal selector of a living mob that is being ticked. A hamster that vanishes in the
     * middle of a run - picked up into the inventory, killed outright, unloaded with its
     * chunk, the world closed - never gets there. Up to 0.5.0 its wheel then stayed
     * occupied for good: comparator at 15, the rim spinning, no hamster could get in.
     *
     * So the wheel checks for itself. Once a second, while it is occupied, it looks for a
     * living hamster that claims exactly this wheel (Hamster.wheelPos), and clears the flag
     * when there is none. Flag 3 notifies the neighbours - the comparator - and the client.
     * The claim is not saved, so after a reload no hamster has one, and every occupied
     * wheel frees itself as soon as its chunk ticks: the wheels left stuck by 0.5.0 too.
     *
     * Not a hook in Entity.remove(): touching the world while a chunk is being unloaded is
     * asking for trouble, and the unload does not even go through remove() - the entity
     * manager calls the final setRemoved() directly.
     *
     * The ticker is attached to every wheel and returns at once unless the wheel is
     * occupied. A ticker that depends on the state, like the campfire's, would work too -
     * LevelChunk resolves the ticker again on chunk load and on every block state change -
     * but wheels are few, and one property read per tick is not worth a second moving part.
     */
    public static void serverTick(Level level, BlockPos pos, BlockState state, HamsterWheelBlockEntity be) {
        // The beacon throttles its own check the same way, with % 80. Every dimension reads
        // the game time of the overworld (DerivedLevelData), so this fires once a second everywhere.
        if (!state.getValue(HamsterWheelBlock.OCCUPIED) || level.getGameTime() % WATCH_INTERVAL != 0L) {
            return;
        }
        // On the tick it climbs in, the hamster is still up to REACH from the centre of the
        // block - it is pinned into the rim only from the next tick, and entities tick before
        // block entities. The block grown by REACH on every side reaches REACH + 0.5 from the
        // centre, so that hamster is inside. A neighbouring wheel's hamster may be inside too;
        // it claims its own wheel, not this one.
        AABB around = new AABB(pos).inflate(UseWheelGoal.REACH);
        boolean claimed = level.hasEntities(HamsterMod.HAMSTER, around,
                hamster -> hamster.isAlive() && pos.equals(hamster.getWheelPos()));
        if (!claimed) {
            level.setBlock(pos, state.setValue(HamsterWheelBlock.OCCUPIED, Boolean.FALSE), 3);
        }
    }

    /** The angle interpolated between ticks - otherwise the rotation stutters. */
    public float spinDegrees(float partialTick) {
        return spinPrev + (spin - spinPrev) * partialTick;
    }
}
