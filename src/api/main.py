import logging
import logging.config
import yaml
import asyncio
import sys
import json
from fastapi import FastAPI, Request
from sse_starlette import EventSourceResponse

# 检查是否在Windows上，并设置正确的asyncio事件循环策略
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 退出信号
shutdown_event = asyncio.Event()

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

def handle_shutdown_signal(sig, frame):
    """信号处理函数，设置退出事件"""
    logger.info("Received shutdown signal. Attempting graceful shutdown...")
    shutdown_event.set()

@app.on_event("startup")
async def startup_event():
    """应用启动时，设置信号处理器"""
    # 在非Windows系统上，标准信号处理更可靠
    if sys.platform != "win32":
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        signal.signal(signal.SIGTERM, handle_shutdown_signal)
    
    logger.info("Application startup complete. Press Ctrl+C to exit.")

@app.post("/tasks") # 不再需要 response_model 和 status_code
async def execute_task(request: TaskRequest, fastapi_req: Request):
    """
    执行一个自动化任务。
    - mode='sync' (或留空): 同步执行任务，等待完成后一次性返回最终结果。
    - mode='stream': 保持连接，通过Server-Sent Events流式返回进度。
    """
    mode = request.mode
    
    # 兼容旧的 'async' 模式名，统一为 'sync' 行为
    if mode == "async":
        mode = "sync"
        
    if mode == "sync":
        # 同步模式：直接调用、等待、返回结果
        logger.info(f"Executing task in 'sync' mode for: '{request.task}'")
        # 传递 shutdown_event 以支持 Ctrl+C
        result_data = await run_agent_task(request.task, shutdown_event=shutdown_event)
        return result_data

    elif mode == "stream":
        # 流式模式：逻辑和之前基本一样
        logger.info(f"Executing task in 'stream' mode for: '{request.task}'")
        
        async def stream_generator():
            async def send_event(event_name: str, data: Any):
                if await fastapi_req.is_disconnected() or shutdown_event.is_set():
                    logger.warning("Client disconnected or shutdown signal received, stopping stream.")
                    # 抛出一个异常来中断生成器
                    raise asyncio.CancelledError("Client disconnected or shutdown.")
                
                if not isinstance(data, str):
                    data = json.dumps(data, ensure_ascii=False) # ensure_ascii=False 对中文友好
                
                yield {"event": event_name, "data": data}

            try:
                # 传递 shutdown_event
                await run_agent_task(request.task, stream_callback=send_event, shutdown_event=shutdown_event)
                yield {"event": "end", "data": "Stream finished."}
            except asyncio.CancelledError:
                yield {"event": "error", "data": "Task cancelled by server or client."}

        return EventSourceResponse(stream_generator())