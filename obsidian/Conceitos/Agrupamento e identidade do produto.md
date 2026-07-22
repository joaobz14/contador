---
tags: [conceito, agrupamento, identidade, ml]
aliases: [agrupar, identidade, ordenar_grupos, SKU GTIN variação]
type: concept
---

# 🧬 Agrupamento e identidade do produto

> [!abstract]
> O núcleo transforma pedidos numa lista de **grupos** = mesmo produto + mesma
> quantidade = uma pilha de etiquetas. É o ganho central do app.

## Prioridade de identidade
```text
SKU  →  GTIN + voltagem  →  item_id:variação
```
Anúncios antigos **sem `seller_sku`** caem no código do anúncio e usam o título como
nome — podem ser **adotados** num SKU → [[Adoção de anúncios sem SKU]].

## Agrupamento por envio = 1 etiqueta
Um pedido com vários SKUs (kit/combo) vira **um único grupo "Combo"**, listando os itens.

## Ordem dos grupos (`ordenar_grupos`)
- Ordena por **quantidade primeiro** (blocos "qtd 1", "qtd 2"…).
- **Só no bloco de qtd 1** segue a **ordem da aba Nomes** (a ordem pessoal de separação) → [[Nomes amigáveis e ordem de separação]].
- SKU não cadastrado vai pro fim em ordem **natural** (`A2` antes de `A10`).
- Usado por `agrupar` **e** `fundir_grupos` (→ [[Modo Ambas (ML)]]).

## Relacionado
- [[separador_etiquetas_ml (núcleo)]] · [[Nomes amigáveis e ordem de separação]] · [[Adoção de anúncios sem SKU]] · [[Identificação na impressão (carimbo)]]
