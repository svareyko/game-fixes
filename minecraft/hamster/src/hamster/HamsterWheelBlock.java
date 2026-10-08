package hamster;

import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.HorizontalDirectionalBlock;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

/**
 * The hamster wheel.
 *
 * The "occupied" state is kept in the block state, not in the block entity: that
 * way it reaches the client for free, and the comparator reads the very same value.
 * The block entity holds no data. On the client it carries the renderer of the
 * spinning rim and its rotation angle; on the server it is the watchdog that frees
 * the wheel when its hamster is gone.
 */
public class HamsterWheelBlock extends BaseEntityBlock {

    public static final MapCodec<HamsterWheelBlock> CODEC = simpleCodec(HamsterWheelBlock::new);

    public static final EnumProperty<Direction> FACING = HorizontalDirectionalBlock.FACING;
    public static final BooleanProperty OCCUPIED = BlockStateProperties.OCCUPIED;

    /** The stand with the rim: takes up most of the block, but is not a full cube. */
    private static final VoxelShape SHAPE_NS = Block.box(2.0, 0.0, 4.0, 14.0, 15.0, 12.0);
    private static final VoxelShape SHAPE_EW = Block.box(4.0, 0.0, 2.0, 12.0, 15.0, 14.0);

    public HamsterWheelBlock(BlockBehaviour.Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any()
                .setValue(FACING, Direction.NORTH)
                .setValue(OCCUPIED, Boolean.FALSE));
    }

    @Override
    protected MapCodec<? extends BaseEntityBlock> codec() {
        return CODEC;
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING, OCCUPIED);
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        // Placed facing the player: a wheel is more interesting to look at from the front.
        return this.defaultBlockState()
                .setValue(FACING, context.getHorizontalDirection().getOpposite());
    }

    @Override
    protected BlockState rotate(BlockState state, Rotation rotation) {
        return state.setValue(FACING, rotation.rotate(state.getValue(FACING)));
    }

    @Override
    protected BlockState mirror(BlockState state, Mirror mirror) {
        return state.rotate(mirror.getRotation(state.getValue(FACING)));
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        Direction facing = state.getValue(FACING);
        return facing.getAxis() == Direction.Axis.Z ? SHAPE_NS : SHAPE_EW;
    }

    // --- comparator ----------------------------------------------------------

    @Override
    protected boolean hasAnalogOutputSignal(BlockState state) {
        return true;
    }

    @Override
    protected int getAnalogOutputSignal(BlockState state, Level level, BlockPos pos, Direction side) {
        return state.getValue(OCCUPIED) ? 15 : 0;
    }

    // --- block entity --------------------------------------------------------

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new HamsterWheelBlockEntity(pos, state);
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state,
                                                                 net.minecraft.world.level.block.entity.BlockEntityType<T> type) {
        // Both sides tick, whatever the state: the client spins the rim (and has to tick on
        // after it stops, or the interpolated angle would keep jittering), the server runs
        // the watchdog, which returns at once on a free wheel.
        if (level.isClientSide()) {
            return createTickerHelper(type, HamsterMod.HAMSTER_WHEEL_ENTITY,
                    HamsterWheelBlockEntity::clientTick);
        }
        return createTickerHelper(type, HamsterMod.HAMSTER_WHEEL_ENTITY,
                HamsterWheelBlockEntity::serverTick);
    }
}
