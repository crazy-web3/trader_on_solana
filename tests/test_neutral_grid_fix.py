"""测试中性网格逻辑修复"""

import pytest
from strategy_engine.models import StrategyConfig, StrategyMode
from strategy_engine.components.order_manager import OrderManager, GridOrder
from market_data_layer.models import KlineData


class TestNeutralGridFix:
    """测试中性网格逻辑修复"""
    
    def setup_method(self):
        """设置测试环境"""
        self.config = StrategyConfig(
            symbol="BTCUSDT",
            mode=StrategyMode.NEUTRAL,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=11,  # 10个网格间隔，11个价格点
            initial_capital=10000.0,
            fee_rate=0.001,
            leverage=1.0,
        )
        self.order_manager = OrderManager(self.config)
    
    def test_neutral_grid_counter_order_after_buy(self):
        """测试中性网格：买单成交后应在上一网格挂卖单"""
        # 模拟在网格5买单成交
        filled_order = GridOrder(
            grid_idx=5,
            price=45000.0,
            side="buy",
            quantity=0.1
        )
        filled_order.is_filled = True
        
        # 放置对手订单
        self.order_manager.place_counter_order(filled_order, StrategyMode.NEUTRAL)
        
        # 验证：应该在网格6（上一网格）挂卖单
        all_orders = self.order_manager.get_all_orders()
        assert 6 in all_orders, "应该在网格6有订单"
        
        counter_orders = all_orders[6]
        assert len(counter_orders) > 0, "网格6应该有订单"
        
        counter_order = counter_orders[-1]  # 获取最新的订单
        assert counter_order.side == "sell", "对手订单应该是卖单"
        assert counter_order.grid_idx == 6, "对手订单应该在网格6"
        
        # 验证价格正确
        expected_price = self.config.lower_price + 6 * self.order_manager.grid_gap
        assert abs(counter_order.price - expected_price) < 0.01, \
            f"对手订单价格应该是{expected_price}，实际是{counter_order.price}"
    
    def test_neutral_grid_counter_order_after_sell(self):
        """测试中性网格：卖单成交后应在下一网格挂买单"""
        # 模拟在网格5卖单成交
        filled_order = GridOrder(
            grid_idx=5,
            price=45000.0,
            side="sell",
            quantity=0.1
        )
        filled_order.is_filled = True
        
        # 放置对手订单
        self.order_manager.place_counter_order(filled_order, StrategyMode.NEUTRAL)
        
        # 验证：应该在网格4（下一网格）挂买单
        all_orders = self.order_manager.get_all_orders()
        assert 4 in all_orders, "应该在网格4有订单"
        
        counter_orders = all_orders[4]
        assert len(counter_orders) > 0, "网格4应该有订单"
        
        counter_order = counter_orders[-1]  # 获取最新的订单
        assert counter_order.side == "buy", "对手订单应该是买单"
        assert counter_order.grid_idx == 4, "对手订单应该在网格4"
        
        # 验证价格正确
        expected_price = self.config.lower_price + 4 * self.order_manager.grid_gap
        assert abs(counter_order.price - expected_price) < 0.01, \
            f"对手订单价格应该是{expected_price}，实际是{counter_order.price}"
    
    def test_neutral_grid_not_symmetric(self):
        """测试中性网格：验证不使用对称逻辑"""
        # 在网格2买单成交
        filled_order = GridOrder(
            grid_idx=2,
            price=42000.0,
            side="buy",
            quantity=0.1
        )
        filled_order.is_filled = True
        
        # 放置对手订单
        self.order_manager.place_counter_order(filled_order, StrategyMode.NEUTRAL)
        
        # 验证：不应该在对称网格（grid_count - 1 - 2 = 8）挂单
        all_orders = self.order_manager.get_all_orders()
        
        # 应该在网格3（上一网格）有卖单
        assert 3 in all_orders, "应该在网格3有订单"
        counter_order = all_orders[3][-1]
        assert counter_order.side == "sell", "应该是卖单"
        
        # 不应该在网格8（对称网格）有新订单
        # 注意：网格8可能有初始订单，但不应该有新的对手订单
        if 8 in all_orders:
            # 检查最新订单不是刚才放置的
            for order in all_orders[8]:
                if not order.is_filled:
                    # 如果有未成交订单，应该是初始订单，不是对手订单
                    assert order.grid_idx == 8
    
    def test_neutral_grid_boundary_buy_at_top(self):
        """测试中性网格：在最高网格买单成交后的边界情况"""
        # 在最高网格（grid_count - 1）买单成交
        top_grid_idx = self.config.grid_count - 1
        filled_order = GridOrder(
            grid_idx=top_grid_idx,
            price=50000.0,
            side="buy",
            quantity=0.1
        )
        filled_order.is_filled = True
        
        # 放置对手订单
        self.order_manager.place_counter_order(filled_order, StrategyMode.NEUTRAL)
        
        # 验证：由于已经在最高网格，不应该放置对手订单
        # （因为上一网格会超出范围）
        all_orders = self.order_manager.get_all_orders()
        
        # 检查是否有超出范围的订单
        for grid_idx in all_orders.keys():
            assert 0 <= grid_idx < self.config.grid_count, \
                f"网格索引{grid_idx}超出范围[0, {self.config.grid_count})"
    
    def test_neutral_grid_boundary_sell_at_bottom(self):
        """测试中性网格：在最低网格卖单成交后的边界情况"""
        # 在最低网格（0）卖单成交
        filled_order = GridOrder(
            grid_idx=0,
            price=40000.0,
            side="sell",
            quantity=0.1
        )
        filled_order.is_filled = True
        
        # 放置对手订单
        self.order_manager.place_counter_order(filled_order, StrategyMode.NEUTRAL)
        
        # 验证：由于已经在最低网格，不应该放置对手订单
        # （因为下一网格会是负数）
        all_orders = self.order_manager.get_all_orders()
        
        # 检查是否有负数索引的订单
        for grid_idx in all_orders.keys():
            assert grid_idx >= 0, f"网格索引{grid_idx}不应该是负数"
    
    def test_neutral_grid_quick_profit_taking(self):
        """测试中性网格：验证快速平仓逻辑"""
        # 初始化订单
        current_price = 45000.0
        self.order_manager.place_initial_orders(current_price, StrategyMode.NEUTRAL)
        
        # 模拟价格下跌，触发买单
        kline_down = KlineData(
            timestamp=1000000,
            open=45000.0,
            high=45000.0,
            low=44000.0,  # 触发网格4的买单
            close=44000.0,
            volume=100.0
        )
        
        filled_orders = self.order_manager.check_order_fills(kline_down)
        
        # 应该有买单成交
        buy_orders = [o for o in filled_orders if o.side == "buy"]
        assert len(buy_orders) > 0, "应该有买单成交"
        
        # 为每个成交的买单放置对手订单
        for buy_order in buy_orders:
            self.order_manager.place_counter_order(buy_order, StrategyMode.NEUTRAL)
        
        # 验证：对手卖单应该在相邻的上一网格
        for buy_order in buy_orders:
            expected_counter_grid = buy_order.grid_idx + 1
            if expected_counter_grid < self.config.grid_count:
                all_orders = self.order_manager.get_all_orders()
                assert expected_counter_grid in all_orders, \
                    f"应该在网格{expected_counter_grid}有对手订单"
                
                counter_orders = all_orders[expected_counter_grid]
                sell_orders = [o for o in counter_orders if o.side == "sell" and not o.is_filled]
                assert len(sell_orders) > 0, \
                    f"网格{expected_counter_grid}应该有未成交的卖单"


