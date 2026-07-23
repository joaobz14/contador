---
tags: [ia, estado, project-state]
type: project-state
status: current
aliases: [Estado atual, o que está pronto, situação do projeto]
source_docs: [docs/CHANGELOG.md, docs/PRIORIDADES_TECNICAS.md, docs/ARQUITETURA.md]
verified_at_commit: bcab879
---

# 📊 Estado atual do projeto

> [!abstract]
> Retrato **verificado** no commit `bcab879`. Cada afirmação foi conferida no código/testes.
> O backlog (`docs/PRIORIDADES_TECNICAS.md`) tem itens **já feitos** — confira sempre no código.

## ✅ Implementado
- **Impressão de etiquetas ML e Shopee** → ZPL → `.zip` na Downloads → Zebra. [[Impressão de etiquetas]] · `separador_etiquetas_ml.py`, `shopee_api.py`.
- **Estado "já impresso"** por marketplace + conta + dia de despacho, camada única em `estado.py` (é a "camada comum" do backlog #2). [[Estado já impresso]].
- **Multi-conta ML** (`definir_conta`, `contas/`) e **Modo Ambas**. [[Multi-conta (ML)]] · [[Modo Ambas (ML)]].
- **Resumo do dia**: tela detalhada por marketplace/conta **+ PDF da soma por produto (SKU)**, ordem da aba Nomes; registro por dia de ação em `historico.py`. [[Resumo do dia]].
- **Confirmação física antes de marcar** + **trava de ponta a ponta** anti-duplicata (Shopee). [[Confirmação física antes de marcar]] · [[Impressão dupla na Shopee]].
- **Token seguro** (`obter_token`, lock de thread + [[Trava entre processos]], `espera=2*TIMEOUT` no Windows). [[Token e rotação do refresh]].
- **Redação de segredos** (`sem_segredos`, formas query e JSON) e **log operacional** `separador.log` (backlog #4 feito). [[Redação de segredos]] · `registro.py`.
- **Config por chave** (`atualizar_config`) e **editores instância única**. [[Config e saneamento]].
- **Desempenho**: filtro ML com **20 workers** + `ml_tempos.log`; Shopee `_gerar_lote` paralelo. [[Desempenho]].
- **Cache de AWB** (`awb_cache_shopee.json`) para conferência confiável. [[Conferência na Shopee (rastreio)]].
- **Bot do Telegram** (consulta ML+Shopee; imprime só ML; `/resumo`). [[Telegram]].
- **Grafo com sincronizador seguro** `tools/graph_sync.py` + `semantic.json` + `tests/test_graphify_sync.py`. [[Grafo em duas camadas]].
- **Base de conhecimento Obsidian** (este cofre) + validador `tools/validar_obsidian.py`.

## 🟡 Parcialmente implementado
- **Separação do núcleo em módulos** (backlog #1): `estado.py` e `historico.py` já extraídos; `zpl.py`/`ml_api.py`/`agrupamento.py` ainda não. Dívida técnica confirmada.
- **`api-monitor/`** (rotina semanal de checagem das docs das APIs): infra pronta (scripts + `prompt-semanal.md`); a **cobertura das fontes** depende de rodar em máquina local (no ambiente de nuvem as fontes do ML/Shopee bloqueiam fetch automático). Não bloqueia o app.
- **`ads-monitor/`** (monitor de campanhas Product Ads/Mercado Ads, 3 camadas): coleta (`coletar.py`) grava snapshot diário de campanha **e de ad_group/item dentro dela** (atribuição por SKU, best-effort) num SQLite local, **com agendamento diário automático** (Agendador do Windows); recomendação (`recomendar.py`) já gera ações pros sinais que **não** dependem de margem (orçamento/ranking/ROAS vs. alvo). Recomendações condicionadas a margem seguem bloqueadas por não existir fonte de custo/margem por SKU. [[Product Ads — coletor (ads-monitor)]].

## ⏳ Pendente (confirmado não feito)
- **Cache de TTL curto** para envios ML não-terminais-e-não-prontos (backlog #8) — **área de risco** (não pode esconder um envio que virou `ready_to_print` dentro do TTL). [[Desempenho]].
- **Reimpressão no resumo do dia** (backlog #9) — decisão de v1: reimpressão não passa por `marcar_impresso`. [[Resumo do dia — soma por produto em PDF]].
- Melhorias de manutenibilidade do backlog: nomes de método explícitos na GUI (#3), tela de diagnóstico (#5), isolamento extra do modo Ambas (#6), padronização de encoding/Windows (#7, só parcial).

## 🔬 Pesquisa futura (nada implementado)
- **Amazon SP-API** (`docs/AMAZON_SP_API.md`) — levantamento; o risco decisivo é de negócio/BR (só FBM/MFN gera etiqueta). [[Amazon (pesquisa)]].
- **MCP Server do Mercado Livre** — avaliado; é **assistente de documentação** (`search_documentation`/`get_documentation_page`), **não** acessa dados/operações da conta. Não integrado. Candidato a apoio do `api-monitor`.

## ⚠️ Limitações conhecidas
- **"Sem data" reabre na virada do dia** (fallback `grupo.dia or hoje`) — caso raro, nada some. [[Dia de despacho]].
- **Shopee: organizar ~14s fixos** (latência do AWB, piso da plataforma) — batch não acelera. [[Shopee — organizar envio e AWB]].
- **`graphify-out/graph.html` defasado** — só o CLI `graphify` o regenera; `graph_sync` não. [[Fontes de verdade]].

## Relacionado
- [[Comece aqui]] · [[Fontes de verdade]] · [[Mapa de tarefas]] · [[Invariantes críticas]]
