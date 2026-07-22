---
tags: [operacao, desempenho, shopee, ml]
aliases: [desempenho, performance, tempos]
type: reference
---

# ⚡ Desempenho (medido, não teórico)

> [!abstract]
> Cronometragem real por fase desfez hipóteses erradas. Logs: `shopee_tempos.log` /
> `ml_tempos.log` (via `_log_tempos`, gitignorados, nunca levantam).

## Shopee
| Fase | Custo | Natureza |
|---|---|---|
| **Organizar** (`ship_order` → AWB) | **~14s FIXO** (1 ou 4 pedidos, igual) | Latência da Shopee emitir o AWB. **Não escala** e **não dá para apressar** — é o piso da plataforma. |
| **Gerar+baixar** | **~5s/pedido**, mas **paralelizável** | A Shopee processa requests **concorrentes** em paralelo. |

**Decisão:** `_gerar_lote` gera **um documento por pedido, em paralelo** (8 por vez).
Real: 4 pedidos **~20s → ~6s** (~70%). O que **não** acelera: `batch_ship_order`
(organizar N num request) — o AWB é latência fixa. Ver [[Shopee — organizar envio e AWB]].

## Mercado Livre ("Atualizar")
As 3 fases de `coletar_grupos` já são paralelas. A cara é o **filtro** (`GET /shipments/{id}`
por pedido não-terminal). "Ficou mais lento com o tempo" = o cache `envios_cache.json`
só guarda status **terminais**; um pedido `paid` ainda não `ready_to_print` é
re-consultado a **cada** Atualizar → cresce com o volume da janela (`DIAS_JANELA=30`).

**Feito:** filtro subiu para **20 workers**; cada fase logada em `ml_tempos.log`.
**Próximo (não feito — risco):** cache de **TTL curto** para envios
não-terminais-e-não-prontos — não pode esconder um que virou `ready_to_print` dentro do TTL.

## Relacionado
- [[shopee_api]] · [[separador_etiquetas_ml (núcleo)]] · [[Shopee — organizar envio e AWB]]
