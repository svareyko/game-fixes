package hamster;

import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.util.EnumSet;

/**
 * The "run in the wheel" goal.
 *
 * The hamster looks for a free wheel nearby, walks to it, climbs in and runs for
 * a set time. While it is inside, the block state of the wheel is marked occupied -
 * that is where both the comparator signal and the spinning rim on the client come from.
 *
 * The goal sets the flag on entering and clears it in stop(), but the game calls stop()
 * only from the goal selector of a living mob that is being ticked. A hamster that
 * vanishes in the middle of a run - picked up, killed outright, unloaded with its
 * chunk - never gets there. That case belongs to the wheel: the hamster claims the
 * wheel it runs in (Hamster.wheelPos), and the wheel frees itself when nobody claims it
 * (HamsterWheelBlockEntity.serverTick).
 *
 * The goal in turn trusts the block state, not its own memory: it checks on entering
 * that the wheel really is free, and it stops running as soon as the wheel no longer
 * says it is occupied.
 */
public class UseWheelGoal extends Goal {

    private static final int SEARCH_RADIUS = 8;
    private static final int SEARCH_HEIGHT = 3;
    /** How close to the centre of the wheel the hamster climbs in; the wheel's watchdog sizes its search by it. */
    static final double REACH = 1.4D;
    private static final int RUN_TICKS = 400;        // 20 seconds of running
    private static final int GIVE_UP_TICKS = 300;    // did not get there - give up
    private static final int COOLDOWN_TICKS = 600;   // then leave wheels alone; counted in canUse calls, about a minute

    private final Hamster hamster;
    private BlockPos target;
    private int cooldown;
    private int walkTicks;
    private int runTicks;
    private boolean inside;

    public UseWheelGoal(Hamster hamster) {
        this.hamster = hamster;
        this.setFlags(EnumSet.of(Goal.Flag.MOVE, Goal.Flag.JUMP, Goal.Flag.LOOK));
    }

    @Override
    public boolean canUse() {
        if (this.cooldown > 0) {
            this.cooldown--;
            return false;
        }
        if (this.hamster.isBaby() || this.hamster.isOrderedToSit() || this.hamster.isInWater()) {
            return false;
        }
        this.target = findFreeWheel();
        return this.target != null;
    }

    @Override
    public boolean canContinueToUse() {
        if (this.target == null || !isFreeOrOurs(this.target)) {
            return false;
        }
        return this.inside ? this.runTicks > 0 : this.walkTicks < GIVE_UP_TICKS;
    }

    @Override
    public void start() {
        this.walkTicks = 0;
        this.runTicks = RUN_TICKS;
        this.inside = false;
        this.hamster.getNavigation().moveTo(
                this.target.getX() + 0.5D, this.target.getY(), this.target.getZ() + 0.5D, 1.0D);
    }

    @Override
    public void tick() {
        if (this.target == null) {
            return;
        }
        if (!this.inside) {
            this.walkTicks++;
            if (this.hamster.distanceToSqr(this.target.getX() + 0.5D,
                    this.target.getY() + 0.5D, this.target.getZ() + 0.5D) <= REACH * REACH) {
                enter();
            } else if (this.hamster.getNavigation().isDone()) {
                this.hamster.getNavigation().moveTo(
                        this.target.getX() + 0.5D, this.target.getY(), this.target.getZ() + 0.5D, 1.0D);
            }
            return;
        }

        this.runTicks--;
        // Keep the hamster in the centre of the rim: the wheel does not carry it, it runs
        // on the spot. Height 0.19 is the inner edge of the rim: the wheel centre is at
        // 0.5 block, the inner radius is 5/16, so the track under its feet is at 0.5 - 0.31.
        this.hamster.setDeltaMovement(0.0D, 0.0D, 0.0D);
        this.hamster.setPos(this.target.getX() + 0.5D,
                this.target.getY() + 0.19D,
                this.target.getZ() + 0.5D);
        // The heading is re-applied every tick: otherwise any trifle knocks it off,
        // such as being pushed by another hamster.
        faceAlongWheel(this.hamster.level().getBlockState(this.target));
    }

