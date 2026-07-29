---
tags: [conceito, shopee, awb, impressao, invariante]
aliases: [organizar envio, AWB, ship_order, drop-off, create_shipping_document]
type: concept
---

# 🛍️ Shopee — organizar envio e AWB

> [!abstract]
> Na Shopee a etiqueta **não existe** de imediato: só **depois de organizar o envio**
> (que emite o **AWB**). Toda a lógica está em [[shopee_api]].

## O caminho (invariantes 8 e 9)
```text
READY_TO_SHIP → agrupar → organizar (drop-off, ship_order) → AWB
→ create_shipping_document (EXIGE o AWB) → aguardar READY → baixar → ZIP
```

## Pegadinhas validadas com loja real
- `get_shipping_parameter` e `get_tracking_number` são **GET** (POST → 404).
- `create_shipping_document` **exige `tracking_number`**; sem ele → `logistics.tracking_number_invalid`.
- Organiza sempre como **Postagem (drop-off)**, nunca buyer-pickup. `info_needed.dropoff` lista campos exigidos (geralmente vazio).
- **Já organizado ≠ sem drop-off**: `envio_ja_arranjado(param)` é consultado **antes** de recusar. Já arranjado → **pula `ship_order`** e só aguarda o AWB (senão `info_needed={}` virava um falso erro).
- **Lote**: `_organizar_varios` em camadas (AWB existente → **`_filtrar_ja_arranjados`** → `batch_ship_order` → confirmação **pelo AWB** → fallback individual).

> [!warning] Compliance da Shopee: success rate do `ship_order` (2026-07)
> A Shopee exige (obrigatório, com prazo) success rate > 90%/7 dias em
> `v2.logistics.ship_order` — "already shipped" é uma causa documentada de
> erro (reenviar um pedido já arranjado). O caminho em lote mandava **todos**
> os pedidos sem AWB pro `batch_ship_order`, sem checar se já estavam
> arranjados (só o caminho individual checava). Corrigido com
> `_filtrar_ja_arranjados` (nova etapa antes do batch). A migração completa
> que a Shopee recomenda (`v2.order.search_package_list` +
> `v2.order.get_package_detail`) ficou **pendente** — `open.shopee.com`
> bloqueado neste ambiente, sem o schema real dos endpoints não dá pra
> implementar com segurança (ver `docs/PRIORIDADES_TECNICAS.md`, item 11).

## Desempenho
Organizar é **~14s fixos** (latência do AWB) — batch **não** acelera. O ganho está em
gerar documentos **em paralelo por pedido** → [[Desempenho]].

## A etiqueta
Vem como **ZIP com ZPL (`~DGR/Z64`) dentro** — imprime direto, não reembrulhar. Sem o
nome do produto → conferência pelo AWB → [[Conferência na Shopee (rastreio)]].

## Relacionado
- [[shopee_api]] · [[Conferência na Shopee (rastreio)]] · [[Desempenho]] · [[Invariantes críticas]] · [[Ponte com a Zebra]]
