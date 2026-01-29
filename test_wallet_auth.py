#!/usr/bin/env python3
"""Test script for wallet authentication module."""

import sys
import json
import requests
from datetime import datetime


def test_wallet_auth():
    """Test wallet authentication endpoints."""
    base_url = "http://localhost:5001"
    
    print("🧪 测试钱包认证模块")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. 测试健康检查...")
    try:
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            print("✅ 健康检查通过")
        else:
            print("❌ 健康检查失败")
            return False
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        return False
    
    # Test 2: Get challenge
    print("\n2. 测试获取认证挑战...")
    test_public_key = "11111111111111111111111111111112"
    
    try:
        response = requests.post(f"{base_url}/api/auth/challenge", json={
            "public_key": test_public_key
        })
        
        if response.status_code == 200:
            challenge_data = response.json()
            print("✅ 成功获取认证挑战")
            print(f"   消息: {challenge_data['message'][:50]}...")
        else:
            print(f"❌ 获取挑战失败: {response.status_code}")
            print(f"   错误: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 获取挑战异常: {e}")
        return False
    
    # Test 3: Test login with invalid signature (should fail)
    print("\n3. 测试无效签名登录（应该失败）...")
    try:
        response = requests.post(f"{base_url}/api/auth/login", json={
            "public_key": test_public_key,
            "message": challenge_data['message'],
            "signature": "invalid_signature"
        })
        
        if response.status_code == 401:
            print("✅ 正确拒绝了无效签名")
        else:
            print(f"❌ 应该拒绝无效签名，但返回了: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试无效签名异常: {e}")
    
    # Test 4: Test whitelist check
    print("\n4. 测试白名单检查...")
    non_whitelisted_key = "22222222222222222222222222222222"
    
    try:
        response = requests.post(f"{base_url}/api/auth/challenge", json={
            "public_key": non_whitelisted_key
        })
        
        if response.status_code == 200:
            challenge_data_2 = response.json()
            
            # Try to login with non-whitelisted wallet
            response = requests.post(f"{base_url}/api/auth/login", json={
                "public_key": non_whitelisted_key,
                "message": challenge_data_2['message'],
                "signature": "fake_signature"
            })
            
            if response.status_code == 403:
                print("✅ 正确拒绝了非白名单钱包")
            else:
                print(f"❌ 应该拒绝非白名单钱包，但返回了: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试白名单异常: {e}")
    
    # Test 5: Test auth verification without token
    print("\n5. 测试无令牌的认证验证...")
    try:
        response = requests.get(f"{base_url}/api/auth/verify")
        
        if response.status_code == 401:
            print("✅ 正确要求认证令牌")
        else:
            print(f"❌ 应该要求认证令牌，但返回了: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试认证验证异常: {e}")
    
    # Test 6: Test protected endpoint without auth
    print("\n6. 测试受保护端点（无认证）...")
    try:
        response = requests.post(f"{base_url}/api/strategy/backtest", json={
            "symbol": "BTC/USDT",
            "mode": "long",
            "lower_price": 40000,
            "upper_price": 50000,
            "grid_count": 10,
            "initial_capital": 10000,
            "days": 7
        })
        
        if response.status_code == 401:
            print("✅ 正确保护了回测端点")
        else:
            print(f"❌ 应该保护回测端点，但返回了: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试受保护端点异常: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 钱包认证模块测试完成")
    print("\n📝 注意事项:")
    print("- 实际使用时需要真实的钱包签名")
    print("- 请确保白名单中包含有效的钱包地址")
    print("- 生产环境请使用 HTTPS")
    
    return True


def test_whitelist_management():
    """Test whitelist management functions."""
    print("\n🧪 测试白名单管理")
    print("=" * 50)
    
    try:
        from wallet_auth import WhitelistManager
        
        # Create test whitelist manager
        whitelist = WhitelistManager("test_whitelist.json")
        
        # Test adding wallet
        test_wallet = "TestWallet123456789"
        whitelist.add_wallet(test_wallet, "Test User", "user")
        print("✅ 成功添加测试钱包")
        
        # Test checking whitelist
        if whitelist.is_whitelisted(test_wallet):
            print("✅ 钱包白名单检查通过")
        else:
            print("❌ 钱包白名单检查失败")
        
        # Test getting wallet info
        info = whitelist.get_wallet_info(test_wallet)
        if info and info['nickname'] == "Test User":
            print("✅ 钱包信息获取正确")
        else:
            print("❌ 钱包信息获取失败")
        
        # Test deactivating wallet
        whitelist.deactivate_wallet(test_wallet)
        if not whitelist.is_whitelisted(test_wallet):
            print("✅ 钱包停用功能正常")
        else:
            print("❌ 钱包停用功能失败")
        
        # Test reactivating wallet
        whitelist.activate_wallet(test_wallet)
        if whitelist.is_whitelisted(test_wallet):
            print("✅ 钱包激活功能正常")
        else:
            print("❌ 钱包激活功能失败")
        
        # Clean up
        whitelist.remove_wallet(test_wallet)
        print("✅ 测试钱包已清理")
        
        # Remove test file
        import os
        if os.path.exists("test_whitelist.json"):
            os.remove("test_whitelist.json")
        
        print("✅ 白名单管理测试完成")
        
    except Exception as e:
        print(f"❌ 白名单管理测试失败: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("🚀 开始钱包认证模块测试")
    
    # Test whitelist management
    if not test_whitelist_management():
        sys.exit(1)
    
    # Test API endpoints
    if not test_wallet_auth():
        sys.exit(1)
    
    print("\n🎉 所有测试完成！")