---
tags: [conceito, data, ml, shopee, gui]
aliases: [dia de despacho, dias úteis, contagem por dia]
type: conceito
---

# 📅 Dia de despacho

> [!abstract]
> A data em que o pedido deve ser postado. Organiza a **coleta**, o **seletor da GUI**
> e a **chave do estado** → [[Estado já impresso]].

## Na GUI
- Mostra os próximos **dias úteis** (`proximos_dias_uteis()` + `rotulo_dia()`) e passa a data como `dia=` (ML e Shopee filtram igual; `dia=""` = sem data).
- Após um Atualizar, o provedor preenche `contagem_dias` (`{data: n}`, da MESMA busca) → o seletor mostra a **contagem por dia** + linha **"Outras datas"** (fim de semana/atrasadas/sem data). **Nenhum pedido fica invisível.**

## Cuidado: "Sem data" reabre na virada do dia
O fallback `grupo.dia or hoje` foi desenhado para o "hoje implícito" de CLI/bot; o
radio **Sem data** (`dia=""`) o herdou. Um pedido sem prazo impresso hoje e pronto
amanhã reaparece como pendente (nada some). Caso raríssimo — decisão documentada.

## Vs. dia de ação
Estado usa **dia de despacho**; o [[Histórico e resumo do dia]] usa **dia de ação** (impressão).

## Relacionado
- [[Estado já impresso]] · [[Fuso de Brasília]] · [[separador_gui]] · [[Histórico e resumo do dia]]
