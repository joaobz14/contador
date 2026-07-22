---
tags: [conceito, impressao, estado, invariante]
aliases: [gera confirma marca, saíram certo, confirmação física]
type: concept
---

# ✋ Confirmação física antes de marcar

> [!abstract] A regra de ouro
> A GUI **gera** as etiquetas mas **não marca** o estado. Ela pergunta *"as etiquetas
> saíram certo?"* e **só após o sim** chama `marcar_impresso`. Se a impressora falhar,
> o pedido continua na lista — **nada some**.

## Ordem imutável
```text
gera  →  confirma (usuário)  →  marca
```
Alterar essa ordem fura a **invariante 1**. Vale para ML e Shopee, lote **e**
individual (o individual roteia pelo fluxo do lote).

## Trava de ponta a ponta (anti-duplicata)
O app fica `ocupado` **desde "Organizar envio" até "saíram certo?"** — `_ocupar(False)`
só roda no `finally` de `_confirmar_e_marcar`. Sem isso, na Shopee a etiqueta **já sai
fisicamente na busca** e um 2º clique reimprimiria o mesmo lote. Ver [[separador_gui]].

## Exceção: bot e CLI
Marcam **direto** — não têm como ver a impressora → [[bot_telegram]].

## Relacionado
- [[Estado já impresso]] · [[separador_gui]] · [[provedores]] (sem `imprimir_grupo`) · [[Invariantes críticas]]
