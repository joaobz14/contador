---
tags: [integracao, mercado-ads, product-ads, monitor]
type: integration
status: current
aliases: [Product Ads, Mercado Ads, ads-monitor, coletor de metricas de campanha]
source_files: [ads-monitor/coletar.py, tools/diag_ads.py, tools/diag_coleta.py]
source_docs: [ads-monitor/README.md]
verified_at_commit: 463f970
---

# 📣 Integração: Product Ads — coletor (`ads-monitor/`)

> [!abstract]
> Camada 1 de um futuro monitor de campanhas de Mercado Ads (Product Ads) para as
> contas Cozilatti e Gastromaq: um **coletor determinístico** (sem IA) que grava,
> uma vez por dia, o snapshot das métricas de cada campanha num SQLite **local**.
> Só leitura — nunca muda campanha/orçamento/anúncio. **Ainda sem** motor de
> recomendação, dado de margem ou agendamento automático.

## Por que existe
Pedido original: um monitor que **sugira** ações de otimização de campanha (não
que as execute) — orçamento, ACOS/ROAS, limitação por rank vs. orçamento. Antes de
construir o motor de recomendação era preciso validar a integração (a conta já usa
Product Ads? quais endpoints funcionam? qual sinal é confiável?) e ter uma base
histórica — daí esta primeira camada.

## Endpoints confirmados (doc oficial, via conector MercadoLibre)
```
GET /advertising/advertisers?product_id=PADS
GET /advertising/{site}/advertisers/{advertiser_id}/product_ads/campaigns/search
GET /advertising/{site}/product_ads/campaigns/{campaign_id}
```
O terceiro (detalhe por campanha) traz `lost_impression_share_by_budget` — o sinal
**oficial** de campanha limitada por orçamento. Endpoints legados (ex.:
`/advertising/advertisers/{id}/product_ads/campaigns`) são **descontinuados em
26/02/2026**; um 404 neles é esperado, não bug.

## Armadilha de negócio validada
O campo `budget` da API é a **média diária de um ciclo mensal com rollover** — um
cálculo caseiro de custo÷orçamento é enganoso (validado com dado real: custo médio
diário R$302 vs. "budget" R$200 numa campanha Cozilatti, sem estar de fato
estourada). Por isso o coletor guarda também `lost_impression_share_by_budget` e
`lost_impression_share_by_ad_rank` — os sinais que a própria plataforma calcula.

## Como o coletor é seguro
- Reusa `obter_token`/`definir_conta`/`carregar_credenciais` do núcleo — mesma
  trava entre processos que GUI/bot, nunca duplica lógica de refresh. Ver
  [[Token e rotação do refresh]].
- Um dia por execução, default **ontem** (o ML atualiza dados de Ads às 10:00
  GMT-3; "hoje" viria incompleto).
- Idempotente por `(dia, conta, campaign_id)` — rodar de novo regrava, não duplica.
- Isola falha por conta (uma conta sem Ads ou com token vencido não derruba as
  demais no mesmo run) — nunca levanta exceção para fora de `coletar_conta`.

## Limitações desta versão
- Sem paginação (limite padrão da API: 50 campanhas — acima do volume atual).
- Sem motor de recomendação nem margem — só a base histórica.
- Sem agendamento automático — roda manualmente por enquanto.

## Relacionado
- [[Token e rotação do refresh]] · [[Trava entre processos]] · [[Grafo em duas camadas]]
- `ads-monitor/README.md` (uso, schema do SQLite, exemplos de consulta)
