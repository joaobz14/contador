---
tags: [conceito, impressao, carimbo, zpl, ml]
aliases: [carimbo, MODO_IDENT, carimbo_nome, divisória, DANFE]
type: concept
---

# 🖋️ Identificação na impressão (carimbo)

> [!abstract]
> No ML, o app carimba a **DANFE** (a etiqueta de envio fica intacta) para o operador
> saber qual produto é. Controlado por `MODO_IDENT`.

## Modos (`MODO_IDENT`)
| Modo | O que sai na DANFE |
|---|---|
| `carimbo` | O **SKU**, centralizado |
| `carimbo_nome` | O **nome** da aba Nomes; fonte adaptativa (`_fonte_nome`); sem nome cai no SKU; 2+ unidades ganham `2x`/`3x` em destaque |
| `divisoria` | Uma página separadora antes de cada lote |
| `nenhuma` | Sem identificação |
`CARIMBAR_SKU` é legado (compat de config antigo).

## Encoding (pegadinha da Zebra)
> [!warning] `^CI28` … `^CI0`
> O nome vai em **UTF-8** e o campo do carimbo é envolto por `^CI28`…`^CI0` (liga só
> antes do `^FD`, reseta logo após o `^FS`). Sem isso os acentos saem embolados. O
> `^CI0` evita o encoding **vazar** para a etiqueta de envio. A `divisoria` também
> fecha com `^CI0` antes do `^XZ`. **Não** converta o nome para CP850 (o app Zebra lê o ZPL como UTF-8).

## Shopee não carimba
A etiqueta Shopee é imagem pronta sem nome → a tela usa o **AWB** → [[Conferência na Shopee (rastreio)]].

## Relacionado
- [[Nomes amigáveis e ordem de separação]] · [[Agrupamento e identidade do produto]] · [[Ponte com a Zebra]] · [[separador_etiquetas_ml (núcleo)]]
