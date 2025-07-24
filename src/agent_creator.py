from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatTongyi
from langchain_experimental.plan_and_execute import PlanAndExecute, load_agent_executor, load_chat_planner
from langchain_community.agent_toolkits.playwright.toolkit import PlayWrightBrowserToolkit
from langchain_tavily import TavilySearch

# 导入我们自己的模块和配置
from config import settings
from src.tools.custom_tools import get_current_date, input_tool
from src.tools.sanbox import SandboxToolManager

async def create_agent(browser, sandbox):
    """
    根据传入的浏览器和沙箱实例，创建并返回一个Plan-and-Execute Agent。
    """
    # 规划器
    plan_llm = ChatGoogleGenerativeAI(
        model=settings.PLANNER_LLM_MODEL, 
        temperature=settings.PLANNER_LLM_TEMPERATURE,
        google_api_key=settings.GOOGLE_API_KEY
    )
    planner = load_chat_planner(plan_llm, system_prompt=settings.PLANNER_PROMPT)

    # 执行器
    executor_llm = ChatTongyi(
        model_name=settings.EXECUTOR_LLM_MODEL,
        temperature=settings.EXECUTOR_LLM_TEMPERATURE,
        dashscope_api_key=settings.DASHSCOPE_API_KEY,
    )

    # 工具集
    tools = [get_current_date, input_tool]
    tools.extend(PlayWrightBrowserToolkit.from_browser(async_browser=browser).get_tools())
    tools.append(TavilySearch(max_results=3)) 

    # E2B沙箱工具
    sandbox_tool_manager = SandboxToolManager(sandbox)
    tools.extend(sandbox_tool_manager.get_all_tools())
    
    # verbose=True 会在执行时打印详细日志，方便调试
    executor = load_agent_executor(executor_llm, tools, verbose=True)

    return PlanAndExecute(planner=planner, executor=executor, verbose=True)