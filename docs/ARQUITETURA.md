# Arquitetura e operação — notas de apoio

> Documento de apoio para leitura arquitetural (humanos e o grafo Graphify em
> `graphify-out/`). **Não** descreve regra de negócio nova — apenas consolida a
> operação real, os fluxos, as invariantes e os riscos já existentes no código.
> Fonte primária das regras: `CLAUDE.md` e `docs/CHANGELOG.md`.

## Sistemas externos (fora do repositório, essenciais à operação)

| Sistema | Papel | Vive no repo? |
|---|---|---|
| **Mercado Livre API** | Fonte dos pedidos, detalhes, envios e etiquetas ZPL (ML). | Não |
| **Shopee Open Platform API (v2)** | Pedidos, organização de envio, AWB, documento térmico (Shopee). | Não |
| **Telegram Bot API** | Canal do bot de consulta/impressão. | Não |
| **Impressora térmica Zebra** | Hardware que imprime o ZPL. | Não |
| **App `impressora_zebra_usb.py`** | Programa **externo** que monitora a pasta Downloads e envia o ZIP para a Zebra. | Não (outro projeto) |
| **Pasta Downloads** | Ponto de entrega do ZIP; **ponte** entre este app e a Zebra. É **por máquina**. | Não |
| **GitHub Actions** | CI: roda pytest e o smoke da GUI headless. | Config sim (`.github/`), execução não |

## Fluxos operacionais

### Fluxo geral de impressão
pedidos prontos → coleta pela API do marketplace → filtragem por dia de despacho →
agrupamento por produto + quantidade → geração de ZPL → geração de ZIP → gravação
na pasta **Downloads** → app Zebra detecta o ZIP → impressora térmica imprime →
**usuário confirma que saiu certo** → só então o sistema marca como impresso.

### Fluxo da GUI (Tkinter)
escolher marketplace → (se ML) escolher conta → escolher dia de despacho → **Atualizar**
→ a GUI chama o **provedor** correspondente → provedor coleta grupos → GUI separa
pendentes / parciais / impressos → usuário seleciona → **GUI gera etiquetas sem marcar
estado** → GUI pergunta "as etiquetas saíram certo?" → só após confirmação chama
`marcar_impresso`.

### Fluxo Shopee (Fase 2)
listar `READY_TO_SHIP` → buscar detalhes → agrupar por SKU/quantidade → **organizar
envio como drop-off/Postagem** (`ship_order`) → gerar **AWB/tracking_number** →
`create_shipping_document` (exige o tracking) → aguardar status `READY` → baixar
etiqueta → combinar ZPLs quando necessário → salvar ZIP da Shopee → marcar estado
**só após a confirmação da GUI**.

### Fluxo Mercado Livre "🌐 Ambas"
listar contas configuradas → coletar grupos de cada conta → **fundir** grupos por
SKU + quantidade (`fundir_grupos`; subgrupos em `.por_conta`) → baixar etiquetas
usando o **token da conta correta** → gerar um **ZIP único** → marcar estado no
arquivo **da conta correta** → **não** persistir "Ambas" como conta ativa definitiva.

### Fluxo Telegram
bot carrega config local → valida `chat_id` → usuário escolhe loja → **ML: consulta e
impressão** / **Shopee: só consulta** → bot guarda a lista de grupos em `chat_data` →
antes de imprimir, valida que loja/conta ainda são as mesmas → imprime na **máquina
onde o bot roda** (ZIP cai no Downloads dessa máquina) → registra em `bot.log`.

## Invariantes críticas (não podem ser quebradas)

1. A GUI **nunca** marca impresso antes da confirmação física do usuário.
2. **Reimpressão nunca altera** o estado de impresso.
3. Estado de impresso é **por marketplace + conta + dia de despacho**.
4. Envio novo em grupo já impresso **reabre o grupo como parcial**.
5. `marcar_impresso` **recarrega do disco e mescla** antes de gravar (last-writer-merge)
   — GUI e bot na mesma conta não apagam a marcação um do outro.
6. Tokens (ML e Shopee) obtidos **sempre via `obter_token`**, nunca `renovar_token`
   direto — o refresh token **rotaciona** e uma corrida pode invalidá-lo.
7. Refresh de token **serializado por lock** (double-checked).
8. Na Shopee, a etiqueta **só existe após organizar o envio e obter o AWB**.
9. `create_shipping_document` **exige `tracking_number`** no corpo.
10. O bot **não imprime grupos da Shopee** (só consulta).
11. O bot **não imprime grupos antigos** se a conta/loja ativa mudou.
12. Credenciais, estado, cache e config **são locais e nunca versionados**.

## Arquivos locais não versionados

