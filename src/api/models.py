from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum

class TaskRequest(BaseModel):
    task: str

class TaskCreationResponse(BaseModel):
    task_id: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
    message: Optional[str] = None


class ExecutionMode(str, Enum):
    SYNC = "sync" # 从 ASYNC 改为 SYNC
    STREAM = "stream"

class TaskRequest(BaseModel):
    task: str
    mode: ExecutionMode = Field(
        ExecutionMode.SYNC, # 默认改为 SYNC
        description="Execution mode: 'sync' for a single response, 'stream' for real-time events."
    )