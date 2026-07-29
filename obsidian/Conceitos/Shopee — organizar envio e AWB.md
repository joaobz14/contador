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
- **Lote**: `_organizar_varios` em camadas (AWB existente → **`_filtrar_ja_arranjados`** → `batch_ship_order` → confirmação **pelo AWB**). Quem sobra sem AWB **depois do batch** vira pendência de confirmação — **não** cai no individual (ver compliance abaixo). O fallback individual (`organizar_envio`) só recebe quem já estava arranjado antes desta chamada, ou quem o batch nunca chegou a tentar.

> [!warning] Compliance da Shopee: success rate do `ship_order` (2026-07, 2 rodadas)
> A Shopee exige (obrigatório, com prazo) success rate > 90%/7 dias em
> `v2.logistics.ship_order` — só o singular (`batch_ship_order` **não**
> conta, confirmado com o suporte). Causas de erro documentadas: "already
> shipped" (`logistics.package_already_shipped`) e "being allocated"
> (`logistics.error_param`).
>
> **Rodada 1:** o caminho em lote mandava **todos** os pedidos sem AWB pro
> `batch_ship_order`, sem checar se já estavam arranjados (só o individual
> checava). Corrigido com `_filtrar_ja_arranjados` (nova etapa antes do
> batch).
>
> **Rodada 2 (após respostas do suporte):** a propagação de
> `fulfillment_status`/`is_shipment_arranged` pode levar **até 15-20
> minutos** — bem mais que os ~40s de polling daqui. A rodada 1 não
> resolvia de fato: um pedido que passava pelo batch sem AWB (só pelo
> timeout curto) caía no individual, que reenviava `ship_order` com status
> ainda desatualizado. Corrigido: esses pedidos não caem mais no
> individual, viram pendência de confirmação. Defesa adicional em
> `organizar_envio`: catch pra "already shipped" (não propaga como erro) e
> retry curto pra "being allocated" (transiente, segundo a própria
> Shopee).
>
> Migração completa (`v2.order.search_package_list` +
> `v2.order.get_package_detail`, `is_shipment_arranged` já vem por pacote;
> `package_number` pode ser 1:N com `order_sn`) fica de backlog — mudança
> de modelo de identidade, não urgente pro compliance (ver
> `docs/PRIORIDADES_TECNICAS.md`, item 11).

## Desempenho
Organizar é **~14s fixos** (latência do AWB) — batch **não** acelera. O ganho está em
gerar documentos **em paralelo por pedido** → [[Desempenho]].

## A etiqueta
Vem como **ZIP com ZPL (`~DGR/Z64`) dentro** — imprime direto, não reembrulhar. Sem o
nome do produto → conferência pelo AWB → [[Conferência na Shopee (rastreio)]].

## Relacionado
- [[shopee_api]] · [[Conferência na Shopee (rastreio)]] · [[Desempenho]] · [[Invariantes críticas]] · [[Ponte com a Zebra]]
