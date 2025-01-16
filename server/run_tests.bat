@echo off
set PYTHONPATH=%PYTHONPATH%;%~dp0
python -m pytest %* 