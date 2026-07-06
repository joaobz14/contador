@echo off
REM ============================================================
REM  Atualiza o programa para a versao mais nova do GitHub.
REM  De um duplo-clique aqui (nao precisa abrir o PowerShell).
REM
REM  So funciona se a pasta tiver sido criada com "git clone".
REM  Rode em CADA PC que usa o programa (cada um tem seu clone).
REM ============================================================

REM Roda na pasta deste arquivo (a pasta do projeto).
cd /d "%~dp0"

echo Procurando atualizacoes (git pull)...
echo.
git pull
echo.

if errorlevel 1 (
    echo ------------------------------------------------------------
    echo  Algo deu errado. Possiveis causas:
    echo   - Esta pasta nao foi criada com "git clone"; ou
    echo   - Sem internet; ou
    echo   - Ha alteracoes locais nao salvas.
    echo  Veja a mensagem acima.
    echo ------------------------------------------------------------
) else (
    echo Pronto! Programa atualizado.
)

echo.
pause
