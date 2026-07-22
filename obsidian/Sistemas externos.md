---
tags: [hub, sistema-externo]
aliases: [Sistemas externos, Integrações externas]
type: hub
status: current
---

# 🌐 Sistemas externos

> [!abstract]
> Tudo que vive **fora do repositório** mas é essencial à operação. Nenhum é versionado; o
> app depende do comportamento de cada um. Esta é a página-índice — o detalhe está nas notas
> de [[Mercado Livre|marketplace]] e [[Telegram|integração]].

## Marketplaces (APIs)
- **[[Mercado Livre]]** — pedidos, envios e etiquetas ZPL; OAuth com `refresh_token` que **rotaciona** → [[Token e rotação do refresh]].
- **[[Shopee]]** — API v2; URL **assinada por HMAC** (leva `access_token`/`sign`); etiqueta só **após organizar o envio** → [[Shopee — organizar envio e AWB]].

## Integrações (serviços e hardware)
- **[[Telegram]]** — bot de consulta (ML+Shopee) e impressão só do ML.
- **[[Zebra e pasta Downloads]]** — a impressora térmica e a **ponte** via pasta Downloads; um app externo (`impressora_zebra_usb.py`, de outro projeto) monitora e imprime → [[Ponte com a Zebra]].
- **[[GitHub Actions (CI)]]** — testes (3.11/3.12), `ruff`, smoke da GUI e validação do cofre.

## Por que documentar aqui
O **contrato** de cada externo governa decisões nossas: o prefixo do `.zip` (Zebra), a
rotação do refresh (OAuth), o AWB antes da etiqueta (Shopee), a URL assinada (Redação de
segredos). Mudar nosso lado sem respeitar o contrato **quebra a operação**.

## Relacionado
- [[🏠 Home]] · [[Fluxos de operação]] · [[Arquivos — locais vs versionados]]
