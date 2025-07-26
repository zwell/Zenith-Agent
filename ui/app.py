import streamlit as st
import requests
import json
import time

# --- 配置 ---
BACKEND_URL = "http://127.0.0.1:8000/tasks"

# --- Streamlit 页面配置 ---
st.set_page_config(page_title="Web Automation Agent", layout="wide")
st.title("🤖 Web Automation Agent")
st.caption("一个由 AI 驱动的网站自动化任务机器人")

# --- 任务输入 ---
task_input = st.text_input("请输入你的任务：", placeholder="例如：特斯拉最新的股价是多少？")

# --- 运行按钮 ---
if st.button("🚀 执行任务", disabled=not task_input):
    st.info("任务已开始，请稍候...")
    
    # 定义UI占位符
    plan_placeholder = st.empty()
    log_placeholder = st.empty()
    result_placeholder = st.empty()
    
    # 存储日志和最终结果
    log_content = ""
    result_data = None
    event_type = "log"

    try:
        payload = {"task": task_input, "mode": "stream"}
        with requests.post(BACKEND_URL, json=payload, stream=True, timeout=600) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue
                
                decoded_line = line.decode('utf-8').strip()

                if decoded_line.startswith('event:'):
                    event_type = decoded_line.split(':', 1)[1].strip()
                    continue

                if decoded_line.startswith('data:'):
                    data_str = decoded_line.split(':', 1)[1].strip()

                    # 1. 健壮地解析 data
                    try:
                        # 我们的后端约定所有数据都是JSON编码的字符串
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        # 如果发生错误，说明后端可能发送了意外的纯文本
                        # 我们将其作为字符串处理，并打印警告
                        print(f"Warning: Received non-JSON data from stream: {data_str}")
                        data = data_str

                    # 2. 根据事件类型更新对应的UI部分
                    if event_type == "plan":
                        with plan_placeholder.expander("📝 Agent 执行计划", expanded=True):
                            st.markdown(data)
                    elif event_type == "result":
                        result_data = ("result", data)
                    elif event_type == "error":
                        result_data = ("error", data)
                    elif event_type == "langsmith_url":
                        st.info(f"🔍 [LangSmith Trace]({data})")
                    elif event_type == "end":
                        st.info(f"任务完成{data}")
                    else: # log
                        log_content += f"`{time.strftime('%H:%M:%S')}` {data}\n"
                        log_placeholder.text_area("实时日志", value=log_content, height=300)

    except Exception as e:
        result_data = ("error", str(e))
    
    # 循环结束后，显示最终结果
    if result_data:
        res_type, res_data_val = result_data
        if res_type == "result":
            result_placeholder.success("✅ 任务完成！最终结果：")
            # 最终结果可能是JSON或文本，我们再次健壮处理
            if isinstance(res_data_val, (dict, list)):
                 result_placeholder.json(res_data_val)
            else:
                 result_placeholder.markdown(res_data_val)
        else: # error
            result_placeholder.error(f"❌ 任务出错：{res_data_val}")