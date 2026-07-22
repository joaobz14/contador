---
tags: [modulo, shopee, impressao]
aliases: [shopee_api.py, integração Shopee]
type: module
arquivo: shopee_api.py
---

# 🛍️ shopee_api.py — integração Shopee (API v2)

> [!abstract] Papel
> Listar pedidos, **organizar envio**, obter **AWB**, gerar/baixar a **etiqueta** e
> gerir o estado da Shopee. Reusa a camada de [[estado]] e o `nome_saida_unico` do núcleo.

## O caminho da etiqueta
Listar `READY_TO_SHIP` → agrupar → **organizar envio (drop-off)** → **AWB** →
`create_shipping_document` (exige o AWB) → aguardar `READY` → baixar → ZIP.
Detalhe completo em [[Shopee — organizar envio e AWB]].

## Pegadinhas embutidas (validadas com loja real)
- `_levantar_se_erro` (nunca `raise_for_status`) e `_rede_limpa` para **não vazar o token** → [[Redação de segredos]].
- `envio_ja_arranjado` antes de recusar organizar (`info_needed={}` não é "sem drop-off").
- `_organizar_varios` em camadas: AWB existente → `batch_ship_order` → confirmação **pelo AWB** → fallback individual.
- `_gerar_lote` **paralelo por pedido** (a Shopee processa requests concorrentes em paralelo) → [[Desempenho]].

## Conferência do operador
Sem nome na etiqueta → a tela lista o **AWB** de cada etiqueta (`_somar_rastreios`,
`_cachear_awbs` → `awb_cache_shopee.json`) → [[Conferência na Shopee (rastreio)]].

## Relacionado
- [[Shopee — organizar envio e AWB]] · [[Conferência na Shopee (rastreio)]] · [[estado]] · [[Desempenho]]
