# Separador de Etiquetas — Mercado Livre

Ferramenta em Python para **separar e imprimir etiquetas de envio do Mercado Livre**
em lote. Ela lê os pedidos da conta, mantém apenas os que estão em
**"Etiquetas para imprimir"** (`ready_to_ship` + `ready_to_print`) e os agrupa por
**produto + quantidade do pedido**, gerando as etiquetas em formato **ZPL** (Zebra).

A identidade de cada produto é definida nesta ordem de prioridade:
**SKU → GTIN + voltagem → `item_id:variação`**.

## Arquivos

| Arquivo | Papel |
|---|---|
| `pegar_token.py` | Configuração inicial (uma vez só): faz o fluxo OAuth do Mercado Livre e gera o `credenciais.json`. |
| `separador_etiquetas_ml.py` | Núcleo da aplicação + interface de linha de comando (CLI). |
| `separador_gui.py` | Interface gráfica (Tkinter) que reaproveita o núcleo. |
| `credenciais.example.json` | Modelo do arquivo de credenciais (copie para `credenciais.json`). |

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
- `link_autorizacao.txt` — link de autorização gerado pelo `pegar_token.py`.

## Testes

A lógica do núcleo tem testes automatizados (pytest), sem rede nem arquivos reais.

```bash
pip install -r requirements-dev.txt
pytest
```

