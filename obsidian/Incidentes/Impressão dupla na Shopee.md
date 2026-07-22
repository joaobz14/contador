---
tags: [incidente, shopee, impressao, gui]
type: incident
status: current
aliases: [Impressão dupla, duplo clique Shopee, trava de ponta a ponta]
source_files: [separador_gui.py, shopee_api.py]
source_docs: [docs/ARQUITETURA.md, docs/CHANGELOG.md]
verified_at_commit: bcab879
---

# 🚨 Incidente: impressão dupla na Shopee (duplo disparo)

> [!abstract]
> Um lote da Shopee foi impresso **duas vezes** porque o operador apertou imprimir de novo
> no intervalo entre o app buscar as etiquetas e pedir a confirmação. Corrigido com a
> **trava de ponta a ponta**.

## Sintomas
Operador confirma "Organizar envio", o app começa a buscar/gerar as etiquetas (que **já
saem fisicamente** — ZIP → Downloads → Zebra), e **antes** da pergunta "saíram certo?" ele
aperta imprimir novamente → o **mesmo lote sai duas vezes**.

## Impacto
Etiquetas duplicadas (desperdício e risco de despachar errado). Erro operacional, mas
facilitado por uma janela do software.

## Causa raiz
Na Shopee a etiqueta **sai durante a busca**, mas o estado só é marcado **depois** da
confirmação. Nesse meio, o botão continuava habilitado — o `if self.ocupado: return` não
pegava porque `ocupado` já tinha voltado a `False`.

## Correção
**Trava de ponta a ponta:** o app fica `ocupado` **desde a confirmação de "Organizar
envio" até a resposta "saíram certo?"**. `imprimir_lotes`/`imprimir` chamam `_ocupar(True)`
antes de `_confirmar_organizar`, e o `_ocupar(False)` só roda no `finally` de
`_confirmar_e_marcar`. Cancelar o organizar libera a trava; o `finally` libera mesmo se a
confirmação estourar. Ver [[Confirmação física antes de marcar]].

## Prevenção / regressão
- A ordem "gera → confirma → marca" é a **invariante 1** → [[Invariantes críticas]].
- Testes da confirmação/trava em `tests/test_gui_confirmacao.py`.

## Relacionado
- [[Confirmação física antes de marcar]] · [[separador_gui]] · [[Shopee — organizar envio e AWB]]
