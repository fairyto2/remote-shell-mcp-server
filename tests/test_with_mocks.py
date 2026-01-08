"""
使用模拟依赖的测试
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Mock external dependencies before importing our modules
@pytest.fixture(autouse=True)
def mock_external_dependencies():
    """模拟所有外部依赖"""
    mocks = {}
    
    # Mock paramiko
    paramiko_mock = Mock()
    paramiko_mock.SSHClient = Mock
    paramiko_mock.AutoAddPolicy = Mock
    paramiko_mock.SFTPClient = Mock
    mocks['paramiko'] = paramiko_mock
    
    # Mock mcp
    mcp_mock = Mock()
    mcp_server_mock = Mock()
    mcp_server_mock.Server = Mock
    mcp_server_mock.stdio_server = Mock
    mcp_types_mock = Mock()
    mcp_types_mock.CallToolRequest = Mock
    mcp_types_mock.CallToolResult = Mock
    mcp_types_mock.ListToolsRequest = Mock
    mcp_types_mock.Tool = Mock
    mcp_types_mock.TextContent = Mock
    mcp_types_mock.InitializationOptions = Mock
    
    mcp_mock.server = mcp_server_mock
    mcp_mock.types = mcp_types_mock
    mocks['mcp'] = mcp_mock
    
    # Mock pydantic
    pydantic_mock = Mock()
    pydantic_mock.BaseModel = Mock
    mocks['pydantic'] = pydantic_mock
    
    with patch.dict('sys.modules', mocks):
        yield


def test_ssh_config_creation():
    """测试 SSH 配置创建"""
    from mcp_ssh_server.ssh_manager import SSHConfig
    
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


def test_ssh_connection_creation():
    """测试 SSH 连接创建"""
    from mcp_ssh_server.ssh_manager import SSHConnection, SSHConfig
    
    config = SSHConfig(
        host="example.com",
        username="testuser",
        password="testpass"
    )
    
    connection = SSHConnection(config)
    
    assert connection.config == config
    assert connection.client is None
    assert connection.sftp is None
    assert connection.is_connected is False


def test_ssh_connection_manager_creation():
    """测试 SSH 连接管理器创建"""
    from mcp_ssh_server.ssh_manager import SSHConnectionManager
    
    manager = SSHConnectionManager()
    
    assert manager.connections == {}
    assert manager._lock is not None
    assert manager._keepalive_thread is None
    assert manager._keepalive_running is False


def test_session_message_creation():
    """测试会话消息创建"""
    from mcp_ssh_server.session_manager import SessionMessage
    
    message = SessionMessage(
        id="msg-123",
        timestamp=1234567890.0,
        role="user",
        content="test message",
        command="ls -la"
    )
    
    assert message.id == "msg-123"
    assert message.timestamp == 1234567890.0
    assert message.role == "user"
    assert message.content == "test message"
    assert message.command == "ls -la"


def test_session_creation():
    """测试会话创建"""
    from mcp_ssh_server.session_manager import Session
    
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


def test_session_add_message():
    """测试会话添加消息"""
    from mcp_ssh_server.session_manager import Session
    
    session = Session(
        id="session-123",
        name="test-session",
        connection_name="test-conn",
        created_at=1234567890.0,
        last_activity=1234567890.0
    )
    
    # 添加用户消息
    message_id = session.add_message(
        role="user",
        content="test command",
        command="ls -la"
    )
    
    assert message_id is not None
    assert len(session.messages) == 1
    assert session.messages[0].role == "user"
    assert session.messages[0].content == "test command"
    assert session.messages[0].command == "ls -la"
    assert session.last_activity > 1234567890.0


def test_session_get_recent_messages():
    """测试获取最近消息"""
    from mcp_ssh_server.session_manager import Session
    
    session = Session(
        id="session-123",
        name="test-session",
        connection_name="test-conn",
        created_at=1234567890.0,
        last_activity=1234567890.0
    )
    
    # 添加多条消息
    for i in range(5):
        session.add_message(
            role="user",
            content=f"message {i}",
            command=f"command {i}"
        )
    
    # 获取最近 3 条消息
    recent_messages = session.get_recent_messages(3)
    assert len(recent_messages) == 3
    assert recent_messages[0].content == "message 2"
    assert recent_messages[1].content == "message 3"
    assert recent_messages[2].content == "message 4"


def test_session_to_dict():
    """测试会话转换为字典"""
    from mcp_ssh_server.session_manager import Session
    
    session = Session(
        id="session-123",
        name="test-session",
        connection_name="test-conn",
        created_at=1234567890.0,
        last_activity=1234567890.0
    )
    
    # 添加消息
    session.add_message(role="user", content="test message")
    
    # 转换为字典
    session_dict = session.to_dict()
    
    assert session_dict["id"] == "session-123"
    assert session_dict["name"] == "test-session"
    assert session_dict["connection_name"] == "test-conn"
    assert session_dict["created_at"] == 1234567890.0
    assert session_dict["last_activity"] == 1234567890.0
    assert session_dict["message_count"] == 1
    assert session_dict["working_directory"] == "/home"
    assert isinstance(session_dict["environment"], dict)


def test_session_manager_creation():
    """测试会话管理器创建"""
    from mcp_ssh_server.session_manager import SessionManager
    
    manager = SessionManager()
    
    assert manager.sessions == {}
    assert manager._lock is not None


def test_session_manager_create_session():
    """测试会话管理器创建会话"""
    from mcp_ssh_server.session_manager import SessionManager
    
    manager = SessionManager()
    
    session_id = manager.create_session("test-session", "test-conn")
    
    assert session_id is not None
    assert session_id in manager.sessions
    assert manager.sessions[session_id].name == "test-session"
    assert manager.sessions[session_id].connection_name == "test-conn"


def test_session_manager_get_session():
    """测试会话管理器获取会话"""
    from mcp_ssh_server.session_manager import SessionManager
    
    manager = SessionManager()
    
    session_id = manager.create_session("test-session", "test-conn")
    
    session = manager.get_session(session_id)
    
    assert session is not None
    assert session.id == session_id
    assert session.name == "test-session"
    assert session.connection_name == "test-conn"
    
    # 测试获取不存在的会话
    non_existent_session = manager.get_session("non-existent")
    assert non_existent_session is None


def test_session_manager_delete_session():
    """测试会话管理器删除会话"""
    from mcp_ssh_server.session_manager import SessionManager
    
    manager = SessionManager()
    
    session_id = manager.create_session("test-session", "test-conn")
    assert session_id in manager.sessions
    
    # 删除会话
    result = manager.delete_session(session_id)
    
    assert result is True
    assert session_id not in manager.sessions
    
    # 测试删除不存在的会话
    result = manager.delete_session("non-existent")
    assert result is False


def test_session_manager_list_sessions():
    """测试会话管理器列出会话"""
    from mcp_ssh_server.session_manager import SessionManager
    
    manager = SessionManager()
    
    # 创建多个会话
    session_ids = []
    for i in range(3):
        session_id = manager.create_session(f"session-{i}", f"conn-{i}")
        session_ids.append(session_id)
    
    # 列出会话
    sessions = manager.list_sessions()
    
    assert len(sessions) == 3
    for i, session in enumerate(sessions):
        assert session["name"] == f"session-{i}"
        assert session["connection_name"] == f"conn-{i}"
        assert session["id"] in session_ids


def test_session_manager_add_user_message():
    """测试会话管理器添加用户消息"""
    from mcp_ssh_server.session_manager import SessionManager
    
    manager = SessionManager()
    session_id = manager.create_session("test-session", "test-conn")
    
    message_id = manager.add_user_message(session_id, "test command")
    
    assert message_id is not None
    session = manager.get_session(session_id)
    assert len(session.messages) == 1
    assert session.messages[0].role == "user"
    assert session.messages[0].content == "test command"


def test_session_manager_add_assistant_message():
    """测试会话管理器添加助手消息"""
    from mcp_ssh_server.session_manager import SessionManager
    
    manager = SessionManager()
    session_id = manager.create_session("test-session", "test-conn")
    
    message_id = manager.add_assistant_message(
        session_id, 
        "command output", 
        "test command",
        {"success": True, "stdout": "output"}
    )
    
    assert message_id is not None
    session = manager.get_session(session_id)
    assert len(session.messages) == 1
    assert session.messages[0].role == "assistant"
    assert session.messages[0].content == "command output"
    assert session.messages[0].command == "test command"
    assert session.messages[0].result["success"] is True


def test_session_manager_get_session_history():
    """测试会话管理器获取会话历史"""
    from mcp_ssh_server.session_manager import SessionManager
    
    manager = SessionManager()
    session_id = manager.create_session("test-session", "test-conn")
    
    # 添加消息
    manager.add_user_message(session_id, "user message")
    manager.add_assistant_message(session_id, "assistant message")
    
    # 获取历史
    history = manager.get_session_history(session_id)
    
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "user message"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "assistant message"


def test_session_manager_get_session_context():
    """测试会话管理器获取会话上下文"""
    from mcp_ssh_server.session_manager import SessionManager
    
    manager = SessionManager()
    session_id = manager.create_session("test-session", "test-conn")
    
    # 添加消息
    manager.add_user_message(session_id, "user message")
    
    # 获取上下文
    context = manager.get_session_context(session_id)
    
    assert context is not None
    assert context["session_id"] == session_id
    assert context["name"] == "test-session"
    assert context["connection_name"] == "test-conn"
    assert context["working_directory"] == "/home"
    assert context["message_count"] == 1
    
    # 测试获取不存在会话的上下文
    context = manager.get_session_context("non-existent")
    assert context is None


def test_config_manager_creation():
    """测试配置管理器创建"""
    from mcp_ssh_server.config import ConfigManager
    
    manager = ConfigManager()
    
    assert manager.config is not None
    assert manager.config_path is not None


def test_config_app_config_from_env():
    """测试应用配置从环境变量创建"""
    from mcp_ssh_server.config import AppConfig
    
    # 使用默认值
    config = AppConfig.from_env()
    
    assert config.log_level == "INFO"
    assert config.default_timeout == 30
    assert config.max_sessions == 100
    assert config.session_cleanup_hours == 24
    assert config.keepalive_interval == 60
    assert isinstance(config.connections, dict)


if __name__ == "__main__":
    pytest.main([__file__])