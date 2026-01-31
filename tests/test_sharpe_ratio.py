"""Tests for Sharpe ratio calculation.

This module tests that the Sharpe ratio is calculated correctly
according to requirement 6.4.
"""

import pytest
import math
from backtest_engine.engine import BacktestEngine


class TestSharpeRatio:
    """Test suite for Sharpe ratio calculation."""
    
    def test_sharpe_ratio_basic_calculation(self):
        """Test basic Sharpe ratio calculation.
        
        Requirement 6.4: 夏普比率 = (平均日收益率 / 日收益率标准差) × sqrt(252)
        """
        # Create equity curve with known returns
        # Starting with 10000, then 10100 (+1%), 10200 (+0.99%), 10300 (+0.98%)
        equity_curve = [10000, 10100, 10200, 10300]
        
        # Calculate expected Sharpe ratio manually
        returns = [
            (10100 - 10000) / 10000,  # 0.01
            (10200 - 10100) / 10100,  # 0.0099009...
            (10300 - 10200) / 10200,  # 0.0098039...
        ]
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        expected_sharpe = (mean_return / std_dev) * math.sqrt(252)
        
        # Calculate using the method
        sharpe = BacktestEngine._calculate_sharpe_ratio(equity_curve)
        
        # Verify
        assert abs(sharpe - expected_sharpe) < 1e-10
    
    def test_sharpe_ratio_positive_returns(self):
        """Test Sharpe ratio with consistently positive returns."""
        # Equity curve with 1% daily returns
        equity_curve = [10000 * (1.01 ** i) for i in range(10)]
        
        sharpe = BacktestEngine._calculate_sharpe_ratio(equity_curve)
        
        # With consistent positive returns, Sharpe should be positive
        assert sharpe > 0
    
    def test_sharpe_ratio_negative_returns(self):
        """Test Sharpe ratio with consistently negative returns."""
        # Equity curve with -1% daily returns
        equity_curve = [10000 * (0.99 ** i) for i in range(10)]
        
        sharpe = BacktestEngine._calculate_sharpe_ratio(equity_curve)
        
        # With consistent negative returns, Sharpe should be negative
        assert sharpe < 0
    
    def test_sharpe_ratio_volatile_returns(self):
        """Test Sharpe ratio with volatile returns."""
        # Equity curve with alternating +2% and -1% returns
        equity_curve = [10000]
        for i in range(10):
            if i % 2 == 0:
                equity_curve.append(equity_curve[-1] * 1.02)
            else:
                equity_curve.append(equity_curve[-1] * 0.99)
        
        sharpe = BacktestEngine._calculate_sharpe_ratio(equity_curve)
        
        # Should have a Sharpe ratio (positive since net return is positive)
        assert sharpe > 0
        # But lower than consistent positive returns due to volatility
        consistent_equity = [10000 * (1.005 ** i) for i in range(11)]
        consistent_sharpe = BacktestEngine._calculate_sharpe_ratio(consistent_equity)
        assert sharpe < consistent_sharpe
    
    def test_sharpe_ratio_zero_std_dev(self):
        """Test Sharpe ratio when all returns are identical (zero std dev)."""
        # Flat equity curve (no returns)
        equity_curve = [10000, 10000, 10000, 10000]
        
        sharpe = BacktestEngine._calculate_sharpe_ratio(equity_curve)
        
        # Should return 0 when std dev is 0
        assert sharpe == 0.0
    
    def test_sharpe_ratio_empty_curve(self):
        """Test Sharpe ratio with empty equity curve."""
        equity_curve = []
        
        sharpe = BacktestEngine._calculate_sharpe_ratio(equity_curve)
        
        # Should return 0 for empty curve
        assert sharpe == 0.0
    
    def test_sharpe_ratio_single_value(self):
        """Test Sharpe ratio with single equity value."""
        equity_curve = [10000]
        
        sharpe = BacktestEngine._calculate_sharpe_ratio(equity_curve)
        
        # Should return 0 for single value (no returns)
        assert sharpe == 0.0
    
    def test_sharpe_ratio_two_values(self):
        """Test Sharpe ratio with only two equity values."""
        equity_curve = [10000, 10100]
        
        sharpe = BacktestEngine._calculate_sharpe_ratio(equity_curve)
        
        # With only one return, cannot calculate sample std dev
        # Should return 0
        assert sharpe == 0.0
    
    def test_sharpe_ratio_zero_equity(self):
        """Test Sharpe ratio when equity drops to zero."""
        equity_curve = [10000, 5000, 0]
        
        sharpe = BacktestEngine._calculate_sharpe_ratio(equity_curve)
        
        # Should calculate Sharpe ratio based on the returns
        # Return 1: (5000 - 10000) / 10000 = -0.5
        # Return 2: (0 - 5000) / 5000 = -1.0
        # Mean: -0.75, these are large negative returns
        # Sharpe should be negative
        assert sharpe < 0
    
    def test_sharpe_ratio_zero_starting_equity(self):
        """Test Sharpe ratio when starting equity is zero."""
        equity_curve = [0, 10000, 20000]
        
        sharpe = BacktestEngine._calculate_sharpe_ratio(equity_curve)
        
        # Cannot calculate return from zero equity
        # Should return 0
        assert sharpe == 0.0
    
    def test_sharpe_ratio_annualization_factor(self):
        """Test that Sharpe ratio uses correct annualization factor."""
        # Create equity curve with known daily return
        daily_return = 0.001  # 0.1% daily
        equity_curve = [10000 * ((1 + daily_return) ** i) for i in range(100)]
        
        sharpe = BacktestEngine._calculate_sharpe_ratio(equity_curve)
        
        # Calculate expected Sharpe manually
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        
        # Verify annualization factor is sqrt(252)
        expected_sharpe = (mean_return / std_dev) * math.sqrt(252)
        assert abs(sharpe - expected_sharpe) < 1e-10
        
        # Verify it's using 252 trading days, not 365 calendar days
        wrong_sharpe = (mean_return / std_dev) * math.sqrt(365)
        assert abs(sharpe - wrong_sharpe) > 0.01  # Should be different
    
    def test_sharpe_ratio_sample_vs_population_std(self):
        """Test that Sharpe ratio uses sample standard deviation (n-1)."""
        equity_curve = [10000, 10100, 10200, 10300, 10400]
        
        sharpe = BacktestEngine._calculate_sharpe_ratio(equity_curve)
        
        # Calculate with sample std dev (n-1)
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)
        
        mean_return = sum(returns) / len(returns)
        sample_variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        sample_std = math.sqrt(sample_variance)
        expected_sharpe_sample = (mean_return / sample_std) * math.sqrt(252)
        
        # Calculate with population std dev (n)
        pop_variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        pop_std = math.sqrt(pop_variance)
        expected_sharpe_pop = (mean_return / pop_std) * math.sqrt(252)
        
        # Verify we're using sample std dev
        assert abs(sharpe - expected_sharpe_sample) < 1e-10
        assert abs(sharpe - expected_sharpe_pop) > 0.01  # Should be different
