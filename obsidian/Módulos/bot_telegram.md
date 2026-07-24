---
tags: [modulo, bot, telegram]
aliases: [bot_telegram.py, bot do Telegram]
type: module
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
`/hoje` `/amanha` `/dia` `/todos` · `/resumo` · `/vendasapos` · `/detalhar <SKU>` ·
`/conta` · `/loja` · `/id` · `/menu`.

## Alerta pós-horário (`job_alerta_pos_horario`)
A cada 5 min, percorre **todas** as contas (`core.listar_contas()`) e avisa — uma vez
por envio — quando surge um envio novo já `ready_to_print` com despacho **hoje**.
Independente do botão Atualizar da tela. `_dados_alerta_da_conta` faz a checagem e o
detalhe dos itens **num só bloco de troca de conta** (`definir_conta` mexe em globais
compartilhadas com o resto do bot — separar em duas chamadas arriscaria a 2ª rodar já
com a conta original restaurada pela 1ª). Dedup por `shipment_id` em
`alertas_pos_horario.json` (gitignorado, reseta sozinho na virada do dia); o mesmo
arquivo também guarda os itens (`chave`+`quantidade`) de cada aviso, usados pelo
`/vendasapos`. Mensagem por SKU somado (`A01 - 2L 110 - 1`), sem número de envio. O
bot sobe sozinho no login do Windows (Agendador de Tarefas,
`atalhos/registrar-tarefa-bot.ps1`) — o alerta só funciona com o bot rodando. →
[[Telegram]] pro histórico de por que não é mais a tela quem sobe o bot.

## Resumo agregado (`/vendasapos`)
Junta tudo que o alerta já avisou hoje (todas as contas) numa mensagem só, com um
TOTAL por SKU no final — evita poluir o chat quando várias vendas caem em sequência
depois das 8:30. Só relê `alertas_pos_horario.json`, não refaz chamada de API.

## Relacionado
- [[relatorio]] · [[Estado já impresso]] · [[Fluxos de operação]] · [[Redação de segredos]] · [[Telegram]]
