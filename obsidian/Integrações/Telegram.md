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
`/hoje` `/amanha` `/dia` `/todos` · `/resumo` · `/vendasapos` · `/detalhar <SKU>` ·
`/conta` · `/loja` · `/id` · `/start` (=`/menu`,`/ajuda`, com botões).

## Jobs automáticos (`JobQueue`)
- **Aviso da manhã** (`job_bom_dia`, 1x/dia, `aviso_horario` no `bot_config.json`).
- **Alerta pós-horário** (`job_alerta_pos_horario`, a cada 5 min, das **07:00 às
  20:59** de Brasília — fora disso é no-op sem chamada de API; busca ML com janela
  dedicada de **5 dias** em vez dos 30 do Atualizar — juntas, as duas janelas
  cortaram ~95% das chamadas que o alerta fazia, auditoria de APIs 2026-07):
  motivado por venda
  que cai depois das 8:30 e passa despercebida até ser tarde pra repor com o
  fornecedor. Percorre **todas** as contas ML **e também a Shopee** (loja única) e
  avisa — uma vez por envio/pedido — quando surge algo novo já pronto pra despachar
  **hoje** (`ready_to_print`+`expected_date` no ML, `READY_TO_SHIP`+`ship_by_date`
  na Shopee — sinais equivalentes; `shopee_api.pedidos_prontos_novos` é o par Shopee
  de `filtrar_para_imprimir`+`extrair_itens`). A checagem da Shopee **pula em
  silêncio** se não houver `credenciais_shopee.json` (setup só-ML continua válido).
  Independente do botão Atualizar da tela; dedup em `alertas_pos_horario.json` (reseta
  sozinho no dia seguinte) — por `shipment_id` no ML, por `order_sn` na Shopee
  (tratada como mais uma chave, `"Shopee"`). Isola falha por conta/loja — envio e
  persistência compartilhados entre ML e Shopee via `_disparar_alerta` (não duplica
  essa lógica). Mostra SKU + quantidade **somada por SKU** (`A01 - 2L 110 - 1`), sem
  número de envio/pedido — pedido do dono, só precisa saber O QUE repor. Cada
  disparo também persiste os itens no mesmo arquivo (junto do dedup), que alimenta
  o `/vendasapos` abaixo.
- **Testar na hora** (sem esperar os 5 min nem uma venda nova):
  `python bot_telegram.py testar-alerta` (ou `atalhos/'Testar Alerta
  Pos-Horario.bat'`) — monta um `Application` de verdade e chama o job uma
  única vez, fora do agendamento.

## Resumo agregado (`/vendasapos`)
Se várias vendas caírem em sequência depois das 8:30, cada uma vira um alerta
separado — poluindo o chat. `/vendasapos` (comando e botão "🔔 Vendas após" no
`/menu`) junta **tudo que já foi avisado hoje**, por conta/loja (ML e Shopee), com
um TOTAL por SKU no final. Só relê `alertas_pos_horario.json` (os itens que o
alerta já persistiu), não refaz nenhuma chamada de API.

## Sobe sozinho no login do Windows
O alerta pós-horário só funciona com o bot de pé, e é fácil esquecer de ligá-lo
à parte. Rode **uma vez** `atalhos\registrar-tarefa-bot.ps1` — registra uma
tarefa no Agendador de Tarefas do Windows (gatilho `AtLogOn` do usuário atual)
que sobe `atalhos\'Iniciar Bot (auto).bat'` sem janela visível a cada login,
independente da tela (`separador_gui.py`) estar aberta. Sem lock de PID: uma
duplicata eventual (ex.: tarefa do login + clique manual no `.bat`) é
autolimitada pelo próprio Telegram (erro 409 ao pollar duas instâncias do
mesmo bot).

> [!bug] Histórico: por que não é mais a tela quem sobe o bot
> A 1ª versão fazia `separador_gui.py` subir o bot sozinho ao abrir (lock de
> PID em `bot.lock`, checado via `tasklist`). Dois bugs reais de **mesma
> causa-raiz** apareceram testando na máquina do dono: a tela roda via
> `pythonw` (sem console) — qualquer `subprocess` disparado dali herda
> handles de stdin/stdout/stderr inválidos. Achado 1: sem
> `stdin=subprocess.DEVNULL`, o `tasklist` que checava o PID falhava sempre
> com `WinError 6`, travando o auto-start pra sempre com um lock preso.
> Achado 2 (corrigido o 1º): faltava redirecionar `stdout`/`stderr` também —
> um `print()` em `bot_telegram.py`, fora do `try/finally` que limpava o
> lock, derrubava o processo ao herdar um stdout inválido, deixando o lock
> preso de novo e fazendo a tela subir outro bot por cima em loop, sem
> nenhum chegar a `app.run_polling()`. Corrigir cada sintoma não resolvia a
> causa — qualquer processo nascido de `pythonw` nasce nesse terreno
> minado. Solução: trocar de mecanismo (Agendador de Tarefas, processo
> criado do zero pelo Windows) em vez de seguir caçando o próximo achado.
> Todo o código do lock de PID foi removido.

## Onde rodar
No PC do escritório com a Zebra — a impressão sai na Downloads **dessa** máquina.

## Relacionado
- [[bot_telegram]] · [[relatorio]] · [[Redação de segredos]] · [[Zebra e pasta Downloads]] · [[Shopee]]
