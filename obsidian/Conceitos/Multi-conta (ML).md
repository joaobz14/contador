---
tags: [conceito, ml, multiconta, token]
aliases: [multi-conta, definir_conta, contas]
type: concept
---

# 👥 Multi-conta (ML)

> [!abstract]
> O Mercado Livre suporta **várias contas**, cada uma com credenciais e estado
> **isolados** em `contas/{nome}/`. `definir_conta()` troca os globais.

## O que é por conta
- `credenciais.json` (+ `.bak`) → [[Token e rotação do refresh]]
- `estado_grupos.json` → [[Estado já impresso]]
- caches de itens/envios

## Shopee é diferente
A Shopee é **uma loja só** (`credenciais_shopee.json`) — sem multi-conta.

## Histórico não é trocado por conta
O `historico_impressao.json` é **único por máquina** (ML de todas as contas + Shopee) e
**não** é trocado por `definir_conta` — o resumo agrega tudo → [[Histórico e resumo do dia]].

## Relacionado
- [[Modo Ambas (ML)]] · [[Token e rotação do refresh]] · [[pegar_token (OAuth)]] · [[Estado já impresso]]
