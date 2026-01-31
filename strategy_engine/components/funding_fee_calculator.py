"""Funding fee calculator component for grid strategy engine."""


class FundingFeeCalculator:
    """资金费率计算器，负责资金费率的计算和结算"""
    
    def __init__(self, funding_rate: float, funding_interval: int):
        """初始化资金费率计算器
        
        Args:
            funding_rate: 资金费率
            funding_interval: 资金费率结算间隔（小时）
        """
        self.funding_rate = funding_rate
        self.funding_interval_ms = funding_interval * 60 * 60 * 1000
        self.last_funding_time = 0
        self.total_funding_fees = 0.0
    
    def should_settle_funding(self, current_time: int) -> bool:
        """判断是否应该结算资金费率
        
        Args:
            current_time: 当前时间（毫秒时间戳）
            
        Returns:
            是否应该结算
        """
        if self.last_funding_time == 0:
            self.last_funding_time = current_time
            return False
        return current_time - self.last_funding_time >= self.funding_interval_ms
    
    def calculate_funding_fee(self, position_size: float, current_price: float) -> float:
        """计算资金费用（正数表示支付，负数表示收取）
        
        Args:
            position_size: 仓位大小（正数为多仓，负数为空仓）
            current_price: 当前价格
            
        Returns:
            资金费用（多仓支付为正，空仓收取为负）
        """
        # 多仓支付资金费率，空仓收取资金费率
        return position_size * current_price * self.funding_rate
    
    def settle_funding(self, current_time: int) -> None:
        """更新资金费率结算时间
        
        Args:
            current_time: 当前时间（毫秒时间戳）
        """
        self.last_funding_time = current_time
    
    def add_funding_fee(self, fee: float) -> None:
        """累加资金费用
        
        Args:
            fee: 资金费用金额
        """
        self.total_funding_fees += abs(fee)
    
    def get_total_funding_fees(self) -> float:
        """获取总资金费用
        
        Returns:
            总资金费用
        """
        return self.total_funding_fees
    
    def reset(self) -> None:
        """重置资金费率计算器"""
        self.last_funding_time = 0
        self.total_funding_fees = 0.0
