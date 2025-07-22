import os
import asyncio
import json

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_experimental.plan_and_execute import PlanAndExecute, load_agent_executor, load_chat_planner
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain import hub
from langchain_community.chat_models import ChatTongyi
from langchain_community.agent_toolkits.playwright.toolkit import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser

from playwright.async_api import async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

from tools import get_current_date, input_tool
from tool_browser import browser_search

async def create_plan_and_execute_agent(browser):
    """创建PlanAndExecute Agent"""

    # 创建规划器 (Planner)
    plan_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    planner_prompt = (
        "请先理解任务内容，并制定解决该任务的计划。"
        " 请以“计划：”为标题输出，"
        "接着用编号列表的形式列出具体步骤。"
        "请使步骤数量尽可能少，且确保准确完成任务。"
        "如果任务是提问，最后一步通常是“根据以上步骤，请回答用户的原始问题”。"
        "在计划末尾，请输出“<END_OF_PLAN>”作为结束标志。"
    )
    planner = load_chat_planner(plan_llm, system_prompt=planner_prompt)

    # 创建执行器 (Executor)
    executor_llm = ChatTongyi(
        model="qwen-turbo-latest",
        temperature=0,
    )
    # 浏览器实例
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser)
    tools = toolkit.get_tools() + [get_current_date, input_tool]
    executor = load_agent_executor(executor_llm, tools, verbose=True)

    # 创建PlanAndExecute Agent
    agent = PlanAndExecute(planner=planner, executor=executor, verbose=True)

    return agent


async def main():
    """主函数"""
    print("=== LangChain PlanAndExecute Agent Demo ===")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        try:
            # 创建Agent
            agent = await create_plan_and_execute_agent(browser)

            # 定义任务
            #  task = """我下周二要从合肥去一趟上海，游玩三天。帮我查一下那几天的天气，结合当地的景点给我一个游玩计划。"""
            task = """给一个上海三天的旅游计划"""

            # 执行任务
            print(f"\n开始执行任务...")
            print(f"任务描述: {task}")
            print("\n" + "=" * 50)

            result = await agent.ainvoke({"input": task})

            print("\n" + "=" * 50)
            print("任务执行完成!")
            print(f"Agent输出: {result}")

        except PlaywrightTimeoutError:
            # 返回明确的超时错误类型
            return json.dumps({
                "status": "timeout_error",
                "details": "The page took too long to load and timed out. The website might be slow or blocking traffic."
            })

        except PlaywrightError as e:
            # 返回明确的网络/浏览器错误类型
            return json.dumps({
                "status": "network_error",
                "details": f"A browser-level network error occurred: {e.message}. The website might be offline or unreachable."
            })

        except Exception as e:
            print(f"\n❌ 执行过程中发生错误: {e}")
            import traceback
            traceback.print_exc()

        finally:
            print("\n正在关闭浏览器...")
            if browser and browser.is_connected():
                await browser.close()
            print("浏览器已关闭。")


if __name__ == "__main__":
    # <<< 修改点 4: 使用 asyncio.run() 来启动异步主函数
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断。")
