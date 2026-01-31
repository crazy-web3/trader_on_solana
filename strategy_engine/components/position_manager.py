"""Position manager component for grid strategy engine."""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from strategy_engine.models import StrategyMode


@dataclass
class Position:
    """仓位信息"""
    grid_idx: int          # 网格索引
    quantity: float        # 数量（正数为多仓，负数为空仓）
    entry_price: float     # 开仓价格
    side: str             # "long" 或 "short"
    timestamp: int        # 开仓时间


class PositionManager:
    """仓位管理器，负责追踪和管理每个网格的仓位"""
    
    def __init__(self):
        """初始化仓位管理器"""
        self.grid_positions: Dict[int, Position] = {}
    
    def open_position(self, grid_idx: int, quantity: float, price: float, 
                     side: str, timestamp: int) -> None:
        """开仓
        
        Args:
            grid_idx: 网格索引
            quantity: 数量（正数）
            price: 开仓价格
            side: 仓位方向 ("long" 或 "short")
            timestamp: 开仓时间
        """
        if grid_idx in self.grid_positions:
            # 如果已有仓位，累加数量
            existing_pos = self.grid_positions[grid_idx]
            if existing_pos.side == side:
                # 同方向，累加数量
                total_quantity = abs(existing_pos.quantity) + quantity
                # 计算平均开仓价格
                avg_price = (existing_pos.entry_price * abs(existing_pos.quantity) + 
                           price * quantity) / total_quantity
                existing_pos.quantity = total_quantity if side == "long" else -total_quantity
                existing_pos.entry_price = avg_price
            else:
                # 反方向，减少数量或反转
                if abs(existing_pos.quantity) >= quantity:
                    # 部分平仓
                    existing_pos.quantity = (existing_pos.quantity + quantity 
                                           if side == "short" else existing_pos.quantity - quantity)
                    if existing_pos.quantity == 0:
                        del self.grid_positions[grid_idx]
                else:
                    # 完全平仓并反转
                    remaining = quantity - abs(existing_pos.quantity)
                    self.grid_positions[grid_idx] = Position(
                        grid_idx=grid_idx,
                        quantity=remaining if side == "long" else -remaining,
                        entry_price=price,
                        side=side,
                        timestamp=timestamp
                    )
        else:
            # 新开仓位
            self.grid_positions[grid_idx] = Position(
                grid_idx=grid_idx,
                quantity=quantity if side == "long" else -quantity,
                entry_price=price,
                side=side,
                timestamp=timestamp
            )
    
    def close_position(self, grid_idx: int, quantity: float) -> Optional[Position]:
        """平仓，返回被平掉的仓位信息
        
        Args:
            grid_idx: 网格索引
            quantity: 平仓数量（正数）
            
        Returns:
            被平掉的仓位信息，如果不存在则返回None
        """
        if grid_idx not in self.grid_positions:
            return None
        
        position = self.grid_positions[grid_idx]
        closed_position = Position(
            grid_idx=position.grid_idx,
            quantity=quantity if position.quantity > 0 else -quantity,
            entry_price=position.entry_price,
            side=position.side,
            timestamp=position.timestamp
        )
        
        # 减少仓位数量
        if abs(position.quantity) <= quantity:
            # 完全平仓
            del self.grid_positions[grid_idx]
        else:
            # 部分平仓
            position.quantity = (position.quantity + quantity 
                               if position.quantity < 0 else position.quantity - quantity)
        
        return closed_position
    
    def find_matching_position(self, grid_idx: int, side: str, 
                              strategy_mode: StrategyMode) -> Optional[Tuple[int, Position]]:
        """查找配对仓位
        
        Args:
            grid_idx: 当前订单的网格索引
            side: 当前订单的方向 ("buy" 或 "sell")
            strategy_mode: 策略模式
            
        Returns:
            配对仓位的(网格索引, 仓位)元组，如果没有找到则返回None
            
        策略逻辑说明:
        - Long模式: 低买高卖，建立多头仓位
          * 买单 = 开多仓（不配对）
          * 卖单 = 平多仓（配对下一网格的多仓）
        - Short模式: 高卖低买，建立空头仓位
          * 卖单 = 开空仓（不配对）
          * 买单 = 平空仓（配对上一网格的空仓）
        - Neutral模式: 双向交易，保持平衡
          * 买单 = 开多仓或平空仓（配对上一网格的空仓）
          * 卖单 = 开空仓或平多仓（配对下一网格的多仓）
        """
        if strategy_mode == StrategyMode.LONG:
            # 做多网格：目标是建立多头仓位
            if side == "buy":
                # 买单 = 开多仓，不需要配对
                return None
            elif side == "sell":
                # 卖单 = 平多仓，查找下一网格的多仓
                target_grid_idx = grid_idx - 1
                if target_grid_idx >= 0 and target_grid_idx in self.grid_positions:
                    position = self.grid_positions[target_grid_idx]
                    if position.quantity > 0:  # 多仓
                        return (target_grid_idx, position)
                return None
                
        elif strategy_mode == StrategyMode.SHORT:
            # 做空网格：目标是建立空头仓位
            if side == "sell":
                # 卖单 = 开空仓，不需要配对
                return None
            elif side == "buy":
                # 买单 = 平空仓，查找上一网格的空仓
                target_grid_idx = grid_idx + 1
                if target_grid_idx in self.grid_positions:
                    position = self.grid_positions[target_grid_idx]
                    if position.quantity < 0:  # 空仓
                        return (target_grid_idx, position)
                return None
                
        elif strategy_mode == StrategyMode.NEUTRAL:
            # 中性网格：双向交易，保持平衡
            if side == "buy":
                # 买单：优先平空仓，否则开多仓
                target_grid_idx = grid_idx + 1
                if target_grid_idx in self.grid_positions:
                    position = self.grid_positions[target_grid_idx]
                    if position.quantity < 0:  # 空仓
                        return (target_grid_idx, position)
                return None
            elif side == "sell":
                # 卖单：优先平多仓，否则开空仓
                target_grid_idx = grid_idx - 1
                if target_grid_idx >= 0 and target_grid_idx in self.grid_positions:
                    position = self.grid_positions[target_grid_idx]
                    if position.quantity > 0:  # 多仓
                        return (target_grid_idx, position)
                return None
        
        return None
    
    def get_net_position(self) -> float:
        """计算净仓位（正数为多仓，负数为空仓）
        
        Returns:
            净仓位数量
        """
        return sum(pos.quantity for pos in self.grid_positions.values())
    
    def get_all_positions(self) -> Dict[int, Position]:
        """获取所有仓位
        
        Returns:
            所有仓位的字典
        """
        return self.grid_positions
    
    def get_position(self, grid_idx: int) -> Optional[Position]:
        """获取指定网格的仓位
        
        Args:
            grid_idx: 网格索引
            
        Returns:
            仓位信息，如果不存在则返回None
        """
        return self.grid_positions.get(grid_idx)
