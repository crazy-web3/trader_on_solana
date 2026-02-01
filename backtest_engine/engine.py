"""Backtest engine implementation."""

from typing import List, Tuple
from datetime import datetime, timedelta
import math
from backtest_engine.models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    StrategyMode,
)
from backtest_engine.exceptions import InvalidConfigError, DataError
from strategy_engine import GridStrategyEngine, StrategyConfig
from market_data_layer.adapter import BinanceDataSourceAdapter
from market_data_layer.validator import KlineDataValidator


class BacktestEngine:
    """Comprehensive backtest engine.
    
    Supports:
    - Single parameter backtest
    - Multi-year historical data
    - Performance metrics calculation
    - Equity curve tracking
    """
    
    def __init__(self, adapter: BinanceDataSourceAdapter = None):
        """Initialize backtest engine.
        
        Args:
            adapter: Data source adapter (default: BinanceDataSourceAdapter)
        """
        self.adapter = adapter or BinanceDataSourceAdapter()
        self.validator = KlineDataValidator()
    
    def run_backtest(self, config: BacktestConfig) -> BacktestResult:
        """Run a single backtest.
        
        Args:
            config: Backtest configuration
            
        Returns:
            Backtest result
            
        Raises:
            InvalidConfigError: If configuration is invalid
            DataError: If data retrieval fails
        """
        self._validate_config(config)
        
        # Parse dates
        start_date = datetime.strptime(config.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(config.end_date, "%Y-%m-%d")
        
        start_time = int(start_date.timestamp() * 1000)
        end_time = int(end_date.timestamp() * 1000)
        
        # Fetch K-line data using configured timeframe
        klines = self.adapter.fetch_kline_data(
            symbol=config.symbol,
            interval=config.timeframe,  # Use configured timeframe
            start_time=start_time,
            end_time=end_time,
        )
        
        if not klines:
            raise DataError(f"No data available for {config.symbol}")
        
        # Validate data
        validation_results = self.validator.validate_batch(klines)
        valid_klines = [
            kline for kline, result in zip(klines, validation_results)
            if result.isValid
        ]
        
        if not valid_klines:
            raise DataError("No valid K-line data")
        
        # Create strategy config
        strategy_config = StrategyConfig(
            symbol=config.symbol,
            mode=config.mode,
            lower_price=config.lower_price,
            upper_price=config.upper_price,
            grid_count=config.grid_count,
            initial_capital=config.initial_capital,
            fee_rate=config.fee_rate,
            leverage=config.leverage,
            funding_rate=config.funding_rate,
            funding_interval=config.funding_interval,
        )
        
        # Run strategy
        engine = GridStrategyEngine(strategy_config)
        strategy_result = engine.execute(valid_klines)
        
        # Calculate performance metrics
        metrics = self._calculate_metrics(
            strategy_result,
            config,
            start_date,
            end_date,
        )
        
        # Create backtest result
        result = BacktestResult(
            config=config,
            metrics=metrics,
            initial_capital=config.initial_capital,
            final_capital=strategy_result.final_capital,
            equity_curve=strategy_result.equity_curve,
            timestamps=strategy_result.timestamps,
            trades=[
                {
                    "timestamp": t.timestamp,
                    "price": t.price,
                    "quantity": t.quantity,
                    "side": t.side,
                    "fee": t.fee,
                    "pnl": t.pnl,
                }
                for t in strategy_result.trades
            ],
        )
        
        return result
    
    def _validate_config(self, config: BacktestConfig) -> None:
        """Validate backtest configuration.
        
        Args:
            config: Backtest configuration
            
        Raises:
            InvalidConfigError: If configuration is invalid
        """
        if config.lower_price <= 0 or config.upper_price <= 0:
            raise InvalidConfigError("Prices must be positive")
        
        if config.lower_price >= config.upper_price:
            raise InvalidConfigError("Lower price must be less than upper price")
        
        if config.grid_count < 2:
            raise InvalidConfigError("Grid count must be at least 2")
        
        if config.initial_capital <= 0:
            raise InvalidConfigError("Initial capital must be positive")
        
        try:
            start_date = datetime.strptime(config.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(config.end_date, "%Y-%m-%d")
            
            if start_date >= end_date:
                raise InvalidConfigError("Start date must be before end date")
            
            # Check if date range is within 3 years
            days_diff = (end_date - start_date).days
            if days_diff > 365 * 3:
                raise InvalidConfigError("Backtest range cannot exceed 3 years")
        
        except ValueError as e:
            raise InvalidConfigError(f"Invalid date format: {str(e)}")
    
    def _calculate_metrics(
        self,
        strategy_result,
        config: BacktestConfig,
        start_date: datetime,
        end_date: datetime,
    ) -> PerformanceMetrics:
        """Calculate performance metrics.
        
        Args:
            strategy_result: Strategy execution result
            config: Backtest configuration
            start_date: Start date
            end_date: End date
            
        Returns:
            Performance metrics
        """
        # Calculate total return
        # Requirement 6.1: 总收益率 = (最终权益 - 初始资金) / 初始资金
        total_return = (
            (strategy_result.final_capital - config.initial_capital) /
            config.initial_capital
        )
        
        # Calculate annualized return
        # Requirement 6.2: 年化收益率 = 总收益率 × (365天 / 回测天数)
        days = (end_date - start_date).days
        annual_return = (
            total_return * (365.0 / days)
            if days > 0 else 0
        )
        
        # Calculate max drawdown
        # Requirement 6.3: 最大回撤 = (峰值权益 - 最低权益) / 峰值权益
        # This is calculated in the strategy engine using the equity curve
        max_drawdown = strategy_result.max_drawdown_pct
        
        # Calculate Sharpe ratio (simplified)
        sharpe_ratio = self._calculate_sharpe_ratio(
            strategy_result.equity_curve
        )
        
        # Calculate trade statistics
        total_trades = strategy_result.total_trades
        winning_trades = strategy_result.winning_trades
        losing_trades = strategy_result.losing_trades
        win_rate = (
            winning_trades / total_trades
            if total_trades > 0 else 0
        )
        
        # Calculate fee cost
        fee_cost = sum(t.fee for t in strategy_result.trades)
        fee_ratio = fee_cost / config.initial_capital
        
        return PerformanceMetrics(
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            fee_cost=fee_cost,
            fee_ratio=fee_ratio,
        )
    
    @staticmethod
    def _calculate_sharpe_ratio(equity_curve: List[float]) -> float:
        """Calculate Sharpe ratio.
        
        Requirement 6.4: 夏普比率 = (平均日收益率 / 日收益率标准差) × sqrt(252)
        
        Args:
            equity_curve: Equity curve values
            
        Returns:
            Sharpe ratio (annualized)
        """
        if len(equity_curve) < 2:
            return 0.0
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i-1] == 0:
                # Handle edge case of zero equity - cannot calculate return
                return 0.0
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Calculate mean of daily returns
        mean_return = sum(returns) / len(returns)
        
        # Calculate sample standard deviation (using n-1 for unbiased estimator)
        if len(returns) == 1:
            # Cannot calculate std dev with only 1 return
            return 0.0
        
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        
        # Handle zero standard deviation (all returns are identical)
        if std_dev == 0:
            return 0.0
        
        # Calculate annualized Sharpe ratio
        # Multiply by sqrt(252) to annualize (252 trading days per year)
        sharpe_ratio = (mean_return / std_dev) * math.sqrt(252)
        
        return sharpe_ratio
