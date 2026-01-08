"""
配置管理模块

管理 SSH 连接配置和应用设置。
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """服务器配置"""

    host: str
    username: str
    port: int = 22
    password: Optional[str] = None
    key_filename: Optional[str] = None
    timeout: int = 30


@dataclass
class AppConfig:
    """应用配置"""

    log_level: str = "INFO"
    default_timeout: int = 30
    max_sessions: int = 100
    session_cleanup_hours: int = 24
    keepalive_interval: int = 60
    connections: Dict[str, ServerConfig] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "AppConfig":
        """从环境变量创建配置"""
        return cls(
            log_level=os.getenv("MCP_SSH_LOG_LEVEL", "INFO"),
            default_timeout=int(os.getenv("MCP_SSH_TIMEOUT", "30")),
            max_sessions=int(os.getenv("MCP_SSH_MAX_SESSIONS", "100")),
            session_cleanup_hours=int(os.getenv("MCP_SSH_CLEANUP_HOURS", "24")),
            keepalive_interval=int(os.getenv("MCP_SSH_KEEPALIVE", "60")),
        )

    @classmethod
    def from_file(cls, config_path: str) -> Optional["AppConfig"]:
        """从配置文件创建配置"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            config = cls.from_env()

            # 更新连接配置
            if "connections" in data:
                for name, conn_data in data["connections"].items():
                    config.connections[name] = ServerConfig(**conn_data)

            # 更新其他配置
            for key in [
                "log_level",
                "default_timeout",
                "max_sessions",
                "session_cleanup_hours",
                "keepalive_interval",
            ]:
                if key in data:
                    setattr(config, key, data[key])

            return config

        except Exception as e:
            logger.error(f"读取配置文件失败: {e}")
            return None

    def to_file(self, config_path: str) -> bool:
        """保存配置到文件"""
        try:
            data = {
                "log_level": self.log_level,
                "default_timeout": self.default_timeout,
                "max_sessions": self.max_sessions,
                "session_cleanup_hours": self.session_cleanup_hours,
                "keepalive_interval": self.keepalive_interval,
                "connections": {
                    name: {
                        "host": conn.host,
                        "username": conn.username,
                        "port": conn.port,
                        "timeout": conn.timeout,
                        "password": conn.password,
                        "key_filename": conn.key_filename,
                    }
                    for name, conn in self.connections.items()
                },
            }

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv(
            "MCP_SSH_CONFIG", os.path.expanduser("~/.mcp_ssh_config.json")
        )
        self.config: AppConfig = self._load_config()

    def _load_config(self) -> AppConfig:
        """加载配置"""
        # 首先从环境变量加载
        config = AppConfig.from_env()

        # 如果配置文件存在，则从文件加载并合并
        if os.path.exists(self.config_path):
            file_config = AppConfig.from_file(self.config_path)
            if file_config:
                config = file_config

        logger.info(f"配置加载完成，日志级别: {config.log_level}")
        return config

    def reload(self) -> bool:
        """重新加载配置"""
        try:
            self.config = self._load_config()
            return True
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            return False

    def save(self) -> bool:
        """保存配置到文件"""
        return self.config.to_file(self.config_path)

    def get_connection(self, name: str) -> Optional[ServerConfig]:
        """获取连接配置"""
        return self.config.connections.get(name)

    def add_connection(self, name: str, config: ServerConfig) -> bool:
        """添加连接配置"""
        try:
            self.config.connections[name] = config
            return True
        except Exception as e:
            logger.error(f"添加连接配置失败: {e}")
            return False

    def remove_connection(self, name: str) -> bool:
        """移除连接配置"""
        try:
            if name in self.config.connections:
                del self.config.connections[name]
                return True
            return False
        except Exception as e:
            logger.error(f"移除连接配置失败: {e}")
            return False

    def list_connections(self) -> Dict[str, ServerConfig]:
        """列出所有连接配置"""
        return self.config.connections.copy()


# 全局配置管理器实例
config_manager = ConfigManager()
