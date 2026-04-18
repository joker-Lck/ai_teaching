@echo off
chcp 65001 >nul
echo ========================================
echo    AI 教学智能体 - 启动程序
echo ========================================
echo.

REM 检查 Python 是否已安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未检测到 Python
    echo 请先安装 Python 3.8 或更高版本
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit
)

REM 检查依赖是否已安装
echo 🔍 检查依赖包...
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  依赖包未安装，正在安装...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ 依赖安装失败！
        echo 请手动运行：pip install -r requirements.txt
        pause
        exit
    )
    echo ✅ 依赖安装完成！
    echo.
)

REM 检查 .env 文件
if not exist ".env" (
    echo ⚠️  未找到 .env 配置文件
    echo 如果已有 .env.example，请复制并修改为 .env
    if exist ".env.example" (
        echo 正在从 .env.example 创建 .env...
        copy .env.example .env
        echo ✅ 已创建 .env 文件，请编辑并填写配置信息
        pause
    )
    echo.
)

echo 🚀 正在启动 AI 教学智能体...
echo 📱 应用将在浏览器中自动打开
echo.
echo ========================================
echo 💡 提示：关闭此窗口将停止服务
echo ========================================
echo.

REM 启动 Streamlit 应用
streamlit run streamlit_001.py

pause
