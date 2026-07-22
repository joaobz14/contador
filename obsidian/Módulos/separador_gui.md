---
tags: [modulo, gui, tkinter]
aliases: [separador_gui.py, a tela, GUI]
type: modulo
arquivo: separador_gui.py
---

# 🖥️ separador_gui.py — a tela (Tkinter)

> [!abstract] Papel
> A interface: seletor de loja + conta + dia útil, busca, "marcar todos", editores de
> Nomes e SKUs, e o **📋 Resumo do dia**. Fala com o [[Provedor — abstração de marketplace]].

## Regras que a tela garante
- **Gera → confirma → marca**: gera sem marcar, pergunta "saíram certo?", só então marca → [[Confirmação física antes de marcar]].
- **Trava de ponta a ponta**: fica `ocupado` do "Organizar envio" até "saíram certo?" (o `_ocupar(False)` só no `finally`) — anti-duplicata na Shopee.
- **Relê o estado do disco antes de gerar** (`prov.carregar_estado()`) — pendente sobre estado defasado imprimiria em dobro → [[Estado já impresso]].
- **Persiste config por chave** (`atualizar_config(**chaves)`), nunca o dict inteiro → [[Config e saneamento]].

## Editores (instância única, travados na operação)
- **✏ Nomes** (`EditorNomes`, setas ↑/↓) → [[Nomes amigáveis e ordem de separação]]
- **🏷 SKUs** / **🏷 Atribuir SKU** (`EditorSkusAnuncio`) → [[Adoção de anúncios sem SKU]]
- Um 2º clique traz a janela aberta para frente (`_focar_editor_aberto`) — editores de substituição total não mesclam.

## Seletor de dia
Mostra os próximos **dias úteis** com a **contagem por dia** + linha "Outras datas" → [[Dia de despacho]].

## Relacionado
- [[provedores]] · [[separador_etiquetas_ml (núcleo)]] · [[Confirmação física antes de marcar]] · [[Fluxos de operação]]
