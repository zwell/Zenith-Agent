import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_experimental.plan_and_execute import PlanAndExecute, load_agent_executor, load_chat_planner
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain import hub
from tools import get_current_date, input_tool
from tool_browser import browser_search
from langchain_community.chat_models import ChatTongyi
from langchain_community.agent_toolkits.playwright.toolkit import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser

async def create_plan_and_execute_agent():
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
    browser = await create_async_playwright_browser(headless=False)
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser)
    tools = toolkit.get_tools() + [get_current_date, input_tool]
    executor = load_agent_executor(executor_llm, tools, verbose=True)

    # 创建PlanAndExecute Agent
    agent = PlanAndExecute(planner=planner, executor=executor, verbose=True)

    return agent


def main():
    """主函数"""
    print("=== LangChain PlanAndExecute Agent Demo ===")

    # 创建Agent
    agent = create_plan_and_execute_agent()

    # 定义任务
    task = """我下周二要从合肥去一趟上海，游玩三天。帮我查一下来回的车票，选择性价比最高的三个；然后查一下那几天的天气，结合当地的景点给我一个游玩计划。"""

    try:
        # 执行任务
        print(f"\n开始执行任务...")
        print(f"任务描述: {task}")
        print("\n" + "=" * 50)

        result = agent.invoke({"input": task})

        print("\n" + "=" * 50)
        print("任务执行完成!")
        print(f"Agent输出: {result}")

        # 检查文件是否生成
        if os.path.exists('stock_comparison.txt'):
            print("\n✅ stock_comparison.txt 文件已生成")
            with open('stock_comparison.txt', 'r') as f:
                content = f.read()
                print(f"文件内容:\n{content}")
        else:
            print("\n❌ stock_comparison.txt 文件未生成")

    except Exception as e:
        print(f"\n❌ 执行过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