| Arquivo | Módulo/uso | Segredo? | Escopo | Versionar? |
|---|---|---|---|---|
| `credenciais.json` | núcleo ML (`obter_token`) | **Sim** | por conta (`contas/{nome}/`) | ❌ Não |
| `credenciais_shopee.json` | `shopee_api` (`obter_token`) | **Sim** | por loja (única) | ❌ Não |
| `estado_grupos.json` | `marcar_impresso`/`status_grupo` (ML) | Não | por conta + dia | ❌ Não |
| `estado_shopee.json` | estado de impresso (Shopee) | Não | por dia | ❌ Não |
| `config.json` | `aplicar_config` (preferências) | Não | por máquina | ❌ Não |
| `bot_config.json` | `bot_telegram` (token do bot) | **Sim** | por máquina | ❌ Não |
| `itens_cache.json` | cache de detalhes de produto | Não | por conta | ❌ Não |
| `envios_cache.json` | `filtrar_para_imprimir` (envios finalizados) | Não | por conta | ❌ Não |
| `bot.log` | atividade/erros do bot | Não | por máquina | ❌ Não |
| backups `.bak` | auto-recuperação de credenciais | **Sim** | por conta | ❌ Não |
| temporários `.tmp` | gravação atômica de JSON | varia | efêmero | ❌ Não |
| **`nomes_sku.json`** | `carregar_nomes` (SKU→nome) | Não | compartilhado | ✅ **Sim** (sincroniza via Git) |

## Testes como documentação viva (que regra cada um protege)

| Teste | Protege |
|---|---|
| `tests/test_estado.py` | ciclo de vida do estado, marcação parcial, mescla com disco, limpeza antiga (inv. 3, 4, 5) |
| `tests/test_lotes.py` | geração em lote **sem** marcar estado antes da confirmação (inv. 1) |
| `tests/test_shopee.py` | assinatura HMAC, AWB, documento térmico, READY, ZIP/ZPL, falha parcial, organização (inv. 8, 9) |
| `tests/test_ambas.py` | fusão de grupos, multi-conta, marcação no estado da conta correta (inv. contexto Ambas) |
| `tests/test_bot_impressao.py` | botões, troca de conta/loja, impedir imprimir Shopee pelo bot (inv. 10, 11) |
| `tests/test_rede.py` | retry/backoff em chamadas de rede |
| `tests/test_datas.py` | datas no fuso de Brasília |
| `tests/test_agrupar.py` + `tests/test_identidade.py` | identidade do produto (SKU→GTIN+voltagem→variação) e agrupamento por envio |
| `tests/test_config.py` | preferências locais (`config.json`) |
| `tests/test_provedores.py` | a interface comum entre GUI e marketplaces |

## CI (qualidade)

`.github/workflows/testes.yml` roda em push para `main` e em PR:
- **`pytest`** em Python 3.11 e 3.12.
- **`gui-smoke`**: abre a GUI de verdade headless com `xvfb`, nos dois marketplaces,
  via `tools/gui_screenshot.py`; publica os PNGs como artefato. Protege import,
  inicialização do Tkinter e renderização básica da tela — o que o pytest não cobre.

## Áreas de risco (o que quebra se mexer sem cuidado)

- **`marcar_impresso`**: perder o merge com o disco → GUI e bot apagam a marcação um do
  outro (inv. 5). Marcar antes da confirmação → imprime errado e some da lista (inv. 1).
- **`obter_token` / `renovar_token`**: chamar `renovar_token` direto ou sem lock →
  corrida entre threads rotaciona o refresh token e **trava a conta** (inv. 6, 7).
- **`_organizar_varios` / `batch_ship_order` (Shopee AWB)**: gerar etiqueta sem AWB →
  `logistics.tracking_number_invalid`; a etiqueta só existe após organizar (inv. 8, 9).
- **`ProvedorMLAmbas` / `fundir_grupos`**: usar o token/estado da conta errada ao fundir
  → imprime com credencial errada ou marca no arquivo errado.
- **`preparar_lotes` / `gerar_zip_lotes` / `imprimir_pendentes`**: alterar a ordem
  "gera → confirma → marca" fura a invariante 1.
- **Botões de impressão do Telegram (`cb_botao`)**: deixar imprimir Shopee, ou imprimir
  um grupo antigo após troca de conta/loja (inv. 10, 11).
- **Pasta Downloads / app Zebra**: mudar o prefixo do nome do ZIP quebra a detecção pelo
  app externo — o papel não sai.

## Perguntas que o grafo enriquecido deve responder

- O que acontece entre clicar "Imprimir selecionados" e marcar um grupo como impresso?
- Por que a GUI não marca estado imediatamente após gerar o ZIP?
- Como a Shopee passa de pedido pronto para etiqueta térmica? Onde o AWB entra?
- Como o modo "Ambas" garante token e estado corretos por conta?
- Quais arquivos são locais da máquina e não devem ir para o Git?
- O que o bot do Telegram pode imprimir e o que só pode consultar?
- Quais testes protegem a regra de não marcar antes da confirmação?
- Como o CI valida a GUI sem monitor?
- Qual o papel do app externo da Zebra?
- O que pode quebrar se `marcar_impresso` ou `obter_token` forem alterados/bypassados?
