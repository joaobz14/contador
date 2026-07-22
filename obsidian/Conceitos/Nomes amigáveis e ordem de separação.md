---
tags: [conceito, sku, gui, ordenacao]
aliases: [nomes_sku, aba Nomes, ordem de separação, EditorNomes]
type: concept
---

# ✏️ Nomes amigáveis e ordem de separação

> [!abstract]
> `nomes_sku.json` mapeia **SKU → nome** e — crucial — a **ordem das chaves é a ordem
> de separação física** do operador. Versionado (sincroniza por Git).

## A ordem é significativa
- **Não** é alfabética: é a sequência em que o operador separa os produtos.
- Define a ordem do bloco **"Quantidade por pedido = 1"** em `ordenar_grupos` → [[Agrupamento e identidade do produto]].
- SKU sem nome cadastrado vai pro fim em ordem **natural**.

## Editor na GUI (`EditorNomes`)
- Botão **✏ Nomes**: buscar, salvar, remover, **reordenar com ↑/↓**.
- Use `carregar_nomes()`/`salvar_nomes()` (apara, descarta vazios; **preserva a ordem**).
- Editor de **substituição total** e **instância única** (travado na operação): um 2º clique traz a janela para frente (`_focar_editor_aberto`), não abre outra que sobrescreveria.

## Liga-se com a adoção
O carimbo de um anúncio adotado vem do nome do SKU aqui → [[Adoção de anúncios sem SKU]].

## Relacionado
- [[Agrupamento e identidade do produto]] · [[Identificação na impressão (carimbo)]] · [[separador_gui]] · [[Arquivos — locais vs versionados]]
