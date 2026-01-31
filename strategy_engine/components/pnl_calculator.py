"""PnL calculator component for grid strategy engine."""

from typing import Dict
from strategy_engine.components.position_manager import Position


class PnLCalculator:
    """盈亏计算器，负责所有盈亏相关的计算"""
    
    def __init__(self):
        """初始化盈亏计算器"""
        self.grid_profit = 0.0  # 已实现盈亏
    
    def calculate_realized_pnl(self, open_price: float, close_price: float, 
                               quantity: float, side: str) -> float:
        """计算已实现盈亏
        
        Args:
            open_price: 开仓价格
            close_price: 平仓价格
            quantity: 数量（正数）
            side: 仓位方向 ("long" 或 "short")
            
        Returns:
            已实现盈亏
        """
        if side == "long":
            return (close_price - open_price) * quantity
        else:  # short
            return (open_price - close_price) * quantity
    
    def calculate_unrealized_pnl(self, positions: Dict[int, Position], 
                                 current_price: float) -> float:
        """计算未实现盈亏
        
        Args:
            positions: 所有仓位的字典
            current_price: 当前价格
            
        Returns:
            未实现盈亏总和
        """
        unrealized_pnl = 0.0
        
        for position in positions.values():
            if position.quantity == 0:
                continue
            
            if position.quantity > 0:  # 多仓
                unrealized_pnl += position.quantity * (current_price - position.entry_price)
            else:  # 空仓（quantity是负数）
                unrealized_pnl += abs(position.quantity) * (position.entry_price - current_price)
        
        return unrealized_pnl
    
    def calculate_equity(self, capital: float, unrealized_pnl: float) -> float:
        """计算权益
        
        Args:
            capital: 当前资金
            unrealized_pnl: 未实现盈亏
            
        Returns:
            当前权益
        """
        return capital + unrealized_pnl
    
    def add_realized_pnl(self, pnl: float) -> None:
        """累加已实现盈亏
        
        Args:
            pnl: 盈亏金额
        """
        self.grid_profit += pnl
    
    def get_grid_profit(self) -> float:
        """获取网格收益
        
        Returns:
            网格收益（已实现盈亏）
        """
        return self.grid_profit
    
    def reset(self) -> None:
        """重置盈亏计算器"""
        self.grid_profit = 0.0
