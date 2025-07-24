from playwright.sync_api import sync_playwright
from langchain.tools import tool
import dashscope
import os


class BrowserTool:
    def _get_search_keyword(self, instruction: str) -> str:
        """调用 LLM 提取用户想搜索的关键词"""
        prompt = f"从这句话中提取用户想搜索的关键词：'{instruction}'。只返回关键词，其他不要输出。"

        # dashscope.api_key = os.getenv("ALI_API_KEY")
        response = dashscope.Generation.call(
            model='qwen-turbo-latest', 
            prompt=prompt,
            top_p=0.8,
            temperature=0.9,
            result_format='message'
        )
        print(prompt, "\n", response)
        
        return response.output.choices[0].message.content

    def run(self, instruction: str):
        """主执行入口"""
        keyword = self._get_search_keyword(instruction)
        print(f"✅ 提取关键词: {keyword}")
        if not keyword:
            raise ValueError("keyword 参数不能为空")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto("https://www.baidu.com")

            # 百度搜索框：input[name=wd]，按钮：input[type=submit]
            page.fill("input[name=wd]", keyword)
            page.click("input[type=submit]")

            # 等待页面加载几秒
            page.wait_for_timeout(5000)
            browser.close()

@tool
def browser_search(text: str) -> str:
    """根据用户提供的查询内容，在网页中搜索相关信息并返回结果摘要。
    适合用于 LLM 不确定答案、需要查找最新资讯或需要浏览网页内容的场景。"""
    # tool = BrowserTool()
    # return tool.run(text)
    return "搜索结果"