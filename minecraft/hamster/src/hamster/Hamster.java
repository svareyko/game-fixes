package hamster;

import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.chat.Component;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.AgeableMob;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.SpawnGroupData;
import net.minecraft.world.entity.TamableAnimal;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.BreedGoal;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.FollowOwnerGoal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.PanicGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.SitWhenOrderedToGoal;
import net.minecraft.world.entity.ai.goal.TemptGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomStrollGoal;
import net.minecraft.world.entity.animal.Animal;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.ServerLevelAccessor;
import net.minecraft.world.level.storage.ValueInput;
import net.minecraft.world.level.storage.ValueOutput;

/**
 * The hamster: tamed with seeds, bred with the same seeds, follows its owner
 * and sits on command.
 *
 * Modelled on the vanilla cat and wolf - in 26.x the game ships unobfuscated, so
 * {@code net.minecraft.world.entity.TamableAnimal} reads like source code.
 * Only the setup is our own: the set of goals, the food and the colour variant.
 */
public class Hamster extends TamableAnimal {

    /** Chance to tame per attempt - like the ocelot, so that it is not instant. */
    private static final int TAME_CHANCE_IN = 3;

    private static final EntityDataAccessor<Integer> DATA_VARIANT =
            SynchedEntityData.defineId(Hamster.class, EntityDataSerializers.INT);

    /** Whether it runs in a wheel. The client needs it: this flag makes the model move its legs. */
    private static final EntityDataAccessor<Boolean> DATA_IN_WHEEL =
            SynchedEntityData.defineId(Hamster.class, EntityDataSerializers.BOOLEAN);

    public Hamster(EntityType<? extends Hamster> type, Level level) {
        super(type, level);
    }

    /**
     * The size is set by an attribute, not by the model geometry: Attributes.SCALE
     * (range 0.0625..16) multiplies both the rendering and the hitbox at once -
     * LivingEntity.getScale() reads exactly this attribute. Editing the boxes of
     * the model could not do that: their sizes are whole texture pixels, and half
     * values would wreck the UV layout.
     *
     * At 0.5 the hitbox comes out as 0.25 x 0.2 blocks. The shadow does NOT inherit
     * the scale - EntityRenderer copies shadowRadius into the render state as is,
     * so it is reduced separately, in HamsterRenderer.
     */
    private static final double SCALE = 0.5D;

    public static AttributeSupplier.Builder createAttributes() {
        return Animal.createAnimalAttributes()
                .add(Attributes.MAX_HEALTH, 6.0D)
                .add(Attributes.MOVEMENT_SPEED, 0.3D)
                .add(Attributes.TEMPT_RANGE, 10.0D)
                .add(Attributes.SCALE, SCALE);
    }

    @Override
    protected void defineSynchedData(SynchedEntityData.Builder builder) {
        super.defineSynchedData(builder);
        builder.define(DATA_VARIANT, 0);
        builder.define(DATA_IN_WHEEL, Boolean.FALSE);
    }

    @Override
    protected void registerGoals() {
        // Order = priority: the lower the number, the more important the goal.
        this.goalSelector.addGoal(0, new FloatGoal(this));
        this.goalSelector.addGoal(1, new PanicGoal(this, 1.5D));
        this.goalSelector.addGoal(2, new SitWhenOrderedToGoal(this));
        this.goalSelector.addGoal(3, new BreedGoal(this, 1.0D));
        this.goalSelector.addGoal(4, new TemptGoal(this, 1.1D, stack -> stack.is(ItemTags.CHICKEN_FOOD), false));
        this.goalSelector.addGoal(5, new UseWheelGoal(this));
        this.goalSelector.addGoal(6, new FollowOwnerGoal(this, 1.2D, 6.0F, 2.0F));
        this.goalSelector.addGoal(7, new WaterAvoidingRandomStrollGoal(this, 0.9D));
        this.goalSelector.addGoal(8, new LookAtPlayerGoal(this, Player.class, 6.0F));
        this.goalSelector.addGoal(9, new RandomLookAroundGoal(this));
    }

    // --- colour variant ------------------------------------------------------

    public HamsterVariant getVariant() {
        return HamsterVariant.byId(this.entityData.get(DATA_VARIANT));
    }

    public void setVariant(HamsterVariant variant) {
        this.entityData.set(DATA_VARIANT, variant.ordinal());
    }

    public boolean isInWheel() {
        return this.entityData.get(DATA_IN_WHEEL);
    }

    public void setInWheel(boolean value) {
        this.entityData.set(DATA_IN_WHEEL, value);
    }

    @Override
    public SpawnGroupData finalizeSpawn(ServerLevelAccessor level, DifficultyInstance difficulty,
                                        EntitySpawnReason reason, SpawnGroupData data) {
        this.setVariant(HamsterVariant.random(this.random));
        return super.finalizeSpawn(level, difficulty, reason, data);
    }

