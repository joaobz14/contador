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
   e o ciclo inteiro **ler → mesclar → salvar** roda sob **trava entre processos**
   (`estado.trava`, um `.lock` ao lado do arquivo) — GUI e bot na mesma conta não
   apagam a marcação um do outro nem em leituras simultâneas. A trava degrada
   suavemente (sem suporte do sistema de arquivos, opera como antes). A **poda por
   idade** que regrava o arquivo (`carregar(persistir_poda=True)`, só ML) também
   roda sob a mesma trava e **relê o disco** antes de gravar — senão a poda de um
   Atualizar apagaria uma marcação que o bot gravou nesse meio-tempo.
6. Tokens (ML e Shopee) obtidos **sempre via `obter_token`**, nunca `renovar_token`
   direto — o refresh token **rotaciona** e uma corrida pode invalidá-lo.
7. Refresh de token **serializado por lock** (double-checked) — entre threads
   (lock) **e entre processos** (trava de arquivo ao lado das credenciais, via
   `estado.trava` com **`espera=2*TIMEOUT`**: no Windows o `LK_LOCK` desiste em
   ~10s e o refresh dura até 30s — a espera estendida impede o segundo processo
   de degradar no meio do refresh do primeiro; quem espera adota o token salvo
   em vez de renovar de novo).
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
| `awb_cache_shopee.json` | cache de AWB da Shopee (`_cachear_awbs`/`preencher_rastreios`) | Não | por máquina | ❌ Não |
| `bot.log` | atividade/erros do bot | Não | por máquina | ❌ Não |
| backups `.bak` | auto-recuperação de credenciais | **Sim** | por conta | ❌ Não |
| | ⚠ O `.bak` só vale **ao lado do principal que ele espelha** (a migração de conta o leva junto e remove órfãos da raiz). Um `.bak` desgarrado guarda um refresh_token **já rotacionado** (morto) — **nunca** restaurá-lo manualmente para outra pasta: o refresh falharia e, na pior hipótese, invalidaria a conta boa. | | | |
| temporários `.tmp` | gravação atômica de JSON | varia | efêmero | ❌ Não |
| `*.corrupto` | estado ilegível preservado por `ler_estado` (ver risco abaixo) | Não | por evento | ❌ Não |
| **`nomes_sku.json`** | `carregar_nomes` (SKU→nome) | Não | compartilhado | ✅ **Sim** (sincroniza via Git) |
| **`skus_por_anuncio.json`** | `carregar_skus_anuncio` (código do anúncio ML sem SKU → SKU) | Não | compartilhado | ✅ **Sim** (sincroniza via Git) |

## Limitações conhecidas (decisões documentadas, não bugs abertos)

- **Grupos "Sem data" reabrem na virada do dia:** o fallback da chave de estado
  (`grupo.dia or hoje`) foi desenhado para o "hoje implícito" de CLI/bot — o
  radio **Sem data** da GUI (`dia=""`) o herdou. Um pedido **sem prazo** impresso
  hoje e ainda pronto amanhã volta como pendente (o operador vê o grupo
  reaparecer — nada some). Caso raríssimo (o núcleo tenta 4 campos + `/sla`
  antes de ficar sem data). Consertar exigiria mexer na chave de estado (um
  namespace fixo tipo `sem-data|` seria **descartado pela poda**, que valida o
  prefixo de data) — decidiu-se documentar; se aparecer na operação real,
  carimbar a data da coleta no grupo é o caminho.

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
- **`lint`**: `ruff check .` (config `ruff.toml`, regras `F` + `E9`) — pega import
  morto / nome indefinido antes da revisão manual (5.13). `E501` (linha longa)
  fica deferido de propósito.
- **`pytest`** em Python 3.11 e 3.12.
- **`gui-smoke`**: abre a GUI de verdade headless com `xvfb`, nos dois marketplaces,
  via `tools/gui_screenshot.py`; publica os PNGs como artefato. Protege import,
  inicialização do Tkinter e renderização básica da tela — o que o pytest não cobre.

## Áreas de risco (o que quebra se mexer sem cuidado)

- **`marcar_impresso`**: perder o merge com o disco OU remover a trava (`arquivo=` →
  `estado.trava`) → GUI e bot apagam a marcação um do outro (inv. 5; sem a trava,
  duas leituras simultâneas perdem a última gravação — reproduzido em teste).
  Marcar antes da confirmação → imprime errado e some da lista (inv. 1). **Ler o
  estado por `ler_json` em vez de `ler_estado`**: um `estado_grupos.json`/
  `estado_shopee.json` corrompido viraria `{}` mudo e a marcação seguinte
  gravaria por cima, destruindo o recuperável (todos os grupos do dia voltam a
  PENDENTE). `ler_estado` move o corrompido para `.corrupto` com aviso e
  recomeça vazio, sem apagar o antigo (5.2); ausência segue `{}` silencioso,
  falha transitória (OSError) não renomeia.
