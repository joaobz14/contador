---
tags: [hub, meta]
type: hub
status: current
aliases: [README do vault, sobre o cofre]
---

# Base de conhecimento (Obsidian) — Contador

Esta pasta é um **cofre Obsidian versionado**: a camada de **contexto humano e
operacional** do projeto *Contador — Separador de Etiquetas* (Mercado Livre + Shopee →
impressora Zebra). Ela existe para que **pessoas e agentes de IA** entendam, mantenham
e modifiquem o projeto com segurança.

## Para que serve (e o que NÃO é)

| Fonte | Responsabilidade |
|---|---|
| **Código e testes** | Comportamento real. Fonte primária. |
| `docs/ARQUITETURA.md` | Invariantes e regras arquiteturais. |
| `AGENTS.md` / `CLAUDE.md` | Instruções operacionais para agentes. |
| `graphify-out/` | Relações **estruturais e semânticas** entre arquivos, símbolos e conceitos (grafo). |
| `docs/CHANGELOG.md` | Histórico cronológico. |
| `docs/PRIORIDADES_TECNICAS.md` | Backlog (confirme no código antes de tratar como pendente). |
| **`obsidian/` (aqui)** | Contexto humano: **decisões, conceitos, estado atual, incidentes, runbooks, funcionalidades** e orientação para IA. |

O cofre **não** substitui o Graphify nem duplica a documentação: cada fonte tem um papel.
Quando duas discordarem, a ordem de prioridade está em [[Fontes de verdade]].

## Como abrir

- **Como vault do Obsidian:** abra a pasta `obsidian/` em *Open folder as vault*.
- **Como Markdown comum:** qualquer editor/visualizador serve; os links `[[Nota]]` são
  wikilinks do Obsidian.
- **Entradas:** [[🏠 Home]] (navegação humana) e [[Comece aqui]] (agentes de IA).

## Validação

```bash
python tools/validar_obsidian.py     # links, frontmatter, vazios, colisões, segredos
pytest tests/test_validar_obsidian.py -q
```
Roda no CI (job `obsidian` em `.github/workflows/testes.yml`).

> [!warning] Conteúdo público — sem segredos
> Tudo aqui é **versionado e público** no GitHub. **Nunca** inclua tokens, `client_secret`,
> `refresh_token`, senhas, URLs assinadas, dados de clientes ou pedidos reais. Use
> placeholders sintéticos (`SEU_TOKEN_AQUI`, `ORDER_ID_FICTICIO`, `example.com`). Mencionar
> o **nome** de um campo (`access_token`) na documentação é permitido; incluir um **valor**
> real não é.
