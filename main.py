#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Faster-Whisper 语音转文字工具
主启动文件
"""

import sys

from controller import WhisperGUI

def main():
    """主函数"""
    try:
        print("🚀 启动 Faster-Whisper 语音转文字工具...")
        app = WhisperGUI()
        app.run()
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 