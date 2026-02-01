"""演示动态仓位权重计算"""

from strategy_engine.components.position_weight_calculator import (
    PositionWeightCalculator,
    VolatilityCalculator,
    WeightConfig
)


def demo_uniform_vs_std_dev():
    """对比均匀权重和标准差权重"""
    
    print("=" * 80)
    print("仓位权重策略对比")
    print("=" * 80)
    print()
    
    # 历史价格数据（BTC价格波动）
    historical_prices = [
        44000, 45000, 46000, 44500, 45500,
        43000, 47000, 45000, 44000, 46000,
        45500, 44500, 46500, 45000, 44000
    ]
    
    mean_price = sum(historical_prices) / len(historical_prices)
    print(f"历史价格统计：")
    print(f"  样本数量：{len(historical_prices)}")
    print(f"  平均价格：${mean_price:,.0f}")
    print(f"  最低价格：${min(historical_prices):,.0f}")
    print(f"  最高价格：${max(historical_prices):,.0f}")
    print()
    
    # 配置
    grid_count = 11
    lower_price = 40000.0
    upper_price = 50000.0
    capital = 10000.0
    leverage = 2.0
    
    print(f"网格配置：")
    print(f"  价格区间：${lower_price:,.0f} - ${upper_price:,.0f}")
    print(f"  网格数量：{grid_count}")
    print(f"  初始资金：${capital:,.0f}")
    print(f"  杠杆倍数：{leverage}x")
    print()
    
    # 方案1：均匀权重
    print("方案1：均匀权重（传统方法）")
    print("-" * 80)
    
    calc_uniform = PositionWeightCalculator()
    uniform_weights = calc_uniform.calculate_uniform_weights(grid_count)
    uniform_prices = calc_uniform._calculate_uniform_grid_prices(
        grid_count, lower_price, upper_price
    )
    
    print(f"每个网格权重：{uniform_weights[0]:.4f} ({uniform_weights[0]*100:.2f}%)")
    print()
    
    print("网格分布：")
    for i, (price, weight) in enumerate(zip(uniform_prices[:5], uniform_weights[:5])):
        size = calc_uniform.calculate_position_size(capital, price, weight, leverage)
        print(f"  网格{i}: ${price:,.0f}, 权重{weight:.4f}, 数量{size:.6f} BTC")
    print(f"  ... (共{grid_count}个网格)")
    print()
    
    # 方案2：标准差权重
    print("方案2：标准差权重（优化方法）")
    print("-" * 80)
    
    config = WeightConfig(
        method="std_dev",
        std_dev_multipliers=[-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0],
        weights=[0.5, 0.3, 0.1, 0.1, 0.3, 0.5]  # 极端位置权重更大
    )
    calc_std = PositionWeightCalculator(config)
    
    std_prices, std_weights = calc_std.calculate_std_dev_weights(
        historical_prices,
        grid_count,
        lower_price,
        upper_price
    )
    
    print(f"生成{len(std_prices)}个网格（基于标准差）")
    print()
    
    print("网格分布：")
    for i, (price, weight) in enumerate(zip(std_prices, std_weights)):
        size = calc_std.calculate_position_size(capital, price, weight, leverage)
        print(f"  网格{i}: ${price:,.0f}, 权重{weight:.4f} ({weight*100:.2f}%), 数量{size:.6f} BTC")
    print()
    
    # 对比分析
    print("📊 对比分析：")
    print(f"  均匀权重：所有网格权重相同，资金平均分配")
    print(f"  标准差权重：极端价格权重更大，符合均值回归策略")
    print(f"  优势：在价格偏离均值时，有更多资金可以建仓")
    print()


def demo_volatility_adjustment():
    """演示波动率自适应调整"""
    
    print("=" * 80)
    print("波动率自适应网格间距")
    print("=" * 80)
    print()
    
    calc = PositionWeightCalculator()
    base_spacing = 1000.0
    
    # 低波动率场景
    print("场景1：低波动率市场")
    print("-" * 80)
    low_vol_data = [
        (45100, 44900, 45000),
        (45200, 44800, 45000),
        (45150, 44850, 45000),
        (45250, 44750, 45000),
        (45100, 44900, 45000),
    ]
    
    low_vol_atr = VolatilityCalculator.calculate_atr(low_vol_data, period=4)
    low_vol_spacing = calc.calculate_atr_based_spacing(
        low_vol_data, base_spacing, period=4
    )
    
    print(f"  ATR: ${low_vol_atr:.2f}")
    print(f"  基础间距: ${base_spacing:,.0f}")
    print(f"  调整后间距: ${low_vol_spacing:,.0f}")
    print(f"  调整幅度: {((low_vol_spacing - base_spacing) / base_spacing * 100):.1f}%")
    print(f"  说明：低波动率，间距略微增加")
    print()
    
    # 高波动率场景
    print("场景2：高波动率市场")
    print("-" * 80)
    high_vol_data = [
        (46000, 44000, 45000),
        (47000, 43000, 45000),
        (48000, 42000, 45000),
        (47500, 42500, 45000),
        (46500, 43500, 45000),
    ]
    
    high_vol_atr = VolatilityCalculator.calculate_atr(high_vol_data, period=4)
    high_vol_spacing = calc.calculate_atr_based_spacing(
        high_vol_data, base_spacing, period=4
    )
    
    print(f"  ATR: ${high_vol_atr:.2f}")
    print(f"  基础间距: ${base_spacing:,.0f}")
    print(f"  调整后间距: ${high_vol_spacing:,.0f}")
    print(f"  调整幅度: {((high_vol_spacing - base_spacing) / base_spacing * 100):.1f}%")
    print(f"  说明：高波动率，间距显著增加")
    print()
    
    # 对比
    print("📊 对比分析：")
    print(f"  低波动率间距: ${low_vol_spacing:,.0f}")
    print(f"  高波动率间距: ${high_vol_spacing:,.0f}")
    print(f"  差异: ${high_vol_spacing - low_vol_spacing:,.0f} ({((high_vol_spacing / low_vol_spacing - 1) * 100):.1f}%)")
    print(f"  优势：根据市场波动自动调整，避免过度交易或错失机会")
    print()


