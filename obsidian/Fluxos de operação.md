---
tags: [moc, fluxo]
aliases: [Fluxos, Fluxos de operação]
type: hub
---

# 🔄 Fluxos de operação

> [!abstract]
> Os caminhos operacionais reais (de `docs/ARQUITETURA.md`). Todos terminam na
> **mesma regra de ouro**: só marcar impresso **depois** da confirmação física →
> [[Confirmação física antes de marcar]].

## Fluxo geral de impressão
```text
pedidos prontos → coleta pela API → filtragem por dia de despacho
→ agrupamento (produto × qtd) → ZPL → .zip na pasta Downloads
→ app Zebra detecta → impressora imprime → usuário confirma → marca impresso
```
Conceitos: [[Agrupamento e identidade do produto]] · [[Dia de despacho]] · [[Ponte com a Zebra]] · [[Estado já impresso]]

## Fluxo da GUI (Tkinter)
Escolher marketplace → (se ML) conta → dia → **Atualizar** → a GUI fala com o
**provedor** → separa pendentes/parciais/impressos → selecionar → **gera sem marcar**
→ pergunta "saíram certo?" → só então `marcar_impresso`.
Nota: [[separador_gui]] · [[Provedor — abstração de marketplace]]

## Fluxo Shopee
Listar `READY_TO_SHIP` → detalhes → agrupar → **organizar envio (drop-off / `ship_order`)**
→ emite **AWB** → `create_shipping_document` (exige o AWB) → aguardar `READY` → baixar
etiqueta → combinar ZPLs → ZIP → marcar **só após confirmação**.
Nota: [[shopee_api]] · [[Shopee — organizar envio e AWB]] · [[Conferência na Shopee (rastreio)]]

## Fluxo Mercado Livre "🌐 Ambas"
Coletar cada conta → **fundir grupos** por SKU+qtd (`fundir_grupos`, subgrupos em
`.por_conta`) → baixar cada etiqueta com o **token da conta certa** → **ZIP único** →
estado marcado **por conta** → não persiste "Ambas" como conta ativa.
Nota: [[Modo Ambas (ML)]] · [[Multi-conta (ML)]]

## Fluxo Telegram
Bot carrega config → valida `chat_id` → escolhe loja → **ML: consulta e impressão** /
**Shopee: só consulta** → guarda os grupos no `chat_data` → antes de imprimir valida
que loja/conta não mudaram → imprime na **máquina onde o bot roda** → registra em `bot.log`.
Nota: [[bot_telegram]] (invariantes 10 e 11)

## Relacionado
- [[🏠 Home]] · [[Invariantes críticas]] · [[Sistemas externos]]
