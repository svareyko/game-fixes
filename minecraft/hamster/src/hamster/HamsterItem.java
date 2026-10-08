package hamster;

import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.level.Level;

/**
 * A hamster carried in the inventory.
 *
 * Not the whole animal is stored, only the colour variant - one number in the
 * {@link HamsterMod#HAMSTER_VARIANT} component. Serialising the entire entity is
 * possible, but in 26.x that means ValueInput/ValueOutput and fiddling with tags,
 * while a pocket pet needs just the colour: the name travels with the item and the
 * owner is set on release - whoever releases the hamster becomes its owner.
 *
 * Only YOUR OWN tamed hamster can be picked up, and only while sneaking, see
 * {@link Hamster#mobInteract}: otherwise a plain right click on a pet, which is
 * supposed to make it sit, would put it into the pocket instead.
 */
public class HamsterItem extends Item {

    /** Same as the snowball: the same speed and the same spread. */
    private static final float THROW_POWER = 1.5F;
    private static final float THROW_INACCURACY = 1.0F;

    public HamsterItem(Properties properties) {
        super(properties);
    }

    /** Puts the hamster into a stack: the colour and the name survive the pocket. */
    public static ItemStack of(Hamster hamster) {
        ItemStack stack = new ItemStack(HamsterMod.HAMSTER_ITEM);
        stack.set(HamsterMod.HAMSTER_VARIANT, hamster.getVariant().ordinal());
        if (hamster.hasCustomName()) {
            stack.set(DataComponents.CUSTOM_NAME, hamster.getCustomName());
        }
        return stack;
    }

    /**
     * The reverse of {@link #of}: gives a freshly created hamster what the stack carried -
     * the colour and the name.
     *
     * Both ways out of the pocket go through here: put down on a block (useOn) and thrown
     * (ThrownHamster). Up to 0.5.0 each of them unpacked the stack by itself, and the throw
     * forgot the name.
     */
    static void applyStack(ItemStack stack, Hamster hamster) {
        hamster.setVariant(HamsterVariant.byId(stack.getOrDefault(HamsterMod.HAMSTER_VARIANT, 0)));
        Component name = stack.get(DataComponents.CUSTOM_NAME);
        if (name != null) {
            hamster.setCustomName(name);
        }
    }

    /**
     * Throwing.
     *
     * A right click on a block calls useOn and releases the hamster; when there is
     * no block under the crosshair the game calls use, and the hamster flies. The
     * split is vanilla, nothing had to be invented.
     */
    @Override
    public InteractionResult use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        level.playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.SNOWBALL_THROW, SoundSource.NEUTRAL, 0.5F,
                0.4F / (level.getRandom().nextFloat() * 0.4F + 0.8F));
        if (level instanceof ServerLevel serverLevel) {
            Projectile.spawnProjectileFromRotation(
                    (lvl, thrower, itemStack) -> new ThrownHamster(lvl, thrower, itemStack),
                    serverLevel, stack, player, 0.0F, THROW_POWER, THROW_INACCURACY);
        }
        if (!player.getAbilities().instabuild) {
            stack.shrink(1);
        }
        return InteractionResult.SUCCESS;
    }

    @Override
    public InteractionResult useOn(UseOnContext context) {
        Level level = context.getLevel();
        if (!(level instanceof ServerLevel serverLevel)) {
            return InteractionResult.SUCCESS;
        }
        // Placed against the clicked face, otherwise the hamster ends up inside the block.
        BlockPos pos = context.getClickedPos().relative(context.getClickedFace());
        Hamster hamster = HamsterMod.HAMSTER.spawn(serverLevel, pos, EntitySpawnReason.SPAWN_ITEM_USE);
        if (hamster == null) {
            return InteractionResult.FAIL;
        }

        ItemStack stack = context.getItemInHand();
        applyStack(stack, hamster);

        Player player = context.getPlayer();
        if (player != null) {
            hamster.tame(player);
            // Out of the pocket the hamster is up and about, not sitting: sitting is a separate gesture.
            hamster.setOrderedToSit(false);
            if (!player.getAbilities().instabuild) {
                stack.shrink(1);
            }
        }
        // Must not despawn: it is a pet, not a random animal from the plains.
        hamster.setPersistenceRequired();
        level.playSound(null, pos, SoundEvents.RABBIT_AMBIENT, SoundSource.NEUTRAL, 0.6F, 1.4F);
        return InteractionResult.SUCCESS;
    }
}
