---
tags: [moc, mapa, repositorio]
aliases: [Estrutura do projeto, Mapa do código]
type: hub
---

# 🗺️ Mapa do repositório

> [!abstract] Papel de cada arquivo
> Fonte: *Mapa do código* do `CLAUDE.md` e a *Estrutura do projeto* do `README.md`.

## Código-fonte (Python)
| Arquivo | Papel | Nota |
|---|---|---|
| `separador_etiquetas_ml.py` | Núcleo: API do ML, agrupamento, ZPL, carimbo, CLI | [[separador_etiquetas_ml (núcleo)]] |
| `estado.py` | Estado "já impresso" (ML+Shopee) + IO JSON atômico | [[estado]] |
| `historico.py` | Registro de impressão por dia de ação + resumo diário | [[historico]] |
| `registro.py` | Log operacional (`separador.log`) + redação de segredos | [[registro]] |
| `shopee_api.py` | Integração Shopee (API v2): listar, organizar, etiqueta, estado | [[shopee_api]] |
| `provedores.py` | Abstração de marketplace (`ProvedorML`/`ProvedorShopee`/`Ambas`) | [[provedores]] |
| `separador_gui.py` | Tela Tkinter (loja + conta + dia, busca, editores) | [[separador_gui]] |
| `bot_telegram.py` | Bot do Telegram (consulta ML+Shopee; imprime só ML) | [[bot_telegram]] |
| `relatorio.py` | Formata textos para o bot | [[relatorio]] |
| `pegar_token.py` / `pegar_token_shopee.py` | OAuth inicial (gera credenciais) | [[pegar_token (OAuth)]] |
| `tools/` | Ferramentas de dev (screenshot da GUI headless) | — |

## Dados versionados (sincronizam por Git)
- `nomes_sku.json` — SKU → nome + **ordem de separação** → [[Nomes amigáveis e ordem de separação]]
- `skus_por_anuncio.json` — código do anúncio ML sem SKU → SKU → [[Adoção de anúncios sem SKU]]

## Dados locais (nunca versionados)
Ver [[Arquivos — locais vs versionados]] para a lista completa (credenciais, estado, caches, logs, config).

## Documentação de apoio
- `README.md` — visão geral para o dono/usuário
- `docs/ARQUITETURA.md` — fluxos, [[Invariantes críticas]], áreas de risco
- `docs/CHANGELOG.md` — histórico de mudanças percebíveis
- `docs/PRIORIDADES_TECNICAS.md` — backlog técnico sugerido
- `docs/AMAZON_SP_API.md` — pesquisa (nada implementado) sobre a Amazon
- `graphify-out/` — grafo de conhecimento (código + docs)

## Relacionado
- [[🏠 Home]] · [[Fluxos de operação]] · [[Sistemas externos]]
