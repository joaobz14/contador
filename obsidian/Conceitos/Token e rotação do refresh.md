---
tags: [conceito, token, oauth, seguranca, concorrencia]
aliases: [obter_token, renovar_token, refresh token, rotação de token]
type: conceito
---

# 🔑 Token e rotação do refresh

> [!abstract]
> ML e Shopee usam OAuth com **`refresh_token` que rotaciona**: cada renovação gera um
> novo e **invalida o anterior**. Uma corrida de renovação pode **travar a conta**.

## Regra absoluta
> [!danger] Sempre `obter_token(cred)`, nunca `renovar_token` direto
> `obter_token` faz cache + lock double-checked. `renovar_token` **não re-tenta**
> (`tentativas=1`): re-tentar após o servidor já ter rotacionado gastaria um token de uso único.

## Serialização em duas camadas (invariantes 6 e 7)
- **Threads**: lock de thread (double-checked).
- **Processos** (GUI + bot na mesma conta): [[Trava entre processos]] no arquivo de credenciais, com **`espera=2*TIMEOUT`**. Quem chega depois **espera, relê o disco** (`_ler_json(ARQUIVO_CRED)`) e **adota** o token salvo pelo primeiro — nunca dois refreshes em paralelo.

## Por que a espera estendida
No Windows o `LK_LOCK` desiste sozinho em ~10s; o refresh dura até 30s. Sem a espera
de `2*TIMEOUT`, o 2º processo degradaria **no meio** do refresh do 1º e renovaria de
novo — rotacionando por cima.

## Credenciais
Locais, com espelho **`.bak`** (auto-recuperação). O `.bak` só vale **ao lado do
principal** — um desgarrado tem refresh já rotacionado (morto) → [[Arquivos — locais vs versionados]].

## Relacionado
- [[pegar_token (OAuth)]] · [[Trava entre processos]] · [[Multi-conta (ML)]] · [[Invariantes críticas]]
