"""
会话管理器

管理多轮交互会话，维护会话状态、历史记录和上下文信息。
"""

import time
import uuid
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class SessionMessage:
    """会话消息"""

    id: str
    timestamp: float
    role: str  # 'user' or 'assistant'
    content: str
    command: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


@dataclass
class Session:
    """交互会话"""

    id: str
    name: str
    connection_name: str
    created_at: float
    last_activity: float
    messages: List[SessionMessage] = field(default_factory=list)
    working_directory: str = "/home"
    environment: Dict[str, str] = field(default_factory=dict)
    shell = None  # 交互式 shell 对象
    shell_active: bool = False  # shell 是否活跃

    def add_message(
        self,
        role: str,
        content: str,
        command: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> str:
        """添加消息到会话"""
        message_id = str(uuid.uuid4())
        message = SessionMessage(
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

    def get_recent_messages(self, count: int = 10) -> List[SessionMessage]:
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


class SessionManager:
    """会话管理器"""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()

    def create_session(self, name: str, connection_name: str) -> str:
        """创建新会话"""
        try:
            session_id = str(uuid.uuid4())
            session = Session(
                id=session_id,
                name=name,
                connection_name=connection_name,
                created_at=time.time(),
                last_activity=time.time(),
            )

            with self._lock:
                self.sessions[session_id] = session

            logger.info(f"会话创建成功: {name} ({session_id})")
            return session_id

        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            raise

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        with self._lock:
            return self.sessions.get(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        with self._lock:
            return [session.to_dict() for session in self.sessions.values()]

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            with self._lock:
                if session_id in self.sessions:
                    del self.sessions[session_id]
                    logger.info(f"会话已删除: {session_id}")
                    return True
                return False

        except Exception as e:
            logger.error(f"删除会话失败: {e}")
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

    def update_working_directory(self, session_id: str, directory: str) -> bool:
        """更新工作目录"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.working_directory = directory
        return True

    def update_environment(self, session_id: str, env_vars: Dict[str, str]) -> bool:
        """更新环境变量"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.environment.update(env_vars)
        return True

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

    def cleanup_inactive_sessions(self, max_inactive_hours: int = 24):
        """清理不活跃的会话"""
        try:
            current_time = time.time()
            inactive_sessions = []

            with self._lock:
                for session_id, session in self.sessions.items():
                    inactive_hours = (current_time - session.last_activity) / 3600
                    if inactive_hours > max_inactive_hours:
                        inactive_sessions.append(session_id)

            for session_id in inactive_sessions:
                self.delete_session(session_id)
                logger.info(f"清理不活跃会话: {session_id}")

        except Exception as e:
            logger.error(f"清理不活跃会话失败: {e}")

    def export_session(self, session_id: str) -> Optional[str]:
        """导出会话为 JSON 字符串"""
        session = self.get_session(session_id)
        if not session:
            return None

        try:
            export_data = {
                "session": session.to_dict(),
                "messages": [
                    {
                        "id": msg.id,
                        "timestamp": msg.timestamp,
                        "role": msg.role,
                        "content": msg.content,
                        "command": msg.command,
                        "result": msg.result,
                    }
                    for msg in session.messages
                ],
            }
            return json.dumps(export_data, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"导出会话失败: {e}")
            return None

    def import_session(self, session_data: str) -> Optional[str]:
        """从 JSON 字符串导入会话"""
        try:
            data = json.loads(session_data)
            session_info = data["session"]
            messages = data["messages"]

            session = Session(
                id=session_info["id"],
                name=session_info["name"],
                connection_name=session_info["connection_name"],
                created_at=session_info["created_at"],
                last_activity=session_info["last_activity"],
                working_directory=session_info.get("working_directory", "/home"),
                environment=session_info.get("environment", {}),
            )

            for msg_data in messages:
                message = SessionMessage(
                    id=msg_data["id"],
                    timestamp=msg_data["timestamp"],
                    role=msg_data["role"],
                    content=msg_data["content"],
                    command=msg_data.get("command"),
                    result=msg_data.get("result"),
                )
                session.messages.append(message)

            with self._lock:
                self.sessions[session.id] = session

            logger.info(f"会话导入成功: {session.name} ({session.id})")
            return session.id

        except Exception as e:
            logger.error(f"导入会话失败: {e}")
            return None

    def create_shell(self, session_id: str, shell) -> bool:
        """为会话创建 shell"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.shell = shell
        session.shell_active = True
        session.last_activity = time.time()
        return True

    def get_shell(self, session_id: str):
        """获取会话的 shell"""
        session = self.get_session(session_id)
        if not session or not session.shell_active:
            return None
        return session.shell

    def close_shell(self, session_id: str) -> bool:
        """关闭会话的 shell"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.shell_active = False
        session.shell = None
        session.last_activity = time.time()
        return True

    def is_shell_active(self, session_id: str) -> bool:
        """检查会话的 shell 是否活跃"""
        session = self.get_session(session_id)
        if not session:
            return False
        return session.shell_active
