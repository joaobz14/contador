---
tags: [conceito, ml, sku, agrupamento]
aliases: [skus_por_anuncio, anúncio sem SKU, adoção de anúncio]
type: concept
---

# 🏷️ Adoção de anúncios sem SKU

> [!abstract]
> Anúncios antigos do ML sem `seller_sku` ficavam fora do sistema (identificados pelo
> código do anúncio). O de-para **`skus_por_anuncio.json`** os **adota** num SKU do sistema.

## Como funciona
- `identidade(item, cache, skus_anuncio)` **reescreve a chave** para o SKU adotado (aí agrupa/ordena/carimba/nomeia como os demais). `extrair_itens` carrega o mapa.
- O arquivo é **versionado** (sincroniza por Git) → [[Arquivos — locais vs versionados]].
- O carimbo final vem do **nome do SKU** na aba Nomes: `MLB… → F1AP` (aqui) + `F1AP → "1B"` (em [[Nomes amigáveis e ordem de separação]]).

## Editável na GUI de dois jeitos
- **🏷 Atribuir SKU** (botão inline no grupo sem SKU): **aplica na hora, em memória** (`_aplicar_mapa_anuncios_local` reescreve a chave e **funde** por SKU+qtd, sem re-buscar).
- **🏷 SKUs** (`EditorSkusAnuncio`): **re-coleta** ao fechar (permite remover/editar, que refaz a identidade do zero).

> [!warning] Exceção no modo Ambas
> Lá o botão inline **RE-COLETA** (`_aplicar_adocao`): aplicar local esconderia envios
> do lote e marcaria estado na chave antiga → [[Modo Ambas (ML)]].

## Relacionado
- [[Agrupamento e identidade do produto]] · [[Nomes amigáveis e ordem de separação]] · [[separador_gui]] · [[Modo Ambas (ML)]]
