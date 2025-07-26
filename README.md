## 🚀 快速上手指南

只需4个步骤，即可在你的本地机器上运行 Zenith Agent。

### 步骤 1: 环境准备

首先，请确保你的电脑上已经安装了以下软件：
*   **Python 3.10 或更高版本**
*   **Git**

### 步骤 2: 下载项目并安装依赖

打开你的终端（命令行工具），然后依次执行以下命令来克隆项目代码、进入项目目录，并安装所有必需的软件库。

```bash
# 1. 克隆 GitHub 仓库
git clone https://github.com/zwell/Zenith-Agent

# 2. 进入项目目录
cd Zenith-Agent

# 3. 安装所有 Python 依赖包
pip install -r requirements.txt

# 4. 下载并安装 Playwright 所需的浏览器驱动
playwright install
```

### 步骤 3: 配置 API 密钥

本项目需要调用多个第三方服务，因此你需要配置相应的 API 密钥。

1.  **复制配置文件**:
    在项目根目录下，将 `.env.example` 文件复制一份，并重命名为 `.env`。

    ```bash
    cp .env.example .env
    ```

2.  **编辑 `.env` 文件**:
    用你喜欢的代码编辑器（如 VSCode）打开刚刚创建的 `.env` 文件。你会看到如下内容：

    ```ini
    # --- 必填：至少配置一个 LLM 提供商 ---
    # 根据你拥有的 API 密钥，取消注释并填入相应的值
    # GOOGLE_API_KEY="your_google_api_key"
    # OPENAI_API_KEY="your_openai_api_key"
    # DASHSCOPE_API_KEY="your_tongyi_api_key"

    # --- 必填：配置要使用的 LLM 模型 ---
    # 你可以自由组合，比如用 Google 做规划，用通义做执行
    ROUTER_LLM_PROVIDER="tongyi"
    PLANNER_LLM_PROVIDER="google"
    EXECUTOR_LLM_PROVIDER="tongyi"
    # ... (其他模型名称配置) ...

    # --- 推荐配置：为了获得更好的体验 ---
    TAVILY_API_KEY="your_tavily_api_key"         # 用于搜索引擎
    E2B_API_KEY="your_e2b_api_key"               # 用于代码沙箱
    LANGCHAIN_API_KEY="your_langsmith_api_key"   # 用于调试和可观测性
    # ... (LangSmith 其他配置) ...
    ```

3.  **获取并填入密钥**:
    *   **LLM 密钥**: 你**至少需要配置一个**大语言模型提供商（Google, OpenAI, 或通义千问）的 API 密钥。然后在下面配置 `..._LLM_PROVIDER` 和 `..._LLM_MODEL` 来指定使用哪个模型。
    *   **工具密钥**: 为了让 Agent 发挥全部能力，强烈建议你前往 [Tavily AI](https://tavily.com/), [E2B](https://e2b.dev/), 和 [LangSmith](https://smith.langchain.com/) 的官网注册并获取免费的 API 密钥。

### 步骤 4: 启动应用

你需要**打开两个独立的终端窗口**来分别启动后端和前端服务。

#### 终端窗口 1: 启动后端 API 服务

```bash
# 确保你仍然在项目的根目录下
uvicorn src.api.main:app
```
当你看到类似 `Uvicorn running on http://127.0.0.1:8000` 的输出时，表示后端服务已成功启动。

#### 终端窗口 2: 启动前端 Web 界面

```bash
# 确保你也在项目的根目录下
streamlit run ui/app.py
```
这个命令会自动在你的默认浏览器中打开一个新的标签页，地址通常是 `http://localhost:8501`。

🎉 **恭喜！** 你现在应该能看到 Zenith Agent 的 Web 界面了。试着输入一个任务（例如：“今天有什么关于AI的新闻吗？”），然后点击“执行任务”，观察 Agent 的工作过程吧！

---

### 常见问题 (FAQ)

*   **Q: 我必须配置所有 API 密钥吗？**
    *   A: 不是。你至少需要一个 LLM 的密钥。但如果没有 `TAVILY_API_KEY`，Agent 将无法搜索网络；没有 `E2B_API_KEY`，它将无法执行代码。`LANGCHAIN_API_KEY` 是可选的，但强烈推荐用于调试。

*   **Q: 启动时出现 `ModuleNotFoundError` 怎么办？**
    *   A: 请确保你在**项目根目录**下运行 `uvicorn` 和 `streamlit` 命令，而不是在 `src/` 或 `ui/` 目录里。