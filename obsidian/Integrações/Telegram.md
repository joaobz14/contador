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

## Jobs automáticos (`JobQueue`)
- **Aviso da manhã** (`job_bom_dia`, 1x/dia, `aviso_horario` no `bot_config.json`).
- **Alerta pós-horário** (`job_alerta_pos_horario`, a cada 5 min): motivado por venda
  que cai depois das 8:30 e passa despercebida até ser tarde pra repor com o
  fornecedor. Percorre **todas** as contas e avisa — uma vez por envio — quando surge
  um envio novo já `ready_to_print` com despacho **hoje**. Independente do botão
  Atualizar da tela; dedup por `shipment_id` em `alertas_pos_horario.json` (reseta
  sozinho no dia seguinte). Isola falha por conta.

## Sobe sozinho com a tela
`separador_gui.py`, ao abrir, chama `core.iniciar_bot_em_segundo_plano()` — sobe o
bot sem janela visível (via `atalhos/'Iniciar Bot (auto).bat'`) **se ainda não
estiver rodando** (lock de PID em `bot.lock`, checado contra o processo de verdade).
O alerta pós-horário só funciona com o bot de pé; isso evita esquecer de ligá-lo à
parte. Decisão do dono: atrelado à abertura da tela (fica aberta o dia todo), não
sempre-ligado via Agendador de Tarefas.

## Onde rodar
No PC do escritório com a Zebra — a impressão sai na Downloads **dessa** máquina.

## Relacionado
- [[bot_telegram]] · [[relatorio]] · [[Redação de segredos]] · [[Zebra e pasta Downloads]] · [[Shopee]]
