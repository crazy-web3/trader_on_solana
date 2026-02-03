"""
钱包认证相关API路由

提供钱包签名认证、登录登出、白名单管理等功能
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request
from functools import wraps
from wallet_auth.exceptions import (
    InvalidSignatureError,
    TokenExpiredError,
    InvalidTokenError
)

# 创建蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
logger = logging.getLogger(__name__)


def init_auth_routes(wallet_auth, whitelist_manager):
    """
    初始化认证路由
    
    Args:
        wallet_auth: 钱包认证管理器
        whitelist_manager: 白名单管理器
    """
    
    def require_auth(f):
        """
        钱包认证装饰器
        
        用于保护需要钱包认证的API端点
        验证请求头中的JWT token，确保用户已通过钱包签名认证
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取Authorization请求头
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({"error": "缺少认证头"}), 401
            
            try:
                # 从"Bearer <token>"格式中提取token
                token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
                
                # 验证token并获取公钥
                public_key = wallet_auth.verify_token(token)
                
                # 将公钥添加到请求上下文中，供被装饰的函数使用
                request.wallet_public_key = public_key
                return f(*args, **kwargs)
                
            except (TokenExpiredError, InvalidTokenError) as e:
                return jsonify({"error": str(e)}), 401
            except Exception as e:
                logger.error(f"认证错误: {e}")
                return jsonify({"error": "认证失败"}), 401
        
        return decorated_function

    @auth_bp.route("/challenge", methods=["POST"])
    def get_auth_challenge():
        """
        获取钱包签名挑战消息
        
        为钱包认证生成一个随机挑战消息，用户需要用私钥签名此消息
        这是钱包认证流程的第一步
        
        请求体:
        {
            "public_key": "钱包公钥字符串"
        }
        
        返回:
        {
            "message": "需要签名的挑战消息",
            "public_key": "钱包公钥"
        }
        """
        try:
            data = request.get_json()
            public_key = data.get("public_key")
            
            # 验证请求参数
            if not public_key:
                return jsonify({"error": "缺少public_key参数"}), 400
            
            # 生成挑战消息
            message = wallet_auth.generate_challenge_message(public_key)
            
            return jsonify({
                "message": message,
                "public_key": public_key
            })
        
        except Exception as e:
            logger.error(f"生成挑战消息错误: {e}")
            return jsonify({"error": "生成挑战消息失败"}), 500

    @auth_bp.route("/login", methods=["POST"])
    def wallet_login():
        """
        钱包登录认证
        
        验证用户的钱包签名，完成认证流程
        用户需要提供公钥、挑战消息和对应的签名
        
        请求体:
        {
            "public_key": "钱包公钥",
            "message": "之前获取的挑战消息",
            "signature": "用私钥签名的消息"
        }
        
        返回:
        {
            "success": true,
            "token": "JWT认证令牌",
            "expires_at": "令牌过期时间",
            "user": {用户信息对象}
        }
        """
        try:
            data = request.get_json()
            public_key = data.get("public_key")
            message = data.get("message")
            signature = data.get("signature")
            
            # 验证必需参数
            if not all([public_key, message, signature]):
                return jsonify({"error": "缺少必需的参数"}), 400
            
            # 验证钱包签名
            wallet_user = wallet_auth.authenticate_wallet(public_key, message, signature)
            
            # 生成认证令牌
            auth_token = wallet_auth.generate_auth_token(public_key)
            
            return jsonify({
                "success": True,
                "token": auth_token.token,
                "expires_at": auth_token.expires_at.isoformat(),
                "user": wallet_user.to_dict()
            })
        
        except InvalidSignatureError as e:
            logger.warning(f"签名验证失败: {e}")
            return jsonify({"error": "钱包签名无效"}), 401
        except Exception as e:
            logger.error(f"登录错误: {e}")
            return jsonify({"error": "认证失败"}), 500

    @auth_bp.route("/logout", methods=["POST"])
    @require_auth
    def wallet_logout():
        """
        钱包登出
        
        撤销当前的认证令牌，用户需要重新登录才能访问受保护的接口
        需要在请求头中提供有效的认证令牌
        
        请求头:
            Authorization: Bearer <token>
        
        返回:
        {
            "success": true,
            "message": "登出成功"
        }
        """
        try:
            # 从请求头获取token
            auth_header = request.headers.get('Authorization')
            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
            
            # 撤销令牌
            wallet_auth.revoke_token(token)
            
            return jsonify({"success": True, "message": "登出成功"})
        
        except Exception as e:
            logger.error(f"登出错误: {e}")
            return jsonify({"error": "登出失败"}), 500

    @auth_bp.route("/verify", methods=["GET"])
    @require_auth
    def verify_auth():
        """
        验证当前认证状态
        
        检查用户的认证令牌是否有效，并返回用户信息
        需要在请求头中提供有效的认证令牌
        
        请求头:
            Authorization: Bearer <token>
        
        返回:
        {
            "authenticated": true,
            "public_key": "用户钱包公钥",
            "wallet_info": {用户钱包信息}
        }
        """
        try:
            public_key = request.wallet_public_key
            wallet_info = whitelist_manager.get_wallet_info(public_key)
            
            return jsonify({
                "authenticated": True,
                "public_key": public_key,
                "wallet_info": wallet_info
            })
        
        except Exception as e:
            logger.error(f"认证验证错误: {e}")
            return jsonify({"error": "验证失败"}), 500

    @auth_bp.route("/whitelist", methods=["GET"])
    @require_auth
    def get_whitelist():
        """
        获取白名单信息（仅管理员）
        
        返回系统中所有白名单用户的信息
        只有管理员角色的用户才能访问此接口
        
        请求头:
            Authorization: Bearer <token>
        
        返回:
        {
            "wallets": [
                {
                    "address": "钱包地址",
                    "nickname": "用户昵称",
                    "role": "用户角色",
                    "created_at": "创建时间"
                }
            ]
        }
        """
        try:
            public_key = request.wallet_public_key
            wallet_info = whitelist_manager.get_wallet_info(public_key)
            
            # 检查用户是否为管理员
            if not wallet_info or wallet_info.get('role') != 'admin':
                return jsonify({"error": "需要管理员权限"}), 403
            
            wallets = whitelist_manager.list_wallets()
            return jsonify({"wallets": wallets})
        
        except Exception as e:
            logger.error(f"白名单错误: {e}")
            return jsonify({"error": "获取白名单失败"}), 500

    return auth_bp, require_auth