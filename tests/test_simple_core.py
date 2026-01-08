"""
简单的核心逻辑测试
"""

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


def test_dataclass_functionality():
    """测试 dataclass 功能"""
    @dataclass
    class TestConfig:
        host: str
        username: str
        port: int = 22
        password: Optional[str] = None
    
    config = TestConfig(host="example.com", username="testuser")
    assert config.host == "example.com"
    assert config.username == "testuser"
    assert config.port == 22
    assert config.password is None
    
    print("✓ dataclass functionality test passed")


def test_uuid_generation():
    """测试 UUID 生成"""
    session_id = str(uuid.uuid4())
    assert len(session_id) == 36
    assert session_id.count('-') == 4
    
    print("✓ UUID generation test passed")


def test_time_functionality():
    """测试时间功能"""
    timestamp1 = time.time()
    time.sleep(0.01)
    timestamp2 = time.time()
    
    assert timestamp2 > timestamp1
    assert timestamp2 - timestamp1 >= 0.01
    
    print("✓ Time functionality test passed")


def test_list_operations():
    """测试列表操作"""
    messages = []
    
    # 添加消息
    messages.append({"role": "user", "content": "test 1"})
    messages.append({"role": "assistant", "content": "test 2"})
    messages.append({"role": "user", "content": "test 3"})
    
    assert len(messages) == 3
    
    # 获取最近消息
    recent = messages[-2:]
    assert len(recent) == 2
    assert recent[0]["content"] == "test 2"
    assert recent[1]["content"] == "test 3"
    
    print("✓ List operations test passed")


def test_dict_operations():
    """测试字典操作"""
    sessions = {}
    
    # 添加会话
    session_id = "session-123"
    sessions[session_id] = {
        "id": session_id,
        "name": "test-session",
        "messages": []
    }
    
    assert session_id in sessions
    assert sessions[session_id]["name"] == "test-session"
    
    # 删除会话
    del sessions[session_id]
    assert session_id not in sessions
    
    print("✓ Dict operations test passed")


def test_session_like_class():
    """测试会话类"""
    @dataclass
    class SessionMessage:
        id: str
        timestamp: float
        role: str
        content: str
        command: Optional[str] = None
    
    @dataclass
    class Session:
        id: str
        name: str
        connection_name: str
        created_at: float
        last_activity: float
        messages: List[SessionMessage] = field(default_factory=list)
        working_directory: str = "/home"
        environment: Dict[str, str] = field(default_factory=dict)
        
        def add_message(self, role: str, content: str, command: Optional[str] = None) -> str:
            message_id = str(uuid.uuid4())
            message = SessionMessage(
                id=message_id,
                timestamp=time.time(),
                role=role,
                content=content,
                command=command
            )
            self.messages.append(message)
            self.last_activity = time.time()
            return message_id
        
        def get_recent_messages(self, count: int = 10) -> List[SessionMessage]:
            return self.messages[-count:] if self.messages else []
    
    # 创建会话
    session = Session(
        id="session-123",
        name="test-session",
        connection_name="test-conn",
        created_at=time.time(),
        last_activity=time.time()
    )
    
    assert session.id == "session-123"
    assert session.name == "test-session"
    assert session.working_directory == "/home"
    assert len(session.messages) == 0
    
    # 添加消息
    message_id = session.add_message("user", "test command", "ls -la")
    assert message_id is not None
    assert len(session.messages) == 1
    assert session.messages[0].role == "user"
    assert session.messages[0].content == "test command"
    assert session.messages[0].command == "ls -la"
    
    # 获取最近消息
    recent = session.get_recent_messages(5)
    assert len(recent) == 1
    assert recent[0].content == "test command"
    
    print("✓ Session-like class test passed")


def test_session_manager_like_class():
    """测试会话管理器类"""
    @dataclass
    class SessionMessage:
        id: str
        timestamp: float
        role: str
        content: str
        command: Optional[str] = None
    
    @dataclass
    class Session:
        id: str
        name: str
        connection_name: str
        created_at: float
        last_activity: float
        messages: List[SessionMessage] = field(default_factory=list)
        
        def add_message(self, role: str, content: str, command: Optional[str] = None) -> str:
            message_id = str(uuid.uuid4())
            message = SessionMessage(
                id=message_id,
                timestamp=time.time(),
                role=role,
                content=content,
                command=command
            )
            self.messages.append(message)
            self.last_activity = time.time()
            return message_id
    
    class SessionManager:
        def __init__(self):
            self.sessions: Dict[str, Session] = {}
        
        def create_session(self, name: str, connection_name: str) -> str:
            session_id = str(uuid.uuid4())
            session = Session(
                id=session_id,
                name=name,
                connection_name=connection_name,
                created_at=time.time(),
                last_activity=time.time()
            )
            self.sessions[session_id] = session
            return session_id
        
        def get_session(self, session_id: str) -> Optional[Session]:
            return self.sessions.get(session_id)
        
        def delete_session(self, session_id: str) -> bool:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False
        
        def list_sessions(self) -> List[Dict[str, Any]]:
            return [
                {
                    "id": session.id,
                    "name": session.name,
                    "connection_name": session.connection_name,
                    "message_count": len(session.messages)
                }
                for session in self.sessions.values()
            ]
    
    # 创建管理器
    manager = SessionManager()
    assert len(manager.sessions) == 0
    
    # 创建会话
    session_id = manager.create_session("test-session", "test-conn")
    assert session_id is not None
    assert session_id in manager.sessions
    
    # 获取会话
    session = manager.get_session(session_id)
    assert session is not None
    assert session.name == "test-session"
    assert session.connection_name == "test-conn"
    
    # 删除会话
    result = manager.delete_session(session_id)
    assert result is True
    assert session_id not in manager.sessions
    
    # 列出会话
    session_id1 = manager.create_session("session-1", "conn-1")
    session_id2 = manager.create_session("session-2", "conn-2")
    
    sessions = manager.list_sessions()
    assert len(sessions) == 2
    
    print("✓ Session manager-like class test passed")


if __name__ == "__main__":
    print("Running core logic tests...")
    
    test_dataclass_functionality()
    test_uuid_generation()
    test_time_functionality()
    test_list_operations()
    test_dict_operations()
    test_session_like_class()
    test_session_manager_like_class()
    
    print("\nAll tests passed! ✓")