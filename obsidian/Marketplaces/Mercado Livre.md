---
tags: [marketplace, ml, hub]
type: marketplace
status: current
aliases: [Mercado Livre, ML, ML API]
source_files: [separador_etiquetas_ml.py, provedores.py]
source_docs: [docs/ARQUITETURA.md]
verified_at_commit: bcab879
---

# 🟡 Mercado Livre

> [!abstract]
> Marketplace principal. Suporta **várias contas**, carimba a **DANFE** para identificar o
> produto, e tem o modo **Ambas** (imprimir todas as contas num dia único). Núcleo em
> `separador_etiquetas_ml.py`.

## Especificidades
- **Multi-conta:** credenciais e estado isolados em `contas/{nome}/`; `definir_conta` troca
  os globais → [[Multi-conta (ML)]].
- **Modo Ambas:** funde grupos de mesmo SKU+qtd entre contas, imprime cada um com o token da
  conta certa → [[Modo Ambas (ML)]].
- **Identificação:** carimbo na DANFE (SKU ou nome), sem tocar a etiqueta de envio →
  [[Identificação na impressão (carimbo)]].
- **Anúncios sem SKU:** adotados num SKU do sistema → [[Adoção de anúncios sem SKU]].
- **Desempenho:** a fase cara do "Atualizar" é o filtro de envios (`GET /shipments/{id}`) →
  [[Desempenho]].

## API (sistema externo)
OAuth com `refresh_token` que **rotaciona** → sempre `obter_token` → [[Token e rotação do refresh]].
Fornece pedidos, detalhes, envios e etiquetas ZPL. Ver [[Sistemas externos]].

## Relacionado
- [[separador_etiquetas_ml (núcleo)]] · [[Multi-conta (ML)]] · [[Modo Ambas (ML)]] · [[Identificação na impressão (carimbo)]] · [[Shopee]]
