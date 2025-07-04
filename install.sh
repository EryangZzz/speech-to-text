#!/bin/bash

# Faster-Whisper 语音转文字工具 - macOS/Linux 安装脚本

echo "================================================"
echo "   Faster-Whisper 语音转文字工具 - 安装脚本"
echo "================================================"
echo ""

echo "🔍 第1步: 检查Python环境..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ 未找到Python! 请先安装Python 3.8或更高版本"
    echo "📥 macOS: brew install python"
    echo "📥 Linux: sudo apt install python3"
    exit 1
fi

$PYTHON_CMD --version
echo "✅ Python环境正常"

echo ""
echo "🔍 第2步: 检查conda环境..."
USE_CONDA=false
if command -v conda &> /dev/null; then
    echo "✅ 检测到conda环境"
    
    echo "💡 建议创建专用的conda环境来避免依赖冲突"
    echo "是否创建新的conda环境 'whisper_env'? (推荐) [y/N]: "
    read -r choice
    
    if [[ $choice =~ ^[Yy]$ ]]; then
        echo "🔧 创建conda环境: whisper_env"
        conda create -n whisper_env python=3.10 -y
        
        echo "🔄 激活环境..."
        source "$(conda info --base)/etc/profile.d/conda.sh"
        conda activate whisper_env
        
        echo "✅ conda环境已创建并激活"
        USE_CONDA=true
    else
        echo "ℹ️  将在当前环境中安装"
    fi
else
    echo "ℹ️  未检测到conda，将在当前Python环境中安装"
fi

echo ""
echo "🔄 第3步: 升级pip..."
$PYTHON_CMD -m pip install --upgrade pip

echo ""
echo "📦 第4步: 安装依赖包..."
# 根据操作系统选择PyTorch安装方式
OS_TYPE=$(uname -s)
if [[ "$OS_TYPE" == "Darwin" ]]; then
    echo "🍎 检测到macOS系统"
    if [[ $(uname -m) == "arm64" ]]; then
        echo "   - 安装PyTorch (Apple Silicon M1/M2)..."
        pip install torch torchvision torchaudio
    else
        echo "   - 安装PyTorch (Intel Mac)..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    fi
elif [[ "$OS_TYPE" == "Linux" ]]; then
    echo "🐧 检测到Linux系统"
    echo "   - 安装PyTorch (CPU版本)..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

echo "   - 安装Faster-Whisper..."
pip install faster-whisper

echo "   - 安装GUI组件..."
pip install customtkinter tkinterdnd2 Pillow

echo "   - 安装其他依赖..."
pip install numpy

echo ""
echo "🎯 第5步: 检查安装结果..."
$PYTHON_CMD -c "import torch; print('✅ PyTorch: %s' % torch.__version__)"
$PYTHON_CMD -c "import faster_whisper; print('✅ Faster-Whisper: 已安装')"
$PYTHON_CMD -c "import customtkinter; print('✅ CustomTkinter: 已安装')"
$PYTHON_CMD -c "import tkinterdnd2; print('✅ TkinterDnD2: 已安装')"

echo ""
echo "🚀 第6步: 安装完成!"
echo "💡 运行方式:"
if [[ $USE_CONDA == true ]]; then
    echo "   1. conda activate whisper_env"
    echo "   2. python main.py"
else
    echo "   python main.py"
fi
echo "💡 程序已安装完成，可以直接使用！"
echo ""

echo "是否现在运行程序? (y/n)"
read -r run_choice
if [[ $run_choice =~ ^[Yy]$ ]]; then
    echo "🎉 启动程序..."
    $PYTHON_CMD main.py
fi

echo ""
echo "感谢使用! 按回车键退出..."
read -r 