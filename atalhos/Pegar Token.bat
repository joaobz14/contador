@echo off
REM ============================================================
REM  Pega o token de uma conta do Mercado Livre (UMA VEZ por conta).
REM
REM  De um duplo-clique e siga as instrucoes na tela. A janela fica
REM  aberta ate o fim (mesmo se der erro), para voce ler a mensagem.
REM ============================================================

cd /d "%~dp0.."

python pegar_token.py
