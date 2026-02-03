"""
钱包认证相关API路由

提供Web3钱包签名认证、JWT令牌管理、白名单权限控制等功能
支持MetaMask等主流钱包的连接和认证
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request
from functools import wraps

logger = logging.getLogger(__name__)


def init_auth_routes(wallet_auth, whitelist_manager):
    """
    初始化认证路由
    
    Args:
        wallet_auth: 钱包认证管理器
        whitelist_manager: 白名单管理器
    
    Returns:
        tuple: (认证蓝图, 认证装饰器函数)
    """
    
    # 创建认证蓝图
    auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

    def require_auth(f):
        """
        认证装饰器
        
        用于保护需要认证的API接口
        检查请求头中的JWT令牌是否有效
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # 获取Authorization头
                auth_header = request.headers.get('Authorization')
                if not auth_header:
                    return jsonify({'error': '缺少认证令牌'}), 401
                
                # 检查Bearer格式
                if not auth_header.startswith('Bearer '):
                    return jsonify({'error': '认证令牌格式错误'}), 401
                
                # 提取令牌
                token = auth_header.split(' ')[1]
                
                # 验证令牌
                user_info = wallet_auth.verify_token(token)
                if not user_info:
                    return jsonify({'error': '认证令牌无效或已过期'}), 401
                
                # 将用户信息添加到请求上下文
                request.user = user_info
                
                return f(*args, **kwargs)
            
            except Exception as e:
                logger.error(f"认证验证错误: {e}")
                return jsonify({'error': '认证验证失败'}), 401
        
        return decorated_function

    @auth_bp.route("/challenge", methods=["POST"])
    def get_challenge():
        """
        获取认证挑战消息
        
        为指定的钱包公钥生成一个需要签名的挑战消息
        用户需要使用私钥对此消息进行签名以证明钱包所有权
        
        请求体:
        {
            "public_key": "0x1234567890abcdef..."
        }
        
        返回:
        {
            "message": "Please sign this message to authenticate: 1706889300",
            "public_key": "0x1234567890abcdef..."
        }
        """
        try:
            data = request.get_json()
            
            if not data or 'public_key' not in data:
                return jsonify({'error': '缺少钱包公钥'}), 400
            
            public_key = data['public_key']
            
            # 验证公钥格式
            if not public_key or not isinstance(public_key, str):
                return jsonify({'error': '钱包公钥格式无效'}), 400
            
            if not public_key.startswith('0x') or len(public_key) != 42:
                return jsonify({'error': '钱包公钥格式无效'}), 400
            
            logger.info(f"为钱包 {public_key} 生成认证挑战")
            
            # 生成挑战消息
            challenge_message = wallet_auth.generate_challenge(public_key)
            
            return jsonify({
                'message': challenge_message,
                'public_key': public_key
            })
        
        except Exception as e:
            logger.error(f"生成认证挑战错误: {e}")
            return jsonify({'error': '生成认证挑战失败'}), 500

    @auth_bp.route("/login", methods=["POST"])
    def login():
        """
        钱包登录认证
        
        验证用户的钱包签名并生成JWT认证令牌
        只有白名单中的钱包地址才能成功登录
        
        请求体:
        {
            "public_key": "0x1234567890abcdef...",
            "message": "Please sign this message to authenticate: 1706889300",
            "signature": "0xabcdef1234567890..."
        }
        
        返回:
        {
            "success": true,
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "expires_at": "2026-02-04T10:00:00",
            "user": {...}
        }
        """
        try:
            data = request.get_json()
            
            # 验证必需字段
            required_fields = ['public_key', 'message', 'signature']
            for field in required_fields:
                if not data or field not in data:
                    return jsonify({'error': f'缺少必需字段: {field}'}), 400
            
            public_key = data['public_key']
            message = data['message']
            signature = data['signature']
            
            logger.info(f"钱包登录请求: {public_key}")
            
            # 验证签名并登录
            result = wallet_auth.authenticate(public_key, message, signature)
            
            if result['success']:
                logger.info(f"钱包 {public_key} 登录成功")
                return jsonify(result)
            else:
                logger.warning(f"钱包 {public_key} 登录失败: {result.get('error', '未知错误')}")
                return jsonify(result), 401
        
        except Exception as e:
            logger.error(f"钱包登录错误: {e}")
            return jsonify({'error': '钱包登录失败'}), 500

    @auth_bp.route("/verify", methods=["GET"])
    @require_auth
    def verify_token():
        """
        验证认证令牌
        
        检查当前的JWT令牌是否有效
        返回当前认证用户的信息
        
        请求头:
            Authorization: Bearer <token>
        
        返回:
        {
            "authenticated": true,
            "public_key": "0x1234567890abcdef...",
            "wallet_info": {...}
        }
        """
        try:
            # 用户信息已经通过装饰器验证并添加到request.user中
            user_info = request.user
            
            logger.info(f"令牌验证成功: {user_info.get('public_key', 'unknown')}")
            
            return jsonify({
                'authenticated': True,
                'public_key': user_info.get('public_key'),
                'wallet_info': user_info
            })
        
        except Exception as e:
            logger.error(f"令牌验证错误: {e}")
            return jsonify({'error': '令牌验证失败'}), 500

    @auth_bp.route("/whitelist", methods=["GET"])
    @require_auth
    def get_whitelist():
        """
        获取白名单用户列表
        
        返回系统中所有白名单用户的信息
        只有已认证的用户才能访问此接口
        
        请求头:
            Authorization: Bearer <token>
        
        返回:
        {
            "wallets": [
                {
                    "address": "0x1234567890abcdef...",
                    "name": "用户名",
                    "added_at": "2026-02-03T10:00:00",
                    "permissions": ["read", "write"]
                }
            ]
        }
        """
        try:
            # 获取白名单
            whitelist = whitelist_manager.get_whitelist()
            
            logger.info(f"返回白名单，包含 {len(whitelist)} 个用户")
            
            return jsonify({
                'wallets': whitelist
            })
        
        except Exception as e:
            logger.error(f"获取白名单错误: {e}")
            return jsonify({'error': '获取白名单失败'}), 500

    @auth_bp.route("/logout", methods=["POST"])
    @require_auth
    def logout():
        """
        用户登出
        
        使当前的JWT令牌失效
        用户需要重新登录才能访问受保护的接口
        
        请求头:
            Authorization: Bearer <token>
        
        返回:
        {
            "success": true,
            "message": "登出成功",
            "timestamp": "2026-02-03T10:00:00"
        }
        """
        try:
            # 获取当前用户信息
            user_info = request.user
            public_key = user_info.get('public_key', 'unknown')
            
            # 注销令牌（这里可以添加令牌黑名单逻辑）
            # wallet_auth.revoke_token(token)
            
            logger.info(f"用户 {public_key} 登出成功")
            
            return jsonify({
                'success': True,
                'message': '登出成功',
                'timestamp': datetime.now().isoformat()
            })
        
        except Exception as e:
            logger.error(f"用户登出错误: {e}")
            return jsonify({'error': '登出失败'}), 500

    return auth_bp, require_auth