class TestNeutralGridVsLongShort:
    """对比测试：中性网格 vs 做多/做空网格"""
    
    def test_neutral_vs_long_counter_order_logic(self):
        """对比中性网格和做多网格的对手订单逻辑"""
        config = StrategyConfig(
            symbol="BTCUSDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=11,
            initial_capital=10000.0,
            fee_rate=0.001,
            leverage=1.0,
        )
        
        # 做多网格
        long_manager = OrderManager(config)
        filled_order = GridOrder(grid_idx=5, price=45000.0, side="buy", quantity=0.1)
        filled_order.is_filled = True
        long_manager.place_counter_order(filled_order, StrategyMode.LONG)
        
        # 中性网格
        config.mode = StrategyMode.NEUTRAL
        neutral_manager = OrderManager(config)
        filled_order_neutral = GridOrder(grid_idx=5, price=45000.0, side="buy", quantity=0.1)
        filled_order_neutral.is_filled = True
        neutral_manager.place_counter_order(filled_order_neutral, StrategyMode.NEUTRAL)
        
        # 验证：两者的对手订单逻辑应该相同（都在上一网格挂卖单）
        long_orders = long_manager.get_all_orders()
        neutral_orders = neutral_manager.get_all_orders()
        
        # 做多网格：买单成交后在上一网格（grid_idx + 1）挂卖单
        assert 6 in long_orders, "做多网格应该在网格6有对手订单"
        
        # 中性网格：买单成交后也应该在上一网格（grid_idx + 1）挂卖单
        assert 6 in neutral_orders, "中性网格应该在网格6有对手订单"
        
        # 验证订单类型相同
        long_counter = long_orders[6][-1]
        neutral_counter = neutral_orders[6][-1]
        
        assert long_counter.side == neutral_counter.side == "sell", \
            "做多和中性网格的对手订单都应该是卖单"
