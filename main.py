import os
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI # 导入 Gemini 的聊天模型类
from langchain.chains.llm_math.base import LLMMathChain
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.tools import Tool, tool
from langchain_experimental.plan_and_execute import PlanAndExecute, load_agent_executor, load_planner

# --- 1. 设置模型 ---
# 我们需要两个模型：一个用于规划 (Planner)，一个用于执行步骤中的推理 (Executor)
# 通常可以使用同一个模型，但也可以根据需求选择不同能力的模型
# Planner 需要强大的推理能力来制定计划，Executor 可以用稍弱的模型来执行具体任务
# 这里我们统一使用 gpt-4-turbo，因为它在规划和遵循指令方面表现出色
# model = ChatOpenAI(model="gpt-4-turbo", temperature=0)

# --- 1. 设置模型 (使用 Gemini) ---
# 将 ChatOpenAI 替换为 ChatGoogleGenerativeAI
# 'gemini-pro' 是一个性能和成本都比较均衡的强大模型，非常适合作为 Agent 的大脑
try:
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    # 如果 1.5 Pro 不可用或遇到问题，可以换成 gemini-pro
    # model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0, convert_system_message_to_human=True)
except Exception as e:
    print(f"初始化 Gemini 模型失败，请检查 API Key 和网络连接。错误: {e}")
    exit()

# --- 2. 定义我们的工具 (Tools) ---
# Agent的能力边界完全由其拥有的工具决定。工具的描述至关重要，LLM会根据描述来决定何时使用哪个工具。

# 2.1. 搜索工具: 用于查询实时信息，比如股价
# LangChain 已经内置了很多好用的工具，比如 DuckDuckGo 搜索
search_tool = DuckDuckGoSearchRun()

# 2.2. 计算工具: 当需要进行数学运算时使用
# LLM 本身不擅长精确计算，所以提供一个计算工具非常重要
llm_math_chain = LLMMathChain.from_llm(llm=model, verbose=True)
math_tool = Tool(
    name="Calculator",
    func=llm_math_chain.run,
    description="当需要回答关于数学的问题时非常有用。例如：'3乘以4是多少？'"
)

# 2.3. 自定义工具: 文件写入工具
# 我们可以用 @tool 装饰器轻松创建自定义工具
@tool
def write_to_file(filename: str, content: str) -> str:
    """
    当需要将文本内容保存到文件时使用此工具。
    :param filename: str, 要写入的文件的名称。
    :param content: str, 需要写入文件的具体内容。
    :return: str, 一个表示操作成功的确认消息。
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    return f"内容已成功写入文件 '{filename}'。"

# 将所有工具放入一个列表
tools = [search_tool, math_tool, write_to_file]

# --- 3. 创建 Planner 和 Executor (这是修改的核心) ---

# 3.1. 创建 Planner (规划器) - 【这是关键的修正点】
# 我们使用 load_planner 函数，它需要 LLM 和工具列表作为输入，
# 以便在生成的规划 Prompt 中包含所有工具的描述。
planner = load_planner(llm=model, tools=tools, verbose=True)

# 3.2. 创建 Executor (执行器) - (这部分不变)
# Executor 同样需要 LLM 和工具列表来执行任务
executor = load_agent_executor(llm=model, tools=tools, verbose=True)


# --- 4. 创建并运行 PlanAndExecute Agent (现在是正确的) ---
# 现在我们将正确的 planner 和 executor 实例传入
agent = PlanAndExecute(planner=planner, executor=executor, verbose=True)

# --- 5. 执行任务 ---
# 提出我们复杂的多步骤问题
user_question = "请帮我查询一下英伟达（NVIDIA）和AMD这两家公司最近的股价，然后比较一下哪家更高，并把最终的比较结果写入一个名为 `stock_comparison.txt` 的文件中。"

print(f"正在执行任务: {user_question}\n")

# 使用 .invoke() 方法来运行 Agent
# LangChain 会自动处理整个流程：规划 -> 执行 -> 返回最终答案
try:
    result = agent.invoke(user_question)
    print("\n\n✅ 任务完成！")
    print("最终结果:")
    print(result)

    # 验证文件是否创建成功
    if os.path.exists("stock_comparison.txt"):
        print("\n📄 正在读取创建的文件 'stock_comparison.txt'...")
        with open("stock_comparison.txt", 'r', encoding='utf-8') as f:
            print("--- 文件内容 ---")
            print(f.read())
            print("------------------")
except Exception as e:
    print(f"\n\n❌ 任务执行出错: {e}")