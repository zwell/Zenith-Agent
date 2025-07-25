from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatTongyi
from langchain_core.language_models import BaseChatModel

from config import settings

def get_llm(provider: str, model_name: str, temperature: float, **kwargs) -> BaseChatModel:
    """
    一个工厂函数，根据提供的参数创建并返回一个LLM实例。
    
    :param provider: LLM提供商 (e.g., "google", "openai", "tongyi")
    :param model_name: 具体的模型名称
    :param temperature: 模型温度
    :param kwargs: 其他传递给模型构造函数的参数 (如 callbacks)
    :return: 一个实现了 BaseChatModel 的LLM实例
    """
    provider = provider.lower()
    
    if provider == "google":
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=settings.GOOGLE_API_KEY,
            **kwargs
        )
    elif provider == "openai":
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            openai_api_key=settings.OPENAI_API_KEY,
            **kwargs
        )
    elif provider == "tongyi":
        return ChatTongyi(
            model_name=model_name,
            temperature=temperature,
            dashscope_api_key=settings.DASHSCOPE_API_KEY,
            **kwargs
        )
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")