---
tags: [moc, home]
aliases: [Início, Home, MOC, Mapa mental]
type: moc
---

# 🏠 Contador — Segundo Cérebro

> [!abstract] O que é o projeto
> **Contador** é uma ferramenta de mesa (Windows) que **separa e imprime etiquetas de
> envio** do **Mercado Livre** e da **Shopee** numa **impressora térmica Zebra (ZPL)**.
> Lê os pedidos prontos, **agrupa por produto + quantidade**, gera o ZPL e entrega um
> `.zip` na pasta **Downloads**, que um app externo da Zebra monitora e imprime.
> O ganho: separar por **produto**, na **ordem pessoal** do operador, reduzindo erro.

> [!tip] Como navegar este cofre
> Use o **grafo do Obsidian** (ícone de grafo na barra lateral) para ver as conexões.
> Cada nota linka para as vizinhas em **Relacionado**. Comece pelos hubs abaixo.

## 🧭 Hubs de navegação
- [[Mapa do repositório]] — todos os arquivos e o que cada um faz
- [[Invariantes críticas]] — as 12 regras que **não** podem quebrar
- [[Fluxos de operação]] — o passo a passo de cada caminho (impressão, GUI, Shopee, Ambas, Telegram)
- [[Sistemas externos]] — ML API, Shopee API, Telegram, Zebra, Downloads
- [[Glossário]] — termos do domínio (SKU, AWB, DANFE, ZPL, dia de despacho…)

## 🧩 Módulos (código)
- [[separador_etiquetas_ml (núcleo)]] — cérebro: API do ML, agrupamento, ZPL, carimbo, CLI
- [[estado]] — estado "já impresso" (ML+Shopee) + IO JSON atômico
- [[historico]] — registro de impressão por dia de ação + resumo do dia
- [[registro]] — log operacional + redação de segredos
- [[shopee_api]] — integração Shopee (organizar envio, AWB, etiqueta)
- [[provedores]] — abstração de marketplace (ML / Shopee / Ambas)
- [[separador_gui]] — a tela Tkinter
- [[bot_telegram]] — bot de consulta (e impressão só do ML)
- [[relatorio]] — formatação de textos do bot
- [[pegar_token (OAuth)]] — configuração inicial (OAuth ML e Shopee)

## 💡 Conceitos-chave
| Estado & concorrência | Impressão & separação | Marketplace |
|---|---|---|
| [[Estado já impresso]] | [[Confirmação física antes de marcar]] | [[Provedor — abstração de marketplace]] |
| [[Trava entre processos]] | [[Identificação na impressão (carimbo)]] | [[Multi-conta (ML)]] |
| [[Token e rotação do refresh]] | [[Agrupamento e identidade do produto]] | [[Modo Ambas (ML)]] |
| [[Escrita atômica de JSON]] | [[Nomes amigáveis e ordem de separação]] | [[Shopee — organizar envio e AWB]] |
| [[Config e saneamento]] | [[Adoção de anúncios sem SKU]] | [[Conferência na Shopee (rastreio)]] |
| [[Redação de segredos]] | [[Ponte com a Zebra]] | [[Dia de despacho]] |
| [[Histórico e resumo do dia]] | [[Fuso de Brasília]] | |

## 🛠️ Operação & qualidade
- [[Desempenho]] — o que é caro (medido) e por quê
- [[Testes como documentação]] — qual teste protege qual regra
- [[Arquivos — locais vs versionados]] — o que sincroniza por Git e o que fica na máquina

## 🕸️ Grafo completo (espelho do graphify)
> [!tip] Duas camadas neste cofre
> As notas acima são a **camada curada** (leitura humana). Além delas, a pasta
> `Grafo/` tem o **espelho fiel** do `graphify-out/graph.json`: **937 nós** (código,
> porquês, conceitos, documentos) e **1695 arestas** (`calls`, `imports`,
> `rationale_for`, `references`, `conceptually_related_to`…) como wikilinks.
> Entre por **[[📊 Índice do Grafo]]**.

---
> [!info] Fontes de verdade (fora deste cofre)
> Regras: `CLAUDE.md` e `docs/CHANGELOG.md`. Arquitetura: `docs/ARQUITETURA.md`.
> Grafo de código: `graphify-out/`. Este cofre é a **camada navegável** desse conhecimento.
