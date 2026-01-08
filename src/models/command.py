from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ExecutionMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"
    INTERACTIVE = "interactive"


class StreamChunk(BaseModel):
    content: str = Field(..., description="Stream content chunk")
    stream_type: str = Field(..., description="stdout, stderr, or mixed")
    timestamp: datetime = Field(default_factory=datetime.now)
    sequence: int = Field(..., description="Chunk sequence number")


class CommandResult(BaseModel):
    connection_id: str = Field(..., description="SSH connection identifier")
    command: str = Field(..., description="Executed command")
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error output")
    exit_code: int = Field(..., description="Command exit code")
    execution_time: float = Field(..., description="Execution time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now)
    mode: ExecutionMode = Field(default=ExecutionMode.SYNC)
    stream_chunks: Optional[List[StreamChunk]] = Field(
        default=None, description="Output stream chunks"
    )

    class Config:
        use_enum_values = True


class ExecuteRequest(BaseModel):
    connection_id: str = Field(..., description="SSH connection identifier")
    command: str = Field(..., description="Command to execute")
    mode: ExecutionMode = Field(default=ExecutionMode.SYNC)
    timeout: int = Field(default=300, description="Command timeout in seconds")
    working_directory: Optional[str] = Field(
        default=None, description="Remote working directory"
    )
    environment: Optional[Dict[str, str]] = Field(
        default=None, description="Environment variables"
    )
    shell: str = Field(
        default="/bin/bash", description="Shell to use for command execution"
    )

    class Config:
        use_enum_values = True


class ShellSession(BaseModel):
    session_id: str = Field(..., description="Interactive shell session identifier")
    connection_id: str = Field(..., description="Parent SSH connection identifier")
    shell_type: str = Field(default="/bin/bash", description="Shell type")
    working_directory: str = Field(default="~", description="Current working directory")
    environment: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)
