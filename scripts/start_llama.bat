@echo off
set CONTEXT=%1
if "%CONTEXT%"=="" set CONTEXT=48k
echo Arrancando llama.cpp en WSL con contexto %CONTEXT%...
wsl.exe -e bash -ic "llama-server-qwen38-%CONTEXT%"
