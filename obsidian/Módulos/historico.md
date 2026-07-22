---
tags: [modulo, historico, impressao]
aliases: [historico.py, histórico de impressão]
type: modulo
arquivo: historico.py
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
- API: `resumo_do_dia` / `formatar_resumo`.

## Onde aparece
Botão **📋 Resumo do dia** na GUI (`JanelaResumo`, só leitura) → [[separador_gui]].
> [!note] Reimpressão não entra no resumo (decisão de v1) — não passa por `marcar_impresso`.

## Relacionado
- [[estado]] · [[Histórico e resumo do dia]] · [[Confirmação física antes de marcar]]