    private void enter() {
        Level level = this.hamster.level();
        BlockState state = level.getBlockState(this.target);
        if (!state.is(HamsterMod.HAMSTER_WHEEL) || state.getValue(HamsterWheelBlock.OCCUPIED)) {
            this.target = null;
            return;
        }
        this.inside = true;
        this.hamster.getNavigation().stop();
        // The claim first, the block state second: the wheel frees itself when it is
        // occupied and nobody claims it, so by the time occupied=true can be seen, the
        // hamster must already say which wheel it is in.
        this.hamster.setWheelPos(this.target);
        this.hamster.setInWheel(true);
        faceAlongWheel(state);
        level.setBlock(this.target, state.setValue(HamsterWheelBlock.OCCUPIED, Boolean.TRUE), 3);
    }

    /**
     * Turns the hamster along the rim.
     *
     * FACING of the wheel is the side from which the FACE of the rim is seen, while
     * running on the rim goes across that: with facing=north the plane of the wheel
     * lies along the X axis, so the hamster has to look east or west. Hence +90 degrees.
     * Without it the hamster stands sideways to the motion and just looks like standing.
     */
    private void faceAlongWheel(BlockState state) {
        float yRot = state.getValue(HamsterWheelBlock.FACING).toYRot() + 90.0F;
        this.hamster.setYRot(yRot);
        this.hamster.yRotO = yRot;
        this.hamster.yBodyRot = yRot;
        this.hamster.yBodyRotO = yRot;
        this.hamster.setYHeadRot(yRot);
        this.hamster.yHeadRotO = yRot;
    }

    @Override
    public void stop() {
        if (this.inside && this.target != null) {
            Level level = this.hamster.level();
            BlockState state = level.getBlockState(this.target);
            if (state.is(HamsterMod.HAMSTER_WHEEL) && state.getValue(HamsterWheelBlock.OCCUPIED)) {
                level.setBlock(this.target, state.setValue(HamsterWheelBlock.OCCUPIED, Boolean.FALSE), 3);
            }
        }
        this.hamster.setWheelPos(null);
        this.hamster.setInWheel(false);
        this.hamster.getNavigation().stop();
        this.target = null;
        this.inside = false;
        this.cooldown = COOLDOWN_TICKS;
    }

    @Override
    public boolean requiresUpdateEveryTick() {
        return true;
    }

    /**
     * On the way the wheel has to be free; inside, it has to still say it is occupied. If
     * the flag was cleared under a running hamster - a debug stick, a command - the hamster
     * gets out instead of running in a wheel that another hamster may already be heading for.
     */
    private boolean isFreeOrOurs(BlockPos pos) {
        BlockState state = this.hamster.level().getBlockState(pos);
        if (!state.is(HamsterMod.HAMSTER_WHEEL)) {
            return false;
        }
        boolean occupied = state.getValue(HamsterWheelBlock.OCCUPIED);
        return this.inside ? occupied : !occupied;
    }

    private BlockPos findFreeWheel() {
        Level level = this.hamster.level();
        BlockPos origin = this.hamster.blockPosition();
        BlockPos best = null;
        double bestDist = Double.MAX_VALUE;
        for (BlockPos pos : BlockPos.betweenClosed(
                origin.offset(-SEARCH_RADIUS, -SEARCH_HEIGHT, -SEARCH_RADIUS),
                origin.offset(SEARCH_RADIUS, SEARCH_HEIGHT, SEARCH_RADIUS))) {
            BlockState state = level.getBlockState(pos);
            if (!state.is(HamsterMod.HAMSTER_WHEEL) || state.getValue(HamsterWheelBlock.OCCUPIED)) {
                continue;
            }
            double dist = this.hamster.distanceToSqr(pos.getX() + 0.5D, pos.getY() + 0.5D, pos.getZ() + 0.5D);
            if (dist < bestDist) {
                bestDist = dist;
                best = pos.immutable();
            }
        }
        return best;
    }
}
