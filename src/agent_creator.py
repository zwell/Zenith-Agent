from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatTongyi
from langchain_experimental.plan_and_execute import PlanAndExecute, load_agent_executor, load_chat_planner
from langchain_community.agent_toolkits.playwright.toolkit import PlayWrightBrowserToolkit
from langchain_tavily import TavilySearch
from typing import Optional, Callable
from langchain_core.callbacks import BaseCallbackHandler
from typing import Any, Dict, List, Optional, Callable, Union
from langchain_core.outputs import LLMResult, ChatGeneration
from config import settings
from src.tools.custom_tools import get_current_date, input_tool
from src.tools.sanbox import SandboxToolManager

class StreamingCallbackHandler(BaseCallbackHandler):
    """一个处理流式输出的回调处理器"""
    def __init__(self, send_event: Callable):
        self.send_event = send_event

    async def on_chat_model_start(
        self, serialized: Dict[str, Any], messages: List[List[Any]], **kwargs: Any
    ) -> None:
        """模型开始生成时"""
        # 可以选择在这里发送一个"思考中..."的事件
        pass

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """流式获取 LLM 的 token"""
        # 对于非流式模型，这个可能不会被频繁触发，但对于流式模型很有用
        await self.send_event("log", f"LLM Token: {token}")

    async def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """工具开始执行时"""
        tool_name = serialized.get("name")
        await self.send_event("log", f"Tool Start: {tool_name} with input '{input_str}'")

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """工具执行结束时"""
        await self.send_event("log", f"Tool End: output '{output[:100]}...'")

    async def on_planner_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """规划器开始时"""
        await self.send_event("log", "Planner started.")

    async def on_planner_end(self, output: Any, **kwargs: Any) -> Any:
        """规划器结束时"""
        await self.send_event("plan", output.return_values['output'])

async def create_agent(browser, sandbox, stream_callback: Optional[Callable] = None):
    """
    根据传入的浏览器和沙箱实例，创建并返回一个Plan-and-Execute Agent。
    """

    callbacks = [StreamingCallbackHandler(stream_callback)] if stream_callback else []

    # 规划器
    plan_llm = ChatGoogleGenerativeAI(
        model=settings.PLANNER_LLM_MODEL, 
        temperature=settings.PLANNER_LLM_TEMPERATURE,
        google_api_key=settings.GOOGLE_API_KEY,
        callbacks=callbacks,
    )
    planner = load_chat_planner(plan_llm, system_prompt=settings.PLANNER_PROMPT)

    # 执行器
    executor_llm = ChatTongyi(
        model_name=settings.EXECUTOR_LLM_MODEL,
        temperature=settings.EXECUTOR_LLM_TEMPERATURE,
        dashscope_api_key=settings.DASHSCOPE_API_KEY,
        callbacks=callbacks,
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