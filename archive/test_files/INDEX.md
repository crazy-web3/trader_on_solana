# Test Files Index

This directory contains Python test scripts and debugging utilities for the trading bot project.

## API Tests
- `test_api.py` - General API endpoint testing
- `test_backend_api.py` - Backend API comprehensive testing
- `test_wallet_auth.py` - Wallet authentication testing

## Strategy Tests
- `test_strategy.py` - Basic strategy engine testing
- `test_backtest.py` - Backtest engine testing
- `test_complete_cycle.py` - End-to-end cycle testing

## Grid Strategy Tests
- `test_correct_grid.py` - Grid strategy correctness testing
- `test_final_grid.py` - Final grid implementation testing
- `test_grid_logic.py` - Grid logic validation
- `test_neutral_grid.py` - Neutral grid strategy testing
- `test_from_bottom.py` - Bottom-up grid testing
- `test_new_initialization.py` - New initialization logic testing

## Feature Tests
- `test_leverage_initial.py` - Leverage functionality testing
- `test_parameter_alignment.py` - Parameter alignment verification

## Debug Tools
- `debug_grid.py` - Grid strategy debugging utility

## Usage
Run any test file with Python:
```bash
# Example
python test_strategy.py
python debug_grid.py
```

## Requirements
- Python 3.8+
- All project dependencies installed (`pip install -r requirements.txt`)
- Backend services running (for integration tests)

## Purpose
These files were created during development to test individual components, validate functionality, and debug issues. They serve as both tests and documentation of expected behavior.