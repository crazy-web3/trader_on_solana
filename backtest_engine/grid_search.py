"""Grid search optimizer for parameter tuning."""

from typing import Dict, List, Tuple
from itertools import product
import logging
from backtest_engine.models import (
    BacktestConfig,
    BacktestResult,
    GridSearchResult,
    StrategyMode,
)
from backtest_engine.engine import BacktestEngine
from backtest_engine.exceptions import InvalidConfigError


logger = logging.getLogger(__name__)


class GridSearchOptimizer:
    """Grid search optimizer for strategy parameter tuning.
    
    Supports parameter ranges for:
    - Grid count
    - Price boundaries (lower and upper)
    """
    
    def __init__(self, engine: BacktestEngine = None):
        """Initialize grid search optimizer.
        
        Args:
            engine: Backtest engine (default: new instance)
        """
        self.engine = engine or BacktestEngine()
    
    def optimize(
        self,
        base_config: BacktestConfig,
        parameter_ranges: Dict[str, List],
        metric: str = "total_return",
    ) -> GridSearchResult:
        """Run grid search optimization.
        
        Args:
            base_config: Base backtest configuration
            parameter_ranges: Parameter ranges to search
                Example: {
                    "grid_count": [5, 10, 15, 20],
                    "lower_price": [85000, 87000, 89000],
                    "upper_price": [91000, 93000, 95000],
                }
            metric: Metric to optimize (total_return, annual_return, sharpe_ratio)
            
        Returns:
            Grid search result with best parameters
            
        Raises:
            InvalidConfigError: If parameter ranges are invalid
        """
        self._validate_parameter_ranges(parameter_ranges)
        
        # Generate all parameter combinations
        param_names = list(parameter_ranges.keys())
        param_values = [parameter_ranges[name] for name in param_names]
        combinations = list(product(*param_values))
        
        logger.info(f"Running grid search with {len(combinations)} combinations")
        
        results = []
        best_result = None
        best_metric_value = float('-inf')
        
        for i, combo in enumerate(combinations):
            try:
                # Create config with current parameters
                config = self._create_config(base_config, param_names, combo)
                
                # Run backtest
                result = self.engine.run_backtest(config)
                results.append(result)
                
                # Get metric value
                metric_value = self._get_metric_value(result, metric)
                
                # Update best result
                if metric_value > best_metric_value:
                    best_metric_value = metric_value
                    best_result = result
                
                logger.info(
                    f"Combination {i+1}/{len(combinations)}: "
                    f"{metric}={metric_value:.4f}"
                )
            
            except Exception as e:
                logger.warning(f"Skipping combination {combo}: {str(e)}")
                continue
        
        if not results:
            raise InvalidConfigError("No valid parameter combinations found")
        
        # Create best parameters dict
        best_params = {}
        for name, value in zip(param_names, combinations[results.index(best_result)]):
            best_params[name] = value
        
        return GridSearchResult(
            best_result=best_result,
            all_results=results,
            best_params=best_params,
            parameter_ranges=parameter_ranges,
        )
    
    def _validate_parameter_ranges(self, parameter_ranges: Dict) -> None:
        """Validate parameter ranges.
        
        Args:
            parameter_ranges: Parameter ranges
            
        Raises:
            InvalidConfigError: If ranges are invalid
        """
        valid_params = {"grid_count", "lower_price", "upper_price"}
        
        for param in parameter_ranges.keys():
            if param not in valid_params:
                raise InvalidConfigError(f"Invalid parameter: {param}")
            
            values = parameter_ranges[param]
            if not isinstance(values, list) or len(values) == 0:
                raise InvalidConfigError(f"Invalid range for {param}")
    
    def _create_config(
        self,
        base_config: BacktestConfig,
        param_names: List[str],
        param_values: Tuple,
    ) -> BacktestConfig:
        """Create config with specific parameters.
        
        Args:
            base_config: Base configuration
            param_names: Parameter names
            param_values: Parameter values
            
        Returns:
            New configuration
        """
        config_dict = {
            "symbol": base_config.symbol,
            "mode": base_config.mode,
            "lower_price": base_config.lower_price,
            "upper_price": base_config.upper_price,
            "grid_count": base_config.grid_count,
            "initial_capital": base_config.initial_capital,
            "start_date": base_config.start_date,
            "end_date": base_config.end_date,
            "fee_rate": base_config.fee_rate,
        }
        
        # Update with current parameters
        for name, value in zip(param_names, param_values):
            config_dict[name] = value
        
        return BacktestConfig(**config_dict)
    
    @staticmethod
    def _get_metric_value(result: BacktestResult, metric: str) -> float:
        """Get metric value from result.
        
        Args:
            result: Backtest result
            metric: Metric name
            
        Returns:
            Metric value
        """
        if metric == "total_return":
            return result.metrics.total_return
        elif metric == "annual_return":
            return result.metrics.annual_return
        elif metric == "sharpe_ratio":
            return result.metrics.sharpe_ratio
        elif metric == "win_rate":
            return result.metrics.win_rate
        else:
            raise ValueError(f"Unknown metric: {metric}")
