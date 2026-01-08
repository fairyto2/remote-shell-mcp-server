"""
测试基本功能，不依赖外部模块
"""

import pytest
import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_project_structure():
    """测试项目结构"""
    # 检查关键文件是否存在
    assert os.path.exists(os.path.join(project_root, "mcp_ssh_server", "__init__.py"))
    assert os.path.exists(os.path.join(project_root, "mcp_ssh_server", "server.py"))
    assert os.path.exists(os.path.join(project_root, "mcp_ssh_server", "ssh_manager.py"))
    assert os.path.exists(os.path.join(project_root, "mcp_ssh_server", "session_manager.py"))
    assert os.path.exists(os.path.join(project_root, "mcp_ssh_server", "config.py"))
    assert os.path.exists(os.path.join(project_root, "main.py"))
    assert os.path.exists(os.path.join(project_root, "pyproject.toml"))


def test_config_loading():
    """测试配置加载"""
    try:
        from mcp_ssh_server.config import AppConfig
        
        # 测试从环境变量创建配置
        config = AppConfig.from_env()
        assert config.log_level is not None
        assert config.default_timeout > 0
        assert config.max_sessions > 0
        assert config.session_cleanup_hours > 0
        assert config.keepalive_interval > 0
    except ImportError as e:
        pytest.skip(f"Cannot import config: {e}")


def test_ssh_config_dataclass():
    """测试 SSH 配置数据类"""
    try:
        from mcp_ssh_server.ssh_manager import SSHConfig
        
        # 测试创建 SSH 配置
        config = SSHConfig(
            host="example.com",
            username="testuser",
            port=22,
            password="testpass",
            timeout=30
        )
        
        assert config.host == "example.com"
        assert config.username == "testuser"
        assert config.port == 22
        assert config.password == "testpass"
        assert config.timeout == 30
    except ImportError as e:
        pytest.skip(f"Cannot import SSHConfig: {e}")


def test_session_message_dataclass():
    """测试会话消息数据类"""
    try:
        from mcp_ssh_server.session_manager import SessionMessage
        
        # 测试创建会话消息
        message = SessionMessage(
            id="msg-123",
            timestamp=1234567890.0,
            role="user",
            content="test message",
            command="ls -la",
            result={"success": True}
        )
        
        assert message.id == "msg-123"
        assert message.timestamp == 1234567890.0
        assert message.role == "user"
        assert message.content == "test message"
        assert message.command == "ls -la"
        assert message.result["success"] is True
    except ImportError as e:
        pytest.skip(f"Cannot import SessionMessage: {e}")


def test_session_dataclass():
    """测试会话数据类"""
    try:
        from mcp_ssh_server.session_manager import Session
        
        # 测试创建会话
        session = Session(
            id="session-123",
            name="test-session",
            connection_name="test-conn",
            created_at=1234567890.0,
            last_activity=1234567890.0
        )
        
        assert session.id == "session-123"
        assert session.name == "test-session"
        assert session.connection_name == "test-conn"
        assert session.created_at == 1234567890.0
        assert session.last_activity == 1234567890.0
        assert session.working_directory == "/home"
        assert isinstance(session.environment, dict)
        assert isinstance(session.messages, list)
        
        # 测试添加消息
        message_id = session.add_message(
            role="user",
            content="test command",
            command="ls -la"
        )
        assert message_id is not None
        assert len(session.messages) == 1
        
        # 测试获取最近消息
        recent_messages = session.get_recent_messages(10)
        assert len(recent_messages) == 1
        assert recent_messages[0].role == "user"
        assert recent_messages[0].content == "test command"
        
        # 测试转换为字典
        session_dict = session.to_dict()
        assert session_dict["id"] == "session-123"
        assert session_dict["name"] == "test-session"
        assert session_dict["connection_name"] == "test-conn"
        assert session_dict["message_count"] == 1
        
    except ImportError as e:
        pytest.skip(f"Cannot import Session: {e}")


if __name__ == "__main__":
    pytest.main([__file__])