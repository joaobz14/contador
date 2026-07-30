# TikTok Shop Open API — levantamento para futura integração

> **Status: pesquisa, nada implementado.** Registra como a API do TikTok Shop
> funciona e como ela encaixaria neste app, ao lado de Mercado Livre e Shopee.
> Levantado em **30/07/2026**.
>
> **Leia a seção "Força da evidência" antes de codar.** A doc oficial
> (`partner.tiktokshop.com`) **não pôde ser lida** durante este levantamento — o
> que está aqui vem de três fontes de peso desigual, e isso está marcado item a
> item. Não trate nada marcado como 🟡 como fato.

## Resumo executivo

- **Encaixa bem no app.** A etiqueta sai em **ZPL** no Brasil (🟢 confirmado em
  produção), a autenticação é **irmã da Shopee** (assinatura HMAC na query) e o
  modelo de envio é **drop-off/postagem**, igual ao que já operamos. Entraria como
  um `ProvedorTikTok` na abstração existente.
- **O risco que matou a Amazon não se repete:** o TikTok Shop opera no Brasil e a
  etiqueta é do vendedor. Nos pedidos por **Correios** (o caso do dono) o envio é
  **TikTok Shipping**, que é justamente o caso coberto pelo endpoint de etiqueta.
- **A pergunta que ainda decide** (🟡): a **API** aceita ZPL? O **painel** aceita
  (confirmado), mas painel e API são coisas diferentes — e foi exatamente esse
  tipo de salto que enterrou o item 12.
- **A segunda pergunta, tão importante quanto** (🟡): a API devolve a **NF-e**? Se
  devolver só a etiqueta, o operador continua tendo que ir ao painel buscar a
  nota, e metade do ganho evapora.

## Força da evidência

| Marca | Fonte | Peso |
|---|---|---|
| 🟢 | **Produção**: print do painel do dono, 30/07/2026 | Fato |
| 🟡 | **SDKs de terceiros** no npm (`tiktokshops-api-client` 1.0.6, mai/2026; `tiktok-shop-sdk` 1.0.3) — código que roda contra a API real, MIT | Forte, mas não-oficial e possivelmente incompleto |
| 🔴 | Prosa de blog / IA de suporte | Descartado (ver "Becos sem saída") |

## O que está confirmado (🟢 produção, painel BR)

O diálogo **"Imprimir documento"** do painel oferece:

| Documento | Tamanho | Marcado por padrão |
|---|---|---|
| Etiqueta de envio | A6 | ✅ |
| Lista de embalagem | A6 | — |
| Lista de seleção | A4 | — |
| **NF-e** | A6 | ✅ |

E, embaixo: `Layout: Imprimir em 1 folha` · **`Formato de arquivo: ZPL`**, com um
link **"Editar configurações"** — ou seja, o formato é uma **preferência da
conta**, não uma escolha por impressão.

> Isso levanta uma hipótese útil (🟡): se o formato é configuração de conta, é
> plausível que a API **honre a preferência salva** em vez de aceitar um
> parâmetro. Confirmar — muda o desenho do cliente.

**Modelo de envio do dono:** postagem por **Correios** → é **TikTok Shipping**
(a plataforma emite a etiqueta), que é o caso que o endpoint de documento cobre.

## Endpoints (🟡 extraídos do código dos SDKs)

```
Produção   https://open-api.tiktokglobalshop.com
Sandbox    https://open-api-sandbox.tiktokglobalshop.com     ← existe
Auth       https://auth.tiktok-shops.com
```

| Operação | Método e caminho |
|---|---|
| Token | `POST /api/v2/token/get` · `POST /api/v2/token/refresh` |
| Listar pedidos | `POST /order/202309/orders/search` |
| Detalhe do pedido | `GET /order/202309/orders` |
| Horários de handover | `GET /fulfillment/202309/packages/{package_id}/handover_time_slots` |
| **Despachar** | `POST /fulfillment/202309/packages/{package_id}/ship` |
| **Etiqueta** | `GET /fulfillment/202309/packages/{package_id}/shipping_documents` |

**Tipos de documento** que o SDK conhece — note que **não há ZPL nem NF-e aqui**,
e é por isso que as duas perguntas em aberto continuam abertas:

```
PACKING_SLIP                      // PDF
SHIPPING_LABEL                    // PDF
SHIPPING_LABEL_PICTURE            // PNG
SHIPPING_LABEL_AND_PACKING_SLIP
```

O SDK expõe só `document_type` e **não implementa** o `document_format` que
outras fontes mencionam. Como o painel comprovadamente imprime ZPL, a leitura
mais provável é que **o SDK esteja incompleto** — não que a API não suporte.

## Autenticação (🟡) — é a da Shopee, não a do ML

Assinatura **HMAC-SHA256**, chave = `app_secret`:

```
base = app_secret + path + query_ordenada + corpo_json + app_secret     (v1)
base = app_secret + path + query_ordenada + corpo_json                  (v2)
sign = hex(HMAC_SHA256(app_secret, base))
```

Detalhes que importam na hora de implementar:

- `sign` e `access_token` são **excluídos** da query assinada;
- as chaves da query vão **ordenadas alfabeticamente**;
- o corpo entra **serializado em JSON**.

**`shop_cipher`**: identificador da loja devolvido junto com o token, exigido na
maioria das chamadas. Um `access_token` por loja autorizada.

