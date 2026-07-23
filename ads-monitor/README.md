# ads-monitor — coletor de métricas do Product Ads (Mercado Livre)

Camada 1 do futuro monitor de campanhas do Mercado Ads: um **coletor
determinístico** (sem IA) que grava, uma vez por dia, o snapshot das métricas
de cada campanha das contas configuradas (Cozilatti, Gastromaq...) num SQLite
**local**. Motor de recomendação, dado de margem e agendamento automático
ficam para uma próxima etapa — isto é só a base histórica.

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

Confirmados na doc oficial "Product Ads" do Mercado Livre Developers (via
conector MercadoLibre) — não são chutes:

```
GET /advertising/advertisers?product_id=PADS
GET /advertising/{site}/advertisers/{advertiser_id}/product_ads/campaigns/search
GET /advertising/{site}/product_ads/campaigns/{campaign_id}
```
O terceiro (detalhe por campanha) traz `lost_impression_share_by_budget` — o
sinal **oficial** de campanha limitada por orçamento (não confiar num cálculo
caseiro de custo÷orçamento: o campo `budget` da API é a média diária de um
ciclo **mensal com rollover**, então esse cálculo é enganoso).

## Uso

```powershell
python ads-monitor\coletar.py                    # ontem, todas as contas
python ads-monitor\coletar.py --dia 2026-07-20    # um dia especifico
python ads-monitor\coletar.py --conta cozilatti   # so uma conta
```

## Armazenamento

`historico_ads.sqlite3` (gitignorado, local — como o `historico_impressao.json`
do Resumo do dia). Uma linha por (dia, conta, campanha), chave primária
`(data, conta, campaign_id)`. Consultável com qualquer cliente SQLite:

```powershell
sqlite3 ads-monitor\historico_ads.sqlite3 "select data, campaign_name, roas, lost_impression_share_by_budget from campanhas_diarias order by data desc;"
```

## Limitações conhecidas desta versão

- Sem paginação (o limite padrão da API é 50 campanhas por advertiser —
  acima do volume atual das duas contas; revisar se crescer).
- Sem motor de recomendação nem dado de margem — só a base histórica.
- Sem agendamento automático ainda — rode manualmente por enquanto.
