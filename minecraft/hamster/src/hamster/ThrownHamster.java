package hamster;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.monster.Creeper;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.throwableitemprojectile.ThrowableItemProjectile;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.HitResult;

/**
 * A thrown hamster.
 *
 * Flies like a snowball, with two differences:
 *
 * 1. It hits a creeper - the creeper dies. The damage comes from the "thrown"
 *    source with the throwing player as the attacker, so the death counts as a
 *    normal kill: gunpowder drops, experience is awarded, advancements count.
 *    The creeper does NOT explode - an explosion comes from ignition only, not
 *    from death.
 *
 * 2. The hamster always survives. Wherever the projectile lands - on a creeper, on
 *    another mob, on a block - the animal appears at the point of impact unharmed
 *    and tamed by whoever threw it. The throw as such never costs the pet.
 *
 * No other creature takes damage from a hamster: it is a hamster, not a missile.
 */
public class ThrownHamster extends ThrowableItemProjectile {

    /** Well above the health of a creeper: a certain kill, no guessing. */
    private static final float LETHAL_MULTIPLIER = 2.0F;

    public ThrownHamster(EntityType<? extends ThrownHamster> type, Level level) {
        super(type, level);
    }

    public ThrownHamster(Level level, LivingEntity thrower, ItemStack stack) {
        super(HamsterMod.THROWN_HAMSTER, thrower, level, stack);
    }

    @Override
    protected Item getDefaultItem() {
        return HamsterMod.HAMSTER_ITEM;
    }

    @Override
    protected void onHitEntity(EntityHitResult result) {
        super.onHitEntity(result);
        Entity target = result.getEntity();
        if (!(target instanceof Creeper creeper)) {
            return;
        }
        // thrown(projectile, owner) is the same source the snowball uses. The player
        // becomes the attacker, so loot and experience drop as for a normal kill.
        creeper.hurt(this.damageSources().thrown(this, this.getOwner()),
                creeper.getMaxHealth() * LETHAL_MULTIPLIER);
    }

    @Override
    protected void onHit(HitResult result) {
        super.onHit(result);
        if (!(this.level() instanceof ServerLevel serverLevel)) {
            return;
        }
        releaseHamster(serverLevel, result);
        this.discard();
    }

    /** Releases the animal safe and sound at the point of impact. */
    private void releaseHamster(ServerLevel level, HitResult result) {
        Hamster hamster = HamsterMod.HAMSTER.create(level, EntitySpawnReason.TRIGGERED);
        if (hamster == null) {
            return;
        }
        hamster.snapTo(result.getLocation().x, result.getLocation().y, result.getLocation().z,
                this.getYRot(), 0.0F);
        hamster.setVariant(HamsterVariant.byId(
                this.getItem().getOrDefault(HamsterMod.HAMSTER_VARIANT, 0)));
        if (this.getOwner() instanceof Player player) {
            hamster.tame(player);
        }
        // A thrown pet must not despawn like a random animal from the plains.
        hamster.setPersistenceRequired();
        level.addFreshEntity(hamster);
        level.playSound(null, hamster.blockPosition(), SoundEvents.RABBIT_AMBIENT,
                SoundSource.NEUTRAL, 0.7F, 1.5F);
    }
}
