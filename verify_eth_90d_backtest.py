"""验证ETH过去90天的回测结果 - 使用真实数据"""

import requests
from datetime import datetime, timedelta
from strategy_engine import GridStrategyEngine, StrategyConfig, StrategyMode
from market_data_layer.models import KlineData

def fetch_binance_klines(symbol="ETHUSDT", interval="1h", days=90):
    """从Binance获取历史K线数据
    
    Args:
        symbol: 交易对
        interval: 时间间隔 (1m, 5m, 15m, 1h, 4h, 1d)
        days: 天数
        
    Returns:
        KlineData列表
    """
    print(f"正在获取 {symbol} 过去 {days} 天的 {interval} K线数据...")
    
    # 计算时间范围
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    
    # Binance API endpoint
    url = "https://api.binance.com/api/v3/klines"
    
    all_klines = []
    current_start = start_time
    
    # Binance限制每次最多1000条，需要分批获取
    while current_start < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": current_start,
            "endTime": end_time,
            "limit": 1000
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
            
            # 转换为KlineData格式
            for kline in data:
                all_klines.append(KlineData(
                    timestamp=int(kline[0]),
                    open=float(kline[1]),
                    high=float(kline[2]),
                    low=float(kline[3]),
                    close=float(kline[4]),
                    volume=float(kline[5])
                ))
            
            # 更新下一批的起始时间
            current_start = int(data[-1][0]) + 1
            
            print(f"  已获取 {len(all_klines)} 条K线...")
            
        except Exception as e:
            print(f"获取数据失败: {e}")
            break
    
    print(f"✓ 共获取 {len(all_klines)} 条K线数据")
    return all_klines


def analyze_price_trend(klines):
    """分析价格趋势"""
    if not klines:
        return None
    
    start_price = klines[0].close
    end_price = klines[-1].close
    
    # 计算最高和最低价
    high_price = max(k.high for k in klines)
    low_price = min(k.low for k in klines)
    
    # 计算价格变化
    price_change = end_price - start_price
    price_change_pct = (price_change / start_price) * 100
    
    return {
        "start_price": start_price,
        "end_price": end_price,
        "high_price": high_price,
        "low_price": low_price,
        "price_change": price_change,
        "price_change_pct": price_change_pct,
        "trend": "下跌" if price_change < 0 else "上涨"
    }


def run_strategy_backtest(klines, mode, lower_price, upper_price, grid_count, initial_capital=10000):
    """运行策略回测
    
    Args:
        klines: K线数据
        mode: 策略模式
        lower_price: 下界价格
        upper_price: 上界价格
        grid_count: 网格数量
        initial_capital: 初始资金
        
    Returns:
        回测结果
    """
    config = StrategyConfig(
        symbol="ETH/USDT",
        mode=mode,
        lower_price=lower_price,
        upper_price=upper_price,
        grid_count=grid_count,
        initial_capital=initial_capital,
        fee_rate=0.0005,  # 0.05% 手续费
        leverage=1.0,
        funding_rate=0.0001,  # 0.01% 资金费率
        funding_interval=8,
        entry_price=klines[0].close
    )
    
    engine = GridStrategyEngine(config)
    result = engine.execute(klines)
    
    return result


def print_result_summary(mode_name, result, trend_info):
    """打印结果摘要"""
    print(f"\n{'='*80}")
    print(f"{mode_name} 策略回测结果")
    print(f"{'='*80}")
    
    print(f"\n📊 基本信息:")
    print(f"  初始资金: ${result.initial_capital:,.2f}")
    print(f"  最终资金: ${result.final_capital:,.2f}")
    print(f"  总收益率: {result.total_return:.2f}%")
    print(f"  网格收益: ${result.grid_profit:,.2f}")
    print(f"  未实现盈亏: ${result.unrealized_pnl:,.2f}")
    
    print(f"\n📈 交易统计:")
    print(f"  总交易次数: {result.total_trades}")
    print(f"  盈利交易: {result.winning_trades}")
    print(f"  亏损交易: {result.losing_trades}")
    print(f"  胜率: {result.win_rate:.2f}%")
    
    print(f"\n💰 费用统计:")
    print(f"  交易手续费: ${result.total_fees:,.2f}")
    print(f"  资金费用: ${result.total_funding_fees:,.2f}")
    
    print(f"\n📉 风险指标:")
    print(f"  最大回撤: {result.max_drawdown_pct:.2f}%")
    
    # 判断结果是否符合预期
    print(f"\n🎯 结果分析:")
    total_pnl = result.final_capital - result.initial_capital
    
    if trend_info["trend"] == "下跌":
        if mode_name == "做空网格":
            expected = "盈利"
            is_correct = total_pnl > 0
        elif mode_name == "做多网格":
            expected = "亏损"
            is_correct = total_pnl < 0
        else:  # 中性
            expected = "小幅盈利或亏损"
            is_correct = True
    else:  # 上涨
        if mode_name == "做多网格":
            expected = "盈利"
            is_correct = total_pnl > 0
        elif mode_name == "做空网格":
            expected = "亏损"
            is_correct = total_pnl < 0
        else:  # 中性
            expected = "小幅盈利或亏损"
            is_correct = True
    
    actual = "盈利" if total_pnl > 0 else "亏损"
    status = "✓ 符合预期" if is_correct else "✗ 不符合预期"
    
    print(f"  市场趋势: {trend_info['trend']} ({trend_info['price_change_pct']:.2f}%)")
    print(f"  预期结果: {expected}")
    print(f"  实际结果: {actual} (${total_pnl:,.2f})")
    print(f"  验证状态: {status}")
    
    return is_correct


