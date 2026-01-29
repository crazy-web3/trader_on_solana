#!/usr/bin/env python3
"""
测试后端API是否返回正确的数据格式
"""

import requests
import json
import sys

def test_strategy_backtest():
    """测试策略回测API"""
    print("=== 测试策略回测API ===")
    
    url = "http://localhost:5001/api/strategy/backtest"
    data = {
        "symbol": "ETH/USDT",
        "mode": "long",
        "initial_capital": 10000,
        "days": 7,  # 使用较短的时间以便快速测试
        "leverage": 1.0,
        "funding_rate": 0.0,
        "funding_interval": 8,
        "auto_calculate_range": True
    }
    
    try:
        print(f"发送请求到: {url}")
        print(f"请求数据: {json.dumps(data, indent=2)}")
        
        response = requests.post(url, json=data, timeout=30)
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API调用成功!")
            
            # 检查关键字段
            required_fields = ["equity_curve", "timestamps", "total_return", "final_capital"]
            missing_fields = []
            
            for field in required_fields:
                if field not in result:
                    missing_fields.append(field)
                else:
                    if field == "equity_curve":
                        print(f"  equity_curve 长度: {len(result[field])}")
                        print(f"  equity_curve 前5个值: {result[field][:5]}")
                    elif field == "timestamps":
                        print(f"  timestamps 长度: {len(result[field])}")
                        print(f"  timestamps 前3个值: {result[field][:3]}")
                    else:
                        print(f"  {field}: {result[field]}")
            
            if missing_fields:
                print(f"❌ 缺少字段: {missing_fields}")
                return False
            
            # 检查数据一致性
            if len(result["equity_curve"]) != len(result["timestamps"]):
                print(f"❌ equity_curve和timestamps长度不一致: {len(result['equity_curve'])} vs {len(result['timestamps'])}")
                return False
            
            print("✅ 数据格式检查通过!")
            return True
            
        else:
            print(f"❌ API调用失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data}")
            except:
                print(f"响应内容: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_full_backtest():
    """测试完整回测API"""
    print("\n=== 测试完整回测API ===")
    
    url = "http://localhost:5001/api/backtest/run"
    data = {
        "symbol": "ETH/USDT",
        "initial_capital": 10000,
        "days": 7,  # 使用较短的时间以便快速测试
        "leverage": 1.0,
        "funding_rate": 0.0,
        "funding_interval": 8,
        "auto_calculate_range": True
    }
    
    try:
        print(f"发送请求到: {url}")
        print(f"请求数据: {json.dumps(data, indent=2)}")
        
        response = requests.post(url, json=data, timeout=30)
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API调用成功!")
            
            # 检查策略字段
            if "strategies" not in result:
                print("❌ 缺少strategies字段")
                return False
            
            strategies = result["strategies"]
            expected_strategies = ["long", "short", "neutral"]
            
            for strategy_name in expected_strategies:
                if strategy_name not in strategies:
                    print(f"❌ 缺少策略: {strategy_name}")
                    return False
                
                strategy_data = strategies[strategy_name]
                print(f"  {strategy_name} 策略:")
                
                # 检查关键字段
                required_fields = ["equity_curve", "timestamps", "total_return", "final_capital"]
                for field in required_fields:
                    if field not in strategy_data:
                        print(f"    ❌ 缺少字段: {field}")
                        return False
                    
                    if field == "equity_curve":
                        print(f"    equity_curve 长度: {len(strategy_data[field])}")
                    elif field == "timestamps":
                        print(f"    timestamps 长度: {len(strategy_data[field])}")
                    else:
                        print(f"    {field}: {strategy_data[field]}")
                
                # 检查数据一致性
                if len(strategy_data["equity_curve"]) != len(strategy_data["timestamps"]):
                    print(f"    ❌ equity_curve和timestamps长度不一致")
                    return False
            
            print("✅ 数据格式检查通过!")
            return True
            
        else:
            print(f"❌ API调用失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data}")
            except:
                print(f"响应内容: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_health():
    """测试健康检查API"""
    print("=== 测试健康检查API ===")
    
    try:
        response = requests.get("http://localhost:5001/api/health", timeout=5)
        
        if response.status_code == 200:
            print("✅ 后端服务正常运行")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到后端服务: {e}")
        print("请确保后端服务正在运行在 http://localhost:5001")
        return False

def main():
    """主测试函数"""
    print("🧪 开始测试后端API...")
    
    # 测试健康检查
    if not test_health():
        print("\n❌ 后端服务不可用，请先启动后端服务")
        sys.exit(1)
    
    # 测试策略回测
    strategy_test_passed = test_strategy_backtest()
    
    # 测试完整回测
    full_test_passed = test_full_backtest()
    
    # 总结
    print("\n" + "="*50)
    print("📊 测试结果总结:")
    print(f"  策略回测API: {'✅ 通过' if strategy_test_passed else '❌ 失败'}")
    print(f"  完整回测API: {'✅ 通过' if full_test_passed else '❌ 失败'}")
    
    if strategy_test_passed and full_test_passed:
        print("\n🎉 所有测试通过! 后端API工作正常")
        print("如果前端图表仍然不显示，问题可能在前端的Chart.js集成")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请检查后端实现")
        sys.exit(1)

if __name__ == "__main__":
    main()