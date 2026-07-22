---
tags: [operacao, testes, ci, invariante]
aliases: [testes, pytest, CI, testes como documentação]
type: reference
---

# 🧪 Testes como documentação viva

> [!abstract]
> Cada teste protege uma regra. Rodam **sem rede** e sem arquivos reais (`pytest`).
> Mapa de teste → regra (de `docs/ARQUITETURA.md`).

| Teste | Protege |
|---|---|
| `tests/test_estado.py` | ciclo de vida do estado, marcação parcial, mescla com disco (inv. 3,4,5) → [[Estado já impresso]] |
| `tests/test_lotes.py` | geração em lote **sem** marcar antes da confirmação (inv. 1) → [[Confirmação física antes de marcar]] |
| `tests/test_shopee.py` | HMAC, AWB, documento térmico, READY, ZIP/ZPL, falha parcial (inv. 8,9) → [[Shopee — organizar envio e AWB]] |
| `tests/test_ambas.py` | fusão de grupos, marcação na conta correta → [[Modo Ambas (ML)]] |
| `tests/test_bot_impressao.py` | botões, troca de conta/loja, impedir imprimir Shopee (inv. 10,11) → [[bot_telegram]] |
| `tests/test_rede.py` | retry/backoff em rede |
| `tests/test_datas.py` | datas no fuso de Brasília → [[Fuso de Brasília]] |
| `tests/test_agrupar.py` + `test_identidade.py` | identidade e agrupamento → [[Agrupamento e identidade do produto]] |
| `tests/test_config.py` | preferências locais → [[Config e saneamento]] |
| `tests/test_provedores.py` | a interface comum GUI↔marketplaces (inclui `test_provedores_nao_expoe_imprimir_grupo`) → [[Provedor — abstração de marketplace]] |

## CI (`.github/workflows/testes.yml`)
- **`lint`**: `ruff check .` (regras `F` + `E9`).
- **`pytest`** em Python 3.11 e 3.12.
- **`gui-smoke`**: abre a GUI headless com `xvfb` nos 2 marketplaces (`tools/gui_screenshot.py`), publica PNGs.

## Relacionado
- [[Invariantes críticas]] · [[Fluxos de operação]] · [[🏠 Home]]
