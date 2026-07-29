---
tags: [operacao, seguranca, arquivos, invariante]
aliases: [arquivos locais, versionados, gitignore, dois PCs]
type: reference
---

# 🗂️ Arquivos — locais vs versionados

> [!abstract]
> Invariante 12: credenciais, estado, cache e config **são locais e nunca versionados**.
> Só dois JSONs de dados sincronizam por Git.

## Onde ficam: `dados/` e `logs/` (desde 2026-07)
Tudo que o app **lê e escreve** vive em **`dados/`** (inclusive `contas/{nome}/`)
e todo registro em **`logs/`**. A raiz fica só com o que se **abre**
(`separador_gui.py`), os módulos `.py` e o que as ferramentas exigem lá
(`README`/`CLAUDE`/`AGENTS.md`, `.gitignore`, `pyproject.toml`, `ruff.toml`).
Quem vinha da versão antiga não move nada: `migrar_para_pastas()` roda no import
do núcleo e migra sozinho — leva `.bak`/`.corrupto` junto, move `contas/`
inteira, nunca sobrescreve destino existente e nunca derruba a abertura.

> [!warning] Cada movimentação é isolada — e `contas/` vai primeiro
> No Windows o bot sobe no logon pelo Agendador e mantém o `bot.log` **aberto**;
> renomear arquivo aberto levanta `WinError 32`. Enquanto a migração inteira
> rodava sob um único `try/except`, essa falha abortava tudo o que vinha depois
> e a pasta `contas/` ficava na raiz — a tela abria **sem nenhuma conta ML**
> (seletor e modo 🌐 Ambas sumiam). Corrigido em 2026-07-29: `try/except` por
> item e `contas/` na frente da fila, por ser o dado mais caro de refazer
> (exigiria refazer o OAuth). Nada se perde: o que falha fica na raiz e é
> re-tentado na abertura seguinte.

## Versionados (sincronizam entre PCs)
- `dados/nomes_sku.json` — SKU→nome + **ordem de separação** → [[Nomes amigáveis e ordem de separação]]
- `dados/skus_por_anuncio.json` — adoção de anúncios sem SKU → [[Adoção de anúncios sem SKU]]
> Gravados em **LF** (via `gravar_json` com `newline="\n"`) → [[Escrita atômica de JSON]].
> No `.gitignore` a regra é **invertida**: ignora `dados/*` e `logs/` inteiros e
> libera só estes dois — arquivo local novo nunca escapa por esquecimento.

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
