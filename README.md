# Faster-Whisper 语音转文字工具

基于OpenAI Whisper的高精度语音识别工具，使用Faster-Whisper优化，速度比原版快4倍，内存占用减少45%。

## 📁 项目结构

```
whisper_demo/
├── main.py                    # 主启动文件
├── controller/                # 控制器模块
│   ├── __init__.py           # 模块初始化
│   ├── gui_controller.py     # GUI控制器
│   └── whisper_engine.py     # Whisper引擎
├── install/                   # 安装脚本
│   ├── install.sh           # macOS/Linux安装脚本
│   └── install.bat          # Windows安装脚本
├── setup/                     # 打包脚本
│   ├── build_exe.py         # exe打包脚本
│   └── test_setup.py        # 环境测试脚本
├── requirements.txt          # Python依赖
├── config.json              # 配置文件
└── README.md                # 项目说明
```

## 🎯 功能特点

- **高精度识别**: 基于OpenAI Whisper，支持中英文等多语言
- **性能优化**: 使用Faster-Whisper，速度提升4倍，内存节省45%
- **现代GUI**: 基于CustomTkinter的现代化界面
- **拖拽操作**: 支持文件拖拽，操作简便
- **多格式支持**: 支持MP3、WAV、M4A、FLAC、MP4、AVI、MOV等格式
- **智能配置**: 自动检测硬件，推荐最佳配置
- **结果保存**: 自动保存转录结果和SRT字幕文件
- **完全独立**: 可打包成exe，无需Python环境

## 🚀 快速开始

### 1. 环境安装

#### macOS/Linux
```bash
# 进入项目目录
cd whisper_demo

# 运行安装脚本
chmod +x install/install.sh
./install/install.sh
```

#### Windows
```bat
# 进入项目目录
cd whisper_demo

# 运行安装脚本
install\install.bat
```

### 2. 运行程序

```bash
# 激活conda环境
conda activate whisper_demo

# 运行主程序
python main.py
```

### 3. 使用说明

1. **选择文件**: 拖拽或点击浏览选择音频/视频文件
2. **配置参数**: 根据硬件配置选择合适的模型和设备
3. **开始转录**: 点击"开始转录"按钮
4. **查看结果**: 转录完成后在结果区域查看文本
5. **保存结果**: 结果会自动保存到音频文件同级目录

## ⚙️ 配置建议

### 模型选择
- **tiny**: 最快速度，39MB，适合快速测试
- **base**: 平衡选择，74MB，推荐日常使用 ⭐
- **small**: 更高质量，244MB，适合重要内容
- **medium**: 高质量，769MB，需要较多内存
- **large-v3**: 最高质量，1550MB，需要强力硬件

### 硬件配置
- **8GB内存**: 推荐tiny或base模型，CPU模式
- **16GB内存**: 推荐base或small模型，可用GPU模式
- **32GB内存**: 可使用medium或large模型
- **有NVIDIA显卡**: 选择GPU模式，float16精度
- **仅有CPU**: 选择CPU模式，int8精度

### 参数说明
- **模型大小**: 影响转录质量和速度
- **处理设备**: auto(自动)/cpu/cuda
- **语言**: auto(自动检测)/zh/en/ja/ko等
- **计算精度**: auto/float16/float32/int8
- **VAD过滤**: 启用可过滤静音部分

## 📦 打包分发

### 打包成exe文件

```bash
# 进入setup目录
cd setup

# 运行打包脚本
python build_exe.py
```

打包完成后，在`release/`目录中会生成:
- `WhisperGUI.exe`: 可执行文件
- `使用说明.txt`: 详细使用说明
- `config.json`: 配置文件模板

### 分发给其他用户

1. 将`release/`目录中的文件复制给用户
2. 用户双击`WhisperGUI.exe`即可运行
3. 无需安装Python环境或任何依赖

## 🔧 开发说明

### 项目架构

- **main.py**: 简洁的启动文件，负责初始化和启动应用
- **controller/**: 核心业务逻辑
  - `gui_controller.py`: 处理GUI界面和用户交互
  - `whisper_engine.py`: 处理语音转文字的核心逻辑
- **install/**: 环境安装脚本
- **setup/**: 打包和部署脚本

### 代码特点

- **模块化设计**: 清晰的模块分离，便于维护
- **面向对象**: 使用类封装功能，代码结构清晰
- **异常处理**: 完善的错误处理机制
- **配置管理**: 支持配置保存和恢复
- **多线程**: 避免界面冻结，提升用户体验

## 📋 依赖列表

```
faster-whisper>=0.9.0
torch>=2.0.0
customtkinter>=5.2.0
tkinterdnd2>=0.3.0
numpy>=1.21.0
scipy>=1.7.0
```

## 🐛 问题排查

### 常见问题

1. **模型下载失败**: 确保网络连接正常
2. **GPU不工作**: 检查NVIDIA驱动是否最新
3. **内存不足**: 选择更小的模型或增加虚拟内存
4. **转录结果不准确**: 尝试更大的模型或指定语言

### 调试模式

```bash
# 运行测试脚本
python setup/test_setup.py

# 查看详细日志
python main.py --verbose
```

## 📞 支持与反馈

如遇问题或建议，请提供:
- 操作系统版本
- 音频文件格式和大小
- 选择的配置参数
- 错误信息截图

## 🎯 更新日志

### v1.0.0
- ✅ 基础功能实现
- ✅ 现代化GUI界面
- ✅ 多格式支持
- ✅ 自动配置检测
- ✅ 结果自动保存
- ✅ exe打包支持

### 计划功能
- 🔄 实时语音转录
- 🔄 批量处理功能
- 🔄 更多语言支持
- 🔄 云端模型支持

## 📜 许可证

本项目基于MIT许可证开源。

---

💝 感谢使用Faster-Whisper语音转文字工具！ 