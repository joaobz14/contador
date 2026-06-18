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

echo "Ambiente pronto: dependencias instaladas (pytest disponivel)."
