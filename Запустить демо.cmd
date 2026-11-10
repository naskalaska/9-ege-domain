@echo off
cd /d "%~dp0"
"C:\Users\anast\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" maintenance\serve-speech-demo.py --open-browser
pause
