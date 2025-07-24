import uuid
import logging
import logging.config
import yaml
import asyncio
import sys
from fastapi import FastAPI, BackgroundTasks, HTTPException
from typing import Dict

# 检查是否在Windows上，并设置正确的asyncio事件循环策略
# 这段代码必须在任何asyncio相关的库（如FastAPI, uvicorn, playwright）被导入和使用之前执行
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 确保在API启动时加载日志配置
try:
    with open('config/logging_config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
except FileNotFoundError:
    logging.basicConfig(level=logging.INFO)
    logging.warning("logging_config.yaml not found, using basic logging.")

from src.api.models import TaskRequest, TaskCreationResponse, TaskStatusResponse
from src.task_runner import run_agent_task

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Web Automation Agent API",
    description="An API to automate web tasks using a Plan-and-Execute Agent.",
    version="1.0.0"
)

# ---- 简单的内存数据库来存储任务状态 ----
# 警告: 这只适用于演示！在生产环境中，你应该使用Redis, PostgreSQL等真实数据库。
tasks_db: Dict[str, Dict] = {}
# ----------------------------------------

async def background_task_wrapper(task_id: str, user_task: str):
    """
    包装器函数，在后台运行agent任务并更新任务数据库。
    """
    logger.info(f"Background task {task_id} started.")
    result = await run_agent_task(user_task)
    tasks_db[task_id] = result
    logger.info(f"Background task {task_id} finished. Status: {result['status']}")

@app.post("/tasks", response_model=TaskCreationResponse, status_code=202)
async def create_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    创建一个新的自动化任务。
    API会立即返回一个任务ID，并在后台开始执行任务。
    """
    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {"status": "running"}
    
    background_tasks.add_task(background_task_wrapper, task_id, request.task)
    
    logger.info(f"Task {task_id} created for prompt: '{request.task}'")
    return {"task_id": task_id, "message": "Task accepted and is running in the background."}

@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    根据任务ID查询任务的状态和结果。
    """
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    response = {"task_id": task_id, **task}
    return response

@app.get("/")
def read_root():
    return {"message": "Welcome to the Web Automation Agent API. Go to /docs to see the API documentation."}