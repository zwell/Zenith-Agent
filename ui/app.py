import streamlit as st
import requests
import json
import time

# --- 配置 ---
# 你的 FastAPI 后端服务的地址
BACKEND_URL = "http://127.0.0.1:8000/tasks"

# --- Streamlit 页面配置 ---
st.set_page_config(page_title="Web Automation Agent", layout="wide")
st.title("🤖 Web Automation Agent")
st.caption("一个由 AI 驱动的网站自动化任务机器人")

# --- 任务输入 ---
task_input = st.text_input(
    "请输入你的任务：",
    placeholder="例如：访问tavily.com搜索'大型语言模型'，然后总结前三个结果。",
    help="详细描述你的任务，Agent会尝试理解并执行。"
)

# --- 运行按钮 ---
if st.button("🚀 执行任务", disabled=not task_input):
    # --- UI 准备 ---
    st.info("任务已开始，请稍候... 实时日志如下：")
    
    # 创建用于显示实时日志的占位符
    log_placeholder = st.empty()
    # 创建用于显示最终结果的占位符
    result_placeholder = st.empty()
    
    full_log = ""
    
    try:
        # --- 调用后端 API ---
        # 使用流式模式
        payload = {"task": task_input, "mode": "stream"}
        
        # requests 库需要设置 stream=True 来接收流式响应
        with requests.post(BACKEND_URL, json=payload, stream=True) as response:
            response.raise_for_status() # 如果HTTP状态码不是2xx，则抛出异常

            # 逐行读取流式响应
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    
                    # SSE 格式是 "event: <event_name>" 和 "data: <json_data>"
                    if decoded_line.startswith('event:'):
                        event_type = decoded_line.split(':', 1)[1].strip()
                    elif decoded_line.startswith('data:'):
                        data_str = decoded_line.split(':', 1)[1].strip()
                        
                        # 简单的日志追加逻辑
                        log_entry = f"[{time.strftime('%H:%M:%S')}] {event_type.upper()}: {data_str}\n"
                        full_log += log_entry
                        
                        # 在UI上更新日志
                        log_placeholder.markdown(f"```log\n{full_log}\n```")

                        # 特殊事件处理
                        if event_type == "langsmith_url":
                            st.info(f"🔍 [LangSmith Trace]({data_str}) (点击查看详细执行过程)")
                        
                        if event_type == "result":
                            result_placeholder.success("✅ 任务完成！最终结果：")
                            try:
                                # 优先尝试将结果作为JSON来解析和显示
                                result_data = json.loads(data_str)
                                result_placeholder.json(result_data)
                            except json.JSONDecodeError:
                                # 如果解析失败，说明它是一个普通字符串，直接用markdown显示
                                result_placeholder.markdown(data_str)

                        if event_type == "error":
                            result_placeholder.error(f"❌ 任务出错：{data_str}")

    except requests.exceptions.RequestException as e:
        st.error(f"连接后端服务失败: {e}")
    except Exception as e:
        st.error(f"处理过程中发生未知错误: {e}")