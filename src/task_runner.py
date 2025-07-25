import asyncio
import traceback
import yaml
import asyncio
import logging.config
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from e2b import AsyncSandbox
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional, Callable
from config import settings
from src.agent_creator import create_agent
from src.router import router_chain 
from src.llm_factory import get_llm

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
        # 分析任务类型
        if stream_callback:
            await stream_callback("log", "正在分析任务类型...")
        
        try:
            route = await router_chain.ainvoke({"input": task})
            route = route.strip() # 去掉可能存在的多余空格或换行符

            # 是否有效
            if route not in ["direct_answer", "plan_and_execute"]:
                logger.warning(
                    f"Router chain returned an unexpected string: '{route}'. "
                    "Defaulting to 'plan_and_execute'."
                )
                if stream_callback:
                    await stream_callback("log", "路由分析异常，将采用默认的简单模式处理。")
                route = "direct_answer" # 回退到安全默认值

        except Exception as e:
            route = "direct_answer"
            logger.error(f"Error during routing: {e}. Defaulting to 'direct_answer'.")
            if stream_callback:
                await stream_callback("log", f"路由分析出错: {e}。将采用默认的简单模式处理。")
  
        if route == "direct_answer": # 直接回复的任务
            direct_answer_llm = get_llm(
                provider=settings.EXECUTOR_LLM_PROVIDER, 
                model_name=settings.EXECUTOR_LLM_MODEL,
                temperature=settings.DIRECT_ANSWER_LLM_TEMPERATURE # 使用单独的温度配置
            )
            direct_answer_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", "你是一个乐于助人的AI助手。请直接、友好地回答用户的问题。"),
                    ("human", "{input}")
                ]
            )
            direct_answer_chain = direct_answer_prompt | direct_answer_llm | StrOutputParser()
            
            # 直接调用LLM回答
            if stream_callback:
                await stream_callback("log", "正在生成直接回答...")
            
            # 使用流式调用 (astream)
            final_answer = ""
            async for chunk in direct_answer_chain.astream({"input": task}):
                final_answer += chunk
                if stream_callback:
                    # 为了简化，我们一次性发送最终结果，但也可以发送每个chunk
                    # await stream_callback("chunk", chunk)
                    pass
            
            # 任务完成
            logger.info(f"Direct answer for '{task}' finished successfully.")
            if stream_callback:
                await stream_callback("result", final_answer)
            return {"status": "completed", "result": final_answer}

        elif route == "plan_and_execute": # 需要规划的任务
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
            
            finally:
                if browser and browser.is_connected():
                    await browser.close()
                if sandbox_cm:
                    await sandbox_cm.__aexit__(None, None, None)
                if playwright_cm:
                    await playwright_cm.__aexit__(None, None, None)
                logger.info(f"Resources for task '{task}' have been cleaned up.")
    
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logger.exception(error_message)
        if stream_callback:
            await stream_callback("error", error_message)
        return {"status": "error", "message": error_message}
        