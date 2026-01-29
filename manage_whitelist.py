#!/usr/bin/env python3
"""Wallet whitelist management tool."""

import argparse
import sys
from wallet_auth import WhitelistManager


def main():
    """Main function for whitelist management."""
    parser = argparse.ArgumentParser(description='管理钱包白名单')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 列出所有钱包
    list_parser = subparsers.add_parser('list', help='列出所有钱包')
    
    # 添加钱包
    add_parser = subparsers.add_parser('add', help='添加钱包到白名单')
    add_parser.add_argument('public_key', help='钱包公钥')
    add_parser.add_argument('--nickname', help='钱包昵称')
    add_parser.add_argument('--role', default='user', help='用户角色 (admin/user)')
    
    # 移除钱包
    remove_parser = subparsers.add_parser('remove', help='从白名单移除钱包')
    remove_parser.add_argument('public_key', help='钱包公钥')
    
    # 激活钱包
    activate_parser = subparsers.add_parser('activate', help='激活钱包')
    activate_parser.add_argument('public_key', help='钱包公钥')
    
    # 停用钱包
    deactivate_parser = subparsers.add_parser('deactivate', help='停用钱包')
    deactivate_parser.add_argument('public_key', help='钱包公钥')
    
    # 查看钱包信息
    info_parser = subparsers.add_parser('info', help='查看钱包信息')
    info_parser.add_argument('public_key', help='钱包公钥')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        whitelist_manager = WhitelistManager()
        
        if args.command == 'list':
            wallets = whitelist_manager.list_wallets()
            if not wallets:
                print("白名单为空")
                return
            
            print(f"{'公钥':<45} {'昵称':<20} {'角色':<10} {'状态':<6}")
            print("-" * 85)
            for public_key, info in wallets.items():
                status = "激活" if info.get('active', True) else "停用"
                print(f"{public_key:<45} {info.get('nickname', 'N/A'):<20} {info.get('role', 'user'):<10} {status:<6}")
        
        elif args.command == 'add':
            whitelist_manager.add_wallet(
                args.public_key,
                args.nickname,
                args.role
            )
            print(f"✅ 钱包 {args.public_key} 已添加到白名单")
        
        elif args.command == 'remove':
            if args.public_key not in whitelist_manager.list_wallets():
                print(f"❌ 钱包 {args.public_key} 不在白名单中")
                return
            
            whitelist_manager.remove_wallet(args.public_key)
            print(f"✅ 钱包 {args.public_key} 已从白名单移除")
        
        elif args.command == 'activate':
            if args.public_key not in whitelist_manager.list_wallets():
                print(f"❌ 钱包 {args.public_key} 不在白名单中")
                return
            
            whitelist_manager.activate_wallet(args.public_key)
            print(f"✅ 钱包 {args.public_key} 已激活")
        
        elif args.command == 'deactivate':
            if args.public_key not in whitelist_manager.list_wallets():
                print(f"❌ 钱包 {args.public_key} 不在白名单中")
                return
            
            whitelist_manager.deactivate_wallet(args.public_key)
            print(f"✅ 钱包 {args.public_key} 已停用")
        
        elif args.command == 'info':
            info = whitelist_manager.get_wallet_info(args.public_key)
            if not info:
                print(f"❌ 钱包 {args.public_key} 不在白名单中")
                return
            
            print(f"钱包信息:")
            print(f"  公钥: {args.public_key}")
            print(f"  昵称: {info.get('nickname', 'N/A')}")
            print(f"  角色: {info.get('role', 'user')}")
            print(f"  状态: {'激活' if info.get('active', True) else '停用'}")
            print(f"  添加时间: {info.get('added_at', 'N/A')}")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()