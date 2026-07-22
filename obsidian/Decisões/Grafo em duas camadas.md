---
tags: [decisao, grafo, graphify, manutencao]
type: decision
status: current
aliases: [Grafo em duas camadas, graph_sync, decisão do grafo, semantic.json]
source_files: [tools/graph_sync.py, tests/test_graphify_sync.py]
source_docs: [graphify-out/GRAPH_REPORT.md, CLAUDE.md]
verified_at_commit: bcab879
---

# 🧭 Decisão: grafo em duas camadas + sincronizador seguro

> [!abstract]
> **Decisão:** o `graphify-out/graph.json` é mantido em **duas camadas** — **AST**
> (regenerável do código) e **semântica** (mantida à mão, espelhada em `semantic.json`) —
> e atualizado por `tools/graph_sync.py`, nunca por `graphify hook install`. **Estado:** implementada.

## Contexto
O grafo mistura relações derivadas do código (`calls`/`imports`/estrutura) com uma camada
de "porquês" mantida à mão (nós `rationale`/`concept`, ~320 nós). O CLI `graphify` **não
roda neste ambiente**, e `graphify hook install` reconstruiria **só** o AST — **apagando**
a camada semântica curada.

## Alternativas consideradas
- **Rodar o CLI / instalar o hook:** descartado — apaga a camada semântica.
- **Editar o `graph.json` à mão para tudo:** era o que se fazia; **não escala** e a camada
  AST ficou 125 commits atrás (405 números de linha errados).
- **Regenerar `calls` inteiro do AST:** medido como ruidoso (colisões de atributo tipo
  `.get()`); descartado. O sync **reconcilia** `calls` (preserva sobreviventes).

## Motivo
Preservar 100% da camada semântica **e** manter a estrutural em dia, de forma reprodutível
e testável, sem depender do CLI.

## Consequências
- `tools/graph_sync.py`: `--check` (defasagem; roda no CI via `tests/test_graphify_sync.py`)
  → `--update` (re-deriva AST, preserva semântica por **IDs estáveis**, re-emite
  `semantic.json` + `manifest.json`, grava atômico) → `--validate`.
- Conhecimento novo (rationale/concept) entra **à mão** no `graph.json` e um `--update` canoniza.
- **`graph.html` fica defasado** — só o CLI o regenera; não editar à mão → [[Fontes de verdade]].

## Relacionado
- [[Fontes de verdade]] · [[Testes como documentação]] · [[GitHub Actions (CI)]]
