---
tags: [ia, tarefas, hub]
type: hub
status: current
aliases: [Mapa de tarefas, quero fazer X, onde mexer]
---

# 🗺️ Mapa de tarefas — "quero fazer X, começo por onde?"

> [!abstract]
> Atalhos do tipo de tarefa → onde olhar primeiro. Sempre confirme no código; o cofre orienta.

| Quero… | Comece por | Cuidado |
|---|---|---|
| Entender o fluxo geral | [[Fluxos de operação]] · [[🏠 Home]] | — |
| Mexer no **estado de impresso** | `estado.py` · [[Estado já impresso]] | `ler_estado` (não `ler_json`); merge sob [[Trava entre processos]] (inv. 5) |
| Mexer em **token/credenciais** | `separador_etiquetas_ml.py` (`obter_token`) · [[Token e rotação do refresh]] | Nunca `renovar_token` direto (inv. 6/7) — trava a conta |
| Mexer na **impressão / saída Zebra** | [[Ponte com a Zebra]] · `separador_etiquetas_ml.py` | Não mudar o **prefixo** do `.zip`; `nome_saida_unico` |
| Mexer na **Shopee** | `shopee_api.py` · [[Shopee — organizar envio e AWB]] | Etiqueta só após organizar (inv. 8/9); não vazar token |
| Mexer na **GUI** | `separador_gui.py` · [[separador_gui]] | Ordem "gera → confirma → marca" (inv. 1); editores instância única |
| Mexer no **bot** | `bot_telegram.py` · [[Telegram]] | Não imprime Shopee (inv. 10); valida conta/loja (inv. 11) |
| Adicionar **capacidade de marketplace** | [[Provedor — abstração de marketplace]] | Método do provedor, não `if marketplace` |
| Investigar **lentidão** | [[Desempenho]] · `ml_tempos.log`/`shopee_tempos.log` | Meça antes; o filtro ML é a fase cara |
| Entender **relações/quem chama** | `graphify-out/` (`GRAPH_REPORT.md`, `semantic.json`) | Camada AST pode defasar → [[Fontes de verdade]] |
| Saber **o que já existe** | [[Estado atual]] | Backlog tem itens já feitos |
| Atualizar o **grafo** | `python tools/graph_sync.py --update` · [[Grafo em duas camadas]] | Nunca `graphify hook install` |
| Atualizar/validar **este cofre** | [[Validar o repositório]] · `tools/validar_obsidian.py` | Sem segredos; links resolvidos |
| Configurar **credenciais** (setup) | [[Setup de credenciais (OAuth)]] | Uma vez por conta/loja |
| Recuperar **estado/credencial** | [[Recuperar estado ou credencial]] | Não restaurar `.bak` desgarrado |

## Relacionado
- [[Comece aqui]] · [[Fontes de verdade]] · [[Estado atual]] · [[Invariantes críticas]]
