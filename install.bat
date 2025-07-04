@echo off
chcp 65001 >nul
echo ================================================
echo    Faster-Whisper 语音转文字工具 - 安装脚本
echo ================================================
echo.

echo 🔍 第1步: 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python! 请先安装Python 3.8或更高版本
    echo 📥 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo ✅ Python环境正常

echo.
echo 🔍 第2步: 检查当前环境...
echo ℹ️  将在当前Python环境中安装依赖

echo.
echo 🔄 第3步: 升级pip...
python -m pip install --upgrade pip

echo.
echo 📦 第4步: 安装依赖包...
echo   - 安装PyTorch (CPU版本)...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

echo   - 安装Faster-Whisper...
pip install faster-whisper

echo   - 安装GUI组件...
pip install customtkinter tkinterdnd2 Pillow

echo   - 安装其他依赖...
pip install numpy

echo.
echo 🎯 第5步: 检查安装结果...
python -c "import torch; print('✅ PyTorch: %s' % torch.__version__)"
python -c "import faster_whisper; print('✅ Faster-Whisper: 已安装')"
python -c "import customtkinter; print('✅ CustomTkinter: 已安装')"
python -c "import tkinterdnd2; print('✅ TkinterDnD2: 已安装')"

echo.
echo 🚀 第6步: 安装完成! 
echo 💡 运行方式: python main.py
echo 💡 程序已安装完成，可以直接使用！
echo.

echo 是否现在运行程序? (y/n)
set /p choice=请选择: 
if /i "%choice%"=="y" (
    echo 🎉 启动程序...
    python main.py
)

echo.
echo 感谢使用! 按任意键退出...
pause >nul 