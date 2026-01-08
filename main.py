"""
MCP SSH 服务器入口点

启动 MCP SSH 服务器，提供 SSH 远程连接和多轮交互功能。
"""

import asyncio
import logging
import os
import sys
from mcp_ssh_server.server import main as server_main


def setup_logging():
    """设置日志配置"""
    log_level = os.getenv("MCP_SSH_LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )


def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("启动 MCP SSH 服务器...")
    
    try:
        asyncio.run(server_main())
    except KeyboardInterrupt:
        logger.info("服务器被用户中断")
    except Exception as e:
        logger.error(f"服务器运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
