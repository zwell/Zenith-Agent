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
    placeholder="",
    help="详细描述你的任务，Agent会尝试理解并执行。"
)

# --- 运行按钮 ---
if st.button("🚀 执行任务", disabled=not task_input):
    # --- UI 准备 ---
    st.info("任务已开始，请稍候... 实时日志如下：")
    
    plan_placeholder = st.empty()
    log_placeholder = st.empty()
    result_placeholder = st.empty()
        
    st.session_state.log_entries = []
    st.session_state.plan_displayed = []
    st.session_state.result_displayed = ""

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

                        if event_type == "plan":
                            st.session_state.plan_displayed.append(data_str)
                        elif event_type == "result" or event_type == "error":
                            st.session_state.result_displayed = (event_type, data_str)
                        elif event_type == "langsmith_url":
                            st.info(f"🔍 [LangSmith Trace]({data_str}) (点击查看详细执行过程)")
                        else: # 普通日志
                            log_entry = f"`{time.strftime('%H:%M:%S')}` {data_str}"
                            st.session_state.log_entries.append(log_entry)

                        # 渲染计划（如果存在）
                        if st.session_state.plan_displayed:
                            for entry in st.session_state.plan_displayed:
                                st.text(entry)
                        
                        # 渲染所有累积的日志
                        with log_placeholder:
                            st.markdown("##### 实时日志")
                            # 遍历并显示每一条日志
                            for entry in st.session_state.log_entries:
                                st.text(entry) # 使用 st.text 保证格式统一，不会被误认为是Markdown

                        # 渲染最终结果（如果存在）
                        if st.session_state.result_displayed:
                            res_type, res_data = st.session_state.result_displayed
                            if res_type == "result":
                                result_placeholder.success("✅ 任务完成！最终结果：")
                                try: # 尝试以JSON或Markdown显示
                                    result_placeholder.json(res_data)
                                except:
                                    result_placeholder.markdown(res_data)
                            else:
                                result_placeholder.error(f"❌ 任务出错：{res_data}")

    except requests.exceptions.RequestException as e:
        st.error(f"连接后端服务失败: {e}")
    except Exception as e:
        st.error(f"处理过程中发生未知错误: {e}")