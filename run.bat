@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ====================================
echo 怪物猎人崛起智能狩猎助手
echo ====================================
echo.
echo 正在启动程序...
echo.

.venv\Scripts\python.exe main.py

if errorlevel 1 (
    echo.
    echo 程序运行出错！
    echo 请确保已安装所有依赖: pip install -r requirements.txt
    pause
)
