from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class FileType(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"
    LINK = "link"
    SOCKET = "socket"
    BLOCK_DEVICE = "block_device"
    CHARACTER_DEVICE = "character_device"
    FIFO = "fifo"


class FileOperation(str, Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"
    LIST = "list"
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MKDIR = "mkdir"
    CHMOD = "chmod"
    CHOWN = "chown"


class FileInfo(BaseModel):
    path: str = Field(..., description="File path")
    name: str = Field(..., description="File name")
    type: FileType = Field(..., description="File type")
    size: int = Field(default=0, description="File size in bytes")
    permissions: str = Field(
        default="", description="File permissions (e.g., 'rwxr-xr-x')"
    )
    owner: str = Field(default="", description="File owner")
    group: str = Field(default="", description="File group")
    modified_time: Optional[datetime] = Field(
        default=None, description="Last modified time"
    )
    access_time: Optional[datetime] = Field(
        default=None, description="Last access time"
    )
    is_symlink: bool = Field(
        default=False, description="Whether file is a symbolic link"
    )
    symlink_target: Optional[str] = Field(
        default=None, description="Symbolic link target"
    )

    class Config:
        use_enum_values = True


class ListDirectoryRequest(BaseModel):
    connection_id: str = Field(..., description="SSH connection identifier")
    path: str = Field(default=".", description="Directory path to list")
    detailed: bool = Field(
        default=True, description="Include detailed file information"
    )
    hidden: bool = Field(default=False, description="Include hidden files")
    recursive: bool = Field(default=False, description="Recursive directory listing")
    max_depth: int = Field(default=1, description="Maximum recursion depth")


class ListDirectoryResult(BaseModel):
    connection_id: str = Field(..., description="SSH connection identifier")
    path: str = Field(..., description="Listed directory path")
    files: List[FileInfo] = Field(
        default_factory=list, description="File and directory entries"
    )
    total_count: int = Field(default=0, description="Total number of entries")
    execution_time: float = Field(..., description="Listing execution time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now)


class FileTransferRequest(BaseModel):
    connection_id: str = Field(..., description="SSH connection identifier")
    local_path: str = Field(..., description="Local file path")
    remote_path: str = Field(..., description="Remote file path")
    permissions: Optional[str] = Field(
        default=None, description="File permissions (chmod format)"
    )
    overwrite: bool = Field(default=False, description="Overwrite existing files")
    preserve_timestamps: bool = Field(
        default=True, description="Preserve file timestamps"
    )


class FileTransferResult(BaseModel):
    connection_id: str = Field(..., description="SSH connection identifier")
    operation: FileOperation = Field(..., description="File operation type")
    local_path: str = Field(..., description="Local file path")
    remote_path: str = Field(..., description="Remote file path")
    success: bool = Field(..., description="Operation success status")
    bytes_transferred: int = Field(default=0, description="Number of bytes transferred")
    transfer_time: float = Field(..., description="Transfer time in seconds")
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True
