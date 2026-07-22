---
tags: [modulo, provedor, arquitetura]
aliases: [provedores.py, abstração de provedor]
type: module
arquivo: provedores.py
---

# 🔌 provedores.py — abstração de marketplace

> [!abstract] Papel
> A GUI **nunca** faz `if marketplace`: ela fala com `self.prov`. `ProvedorML`,
> `ProvedorShopee` e `ProvedorMLAmbas` implementam a mesma interface.

## Convenção central
> [!tip] Provedor, não `if marketplace`
> Toda capacidade nova de impressão/coleta entra como **método do provedor**. A GUI
> consulta status/pendentes **via provedor** (`prov.status_grupo`), não o core direto.

## Deliberadamente **sem** `imprimir_grupo`
A interface **não** expõe um método que marque estado direto — seria uma "arma
engatilhada" para um botão que furaria a [[Confirmação física antes de marcar]].
Há teste-guardião (`test_provedores_nao_expoe_imprimir_grupo`).

## Modo Ambas
`ProvedorMLAmbas` coleta contas em sequência e **funde** grupos por SKU+qtd → [[Modo Ambas (ML)]].

## Relacionado
- [[separador_gui]] · [[Modo Ambas (ML)]] · [[Multi-conta (ML)]] · [[Confirmação física antes de marcar]]
