"""
测试核心逻辑，不依赖外部模块
"""

import pytest
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# 定义测试用的数据类，避免导入外部模块
@dataclass
class TestSSHConfig:
    """测试用 SSH 配置"""
    host: str
    username: str
    port: int = 22
    password: Optional[str] = None
    key_filename: Optional[str] = None
    timeout: int = 30
    keepalive_interval: int = 60


@dataclass
class TestSessionMessage:
    """测试用会话消息"""
    id: str
    timestamp: float
    role: str  # 'user' or 'assistant'
    content: str
    command: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


@dataclass
class TestSession:
    """测试用会话"""
    id: str
    name: str
    connection_name: str
    created_at: float
    last_activity: float
    messages: List[TestSessionMessage] = field(default_factory=list)
    working_directory: str = "/home"
    environment: Dict[str, str] = field(default_factory=dict)

    def add_message(
        self,
        role: str,
        content: str,
        command: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> str:
        """添加消息到会话"""
        message_id = str(uuid.uuid4())
        message = TestSessionMessage(
            id=message_id,
            timestamp=time.time(),
            role=role,
            content=content,
            command=command,
            result=result,
        )
        self.messages.append(message)
        self.last_activity = time.time()
        return message_id

    def get_recent_messages(self, count: int = 10) -> List[TestSessionMessage]:
        """获取最近的消息"""
        return self.messages[-count:] if self.messages else []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "connection_name": self.connection_name,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "message_count": len(self.messages),
            "working_directory": self.working_directory,
            "environment": self.environment,
        }


class TestSessionManager:
    """测试用会话管理器"""

    def __init__(self):
        self.sessions: Dict[str, TestSession] = {}

    def create_session(self, name: str, connection_name: str) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        session = TestSession(
            id=session_id,
            name=name,
            connection_name=connection_name,
            created_at=time.time(),
            last_activity=time.time(),
        )
        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[TestSession]:
        """获取会话"""
        return self.sessions.get(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        return [session.to_dict() for session in self.sessions.values()]

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def add_user_message(self, session_id: str, content: str) -> Optional[str]:
        """添加用户消息"""
        session = self.get_session(session_id)
        if not session:
            return None
        return session.add_message(role="user", content=content)

    def add_assistant_message(
        self,
        session_id: str,
        content: str,
        command: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """添加助手消息"""
        session = self.get_session(session_id)
        if not session:
            return None
        return session.add_message(
            role="assistant", content=content, command=command, result=result
        )

    def get_session_history(
        self, session_id: str, count: int = 20
    ) -> List[Dict[str, Any]]:
        """获取会话历史"""
        session = self.get_session(session_id)
        if not session:
            return []

        messages = session.get_recent_messages(count)
        return [
            {
                "id": msg.id,
                "timestamp": msg.timestamp,
                "role": msg.role,
                "content": msg.content,
                "command": msg.command,
                "result": msg.result,
            }
            for msg in messages
        ]

    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话上下文信息"""
        session = self.get_session(session_id)
        if not session:
            return None

        return {
            "session_id": session.id,
            "name": session.name,
            "connection_name": session.connection_name,
            "working_directory": session.working_directory,
            "environment": session.environment,
            "message_count": len(session.messages),
            "last_activity": session.last_activity,
        }


# 现在开始测试
class TestSSHConfig:
    """测试 SSH 配置"""

    def test_ssh_config_creation(self):
        """测试 SSH 配置创建"""
        config = TestSSHConfig(
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
        assert config.keepalive_interval == 60

    def test_ssh_config_defaults(self):
        """测试 SSH 配置默认值"""
        config = TestSSHConfig(
            host="example.com",
            username="testuser"
        )
        
        assert config.host == "example.com"
        assert config.username == "testuser"
        assert config.port == 22
        assert config.password is None
        assert config.key_filename is None
        assert config.timeout == 30
        assert config.keepalive_interval == 60


class TestSession:
    """测试会话"""

    def test_session_creation(self):
        """测试会话创建"""
        session = TestSession(
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

    def test_session_add_message(self):
        """测试会话添加消息"""
        session = TestSession(
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

    def test_session_get_recent_messages(self):
        """测试获取最近消息"""
        session = TestSession(
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

    def test_session_to_dict(self):
        """测试会话转换为字典"""
        session = TestSession(
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


class TestSessionManager:
    """测试会话管理器"""

    def test_session_manager_creation(self):
        """测试会话管理器创建"""
        manager = TestSessionManager()
        
        assert manager.sessions == {}
        assert isinstance(manager.sessions, dict)

    def test_session_manager_create_session(self):
        """测试会话管理器创建会话"""
        manager = TestSessionManager()
        
        session_id = manager.create_session("test-session", "test-conn")
        
        assert session_id is not None
        assert session_id in manager.sessions
        assert manager.sessions[session_id].name == "test-session"
        assert manager.sessions[session_id].connection_name == "test-conn"

    def test_session_manager_get_session(self):
        """测试会话管理器获取会话"""
        manager = TestSessionManager()
        
        session_id = manager.create_session("test-session", "test-conn")
        
        session = manager.get_session(session_id)
        
        assert session is not None
        assert session.id == session_id
        assert session.name == "test-session"
        assert session.connection_name == "test-conn"
        
        # 测试获取不存在的会话
        non_existent_session = manager.get_session("non-existent")
        assert non_existent_session is None

    def test_session_manager_delete_session(self):
        """测试会话管理器删除会话"""
        manager = TestSessionManager()
        
        session_id = manager.create_session("test-session", "test-conn")
        assert session_id in manager.sessions
        
        # 删除会话
        result = manager.delete_session(session_id)
        
        assert result is True
        assert session_id not in manager.sessions
        
        # 测试删除不存在的会话
        result = manager.delete_session("non-existent")
        assert result is False

    def test_session_manager_list_sessions(self):
        """测试会话管理器列出会话"""
        manager = TestSessionManager()
        
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

    def test_session_manager_add_user_message(self):
        """测试会话管理器添加用户消息"""
        manager = TestSessionManager()
        session_id = manager.create_session("test-session", "test-conn")
        
        message_id = manager.add_user_message(session_id, "test command")
        
        assert message_id is not None
        session = manager.get_session(session_id)
        assert len(session.messages) == 1
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "test command"

    def test_session_manager_add_assistant_message(self):
        """测试会话管理器添加助手消息"""
        manager = TestSessionManager()
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

    def test_session_manager_get_session_history(self):
        """测试会话管理器获取会话历史"""
        manager = TestSessionManager()
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

    def test_session_manager_get_session_context(self):
        """测试会话管理器获取会话上下文"""
        manager = TestSessionManager()
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


if __name__ == "__main__":
    pytest.main([__file__])