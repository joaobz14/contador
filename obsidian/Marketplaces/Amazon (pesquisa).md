---
tags: [marketplace, amazon, pesquisa]
type: marketplace
status: research
aliases: [Amazon, Amazon SP-API, Amazon pesquisa]
source_docs: [docs/AMAZON_SP_API.md]
verified_at_commit: bcab879
---

# 🔬 Amazon (pesquisa — não implementado)

> [!warning] Status: pesquisa
> **Nada** da Amazon está implementado. Esta nota resume o levantamento em
> `docs/AMAZON_SP_API.md`. Não trate como funcionalidade.

## O que foi levantado
Como a **Amazon SP-API** encaixaria no app no futuro (autenticação, obtenção de pedidos e
etiquetas). O detalhe está em `docs/AMAZON_SP_API.md`.

## Risco decisivo (de negócio, não técnico)
No Brasil, **só FBM/MFN** (envio pelo vendedor) gera etiqueta que o app poderia imprimir;
FBA é logística da Amazon. Isso — e não a integração técnica — é o que decide se vale a pena.

## Se um dia for implementar
Entraria como mais um **provedor** (`ProvedorAmazon`), sem `if marketplace` → [[Provedor — abstração de marketplace]].

## Relacionado
- [[Mercado Livre]] · [[Shopee]] · [[Provedor — abstração de marketplace]] · [[Estado atual]]