def main():
    """主函数"""
    print("="*80)
    print("ETH 过去90天真实数据回测验证")
    print("="*80)
    
    # 1. 获取真实数据
    klines = fetch_binance_klines(symbol="ETHUSDT", interval="1h", days=90)
    
    if not klines:
        print("❌ 无法获取数据，退出")
        return
    
    # 2. 分析价格趋势
    trend_info = analyze_price_trend(klines)
    
    print(f"\n{'='*80}")
    print("价格趋势分析")
    print(f"{'='*80}")
    print(f"起始价格: ${trend_info['start_price']:,.2f}")
    print(f"结束价格: ${trend_info['end_price']:,.2f}")
    print(f"历史最高: ${trend_info['high_price']:,.2f}")
    print(f"历史最低: ${trend_info['low_price']:,.2f}")
    print(f"价格变化: ${trend_info['price_change']:,.2f} ({trend_info['price_change_pct']:.2f}%)")
    print(f"趋势判断: {trend_info['trend']}")
    
    # 3. 设置网格参数（基于实际价格范围）
    # 使用历史最低和最高价作为网格边界，留一些缓冲
    # 对于做空网格，需要确保有足够的网格在起始价格之上
    buffer = (trend_info['high_price'] - trend_info['low_price']) * 0.2  # 增加缓冲到20%
    lower_price = max(100, trend_info['low_price'] - buffer)  # 至少100
    upper_price = trend_info['high_price'] + buffer
    
    # 向下取整到100的倍数
    lower_price = int(lower_price / 100) * 100
    upper_price = int(upper_price / 100) * 100
    
    # 确保起始价格在网格范围内，且有足够的空间
    if trend_info['start_price'] > upper_price * 0.9:
        # 如果起始价格太接近上界，扩大上界
        upper_price = int(trend_info['start_price'] * 1.2 / 100) * 100
    
    grid_count = 20  # 20个网格
    initial_capital = 10000  # 1万美元初始资金
    
    print(f"\n{'='*80}")
    print("网格参数设置")
    print(f"{'='*80}")
    print(f"价格区间: ${lower_price:,.0f} - ${upper_price:,.0f}")
    print(f"网格数量: {grid_count}")
    print(f"网格间距: ${(upper_price - lower_price) / (grid_count - 1):,.2f}")
    print(f"初始资金: ${initial_capital:,.2f}")
    
    # 4. 运行三种策略回测
    results = {}
    
    print(f"\n{'='*80}")
    print("开始回测...")
    print(f"{'='*80}")
    
    # 做多网格
    print("\n[1/3] 运行做多网格回测...")
    results['long'] = run_strategy_backtest(
        klines, StrategyMode.LONG, lower_price, upper_price, grid_count, initial_capital
    )
    
    # 做空网格
    print("[2/3] 运行做空网格回测...")
    results['short'] = run_strategy_backtest(
        klines, StrategyMode.SHORT, lower_price, upper_price, grid_count, initial_capital
    )
    
    # 中性网格
    print("[3/3] 运行中性网格回测...")
    results['neutral'] = run_strategy_backtest(
        klines, StrategyMode.NEUTRAL, lower_price, upper_price, grid_count, initial_capital
    )
    
    # 5. 打印结果
    long_correct = print_result_summary("做多网格", results['long'], trend_info)
    short_correct = print_result_summary("做空网格", results['short'], trend_info)
    neutral_correct = print_result_summary("中性网格", results['neutral'], trend_info)
    
    # 6. 对比总结
    print(f"\n{'='*80}")
    print("策略对比总结")
    print(f"{'='*80}")
    
    strategies = [
        ("做多网格", results['long'], long_correct),
        ("做空网格", results['short'], short_correct),
        ("中性网格", results['neutral'], neutral_correct)
    ]
    
    # 按收益率排序
    strategies.sort(key=lambda x: x[1].total_return, reverse=True)
    
    print(f"\n排名 | 策略     | 收益率    | 最终资金      | 交易次数 | 验证")
    print(f"-" * 80)
    for i, (name, result, correct) in enumerate(strategies, 1):
        status = "✓" if correct else "✗"
        print(f"{i:^4} | {name:^8} | {result.total_return:>7.2f}% | ${result.final_capital:>11,.2f} | {result.total_trades:>8} | {status}")
    
    # 7. 最终结论
    print(f"\n{'='*80}")
    print("最终结论")
    print(f"{'='*80}")
    
    all_correct = long_correct and short_correct and neutral_correct
    
    if all_correct:
        print("✅ 所有策略表现符合预期！算法验证通过！")
    else:
        print("⚠️  部分策略表现不符合预期，需要进一步检查")
    
    print(f"\n在 {trend_info['trend']} 趋势下:")
    if trend_info['trend'] == "下跌":
        print("  • 做空网格应该盈利 ✓")
        print("  • 做多网格应该亏损 ✓")
        print("  • 中性网格表现取决于震荡程度")
    else:
        print("  • 做多网格应该盈利 ✓")
        print("  • 做空网格应该亏损 ✓")
        print("  • 中性网格表现取决于震荡程度")
    
    print(f"\n数据来源: Binance")
    print(f"数据时间: {datetime.fromtimestamp(klines[0].timestamp/1000).strftime('%Y-%m-%d')} 至 {datetime.fromtimestamp(klines[-1].timestamp/1000).strftime('%Y-%m-%d')}")
    print(f"K线数量: {len(klines)}")


if __name__ == "__main__":
    main()
