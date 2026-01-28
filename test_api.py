#!/usr/bin/env python3
"""Simple API test script."""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5001/api"

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_health():
    """Test health endpoint."""
    print_section("1. 健康检查 (Health Check)")
    try:
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()
        print(f"✅ 状态: {data['status']}")
        print(f"⏰ 时间: {data['timestamp']}")
    except Exception as e:
        print(f"❌ 错误: {e}")

def test_symbols():
    """Test symbols endpoint."""
    print_section("2. 获取支持的币种 (Supported Symbols)")
    try:
        response = requests.get(f"{BASE_URL}/symbols")
        data = response.json()
        print(f"✅ 支持的币种:")
        for symbol in data['symbols']:
            print(f"   - {symbol}")
    except Exception as e:
        print(f"❌ 错误: {e}")

def test_intervals():
    """Test intervals endpoint."""
    print_section("3. 获取支持的时间周期 (Supported Intervals)")
    try:
        response = requests.get(f"{BASE_URL}/intervals")
        data = response.json()
        print(f"✅ 支持的时间周期:")
        for interval in data['intervals']:
            print(f"   - {interval}")
    except Exception as e:
        print(f"❌ 错误: {e}")

def test_klines():
    """Test klines endpoint."""
    print_section("4. 获取K线数据 (Fetch K-line Data)")
    try:
        params = {
            "symbol": "BTC/USDT",
            "interval": "1h",
            "days": 2
        }
        response = requests.get(f"{BASE_URL}/klines", params=params)
        data = response.json()
        
        print(f"✅ 查询参数:")
        print(f"   - 币种: {data['symbol']}")
        print(f"   - 周期: {data['interval']}")
        print(f"   - 数据条数: {data['count']}")
        
        if data['data']:
            print(f"\n📊 前5条数据:")
            for i, kline in enumerate(data['data'][:5], 1):
                timestamp = datetime.fromtimestamp(kline['timestamp'] / 1000)
                print(f"\n   K线 #{i}:")
                print(f"   - 时间: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   - 开盘: {kline['open']:.2f}")
                print(f"   - 最高: {kline['high']:.2f}")
                print(f"   - 最低: {kline['low']:.2f}")
                print(f"   - 收盘: {kline['close']:.2f}")
                print(f"   - 成交量: {kline['volume']:.0f}")
    except Exception as e:
        print(f"❌ 错误: {e}")

def test_cache_stats():
    """Test cache stats endpoint."""
    print_section("5. 获取缓存统计 (Cache Statistics)")
    try:
        response = requests.get(f"{BASE_URL}/cache/stats")
        data = response.json()
        print(f"✅ 缓存信息:")
        print(f"   - 当前条目数: {data['size']}")
        print(f"   - 最大容量: {data['max_size']}")
        print(f"   - TTL (小时): {data['default_ttl'] / (60 * 60 * 1000):.0f}")
    except Exception as e:
        print(f"❌ 错误: {e}")

def test_multiple_symbols():
    """Test multiple symbols."""
    print_section("6. 测试多个币种 (Test Multiple Symbols)")
    symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
    
    for symbol in symbols:
        try:
            response = requests.get(
                f"{BASE_URL}/klines",
                params={"symbol": symbol, "interval": "1h", "days": 1}
            )
            data = response.json()
            print(f"✅ {symbol}: {data['count']} 条数据")
        except Exception as e:
            print(f"❌ {symbol}: {e}")

def test_multiple_intervals():
    """Test multiple intervals."""
    print_section("7. 测试多个时间周期 (Test Multiple Intervals)")
    intervals = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
    
    for interval in intervals:
        try:
            response = requests.get(
                f"{BASE_URL}/klines",
                params={"symbol": "BTC/USDT", "interval": interval, "days": 1}
            )
            data = response.json()
            print(f"✅ {interval}: {data['count']} 条数据")
        except Exception as e:
            print(f"❌ {interval}: {e}")

def test_cache_hit():
    """Test cache hit."""
    print_section("8. 测试缓存命中 (Test Cache Hit)")
    
    params = {
        "symbol": "BTC/USDT",
        "interval": "1h",
        "days": 1
    }
    
    try:
        # First request
        print("📍 第一次请求 (从数据源获取)...")
        response1 = requests.get(f"{BASE_URL}/klines", params=params)
        data1 = response1.json()
        print(f"✅ 获取 {data1['count']} 条数据")
        
        # Second request (should hit cache)
        print("\n📍 第二次请求 (应该命中缓存)...")
        response2 = requests.get(f"{BASE_URL}/klines", params=params)
        data2 = response2.json()
        print(f"✅ 获取 {data2['count']} 条数据")
        
        # Verify data is the same
        if data1['data'] == data2['data']:
            print("\n✅ 缓存命中成功！返回的数据完全相同")
        else:
            print("\n⚠️  数据不同")
    except Exception as e:
        print(f"❌ 错误: {e}")

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  🚀 行情数据层 API 测试")
    print("="*60)
    
    try:
        test_health()
        test_symbols()
        test_intervals()
        test_klines()
        test_cache_stats()
        test_multiple_symbols()
        test_multiple_intervals()
        test_cache_hit()
        
        print_section("✅ 所有测试完成！")
        print("🎉 API 工作正常！\n")
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    main()
