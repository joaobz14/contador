---
tags: [decisao, historico, impressao, pdf]
type: decision
status: current
aliases: [Decisão resumo PDF, PDF soma por produto, por que PDF]
source_files: [historico.py, separador_gui.py]
source_docs: [docs/CHANGELOG.md, docs/PRIORIDADES_TECNICAS.md]
verified_at_commit: bcab879
---

# 🧭 Decisão: resumo do dia impresso como PDF com a soma por produto

> [!abstract]
> **Decisão:** a impressão do resumo do dia é um **PDF consolidado por SKU** (soma de
> todas as contas ML + Shopee), na ordem da aba Nomes — não o detalhado por marketplace,
> nem `.txt`. **Estado:** implementada (v1).

## Contexto
O operador precisa de uma **lista de produção/separação**: "quantas unidades de cada
produto preparar hoje", independentemente de qual marketplace/conta gerou o pedido. A
tela já mostra o detalhado por marketplace (útil para auditar), mas para **imprimir e
separar** o que importa é a soma por produto.

## Alternativas consideradas
- **Imprimir o detalhado em `.txt`** (via Bloco de Notas): descartado — o `.txt` impresso
  **gasta folha à toa** (fonte grande, quebra ruim) e mistura marketplaces.
- **Imprimir na própria Zebra** (etiqueta térmica): descartado para v1 — largura estreita,
  lista longa vira uma etiqueta comprida; o alvo é a impressora A4 comum.
- **Depender de uma biblioteca de PDF** (reportlab/fpdf): descartado — exigiria instalar
  dependência na máquina de operação. O PDF é gerado em **Python puro** (`gerar_pdf`,
  Helvetica/WinAnsiEncoding).

## Motivo
Soma por produto = a informação acionável para separar. PDF = compacto, controlado,
imprime bem. Python puro = zero fricção de instalação.

## Consequências
- Duas saídas na `JanelaResumo`: **PDF (soma por produto)** e **Detalhado (.txt)**.
- A ordem segue a aba Nomes (`resumo_do_dia(ordem=…)`) → [[Nomes amigáveis e ordem de separação]].
- **Reimpressão manual não entra** no resumo (não passa por `marcar_impresso`) — decisão
  de v1, registrada no backlog (`docs/PRIORIDADES_TECNICAS.md` #9). Incluir depois exigiria
  chamar `historico.registrar` também no caminho de reimpressão.

## Relacionado
- [[Resumo do dia]] · [[Histórico e resumo do dia]] · [[historico]]
