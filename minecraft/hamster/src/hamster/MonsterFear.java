package hamster;

import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.goal.AvoidEntityGoal;
import net.minecraft.world.entity.monster.skeleton.AbstractSkeleton;
import net.minecraft.world.entity.monster.zombie.Zombie;

/**
 * Zombies and skeletons are afraid of hamsters.
 *
 * Done without mixins: Fabric provides a server-side entity load event, and in it
 * the vanilla AvoidEntityGoal is simply added to the mob that was just created.
 * The behaviour of individual instances is changed, not the classes of the game -
 * so nothing breaks for other mods or for the game itself.
 *
 * Priority 1 is higher than the melee attack of both (theirs comes second). That is
 * deliberate: the point is that a hamster really drives them away, not that a zombie
 * backs off reluctantly while still hitting. Outside RADIUS the goal never triggers,
 * so the usual behaviour of monsters in the rest of the world does not change.
 *
 * Zombie also covers drowned, husks, zombie villagers and zombified piglins,
 * AbstractSkeleton covers strays, wither skeletons, bogged and parched: they all inherit from the two.
 */
public final class MonsterFear {

    private static final float RADIUS = 8.0F;
    private static final double WALK_SPEED = 1.0D;
    private static final double SPRINT_SPEED = 1.25D;

    private MonsterFear() {
    }

    public static void register() {
        ServerEntityEvents.ENTITY_LOAD.register((entity, level) -> {
            if (!(entity instanceof Zombie) && !(entity instanceof AbstractSkeleton)) {
                return;
            }
            PathfinderMob mob = (PathfinderMob) entity;
            // getGoalSelector() is public - no mixin, no access widener and no
            // reflection needed. The goalSelector field itself is protected.
            mob.getGoalSelector().addGoal(1, new AvoidEntityGoal<>(
                    mob, Hamster.class, RADIUS, WALK_SPEED, SPRINT_SPEED));
        });
    }
}
