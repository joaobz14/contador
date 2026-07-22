---
tags: [ia, onboarding, hub]
type: hub
status: current
aliases: [Comece aqui, IA Comece aqui, onboarding de agente]
source_docs: [CLAUDE.md, AGENTS.md, docs/ARQUITETURA.md]
---

# 🤖 Comece aqui (agentes de IA)

> [!abstract]
> Onboarding rápido para um agente que vai investigar, manter ou modificar este
> projeto. Leia isto, depois [[Fontes de verdade]] e [[Estado atual]].

## O que é o sistema
Ferramenta de mesa (Windows, Python) que separa e imprime **etiquetas de envio** do
**Mercado Livre** e da **Shopee** numa **impressora Zebra** (ZPL). Agrupa pedidos por
**produto + quantidade**, gera ZPL e entrega um `.zip` na pasta **Downloads**, que um
app externo da Zebra imprime. Visão geral: [[🏠 Home]].

## Como investigar uma tarefa (ordem recomendada)
1. **Comportamento/desempenho** ("por que está lento", "o que este código faz"): leia a
   **fonte** (código + testes). O grafo orienta, mas número e fluxo exato só o código tem.
2. **Arquitetura/relação** ("quem chama X?", "o que quebra se eu mexer em Y?"): consulte
   **`graphify-out/`** e `docs/ARQUITETURA.md` **antes** de reler arquivos crus.
3. **Contexto/decisão/incidente/procedimento**: este cofre (`obsidian/`).
4. Detalhes da priorização das fontes: [[Fontes de verdade]].

## Quais arquivos ler primeiro
- `CLAUDE.md` / `AGENTS.md` — convenções e fluxo de trabalho (espelhos entre si).
- `docs/ARQUITETURA.md` — **12 invariantes críticas** + áreas de risco (leitura
  obrigatória antes de mexer em estado/token/impressão).
- `graphify-out/GRAPH_REPORT.md` e `graphify-out/semantic.json` — relações + "porquês".
- Aqui: [[Invariantes críticas]], [[Estado atual]], [[Mapa de tarefas]].

## Onde ficam as invariantes
`docs/ARQUITETURA.md` (fonte) e o resumo navegável em [[Invariantes críticas]] (12 regras
que, se quebradas, levam a **imprimir errado, imprimir em dobro ou travar uma conta**).

## Como descobrir o estado atual
[[Estado atual]] separa **implementado / parcial / pendente / pesquisa / limitação /
dívida técnica**, cada afirmação ligada a arquivos e testes. **Não** confie no backlog
(`docs/PRIORIDADES_TECNICAS.md`) sem confirmar no código — vários itens já foram feitos.

## Como validar mudanças
```bash
pytest -q                                   # sem rede; py3.11
xvfb-run -a python3.12 -m pytest -q         # inclui GUI (tkinter no 3.12)
ruff check .
python tools/graph_sync.py --check          # grafo em dia
python tools/validar_obsidian.py            # este cofre
```
Mapa teste → regra: [[Testes como documentação]]. Procedimento completo: [[Validar o repositório]].

## Áreas sensíveis (mexa com cuidado)
- **`estado.marcar_impresso`** — merge + [[Trava entre processos]]; `ler_estado`, nunca `ler_json`.
- **`obter_token`** — nunca `renovar_token` direto (o refresh **rotaciona**) → [[Token e rotação do refresh]].
- **Shopee AWB** — etiqueta só existe após organizar o envio → [[Shopee — organizar envio e AWB]].
- **Prefixo do `.zip` na Downloads** — mudá-lo quebra a Zebra → [[Ponte com a Zebra]].
- **Ordem "gera → confirma → marca"** — furá-la é a invariante 1 → [[Confirmação física antes de marcar]].

## Como evitar quebrar comportamento crítico
- Toda capacidade de impressão/coleta entra como **método do provedor**, não `if marketplace`.
- **Não** altere regra de negócio só para casar com uma nota — corrija a nota.
- Ao terminar, atualize o que se aplicar (CHANGELOG, ARQUITETURA, grafo via `graph_sync`,
  este cofre) e rode os validadores. Detalhe: [[Fontes de verdade]].

## Relacionado
- [[Fontes de verdade]] · [[Estado atual]] · [[Mapa de tarefas]] · [[🏠 Home]] · [[Invariantes críticas]]
