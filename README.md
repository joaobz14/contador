# Separador de Etiquetas — Mercado Livre

[![Testes](https://github.com/joaobz14/contador/actions/workflows/testes.yml/badge.svg)](https://github.com/joaobz14/contador/actions/workflows/testes.yml)

Ferramenta em Python para **separar e imprimir etiquetas de envio do Mercado Livre**
em lote. Ela lê os pedidos da conta, mantém apenas os que estão em
**"Etiquetas para imprimir"** (`ready_to_ship` + `ready_to_print`) e os agrupa por
**produto + quantidade do pedido**, gerando as etiquetas em formato **ZPL** (Zebra).

A identidade de cada produto é definida nesta ordem de prioridade:
**SKU → GTIN + voltagem → `item_id:variação`**.

O agrupamento é **por envio = 1 etiqueta**: um pedido com vários SKUs diferentes
(combo/kit) vira um único grupo "Combo" (1 etiqueta, listando os itens), em vez de
ser separado por SKU.

## Estrutura do projeto

**Código**
| Arquivo | Papel |
|---|---|
| `separador_etiquetas_ml.py` | Núcleo da aplicação + interface de linha de comando (CLI). |
| `separador_gui.py` | Interface gráfica (Tkinter) que reaproveita o núcleo. |
| `pegar_token.py` | Configuração inicial (uma vez só): faz o fluxo OAuth do Mercado Livre e gera o `credenciais.json`. |
| `tests/` | Testes automatizados (pytest). |

**Atalhos do Windows**
| Arquivo | Papel |
|---|---|
| `Abrir Separador.bat` | Abre a tela sem terminal (duplo-clique). |
| `Abrir Separador (diagnostico).bat` | Abre com terminal visível, para ver erros. |
| `Abrir Separador.pyw` | Alternativa ao `.bat` (depende da associação do `.pyw`). |
| `Atualizar programa.bat` | Atualiza para a versão mais nova (`git pull`). |
| `Pegar Token.bat` | Configura/adiciona uma conta (roda o `pegar_token.py`). |

**Configuração e dados**
| Arquivo | Papel |
|---|---|
| `nomes_sku.json` | De-para SKU → nome amigável (versionado). |
| `credenciais.example.json` | Modelo do arquivo de credenciais (copie para `credenciais.json`). |
| `pyproject.toml` / `requirements*.txt` | Metadados, dependências e configuração de testes. |

> Arquivos com segredos/estado (`credenciais.json`, `estado_grupos.json`, caches) **não** são versionados — veja "Arquivos gerados" no fim.

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração (uma vez por conta)

```bash
python pegar_token.py
```

Siga as instruções na tela. O programa pede o **nome da conta** (ex.: `Gastromaq`,
`Cozilatti`) e ao final salva o arquivo em `contas/{nome}/credenciais.json`.
Repita para cada conta adicional.

> ⚠️ **Nunca** compartilhe ou versione os arquivos de credenciais: eles contêm
> segredos da sua aplicação. Já estão no `.gitignore` (`contas/*/credenciais.json`).

### Múltiplas contas

O app suporta várias contas Mercado Livre simultaneamente. Cada conta tem seus
próprios arquivos em `contas/{nome}/` (credenciais, estado de impresso, caches),
completamente isolados. O `nomes_sku.json` e as preferências gerais são compartilhados.

Quando há 2 ou mais contas configuradas, a tela mostra um seletor de conta
(`[Gastromaq] [Cozilatti]`) antes do filtro de dia. A conta ativa é lembrada
automaticamente.

**Migração da conta antiga:** se você já usava o app com uma conta na raiz, na
primeira vez que abrir a tela ele pergunta o nome dessa conta (ex.: `Gastromaq`)
e move os arquivos para `contas/{nome}/` automaticamente. Depois disso é só rodar
`pegar_token.py` para adicionar a segunda conta.

## Atualizar para a versão mais nova

Se você obteve o projeto com `git clone`, dê um duplo-clique em
**`Atualizar programa.bat`** (ele roda `git pull` na pasta, sem abrir o
terminal). Em seguida, abra o programa normalmente pelo `Abrir Separador.bat`.

> Usando em mais de um PC via OneDrive (mesma conta): atualize em **apenas um**
> deles; o OneDrive sincroniza a pasta para o outro. Não use os dois ao mesmo
> tempo e espere o OneDrive terminar de sincronizar antes de trocar de máquina.

## Uso

### Linha de comando

```bash
python separador_etiquetas_ml.py            # lista os grupos prontos (somente de HOJE)
python separador_etiquetas_ml.py todos      # inclui também os de outros dias
python separador_etiquetas_ml.py envios     # mostra as datas de despacho
python separador_etiquetas_ml.py resumo     # quantos pacotes em cada dia de despacho
python separador_etiquetas_ml.py detalhar "<nome>" <QTD>   # composição de um grupo
python separador_etiquetas_ml.py imprimir "<nome>" <QTD>   # imprime um grupo
python separador_etiquetas_ml.py reimprimir "<nome>" <QTD> # reimprime um grupo (não altera o estado)
python separador_etiquetas_ml.py proximo    # imprime o próximo grupo pendente
python separador_etiquetas_ml.py rastrear <SKU>            # diagnóstico de um SKU
```

### Interface gráfica

Mostra os grupos do dia (produto + quantidade) com um botão **Imprimir** em cada um.
A lista é separada em **🖨 Para imprimir** (em cima) e **✓ Já impressas — arquivadas**
(embaixo), para que um grupo pendente nunca fique perdido no meio dos já impressos.
Cada grupo também tem **↻ Reimprimir**, que refaz as etiquetas daquele grupo (útil
se uma etiqueta atolar/estragar) sem alterar o controle de impresso.

**Marketplace (Mercado Livre / Shopee):** no topo há um seletor **Loja**. No
Mercado Livre aparecem o seletor de conta (Gastromaq/Cozilatti) e o de
identificação (carimbo/divisória); na Shopee esses somem (a etiqueta Shopee é
imagem, sem DANFE). Imprimir um pedido Shopee **organiza o envio como Postagem
(drop-off) automaticamente** — com uma confirmação antes — e baixa a etiqueta, que
o app da Zebra imprime igual ao Mercado Livre. O controle de "já impresso" é
separado por marketplace. A arquitetura fica em `provedores.py` (um provedor por
marketplace), então a tela é a mesma para os dois.

**Jeito prático (Windows):** dê um duplo-clique em **`Abrir Separador.bat`**.
Ele abre a tela direto, sem a janela preta do terminal. Para ter um ícone na
área de trabalho, clique com o botão direito nesse arquivo →
**Enviar para → Área de trabalho (criar atalho)**.

> Se a tela não abrir, use **`Abrir Separador (diagnostico).bat`**: ele mantém o
> terminal aberto mostrando o motivo do erro.

**Alternativa — `Abrir Separador.pyw`:** também abre a tela sem terminal por
duplo-clique. Depende de o Windows ter o `.pyw` associado ao `pythonw`; se o
duplo-clique não fizer nada, fique com o `Abrir Separador.bat` (mais garantido).

**Pelo terminal (alternativa):**

```bash
python separador_gui.py
```

## Bot do Telegram (opcional — consulta e impressão)

Permite consultar **e imprimir** os pedidos pelo celular. A consulta é somente
leitura; a impressão reaproveita exatamente a mesma lógica da tela/CLI. Comandos:

- `/hoje`, `/amanha`, `/dia AAAA-MM-DD`, `/todos` — grupos por dia de despacho
- `/detalhar SKU` — composição de um SKU (itens/variações que o formam)
- `/resumo` — quantos pacotes por dia
- `/conta` — vê/troca a conta ativa pelo Telegram (aparece com 2+ contas)
- `/id` — mostra seu chat id (para liberar no `chat_ids`)

**Várias contas pelo bot:** o bot usa a **conta ativa** (a mesma do `config.json`,
compartilhada com a tela). Com 2+ contas, `/conta` lista botões para alternar —
a troca vale também para a tela. Se a conta salva sumir, o bot escolhe a primeira
automaticamente (igual à tela), em vez de falhar.

**Imprimir pelo bot:** em qualquer listagem (Hoje/Amanhã/Dia/Todos), cada grupo
ganha um botão **🖨 Imprimir**. Ao tocar, o bot pede uma confirmação
(**Confirmar / Cancelar**) antes de gerar a etiqueta — evita impressão acidental.
Confirmado, ele imprime só os envios ainda **pendentes** do grupo e marca o
estado, igual à tela.

> ⚠️ **A impressão sai na máquina onde o bot está rodando.** Imprimir gera o
> `.zip` na pasta Downloads desse PC, que o app da Zebra (`impressora_zebra_usb.py`)
> vigia e manda para a impressora. Por isso, para imprimir pelo celular o bot
> precisa estar ligado **no PC do escritório**, com a Zebra e o monitor da Zebra
> ativos. De longe você dispara; o papel sai lá. O bot usa a **conta ativa**
> (a mesma escolhida na tela, lida do `config.json`).

Mensagens longas são divididas automaticamente; a atividade fica registrada em
`bot.log`.

**Botões:** `/start` (ou `/menu`) mostra botões **Hoje / Amanhã / Resumo / Todos**
— é só tocar, sem digitar.

**Aviso automático da manhã:** defina `"aviso_horario"` no `bot_config.json` (ex.:
`"08:00"`) e o bot manda o resumo do dia nesse horário (horário de Brasília) para
os `chat_ids`. Deixe em branco/remova para desativar. Precisa do bot ligado no
horário e da dependência de agendador (já incluída no `requirements-bot.txt`).

```bash
pip install -r requirements-bot.txt
copy bot_config.example.json bot_config.json   # e preencha o token do @BotFather
python bot_telegram.py                          # precisa do credenciais.json na mesma pasta
```

Segurança: o **token vem do `bot_config.json`** (não versionado) ou da variável
`TELEGRAM_BOT_TOKEN`, e o bot só responde aos **chat ids autorizados**. Mande
`/id` ao bot para descobrir seu chat id, coloque-o em `chat_ids` e reinicie.

Onde rodar: numa máquina **sempre ligada e com internet** que tenha o projeto e o
`credenciais.json` (ex.: o PC do escritório).

**Ligar por duplo-clique:** use **`Iniciar Bot.bat`** (mantenha a janela aberta — o
bot só responde enquanto ela estiver rodando).

**Ligar com reinício automático (recomendado para o PC do escritório):** use
**`Iniciar Bot (auto).bat`**. Se o bot cair (erro, queda de rede, etc.), ele
**religa sozinho** depois de alguns segundos, em vez de ficar fora do ar sem
ninguém perceber. Para parar de vez, feche a janela (ou `Ctrl+C` → responda *Sim*).
O motivo de cada queda fica registrado em `bot.log`.

**Ligar junto com o Windows (opcional):** clique com o botão direito no
`Iniciar Bot (auto).bat` (ou no `Iniciar Bot.bat`) → *Enviar para → Área de
trabalho (criar atalho)*; depois pressione `Win+R`, digite `shell:startup` e mova
esse atalho para a pasta que abrir. Assim o bot inicia sozinho quando o PC liga —
e, com o lançador automático, se mantém no ar mesmo que caia.

## Shopee (experimental)

Integração com a Shopee Open Platform (API v2). Pré-requisito: criar um app em
https://open.shopee.com, deixá-lo **Live** e cadastrar a **Redirect URL**
`https://joaobz14.github.io/contador/` (página em `docs/`, servida pelo GitHub Pages).

```bash
python pegar_token_shopee.py      # uma vez: autoriza a loja -> credenciais_shopee.json
python shopee_api.py              # grupos prontos para enviar HOJE
python shopee_api.py amanha | todos | dia <AAAA-MM-DD>
python shopee_api.py etiqueta <order_sn>     # gera/baixa a etiqueta na pasta Downloads
python shopee_api.py parametros <order_sn>   # tipos de documento disponiveis (diagnostico)
```

**Fase 1 (leitura):** lista e agrupa por SKU + quantidade, reaproveitando os nomes
(`nomes_sku.json`) e o fuso de Brasília.

**Fase 2 (etiqueta):** a Shopee só gera a etiqueta **depois que o envio foi
organizado** (botão "Organizar Envio" no Seller Center — é o que emite o número de
rastreio/AWB). O comando `etiqueta` busca o AWB (`get_tracking_number`), cria o
documento térmico (`create_shipping_document` com o `tracking_number`, tipo
**`THERMAL_AIR_WAYBILL`**), espera ficar `READY` (`get_shipping_document_result`) e
baixa (`download_shipping_document`). O resultado é um `.zip`
(`etiqueta shopee - <order_sn>.zip`) salvo em **Downloads**, contendo o ZPL
(`~DGR/Z64`). O app da Zebra (`impressora_zebra_usb.py`) reconhece esse ZIP pelo
nome e imprime sozinho — o mesmo caminho do Mercado Livre. Se o envio ainda não foi
organizado, o comando avisa em vez de falhar.

**Atalho (Windows):** dê um duplo-clique em **`Etiqueta Shopee.bat`** — ele lista os
pedidos de hoje, pergunta o `order_sn` e gera a etiqueta, deixando a janela aberta.

## Como a impressão funciona

Ao imprimir um grupo, o programa baixa o ZPL pela API (`/shipment_labels`) e grava
um arquivo `.zip` na pasta **Downloads**, com um nome que um aplicativo separado da
Zebra (`impressora_zebra_usb.py`) monitora e envia automaticamente para a impressora.
Ajuste `PASTA_DOWNLOADS` em `separador_etiquetas_ml.py` caso o seu app monitore
outra pasta.

**Carimbar o SKU na etiqueta:** o checkbox **"Carimbar SKU"** na tela imprime o
código do produto na **DANFE** (nota fiscal), na área livre central (a etiqueta
de envio não é carimbada, pois é cheia e varia de layout), para identificar o
produto ao separar. A escolha fica lembrada (`config.json`). A posição/tamanho do
carimbo são ajustáveis pelas constantes `CARIMBO_X`, `CARIMBO_Y` e `CARIMBO_ALTURA`.

## Nomes amigáveis para os SKUs

Para mostrar o nome do produto ao lado do SKU (ex.: `PRP — Picador Pequeno`),
edite o arquivo **`nomes_sku.json`** com o de‑para `SKU → nome`:

```json
{
  "PRP": "Picador Pequeno",
  "A02": "Outro produto"
}
```

É só exibição: o agrupamento e o controle de impresso continuam pelo SKU. SKUs
sem nome cadastrado seguem mostrando apenas o SKU.

## Arquivos gerados (não versionados)

- `credenciais.json` — segredos e tokens da sua conta.
- `estado_grupos.json` — registra quais grupos já foram impressos no dia.
- `itens_cache.json` — cache de detalhes de produtos.
- `envios_cache.json` — cache de envios já finalizados (pulados nas próximas buscas para acelerar).
- `link_autorizacao.txt` — link de autorização gerado pelo `pegar_token.py`.

## Testes

A lógica do núcleo tem testes automatizados (pytest), sem rede nem arquivos reais.

```bash
pip install -r requirements-dev.txt
pytest
```

### Testar a GUI sem monitor (headless)

A tela (Tkinter) não tem testes automáticos, mas dá para **abrir e tirar um
screenshot** dela em máquinas sem display (ex.: CI / Claude Code na web):

```bash
bash tools/setup_gui_tests.sh          # instala tkinter, xvfb e imagemagick (uma vez)
xvfb-run -a python3.12 tools/gui_screenshot.py out.png            # modo Mercado Livre
xvfb-run -a python3.12 tools/gui_screenshot.py shopee.png Shopee  # modo Shopee
```

Gera um PNG da tela inicial (sem rede/credenciais), útil para conferir o layout
após mudanças visuais. O SessionStart hook já prepara isso em segundo plano.

