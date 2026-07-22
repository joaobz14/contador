---
tags: [hub, home]
aliases: [Início, Home, MOC, Mapa mental]
type: hub
status: current
---

# 🏠 Contador — Segundo Cérebro

> [!abstract] O que é o projeto
> **Contador** é uma ferramenta de mesa (Windows) que **separa e imprime etiquetas de
> envio** do **Mercado Livre** e da **Shopee** numa **impressora térmica Zebra (ZPL)**.
> Lê os pedidos prontos, **agrupa por produto + quantidade**, gera o ZPL e entrega um
> `.zip` na pasta **Downloads**, que um app externo da Zebra monitora e imprime.
> O ganho: separar por **produto**, na **ordem pessoal** do operador, reduzindo erro.

> [!tip] Como navegar este cofre
> Cada nota linka para as vizinhas na seção **Relacionado**. O **grafo do Obsidian**
> (ícone na barra lateral) mostra essas conexões. Comece pelos hubs abaixo — ou, se
> você é um **agente de IA**, comece por **[[Comece aqui]]**.

## 🤖 Para agentes de IA
- [[Comece aqui]] — como investigar uma tarefa neste projeto, do zero
- [[Fontes de verdade]] — em que confiar (código, ARQUITETURA, Graphify, este cofre)
- [[Estado atual]] — o que está implementado, parcial, pendente ou pesquisa
- [[Mapa de tarefas]] — "quero fazer X, começo por onde?"

## 🧭 Hubs de navegação
- [[Mapa do repositório]] — todos os arquivos e o que cada um faz
- [[Invariantes críticas]] — as 12 regras que **não** podem quebrar
- [[Fluxos de operação]] — o passo a passo de cada caminho (impressão, GUI, Shopee, Ambas, Telegram)
- [[Sistemas externos]] — visão geral dos [[Mercado Livre|marketplaces]] e [[Telegram|integrações]]
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

## 🧱 Funcionalidades, decisões e operação
- **Funcionalidades:** [[Resumo do dia]] · [[Impressão de etiquetas]]
- **Marketplaces:** [[Mercado Livre]] · [[Shopee]] · [[Amazon (pesquisa)]]
- **Integrações:** [[Telegram]] · [[Zebra e pasta Downloads]] · [[GitHub Actions (CI)]]
- **Decisões:** [[Resumo do dia — soma por produto em PDF]] · [[Grafo em duas camadas]]
- **Incidentes:** [[Impressão dupla na Shopee]] · [[Churn de git na máquina de operação]]
- **Runbooks:** [[Setup de credenciais (OAuth)]] · [[Recuperar estado ou credencial]] · [[Validar o repositório]]

## 🛠️ Qualidade
- [[Desempenho]] — o que é caro (medido) e por quê
- [[Testes como documentação]] — qual teste protege qual regra
- [[Arquivos — locais vs versionados]] — o que sincroniza por Git e o que fica na máquina

---
> [!info] Onde está o grafo técnico
> As relações estruturais e semânticas entre arquivos, símbolos e conceitos vivem em
> **`graphify-out/`** (não neste cofre). Este cofre é a **camada de contexto humano**;
> como as duas se dividem está em [[Fontes de verdade]].
