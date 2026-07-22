---
tags: [runbook, oauth, token, setup]
type: runbook
status: current
aliases: [Setup de credenciais, OAuth inicial, pegar token]
source_files: [pegar_token.py, pegar_token_shopee.py]
source_docs: [README.md]
verified_at_commit: bcab879
---

# 🛠️ Runbook: configurar credenciais (OAuth)

> [!abstract]
> Procedimento **único por conta/loja** para gerar as credenciais locais. O app runtime
> nunca refaz isso sozinho — depois usa `obter_token` → [[Token e rotação do refresh]].

## Pré-condições
- App/loja registrados no ML e/ou na Shopee (Shopee exige app **Live** e a Redirect URL
  `https://joaobz14.github.io/contador/`, servida pela pasta `docs/`).
- Python do projeto instalado.

## Mercado Livre (por conta)
```bash
python pegar_token.py
# informe o NOME da conta quando pedir (ex.: cozilatti)
# grava contas/<nome>/credenciais.json (+ .bak)
```
Repita para **cada** conta. Ver [[Multi-conta (ML)]].

## Shopee (loja única)
```bash
python pegar_token_shopee.py
# segue o fluxo OAuth com a Redirect URL do docs/
# grava credenciais_shopee.json (+ .bak)
```

## Critério de sucesso
- O arquivo de credencial existe **e** o app abre/consulta sem erro de token.
- **Nunca** commitar credenciais: são locais e gitignoradas → [[Arquivos — locais vs versionados]].

## Recuperação
- Perdeu o token / conta travada? Ver [[Recuperar estado ou credencial]].
- **Não** restaure um `.bak` desgarrado (refresh já rotacionado, morto) → [[Token e rotação do refresh]].

## Relacionado
- [[pegar_token (OAuth)]] · [[Token e rotação do refresh]] · [[Multi-conta (ML)]]
