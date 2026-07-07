<div align="center">

# 🏷️ Contador — Separador de Etiquetas

**Mercado Livre + Shopee → impressora térmica Zebra, em lote e sem erro de separação.**

[![Testes](https://github.com/joaobz14/contador/actions/workflows/testes.yml/badge.svg)](https://github.com/joaobz14/contador/actions/workflows/testes.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Plataforma](https://img.shields.io/badge/windows-Zebra%20ZPL-lightgrey)

<img src="docs/img/tela.png" width="620" alt="Tela do Separador">

</div>

Lê os pedidos prontos das lojas, agrupa por **produto + quantidade**, gera o **ZPL**
e solta um `.zip` na pasta **Downloads** — que o app da Zebra
(`impressora_zebra_usb.py`, fora deste repositório) reconhece pelo nome e imprime sozinho.

```
pedidos prontos ──► grupos (produto × qtd) ──► ZPL ──► .zip em Downloads ──► 🖨 Zebra
```

## ✨ Destaques

- **Duas lojas, uma tela** — seletor Mercado Livre / Shopee; a arquitetura de
  provedores (`provedores.py`) faz a tela ser a mesma para os dois.
- **Multi-conta no ML** (ex.: Gastromaq / Cozilatti), cada uma com estado e
  credenciais isolados em `contas/{nome}/` — e o modo **🌐 Ambas**, que junta
  as contas num dia de motorista único (uma pilha por produto, ZIP único,
  controle de impresso continua por conta).
- **Dia de despacho com contagem** — os próximos dias úteis com o total de
  pedidos em cada um; datas fora de seg–sex (fim de semana, atrasadas, sem data)
  aparecem em "Outras datas". Nenhum pedido fica invisível.
- **Impressão em lote** com *marcar todos* (geral e por bloco de quantidade),
  busca por nome/SKU e confirmação física antes de marcar como impresso.
- **Identificação na DANFE**: carimbo do **SKU** ou do **nome do produto**
  (fonte adaptativa), etiqueta divisória, ou nada.
- **Nomes amigáveis** editáveis na própria tela (botão **✏ Nomes**) —
  `SKU → nome`, sincronizado entre PCs pelo git.
- **Shopee de ponta a ponta**: organiza o envio como Postagem (drop-off),
  espera o rastreio (AWB), baixa a etiqueta térmica e mostra o rastreio na tela.
- **Recuperação rápida**: reimpressão individual ou **em lote** das já impressas
  (papel atolou? marca e reimprime tudo de uma vez, sem mexer no controle).
- **À prova de queda de energia**: gravação atômica com `fsync` + backup `.bak`
  das credenciais com auto-recuperação (não precisa refazer token).
- **Bot do Telegram** (opcional) para consultar e imprimir de longe.
- **Atalhos**: `F5` atualiza, `Ctrl+F` busca, `Esc` limpa a busca.

## 🚀 Instalação

```bash
pip install -r requirements.txt
```

**Mercado Livre (uma vez por conta):**

```bash
python pegar_token.py        # ou duplo-clique em "atalhos\Pegar Token.bat"
```

O programa pede o **nome da conta** (ex.: `Gastromaq`) e salva em
`contas/{nome}/credenciais.json`. Repita para cada conta.

**Shopee (uma vez):**

```bash
python pegar_token_shopee.py # ou duplo-clique em "atalhos\Pegar Token Shopee.bat"
```

Pré-requisito: app **Live** em [open.shopee.com](https://open.shopee.com) com a
Redirect URL `https://joaobz14.github.io/contador/` (página em `docs/`).

> ⚠️ Credenciais **nunca** são versionadas (já estão no `.gitignore`).
> Os modelos dos arquivos ficam em [`exemplos/`](exemplos/).

## 🖥️ Usando

Duplo-clique em **`Abrir Separador.bat`** (sem janela preta). Se a tela não abrir,
use **`atalhos\Abrir Separador (diagnostico).bat`** para ver o erro.

1. Escolha a **loja** (e a conta, no ML) e o **dia de despacho** — após um
   🔄 Atualizar, cada dia mostra quantos pedidos tem.
2. Marque os grupos (ou **Marcar todos**) e clique **🖨 Imprimir selecionados** —
   sai tudo num `.zip` único, sem pausa entre etiquetas.
3. Confira se as etiquetas saíram e confirme — só então os grupos são marcados
   como impressos. Na Shopee, o app pergunta antes de **organizar o envio**
   (Postagem/drop-off), que é o passo que emite o rastreio.

**Dois PCs (escritório + casa):** cada um com seu clone; para atualizar,
duplo-clique em **`Atualizar programa.bat`** (roda `git pull`). Os nomes
amigáveis viajam pelo git; credenciais e estado são locais de cada PC.

<details>
<summary><b>📱 Bot do Telegram (opcional)</b></summary>

Consulta e impressão pelo celular. A impressão sai **na máquina onde o bot roda**
(o `.zip` cai no Downloads dela) — então rode-o no PC do escritório, com a Zebra ligada.

```bash
pip install -r requirements-bot.txt
copy exemplos\bot_config.example.json bot_config.json   # preencha o token do @BotFather
python bot_telegram.py
```

- Comandos: `/hoje` `/amanha` `/dia AAAA-MM-DD` `/todos` `/resumo`
  `/detalhar SKU` `/conta` `/loja` `/id` `/menu`
- **Imprimir pelo bot** (só ML): botão 🖨 em cada grupo, com confirmação antes.
  A Shopee no bot é **somente consulta** — a impressão dela fica no app.
- **Segurança**: token via `bot_config.json` (não versionado) ou
  `TELEGRAM_BOT_TOKEN`; só responde aos `chat_ids` autorizados (mande `/id` para
  descobrir o seu).
- **Aviso da manhã**: defina `"aviso_horario": "08:00"` no `bot_config.json` e o
  bot manda o resumo do dia nesse horário (Brasília).
- **Ligar**: `atalhos\Iniciar Bot.bat` (simples) ou `atalhos\Iniciar Bot (auto).bat`
  (**religa sozinho** se cair — recomendado). Para iniciar com o Windows:
  atalho do `.bat` em `Win+R` → `shell:startup`.
- Atividade registrada em `bot.log`.

</details>

<details>
<summary><b>⌨️ Linha de comando</b></summary>

**Mercado Livre** (`separador_etiquetas_ml.py`):

```bash
python separador_etiquetas_ml.py            # grupos prontos de HOJE
python separador_etiquetas_ml.py todos      # todos os dias
python separador_etiquetas_ml.py envios     # datas de despacho de cada envio
python separador_etiquetas_ml.py resumo     # quantos pacotes por dia
python separador_etiquetas_ml.py detalhar "<nome>" <QTD>
python separador_etiquetas_ml.py imprimir "<nome>" <QTD>
python separador_etiquetas_ml.py reimprimir "<nome>" <QTD>
python separador_etiquetas_ml.py proximo    # imprime o próximo pendente
python separador_etiquetas_ml.py rastrear <SKU>
```

**Shopee** (`shopee_api.py`):

```bash
python shopee_api.py                        # grupos prontos de HOJE
python shopee_api.py amanha | todos | dia <AAAA-MM-DD>
python shopee_api.py etiqueta <order_sn>    # gera/baixa a etiqueta (Downloads)
python shopee_api.py parametros <order_sn>  # diagnóstico dos tipos de documento
```

Atalho Windows: **`atalhos\Etiqueta Shopee.bat`** lista os pedidos de hoje, pergunta o
`order_sn` e gera a etiqueta.

</details>

<details>
<summary><b>🔎 Por dentro (agrupamento, carimbo, Shopee, arquivos)</b></summary>

**Agrupamento** — identidade do produto: **SKU → GTIN + voltagem →
`item_id:variação`**. Um pedido com vários SKUs (kit) vira um único grupo
"Combo" (1 etiqueta listando os itens). Agrupar é **por envio = 1 etiqueta**.

**Identificação na impressão** — o seletor da tela oferece:
| Modo | O que sai na DANFE |
|---|---|
| Carimbo SKU | o código do produto, centralizado na área livre |
| Carimbo nome | o nome da aba **Nomes** (fonte adaptativa: curto maior, longo até 3 linhas; sem nome cadastrado cai no SKU). Pedido com 2+ unidades ganha a quantidade em destaque abaixo do nome (`2x`, `3x`…) |
| Etiqueta divisória | uma página separadora antes de cada lote |
| Nenhuma | nada |

Só a DANFE é carimbada (a etiqueta de envio fica intacta). Posição/tamanho nas
constantes `CARIMBO_Y`, `CARIMBO_ALTURA` e `CARIMBO_ALTURA_NOME`.

**Shopee** — a etiqueta só existe depois de **organizar o envio** (é o que emite
o AWB). O app organiza como **Postagem (drop-off)** via `ship_order` — com
confirmação antes — espera o rastreio, cria o documento térmico
(`THERMAL_AIR_WAYBILL`), aguarda `READY` e baixa. O resultado é um ZIP com o ZPL
dentro, que a Zebra imprime direto. Grupos de 1 pedido já impressos mostram o
**rastreio (🏷)** na tela para conferência.

**Nomes amigáveis** — `nomes_sku.json` (versionado) mapeia `SKU → nome`. Edite
pela tela (**✏ Nomes**: busca, salvar, remover — sem risco de quebrar o JSON) ou
no arquivo direto.

**Estado de "já impresso"** — por marketplace e por **dia de despacho**
(`contas/{conta}/estado_grupos.json` no ML, `estado_shopee.json` na Shopee).
Lotes só marcam depois da confirmação física.

**Arquivos gerados (não versionados)** — credenciais (e espelhos `.bak`),
`estado_grupos.json`, `itens_cache.json`, `envios_cache.json`, `config.json`,
`bot_config.json`, `bot.log`, `link_autorizacao*.txt`.

</details>

## 🧪 Testes

```bash
pip install -r requirements-dev.txt
pytest            # suíte completa, sem rede
```

A GUI pode ser inspecionada **sem monitor** (CI / máquinas headless):

```bash
bash tools/setup_gui_tests.sh                             # 1x: tkinter+xvfb+imagemagick
xvfb-run -a python3.12 tools/gui_screenshot.py out.png [Shopee]
```

O CI roda esse smoke em **cada PR** (job `gui-smoke`): abre a tela nos dois
marketplaces e publica os screenshots como artefato do run.

## 📁 Estrutura

| | Papel |
|---|---|
| `separador_etiquetas_ml.py` | Núcleo: API do ML, agrupamento, estado, ZPL, carimbo, CLI. |
| `shopee_api.py` | Integração Shopee (API v2): listar, organizar envio, etiqueta. |
| `provedores.py` | Abstração de marketplace usada pela tela. |
| `separador_gui.py` | A tela (Tkinter). |
| `bot_telegram.py` / `relatorio.py` | Bot do Telegram e formatação dos textos. |
| `pegar_token*.py` | OAuth inicial (ML e Shopee). |
| `Abrir Separador.bat` · `Atualizar programa.bat` | Os 2 atalhos do dia a dia (raiz, duplo-clique). |
| `atalhos/` | Demais atalhos (tokens, bot, diagnóstico, etiqueta Shopee). |
| `exemplos/` | Modelos dos arquivos de configuração. |
| `tests/` · `tools/` · `docs/` | Testes (pytest) · ferramentas de dev · página de callback + imagens. |
