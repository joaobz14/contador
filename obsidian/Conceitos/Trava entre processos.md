---
tags: [conceito, concorrencia, estado, seguranca]
aliases: [estado.trava, lock, trava de arquivo]
type: concept
---

# 🔒 Trava entre processos (`estado.trava`)

> [!abstract]
> Um lock de **arquivo** (`.lock` ao lado do alvo, gitignorado) que serializa
> **processos** diferentes — tipicamente a **GUI** e o **bot** na mesma conta.

## Onde protege
- **`marcar_impresso`**: o ciclo ler→mesclar→salvar roda sob a trava; sem ela, duas leituras simultâneas (tela + bot) perdem marcação → [[Estado já impresso]].
- **Poda por idade** (`carregar(persistir_poda=True)`): mesma trava + **relê o disco** antes de gravar.
- **Refresh de token**: adquire a trava com **`espera=2*TIMEOUT`** (no Windows o `msvcrt.LK_LOCK` desiste em ~10s e o refresh HTTP dura até 30s) → [[Token e rotação do refresh]].

## Degradação suave
Sem suporte do sistema de arquivos, opera como antes (relê o disco). O `.tmp` do
`gravar_json` inclui o **PID**. O lock de **thread** cobre threads; a trava de
**arquivo** cobre processos.

## Relacionado
- [[estado]] · [[Estado já impresso]] · [[Token e rotação do refresh]] · [[Escrita atômica de JSON]]
