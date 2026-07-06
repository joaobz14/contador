@echo off
chcp 65001 >nul
REM ============================================================
REM  Inicia o bot do Telegram com REINICIO AUTOMATICO.
REM
REM  Se o bot cair (erro, queda de rede, etc.), esta janela espera
REM  alguns segundos e o liga de novo sozinho. Use este lancador no
REM  PC do escritorio para o bot nao ficar fora do ar sem ninguem ver.
REM
REM  DEIXE esta janela ABERTA. Para PARAR de vez:
REM    - feche a janela; ou
REM    - pressione Ctrl+C e responda "S" (Sim) ao "Terminar tarefa?".
REM
REM  Para iniciar junto com o Windows, veja o README ("Ligar junto
REM  com o Windows"): crie um atalho deste arquivo na pasta shell:startup.
REM
REM  Precisa do bot_config.json (token) e das contas configuradas.
REM ============================================================

cd /d "%~dp0.."

REM Modo automatico: o bot nao pausa pedindo Enter; quem reinicia e este .bat.
set BOT_SEM_PAUSA=1

echo Bot do Telegram com reinicio automatico.
echo (Mantenha esta janela aberta. Feche-a para parar o bot.)
echo.

:loop
python bot_telegram.py
echo.
echo ------------------------------------------------------------
echo  [%date% %time%] O bot parou (codigo %errorlevel%).
echo  Reiniciando em 15 segundos... (feche a janela para parar)
echo  O motivo do erro tambem fica registrado em bot.log
echo ------------------------------------------------------------
timeout /t 15 /nobreak >nul
goto loop
