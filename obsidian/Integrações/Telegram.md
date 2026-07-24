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

> [!bug] Achado real: auto-start travava pra sempre
> Testando na máquina do dono, o bot funcionava manual mas nunca subia sozinho, sem
> erro no log. Causa: a tela roda via `pythonw` (sem console) — sem
> `stdin=subprocess.DEVNULL`, o `tasklist` que checa o PID falhava com `WinError 6`,
> e o default antigo "em dúvida assume vivo" fazia um `bot.lock` travado bloquear o
> auto-start **para sempre**. Corrigido com `stdin=DEVNULL` + default invertido pra
> "em dúvida assume morto" (duplicar é autolimitado pelo próprio Telegram, erro 409;
> travar pra sempre é pior). `iniciar_bot_em_segundo_plano()` agora devolve o motivo
> (`subiu`/`ja_rodando`/`nao_windows`/`bat_ausente`), sempre logado pela tela.
>
> **Achado 2 (mesma causa-raiz):** mesmo com o `stdin` corrigido, o log mostrava
> "subiu" duas vezes seguidas (a tela aberta de novo achava que o bot não estava
> rodando) e o bot nunca respondia no Telegram. Causa: o `Popen` que sobe o `.bat`
> só redirecionava `stdin`, não `stdout`/`stderr` — o `print("Bot rodando...")` em
> `bot_telegram.py`, fora do `try/finally` que limpa o lock, derrubava o processo
> ao escrever num stdout inválido herdado do `pythonw`, logo após gravar
> `bot.lock`. O lock ficava preso num PID já morto; a tela seguinte via
> `bot_ja_rodando()==False` e subia outro bot por cima, em loop, sem nunca chegar
> a `app.run_polling()`. Corrigido com `stdout=DEVNULL, stderr=DEVNULL` no mesmo
> `Popen` (o log de verdade já vai pro arquivo).

## Onde rodar
No PC do escritório com a Zebra — a impressão sai na Downloads **dessa** máquina.

## Relacionado
- [[bot_telegram]] · [[relatorio]] · [[Redação de segredos]] · [[Zebra e pasta Downloads]] · [[Shopee]]
