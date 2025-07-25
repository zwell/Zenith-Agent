import logging
import logging.config
import yaml
import asyncio
import sys
import json
from fastapi import FastAPI, Request
from sse_starlette import EventSourceResponse
from typing import Any
from langchain.globals import set_debug
from config import settings

# 调试模式
if hasattr(settings, 'LANGCHAIN_DEBUG') and settings.LANGCHAIN_DEBUG:
    set_debug(True)

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
    
    if mode == "sync":
        # 同步模式：直接调用、等待、返回结果
        logger.info(f"Executing task in 'sync' mode for: '{request.task}'")
        # 传递 shutdown_event 以支持 Ctrl+C
        result_data = await run_agent_task(request.task, shutdown_event=shutdown_event)
        return result_data

    elif request.mode == "stream":
        logger.info(f"Executing task in 'stream' mode for: '{request.task}'")
        
        # 使用 asyncio.Queue 作为中间的桥梁
        # Agent 把事件放入队列，主循环从队列中取出并发送
        event_queue = asyncio.Queue()

        async def stream_generator():
            try:
                while True:
                    # 从队列中获取事件
                    event = await event_queue.get()
                    
                    # 检查是否是结束信号
                    if event is None:
                        yield {"event": "end", "data": "Stream finished."}
                        break
                    
                    event_name, data = event
                    
                    if await fastapi_req.is_disconnected():
                        logger.warning("Client disconnected, stopping stream.")
                        break

                    if not isinstance(data, str):
                        data = json.dumps(data, ensure_ascii=False)
                    
                    yield {"event": event_name, "data": data}
                    
                    # 标记任务完成，让 get() 不再阻塞
                    event_queue.task_done()

            except asyncio.CancelledError:
                logger.warning("Stream generator cancelled.")
        
        # 定义一个真正的协程回调函数，它只负责把事件放入队列
        async def queue_callback(event_name: str, data: Any):
            await event_queue.put((event_name, data))
            
        # 在后台启动Agent任务，它会通过回调函数向队列中填充事件
        async def run_in_background():
            try:
                await run_agent_task(
                    request.task, 
                    stream_callback=queue_callback, 
                    shutdown_event=shutdown_event
                )
            finally:
                # 任务结束后，放入结束信号
                await event_queue.put(None)

        # 启动后台任务，但不等待它完成
        asyncio.create_task(run_in_background())

        return EventSourceResponse(stream_generator())
