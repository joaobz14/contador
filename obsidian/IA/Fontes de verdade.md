---
tags: [ia, fontes, hub]
type: hub
status: current
aliases: [Fontes de verdade, prioridade de fontes, o que confiar]
source_docs: [CLAUDE.md, AGENTS.md, docs/ARQUITETURA.md, graphify-out/GRAPH_REPORT.md]
---

# 🎯 Fontes de verdade

> [!abstract]
> Quando duas fontes discordarem, use esta prioridade. Nenhuma nota deste cofre é a
> fonte absoluta do comportamento — o **código** é.

## Ordem de prioridade
1. **Código e testes** — comportamento atual (o que o sistema **faz de fato**).
2. **`docs/ARQUITETURA.md`** — invariantes e regras arquiteturais.
3. **`AGENTS.md` / `CLAUDE.md`** — fluxo de trabalho dos agentes (são espelhos).
4. **Graphify (`graphify-out/`)** — relações estruturais e semânticas.
5. **`docs/CHANGELOG.md`** — fatos históricos.
6. **`docs/PRIORIDADES_TECNICAS.md`** — possíveis pendências, **só depois de confirmar
   no código** que ainda não foram feitas.

Achou divergência? Verifique no código/testes, **atualize a nota** para o estado real,
registre a fonte em `source_files`/`source_docs`, e **não** mude comportamento só para
casar com a nota. Se ficar incerto, marque `status: needs-verification` — não invente.

## Quando confiar no código
Sempre que a pergunta for "o que acontece de fato": números (`DIAS_JANELA`, `max_workers`,
`DIAS_HISTORICO`), fluxo exato, semântica de cache, condições de corrida. O grafo e as
notas **orientam** (onde olhar e por quê); só o código **decide**.

## Quando consultar ARQUITETURA.md
Antes de mexer em **estado, token ou impressão**. Ele tem as **12 invariantes críticas**
e as áreas de risco. As notas [[Invariantes críticas]] e os conceitos deste cofre são a
camada navegável dessas regras — a fonte é o `.md`.

## Quando consultar o Graphify
Perguntas de **arquitetura/relação** ("quem chama X?", "o que quebra se eu mexer em Y?").
Consulte `graphify-out/` **antes** de reler arquivos crus.

## Como interpretar o `semantic.json`
`graphify-out/semantic.json` é o **extrato durável da camada semântica** do grafo
(nós `rationale`/`concept` e arestas manuais — os "porquês" mantidos à mão). É a parte do
grafo em que se pode confiar mesmo entre rebuilds, porque `tools/graph_sync.py` a
**preserva por IDs estáveis**. A camada **AST** (arestas `calls`/`imports`) é re-derivada
do código pelo `graph_sync`.

## Sobre o `graph.html`
> [!warning]
> `graphify-out/graph.html` é a visualização *baked* do último build do **CLI** `graphify`
> e **pode não acompanhar** as atualizações feitas por `tools/graph_sync.py`. Não o trate
> como atual e não o edite à mão. Só um rebuild do CLI o regenera.

## Sobre o backlog
`docs/PRIORIDADES_TECNICAS.md` lista sugestões — **algumas já implementadas** (ex.: a
"camada comum de estado" é o `estado.py`; os "logs operacionais" são o `separador.log`).
Confirme no código antes de tratar qualquer item como pendente. Ver [[Estado atual]].

## O Obsidian não é fonte absoluta
Este cofre é **contexto humano** (decisões, conceitos, incidentes, runbooks). Útil para
entender **por que** e **como operar**, mas o comportamento verdadeiro está no código.

## Relacionado
- [[Comece aqui]] · [[Estado atual]] · [[Invariantes críticas]] · [[Grafo em duas camadas]]
