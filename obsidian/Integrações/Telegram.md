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
`/conta` · `/loja` · `/id` · `/versao` · `/perguntas` (ver abaixo) · `/start`
(=`/menu`,`/ajuda`, com botões).

O menu "/" do app é publicado por `setMyCommands` **no escopo de cada chat**
(`BotCommandScopeChat`), nunca no global — no global a lista de comandos
apareceria para qualquer estranho que abrisse o bot. O `setMyCommands`
**substitui a lista inteira**: comando novo tem de entrar em `COMANDOS_MENU`,
senão some do menu.

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
- **Shopee: "Enviar NF-e"** (`invoice_data.status == "pending"`) — o espelho
  **invertido** do ML: a venda não some, ela já aparecia como *pronta*, e a
  Shopee **recusa organizar o envio** enquanto a nota não subir. Agora vem em
  aviso separado. `pending` sozinho é o estado de toda venda nova, então o que
  distingue é o **dia** — e como o prazo demora a ser atribuído, ele é derivado
  de `pay_time + days_to_ship` quando falta.
- **Alerta também de "Informe a NF-e"** (`invoice_pending`, ML): venda de item
  **sem estoque** não recebe o XML do faturador e nunca chega a `ready_to_print`
  — era a única invisível, e a que mais precisa de aviso. Vem num aviso separado
  (rótulo `· falta NF-e`), com dedup próprio, e **não entra em lote de impressão
  nenhum** (o ML não libera a etiqueta). Diagnóstico do nome do substatus:
  `python separador_etiquetas_ml.py substatus`.
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

> [!warning] Reiniciar: use `atalhos\Reiniciar Bot.bat`
> O par `schtasks /end` + `/run` **não reiniciava nada** (incidente 2026-08-04):
> o lançador subia o `.bat` sem `-Wait`, a tarefa era dada por terminada e o bot
> ficava **órfão** — o `/end` não matava nada e o `/run` subia um **segundo**
> bot; os dois brigavam pelo `getUpdates` e o **antigo** continuava respondendo.
> O script novo derruba o que estiver de pé (lançador primeiro) e sobe um só.

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

## Integrações do n8n (`/perguntas`, `/anuncios`)
Comandos que o bot **dispara** e o n8n responde. Um fluxo por comando, uma linha
na tupla `INTEGRACOES` + a URL no `bot_config.json` — menu, botão, autorização e
tratamento de erro saem de graça.

| Comando | O que devolve |
|---|---|
| `/perguntas` | perguntas e mensagens sem resposta (conta 3) |
| `/anuncios` | saúde dos anúncios das **duas** contas, numa resposta só |

## `/perguntas` — o bot dispara, o **n8n** responde
Um fluxo do **n8n** (fora deste projeto) lista as perguntas e mensagens sem
resposta da **conta 3**. O `/perguntas` só **aciona** esse fluxo: faz um POST no
webhook (levando o `chat_id` de quem disparou, para o fluxo responder a quem
perguntou em vez de a um chat fixo), manda um "🔎 Consultando..." na hora e sai
de cena — a **resposta chega
alguns segundos depois, escrita pelo próprio n8n** no mesmo chat. Também há o
botão **🔎 Perguntas** no `/menu`.

> [!important] Dois sistemas, um bot só — e por isso o polling não pode mudar
> O Telegram entrega os updates de um bot a **um consumidor só**. Quem **lê** os
> comandos é este projeto (polling, em `main`); o n8n entra apenas como
> **remetente** (`sendMessage`), sem ler nada. Trocar o polling por webhook aqui
> derrubaria um dos dois lados.

> [!warning] O endereço do webhook é uma credencial
> O webhook não pede token nem cabeçalho: **quem tem o link dispara o fluxo** (por
> isso o caminho leva um sufixo aleatório). Ele mora no `bot_config.json`
> (`webhook_perguntas`) ou na variável `N8N_WEBHOOK_PERGUNTAS` — **nunca no
> código**, que é público — e não entra em texto de erro nenhum. Ver
> [[Redação de segredos]].

Restrito a **um** chat (`chat_perguntas` no `bot_config.json`), não à whitelist
inteira: o comando fala de uma conta específica do dono. De qualquer outro chat é
ignorado **em silêncio** — responder "não autorizado" já confirmaria que o comando
existe. Sem as duas chaves configuradas, o comando fica desligado e explica o que
falta a quem está autorizado.

## Contrato com o n8n (para as próximas integrações)
Fechado com o outro lado em 04/08/2026, antes de existir a 2ª função:

| Ponto | Acordo |
|---|---|
| `chat_id` | O n8n responde ao chat que vier no corpo. **A autorização é deste lado** — só vai para o POST um chat já autorizado. |
| Webhook | **Um por fluxo**, não roteador. Uma chave de config por comando (passando de ~3, virar bloco `webhooks: {}`). |
| Botões | O n8n **não** manda teclado. Toque em botão vira `callback_query`, que vai para o polling daqui — botão exige handler nosso. |
| Parâmetro | Campo `args`, string crua com trim, `""` quando não houver. |
| Quantidade | Um comando por função até ~5; submenu só depois. |
| Fluxo caro | Ads leva ~5 min e **gasta dinheiro**: aviso explícito de demora, restrito ao chat do dono, e limite de frequência **persistido em arquivo** (em memória zeraria a cada `/atualizar`). |

## `/atualizar` — atualizar do celular
`git pull` + reinício sem estar no PC. Responde o que aconteceu ("já estava na
versão mais nova" / "atualizado: `abc` → `def`") e, quando volta, um "✅ Voltei".

**Como reinicia:** o bot roda sob o `Iniciar Bot (auto).bat`, que é um **laço** —
se o processo morre, ele sobe de novo 15s depois. Então o comando só **sai**; não
dispara processo nenhum (nada de `schtasks` daqui, que é o terreno do WinError 6
→ ver o histórico abaixo). Se o bot tiver sido aberto na mão (sem o lançador), ele
**não sai**: atualiza e manda reiniciar no PC — bot mudo é pior que bot
desatualizado.

> [!warning] O que ele nunca faz
> - **Não mexe em alteração local.** `nomes_sku.json`/`skus_por_anuncio.json` são
>   versionados **e** editados pela tela: com alteração não commitada ele não puxa
>   nada e lista os arquivos. Nada de `stash`/`reset` automático em cima da ordem
>   de separação e dos nomes que o dono digitou.
> - **Não atropela impressão.** Pega a `TRAVA_CONTA` sem esperar; ocupado responde
>   "tente em instantes" — o reinício não pode cair entre gerar o ZIP e marcar o
>   estado ([[Invariantes críticas|invariante 1]]).
> - **Não faz merge.** `git pull --ff-only`: sem fast-forward há commit local, e
>   isso pede um humano.

A **tela** não é atualizada por ele — continua na versão antiga até fechar e abrir.

## Onde rodar
No PC do escritório com a Zebra — a impressão sai na Downloads **dessa** máquina.

## Relacionado
- [[bot_telegram]] · [[relatorio]] · [[Redação de segredos]] · [[Zebra e pasta Downloads]] · [[Shopee]]
