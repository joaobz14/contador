---
tags: [runbook, ci, testes, validacao]
type: runbook
status: current
aliases: [Validar o repositório, rodar testes, validar vault, validar grafo]
source_files: [tools/validar_obsidian.py, tools/graph_sync.py]
source_docs: [.github/workflows/testes.yml]
verified_at_commit: bcab879
---

# 🛠️ Runbook: validar o repositório (testes, grafo, vault)

> [!abstract]
> A sequência de checagens antes de abrir um PR. Todas são **seguras** (não tocam
> credenciais, estado ou dados de execução) e rodam sem rede.

## Testes e lint
```bash
pytest -q                                   # py3.11 (sem tkinter)
xvfb-run -a python3.12 -m pytest -q         # inclui a GUI (tkinter no 3.12)
ruff check .                                # regras F + E9
```
Mapa teste → regra: [[Testes como documentação]].

## Grafo (Graphify)
```bash
python tools/graph_sync.py --check          # detecta defasagem (exit != 0 se houver)
python tools/graph_sync.py --update         # SÓ se mudou código/estrutura relevante
python tools/graph_sync.py --validate       # integridade (0 arestas órfãs)
pytest tests/test_graphify_sync.py -q
```
> [!warning] Nunca `graphify hook install` (apagaria a camada semântica) → [[Grafo em duas camadas]].

## Cofre Obsidian
```bash
python tools/validar_obsidian.py            # links, frontmatter, vazios, colisões, segredos
pytest tests/test_validar_obsidian.py -q
```
O validador falha (exit != 0) em **erro real** de arquivo rastreado; ignora artefatos locais
do Obsidian (workspace/cache).

## Higiene final
```bash
git diff --check                            # espaços/conflitos
git status --short                          # nada inesperado rastreado
```

## Critério de sucesso
Tudo verde, `graph_sync --check` sem defasagem, validador do vault sem erros, `git status`
limpo (só o que você pretende commitar).

## Relacionado
- [[Testes como documentação]] · [[Grafo em duas camadas]] · [[GitHub Actions (CI)]] · [[Comece aqui]]
