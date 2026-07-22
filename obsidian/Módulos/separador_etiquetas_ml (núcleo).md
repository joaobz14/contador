---
tags: [modulo, ml, nucleo, impressao]
aliases: [separador_etiquetas_ml, núcleo, core]
type: modulo
arquivo: separador_etiquetas_ml.py
---

# 🧠 separador_etiquetas_ml.py — o núcleo

> [!abstract] Papel
> O cérebro do app: fala com a **API do Mercado Livre**, faz o **agrupamento** por
> produto+quantidade, gera o **ZPL** e o **carimbo** na DANFE, e expõe a **CLI**.

## Responsabilidades
- **Coleta ML** (`coletar_grupos`): `buscar_pedidos` → `filtrar_para_imprimir` → `extrair_itens` + `agrupar` (fases **paralelas**).
- **Identidade e agrupamento** → [[Agrupamento e identidade do produto]] (`identidade`, `agrupar`, `ordenar_grupos`, `fundir_grupos`).
- **Geração de ZPL + carimbo** → [[Identificação na impressão (carimbo)]] (`carimbo`, `carimbo_nome`, `_fonte_nome`, `MODO_IDENT`).
- **Saída para a Zebra** → [[Ponte com a Zebra]] (`nome_saida_unico`, `tmp_saida`).
- **Config** → [[Config e saneamento]] (`aplicar_config`, `_sanear_config`, `atualizar_config`).
- **CLI**: `imprimir`, `reimprimir`, `resumo`, `detalhar`, `proximo`, `rastrear`…

## Invariantes que toca
- Marca estado **só** via os helpers de [[estado]] (`status_grupo`, `envios_pendentes`, `marcar_impresso`) — **não** reimplementa o merge.
- Token **sempre** via `obter_token` → [[Token e rotação do refresh]].
- `nome_saida_unico` garante nome **único** por trabalho (evita apagar lote não consumido) → [[Ponte com a Zebra]].

## Desempenho
A fase cara do "Atualizar" é o **filtro** (`GET /shipments/{id}` por pedido não-terminal). Ver [[Desempenho]].

## Relacionado
- [[estado]] · [[historico]] · [[provedores]] · [[separador_gui]] · [[Fluxos de operação]]
