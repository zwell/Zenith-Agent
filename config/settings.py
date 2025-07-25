import os
from dotenv import load_dotenv

# 从 .env 文件加载环境变量
# 这会查找项目根目录下的 .env 文件
load_dotenv()

LANGCHAIN_DEBUG = os.getenv("LANGCHAIN_DEBUG")

# --- API 密钥 ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY") # Qwen/Tongyi 使用的是这个
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
E2B_API_KEY = os.getenv("E2B_API_KEY")

# --- LLM 配置 ---
PLANNER_LLM_MODEL = "gemini-2.5-flash"
PLANNER_LLM_TEMPERATURE = 0.0
EXECUTOR_LLM_MODEL = "qwen-turbo" # langchain-community中qwen-turbo-latest可能会有变化，用qwen-turbo更稳定
EXECUTOR_LLM_TEMPERATURE = 0.0

# --- Browser 配置 ---
# True 为无头模式（后台运行），False 为有头模式（会弹出浏览器窗口）
BROWSER_HEADLESS = False 

# --- Agent 配置 ---
PLANNER_PROMPT = (
    "请先理解任务内容，并制定解决该任务的计划。"
    " 请以“计划：”为标题输出，"
    "接着用编号列表的形式列出具体步骤。"
    "请使步骤数量尽可能少，且确保准确完成任务。"
    "如果任务是提问，最后一步通常是“根据以上步骤，请回答用户的原始问题”。"
    "在计划末尾，请输出“<END_OF_PLAN>”作为结束标志。"
)