> ⚠️ **A URL leva credencial**, como na Shopee. Toda a disciplina de
> `_levantar_se_erro` / `_rede_limpa` / `sem_segredos` se aplica igual — nunca
> `raise_for_status()`, e erro de transporte tem que ser convertido com
> `from None`. Ver a convenção "Erro da Shopee não pode vazar o token".

## Despachar (🟡)

Corpo do `ship`:

```
handover_method
pickup_slot { start_time, end_time }
self_shipment { tracking_number, shipping_provider_id }    ← opcional
```

A resposta de horários traz `can_drop_off`, `can_pickup` e `drop_off_point_url` —
**o mesmo modelo da Shopee**, e a mesma decisão de sempre: usar **drop-off**.

**`self_shipment` é o risco residual.** Quando o vendedor usa logística própria,
é ele quem informa o rastreio — e aí provavelmente **não há etiqueta pela API**.
Não afeta o dono hoje (Correios = TikTok Shipping), mas afeta se ele mudar de
modalidade. Filtrar por isso ao listar, como o levantamento da Amazon recomenda
filtrar FBM.

## ⚠️ O ponto novo: NF-e, e o que ele faz com o contrato da Zebra

O painel imprime **etiqueta + NF-e**, os dois marcados por padrão. Isso põe o
TikTok no mesmo formato do **Mercado Livre** (1 envio + 1 DANFE por venda), e
**não** no da Shopee (1 etiqueta por venda).

Isso não é detalhe cosmético: o app da Zebra **valida paridade** para o ML
(`_verificar_paridade_ml` — total de ZPLs tem que ser par, senão avisa "possível
DANFE ausente"), e essa validação é ligada pela **origem detectada no ZIP**. Um
prefixo novo de TikTok obrigaria a decidir, **junto com o outro repo**:

1. o lote vem 2-por-venda (valida paridade, como ML) ou 1-por-venda (não valida)?
2. o `Layout: Imprimir em 1 folha` funde etiqueta + NF-e num **único** ZPL? Se
   sim, a contagem muda e a paridade **não** se aplica.

Sem responder isso antes, o monitor da Zebra ou acusa falso alarme a cada lote,
ou deixa passar NF-e faltando.

## Como encaixaria (arquitetura)

A abstração de **provedor** é a costura certa, como no levantamento da Amazon:

- **`ProvedorTikTok`** ao lado de `ProvedorML`/`ProvedorShopee`.
- Reaproveita `agrupar`/`ordenar_grupos`, a aba **Nomes** (`nomes_sku.json`),
  `estado.py` (novo `estado_tiktok.json`, mesma chave `{dia}|{chave}|q{qtd}`),
  `_com_retry` e o padrão `obter_token(cred)` com trava entre processos.
- **ZPL cai no fluxo da Zebra que já existe** — precisa só de um **prefixo novo**
  no nome do `.zip` (ex.: `etiqueta tiktok - ...`), **combinado antes** com o repo
  `impressora-zebra-usb`: o prefixo é o contrato entre os dois apps, e agora
  também o mural de status.
- Bootstrap: `pegar_token_tiktok.py`, como os dois que já existem.
- Se houver carimbo, manter `^CI28`…`^CI0` (UTF-8).

## Roteiro sugerido (quando/se formos fazer)

1. **Responder as duas perguntas em aberto primeiro** — API devolve ZPL? API
   devolve NF-e? O **sandbox existe**, então dá para responder sem tocar na loja
   de produção. Sem isso, não vale codar.
2. Medir quantos pedidos caem em `self_shipment` (hoje: zero).
3. Combinar o prefixo e o formato do lote com o repo da Zebra (paridade!).
4. `pegar_token_tiktok.py` + `tiktok_api.py` (listar, despachar, etiqueta, estado).
5. `ProvedorTikTok` na GUI + arquivo de estado.
6. Testes sem rede (mocks), como Shopee/ML.

## Becos sem saída (para ninguém repetir)

- **`partner.tiktokshop.com` é inacessível** do ambiente de sessão do Claude: a
  política de rede recusa o CONNECT (`WebFetch` devolve 403 até em `example.com`;
  Chromium dá `ERR_TUNNEL_CONNECTION_FAILED`). O truque do `api-monitor/`
  (Chromium quando o fetch falha) **não** ajuda — sai pelo mesmo proxy. O npm e o
  PyPI, esses, são acessíveis: foi por aí que os SDKs chegaram.
- **A IA de suporte do painel respondeu pela documentação ERRADA.** Ela citou
  Mini Programs (`/v2/minis/subscription/create/`), Local Services
  (`/v2/localservice/...`) e TikTok for Developers
  (`open.tiktokapis.com/merchant/oauth/token/`), e chegou a "corrigir" o endpoint
  de token **certo** por um errado. **Teste de sanidade antes de gastar perguntas
  com ela:** *"What is shop_cipher?"* — se não souber, é a IA errada, feche.

## Fontes

- Coleção oficial no Postman — https://www.postman.com/tiktok-shop-open/tiktok-shop-public-workspace
- Doc oficial (inacessível daqui) — https://partner.tiktokshop.com/docv2
- SDK `tiktokshops-api-client` (npm, MIT) — endpoints e DTOs de fulfillment
- SDK `tiktok-shop-sdk` (npm, MIT) — assinatura, token e `shop_cipher`
- Print do painel do vendedor BR, 30/07/2026 — formato ZPL e lista de documentos
