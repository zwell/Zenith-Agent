from langchain.tools import tool
from datetime import datetime

@tool
def get_current_date(_: str = "") -> str:
    """获取当前的日期，返回格式为 YYYY-MM-DD。适合用于需要当前日期的场景。"""
    return datetime.now().strftime("%Y-%m-%d")

@tool
def input_tool(prompt: str) -> str:
    """
    当信息不确认时提示用户输入。
    参数 prompt 是等待用户输入时显示的提示信息。
    返回用户输入的字符串。
    """
    # 打印提示，等待输入
    user_input = input(f"{prompt}\n请输入：")
    return user_input.strip()