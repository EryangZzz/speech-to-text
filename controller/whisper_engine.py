#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Whisper引擎 - 语音转文字核心业务逻辑
"""

import os
import time
from datetime import datetime
from pathlib import Path
from faster_whisper import WhisperModel
import torch


class WhisperEngine:
    """Whisper语音转文字引擎"""
    
    def __init__(self):
        self.model = None
        self.current_segments = []
        self.current_srt = ""
        
    def load_model(self, model_size="base", device="auto", compute_type="auto"):
        """加载Whisper模型"""
        try:
            # 自动选择设备
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # 自动选择计算类型
            if compute_type == "auto":
                if device == "cuda":
                    compute_type = "float16"
                else:
                    compute_type = "int8"
            
            # 加载模型
            self.model = WhisperModel(
                model_size, 
                device=device, 
                compute_type=compute_type
            )
            
            return True, f"模型加载成功: {model_size} ({device}, {compute_type})"
            
        except Exception as e:
            return False, f"加载模型失败: {str(e)}"
    
    def transcribe_audio(self, file_path, language=None, vad_filter=True, beam_size=5, progress_callback=None):
        """转录音频文件"""
        try:
            if not self.model:
                return False, "模型未加载", None, None
            
            if not os.path.exists(file_path):
                return False, "文件不存在", None, None
            
            # 转录音频
            if progress_callback:
                progress_callback("开始转录音频...", 0.3)
            
            segments, info = self.model.transcribe(
                file_path,
                beam_size=beam_size,
                language=language,
                vad_filter=vad_filter,
                temperature=0.0
            )
            
            # 处理结果
            if progress_callback:
                progress_callback("正在处理转录结果...", 0.5)
            
            # 收集所有段落
            segments_list = list(segments)
            total_segments = len(segments_list)
            
            if total_segments == 0:
                return False, "未检测到有效的语音内容", None, None
            
            result_text = ""
            srt_content = ""
            
            for i, segment in enumerate(segments_list):
                # 文本格式
                result_text += f"[{self.format_time(segment.start)} -> {self.format_time(segment.end)}]\n"
                result_text += f"{segment.text.strip()}\n\n"
                
                # SRT格式
                srt_content += f"{i+1}\n"
                srt_content += f"{self.format_time_srt(segment.start)} --> {self.format_time_srt(segment.end)}\n"
                srt_content += f"{segment.text.strip()}\n\n"
                
                # 更新进度
                if progress_callback:
                    progress = 0.5 + (i / total_segments) * 0.4
                    progress_callback(f"处理进度: {i+1}/{total_segments}", progress)
            
            # 保存segments数据
            self.current_segments = segments_list
            self.current_srt = srt_content
            
            return True, "转录完成", result_text, info
            
        except Exception as e:
            return False, f"转录失败: {str(e)}", None, None
    
    def format_time(self, seconds):
        """格式化时间 (HH:MM:SS)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def format_time_srt(self, seconds):
        """格式化SRT时间 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def save_result(self, file_path, result_text, info, model_size="base"):
        """保存转录结果到文件"""
        try:
            # 使用标准的os.path处理，避免pathlib在打包后的问题
            audio_dir = os.path.dirname(file_path)
            audio_basename = os.path.basename(file_path)
            audio_name = os.path.splitext(audio_basename)[0]
            
            # 创建结果文件路径
            result_file = os.path.join(audio_dir, f"{audio_name}_转录结果.txt")
            
            # 准备完整的结果内容
            full_content = f"# {audio_name} 转录结果\n\n"
            full_content += f"文件: {audio_basename}\n"
            full_content += f"时长: {self.format_time(info.duration)}\n"
            full_content += f"语言: {info.language} (置信度: {info.language_probability:.2f})\n"
            full_content += f"转录时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            full_content += f"模型: {model_size}\n\n"
            full_content += "=" * 50 + "\n\n"
            full_content += result_text
            
            # 保存文本文件
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            # 保存SRT文件
            if self.current_srt:
                srt_file = os.path.join(audio_dir, f"{audio_name}.srt")
                with open(srt_file, 'w', encoding='utf-8') as f:
                    f.write(self.current_srt)
                return True, f"结果已保存: {os.path.basename(result_file)} 和 {audio_name}.srt"
            else:
                return True, f"结果已保存: {os.path.basename(result_file)}"
            
        except Exception as e:
            return False, f"保存失败: {str(e)}"
    
    def get_device_info(self):
        """获取设备信息"""
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            try:
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory // (1024**3)
                return f"GPU: {gpu_name} ({gpu_memory}GB)"
            except:
                return "GPU: 可用"
        else:
            return "设备: CPU" 