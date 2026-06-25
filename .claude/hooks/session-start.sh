#!/bin/bash
# SessionStart hook: prepara o ambiente do Claude Code na web.
# Instala as dependencias (incl. pytest) para que testes rodem na sessao.
set -euo pipefail

# So roda no ambiente remoto (Claude Code na web); no PC local nao faz nada.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

# Instala dependencias de desenvolvimento (que ja incluem as de runtime).
# Idempotente: seguro rodar em toda sessao. Saida do pip vai para stderr
# para nao poluir o contexto da sessao.
python -m pip install --quiet -r requirements-dev.txt 1>&2

# Teste da GUI (Tkinter) headless: o python do projeto (3.11) nao tem tkinter,
# entao preparamos o python3.12 do sistema + xvfb + imagemagick EM SEGUNDO PLANO
# (nao atrasa a sessao). Quando estiver pronto, valida-se a tela com:
#   xvfb-run -a python3.12 tools/gui_screenshot.py out.png [Shopee]
if [ -f tools/setup_gui_tests.sh ]; then
  nohup bash tools/setup_gui_tests.sh >/tmp/setup_gui_tests.log 2>&1 &
fi

echo "Ambiente pronto: dependencias instaladas (pytest). GUI headless preparando em 2o plano."
