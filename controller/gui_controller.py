#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GUI控制器 - 处理用户界面和交互逻辑
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
from datetime import datetime
import json
from .whisper_engine import WhisperEngine

# 设置CustomTkinter主题
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class ToolTip:
    """工具提示类"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
    
    def on_enter(self, event=None):
        """鼠标进入时显示提示"""
        if self.tooltip:
            return
        
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(
            self.tooltip,
            text=self.text,
            background="lightyellow",
            relief="solid",
            borderwidth=1,
            font=("Arial", 10),
            justify="left",
            wraplength=300
        )
        label.pack()
    
    def on_leave(self, event=None):
        """鼠标离开时隐藏提示"""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class WhisperGUI:
    def __init__(self):
        # 创建主窗口
        self.root = TkinterDnD.Tk()
        self.root.title("Faster-Whisper 语音转文字工具 v1.0")
        self.root.geometry("1200x800")  # 进一步增大窗口尺寸
        self.root.minsize(1000, 700)   # 增大最小尺寸，确保按钮可见
        
        # 初始化变量
        self.processing = False
        self.current_file = ""
        
        # 初始化Whisper引擎
        self.whisper_engine = WhisperEngine()
        
        # 配置参数
        self.config = {
            "model_size": "base",
            "device": "auto", 
            "compute_type": "auto",
            "language": "auto",
            "beam_size": 5,
            "vad_filter": True,
            "temperature": 0.0
        }
        
        self.setup_ui()
        self.load_config()
        
    def setup_ui(self):
        """设置用户界面 - 重新设计的简洁布局"""
        # 主容器 - 使用grid布局更可靠
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)  # 让结果区域可以扩展
        
        # 顶部控制区域 - 不固定高度，让内容自然展开
        control_frame = ctk.CTkFrame(self.root)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        control_frame.grid_columnconfigure(0, weight=1)
        
        # 标题
        title_label = ctk.CTkLabel(
            control_frame, 
            text="🎙️ Faster-Whisper 语音转文字工具",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.grid(row=0, column=0, pady=(10, 8), sticky="ew")
        
        # 文件选择区域
        self.setup_file_area(control_frame, row=1)
        
        # 配置区域  
        self.setup_config_area(control_frame, row=2)
        
        # 处理区域
        self.setup_process_area(control_frame, row=3)
        
        # 结果区域 - 可扩展
        result_frame = ctk.CTkFrame(self.root)
        result_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        result_frame.grid_columnconfigure(0, weight=1)
        result_frame.grid_rowconfigure(1, weight=1)  # 让文本框可以扩展
        
        self.setup_result_area(result_frame)
        
        # 状态栏 - 固定在底部
        self.setup_status_bar()
        
    def setup_file_area(self, parent, row):
        """文件选择区域"""
        file_frame = ctk.CTkFrame(parent)
        file_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        file_frame.grid_columnconfigure(1, weight=1)
        
        # 标题
        file_label = ctk.CTkLabel(file_frame, text="📁 选择音频文件:", font=ctk.CTkFont(size=12, weight="bold"))
        file_label.grid(row=0, column=0, padx=10, pady=(8, 3), sticky="w")
        
        # 格式提示
        format_label = ctk.CTkLabel(
            file_frame, 
            text="支持: MP3, WAV, M4A, FLAC, MP4, AVI, MOV 等",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        format_label.grid(row=0, column=1, padx=10, pady=(8, 3), sticky="e")
        
        # 文件输入框
        self.file_entry = ctk.CTkEntry(
            file_frame, 
            placeholder_text="拖拽文件到此处或点击浏览选择文件...",
            height=32
        )
        self.file_entry.grid(row=1, column=0, columnspan=2, padx=(10, 5), pady=(0, 8), sticky="ew")
        
        # 浏览按钮
        browse_btn = ctk.CTkButton(
            file_frame, 
            text="浏览", 
            command=self.browse_file,
            width=70,
            height=32
        )
        browse_btn.grid(row=1, column=2, padx=(5, 10), pady=(0, 8))
        
        # 启用拖拽功能
        self.file_entry.drop_target_register(DND_FILES)
        self.file_entry.dnd_bind('<<Drop>>', self.on_file_drop)
        
    def setup_config_area(self, parent, row):
        """配置区域"""
        config_frame = ctk.CTkFrame(parent)
        config_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        config_frame.grid_columnconfigure(0, weight=1)
        
        # 标题
        config_label = ctk.CTkLabel(config_frame, text="⚙️ 转录配置:", font=ctk.CTkFont(size=12, weight="bold"))
        config_label.grid(row=0, column=0, padx=10, pady=(8, 3), sticky="w")
        
        # 配置选项 - 使用grid布局让控件整齐排列
        options_frame = ctk.CTkFrame(config_frame)
        options_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        
        # 第一行：模型、设备、语言
        current_col = 0
        
        # 模型
        ctk.CTkLabel(options_frame, text="模型:", font=ctk.CTkFont(size=11)).grid(row=0, column=current_col, padx=(10, 5), pady=8, sticky="w")
        current_col += 1
        
        self.model_var = ctk.StringVar(value="base")
        model_combo = ctk.CTkComboBox(
            options_frame,
            values=["tiny", "base", "small", "medium", "large-v3"],
            variable=self.model_var,
            width=90, height=28, font=ctk.CTkFont(size=11)
        )
        model_combo.grid(row=0, column=current_col, padx=5, pady=8)
        current_col += 1
        
        # 设备
        ctk.CTkLabel(options_frame, text="设备:", font=ctk.CTkFont(size=11)).grid(row=0, column=current_col, padx=(15, 5), pady=8, sticky="w")
        current_col += 1
        
        self.device_var = ctk.StringVar(value="auto")
        device_combo = ctk.CTkComboBox(
            options_frame,
            values=["auto", "cpu", "cuda"],
            variable=self.device_var,
            width=70, height=28, font=ctk.CTkFont(size=11)
        )
        device_combo.grid(row=0, column=current_col, padx=5, pady=8)
        current_col += 1
        
        # 语言
        ctk.CTkLabel(options_frame, text="语言:", font=ctk.CTkFont(size=11)).grid(row=0, column=current_col, padx=(15, 5), pady=8, sticky="w")
        current_col += 1
        
        self.language_var = ctk.StringVar(value="auto")
        language_combo = ctk.CTkComboBox(
            options_frame,
            values=["auto", "zh", "en", "ja", "ko", "es", "fr", "de"],
            variable=self.language_var,
            width=70, height=28, font=ctk.CTkFont(size=11)
        )
        language_combo.grid(row=0, column=current_col, padx=5, pady=8)
        
        # 第二行：VAD和精度
        current_col = 0
        
        # VAD
        self.vad_var = ctk.BooleanVar(value=True)
        vad_checkbox = ctk.CTkCheckBox(
            options_frame,
            text="启用VAD检测",
            variable=self.vad_var,
            font=ctk.CTkFont(size=11)
        )
        vad_checkbox.grid(row=1, column=current_col, columnspan=2, padx=10, pady=8, sticky="w")
        current_col += 2
        
        # 精度
        ctk.CTkLabel(options_frame, text="精度:", font=ctk.CTkFont(size=11)).grid(row=1, column=current_col, padx=(15, 5), pady=8, sticky="w")
        current_col += 1
        
        self.compute_var = ctk.StringVar(value="auto")
        compute_combo = ctk.CTkComboBox(
            options_frame,
            values=["auto", "float16", "float32", "int8"],
            variable=self.compute_var,
            width=80, height=28, font=ctk.CTkFont(size=11)
        )
        compute_combo.grid(row=1, column=current_col, padx=5, pady=8)
        
        # 添加工具提示
        self.add_tooltips(model_combo, device_combo, language_combo, vad_checkbox, compute_combo)
        
    def add_tooltips(self, model_combo, device_combo, language_combo, vad_checkbox, compute_combo):
        """添加工具提示"""
        model_tooltip = """模型大小选择：
