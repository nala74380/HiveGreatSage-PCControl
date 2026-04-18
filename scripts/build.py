#!/usr/bin/env python3
# 打包脚本
import subprocess
subprocess.run(["pyinstaller", "main.py", "--name=ControlApp", "--onefile"])
