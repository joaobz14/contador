# ads-monitor — monitor de campanhas do Product Ads (Mercado Livre)

Monitor de campanhas do Mercado Ads (Product Ads) para as contas Cozilatti e
Gastromaq, em três camadas:

1. **Coleta** (`coletar.py`, agendada) — grava, uma vez por dia, o snapshot
   das métricas de cada campanha — e, dentro dela, de cada **ad_group/item
   anunciado** — num SQLite **local**.
2. **Atribuição por SKU** (dentro do `coletar.py`) — já construída (para não
   esperar a fonte de margem por SKU, que ainda não existe — ver "Limitações"
   abaixo); quando a margem existir, é só cruzar com o que já está gravado.
3. **Recomendação** (`recomendar.py`) — gera recomendações de ação a partir do
   histórico, usando só os sinais que **não** dependem de margem (ver seção
   própria abaixo). Recomendações condicionadas a margem ficam pra quando essa
   fonte existir.

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

Pra resolver o **SKU** de cada `item_id`, o coletor reusa `GET /items/{id}`
(a **mesma** chamada que o núcleo já faz para GTIN/título) via
`core.buscar_detalhes` — sem chamada de API nova, só um campo a mais lido da
mesma resposta.

## Uso

```powershell
python ads-monitor\coletar.py                    # ontem, todas as contas
python ads-monitor\coletar.py --dia 2026-07-20    # um dia especifico
python ads-monitor\coletar.py --conta cozilatti   # so uma conta
```

## Agendamento automático (Windows)

Sem histórico de vários dias não dá pra confiar em nenhuma recomendação
futura — então vale rodar sozinho, todo dia, sem depender de lembrar.

```
ads-monitor/
├─ run-diario.ps1           # roda coletar.py + grava log (chamado pela tarefa)
├─ registrar-tarefa.ps1     # registra a tarefa diaria no Agendador do Windows (rode 1x)
└─ logs/                    # saída de cada run (gitignorado)
```

Registrar (uma vez, no PowerShell da sua máquina):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ads-monitor\registrar-tarefa.ps1
```

Por padrão roda **todo dia às 11:00** (depois das 10:00 GMT-3 que a doc
oficial cita como horário de fechamento das métricas do dia anterior — a
margem de 1h evita coletar "ontem" ainda provisório). Ajuste a variável
`$Hora` no topo do script se quiser outro horário. Mesmo padrão do
`api-monitor/registrar-tarefa.ps1` — `Register-ScheduledTask` nativo (sem Git
Bash), roda com o seu usuário só quando você está logado (não guarda senha).

Comandos úteis depois:
```powershell
Start-ScheduledTask   -TaskName 'Contador - Monitor Ads (diario)'   # rodar agora
Get-ScheduledTaskInfo -TaskName 'Contador - Monitor Ads (diario)'   # ver próxima execução / último resultado
Unregister-ScheduledTask -TaskName 'Contador - Monitor Ads (diario)' -Confirm:$false  # remover
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

## Recomendações (`recomendar.py`)

Lê `campanhas_diarias` numa janela de dias e gera recomendações no formato
pedido desde o início do projeto: conta, campanha, problema, evidência, ação
exata, justificativa, impacto esperado, risco, confiança, urgência, prazo de
reavaliação e métrica de verificação.

```powershell
python ads-monitor\recomendar.py                    # janela padrao (7 dias), todas as contas
python ads-monitor\recomendar.py --dias 14           # janela maior
python ads-monitor\recomendar.py --conta cozilatti   # so uma conta
```

**Só os sinais que a própria API já calcula e não dependem de margem:**
- **Orçamento insuficiente** (`lost_impression_share_by_budget` médio alto).
- **Ranking baixo** (`lost_impression_share_by_ad_rank` médio alto).
- **ROAS abaixo do objetivo** (`roas` médio < `roas_target` da campanha).

Recomendação de **aumentar investimento** (orçamento ou ranking — ajustar
ACOS/CPC também custa dinheiro) sai sempre marcada **"Recomendação
condicionada à validação da margem"**. ROAS abaixo do alvo não precisa dessa
ressalva — é redução de risco, não aposta de investimento.

**Trava contra recomendar em cima de dado fraco** (regra do pedido original —
nunca recomendar com base em 1 dia, poucos cliques ou dado provisório):
campanha com menos de `MIN_DIAS` (3) dias distintos ou `MIN_CLICKS` (20)
cliques na janela fica "monitorando", sem recomendação. Dado provisório já é
impossível por construção — `coletar.py` só grava dias fechados, nunca "hoje".
**Não detecta campanha recém-criada de verdade** (precisaria de
`date_created`, fora do schema atual) — `MIN_DIAS` é um substituto aproximado
(dias no *nosso* histórico, não a idade real na ML).

## Limitações conhecidas desta versão

- `campanhas_diarias` sem paginação (o limite padrão da API é 50 campanhas
  por advertiser — acima do volume atual das duas contas; revisar se
  crescer). `ad_groups_diarios` **já pagina**.
- **Resolução de SKU** prioriza o `seller_sku` real (via `GET /items/{id}`,
  cacheado no mesmo `itens_cache.json` do núcleo — sem chamada extra de rede
  além do que a impressão já faz) e cai pro `skus_por_anuncio.json` local
  (mesma chave que `identidade()` usa, `"{item_id}:0"`) só quando o item não
  tem `seller_sku` cadastrado. Antes desta extensão a cobertura era 0/468
  itens (o mapa local sozinho não resolve a maioria — é um mapa manual pequeno,
  não um resolvedor geral).
- **Ad_group não é 1:1 com item.** Tipos `FAMILY` (variações) e `CATALOG`
  (vários vendedores concorrendo no mesmo anúncio — visto 1 caso com 7
  `item_id` diferentes) agrupam vários `item_id` sem quebra de métrica por
  item dentro do grupo; a granularidade mais fina que a API dá é o ad_group.
- **Item com variações de SKU diferentes fica sem SKU** (limitação aceita, não
  perseguida por ora): `GET /ad_groups/{id}/ads` não informa `variation_id`,
  então mesmo achando onde o SKU mora por variação não dá pra saber qual
  variação está sendo anunciada. **Confirmado oficialmente** pelo assistente de
  IA do Mercado Livre: a API de Product Ads não expõe SKU nem variação-SKU em
  nenhuma resposta — o agrupamento por variante usa só
  `family_id`/`catalog_product_id`/`parent_id`/`ad_group_external_id`.
- Sem dado de margem — `recomendar.py` só cobre sinais sem margem; a
  atribuição por SKU está pronta, mas ninguém ainda cruza com custo/margem
  (ver `docs/PRIORIDADES_TECNICAS.md`, item 10).
- Sem tela/GUI própria — `recomendar.py` imprime relatório em texto (CLI).
  Uma interface fica pra quando fizer sentido (subsistema isolado da tela de
  etiquetas, mesma decisão de sempre).
