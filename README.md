# Separador de Etiquetas — Mercado Livre

Ferramenta em Python para **separar e imprimir etiquetas de envio do Mercado Livre**
em lote. Ela lê os pedidos da conta, mantém apenas os que estão em
**"Etiquetas para imprimir"** (`ready_to_ship` + `ready_to_print`) e os agrupa por
**produto + quantidade do pedido**, gerando as etiquetas em formato **ZPL** (Zebra).

A identidade de cada produto é definida nesta ordem de prioridade:
**SKU → GTIN + voltagem → `item_id:variação`**.

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

## Configuração (uma vez só)

```bash
python pegar_token.py
```

Siga as instruções na tela. Ao final será criado o arquivo `credenciais.json`
com o `refresh_token` e o `seller_id` da sua conta.

> ⚠️ **Nunca** compartilhe ou versione o `credenciais.json`: ele contém segredos
> da sua aplicação. Esse arquivo já está no `.gitignore`.

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
python separador_etiquetas_ml.py proximo    # imprime o próximo grupo pendente
python separador_etiquetas_ml.py rastrear <SKU>            # diagnóstico de um SKU
```

### Interface gráfica

Mostra os grupos do dia (produto + quantidade) com um botão **Imprimir** em cada um.

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

## Bot do Telegram (opcional — consulta)

Permite consultar os pedidos pelo celular (somente leitura). Não imprime nem
altera nada — só lê via o núcleo. Comandos:

- `/hoje`, `/amanha`, `/dia AAAA-MM-DD`, `/todos` — grupos por dia de despacho
- `/detalhar SKU` — composição de um SKU (itens/variações que o formam)
- `/resumo` — quantos pacotes por dia
- `/id` — mostra seu chat id (para liberar no `chat_ids`)

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

**Ligar junto com o Windows (opcional):** clique com o botão direito no
`Iniciar Bot.bat` → *Enviar para → Área de trabalho (criar atalho)*; depois
pressione `Win+R`, digite `shell:startup` e mova esse atalho para a pasta que
abrir. Assim o bot inicia sozinho quando o PC liga.

## Shopee (experimental — Fase 1: leitura)

Integração inicial com a Shopee Open Platform (somente **listar/agrupar**, ainda
sem impressão). Pré-requisito: criar um app em https://open.shopee.com e autorizar
a loja.

```bash
python pegar_token_shopee.py      # uma vez: autoriza a loja -> credenciais_shopee.json
python shopee_api.py              # grupos prontos para enviar HOJE
python shopee_api.py amanha | todos | dia <AAAA-MM-DD>
```

Reaproveita o agrupamento por SKU + quantidade, os nomes (`nomes_sku.json`) e o
fuso de Brasília. A impressão das etiquetas da Shopee fica para a Fase 2.

## Como a impressão funciona

Ao imprimir um grupo, o programa baixa o ZPL pela API (`/shipment_labels`) e grava
um arquivo `.zip` na pasta **Downloads**, com um nome que um aplicativo separado da
Zebra (`impressora_zebra_usb.py`) monitora e envia automaticamente para a impressora.
Ajuste `PASTA_DOWNLOADS` em `separador_etiquetas_ml.py` caso o seu app monitore
outra pasta.

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

