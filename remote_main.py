"""远程 MCP SSH 服务器入口点"""

import logging
import sys
import os
from mcp_ssh_server.remote_server import RemoteMCPSshServer


def setup_logging():
    """设置日志配置"""
    log_level = os.getenv("MCP_SSH_LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 获取配置文件路径
    config_path = os.getenv("MCP_SSH_CONFIG_FILE")
    if not config_path:
        # 尝试使用默认配置文件
        default_config = os.path.join(
            os.path.dirname(__file__), 
            "config", 
            "remote_config.json"
        )
        if os.path.exists(default_config):
            config_path = default_config
    
    logger.info("启动远程 MCP SSH 服务器")
    if config_path:
        logger.info(f"使用配置文件: {config_path}")
    
    try:
        server = RemoteMCPSshServer(config_path=config_path)
        logger.info(f"服务器监听在 {server.host}:{server.port}")
        try:
            server.run()
        except KeyboardInterrupt:
            logger.info("服务器被用户中断")
        finally:
            server.shutdown()
    except Exception as e:
        logger.error(f"服务器运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
