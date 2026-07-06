@echo off
REM ============================================================
REM  Igual ao "Abrir Separador.bat", mas MANTEM a janela de
REM  terminal aberta para mostrar erros.
REM
REM  Use este quando a tela nao abrir e voce quiser ver o motivo.
REM ============================================================

cd /d "%~dp0.."

echo Abrindo o Separador de Etiquetas...
echo (Esta janela mostra mensagens de erro. Pode fechar depois.)
echo.

python "separador_gui.py"

echo.
echo Programa encerrado. Pressione uma tecla para fechar.
pause >nul
