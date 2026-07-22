---
tags: [modulo, bot, telegram]
aliases: [bot_telegram.py, bot do Telegram]
type: modulo
arquivo: bot_telegram.py
---

# 🤖 bot_telegram.py — o bot do Telegram

> [!abstract] Papel
> Consulta os pedidos de qualquer lugar (ML **e** Shopee) e, **no ML**, dispara a
> impressão remota. Formata textos via [[relatorio]].

## Invariantes específicas do bot
> [!warning]
> - **Não imprime grupos da Shopee** — só consulta (invariante 10).
> - **Não imprime grupos antigos** se a conta/loja ativa mudou (invariante 11): valida antes de imprimir.
> - Marca estado **direto** (não tem como ver a impressora) — ao contrário da [[Confirmação física antes de marcar]] da GUI.
> - Imprime na **máquina onde o bot roda** (o ZIP cai no Downloads dela) → rode no PC do escritório com a Zebra.

## Segurança
- Responde só aos `chat_ids` autorizados; token do `bot_config.json` (não versionado) ou `TELEGRAM_BOT_TOKEN`.
- Redige o texto antes de mandar ao chat → [[Redação de segredos]].

## Comandos
`/hoje` `/amanha` `/dia` `/todos` · `/resumo` · `/detalhar <SKU>` · `/conta` · `/loja` · `/id` · `/menu`.

## Relacionado
- [[relatorio]] · [[Estado já impresso]] · [[Fluxos de operação]] · [[Redação de segredos]]
