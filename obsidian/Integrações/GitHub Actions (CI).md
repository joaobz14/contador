---
tags: [integracao, ci, github, testes]
type: integration
status: current
aliases: [GitHub Actions, CI, workflow de testes]
source_files: [.github/workflows/testes.yml, tools/gui_screenshot.py]
source_docs: []
verified_at_commit: bcab879
---

# ⚙️ Integração: GitHub Actions (CI)

> [!abstract]
> A cada Pull Request e push no `main`, o CI roda os testes, o lint e um smoke da GUI. Falha
> real bloqueia o merge. Workflow: `.github/workflows/testes.yml`.

## Jobs
- **`lint`** — `ruff check .` (regras `F` + `E9`).
- **`pytest`** — em **Python 3.11 e 3.12** (o 3.12 tem tkinter → cobre a GUI).
- **`gui-smoke`** — abre a tela headless com `xvfb` nos dois marketplaces
  (`tools/gui_screenshot.py`) e publica os PNGs; pega quebra de import que o pytest não vê.
- **`obsidian`** — roda `tools/validar_obsidian.py` e `tests/test_validar_obsidian.py`
  (validação do cofre; job leve, sem instalar o app inteiro).

## Princípio
O CI **não** falha por arquivos locais corretamente não versionados (workspace/cache do
Obsidian, estado, credenciais) — só por problemas reais em arquivos rastreados.

## Relacionado
- [[Testes como documentação]] · [[Validar o repositório]] · [[Grafo em duas camadas]]
