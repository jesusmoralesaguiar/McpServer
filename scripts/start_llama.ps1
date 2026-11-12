param(
    [ValidateSet("48k", "64k")]
    [string]$Context = "48k"
)

Write-Host "Arrancando llama.cpp en WSL con contexto $Context y MCP..." -ForegroundColor Cyan
wsl.exe -e bash -ic "llama-server-qwen38-$Context"
