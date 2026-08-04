@echo off
REM ============================================================
REM  Atualiza o programa para a versao mais nova do GitHub
REM  E REINICIA O BOT, se ele estiver registrado no Agendador.
REM  De um duplo-clique aqui (nao precisa abrir o PowerShell).
REM
REM  POR QUE REINICIAR: o `git pull` troca os ARQUIVOS, mas o bot
REM  que ja esta rodando continua com o codigo que carregou no
REM  logon -- ele so pega a versao nova quando o processo reinicia.
REM  Sem isto, uma atualizacao "nao pega" e nao ha nenhum sinal do
REM  porque (aconteceu duas vezes: /vendasapos e o layout do
REM  resumo de vendas).
REM
REM  So funciona se a pasta tiver sido criada com "git clone".
REM  Rode em CADA PC que usa o programa (cada um tem seu clone).
REM ============================================================

setlocal
set "TAREFA=Contador - Bot do Telegram (login)"

REM Roda na pasta deste arquivo (a pasta do projeto).
cd /d "%~dp0"

REM Guarda o commit atual para saber, depois, se algo mudou de verdade.
set "ANTES="
for /f "delims=" %%i in ('git rev-parse HEAD 2^>nul') do set "ANTES=%%i"

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
    echo.
    pause
    exit /b 1
)

set "DEPOIS="
for /f "delims=" %%i in ('git rev-parse HEAD 2^>nul') do set "DEPOIS=%%i"

if "%ANTES%"=="%DEPOIS%" (
    echo Ja estava na versao mais nova. Nada a reiniciar.
    echo.
    pause
    exit /b 0
)

echo Programa atualizado.
echo.

REM O bot so existe como tarefa agendada se voce rodou uma vez o
REM atalhos\registrar-tarefa-bot.ps1. Sem ela, nao ha o que reiniciar.
schtasks /query /tn "%TAREFA%" >nul 2>&1
if errorlevel 1 (
    echo ------------------------------------------------------------
    echo  ATENCAO: o bot NAO esta registrado no Agendador de Tarefas.
    echo  Se ele estiver rodando, ainda esta com a versao ANTIGA --
    echo  feche e abra de novo para pegar a atualizacao.
    echo.
    echo  Para ele passar a subir sozinho no logon (e a reiniciar
    echo  aqui), rode UMA vez, no PowerShell:
    echo    powershell -NoProfile -ExecutionPolicy Bypass -File atalhos\registrar-tarefa-bot.ps1
    echo ------------------------------------------------------------
    echo.
    pause
    exit /b 0
)

echo Reiniciando o bot para ele pegar a versao nova...
REM NAO usar "schtasks /end + /run" aqui: quando o bot fica orfao da tarefa,
REM o /end nao tem o que matar e o /run sobe um SEGUNDO bot por cima do
REM primeiro -- os dois brigam pelo getUpdates e o ANTIGO continua
REM respondendo ("reiniciei e a versao nao mudou", achado 2026-08-04). O
REM script abaixo identifica e derruba o que estiver de pe antes de subir um so.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0atalhos\reiniciar-bot.ps1"
if errorlevel 1 (
    echo  Nao consegui reiniciar o bot automaticamente. Veja a mensagem acima.
) else (
    echo Bot reiniciado. Mande /versao no Telegram para confirmar.
)

echo.
echo LEMBRETE: se a TELA do separador estiver aberta, feche e abra de
echo novo -- ela tambem carrega o codigo na abertura.
echo.
pause
