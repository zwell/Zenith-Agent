# 1. 安装 Python 包
pip install -r requirements.txt

# 2. 安装 Playwright 浏览器驱动
playwright install

# 3. 启动后端服务
uvicorn src.api.main:app

# 4. 启动前端服务
streamlit run ui/app.py