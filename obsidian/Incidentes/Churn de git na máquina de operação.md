---
tags: [incidente, git, io, operacao]
type: incident
status: current
aliases: [Churn de git, CRLF nos JSONs, git pull colide]
source_files: [estado.py, .gitignore, .gitattributes]
source_docs: [docs/CHANGELOG.md]
verified_at_commit: bcab879
---

# 🚨 Incidente: `git pull` colidia a cada dia na máquina de operação

> [!abstract]
> Em `C:\contador` (a máquina que opera direto no `main`), todo `git pull` colidia com
> arquivos "modificados" que o operador não tinha editado. Corrigido na origem.

## Sintomas
`git status` sempre sujo com `nomes_sku.json` e `skus_por_anuncio.json` "modificados"
(sem edição real), e o `git pull` recusando por conflito local.

## Impacto
Atrito diário: a sincronização dos dois JSONs versionados (nomes/ordem de separação e
adoção de anúncios) travava, exigindo intervenção manual.

## Causa raiz
Dois motivos concretos:
1. **CRLF nos JSONs versionados** — `gravar_json` abria em modo texto e, no Windows,
   convertia `\n`→CRLF. Como o repo mantém esses arquivos em **LF** (`.gitattributes
   eol=lf`), a GUI os reescrevia em CRLF e eles ficavam "modificados" para sempre.
2. **Saídas geradas do monitor rastreadas** — `api-monitor/relatorios/` e `snapshots/*.md`
   poluíam o `git status` e entravam em stashes/conflitos.

## Correção
1. `gravar_json` grava **LF** (`open(..., newline="\n")`) → [[Escrita atômica de JSON]].
2. As saídas do `api-monitor` (`relatorios/`, `snapshots/*.md`, `fetched/`, `logs/`) viraram
   **gitignoradas**; só a infra é versionada.

## Prevenção / regressão
- Teste-guardião `test_gravar_json_escreve_lf_nao_crlf` (grava LF, nunca CRLF).
- Runbook para quando ainda surgir conflito local: [[Recuperar estado ou credencial]].

## Relacionado
- [[Escrita atômica de JSON]] · [[Arquivos — locais vs versionados]] · [[Nomes amigáveis e ordem de separação]]
