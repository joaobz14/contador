---
tags: [modulo, token, oauth, setup]
aliases: [pegar_token.py, pegar_token_shopee.py, OAuth inicial]
type: modulo
arquivo: pegar_token.py / pegar_token_shopee.py
---

# 🔑 pegar_token — configuração inicial (OAuth)

> [!abstract] Papel
> Scripts de **setup** (uma vez por conta/loja) que rodam o OAuth e gravam as
> credenciais. `pegar_token.py` (ML, por conta) e `pegar_token_shopee.py` (Shopee, loja única).

## Fluxo
- **ML**: `python pegar_token.py` → pede o nome da conta → salva em `contas/{nome}/credenciais.json`. Repita por conta.
- **Shopee**: `python pegar_token_shopee.py` → precisa do app **Live** e da Redirect URL `https://joaobz14.github.io/contador/` (servida pela pasta `docs/`).

## Depois do setup
O app runtime **nunca** chama `renovar_token` direto — usa `obter_token` → [[Token e rotação do refresh]].
As credenciais são **locais, com espelho `.bak`**, nunca versionadas → [[Arquivos — locais vs versionados]].

## Relacionado
- [[Token e rotação do refresh]] · [[Multi-conta (ML)]] · [[Sistemas externos]]
