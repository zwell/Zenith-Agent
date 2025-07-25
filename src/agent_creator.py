from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatTongyi
from langchain_experimental.plan_and_execute import PlanAndExecute, load_agent_executor, load_chat_planner
from langchain_community.agent_toolkits.playwright.toolkit import PlayWrightBrowserToolkit
from langchain_tavily import TavilySearch
from typing import Optional, Callable
from uuid import UUID
from langchain_core.callbacks import BaseCallbackHandler
from typing import Any, Dict, List, Optional, Callable, Union
from langchain_core.outputs import LLMResult, ChatGeneration
from config import settings
from src.tools.custom_tools import get_current_date
from src.tools.sanbox import SandboxToolManager
from src.llm_factory import get_llm

class StreamingCallbackHandler(BaseCallbackHandler):
    """一个处理流式输出的回调处理器"""
    def __init__(self, send_event: Callable):
        self.send_event = send_event
        self.planner_run_id: Optional[UUID] = None

    async def on_chat_model_start(
        self, serialized: Dict[str, Any], messages: List[List[Any]], **kwargs: Any
    ) -> None:
        """模型开始生成时"""
        # await self.send_event("log", "思考中...")
        pass

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """流式获取 LLM 的 token"""
        # 对于非流式模型，这个可能不会被频繁触发，但对于流式模型很有用
        await self.send_event("log", f"LLM Token: {token}")

    async def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """工具开始执行时"""
        tool_name = serialized.get("name")
        # 将日志信息格式化得更易读
        await self.send_event("log", f"⏳ 正在调用工具: `{tool_name}` | 输入: `{input_str}`")

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """工具执行结束时"""
        if output is not None:
            await self.send_event("log", f"✅ 工具返回: `{output[:200]}...`")

    async def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any
    ) -> None:
        print(parent_run_id, run_id)
        print("on_chain_start", inputs)
        # --- 关键逻辑：识别 Planner Chain ---
        # PlanAndExecute Agent内部的Planner Chain通常有一个特定的名称或结构
        # 我们可以通过 `serialized.get('name')` 或其他特征来识别它
        # 一个简单的（但不完全可靠的）方法是假设第一个非最外层的链是Planner
        # 更可靠的方法是检查 'id' 或 'name' 字段
        # 例如，load_chat_planner 创建的链的id可能包含 "LLMChain"
        if self.planner_run_id is None and parent_run_id is not None:
             # 假设第一个子链是 planner
             self.planner_run_id = run_id
             await self.send_event("log", "📝 规划器已启动，正在制定计划...")

    async def on_chain_end(
        self, outputs: Dict[str, Any], *, run_id: UUID, **kwargs: Any
    ) -> Any:
        print("on_chain_end", outputs, run_id)
        """在链结束时触发"""
        # --- 关键逻辑：检查是否是 Planner Chain 结束 ---
        if run_id == self.planner_run_id:
            # 如果是 Planner Chain 结束，就提取计划并发送
            plan_text = outputs.get('text', '无法提取计划文本。')
            await self.send_event("plan", plan_text)
            self.planner_run_id = None # 重置 run_id，以备将来使用

async def create_agent(browser, sandbox, stream_callback: Optional[Callable] = None):
    """
    根据传入的浏览器和沙箱实例，创建并返回一个Plan-and-Execute Agent。
    """

    # 规划器
    plan_llm = get_llm(
        provider=settings.PLANNER_LLM_PROVIDER,
        model_name=settings.PLANNER_LLM_MODEL,
        temperature=settings.PLANNER_LLM_TEMPERATURE
    )
    planner = load_chat_planner(
        plan_llm, 
        system_prompt=settings.PLANNER_PROMPT,
    )

    # 执行器
    executor_llm = get_llm(
        provider=settings.EXECUTOR_LLM_PROVIDER,
        model_name=settings.EXECUTOR_LLM_MODEL,
        temperature=settings.EXECUTOR_LLM_TEMPERATURE
    )

    # 工具集
    tools = [get_current_date]
    tools.extend(PlayWrightBrowserToolkit.from_browser(async_browser=browser).get_tools())
    tools.append(TavilySearch(max_results=3)) 

    # E2B沙箱工具
    sandbox_tool_manager = SandboxToolManager(sandbox)
    tools.extend(sandbox_tool_manager.get_all_tools())
    
    # verbose=True 会在执行时打印详细日志，方便调试
    executor = load_agent_executor(
        executor_llm, 
        tools, 
        verbose=True,
    )

    return PlanAndExecute(
        planner=planner, 
        executor=executor, 
        verbose=True,
        callbacks=[StreamingCallbackHandler(stream_callback)]
    )