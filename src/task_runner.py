import asyncio
import traceback
import yaml
import asyncio
import logging.config
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from e2b import AsyncSandbox
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional, Callable
from config import settings
from src.agent_creator import create_agent

# 日志
try:
    with open('config/logging_config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
except FileNotFoundError:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.warning("logging_config.yaml not found, using basic logging.")

logger = logging.getLogger(__name__)

# 带重试的 Agent 调用函数
@retry(
    stop=stop_after_attempt(3), # 最多重试3次
    wait=wait_exponential(multiplier=1, min=4, max=10), # 等待时间指数增长，4s, 8s, 10s
    reraise=True # 如果重试3次后仍然失败，则抛出原始异常
)
async def invoke_agent_with_retry(agent, task: str):
    """
    包装 agent.ainvoke 调用，增加重试逻辑。
    """
    logger.info("正在调用 Agent...")
    result = await agent.ainvoke({"input": task})
    return result

async def run_agent_task(
        task: str,
        stream_callback: Optional[Callable] = None,
        shutdown_event: Optional[asyncio.Event] = None
    ) -> dict:
    """
    一个独立的、可调用的函数，用于执行完整的Agent任务。
    它会处理所有资源的创建和清理。
    成功则返回结果，失败则返回包含错误信息的字典。
    """

    logger.info(f"Starting agent task for: '{task}'")

    try:
        # 我们将把异步上下文管理器拆开，以便在中间插入检查
        p = await async_playwright().__aenter__()
        sandbox = await (await AsyncSandbox.create(api_key=settings.E2B_API_KEY)).__aenter__()
        
        # 检查退出信号
        if shutdown_event and shutdown_event.is_set():
            raise asyncio.CancelledError("Shutdown signal received before browser launch.")

        browser = await p.chromium.launch(headless=settings.BROWSER_HEADLESS)

        try:
            agent = await create_agent(browser, sandbox, stream_callback)

            # 检查退出信号
            if shutdown_event and shutdown_event.is_set():
                raise asyncio.CancelledError("Shutdown signal received before agent execution.")

            # 创建两个任务：agent执行和等待退出信号
            agent_task = asyncio.create_task(
                agent.ainvoke(
                    {"input": task},
                    config={"callbacks": agent.callbacks} if stream_callback else None
                )
            )
            shutdown_task = asyncio.create_task(shutdown_event.wait()) if shutdown_event else None

            # 等待其中一个任务完成
            done, pending = await asyncio.wait(
                [task for task in [agent_task, shutdown_task] if task is not None],
                return_when=asyncio.FIRST_COMPLETED
            )

            if shutdown_task and shutdown_task in done:
                agent_task.cancel() # 取消agent任务
                raise asyncio.CancelledError("Shutdown signal received during agent execution.")

            # 如果是agent任务完成了
            result = await agent_task

            output = result.get('output', 'No output from agent.')

            logger.info(f"Agent task for '{task}' finished successfully.")

            return {"status": "success", "result": output}
        
        finally:
            # 确保所有资源都被清理
            if browser and browser.is_connected():
                await browser.close()
            await sandbox.__aexit__(None, None, None)
            await p.__aexit__(None, None, None)

    except PlaywrightTimeoutError:
        error_message = "Browser operation timed out."
        logger.error(error_message)
        return {"status": "error", "message": error_message}
    
    except PlaywrightError as e:
        error_message = f"Browser or network error: {e}"
        logger.error(error_message)
        return {"status": "error", "message": error_message}
    
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logger.exception(error_message)
        return {"status": "error", "message": error_message}
        
        