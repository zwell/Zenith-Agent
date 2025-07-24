import asyncio
import traceback
import yaml
import logging.config
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from e2b import AsyncSandbox
from tenacity import retry, stop_after_attempt, wait_exponential

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

async def run_task(task: str):
    """
    初始化环境并执行单个任务。
    """
    # 异步上下文管理器，确保资源被正确释放
    async with async_playwright() as p, await AsyncSandbox.create(api_key=settings.E2B_API_KEY) as sandbox:
        browser = None
        try:
            browser = await p.chromium.launch(headless=settings.BROWSER_HEADLESS)
            
            # 创建Agent
            agent = await create_agent(browser, sandbox)

            print(f"开始执行任务: {task}")
            result = await invoke_agent_with_retry(agent, task)
            print(f"\n✅ 任务执行完成!", result)

        except PlaywrightTimeoutError:
            print("\n❌ 错误：浏览器操作超时。")
        except PlaywrightError as e:
            print(f"\n❌ 错误：发生浏览器或网络错误: {e}")
        except Exception as e:
            print(f"\n❌ 执行过程中发生未知错误: {e}")
            traceback.print_exc()

        finally:
            if browser and browser.is_connected():
                print("\n正在关闭浏览器...")
                await browser.close()
                print("浏览器已关闭。")
            print("沙箱已自动关闭。")


if __name__ == "__main__":
    try:
        task_input = input("请输入你的任务：")
        if task_input == "":
            print("您没有输入任何内容")
        # 在Windows上，你可能需要下面的策略来避免事件循环错误
        # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_task(task_input))
    except KeyboardInterrupt:
        print("\n程序被用户中断。")