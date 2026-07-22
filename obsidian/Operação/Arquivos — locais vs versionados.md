---
tags: [operacao, seguranca, arquivos, invariante]
aliases: [arquivos locais, versionados, gitignore, dois PCs]
type: operacao
---

# 🗂️ Arquivos — locais vs versionados

> [!abstract]
> Invariante 12: credenciais, estado, cache e config **são locais e nunca versionados**.
> Só dois JSONs de dados sincronizam por Git.

## Versionados (sincronizam entre PCs)
- `nomes_sku.json` — SKU→nome + **ordem de separação** → [[Nomes amigáveis e ordem de separação]]
- `skus_por_anuncio.json` — adoção de anúncios sem SKU → [[Adoção de anúncios sem SKU]]
> Gravados em **LF** (via `gravar_json` com `newline="\n"`) → [[Escrita atômica de JSON]].

## Locais de cada máquina (NÃO versionados)
| Arquivo | Uso | Segredo? |
|---|---|---|
| `credenciais.json` (+ `.bak`) | token ML, por conta | **Sim** |
| `credenciais_shopee.json` | token Shopee, loja única | **Sim** |
| `estado_grupos.json` / `estado_shopee.json` | [[Estado já impresso]] | Não |
| `config.json` | preferências → [[Config e saneamento]] | Não |
| `bot_config.json` | token do bot | **Sim** |
| `itens_cache.json` / `envios_cache.json` | caches ML | Não |
| `awb_cache_shopee.json` | AWB cacheado → [[Conferência na Shopee (rastreio)]] | Não |
| `historico_impressao.json` | [[Histórico e resumo do dia]] | Não |
| `bot.log` / `separador.log` / `*_tempos.log` | logs | Não |
| `*.corrupto` | estado ilegível preservado por `ler_estado` | Não |

> [!warning] O `.bak` só vale ao lado do principal
> Um `.bak` desgarrado guarda um `refresh_token` **já rotacionado** (morto). Nunca
> restaurá-lo para outra pasta → [[Token e rotação do refresh]].

## Dois PCs (escritório e casa)
Cada PC tem seu clone (`git pull`). **Sincroniza:** os dois JSONs versionados.
**Fica local:** credenciais, estado, caches, logs.

## Relacionado
- [[Invariantes críticas]] · [[Escrita atômica de JSON]] · [[Token e rotação do refresh]] · [[Sistemas externos]]
