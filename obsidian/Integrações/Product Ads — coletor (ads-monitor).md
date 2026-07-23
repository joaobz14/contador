---
tags: [integracao, mercado-ads, product-ads, monitor]
type: integration
status: current
aliases: [Product Ads, Mercado Ads, ads-monitor, coletor de metricas de campanha]
source_files: [ads-monitor/coletar.py, ads-monitor/recomendar.py, ads-monitor/run-diario.ps1, ads-monitor/registrar-tarefa.ps1, tools/diag_ads.py, tools/diag_coleta.py]
source_docs: [ads-monitor/README.md]
verified_at_commit: 463f970
---

# 📣 Integração: Product Ads — monitor de campanhas (`ads-monitor/`)

> [!abstract]
> Monitor de campanhas de Mercado Ads (Product Ads) para as contas Cozilatti e
> Gastromaq, em 3 camadas: **coleta** (`coletar.py`, sem IA, agendada
> diariamente) grava o snapshot das métricas de cada campanha — e, dentro dela,
> de cada **ad_group/item anunciado** (atribuição por SKU, best-effort) — num
> SQLite **local**; **recomendação** (`recomendar.py`) gera ações a partir do
> histórico usando só os sinais que **não** dependem de margem (orçamento,
> ranking, ROAS vs. alvo). Só leitura — nunca muda campanha/orçamento/anúncio.
> Recomendações condicionadas a margem ficam **bloqueadas** (nenhuma fonte de
> custo/margem por SKU existe no projeto ainda).

## Por que existe
Pedido original: um monitor que **sugira** ações de otimização de campanha (não
que as execute) — orçamento, ACOS/ROAS, limitação por rank vs. orçamento. Antes de
construir o motor de recomendação era preciso validar a integração (a conta já usa
Product Ads? quais endpoints funcionam? qual sinal é confiável?) e ter uma base
histórica — daí a primeira camada. Depois, o dono pediu para já construir a
**atribuição por SKU dentro da campanha** mesmo sem a fonte de margem pronta
("acrescentamos depois") — para não esperar essa decisão de negócio para ter a
base de dados no lugar.

## Endpoints confirmados (doc oficial)
```
GET /advertising/advertisers?product_id=PADS
GET /advertising/{site}/advertisers/{advertiser_id}/product_ads/campaigns/search
GET /advertising/{site}/product_ads/campaigns/{campaign_id}
GET /advertising/{site}/advertisers/{advertiser_id}/product_ads/ad_groups/search
GET /advertising/{site}/product_ads/ad_groups/{ad_group_id}/ads
```
O terceiro (detalhe por campanha) traz `lost_impression_share_by_budget` — o sinal
**oficial** de campanha limitada por orçamento. Endpoints legados (ex.:
`/advertising/advertisers/{id}/product_ads/campaigns`) são **descontinuados em
26/02/2026**; um 404 neles é esperado, não bug.

Os dois últimos (fluxo por `ad_group_id`) resolvem a cadeia campanha → ad_group →
item_id, substituindo o antigo endpoint de métricas **por item** dentro da
campanha, descontinuado em **27/05/2026** (doc "Product Ads para Catálogo e User
Products"). Achado confirmado com dado real: um **ad_group não é 1:1 com item** —
tipos `FAMILY` (variações) e `CATALOG` (vários vendedores concorrendo no mesmo
anúncio — visto 1 caso com 7 `item_id` diferentes) agrupam vários `item_id` sem
quebra de métrica por item dentro do grupo; a granularidade mais fina que a API dá
é o ad_group. O `item_id` resolve pro SKU priorizando o `seller_sku` real
(`GET /items/{id}`, **mesma** chamada que o núcleo já faz pra GTIN/título,
cacheada no `itens_cache.json` compartilhado) e caindo pro `skus_por_anuncio.json`
local só quando o item não tem `seller_sku` cadastrado — achado real: a versão
inicial que só usava o mapa local resolvia **0 de 468 itens** (o mapa é manual e
pequeno, não um resolvedor geral).

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
- `campanhas_diarias` sem paginação (limite padrão da API: 50 campanhas — acima
  do volume atual). `ad_groups_diarios` já pagina.
- Resolução de SKU ainda é best-effort: itens de outros vendedores (dentro de
  um `ad_group` `CATALOG` compartilhado) ou sem `seller_sku`/adoção cadastrados
  ficam sem SKU.
- Item com variações de SKU diferentes fica sem SKU (Product Ads não expõe
  `variation_id` nem SKU — confirmado oficialmente pelo assistente de IA do
  Mercado Livre; limitação aceita, não perseguida por ora).
- `recomendar.py` só cobre sinais sem margem — recomendações condicionadas
  (aumentar investimento) ficam bloqueadas até existir a fonte de margem
  (ver `docs/PRIORIDADES_TECNICAS.md`, item 10).
- Sem tela/GUI — `recomendar.py` imprime relatório em texto (CLI). Uma
  interface fica pra quando fizer sentido, sempre como subsistema isolado
  (nunca dentro da tela de etiquetas).

## Agendamento
`run-diario.ps1` + `registrar-tarefa.ps1` (mesmo padrão do `api-monitor/`,
`Register-ScheduledTask` nativo) registram uma tarefa diária às 11:00 — depois
das 10:00 GMT-3 de fechamento das métricas. Sem histórico de vários dias
nenhum próximo passo (motor de recomendação, com ou sem margem) teria dado
suficiente; o pedido original é explícito: nunca recomendar em cima de 1 dia.

## Recomendações (`recomendar.py`)
Lê `campanhas_diarias` numa janela de dias (default 7) e gera recomendações no
formato do pedido original: conta/campanha/problema/evidência/ação/
justificativa/impacto/risco/confiança/urgência/prazo de reavaliação/métrica de
verificação. Só os 3 sinais que a própria API já calcula e não dependem de
margem: orçamento insuficiente, ranking baixo, ROAS abaixo do `roas_target`.
Recomendação de **aumentar investimento** (orçamento ou ranking) sai sempre
marcada **"Recomendação condicionada à validação da margem"**; ROAS abaixo do
alvo não precisa da ressalva (redução de risco, não aposta de investimento).

**Trava contra dado fraco** (regra do pedido original — nunca recomendar em
cima de 1 dia, poucos cliques ou dado provisório): campanha com menos de
`MIN_DIAS=3` dias distintos ou `MIN_CLICKS=20` cliques na janela fica
"monitorando", sem recomendação (`avaliar_campanha()` é função pura, testada
isoladamente). Dado provisório já é impossível por construção — o coletor só
grava dias fechados. **Não** detecta campanha recém-criada de verdade
(precisaria de `date_created`, fora do schema); `MIN_DIAS` é um substituto
aproximado (dias no *nosso* histórico, não a idade real na ML).

## Relacionado
- [[Token e rotação do refresh]] · [[Trava entre processos]] · [[Grafo em duas camadas]]
- `ads-monitor/README.md` (uso, schema do SQLite, exemplos de consulta)
