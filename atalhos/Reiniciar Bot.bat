@echo off
REM ============================================================
REM  Reinicia o bot do Telegram, deixando exatamente UM rodando.
REM  De um duplo-clique aqui (nao precisa abrir o PowerShell).
REM
REM  Use isto em vez do par "schtasks /end + /run": aquele nao
REM  funcionava quando o bot ficava orfao da tarefa, e o /run
REM  acabava subindo um SEGUNDO bot por cima do primeiro (os dois
REM  brigavam pelo getUpdates e o antigo continuava respondendo).
REM  O porque completo esta em atalhos\reiniciar-bot.ps1.
REM ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0reiniciar-bot.ps1"
echo.
pause
