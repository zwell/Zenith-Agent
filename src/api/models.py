from pydantic import BaseModel
from typing import Optional, Any

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