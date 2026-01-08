from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class AuthMethod(str, Enum):
    PASSWORD = "password"
    KEY = "key"
    AGENT = "agent"


class ConnectionStatus(str, Enum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ConnectionInfo(BaseModel):
    connection_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    host: str = Field(..., description="Remote server hostname or IP")
    port: int = Field(default=22, description="SSH port")
    username: str = Field(..., description="SSH username")
    auth_method: AuthMethod = Field(..., description="Authentication method")
    credentials: Optional[Dict[str, Any]] = Field(
        default=None, description="Authentication credentials"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    status: ConnectionStatus = Field(default=ConnectionStatus.DISCONNECTED)
    session_id: Optional[str] = Field(
        default=None, description="SSH session identifier"
    )

    class Config:
        use_enum_values = True


class ConnectionRequest(BaseModel):
    host: str = Field(..., description="Remote server hostname or IP")
    port: int = Field(default=22, description="SSH port")
    username: str = Field(..., description="SSH username")
    auth_method: AuthMethod = Field(..., description="Authentication method")
    password: Optional[str] = Field(
        default=None, description="Password for password auth"
    )
    private_key: Optional[str] = Field(default=None, description="Private key content")
    key_passphrase: Optional[str] = Field(
        default=None, description="Private key passphrase"
    )
    timeout: int = Field(default=30, description="Connection timeout in seconds")

    class Config:
        use_enum_values = True
