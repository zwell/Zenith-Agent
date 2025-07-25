from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatTongyi
from langchain_core.output_parsers import StrOutputParser

from config import settings
from src.llm_factory import get_llm

llm = get_llm(
    provider=settings.ROUTER_LLM_PROVIDER,
    model_name=settings.ROUTER_LLM_MODEL,
    temperature=settings.ROUTER_LLM_TEMPERATURE
)

# --- 创建新的、更简单的路由提示 ---
router_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
         "你是一个任务分类机器人。你的唯一工作是分析用户查询，并从以下两个选项中选择一个最合适的来描述它："
         "'direct_answer' 或 'plan_and_execute'。\n"
         "不要添加任何解释、标点符号或多余的文字，只返回这两个词中的一个。\n\n"
         "- 如果任务是简单的问答、对话、或总结，请返回: direct_answer\n"
         "- 如果任务需要使用工具（如浏览器、搜索引擎、代码执行）来完成，请返回: plan_and_execute"),
        ("human", "用户查询: ```{input}```"),
    ]
)

# --- 构建新的、更简单的路由链 ---
# 流程: 提示 -> LLM -> 输出字符串
router_chain = router_prompt | llm | StrOutputParser()