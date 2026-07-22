---
tags: [integracao, telegram, bot]
type: integration
status: current
aliases: [Telegram, bot do Telegram, Telegram Bot API]
source_files: [bot_telegram.py, relatorio.py]
source_docs: [docs/ARQUITETURA.md]
verified_at_commit: bcab879
---

# 💬 Integração: Telegram

> [!abstract]
> Canal remoto para **consultar** os pedidos (ML **e** Shopee) e **imprimir** (só ML). Roda
> na **máquina onde o bot está** (o ZIP cai na Downloads dela). Código em `bot_telegram.py`.

## O que faz
- **Consulta:** ML e Shopee.
- **Impressão:** **só ML** (invariante 10) — a Shopee exige organizar envio, que o bot não
  conduz com segurança sem ver a impressora.
- **Marca estado direto** (não vê a impressora) — ao contrário da GUI → [[Confirmação física antes de marcar]].

## Segurança
- Responde só aos `chat_ids` autorizados; token via `bot_config.json` (local, não versionado)
  ou `TELEGRAM_BOT_TOKEN`.
- **Redige** o texto antes de mandar ao chat → [[Redação de segredos]].
- **Não imprime grupos antigos** se a conta/loja ativa mudou (invariante 11).

## Comandos
`/hoje` `/amanha` `/dia` `/todos` · `/resumo` · `/detalhar <SKU>` · `/conta` · `/loja` ·
`/id` · `/start` (=`/menu`,`/ajuda`, com botões).

## Onde rodar
No PC do escritório com a Zebra — a impressão sai na Downloads **dessa** máquina.

## Relacionado
- [[bot_telegram]] · [[relatorio]] · [[Redação de segredos]] · [[Zebra e pasta Downloads]] · [[Shopee]]
