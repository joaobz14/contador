---
tags: [conceito, provedor, arquitetura]
aliases: [Provedor, abstração de marketplace, self.prov]
type: conceito
---

# 🔌 Provedor — abstração de marketplace

> [!abstract]
> A GUI fala com `self.prov` (ML, Shopee ou Ambas), **nunca** com `if marketplace`.
> Toda capacidade nova de impressão/coleta entra como **método do provedor**.

## Por que
Isola a GUI das diferenças entre marketplaces. A GUI consulta status/pendentes **via
provedor** (`prov.status_grupo`, `prov.carregar_estado`), não o core direto.

## Deliberadamente sem `imprimir_grupo`
Não existe um método de grupo que marque estado direto — seria uma arma engatilhada
contra a [[Confirmação física antes de marcar]]. Teste-guardião
`test_provedores_nao_expoe_imprimir_grupo`.

## Implementações
`ProvedorML` · `ProvedorShopee` · `ProvedorMLAmbas` (→ [[Modo Ambas (ML)]]). Ver [[provedores]].

## Relacionado
- [[provedores]] · [[separador_gui]] · [[Modo Ambas (ML)]] · [[Confirmação física antes de marcar]]
