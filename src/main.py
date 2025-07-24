import asyncio
import traceback
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from e2b import AsyncSandbox

# 导入我们自己的模块和配置
from config import settings
from src.agent_creator import create_agent

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
            result = await agent.ainvoke({"input": task})
            print(f"\n✅ 任务执行完成!")
            print("------最终结果------")
            print(result.get('output', '没有获取到最终结果。'))
            print("--------------------")


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
        # 在Windows上，你可能需要下面的策略来避免事件循环错误
        # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_task(task_input))
    except KeyboardInterrupt:
        print("\n程序被用户中断。")