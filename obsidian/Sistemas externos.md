---
tags: [moc, sistema-externo]
aliases: [Sistemas externos, Integrações]
type: sistema-externo
---

# 🌐 Sistemas externos

> [!abstract]
> Tudo que vive **fora do repositório** mas é essencial à operação. Nenhum é
> versionado; o app depende do comportamento de cada um.

## Mercado Livre API
Fonte dos pedidos, detalhes, envios e etiquetas ZPL do ML. Autenticação OAuth com
`refresh_token` que **rotaciona** → [[Token e rotação do refresh]]. Consumida pelo
[[separador_etiquetas_ml (núcleo)]].

## Shopee Open Platform API (v2)
Pedidos, organização de envio, AWB e documento térmico. URL **assinada por HMAC**
que leva `access_token`/`sign` na query (→ cuidado de [[Redação de segredos]]). A
etiqueta só existe **após organizar o envio** → [[Shopee — organizar envio e AWB]].
Consumida por [[shopee_api]].
> [!note] Pegadinhas validadas com loja real
> - `get_shipping_parameter` e `get_tracking_number` são **GET** (POST → 404).
> - `create_shipping_document` **exige `tracking_number`** no corpo.
> - Organizar é **~14s fixos** (latência do AWB) — batch **não** acelera → [[Desempenho]].

## Telegram Bot API
Canal do [[bot_telegram]]. Consulta em ambos os marketplaces; **impressão só do ML**.

## Impressora térmica Zebra
Hardware que imprime o ZPL. A etiqueta térmica da Shopee vem como **ZIP com ZPL
(`~DGR/Z64`) dentro** — imprime direto, não reembrulhar.

## App `impressora_zebra_usb.py` (externo)
Programa de **outro projeto** que monitora a pasta Downloads e envia o ZIP à Zebra.
O contrato dele (prefixos, extensões, detecção de duplicata) governa nossos nomes de
arquivo → [[Ponte com a Zebra]].

## Pasta Downloads
A **ponte** entre este app e a Zebra. É **por máquina**. O ZIP cai aqui com um
**prefixo** que o monitor reconhece → [[Ponte com a Zebra]].

## GitHub Actions (CI)
Roda `pytest` (3.11 e 3.12), `ruff` e o **smoke da GUI headless** (xvfb) nos dois
marketplaces → [[Testes como documentação]].

## Relacionado
- [[🏠 Home]] · [[Fluxos de operação]] · [[Arquivos — locais vs versionados]]
