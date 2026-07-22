---
tags: [conceito, io, durabilidade, seguranca]
aliases: [gravar_json, escrita atômica, LF, .bak]
type: conceito
---

# 💽 Escrita atômica de JSON

> [!abstract]
> Toda gravação de JSON é **atômica e durável**: `.tmp` + `flush`/`fsync` → `replace`.
> A leitura é **tolerante**. Implementado em [[estado]] (`gravar_json`/`ler_json`).

## Detalhes que já causaram bug
- **`newline="\n"` (LF)** mesmo no Windows: sem isso a GUI reescrevia os JSONs **versionados** (`nomes_sku.json`, `skus_por_anuncio.json`, que o repo mantém em LF via `.gitattributes`) em CRLF — ficavam "modificados" para sempre e colidiam em todo `git pull`.
- **`.bak` de credenciais** com auto-recuperação (queda de energia não exige refazer o token). Só vale **ao lado do principal** → [[Token e rotação do refresh]].
- Estado usa **`ler_estado`**, não `ler_json` (corrupção ≠ ausência) → [[Estado já impresso]].
- O `.tmp` inclui o **PID**; na saída para a Zebra o temporário é `tmp_*.part` (não pode casar prefixo/extensão vigiada) → [[Ponte com a Zebra]].

## Relacionado
- [[estado]] · [[Estado já impresso]] · [[Trava entre processos]] · [[Ponte com a Zebra]]