def demo_dynamic_weights():
    """演示动态权重调整"""
    
    print("=" * 80)
    print("动态权重调整（基于当前价格）")
    print("=" * 80)
    print()
    
    calc = PositionWeightCalculator()
    
    grid_prices = [40000, 42000, 44000, 46000, 48000, 50000]
    current_price = 45000.0
    
    print(f"网格价格: {[f'${p:,.0f}' for p in grid_prices]}")
    print(f"当前价格: ${current_price:,.0f}")
    print()
    
    # 距离权重
    print("方法1：距离权重（距离越近权重越大）")
    print("-" * 80)
    distance_weights = calc.calculate_dynamic_weights(
        current_price, grid_prices, method="distance"
    )
    
    for price, weight in zip(grid_prices, distance_weights):
        distance = abs(price - current_price)
        bar = "█" * int(weight * 100)
        print(f"  ${price:,.0f}: {weight:.4f} ({weight*100:.2f}%) {bar}")
    print()
    
    # 指数权重
    print("方法2：指数权重（指数衰减）")
    print("-" * 80)
    exp_weights = calc.calculate_dynamic_weights(
        current_price, grid_prices, method="exponential"
    )
    
    for price, weight in zip(grid_prices, exp_weights):
        distance = abs(price - current_price)
        bar = "█" * int(weight * 100)
        print(f"  ${price:,.0f}: {weight:.4f} ({weight*100:.2f}%) {bar}")
    print()
    
    print("📊 说明：")
    print(f"  动态权重根据当前价格位置调整")
    print(f"  距离当前价格越近的网格，权重越大")
    print(f"  优势：更灵活地响应市场变化")
    print()


def demo_complete_example():
    """完整示例：从历史数据到仓位分配"""
    
    print("=" * 80)
    print("完整示例：动态仓位管理")
    print("=" * 80)
    print()
    
    # 历史数据
    historical_prices = [
        44000, 45000, 46000, 44500, 45500,
        43000, 47000, 45000, 44000, 46000,
        45500, 44500, 46500, 45000, 44000
    ]
    
    # 计算波动率
    volatility = VolatilityCalculator.calculate_historical_volatility(
        historical_prices, period=10
    )
    
    print(f"市场分析：")
    print(f"  历史价格样本：{len(historical_prices)}个")
    print(f"  平均价格：${sum(historical_prices)/len(historical_prices):,.0f}")
    print(f"  年化波动率：{volatility:.2%}")
    print()
    
    # 配置
    capital = 10000.0
    leverage = 2.0
    lower_price = 40000.0
    upper_price = 50000.0
    
    # 使用标准差权重
    config = WeightConfig(method="std_dev")
    calc = PositionWeightCalculator(config)
    
    grid_prices, weights = calc.calculate_std_dev_weights(
        historical_prices,
        grid_count=7,
        lower_price=lower_price,
        upper_price=upper_price
    )
    
    print(f"仓位分配方案：")
    print(f"  初始资金：${capital:,.0f}")
    print(f"  杠杆倍数：{leverage}x")
    print(f"  可用资金：${capital * leverage:,.0f}")
    print()
    
    print("网格配置：")
    print(f"{'网格':<6} {'价格':<12} {'权重':<12} {'数量':<15} {'价值':<12}")
    print("-" * 70)
    
    total_value = 0
    for i, (price, weight) in enumerate(zip(grid_prices, weights)):
        size = calc.calculate_position_size(capital, price, weight, leverage)
        value = size * price
        total_value += value
        
        print(f"{i:<6} ${price:<11,.0f} {weight:<11.4f} {size:<14.6f} ${value:<11,.2f}")
    
    print("-" * 70)
    print(f"{'总计':<6} {'':<12} {sum(weights):<11.4f} {'':<14} ${total_value:<11,.2f}")
    print()
    
    print("📊 资金使用情况：")
    print(f"  总仓位价值：${total_value:,.2f}")
    print(f"  可用资金：${capital * leverage:,.2f}")
    print(f"  使用率：{(total_value / (capital * leverage) * 100):.1f}%")
    print()


if __name__ == "__main__":
    demo_uniform_vs_std_dev()
    print()
    demo_volatility_adjustment()
    print()
    demo_dynamic_weights()
    print()
    demo_complete_example()
    
    print("=" * 80)
    print("演示完成！")
    print("=" * 80)
    print()
    print("运行测试验证实现：")
    print("  ./venv/bin/pytest tests/test_position_weight_calculator.py -v")
    print()
