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

    playwright_cm = async_playwright()
    p = None
    sandbox_cm = None
    sandbox = None
    browser = None

    try:
        p = await playwright_cm.__aenter__()
        sandbox_cm = await AsyncSandbox.create(api_key=settings.E2B_API_KEY)
        sandbox = await sandbox_cm.__aenter__()

        if shutdown_event and shutdown_event.is_set():
            raise asyncio.CancelledError("Shutdown signal received before browser launch.")

        browser = await p.chromium.launch(headless=settings.BROWSER_HEADLESS)

        agent = await create_agent(browser, sandbox, stream_callback)

        if shutdown_event and shutdown_event.is_set():
            raise asyncio.CancelledError("Shutdown signal received before agent execution.")

        agent_task = asyncio.create_task(
            agent.ainvoke(
                {"input": task},
                config={"callbacks": agent.callbacks} if stream_callback else None
            )
        )
        shutdown_task = asyncio.create_task(shutdown_event.wait()) if shutdown_event else None

        done, pending = await asyncio.wait(
            [t for t in [agent_task, shutdown_task] if t is not None],
            return_when=asyncio.FIRST_COMPLETED
        )

        if shutdown_task and shutdown_task in done:
            agent_task.cancel()
            raise asyncio.CancelledError("Shutdown signal received during agent execution.")

        result = await agent_task
        output = result.get('output', 'No output from agent.')
        logger.info(f"Agent task for '{task}' finished successfully.")

        if stream_callback:
            await stream_callback("result", output)
        return {"status": "completed", "result": output}
        
    except PlaywrightTimeoutError:
        error_message = "Browser operation timed out."
        logger.error(error_message)
        return {"status": "error", "message": error_message}
    
    except PlaywrightError as e:
        error_message = f"Browser or network error: {e}"
        logger.error(error_message)
        return {"status": "error", "message": error_message}
    
    except asyncio.CancelledError as e:
        logger.warning(f"Task cancelled: {e}")
        return {"status": "cancelled", "message": str(e)}
    
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logger.exception(error_message)
        if stream_callback:
            await stream_callback("error", error_message)
        return {"status": "error", "message": error_message}
    
    finally:
        if browser and browser.is_connected():
            await browser.close()
        if sandbox_cm:
            await sandbox_cm.__aexit__(None, None, None)
        if playwright_cm:
            await playwright_cm.__aexit__(None, None, None)
        logger.info(f"Resources for task '{task}' have been cleaned up.")
        
        