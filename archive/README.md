# Archive Directory

This directory contains archived files that were moved from the root directory for better project organization.

## Directory Structure

### `/test_files/`
Contains all test scripts and debugging files:
- `test_*.py` - Python test scripts for various components
- `debug_grid.py` - Grid strategy debugging script

### `/html_demos/`
Contains HTML demonstration and test files:
- `test_*.html` - HTML test pages for UI components
- `backtest.html` - Backtest demonstration page
- `dashboard.html` - Dashboard demo
- `index.html` - Main index page

### `/scripts/`
Contains utility scripts:
- `run.bat` - Windows startup script
- `run.sh` - Unix/Linux startup script
- `verify_fixes.sh` - Fix verification script

### `/pic/`
Contains demonstration screenshots:
- `image copy 0.png` - Market data page demonstration
- `image copy 1.png` - Strategy backtest page demonstration  
- `image copy 2.png` - Full backtest comparison demonstration
- `image copy 3.png` - Parameter optimization demonstration

### `/config/`
Contains configuration files:
- `docker-compose.yml` - Docker composition configuration
- `Dockerfile.backend` - Backend Docker configuration
- `wallet_whitelist.json` - Wallet whitelist configuration

## Purpose

These files were moved to improve the root directory structure and make the project more maintainable. All files remain functional and can be accessed from their new locations.

## Usage

To use any archived file, reference it with the new path:
```bash
# Example: Run a test file
python archive/test_files/test_strategy.py

# Example: View HTML demo
open archive/html_demos/test_chart.html
```

## Archive Date
Created: $(date)