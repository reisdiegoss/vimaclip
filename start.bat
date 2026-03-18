@echo off
chcp 65001 >nul
title VimaClip - Inicializador do Sistema

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║                VIMACLIP - INICIALIZADOR                   ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM ============================================================
REM PASSO 1: Validar Motor de Vídeo (Docker Swarm)
REM ============================================================
echo [1/4] Validando Motor de Vídeo (Porta 8000)...
powershell -Command "try { $response = Invoke-RestMethod -Uri 'http://localhost:8000/' -TimeoutSec 3; if ($response.status -eq 'online') { exit 0 } else { exit 1 } } catch { exit 1 }"
if %errorlevel% neq 0 (
    echo [X] Erro: Motor de Vídeo offline na porta 8000.
    echo     Certifique-se de que o Docker Swarm está rodando.
    pause
    exit /b 1
)
echo [✓] Motor de Vídeo está online.

REM ============================================================
REM PASSO 2: Limpar portas 8001 (Backend) e 8002 (Frontend)
REM ============================================================
echo.
echo [2/4] Verificando conflitos nas portas 8001 e 8002...

powershell -Command "Get-NetTCPConnection -LocalPort 8001, 8002 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Host \"[!] Processo encerrado na porta $($_.LocalPort)\" -ForegroundColor Yellow }"

echo [✓] Portas prontas para inicialização.

REM ============================================================
REM PASSO 3: Iniciar Backend Principal (Porta 8001)
REM ============================================================
echo.
echo [3/4] Iniciando Backend Principal...
cd main-backend
start "VimaClip Backend" /MIN cmd /c ".\venv\Scripts\activate && uvicorn main:app --host 0.0.0.0 --port 8001"

echo [*] Aguardando Backend...
:wait_backend
timeout /t 1 /nobreak >nul
netstat -ano | findstr :8001 | findstr LISTENING >nul
if %errorlevel% neq 0 (
    <nul set /p=". "
    goto :wait_backend
)
echo.
echo [✓] Backend iniciado (8001).

REM ============================================================
REM PASSO 4: Iniciar Frontend React (Porta 8002)
REM ============================================================
echo.
echo [4/4] Iniciando Frontend React...
cd ..\frontend
start "VimaClip Frontend" /MIN cmd /c "npm run dev"

echo [*] Aguardando Frontend...
:wait_frontend
timeout /t 1 /nobreak >nul
netstat -ano | findstr :8002 | findstr LISTENING >nul
if %errorlevel% neq 0 (
    <nul set /p=". "
    goto :wait_frontend
)
echo.
echo [✓] Frontend iniciado (8002).

echo.
echo ════════════════════════════════════════════════════════════
echo   VIMACLIP ESTÁ PRONTO!
echo.
echo   Frontend: http://localhost:8002
echo   Backend:  http://localhost:8001
echo   Motor:    http://localhost:8000
echo ════════════════════════════════════════════════════════════
echo.
echo Pressione qualquer tecla para encerrar os servidores e sair.
pause

REM Cleanup ao sair
powershell -Command "Get-NetTCPConnection -LocalPort 8001, 8002 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
taskkill /F /FI "WINDOWTITLE eq VimaClip Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq VimaClip Frontend*" >nul 2>&1

exit /b 0
