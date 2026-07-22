---
tags: [modulo, estado, concorrencia]
aliases: [estado.py, camada de estado]
type: modulo
arquivo: estado.py
---

# 💾 estado.py — a camada comum do "já impresso"

> [!abstract] Papel
> Lógica **única** do estado de impresso (ML **e** Shopee) e o **IO de JSON atômico**.
> Núcleo e `shopee_api` só expõem wrappers finos que passam o seu `ARQUIVO_ESTADO`.

## Funções centrais
- `chave_estado` — a chave `{dia}|{chave}|q{qtd}` → [[Estado já impresso]]
- `status_grupo`, `impressos`, `envios_pendentes` — classificam pendente/parcial/impresso
- `marcar_impresso` — o ciclo **ler → mesclar → salvar** sob [[Trava entre processos]]
- `carregar` / `limpar_antigo` — poda por idade (`persistir_poda=True` relê o disco antes de gravar)
- `ler_estado` — distingue **corrupção** (→ `.corrupto`) de **ausência** (`{}`) de **falha transitória**
- `ler_json` / `gravar_json` — IO tolerante e **atômico e durável** → [[Escrita atômica de JSON]]
- `.trava` — a trava de arquivo entre processos → [[Trava entre processos]]

> [!warning] Nunca ler estado por `ler_json`
> `ler_json` silencia falha como `{}` (certo para config/cred/cache). No **estado**
> isso destruiria o recuperável: corrompido lido como `{}` faz todos os grupos
> voltarem a PENDENTE e a próxima marcação grava por cima. Use `ler_estado`.

## Callback de histórico
`marcar_impresso` recebe um callback `registrar` com **só o delta** (ids novos) —
alimenta o [[Histórico e resumo do dia]] sem contagem dobrada.

## Relacionado
- [[separador_etiquetas_ml (núcleo)]] · [[shopee_api]] · [[historico]] · [[Invariantes críticas]]
