@echo off
REM ============================================================
REM  Gera e baixa a etiqueta de um pedido da Shopee.
REM
REM  Duplo-clique: ele lista os pedidos prontos de HOJE, voce
REM  digita o numero do pedido (order_sn) e ele gera a etiqueta
REM  na pasta Downloads (o app da Zebra imprime sozinho).
REM
REM  IMPORTANTE: o envio precisa estar ORGANIZADO na Shopee
REM  (botao "Organizar Envio"); so depois disso a etiqueta existe.
REM
REM  A janela fica aberta ate o fim (mesmo com erro) para ler.
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo   ETIQUETA SHOPEE
echo ============================================================
echo.
echo Pedidos prontos para enviar HOJE:
echo.
python shopee_api.py
echo.
echo ------------------------------------------------------------
set /p SN="Numero do pedido (order_sn) e Enter (ou so Enter p/ sair): "
if "%SN%"=="" goto fim

echo.
python shopee_api.py etiqueta %SN%

:fim
echo.
pause
