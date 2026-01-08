"""
远程 MCP SSH 服务器入口点

启动基于 HTTP/WebSocket 的远程 MCP SSH 服务器。
"""

import asyncio
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


async def main():
    """主函数"""
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
    
    logger.info(f"启动远程 MCP SSH 服务器")
    if config_path:
        logger.info(f"使用配置文件: {config_path}")
    
    try:
        server = RemoteMCPSshServer(config_path=config_path)
        logger.info(f"服务器监听在 {server.host}:{server.port}")
        
        # 启动服务器
        runner = await server.start()
        
        # 保持运行
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("服务器被用户中断")
        finally:
            await server.stop()
            await runner.cleanup()
            
    except Exception as e:
        logger.error(f"服务器运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())