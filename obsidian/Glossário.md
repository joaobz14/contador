---
tags: [glossario, referencia]
aliases: [Glossário, Termos]
type: referencia
---

# 📖 Glossário

> [!abstract] Vocabulário do domínio
> Termos que aparecem no código e nas notas. Cada um linka a nota que aprofunda.

- **SKU** — código do produto. Base da identidade e do agrupamento → [[Agrupamento e identidade do produto]].
- **AWB / tracking_number** — código de rastreio da Shopee, emitido **só ao organizar o envio**; é o piso de latência (~14s) → [[Shopee — organizar envio e AWB]].
- **DANFE** — o "documentinho" fiscal do ML onde o app aplica o **carimbo** → [[Identificação na impressão (carimbo)]].
- **ZPL** — linguagem da impressora Zebra. O app **gera** ZPL e o entrega num `.zip` → [[Ponte com a Zebra]].
- **Grupo** — conjunto de envios do **mesmo produto + mesma quantidade** = uma pilha de etiquetas → [[Agrupamento e identidade do produto]].
- **Dia de despacho** — a data em que o pedido deve ser postado; organiza a coleta e o estado → [[Dia de despacho]].
- **Dia de ação** — o momento em que a etiqueta foi **impressa** (carimbo de tempo), base do [[Histórico e resumo do dia]]. **Não** é o dia de despacho.
- **Pendente / parcial / impresso** — os três estados de um grupo → [[Estado já impresso]].
- **Provedor** — a abstração `ProvedorML`/`ProvedorShopee`/`Ambas` com que a GUI fala → [[Provedor — abstração de marketplace]].
- **Modo Ambas** — imprimir várias contas do ML num dia de motorista único → [[Modo Ambas (ML)]].
- **Drop-off / Postagem** — a modalidade de envio que o app usa na Shopee (`ship_order`) → [[Shopee — organizar envio e AWB]].
- **Combo** — pedido com vários SKUs = uma única etiqueta/grupo → [[Agrupamento e identidade do produto]].
- **Carimbo** — identificação impressa na DANFE (SKU ou nome) → [[Identificação na impressão (carimbo)]].
- **`obter_token` / `renovar_token`** — o app **sempre** usa `obter_token` (cache+lock) → [[Token e rotação do refresh]].
- **`estado.trava`** — trava de arquivo entre processos (`.lock`) → [[Trava entre processos]].

## Relacionado
- [[🏠 Home]] · [[Mapa do repositório]]
