package metaltorch;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.WallTorchBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;

/**
 * A metal torch on a wall.
 *
 * Differs from the standing one only in where the sparks come from: the head of a
 * wall torch sits 0.27 off the block centre - the offset the vanilla wall torch uses.
 */
public class MetalWallTorchBlock extends WallTorchBlock {

    /**
     * The type really is MapCodec<WallTorchBlock> and not our own class:
     * WallTorchBlock declares codec() invariantly, without "? extends", so the
     * return type cannot be narrowed. Hence the cast in the getter as well.
     */
    public static final MapCodec<WallTorchBlock> CODEC = RecordCodecBuilder.mapCodec(
            instance -> instance.group(
                    Codec.INT.fieldOf("colour")
                            .forGetter(block -> ((MetalWallTorchBlock) block).colour),
                    propertiesCodec()
            ).apply(instance, (colour, properties) ->
                    (WallTorchBlock) new MetalWallTorchBlock(colour, properties)));

    /**
     * Where the tip of a wall torch is, relative to a standing one. The numbers are
     * those of WallTorchBlock.animateTick: the model is the vanilla
     * template_torch_wall, so the flame sits where the vanilla one does.
     */
    private static final double WALL_OFFSET = 0.27;
    private static final double WALL_LIFT = 0.22;

    protected final int colour;

    public MetalWallTorchBlock(int colour, BlockBehaviour.Properties properties) {
        super(ParticleTypes.FLAME, properties);
        this.colour = colour;
    }

    @Override
    public MapCodec<WallTorchBlock> codec() {
        return CODEC;
    }

    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        Direction away = state.getValue(FACING).getOpposite();
        double x = pos.getX() + 0.5 + WALL_OFFSET * away.getStepX();
        double y = pos.getY() + 0.7 + WALL_LIFT;
        double z = pos.getZ() + 0.5 + WALL_OFFSET * away.getStepZ();
        MetalTorchBlock.emit(level, random, x, y, z, this.colour);
    }
}