- **`carregar(persistir_poda=True)`**: regravar a poda **fora da trava** ou **sem
  reler** o disco → a poda de um Atualizar apaga uma marcação concorrente do bot
  (mesma corrida da inv. 5, por uma porta lateral — reproduzido em teste).
- **`obter_token` / `renovar_token`**: chamar `renovar_token` direto ou sem lock →
  corrida entre threads rotaciona o refresh token e **trava a conta** (inv. 6, 7).
- **`_organizar_varios` / `batch_ship_order` (Shopee AWB)**: gerar etiqueta sem AWB →
  `logistics.tracking_number_invalid`; a etiqueta só existe após organizar (inv. 8, 9).
  **`organizar_envio` deve consultar `envio_ja_arranjado` antes de recusar**: um
  pedido já organizado tem `info_needed={}` até o AWB sair — sem o helper, isso
  virava um falso "não oferece drop-off" (5.3). Já arranjado → pular `ship_order`
  e aguardar o AWB.
- **`ProvedorMLAmbas` / `fundir_grupos`**: usar o token/estado da conta errada ao fundir
  → imprime com credencial errada ou marca no arquivo errado. A adoção de anúncio
  sem SKU **não pode ser aplicada em memória** neste modo (os sub-grupos
  `.por_conta` manteriam a chave antiga) — o botão inline re-coleta
  (`_aplicar_adocao`); mudar isso esconde envios do lote e grava estado na chave
  errada (reproduzido em teste na auditoria).
- **`preparar_lotes` / `gerar_zip_lotes` / `imprimir_pendentes`**: alterar a ordem
  "gera → confirma → marca" fura a invariante 1. A interface de provedor **não
  tem `imprimir_grupo` de propósito** (um método de grupo que marcasse direto
  seria uma arma engatilhada para um botão novo) — há teste-guardião
  (`test_provedores_nao_expoe_imprimir_grupo`).
- **Botões de impressão do Telegram (`cb_botao`)**: deixar imprimir Shopee, ou imprimir
  um grupo antigo após troca de conta/loja (inv. 10, 11).
- **Pasta Downloads / app Zebra**: mudar o **prefixo** do nome do ZIP quebra a
  detecção pelo app externo — o papel não sai. O **restante** do nome, ao
  contrário, precisa ser **único** por trabalho (`nome_saida_unico`): nome
  determinístico + `tmp.replace` apagava em silêncio um lote que o monitor ainda
  não consumira (auditoria 5.1). Antes de gerar, a GUI **relê o estado do disco**
  (`prov.carregar_estado`) — pendente calculado sobre estado defasado imprime em
  dobro o que foi marcado por fora (CLI/2ª GUI).

## Desempenho da impressão Shopee (medido em produção)

Cronometragem real por fase (`shopee_tempos.log`, via `_log_tempos`) mostrou onde o
tempo realmente vai — e desfez duas hipóteses erradas:

| Fase | Custo medido | Natureza |
|---|---|---|
| **Organizar** (`ship_order` → AWB) | **~14s FIXO** (1 pedido ou 4, dá o mesmo) | Latência do servidor da Shopee para emitir o AWB. **Não escala com a quantidade e não dá para apressar** — o documento exige o AWB, então não há como adiantar nem encavalar. É o **piso** da plataforma. |
| **Gerar+baixar** (`create` → READY → download) | **~5s por pedido**, mas **paralelizável** | Num pedido único de documento para vários, a Shopee gera **em série**; em **requests concorrentes**, ela processa **em paralelo**. |

**Decisão (medida, não teórica):** `_gerar_lote` gera **um documento por pedido, em
paralelo** (8 por vez) e combina num ZIP único. Resultado real: 4 pedidos caíram de
**~20s → ~6s** na fase de gerar (~70%); projeção de 25 pedidos: **~2 min → ~40s** no total.

**O que NÃO acelera:** `batch_ship_order` (organizar N num request) foi testado com a
loja real e **não muda o tempo** — organizar é latência fixa do AWB, não número de
chamadas. Mantido (sem downside), mas **não é o ganho**. Regra prática para a Shopee:
o AWB é um piso intransponível; o ganho está em **paralelizar por pedido** as chamadas
que a plataforma processa concorrentemente (a geração do documento).

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
