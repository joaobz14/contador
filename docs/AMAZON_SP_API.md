# Amazon SP-API — levantamento para futura integração

> **Status: pesquisa, nada implementado.** Este documento registra como a API da
> Amazon funciona e como ela encaixaria neste app, para quando/se decidirmos
> adicionar a Amazon ao lado de Mercado Livre e Shopee. Levantado em **jul/2026**;
> confira as datas de versão da API antes de codar (a Amazon versiona bastante).

## Resumo executivo

- **Tecnicamente cabe bem** no app: a Amazon devolve etiqueta em **ZPL térmico**,
  autentica por **OAuth2 (refresh_token)** e lista pedidos por status — os três
  pilares que ML e Shopee já usam. Encaixa direto na abstração de **provedor**.
- **O risco NÃO é técnico, é de negócio/Brasil:** só faz sentido para pedidos que
  **você mesmo envia** (FBM/MFN). Se os pedidos forem **FBA** ou **DBA (Delivery by
  Amazon)**, a Amazon cuida do envio e **não há etiqueta de vendedor para separar/
  imprimir** — o app não teria o que fazer.
- **Teste decisivo antes de investir tempo:** confirmar no Seller Central que os
  pedidos Amazon BR geram uma **etiqueta de auto-envio imprimível via API**.

## O que é a SP-API

**Selling Partner API (SP-API)** é a API REST oficial da Amazon para vendedores
acessarem pedidos, estoque, envios, etc. Substituiu a antiga MWS. Boa notícia: a
exigência histórica de **assinatura AWS (SigV4/IAM role)** foi **removida** — hoje
basta o token LWA (ver abaixo).

Marketplace do Brasil: **Amazon.com.br**, `marketplaceId = A2Q3Y263D00KWC`
(região de endpoint: `sellingpartnerapi-na.amazon.com`, grupo das Américas).

## Autenticação (muito parecida com ML/Shopee)

Fluxo **LWA — "Login with Amazon"** (OAuth 2.0):

- Credenciais do app: `client_id` (LWA) + `client_secret`.
- O vendedor autoriza → gera um **`refresh_token`** de longa duração.
- Em runtime: troca `refresh_token` por **`access_token`** (~1h) no endpoint
  `https://api.amazon.com/auth/o2/token`.

Encaixe no nosso padrão: **igual ao `obter_token(cred)`** já existente (cache +
lock + relê disco). Um `pegar_token_amazon.py` faria o bootstrap, como
`pegar_token.py` (ML) e `pegar_token_shopee.py`.

Diferenças em relação a ML/Shopee (atenção):

- O **authorization code expira em ~5 min** (igual ML; o passo do navegador tem
  que ser rápido).
- **Re-autorização a cada 365 dias:** o vendedor precisa reautorizar o app 1x por
  ano. ML/Shopee não têm isso — vale um lembrete/tratamento no futuro.
- **Cadastro de desenvolvedor** no *Solution Provider Portal* + criação do app +
  aprovação da Amazon. É mais burocrático que ML/Shopee.
- **Throttling** por operação (token bucket / rate limits) — respeitar `x-amzn-
  RateLimit-Limit` e fazer backoff (já temos `_com_retry` no núcleo para reusar).

## O ponto que decide tudo: modelo de fulfillment

| Modelo | Quem envia | Tem etiqueta p/ o app imprimir? |
|---|---|---|
| **FBA** (Fulfillment by Amazon) | Amazon (do centro dela) | **Não** — Amazon envia. |
| **DBA** (Delivery by Amazon, BR) | Logística gerenciada Amazon | **Provavelmente não** para o vendedor. |
| **FBM / MFN** (Merchant Fulfilled) | **Você** | **Sim** — é o caso que interessa. |

**Só pedidos FBM/MFN entram no app.** Filtrar por isso ao listar.

## Pedidos

**Orders API** (versão nova **`v2026-01-01`**, que simplificou 10 operações em 2:
`getOrder` e `searchOrders`). Lista pedidos por status (`Unshipped`,
`PartiallyShipped`) — análogo ao "listar pedidos prontos" de ML/Shopee. Guia de
migração da v0 → v2026-01-01 existe na doc.

Agrupar por produto+quantidade reaproveita `agrupar`/`ordenar_grupos` do núcleo.

