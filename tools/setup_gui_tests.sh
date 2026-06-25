#!/bin/bash
# setup_gui_tests.sh
# Prepara o ambiente para TESTAR A GUI (Tkinter) headless em maquinas sem display
# (ex.: Claude Code na web). Idempotente e best-effort.
#
# O python do projeto (3.11, em /usr/local) nao tem tkinter; usamos o
# python3.12 do sistema, que ganha tkinter via apt. Tambem garante:
#   - xvfb        (display virtual para rodar a janela sem monitor)
#   - imagemagick (comando `import`, para o screenshot)
#   - requests    (dependencia do nucleo) no python3.12
#
# Depois: xvfb-run -a python3.12 tools/gui_screenshot.py saida.png [Shopee]
set -uo pipefail

if ! command -v python3.12 >/dev/null 2>&1; then
  echo "python3.12 nao encontrado — nao da para testar a GUI aqui." >&2
  exit 0
fi

# Instala tkinter/xvfb/imagemagick so se faltar algo (apt e lento).
if ! python3.12 -c 'import tkinter' >/dev/null 2>&1 \
   || ! command -v xvfb-run >/dev/null 2>&1 \
   || ! command -v import >/dev/null 2>&1; then
  sudo apt-get install -y python3-tk xvfb imagemagick >&2 || \
    echo "Aviso: apt-get falhou (sem rede/permissao?)." >&2
fi

# requests para o python3.12 (o nucleo importa requests).
python3.12 -c 'import requests' >/dev/null 2>&1 || \
  python3.12 -m pip install --quiet --break-system-packages requests >&2 || \
  echo "Aviso: nao consegui instalar requests no python3.12." >&2

if python3.12 -c 'import tkinter, requests' >/dev/null 2>&1; then
  echo "GUI pronta para teste headless: xvfb-run -a python3.12 tools/gui_screenshot.py out.png [Shopee]"
else
  echo "Setup da GUI incompleto — veja os avisos acima." >&2
fi
