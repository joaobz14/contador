---
tags: [conceito, historico, impressao, gui]
aliases: [resumo do dia, histórico de impressão, dia de ação]
type: concept
status: current
source_files: [historico.py, separador_gui.py, estado.py]
source_docs: [docs/ARQUITETURA.md, docs/CHANGELOG.md]
verified_at_commit: bcab879
---

# 📋 Histórico e resumo do dia

> [!abstract]
> Responde **"o que imprimi hoje"** — algo que o [[Estado já impresso]] (por dia de
> despacho) **não** guarda. Registra por **dia de ação** (carimbo de tempo, Brasília).

## De onde vem o dado
- Callback `registrar` de `estado.marcar_impresso` recebe **só o delta** (ids novos) → reimpressão **não** conta duas vezes. Ver [[historico]] e [[estado]].
- Arquivo **único por máquina** (`historico_impressao.json`, ML de todas as contas + Shopee), gitignorado, `DIAS_HISTORICO=60`.
- Gravação **best-effort** (fora da trava do estado, nunca levanta).

## Na tela: detalhado por marketplace/conta
Botão **📋 Resumo do dia** (`JanelaResumo`, só leitura — não toca estado/grupos, fica
habilitado durante a operação). A tela mostra o **detalhado** separado por Mercado
Livre (por conta) e Shopee, na **ordem da aba Nomes** — usa `resumo_do_dia(ordem=…)` +
`formatar_resumo` → [[Nomes amigáveis e ordem de separação]].

## Na impressão: PDF com a soma por produto (SKU)
O botão **Imprimir soma por produto (PDF)** gera um **PDF compacto** com a **soma por
SKU**, consolidando **todas as contas ML + Shopee** num só produto (ex.: `A01 - 2L 110 - 5`)
— é a lista de produção/separação. Também na ordem da aba Nomes. Funções
`linhas_consolidado` + `gerar_pdf` (PDF em **Python puro**, sem dependência externa).
Há ainda um botão **Detalhado (.txt)** para arquivar. Ver a [[Resumo do dia — soma por produto em PDF|decisão]].

> [!note] Reimpressão não entra no resumo (decisão de v1) — não passa por `marcar_impresso`.

## Relacionado
- [[historico]] · [[estado]] · [[Estado já impresso]] · [[Resumo do dia]] · [[Nomes amigáveis e ordem de separação]] · [[Dia de despacho]]
