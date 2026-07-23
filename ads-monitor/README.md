# ads-monitor — coletor de métricas do Product Ads (Mercado Livre)

Base do futuro monitor de campanhas do Mercado Ads: um **coletor
determinístico** (sem IA) que grava, uma vez por dia, o snapshot das métricas
de cada campanha — e, dentro dela, de cada **ad_group/item anunciado** — das
contas configuradas (Cozilatti, Gastromaq...) num SQLite **local**. Motor de
recomendação e agendamento automático ficam para uma próxima etapa. A
atribuição por ad_group/item já foi construída (para não esperar a fonte de
margem por SKU, que ainda não existe — ver "Limitações" abaixo); quando a
margem existir, é só cruzar com o que já está gravado.

## O que faz (e o que não faz)

- **Só leitura (GET).** Nunca pausa, edita ou muda orçamento de campanha.
- Reusa a autenticação do núcleo (`obter_token`/`definir_conta`) — mesma
  trava entre processos que a GUI/bot usam; nunca duplica lógica de refresh
  nem arrisca rotacionar o `refresh_token` por fora.
- **Um dia por execução, default ONTEM** — o Mercado Livre atualiza os dados
  de Ads às 10:00 GMT-3, então "hoje" viria incompleto/provisório. Sem
  backfill automático: para coletar vários dias, rode com `--dia` repetidas
  vezes.
- **Idempotente:** rodar o mesmo dia de novo **regrava** (não duplica).
- **Isola falha por conta:** uma conta sem Product Ads ou com token vencido
  não derruba a coleta das demais no mesmo run.

## Endpoints usados

Confirmados na doc oficial "Product Ads" e "Product Ads para Catálogo e User
Products" do Mercado Livre Developers — não são chutes:

```
GET /advertising/advertisers?product_id=PADS
GET /advertising/{site}/advertisers/{advertiser_id}/product_ads/campaigns/search
GET /advertising/{site}/product_ads/campaigns/{campaign_id}
GET /advertising/{site}/advertisers/{advertiser_id}/product_ads/ad_groups/search
GET /advertising/{site}/product_ads/ad_groups/{ad_group_id}/ads
```
O terceiro (detalhe por campanha) traz `lost_impression_share_by_budget` — o
sinal **oficial** de campanha limitada por orçamento (não confiar num cálculo
caseiro de custo÷orçamento: o campo `budget` da API é a média diária de um
ciclo **mensal com rollover**, então esse cálculo é enganoso).

Os dois últimos (fluxo por `ad_group_id`) substituem o antigo endpoint de
métricas por item dentro da campanha, **descontinuado em 27/05/2026**.
Validados com chamada real de leitura antes de virar código de produção
(`tools/diag_ads.py`, passo 5). O 4º (`ad_groups/search`) traz todo ad_group
da campanha no dia (paginado — o limite padrão da API é 50 por chamada); o 5º
(`ad_groups/{id}/ads`) só é chamado para ad_groups com atividade no dia
(clicks/cost/vendas > 0) e resolve os `item_id` que compõem aquele ad_group.

## Uso

```powershell
python ads-monitor\coletar.py                    # ontem, todas as contas
python ads-monitor\coletar.py --dia 2026-07-20    # um dia especifico
python ads-monitor\coletar.py --conta cozilatti   # so uma conta
```

## Armazenamento

`historico_ads.sqlite3` (gitignorado, local — como o `historico_impressao.json`
do Resumo do dia). Três tabelas, todas idempotentes por dia (`INSERT OR
REPLACE`):

- **`campanhas_diarias`** — uma linha por (dia, conta, campanha).
- **`ad_groups_diarios`** — uma linha por (dia, conta, ad_group) — o item,
  família ou catálogo anunciado dentro de uma campanha.
- **`ad_group_itens_diarios`** — uma linha por (dia, conta, ad_group, item) —
  o(s) `item_id` que compõem cada ad_group, com o `sku` resolvido (quando
  possível) e só gravado para ad_groups que tiveram atividade no dia.

Consultável com qualquer cliente SQLite:

```powershell
sqlite3 ads-monitor\historico_ads.sqlite3 "select data, campaign_name, roas, lost_impression_share_by_budget from campanhas_diarias order by data desc;"
sqlite3 ads-monitor\historico_ads.sqlite3 "select ag.ad_group_title, i.item_id, i.sku, ag.cost from ad_groups_diarios ag join ad_group_itens_diarios i using (data, conta, ad_group_id) order by ag.cost desc;"
```

## Limitações conhecidas desta versão

- `campanhas_diarias` sem paginação (o limite padrão da API é 50 campanhas
  por advertiser — acima do volume atual das duas contas; revisar se
  crescer). `ad_groups_diarios` **já pagina**.
- **Resolução de SKU é best-effort:** só usa o `skus_por_anuncio.json` local
  (mesma chave que `identidade()` usa para anúncio sem variação,
  `"{item_id}:0"`) — **não** chama a Items API para pegar `seller_sku`
  diretamente. Um anúncio com SKU cadastrado mas fora desse mapa fica sem SKU
  por enquanto.
- **Ad_group não é 1:1 com item.** Tipos `FAMILY` (variações) e `CATALOG`
  (vários vendedores concorrendo no mesmo anúncio — visto 1 caso com 7
  `item_id` diferentes) agrupam vários `item_id` sem quebra de métrica por
  item dentro do grupo; a granularidade mais fina que a API dá é o ad_group.
- Sem motor de recomendação nem dado de margem — a atribuição por SKU está
  pronta, mas ninguém ainda cruza com custo/margem (ver
  `docs/PRIORIDADES_TECNICAS.md`, item 10).
- Sem agendamento automático ainda — rode manualmente por enquanto.