• tiny: 最快，39MB，质量较低
• base: 平衡选择，74MB，推荐日常使用
• small: 244MB，质量更好
• medium: 769MB，高质量，速度较慢
• large-v3: 1550MB，最高质量，需要大内存"""
        ToolTip(model_combo, model_tooltip)
        
        device_tooltip = """处理设备：
• auto: 自动检测，推荐
• cpu: 强制CPU，稳定可靠
• cuda: 强制GPU，需要NVIDIA显卡"""
        ToolTip(device_combo, device_tooltip)
        
        language_tooltip = """语言选择：
• auto: 自动检测，推荐
• zh: 中文  • en: 英文
• ja: 日文  • ko: 韩文"""
        ToolTip(language_combo, language_tooltip)
        
        vad_tooltip = """语音活动检测：
• 启用：自动过滤静音，提高质量
• 禁用：处理整个音频"""
        ToolTip(vad_checkbox, vad_tooltip)
        
        compute_tooltip = """计算精度：
• auto: 自动选择，推荐
• int8: 内存最少，CPU推荐
• float16: GPU推荐
• float32: 质量最高，内存占用大"""
        ToolTip(compute_combo, compute_tooltip)
        
    def setup_process_area(self, parent, row):
        """处理区域"""
        process_frame = ctk.CTkFrame(parent)
        process_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        process_frame.grid_columnconfigure(2, weight=1)  # 让进度条可以扩展
        
        # 操作标题
        process_label = ctk.CTkLabel(
            process_frame, 
            text="🚀 操作控制:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        process_label.grid(row=0, column=0, columnspan=3, padx=10, pady=(8, 3), sticky="w")
        
        # 按钮和进度条
        self.process_btn = ctk.CTkButton(
            process_frame,
            text="🎯 开始转录",
            command=self.start_processing,
            height=36, width=120,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.process_btn.grid(row=1, column=0, padx=(10, 8), pady=(0, 8))
        
        self.stop_btn = ctk.CTkButton(
            process_frame,
            text="⏹️ 停止",
            command=self.stop_processing,
            height=36, width=80,
            font=ctk.CTkFont(size=12),
            state="disabled"
        )
        self.stop_btn.grid(row=1, column=1, padx=5, pady=(0, 8))
        
        # 进度条
        self.progress = ctk.CTkProgressBar(process_frame, height=20)
        self.progress.grid(row=1, column=2, padx=(8, 10), pady=(0, 8), sticky="ew")
        self.progress.set(0)
        
        # 进度信息
        self.progress_label = ctk.CTkLabel(
            process_frame,
            text="准备就绪",
            font=ctk.CTkFont(size=10)
        )
        self.progress_label.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 8))
        
    def setup_result_area(self, parent):
        """结果区域"""
        # 结果标题
        result_label = ctk.CTkLabel(
            parent, 
            text="📝 转录结果:", 
            font=ctk.CTkFont(size=12, weight="bold")
        )
        result_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # 状态显示
        self.result_status_label = ctk.CTkLabel(
            parent,
            text="等待转录...",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.result_status_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="e")
        
        # 结果文本框
        self.result_text = ctk.CTkTextbox(
            parent,
            wrap="word",
            font=ctk.CTkFont(size=12),
            corner_radius=8
        )
        self.result_text.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        # 底部信息和按钮
        bottom_frame = ctk.CTkFrame(parent)
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        bottom_frame.grid_columnconfigure(1, weight=1)
        
        # 字数统计
        self.word_count_label = ctk.CTkLabel(
            bottom_frame,
            text="字符数: 0 | 单词数: 0",
            font=ctk.CTkFont(size=9),
            text_color="gray"
        )
        self.word_count_label.grid(row=0, column=0, padx=10, pady=8, sticky="w")
        
        # 操作按钮
        btn_frame = ctk.CTkFrame(bottom_frame)
        btn_frame.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
        copy_btn = ctk.CTkButton(btn_frame, text="📋 复制", command=self.copy_result, width=80, height=30, font=ctk.CTkFont(size=11))
        copy_btn.grid(row=0, column=0, padx=3, pady=3)
        
        save_btn = ctk.CTkButton(btn_frame, text="💾 保存", command=self.save_result, width=80, height=30, font=ctk.CTkFont(size=11))
        save_btn.grid(row=0, column=1, padx=3, pady=3)
        
        clear_btn = ctk.CTkButton(btn_frame, text="🗑️ 清空", command=self.clear_result, width=80, height=30, font=ctk.CTkFont(size=11))
        clear_btn.grid(row=0, column=2, padx=3, pady=3)
        
    def setup_status_bar(self):
        """状态栏"""
        status_frame = ctk.CTkFrame(self.root, height=25)
        status_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        status_frame.grid_columnconfigure(0, weight=1)
        status_frame.grid_propagate(False)
        
        self.status_label = ctk.CTkLabel(status_frame, text="就绪", font=ctk.CTkFont(size=9))
        self.status_label.grid(row=0, column=0, padx=10, pady=3, sticky="w")
        
        # 系统信息
        device_info = self.whisper_engine.get_device_info()
        self.device_info_label = ctk.CTkLabel(status_frame, text=device_info, font=ctk.CTkFont(size=9))
        self.device_info_label.grid(row=0, column=1, padx=10, pady=3, sticky="e")
        
    def browse_file(self):
        """浏览文件"""
        file_types = [
            ("音频文件", "*.mp3 *.wav *.m4a *.flac *.aac *.ogg"),
            ("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv"),
            ("所有文件", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="选择音频或视频文件",
            filetypes=file_types
        )
        
        if filename:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)
            self.current_file = filename
            self.update_status(f"已选择文件: {os.path.basename(filename)}")
    
    def on_file_drop(self, event):
        """处理文件拖拽"""
        files = self.root.tk.splitlist(event.data)
        if files:
            file_path = files[0]
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file_path)
            self.current_file = file_path
            self.update_status(f"已拖入文件: {os.path.basename(file_path)}")
    
    def update_status(self, message):
        """更新状态栏"""
        self.status_label.configure(text=message)
        
    def update_progress(self, message, progress=None):
        """更新进度"""
        self.progress_label.configure(text=message)
        if progress is not None:
            self.progress.set(progress)
        self.root.update_idletasks()
        
    def update_result_status(self, status):
        """更新结果状态"""
        self.result_status_label.configure(text=status)
        
    def update_word_count(self, text):
        """更新字数统计"""
        # 计算字符数和单词数
        char_count = len(text.replace('\n', '').replace(' ', ''))
        word_count = len(text.split())
        
        count_text = f"字符数: {char_count} | 单词数: {word_count}"
        self.word_count_label.configure(text=count_text)
        
    def start_processing(self):
        """开始处理"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先选择音频文件")
            return
            
        if not os.path.exists(self.current_file):
            messagebox.showerror("错误", "文件不存在")
            return
        
        # 启动处理线程
        self.processing = True
        self.process_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        thread = threading.Thread(target=self.process_audio)
        thread.daemon = True
        thread.start()
    
    def stop_processing(self):
        """停止处理"""
        self.processing = False
        self.process_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.update_progress("已停止", 0)
        self.update_result_status("处理已停止")
    
    def process_audio(self):
        """处理音频"""
        try:
            # 更新结果状态
            self.update_result_status("🔄 正在加载模型...")
            
            # 加载模型
            success, message = self.whisper_engine.load_model(
                model_size=self.model_var.get(),
                device=self.device_var.get(),
                compute_type=self.compute_var.get()
            )
            
            if not success:
                self.update_result_status("❌ 模型加载失败")
                self.root.after(0, lambda: messagebox.showerror("错误", message))
                return
            
            self.update_progress("模型加载完成", 0.2)
            self.update_result_status("🎙️ 正在转录音频...")
            
            # 转录音频
            language = self.language_var.get() if self.language_var.get() != "auto" else None
            vad_filter = self.vad_var.get()
            
            success, message, result_text, info = self.whisper_engine.transcribe_audio(
                file_path=self.current_file,
                language=language,
                vad_filter=vad_filter,
                progress_callback=self.update_progress
            )
            
            if self.processing and success:
                # 显示结果
                self.root.after(0, self.display_result, result_text, info)
                self.update_progress("🎉 转录完成!", 1.0)
            elif not success:
                self.update_result_status("❌ 转录失败")
                self.root.after(0, lambda: messagebox.showerror("错误", message))
            
        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            print(f"详细错误: {e}")
            self.update_result_status("❌ 处理失败")
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
        
        finally:
            self.processing = False
            self.root.after(0, lambda: self.process_btn.configure(state="normal"))
            self.root.after(0, lambda: self.stop_btn.configure(state="disabled"))
            
    def display_result(self, text, info):
        """显示结果"""
        try:
            # 更新结果状态
            self.update_result_status("✅ 转录完成")
            
            # 清空并设置结果文本
            self.result_text.delete("1.0", tk.END)
            
            # 添加成功标题
            success_header = "🎉 转录完成！\n"
            success_header += "=" * 50 + "\n\n"
            
            # 音频信息
            duration = info.duration
            language = info.language
            language_probability = info.language_probability
            
            info_text = f"📁 文件: {os.path.basename(self.current_file)}\n"
            info_text += f"⏱️ 时长: {self.whisper_engine.format_time(duration)}\n"
            info_text += f"🌐 检测语言: {language} (置信度: {language_probability:.2f})\n"
            info_text += f"🤖 使用模型: {self.model_var.get()}\n"
            info_text += f"📅 转录时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            info_text += "=" * 50 + "\n\n"
            info_text += "📝 转录内容:\n\n"
            
            # 插入所有内容
            full_text = success_header + info_text + text
            self.result_text.insert("1.0", full_text)
            
            # 更新字数统计
            self.update_word_count(text)
            
            # 滚动到顶部
            self.result_text.see("1.0")
            
            # 自动保存结果
            success, save_message = self.whisper_engine.save_result(
                self.current_file, text, info, self.model_var.get()
            )
            
            # 更新状态
            status_msg = f"✅ 转录完成！时长: {self.whisper_engine.format_time(duration)}, 语言: {language}"
            self.update_status(status_msg)
            
            # 显示成功提示框
            self.root.after(100, lambda: messagebox.showinfo(
                "转录完成", 
                f"转录成功完成！\n\n"
                f"文件: {os.path.basename(self.current_file)}\n"
                f"时长: {self.whisper_engine.format_time(duration)}\n"
                f"语言: {language}\n"
                f"段落数: {len(self.whisper_engine.current_segments)}\n\n"
                f"{save_message}"
            ))
            
        except Exception as e:
            print(f"显示结果时出错: {e}")
            messagebox.showerror("错误", f"显示结果时出错: {str(e)}")
    
    def copy_result(self):
        """复制结果"""
        text = self.result_text.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.update_status("结果已复制到剪贴板")
    
    def save_result(self):
        """手动保存结果"""
        text = self.result_text.get("1.0", tk.END)
        if not text.strip():
            messagebox.showwarning("警告", "没有可保存的内容")
            return
        
        # 默认保存位置为音频文件同级目录
        initial_dir = "."
        initial_filename = "转录结果.txt"
        
        if self.current_file:
            initial_dir = os.path.dirname(self.current_file)
            audio_name = os.path.splitext(os.path.basename(self.current_file))[0]
            initial_filename = f"{audio_name}_转录结果.txt"
        
        filename = filedialog.asksaveasfilename(
            title="保存转录结果",
            initialdir=initial_dir,
            initialfile=initial_filename,
            defaultextension=".txt",
            filetypes=[
                ("文本文件", "*.txt"),
                ("SRT字幕", "*.srt"),
                ("所有文件", "*.*")
            ]
        )
        
        if filename:
            try:
                # 根据文件扩展名选择保存格式
                if filename.lower().endswith('.srt'):
                    # 保存为SRT格式
                    if self.whisper_engine.current_srt:
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(self.whisper_engine.current_srt)
                    else:
                        messagebox.showwarning("警告", "没有可用的SRT格式数据")
                        return
                else:
                    # 保存为文本格式
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(text)
                
                self.update_status(f"结果已保存到: {os.path.basename(filename)}")
                messagebox.showinfo("成功", "文件保存成功!")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def clear_result(self):
        """清空结果"""
        self.result_text.delete("1.0", tk.END)
        self.update_result_status("等待转录...")
        self.update_word_count("")
        self.update_status("结果已清空")
    
    def load_config(self):
        """加载配置"""
        config_file = "config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
                    
                    # 恢复界面配置
                    self.model_var.set(saved_config.get("model_size", "base"))
                    self.device_var.set(saved_config.get("device", "auto"))
                    self.compute_var.set(saved_config.get("compute_type", "auto"))
                    self.language_var.set(saved_config.get("language", "auto"))
                    self.vad_var.set(saved_config.get("vad_filter", True))
            except:
                pass
    
    def save_config(self):
        """保存配置"""
        self.config.update({
            "model_size": self.model_var.get(),
            "device": self.device_var.get(),
            "compute_type": self.compute_var.get(),
            "language": self.language_var.get(),
            "vad_filter": self.vad_var.get()
        })
        
        try:
            with open("config.json", 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def run(self):
        """运行应用"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
    
    def on_closing(self):
        """关闭应用"""
        self.save_config()
        if self.processing:
            self.stop_processing()
        self.root.destroy() 