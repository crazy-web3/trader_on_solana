"""Optimized backtest engine with improved grid trading algorithm."""

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
from strategy_engine.optimized_engine import OptimizedGridStrategyEngine
from strategy_engine.models import StrategyConfig, GridType
from market_data_layer.adapter import BinanceDataSourceAdapter
from market_data_layer.validator import KlineDataValidator


class OptimizedBacktestEngine:
    """Optimized backtest engine with improved grid trading algorithm.
    
    Key improvements:
    1. Supports arithmetic and geometric grid types
    2. Implements proper grid closure mechanism
    3. Accurate margin and risk management
    4. Separate tracking of grid profit and unrealized PnL
    5. Better performance metrics calculation
    """
    
    def __init__(self, adapter: BinanceDataSourceAdapter = None):
        """Initialize optimized backtest engine.
        
        Args:
            adapter: Data source adapter (default: BinanceDataSourceAdapter)
        """
        self.adapter = adapter or BinanceDataSourceAdapter()
        self.validator = KlineDataValidator()
    
    def run_backtest(self, config: BacktestConfig, grid_type: GridType = GridType.ARITHMETIC) -> BacktestResult:
        """Run a single backtest with optimized algorithm.
        
        Args:
            config: Backtest configuration
            grid_type: Grid type (arithmetic or geometric)
            
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
        
        # Fetch K-line data
        klines = self.adapter.fetch_kline_data(
            symbol=config.symbol,
            interval="1d",
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
        
        # Create strategy config with grid type
        strategy_config = StrategyConfig(
            symbol=config.symbol,
            mode=config.mode,
            grid_type=grid_type,
            lower_price=config.lower_price,
            upper_price=config.upper_price,
            grid_count=config.grid_count,
            initial_capital=config.initial_capital,
            fee_rate=config.fee_rate,
            leverage=config.leverage,
            funding_rate=config.funding_rate,
            funding_interval=config.funding_interval,
        )
        
        # Run optimized strategy
        engine = OptimizedGridStrategyEngine(strategy_config)
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
                    "grid_level": t.grid_level,
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
        
        if config.grid_count < 2 or config.grid_count > 169:
            raise InvalidConfigError("Grid count must be between 2 and 169")
        
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
        total_return = (
            (strategy_result.final_capital - config.initial_capital) /
            config.initial_capital
        )
        
        # Calculate annualized return
        days = (end_date - start_date).days
        years = days / 365.0
        annual_return = (
            (1 + total_return) ** (1 / years) - 1
            if years > 0 else 0
        )
        
        # Calculate max drawdown
        max_drawdown = strategy_result.max_drawdown_pct
        
        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio(
            strategy_result.equity_curve
        )
        
        # Calculate trade statistics
        total_trades = strategy_result.total_trades
        winning_trades = strategy_result.winning_trades
        losing_trades = strategy_result.losing_trades
        win_rate = strategy_result.win_rate
        
        # Calculate fee cost
        fee_cost = strategy_result.total_fees
        fee_ratio = fee_cost / config.initial_capital if config.initial_capital > 0 else 0
        
        # Calculate funding cost
        funding_cost = strategy_result.total_funding_fees
        funding_ratio = funding_cost / config.initial_capital if config.initial_capital > 0 else 0
        
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
            funding_cost=funding_cost,
            funding_ratio=funding_ratio,
        )
    
    @staticmethod
    def _calculate_sharpe_ratio(equity_curve: List[float]) -> float:
        """Calculate Sharpe ratio.
        
        Args:
            equity_curve: Equity curve values
            
        Returns:
            Sharpe ratio
        """
        if len(equity_curve) < 2:
            return 0.0
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Calculate mean and std dev
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        # Calculate Sharpe ratio (assuming 0% risk-free rate)
        if std_dev == 0:
            return 0.0
        
        # Annualize (252 trading days)
        sharpe_ratio = (mean_return / std_dev) * math.sqrt(252)
        
        return sharpe_ratio
    
    def run_grid_search(
        self,
        config: BacktestConfig,
        grid_count_range: Tuple[int, int] = (5, 50),
        leverage_range: Tuple[float, float] = (1.0, 10.0),
        grid_type: GridType = GridType.ARITHMETIC,
    ) -> dict:
        """Run grid search optimization.
        
        Args:
            config: Base backtest configuration
            grid_count_range: Range of grid counts to test
            leverage_range: Range of leverage values to test
            grid_type: Grid type to use
            
        Returns:
            Grid search results
        """
        results = []
        best_result = None
        best_return = float('-inf')
        
        # Test different grid counts and leverage values
        for grid_count in range(grid_count_range[0], grid_count_range[1] + 1, 5):
            for leverage in [1.0, 2.0, 3.0, 5.0, 10.0]:
                if leverage < leverage_range[0] or leverage > leverage_range[1]:
                    continue
                
                # Create config with current parameters
                test_config = BacktestConfig(
                    symbol=config.symbol,
                    mode=config.mode,
                    lower_price=config.lower_price,
                    upper_price=config.upper_price,
                    grid_count=grid_count,
                    initial_capital=config.initial_capital,
                    start_date=config.start_date,
                    end_date=config.end_date,
                    fee_rate=config.fee_rate,
                    leverage=leverage,
                    funding_rate=config.funding_rate,
                    funding_interval=config.funding_interval,
                )
                
                try:
                    # Run backtest
                    result = self.run_backtest(test_config, grid_type)
                    results.append({
                        "grid_count": grid_count,
                        "leverage": leverage,
                        "result": result,
                    })
                    
                    # Track best result
                    if result.metrics.total_return > best_return:
                        best_return = result.metrics.total_return
                        best_result = result
                
                except Exception as e:
                    # Skip failed configurations
                    continue
        
        return {
            "best_result": best_result,
            "all_results": results,
            "best_params": {
                "grid_count": best_result.config.grid_count if best_result else None,
                "leverage": best_result.config.leverage if best_result else None,
            } if best_result else {},
        }
