---
tags: [integracao, zebra, downloads, impressao]
type: integration
status: current
aliases: [Zebra, pasta Downloads, impressora térmica, monitor Zebra]
source_files: [separador_etiquetas_ml.py, shopee_api.py]
source_docs: [docs/ARQUITETURA.md]
verified_at_commit: bcab879
---

# 🖨️ Integração: Zebra e pasta Downloads

> [!abstract]
> O app **não** fala com a impressora direto: grava um `.zip` na pasta **Downloads** e um app
> externo (`impressora_zebra_usb.py`, de outro projeto) monitora a pasta e envia à Zebra. A
> **ponte** é o nome do arquivo.

## O contrato (governado pelo app externo)
- **Prefixo** que o monitor casa: `etiqueta de envio` (ML) / `etiqueta shopee` (Shopee).
  **Mudar o prefixo quebra a detecção** — o papel não sai.
- Nome **único** por trabalho (`nome_saida_unico`): determinístico + `replace` apagava em
  silêncio um lote ainda não consumido.
- Temporário `tmp_saida` → `tmp_*.part`: **não pode casar** prefixo nem extensão vigiada
  (`*.zip`/`*.plain`). Teste-guardião `test_tmp_saida_nao_casa_o_que_o_monitor_vigia`.
- App Zebra **v1.25.7** (verificado 20/07/2026): polling 1s; duplicata por
  `nome+tamanho+mtime`; arquivos **em UTF-8** (decode `errors="ignore"`) → não converter.

Detalhe e pegadinhas: [[Ponte com a Zebra]].

## Por que assim
Desacopla o app da impressora (hardware/driver) e permite imprimir de qualquer origem (GUI,
bot, CLI) só soltando o ZIP na Downloads. A Downloads é **por máquina**.

## A etiqueta
ML: ZPL/gráfico da API. Shopee: **ZIP com ZPL (`~DGR/Z64`) dentro** — imprime direto, não
reembrulhar.

## Relacionado
- [[Ponte com a Zebra]] · [[Identificação na impressão (carimbo)]] · [[Escrita atômica de JSON]] · [[Sistemas externos]]
