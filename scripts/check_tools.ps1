Write-Host "Consultando GET http://127.0.0.1:8080/tools..." -ForegroundColor Cyan
wsl.exe -e bash -ic "curl -s http://127.0.0.1:8080/tools | python3 -m json.tool"
