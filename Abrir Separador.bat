@echo off
REM ============================================================
REM  Abre a tela do Separador de Etiquetas SEM janela de terminal.
REM
REM  Como usar:
REM    - De um duplo-clique neste arquivo, OU
REM    - Clique com o botao direito > Enviar para > Area de trabalho
REM      (criar atalho), para ter um icone na area de trabalho.
REM
REM  Se a tela NAO abrir, use o "Abrir Separador (diagnostico).bat"
REM  para ver a mensagem de erro.
REM ============================================================

REM Roda sempre na pasta deste arquivo (onde estao credenciais.json etc.)
cd /d "%~dp0"

REM pythonw = Python sem a janela preta de terminal.
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "separador_gui.py"
) else (
    REM Tenta o launcher do Python (pyw) como alternativa.
    start "" pyw "separador_gui.py"
)
