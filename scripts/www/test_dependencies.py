#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试依赖项和常见问题"""

import sys
import io

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 50)
print("依赖项检查")
print("=" * 50)

# 检查Python版本
print(f"\nPython版本: {sys.version}")

# 检查tkinter
try:
    import tkinter as tk
    print("[OK] tkinter 可用")
    
    # 测试创建窗口
    root = tk.Tk()
    root.withdraw()
    root.destroy()
    print("[OK] tkinter 窗口创建成功")
except Exception as e:
    print(f"[ERROR] tkinter 错误: {e}")

# 检查requests
try:
    import requests
    print(f"[OK] requests 版本: {requests.__version__}")
except ImportError:
    print("[ERROR] requests 未安装，请运行: pip install requests")

# 检查其他模块
modules = ['json', 're', 'datetime', 'threading', 'urllib.parse', 'typing']
for module_name in modules:
    try:
        __import__(module_name)
        print(f"[OK] {module_name} 可用")
    except ImportError as e:
        print(f"[ERROR] {module_name} 导入失败: {e}")

# 检查字体
try:
    import tkinter.font as tkfont
    root = tk.Tk()
    fonts = tkfont.families()
    root.destroy()
    
    print("\n可用字体检查:")
    chinese_fonts = ['Microsoft YaHei', 'SimHei', 'Microsoft Sans Serif', 'SimSun']
    for font in chinese_fonts:
        if font in fonts:
            print(f"[OK] {font} 可用")
        else:
            print(f"[WARN] {font} 不可用")
except Exception as e:
    print(f"[ERROR] 字体检查失败: {e}")

print("\n" + "=" * 50)
print("检查完成")
print("=" * 50)

