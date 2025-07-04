#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Controller模块 - 包含GUI控制器和Whisper引擎
"""

from .gui_controller import WhisperGUI
from .whisper_engine import WhisperEngine

__all__ = ['WhisperGUI', 'WhisperEngine'] 