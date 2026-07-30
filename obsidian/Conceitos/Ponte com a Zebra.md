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

> O app da Zebra é do **mesmo dono** (repo `impressora-zebra-usb`) e desde
> 2026-07-29 tem **teste do contrato do lado dele também** — contrato documentado
> só de um lado é meio contrato.

## Retorno do monitor (desde 2026-07-29)
A entrega é por arquivo e não havia canal de volta: com o monitor fechado, os ZIPs
só se acumulavam e o dono descobria pelo papel que não saía. `aguardar_impressao`
observa dois sinais que o monitor **já produzia**:
- o arquivo **some** (ele apaga após imprimir) → `impresso`;
- o **log dele avança** (`~/zebra_usb_log.txt`) → `imprimindo` (cobre o lote grande,
  em que o ZIP só some na última etiqueta);
- nenhum dos dois → `sem_sinal` (provavelmente fechado).

A tela sabe quais arquivos são dela por **diferença de dois instantâneos**
(`saidas_na_pasta` antes/depois de gerar) — `gerar_zip_lotes` devolve os pendentes,
não o caminho.

> [!warning] Na dúvida, calado
> O monitor varre a cada 1s e pode consumir o ZIP **antes** do 2º instantâneo — aí
> a diferença vem vazia. Nesse caso o veredito é `imprimindo`, **nunca** `impresso`:
> sem ter visto o nosso arquivo sumir, afirmar que ele saiu seria o erro que esta
> tela não pode cometer. Mesma regra se o `exists()` levantar (arquivo preso pelo
> antivírus/OneDrive): responde "ainda está lá".

> [!bug] O ⚠️ exige PROVA (incidente 2026-07-30)
> Um lote de 12 avisou "o monitor NÃO deu sinal" **imprimindo normalmente**; lotes
> pequenos acertavam. Dois fatos somados: em lote grande o arquivo não some dentro
> do teto (só é apagado na última etiqueta) **e** o log não pôde ser lido — e a
> versão anterior colapsava "não sei" e "log parado" num booleano.
> Agora `_mtime_log_monitor` devolve `None` para "não sei" → `sem_saida`
> (silêncio); só log **encontrado e sem avanço** vira `sem_sinal`.
> **Falso alarme é pior que aviso nenhum:** ensina o operador a ignorar o ⚠️, e ele
> perde a utilidade justamente no dia em que estiver certo.

> [!danger] O sinal informa, nunca decide
> Quem responde "as etiquetas saíram corretamente?" continua sendo o operador,
> olhando o papel → [[Invariantes críticas]]. O monitor confirma que **mandou**
> imprimir, não que a etiqueta saiu legível e no lugar.

## Relacionado
- [[Sistemas externos]] · [[Escrita atômica de JSON]] · [[Identificação na impressão (carimbo)]] · [[separador_etiquetas_ml (núcleo)]]
