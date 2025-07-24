from langchain.tools import tool
from datetime import datetime

@tool
def get_current_date(_: str = "") -> str:
    """
    获取当前日期。
    """
    return datetime.now().strftime("%Y-%m-%d")

@tool
def input_tool(prompt: str) -> str:
    """
    当需要向用户提问以获取更多信息时使用此工具。
    """
    # 打印提示，等待输入
    user_input = input(f"{prompt}\n请输入：")
    return user_input.strip()