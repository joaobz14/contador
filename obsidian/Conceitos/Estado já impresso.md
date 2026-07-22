---
tags: [conceito, estado, concorrencia, invariante]
aliases: [Estado de impresso, já impresso, pendente parcial impresso]
type: conceito
---

# 📦 Estado "já impresso"

> [!abstract]
> Controla o que **já foi impresso**, para não imprimir em dobro. É **por marketplace +
> conta + dia de despacho**. A lógica é única em [[estado]].

## Chave e escopo
- Chave: `{dia}|{chave}|q{qtd}` (`chave_estado`).
- ML → `contas/{conta}/estado_grupos.json`; Shopee → `estado_shopee.json`.
- Três status: **pendente / parcial / impresso** (`status_grupo`). Um **envio novo** em grupo impresso o **reabre como parcial** (invariante 4).

## Regras que o protegem
- Marca **só após confirmação** → [[Confirmação física antes de marcar]] (invariante 1).
- **Reimpressão nunca altera** o estado (invariante 2).
- `marcar_impresso` faz **ler → mesclar → salvar** sob [[Trava entre processos]] (invariante 5) — GUI e bot não apagam a marcação um do outro.
- **Poda por idade** (`carregar(persistir_poda=True)`, ML **e** Shopee) relê o disco antes de gravar (mesma corrida por porta lateral).

## Cuidado ao ler
> [!danger] `ler_estado`, nunca `ler_json`
> Corrompido lido como `{}` faria todos os grupos voltarem a PENDENTE e a próxima
> marcação gravaria por cima. `ler_estado` move o corrompido para `.corrupto` sem
> apagar o antigo. Ver [[estado]].

## Não confundir com histórico
O estado é por **dia de despacho** e **não** guarda *quando* imprimiu. "O que imprimi
hoje" vem do [[Histórico e resumo do dia]] (por **dia de ação**).

## Relacionado
- [[estado]] · [[Trava entre processos]] · [[Confirmação física antes de marcar]] · [[Dia de despacho]] · [[Invariantes críticas]]
