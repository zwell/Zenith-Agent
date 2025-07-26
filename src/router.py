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
         "判断的核心标准是：**该任务是否需要访问外部、实时的信息或执行具体操作。**\n\n"
         "--- 规则 ---\n"
         "1.  如果查询是**纯粹的对话、常识性问答、文本总结、内容创作或数学计算**，这些你仅凭自身知识就能完成的任务，请返回: `direct_answer`\n"
         "    - 示例: '你好', '什么是人工智能?', '总结一下这段文字', '写一首诗', '2+2等于几?'\n\n"
         "2.  如果查询需要**获取当前、实时或非常具体的信息（如天气、新闻、股价、特定网站内容）**，或者需要**执行代码、操作文件**，这些必须使用工具才能完成的任务，请返回: `plan_and_execute`\n"
         "    - 示例: '今天天气怎么样?', '苹果公司最新的股价是多少?', '访问 xxx.com', '运行这段代码'"),
        ("human", "用户查询: ```{input}```"),
    ]
)

# --- 构建新的、更简单的路由链 ---
# 流程: 提示 -> LLM -> 输出字符串
router_chain = router_prompt | llm | StrOutputParser()