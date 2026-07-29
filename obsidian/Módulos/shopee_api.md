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

## Alerta pós-horário do bot
`pedidos_prontos_novos(cred, token, avisados, hoje)` é o par Shopee de
`filtrar_para_imprimir`+`extrair_itens` do núcleo: pedidos `READY_TO_SHIP` com
despacho **hoje** (`ship_by_date`) ainda não avisados (dedup por `order_sn`).
Reusa `_itens_de_detalhes` (extraído de dentro de `grupos_de_detalhes` — mesma
extração de SKU/quantidade, sem duplicar). Consumido por
`bot_telegram._dados_alerta_shopee` → [[bot_telegram]].

## Pegadinhas embutidas (validadas com loja real)
- `_levantar_se_erro` (nunca `raise_for_status`) e `_rede_limpa` para **não vazar o token** → [[Redação de segredos]].
- `envio_ja_arranjado` antes de recusar organizar (`info_needed={}` não é "sem drop-off").
- `_organizar_varios` em camadas: AWB existente → `_filtrar_ja_arranjados` → `batch_ship_order` → confirmação **pelo AWB**; quem sobra sem AWB depois do batch **não** cai no individual (vira pendência de confirmação) → [[Shopee — organizar envio e AWB]] (compliance da Shopee, achado 2026-07, 2 rodadas).
- `_gerar_lote` **paralelo por pedido** (a Shopee processa requests concorrentes em paralelo) → [[Desempenho]].

## Conferência do operador
Sem nome na etiqueta → a tela lista o **AWB** de cada etiqueta (`_somar_rastreios`,
`_cachear_awbs` → `awb_cache_shopee.json`) → [[Conferência na Shopee (rastreio)]].

## Relacionado
- [[Shopee — organizar envio e AWB]] · [[Conferência na Shopee (rastreio)]] · [[estado]] · [[Desempenho]] · [[bot_telegram]]
