---
tags: [runbook, estado, credenciais, recuperacao]
type: runbook
status: current
aliases: [Recuperar estado, estado corrompido, .corrupto, git pull colide]
source_files: [estado.py, separador_etiquetas_ml.py]
source_docs: [docs/ARQUITETURA.md]
verified_at_commit: bcab879
---

# 🛠️ Runbook: recuperar estado ou credencial

> [!abstract]
> O que fazer quando o estado de impresso parece "zerado", uma credencial falha, ou o
> `git pull` colide na máquina de operação. **Nenhum** desses passos toca regra de negócio.

## Estado de impresso "zerado" / arquivo `.corrupto`
`ler_estado` **preserva** um estado ilegível movendo-o para `{nome}.{timestamp}.corrupto`
(com aviso) e recomeça vazio — ele **não** apaga o recuperável → [[Estado já impresso]].
1. Procure `estado_grupos.json.*.corrupto` (ML, por conta) ou `estado_shopee.json.*.corrupto`.
2. **Antes de reimprimir**, confira o `.corrupto`: grupos que apareceram como PENDENTE podem
   já ter sido impressos.
3. Se o `.corrupto` estiver íntegro, dá para restaurá-lo por cima do estado atual (com o app
   fechado). Se não, siga com cuidado — reimpressão não altera o estado (inv. 2).

## Credencial falha / conta "travada"
Causa comum: refresh rotacionado em corrida → [[Token e rotação do refresh]].
1. **Não** restaure um `.bak` de outra pasta — o `.bak` só vale **ao lado** do principal.
2. Se o `.bak` ao lado do principal estiver bom, o app já se auto-recupera dele.
3. Sem `.bak` válido: refaça o OAuth → [[Setup de credenciais (OAuth)]].

## `git pull` colide (máquina de operação)
Depois do fix de churn ([[Churn de git na máquina de operação]]) isso deveria ser raro.
Se ainda ocorrer com `nomes_sku.json`/`skus_por_anuncio.json`:
```bash
git status                 # veja o que está "modificado"
git stash                  # guarda edições locais reais
git pull                   # traz o main
git stash pop              # reaplica; resolva conflito preferindo suas edições de dados
```
Se a "modificação" for só de fim de linha (CRLF), é o bug já corrigido — um `git checkout --
<arquivo>` limpa.

## Critério de sucesso
App abre, consulta e imprime; `git status` limpo; nenhum `.corrupto` novo surgindo.

## Relacionado
- [[Estado já impresso]] · [[Token e rotação do refresh]] · [[Churn de git na máquina de operação]] · [[Arquivos — locais vs versionados]]
