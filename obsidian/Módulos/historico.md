---
tags: [modulo, historico, impressao]
aliases: [historico.py, histórico de impressão]
type: module
status: current
arquivo: historico.py
source_files: [historico.py]
source_docs: [tests/test_historico.py]
verified_at_commit: bcab879
---

# 🕒 historico.py — registro por dia de ação

> [!abstract] Papel
> Log **separado** do estado: guarda **quando** cada etiqueta saiu (carimbo de tempo,
> Brasília). Responde "o que imprimi hoje" — que o [[Estado já impresso]] **não** responde.

## Por que existe
O estado é por **dia de despacho** e não guarda o momento da impressão. O histórico é
por **dia de ação** (impressão), gravado no momento da marcação confirmada.

## Como funciona
- Hook único: o callback **`registrar`** de `estado.marcar_impresso` recebe **só o delta** → sem contagem dobrada (reimpressão não gera evento).
- Cobre GUI, bot e CLI de uma vez (wrappers do núcleo e do Shopee passam o callback).
- Gravação **best-effort**: fora da trava do estado, arquivo/trava próprios, **nunca levanta**.
- Arquivo **único por máquina** (`historico_impressao.json`), gitignorado, podado (`DIAS_HISTORICO=60`).
- API: `resumo_do_dia(ordem=…)` (agrega por marketplace/conta + consolida por SKU, na ordem da aba Nomes) · `formatar_resumo` (texto detalhado da tela) · `linhas_consolidado` + `gerar_pdf` (o **PDF da soma por produto**, em Python puro).

## Onde aparece
Botão **📋 Resumo do dia** na GUI (`JanelaResumo`, só leitura) → [[separador_gui]]: tela
**detalhada** por marketplace/conta e botão **Imprimir soma por produto (PDF)** →
[[Resumo do dia]].
> [!note] Reimpressão não entra no resumo (decisão de v1) — não passa por `marcar_impresso`.

## Relacionado
- [[estado]] · [[Histórico e resumo do dia]] · [[Confirmação física antes de marcar]]
