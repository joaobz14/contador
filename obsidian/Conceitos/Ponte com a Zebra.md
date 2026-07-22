---
tags: [conceito, impressao, zebra, zpl, downloads]
aliases: [pasta Downloads, nome_saida_unico, tmp_saida, monitor Zebra]
type: concept
---

# 🖨️ Ponte com a Zebra (pasta Downloads)

> [!abstract]
> O app **não** fala com a impressora direto: grava um `.zip` na pasta **Downloads** e
> um app externo (`impressora_zebra_usb.py`) monitora a pasta e imprime. Ver [[Sistemas externos]].

## O contrato do nome do arquivo
- **Prefixo** que o monitor casa: `etiqueta de envio` (ML) / `etiqueta shopee` (Shopee). **Mudar o prefixo quebra a detecção** — o papel não sai.
- O resto é livre, mas precisa ser **único** por trabalho: `nome_saida_unico` (carimbo de tempo + `-1`,`-2`… na colisão). Nome determinístico + `replace` apagava em silêncio um lote que o monitor ainda não consumira.
- Temporário `tmp_saida` → `tmp_*.part`: **não pode casar** prefixo nem extensão vigiada (`*.zip`/`*.plain`). Teste-guardião `test_tmp_saida_nao_casa_o_que_o_monitor_vigia`.

## Antes de gerar
A GUI **relê o estado do disco** (`prov.carregar_estado()`) — pendente sobre estado
defasado imprimiria em dobro o que foi marcado por fora (CLI/2ª GUI) → [[Estado já impresso]].

## Contrato do app Zebra (v1.25.7, verificado 20/07/2026)
Polling de 1s; aceita `*.zip` (prefixos) e `*.plain` (DANFE); **duplicata** por
`nome+tamanho+mtime` (nomes únicos nunca colidem); arquivos **devem estar em UTF-8**
(decode `errors="ignore"`) → não converter → [[Identificação na impressão (carimbo)]].

## Relacionado
- [[Sistemas externos]] · [[Escrita atômica de JSON]] · [[Identificação na impressão (carimbo)]] · [[separador_etiquetas_ml (núcleo)]]
