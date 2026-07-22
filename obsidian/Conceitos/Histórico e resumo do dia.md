---
tags: [conceito, historico, impressao, gui]
aliases: [resumo do dia, histórico de impressão, dia de ação]
type: conceito
---

# 📋 Histórico e resumo do dia

> [!abstract]
> Responde **"o que imprimi hoje"** — algo que o [[Estado já impresso]] (por dia de
> despacho) **não** guarda. Registra por **dia de ação** (carimbo de tempo, Brasília).

## De onde vem o dado
- Callback `registrar` de `estado.marcar_impresso` recebe **só o delta** (ids novos) → reimpressão **não** conta duas vezes. Ver [[historico]] e [[estado]].
- Arquivo **único por máquina** (`historico_impressao.json`, ML+Shopee), gitignorado, `DIAS_HISTORICO=60`.
- Gravação **best-effort** (fora da trava do estado, nunca levanta).

## Na tela
Botão **📋 Resumo do dia** (`JanelaResumo`, só leitura — não toca estado/grupos, fica
habilitado durante a operação). "Salvar para imprimir" gera um `.txt`. Usa
`resumo_do_dia` + `formatar_resumo`.

> [!note] Reimpressão não entra no resumo (decisão de v1) — não passa por `marcar_impresso`.

## Relacionado
- [[historico]] · [[estado]] · [[Estado já impresso]] · [[Fuso de Brasília]] · [[Dia de despacho]]
