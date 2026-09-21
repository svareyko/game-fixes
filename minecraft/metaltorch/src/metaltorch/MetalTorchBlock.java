package metaltorch;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.TorchBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * A metal torch standing on the floor or on top of a block.
 *
 * Extends the vanilla {@link TorchBlock}: everything about what a torch can
 * stand on and when it falls off is already written in BaseTorchBlock, and
 * there is no reason to write it again.
 *
 * The parent constructor insists on a {@code SimpleParticleType}, so a coloured
 * flame cannot be passed in. We pass the vanilla flame and override animateTick
 * completely: smoke like an ordinary torch, plus coloured sparks of the metal.
 */
public class MetalTorchBlock extends TorchBlock {

    public static final MapCodec<MetalTorchBlock> CODEC = RecordCodecBuilder.mapCodec(
            instance -> instance.group(
                    Codec.INT.fieldOf("colour").forGetter(block -> block.colour),
                    propertiesCodec()
            ).apply(instance, MetalTorchBlock::new));

    /** Sparks per animation tick: one looks poor, three already flicker too much. */
    private static final int SPARKS = 2;
    private static final float SPARK_SCALE = 0.7F;

    protected final int colour;

    public MetalTorchBlock(int colour, BlockBehaviour.Properties properties) {
        super(ParticleTypes.FLAME, properties);
        this.colour = colour;
    }

    @Override
    public MapCodec<? extends TorchBlock> codec() {
        return CODEC;
    }

    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        double x = pos.getX() + 0.5;
        double y = pos.getY() + 0.7;
        double z = pos.getZ() + 0.5;
        emit(level, random, x, y, z, this.colour);
    }

    /** Shared by the floor and the wall variant: smoke plus coloured sparks above the flame. */
    static void emit(Level level, RandomSource random, double x, double y, double z, int colour) {
        level.addParticle(ParticleTypes.SMOKE, x, y, z, 0.0, 0.0, 0.0);
        DustParticleOptions spark = new DustParticleOptions(colour, SPARK_SCALE);
        for (int i = 0; i < SPARKS; i++) {
            level.addParticle(spark,
                    x + (random.nextDouble() - 0.5) * 0.12,
                    y + random.nextDouble() * 0.12,
                    z + (random.nextDouble() - 0.5) * 0.12,
                    0.0, 0.0, 0.0);
        }
    }
}