## Etiqueta de envio

Dois caminhos (a Amazon recomenda o v2 para integrações novas):

1. **Merchant Fulfillment API** (v0): `getEligibleShipmentServices` →
   `createShipment` (→ `getShipment`, `cancelShipment`). Compra o frete via
   **"Amazon Buy Shipping"** e devolve a etiqueta.
2. **Shipping API v2** (recomendada): `getRates` → `purchaseShipment` → etiqueta.

**Formato da etiqueta:** pode vir em **ZPL (ZPL203)** — ou seja, **térmica, pronta
para a Zebra** 🎯 (também há PDF/PNG dependendo da transportadora; pediríamos ZPL).

**Empacotamento (difere da Shopee):** a Amazon devolve o documento como
**string Base64 → conteúdo GZIP → extrair o ZPL de dentro**. (A Shopee é um ZIP
com o `.txt`.) É só um **adaptador de desempacotamento** diferente antes de jogar
na Downloads.

> Nota: a operação em lote `getShipmentLabels` é **só região NA** — mas a etiqueta
> individual do `createShipment`/`purchaseShipment` funciona normalmente.

## ⚠️ Ressalva Brasil (a mais importante)

A etiqueta da Merchant Fulfillment é comprada via **Amazon Buy Shipping** (frete
pelos parceiros da Amazon). No Brasil os programas fortes são **FBA** e **DBA**, e
a disponibilidade de gerar **etiqueta de auto-envio via API para transportadoras
BR varia** conforme o setup do vendedor e as transportadoras habilitadas.

**Antes de qualquer código:** confirmar no **Seller Central** se os pedidos Amazon
BR produzem etiqueta imprimível pelo vendedor. Se forem FBA/DBA, não há o que
separar/imprimir.

## Como encaixaria no app (arquitetura)

A abstração de **provedor** já é a costura certa:

- **`ProvedorAmazon`** ao lado de `ProvedorML`/`ProvedorShopee`: métodos de listar,
  organizar (se preciso), gerar etiqueta e coletar contagem por dia.
- Reaproveita: `agrupar`/`ordenar_grupos`, aba **Nomes** (`nomes_sku.json`),
  `estado.py` (novo arquivo de estado, ex.: `estado_amazon.json`, mesma chave
  `{dia}|{chave}|q{qtd}`), `_com_retry`, e o padrão `obter_token`.
- **ZPL cai no mesmo fluxo da Zebra** — precisa só de um **prefixo novo** no nome
  do `.zip` na Downloads (ex.: `etiqueta amazon - ...`) que o app da Zebra
  (`impressora_zebra_usb.py`, fora deste repo) reconheça. **Combinar** com o app
  da Zebra antes (o prefixo é o contrato entre os dois).
- Bootstrap: `pegar_token_amazon.py`.
- **Encoding:** se usarmos carimbo/nome, manter o padrão `^CI28`…`^CI0` (UTF-8),
  como no ML.

## Roteiro sugerido (quando/se formos fazer)

1. **Validar o negócio primeiro:** cadastrar-se como dev SP-API, criar o app,
   autorizar a conta e **listar 1 pedido FBM** + pedir a etiqueta dele para ver o
   que volta (ZPL? Base64/GZIP?). Sem isso, não vale codar.
2. Confirmar com o dono do app da Zebra o **prefixo** do arquivo (`etiqueta
   amazon - ...`).
3. `pegar_token_amazon.py` (OAuth) + `amazon_api.py` (listar, etiqueta, estado).
4. `ProvedorAmazon` na GUI + arquivo de estado.
5. Testes sem rede (mocks), como Shopee/ML.

## Fontes (jul/2026)

- Merchant Fulfillment API — https://developer-docs.amazon.com/sp-api/docs/merchant-fulfillment-api
- Orders API (v2026-01-01) — https://developer-docs.amazon.com/sp-api/docs/orders-api
- Manipular/recuperar etiquetas (ZPL, Base64/GZIP) — https://developer-docs.amazon.com/sp-api/docs/manipulate-shipping-labels
- Conectar à SP-API (LWA OAuth) — https://developer-docs.amazon.com/sp-api/docs/connecting-to-the-selling-partner-api
- Autorizar aplicações públicas — https://developer-docs.amazon.com/sp-api/docs/authorize-public-applications
