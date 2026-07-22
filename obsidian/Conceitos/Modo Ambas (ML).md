---
tags: [conceito, ml, provedor, multiconta]
aliases: [Ambas, ProvedorMLAmbas, fundir_grupos]
type: concept
---

# 🌐 Modo "Ambas" (ML)

> [!abstract]
> Radio extra no seletor de conta para um **dia de motorista único**: junta as contas
> do ML, **fundindo** grupos de mesmo SKU+qtd numa pilha só, num ZIP único.

## Como funciona
- `ProvedorMLAmbas` coleta as contas **em sequência** e usa `fundir_grupos` (subgrupos em `.por_conta`).
- Imprime cada etiqueta com o **token da conta dela** → [[Token e rotação do refresh]].
- Estado segue **por conta**: `marcar_impresso` roteia com `definir_conta` antes de cada gravação → [[Estado já impresso]].
- Não é persistido no config (escolha pontual).

## Cuidado com anúncio sem SKU
> [!warning]
> No modo Ambas, o botão inline de adoção **RE-COLETA** (`_aplicar_adocao`), **não**
> aplica em memória: os sub-grupos `.por_conta` manteriam a chave antiga do anúncio,
> escondendo envios do lote e marcando estado na chave errada → [[Adoção de anúncios sem SKU]].

## Relacionado
- [[provedores]] · [[Multi-conta (ML)]] · [[Agrupamento e identidade do produto]] · [[Adoção de anúncios sem SKU]]
