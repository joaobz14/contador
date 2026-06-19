@echo off
REM ============================================================
REM  Inicia o bot do Telegram (consulta de pedidos pelo celular).
REM
REM  De um duplo-clique para ligar o bot. DEIXE esta janela ABERTA:
REM  o bot so responde enquanto ela estiver rodando. Para parar,
REM  feche a janela (ou Ctrl+C).
REM
REM  Precisa do bot_config.json (com o token) e do credenciais.json
REM  na mesma pasta.
REM ============================================================

cd /d "%~dp0"

echo Iniciando o bot do Telegram...
echo (Mantenha esta janela aberta. Feche-a para parar o bot.)
echo.

python bot_telegram.py

echo.
echo ------------------------------------------------------------
echo  O bot parou. Se foi por erro, a mensagem aparece acima.
echo ------------------------------------------------------------
pause
