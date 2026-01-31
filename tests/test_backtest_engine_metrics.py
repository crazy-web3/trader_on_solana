"""Tests for BacktestEngine metrics calculation.

This module tests that performance metrics are calculated correctly
according to requirements 6.1, 6.2, and 6.3.
"""

import pytest
from datetime import datetime, timedelta
from backtest_engine.engine import BacktestEngine
from backtest_engine.models import BacktestConfig, StrategyMode
from strategy_engine.models import StrategyResult, TradeRecord


class TestBacktestEngineMetrics:
    """Test suite for BacktestEngine metrics calculation."""
    
    def test_total_return_calculation(self):
        """Test that total return is calculated correctly.
        
        Requirement 6.1: 总收益率 = (最终权益 - 初始资金) / 初始资金
        """
        engine = BacktestEngine()
        
        # Create mock strategy result
        initial_capital = 10000.0
        final_capital = 12000.0  # 20% gain
        
        strategy_result = self._create_mock_strategy_result(
            initial_capital=initial_capital,
            final_capital=final_capital,
        )
        
        # Create config
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=30000,
            upper_price=40000,
            grid_count=10,
            initial_capital=initial_capital,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        # Calculate metrics
        metrics = engine._calculate_metrics(
            strategy_result,
            config,
            start_date,
            end_date,
        )
        
        # Verify total return
        expected_total_return = (final_capital - initial_capital) / initial_capital
        assert abs(metrics.total_return - expected_total_return) < 1e-10
        assert abs(metrics.total_return - 0.2) < 1e-10  # 20%
    
    def test_annualized_return_calculation(self):
        """Test that annualized return is calculated correctly.
        
        Requirement 6.2: 年化收益率 = 总收益率 × (365天 / 回测天数)
        """
        engine = BacktestEngine()
        
        # Test case 1: 1 year backtest with 20% return
        initial_capital = 10000.0
        final_capital = 12000.0  # 20% gain
        
        strategy_result = self._create_mock_strategy_result(
            initial_capital=initial_capital,
            final_capital=final_capital,
        )
        
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=30000,
            upper_price=40000,
            grid_count=10,
            initial_capital=initial_capital,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        days = (end_date - start_date).days
        
        metrics = engine._calculate_metrics(
            strategy_result,
            config,
            start_date,
            end_date,
        )
        
        # Verify annualized return using simple formula
        total_return = 0.2
        expected_annual_return = total_return * (365.0 / days)
        assert abs(metrics.annual_return - expected_annual_return) < 1e-10
        
        # Test case 2: 6 months backtest with 10% return
        final_capital = 11000.0  # 10% gain
        strategy_result = self._create_mock_strategy_result(
            initial_capital=initial_capital,
            final_capital=final_capital,
        )
        
        config.start_date = "2024-01-01"
        config.end_date = "2024-07-01"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 7, 1)
        days = (end_date - start_date).days
        
        metrics = engine._calculate_metrics(
            strategy_result,
            config,
            start_date,
            end_date,
        )
        
        # Verify annualized return
        total_return = 0.1
        expected_annual_return = total_return * (365.0 / days)
        assert abs(metrics.annual_return - expected_annual_return) < 1e-10
        # For 182 days, annualized return should be approximately 0.1 * (365/182) = 0.2
        assert abs(metrics.annual_return - 0.2005) < 0.001
    
    def test_max_drawdown_from_strategy_result(self):
        """Test that max drawdown is correctly taken from strategy result.
        
        Requirement 6.3: 最大回撤 = (峰值权益 - 最低权益) / 峰值权益
        
        Note: The actual calculation is done in the strategy engine,
        this test verifies that the backtest engine correctly uses that value.
        """
        engine = BacktestEngine()
        
        # Create mock strategy result with known max drawdown
        strategy_result = self._create_mock_strategy_result(
            initial_capital=10000.0,
            final_capital=12000.0,
            max_drawdown_pct=0.15,  # 15% max drawdown
        )
        
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=30000,
            upper_price=40000,
            grid_count=10,
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        metrics = engine._calculate_metrics(
            strategy_result,
            config,
            start_date,
            end_date,
        )
        
        # Verify max drawdown is correctly passed through
        assert abs(metrics.max_drawdown - 0.15) < 1e-10
    
    def test_edge_case_zero_days(self):
        """Test that metrics handle edge case of zero days correctly."""
        engine = BacktestEngine()
        
        strategy_result = self._create_mock_strategy_result(
            initial_capital=10000.0,
            final_capital=12000.0,
        )
        
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=30000,
            upper_price=40000,
            grid_count=10,
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-01-01",
        )
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        metrics = engine._calculate_metrics(
            strategy_result,
            config,
            start_date,
            end_date,
        )
        
        # Annual return should be 0 when days is 0
        assert metrics.annual_return == 0
    
    def test_negative_return_calculation(self):
        """Test that metrics correctly handle negative returns."""
        engine = BacktestEngine()
        
        # Create mock strategy result with loss
        initial_capital = 10000.0
        final_capital = 8000.0  # 20% loss
        
        strategy_result = self._create_mock_strategy_result(
            initial_capital=initial_capital,
            final_capital=final_capital,
        )
        
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=30000,
            upper_price=40000,
            grid_count=10,
            initial_capital=initial_capital,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        days = (end_date - start_date).days
        
        metrics = engine._calculate_metrics(
            strategy_result,
            config,
            start_date,
            end_date,
        )
        
        # Verify negative total return
        expected_total_return = (final_capital - initial_capital) / initial_capital
        assert abs(metrics.total_return - expected_total_return) < 1e-10
        assert abs(metrics.total_return - (-0.2)) < 1e-10  # -20%
        
        # Verify negative annualized return
        expected_annual_return = expected_total_return * (365.0 / days)
        assert abs(metrics.annual_return - expected_annual_return) < 1e-10
    
    def test_win_rate_calculation(self):
        """Test that win rate is calculated correctly.
        
        Requirement 6.5: 胜率 = 盈利交易数 / 总交易数
        """
        engine = BacktestEngine()
        
        # Test case 1: 60% win rate (6 winning out of 10 trades)
        initial_capital = 10000.0
        final_capital = 11000.0
        
        strategy_result = self._create_mock_strategy_result(
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
        )
        
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=30000,
            upper_price=40000,
            grid_count=10,
            initial_capital=initial_capital,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        metrics = engine._calculate_metrics(
            strategy_result,
            config,
            start_date,
            end_date,
        )
        
        # Verify win rate
        expected_win_rate = 6 / 10
        assert abs(metrics.win_rate - expected_win_rate) < 1e-10
        assert abs(metrics.win_rate - 0.6) < 1e-10
        assert metrics.total_trades == 10
        assert metrics.winning_trades == 6
        assert metrics.losing_trades == 4
    
    def test_win_rate_edge_case_zero_trades(self):
        """Test that win rate handles edge case of zero trades correctly.
        
        Requirement 6.5: When total_trades = 0, win_rate should be 0
        """
        engine = BacktestEngine()
        
        strategy_result = self._create_mock_strategy_result(
            initial_capital=10000.0,
            final_capital=10000.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
        )
        
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=30000,
            upper_price=40000,
            grid_count=10,
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        metrics = engine._calculate_metrics(
            strategy_result,
            config,
            start_date,
            end_date,
        )
        
        # Win rate should be 0 when there are no trades
        assert metrics.win_rate == 0.0
        assert metrics.total_trades == 0
        assert metrics.winning_trades == 0
        assert metrics.losing_trades == 0
    
    def test_win_rate_all_winning_trades(self):
        """Test win rate when all trades are winning.
        
        Requirement 6.5: 100% win rate
        """
        engine = BacktestEngine()
        
        strategy_result = self._create_mock_strategy_result(
            initial_capital=10000.0,
            final_capital=15000.0,
            total_trades=5,
            winning_trades=5,
            losing_trades=0,
        )
        
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=30000,
            upper_price=40000,
            grid_count=10,
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        metrics = engine._calculate_metrics(
            strategy_result,
            config,
            start_date,
            end_date,
        )
        
        # Win rate should be 1.0 (100%)
        assert abs(metrics.win_rate - 1.0) < 1e-10
        assert metrics.total_trades == 5
        assert metrics.winning_trades == 5
        assert metrics.losing_trades == 0
    
    def test_win_rate_all_losing_trades(self):
        """Test win rate when all trades are losing.
        
        Requirement 6.5: 0% win rate
        """
        engine = BacktestEngine()
        
        strategy_result = self._create_mock_strategy_result(
            initial_capital=10000.0,
            final_capital=8000.0,
            total_trades=5,
            winning_trades=0,
            losing_trades=5,
        )
        
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=30000,
            upper_price=40000,
            grid_count=10,
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        metrics = engine._calculate_metrics(
            strategy_result,
            config,
            start_date,
            end_date,
        )
        
        # Win rate should be 0.0 (0%)
        assert metrics.win_rate == 0.0
        assert metrics.total_trades == 5
        assert metrics.winning_trades == 0
        assert metrics.losing_trades == 5
    
    def _create_mock_strategy_result(
        self,
        initial_capital: float,
        final_capital: float,
        max_drawdown_pct: float = 0.0,
        total_trades: int = 0,
        winning_trades: int = 0,
        losing_trades: int = 0,
    ) -> StrategyResult:
        """Create a mock strategy result for testing.
        
        Args:
            initial_capital: Initial capital
            final_capital: Final capital
            max_drawdown_pct: Maximum drawdown percentage
            total_trades: Total number of trades
            winning_trades: Number of winning trades
            losing_trades: Number of losing trades
            
        Returns:
            Mock strategy result
        """
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        return StrategyResult(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=(final_capital - initial_capital) / initial_capital,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            max_drawdown=0.0,
            max_drawdown_pct=max_drawdown_pct,
            total_fees=0.0,
            total_funding_fees=0.0,
            grid_profit=0.0,
            unrealized_pnl=0.0,
            trades=[],
            equity_curve=[initial_capital, final_capital],
            timestamps=[],
        )
