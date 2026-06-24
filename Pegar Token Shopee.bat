@echo off
REM ============================================================
REM  Autoriza uma loja Shopee e gera o credenciais_shopee.json.
REM  Duplo-clique e siga as instrucoes. A janela fica aberta ate
REM  o fim (mesmo com erro) para voce ler a mensagem.
REM ============================================================

cd /d "%~dp0"

python pegar_token_shopee.py
