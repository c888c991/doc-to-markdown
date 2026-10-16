@echo off
title 文档转 Markdown
cd /d "%~dp0"
".venv\Scripts\python.exe" "转Markdown.py" %*
echo.
if not errorlevel 1 start "" "转换结果"
echo 按任意键关闭窗口……
pause >nul
