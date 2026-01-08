"""
安全模块

提供认证、授权和安全检查功能。
"""

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Dict, Optional, List, Set
from dataclasses import dataclass, field
import jwt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import secrets

logger = logging.getLogger(__name__)


@dataclass
class AuthConfig:
    """认证配置"""
    enable_auth: bool = True
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600  # 1小时
    api_keys: Dict[str, str] = field(default_factory=dict)  # client_id: api_key
    allowed_ips: List[str] = field(default_factory=list)  # 允许的 IP 地址
    rate_limit: int = 100  # 每分钟请求限制
    enable_cors: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, limit: int = 100):
        self.limit = limit
        self.requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, client_id: str) -> bool:
        """检查是否允许请求"""
        now = time.time()
        
        # 清理过期记录
        if client_id in self.requests:
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if now - req_time < 60  # 1分钟内
            ]
        else:
            self.requests[client_id] = []
        
        # 检查限制
        if len(self.requests[client_id]) >= self.limit:
            return False
        
        # 记录请求
        self.requests[client_id].append(now)
        return True


class AuthManager:
    """认证管理器"""
    
    def __init__(self, config: AuthConfig):
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit)
        self.active_tokens: Set[str] = set()
        
    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple:
        """哈希密码"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
            backend=default_backend()
        )
        
        hashed = kdf.derive(password.encode())
        return salt, hashed.hex()
    
    def verify_password(self, password: str, salt: str, hashed: str) -> bool:
        """验证密码"""
        _, check_hash = self.hash_password(password, salt)
        return hmac.compare_digest(check_hash, hashed)
    
    def generate_token(self, client_id: str, api_key: str) -> Optional[str]:
        """生成 JWT 令牌"""
        if not self.config.enable_auth:
            return "no-auth"
        
        # 验证 API 密钥
        if client_id not in self.config.api_keys:
            logger.warning(f"未知的客户端 ID: {client_id}")
            return None
        
        if not hmac.compare_digest(self.config.api_keys[client_id], api_key):
            logger.warning(f"无效的 API 密钥: {client_id}")
            return None
        
        # 生成令牌
        payload = {
            "client_id": client_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.config.jwt_expiration
        }
        
        try:
            token = jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)
            self.active_tokens.add(token)
            return token
        except Exception as e:
            logger.error(f"生成令牌失败: {e}")
            return None
    
    def verify_token(self, token: str) -> Optional[str]:
        """验证 JWT 令牌"""
        if not self.config.enable_auth:
            return "anonymous"
        
        if token not in self.active_tokens:
            logger.warning("未知的令牌")
            return None
        
        try:
            payload = jwt.decode(
                token, 
                self.config.jwt_secret, 
                algorithms=[self.config.jwt_algorithm]
            )
            return payload["client_id"]
        except jwt.ExpiredSignatureError:
            logger.warning("令牌已过期")
            self.active_tokens.discard(token)
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效令牌: {e}")
            self.active_tokens.discard(token)
            return None
    
    def revoke_token(self, token: str):
        """撤销令牌"""
        self.active_tokens.discard(token)
    
    def check_rate_limit(self, client_id: str) -> bool:
        """检查速率限制"""
        return self.rate_limiter.is_allowed(client_id)
    
    def is_ip_allowed(self, ip: str) -> bool:
        """检查 IP 是否允许"""
        if not self.config.allowed_ips:
            return True
        return ip in self.config.allowed_ips


class SecurityMiddleware:
    """安全中间件"""
    
    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager
    
    async def authenticate_request(self, request) -> Optional[str]:
        """认证请求"""
        # 检查 IP 白名单
        client_ip = request.remote
        if not self.auth_manager.is_ip_allowed(client_ip):
            logger.warning(f"IP 不被允许: {client_ip}")
            return None
        
        # 检查速率限制
        if not self.auth_manager.check_rate_limit(client_ip):
            logger.warning(f"速率限制: {client_ip}")
            return None
        
        # 获取认证信息
        auth_header = request.headers.get("Authorization", "")
        api_key = request.headers.get("X-API-Key", "")
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return self.auth_manager.verify_token(token)
        elif api_key:
            # 尝试使用 API 密钥直接认证
            client_id = request.headers.get("X-Client-ID", "")
            if client_id:
                token = self.auth_manager.generate_token(client_id, api_key)
                if token:
                    return client_id
        elif not self.auth_manager.config.enable_auth:
            return "anonymous"
        
        return None
    
    def add_cors_headers(self, response, origin: str = "*"):
        """添加 CORS 头"""
        if self.auth_manager.config.enable_cors:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key, X-Client-ID"
            response.headers["Access-Control-Max-Age"] = "86400"


def create_default_config() -> AuthConfig:
    """创建默认配置"""
    jwt_secret = os.getenv("MCP_SSH_JWT_SECRET", "")
    if not jwt_secret:
        jwt_secret = secrets.token_urlsafe(32)
        logger.warning("使用随机生成的 JWT 密钥，请设置 MCP_SSH_JWT_SECRET 环境变量")
    
    # 从环境变量加载 API 密钥
    api_keys_str = os.getenv("MCP_SSH_API_KEYS", "")
    api_keys = {}
    if api_keys_str:
        try:
            for pair in api_keys_str.split(","):
                client_id, key = pair.split(":")
                api_keys[client_id.strip()] = key.strip()
        except ValueError:
            logger.error("无效的 API 密钥格式，应为: client1:key1,client2:key2")
    
    # 从环境变量加载允许的 IP
    allowed_ips_str = os.getenv("MCP_SSH_ALLOWED_IPS", "")
    allowed_ips = []
    if allowed_ips_str:
        allowed_ips = [ip.strip() for ip in allowed_ips_str.split(",")]
    
    return AuthConfig(
        enable_auth=os.getenv("MCP_SSH_ENABLE_AUTH", "true").lower() == "true",
        jwt_secret=jwt_secret,
        jwt_algorithm=os.getenv("MCP_SSH_JWT_ALGORITHM", "HS256"),
        jwt_expiration=int(os.getenv("MCP_SSH_JWT_EXPIRATION", "3600")),
        api_keys=api_keys,
        allowed_ips=allowed_ips,
        rate_limit=int(os.getenv("MCP_SSH_RATE_LIMIT", "100")),
        enable_cors=os.getenv("MCP_SSH_ENABLE_CORS", "true").lower() == "true",
        cors_origins=os.getenv("MCP_SSH_CORS_ORIGINS", "*").split(",")
    )