    @Override
    protected void addAdditionalSaveData(ValueOutput out) {
        super.addAdditionalSaveData(out);
        out.putInt("Variant", this.entityData.get(DATA_VARIANT));
    }

    @Override
    protected void readAdditionalSaveData(ValueInput in) {
        super.readAdditionalSaveData(in);
        this.entityData.set(DATA_VARIANT, in.getIntOr("Variant", 0));
    }

    // --- food, taming, breeding ----------------------------------------------

    @Override
    public boolean isFood(ItemStack stack) {
        return stack.is(ItemTags.CHICKEN_FOOD);
    }

    @Override
    public InteractionResult mobInteract(Player player, InteractionHand hand) {
        ItemStack held = player.getItemInHand(hand);

        // Sneaking with an empty hand is an attempt to pick the hamster up. The
        // sneak check is required: a plain right click makes a pet sit, and without
        // it there would be no way to simply ask the hamster to sit.
        //
        // The branch stands BEFORE the tameness check on purpose: otherwise the
        // gesture would do exactly nothing on a wild hamster, silently. That is what
        // 0.4.0 did - it looked broken although a condition was simply not met.
        if (held.isEmpty() && player.isSecondaryUseActive()) {
            if (!this.isTame()) {
                tell(player, "message.hamster.tame_first");
                return InteractionResult.SUCCESS;
            }
            if (!this.isOwnedBy(player)) {
                tell(player, "message.hamster.not_yours");
                return InteractionResult.SUCCESS;
            }
            if (!this.level().isClientSide()) {
                ItemStack pocket = HamsterItem.of(this);
                if (!player.addItem(pocket)) {
                    player.drop(pocket, false);
                }
                this.playSound(SoundEvents.RABBIT_AMBIENT, 0.6F, 1.4F);
                this.discard();
            }
            return InteractionResult.SUCCESS;
        }

        if (this.isTame()) {
            // A tamed hamster is fed when it is hurt; otherwise toggle "sit / follow".
            if (this.isFood(held) && this.getHealth() < this.getMaxHealth()) {
                this.usePlayerItem(player, hand, held);
                this.heal(2.0F);
                return InteractionResult.SUCCESS;
            }
            InteractionResult vanilla = super.mobInteract(player, hand);
            if (vanilla.consumesAction() || !this.isOwnedBy(player)) {
                return vanilla;
            }
            this.setOrderedToSit(!this.isOrderedToSit());
            this.jumping = false;
            this.navigation.stop();
            this.setTarget(null);
            return InteractionResult.SUCCESS;
        }

        if (this.isFood(held)) {
            this.usePlayerItem(player, hand, held);
            if (!this.level().isClientSide()) {
                if (this.random.nextInt(TAME_CHANCE_IN) == 0) {
                    this.tame(player);
                    this.setOrderedToSit(true);
                    this.level().broadcastEntityEvent(this, (byte) 7);   // hearts
                } else {
                    this.level().broadcastEntityEvent(this, (byte) 6);   // smoke
                }
            }
            return InteractionResult.SUCCESS;
        }

        return super.mobInteract(player, hand);
    }

    @Override
    public AgeableMob getBreedOffspring(ServerLevel level, AgeableMob mate) {
        Hamster baby = HamsterMod.HAMSTER.create(level, EntitySpawnReason.BREEDING);
        if (baby == null) {
            return null;
        }
        // The baby takes the colour of a random parent - like the coat of cats.
        HamsterVariant inherited = (mate instanceof Hamster other && this.random.nextBoolean())
                ? other.getVariant()
                : this.getVariant();
        baby.setVariant(inherited);
        if (this.isTame()) {
            baby.setOwnerReference(this.getOwnerReference());
            baby.setTame(true, true);
        }
        return baby;
    }

    /** A hint in the line above the hotbar: a silent refusal is worse than one with a reason. */
    private static void tell(Player player, String key) {
        if (player instanceof ServerPlayer serverPlayer) {
            serverPlayer.sendSystemMessage(Component.translatable(key), true);
        }
    }

    // --- small things --------------------------------------------------------

    @Override
    protected SoundEvent getAmbientSound() {
        return SoundEvents.RABBIT_AMBIENT;
    }

    @Override
    protected SoundEvent getHurtSound(DamageSource source) {
        return SoundEvents.RABBIT_HURT;
    }

    @Override
    protected SoundEvent getDeathSound() {
        return SoundEvents.RABBIT_DEATH;
    }

    @Override
    public int getAmbientSoundInterval() {
        return 600;      // squeaks far less often than the default: there will be many of them
    }

    @Override
    protected float nextStep() {
        return this.moveDist + 0.4F;    // a small animal, more frequent steps
    }
}
