---
tags: [funcionalidade, historico, gui]
type: feature
status: current
aliases: [Resumo do dia, funcionalidade resumo, soma por produto]
source_files: [historico.py, separador_gui.py]
source_docs: [tests/test_historico.py, docs/CHANGELOG.md]
verified_at_commit: bcab879
---

# 📋 Resumo do dia (funcionalidade)

> [!abstract]
> O que o **operador** vê: um botão **📋 Resumo do dia** na tela que mostra o que saiu da
> impressora **hoje** e permite imprimir a **soma por produto** para separar/produzir.

## Comportamento observável
- Botão **📋 Resumo do dia** abre uma janela (`JanelaResumo`, só leitura — não interfere na
  operação em andamento).
- **Na tela:** detalhado por **Mercado Livre (por conta)** e **Shopee**, na **ordem da aba
  Nomes**, com totais de etiquetas e unidades.
- **Botão "Imprimir soma por produto (PDF)":** gera um **PDF compacto** com a soma de cada
  SKU somando **todas as contas ML + Shopee** (ex.: `A01 - 2L 110 - 5`) — a lista de
  produção/separação. Abre no visualizador para imprimir.
- **Botão "Detalhado (.txt)":** salva o detalhado da tela para arquivar.

## Como funciona por baixo
Registro por **dia de ação** (carimbo de tempo) gravado no momento da marcação confirmada,
via callback `registrar` de `estado.marcar_impresso` (só o **delta** de ids novos). Cobre
GUI, bot e CLI. Detalhe: [[Histórico e resumo do dia]] · [[historico]].

## Limitações
- **Reimpressão manual não aparece** (não passa por `marcar_impresso`) — decisão de v1.
- O PDF é a **soma consolidada**; a separação por marketplace fica só na tela.
- Histórico é **por máquina** (`historico_impressao.json`, gitignorado) — não sincroniza entre PCs.

## Fontes no código e testes
`historico.py` (`resumo_do_dia`, `formatar_resumo`, `linhas_consolidado`, `gerar_pdf`);
`separador_gui.py` (`JanelaResumo`, `abrir_resumo_dia`); `tests/test_historico.py`.

## Relacionado
- [[Histórico e resumo do dia]] · [[historico]] · [[Resumo do dia — soma por produto em PDF]] · [[Nomes amigáveis e ordem de separação]]
