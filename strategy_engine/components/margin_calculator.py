"""Margin calculator component for grid strategy engine."""


class MarginCalculator:
    """保证金计算器，负责保证金相关的所有计算"""
    
    def __init__(self, leverage: float):
        """初始化保证金计算器
        
        Args:
            leverage: 杠杆倍数
        """
        self.leverage = leverage
        self.used_margin = 0.0
    
    def calculate_required_margin(self, quantity: float, price: float) -> float:
        """计算开仓所需保证金
        
        Args:
            quantity: 数量
            price: 价格
            
        Returns:
            所需保证金金额
        """
        return quantity * price / self.leverage
    
    def allocate_margin(self, amount: float, total_capital: float) -> bool:
        """分配保证金，返回是否成功
        
        Args:
            amount: 需要分配的保证金金额
            total_capital: 总资金
            
        Returns:
            是否成功分配保证金
        """
        available = total_capital - self.used_margin
        if available >= amount:
            self.used_margin += amount
            return True
        return False
    
    def release_margin(self, amount: float) -> None:
        """释放保证金
        
        Args:
            amount: 需要释放的保证金金额
        """
        self.used_margin -= amount
        # 确保已用保证金不会变为负数
        if self.used_margin < 0:
            self.used_margin = 0.0
    
    def get_available_capital(self, total_capital: float) -> float:
        """计算可用资金
        
        Args:
            total_capital: 总资金
            
        Returns:
            可用资金金额
        """
        return total_capital - self.used_margin
    
    def get_used_margin(self) -> float:
        """获取已用保证金
        
        Returns:
            已用保证金金额
        """
        return self.used_margin
    
    def reset(self) -> None:
        """重置保证金计算器"""
        self.used_margin = 0.0
