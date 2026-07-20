# Guia do projeto (para o Codex)

> **Comece por aqui (chat novo):**
> 1. Leia este guia inteiro — convenções + pegadinhas de domínio.
> 2. Para **arquitetura/relações** ("quem chama X?", "o que quebra se eu mexer em
>    Y?"), **consulte o grafo `graphify-out/`** (skill graphify: `query`/`path`/
>    `explain`; sem o CLI, leia `graph.json`) e `docs/ARQUITETURA.md` — **antes**
>    de reler arquivos crus.
> 3. **Antes de mexer em estado / token / impressão**, `docs/ARQUITETURA.md` é
>    leitura obrigatória (12 invariantes críticas + áreas de risco).
> 4. **NÃO** rode `graphify hook install` (apagaria a camada de docs do grafo).
> 5. Backlog técnico sugerido em `docs/PRIORIDADES_TECNICAS.md`.

Ferramenta em Python para **separar e imprimir etiquetas de envio** de marketplaces
(Mercado Livre e Shopee) numa impressora térmica Zebra. Lê os pedidos prontos,
agrupa por **produto + quantidade**, gera **ZPL** e entrega um `.zip` na pasta
**Downloads**, que um app separado da Zebra (`impressora_zebra_usb.py`, fora deste
repo) monitora e imprime.

## Mapa do código

| Arquivo | Papel |
|---|---|
| `separador_etiquetas_ml.py` | Núcleo: API do ML, agrupamento, ZPL, carimbo, CLI. |
| `estado.py` | Camada comum do estado "já impresso" (ML+Shopee) + IO JSON atômico. |
| `registro.py` | Log operacional (`separador.log`) + redação de segredos (`sem_segredos`). |
| `shopee_api.py` | Integração Shopee (API v2): listar, organizar envio, etiqueta, estado. |
| `provedores.py` | Abstração de marketplace (`ProvedorML`/`ProvedorShopee`) usada pela GUI. |
| `separador_gui.py` | Tela Tkinter (loja + conta + dia útil, busca, marcar todos, editor de Nomes). Usa `provedores`. |
| `bot_telegram.py` | Bot do Telegram: **consulta** (ML e Shopee) e **impressão só do ML** (com confirmação; marca direto — não vê a impressora). |
| `relatorio.py` | Formata textos para o bot. |
| `pegar_token.py` / `pegar_token_shopee.py` | OAuth inicial (gera credenciais). |
| `tools/` | Ferramentas de dev (screenshot da GUI headless). |

## Comandos

```bash
pytest                                   # testes (sem rede; python 3.11)
python separador_gui.py                  # abre a tela (precisa de display)
python shopee_api.py etiqueta <order_sn> # gera/baixa etiqueta Shopee
```

**Testar a GUI sem display** (o python 3.11 do projeto não tem tkinter; usa-se o
`python3.12` do sistema):
```bash
bash tools/setup_gui_tests.sh                              # 1x: tkinter+xvfb+imagemagick
xvfb-run -a python3.12 tools/gui_screenshot.py out.png [Shopee]
```
Depois `Read out.png` para conferir o layout. O SessionStart hook já prepara isso
em 2º plano.

## Grafo de conhecimento (graphify) e docs de apoio

- **`graphify-out/`** tem um grafo do projeto (código AST + docs + arquitetura):
  `graph.json` (consultável), `GRAPH_REPORT.md` (relatório) e `graph.html`
  (visualização). Para perguntas de arquitetura/relações, consulte o grafo e o
  `docs/ARQUITETURA.md` **antes** de reler os arquivos crus (ex.:
  `graphify query "..."`, `graphify path "A" "B"`, `graphify explain "X"`).
  - **O que confiar:** o **inventário de nós** (módulos/funções) e a **camada de
    "porquês"** (`rationale`/`concept`) são mantidos à mão e estão **em dia**. Já
    a **camada AST** (arestas de `calls`/`imports`), as **métricas** do relatório
    (centralidade, "perguntas sugeridas") e o **`graph.html`** são um **snapshot
    do último build completo** — só um rebuild com o CLI os re-deriva (ver a nota
    no topo do `GRAPH_REPORT.md`).
- **`docs/ARQUITETURA.md`**: fluxos operacionais, **invariantes críticas**,
  arquivos locais e áreas de risco — leitura obrigatória antes de mexer em
  estado/token/impressão. **`docs/PRIORIDADES_TECNICAS.md`**: backlog técnico
  sugerido (ordem recomendada de evolução). **`docs/AMAZON_SP_API.md`**:
  levantamento (pesquisa, nada implementado) de como a Amazon SP-API encaixaria
  no app no futuro — o risco decisivo é de negócio/BR (só FBM/MFN gera etiqueta).
- **`CLAUDE.md` é espelho deste arquivo** (adaptado para o Claude Code: título e
  trailer). Alterou uma convenção aqui? Replique lá.
- **NÃO rode `graphify hook install`**: o hook reconstrói o grafo só com código
  (AST) e apagaria a camada de docs/arquitetura — foi desinstalado de propósito.
  Após mudanças grandes, refaça a extração completa + a passada semântica dos
  docs manualmente.
- **SEMPRE atualize o grafo com o que aprender:** ao terminar uma tarefa,
  acrescente ao `graphify-out/graph.json` os módulos/funções novos e, como nós de
  `rationale`/`concept`, as **descobertas, barreiras e soluções** encontradas
  (ligue-as com `rationale_for`/`calls`/`imports`/`conceptually_related_to`).
  Registre também um resumo em "Atualizações manuais (pós-build)" no
  `GRAPH_REPORT.md`. Edite o JSON direto (sem o CLI); valide que não sobraram
  arestas órfãs. Isso preserva a camada de docs até o próximo rebuild completo.

## Convenções

- **Provedor, não `if marketplace`:** a GUI fala com `self.prov` (ML ou Shopee). Toda
  capacidade nova de impressão/coleta entra como método do provedor.
- **Estado de "já impresso"** é por marketplace e por **dia de despacho**: ML em
  `contas/{conta}/estado_grupos.json`, Shopee em `estado_shopee.json`. Chave:
  `{dia}|{chave}|q{qtd}`. A lógica é única em **`estado.py`** (`chave_estado`,
  `impressos`, `status_grupo`, `envios_pendentes`, `limpar_antigo`, `carregar`,
  `marcar_impresso`); núcleo e `shopee_api` só expõem wrappers finos que passam o
  seu `ARQUIVO_ESTADO`. Continue usando os helpers do núcleo (`status_grupo`,
  `envios_pendentes`, `marcar_impresso`) — não reimplemente o merge. O ciclo
  ler→mesclar→salvar do `marcar_impresso` roda sob **trava entre processos**
  (`estado.trava`, `.lock` ao lado do arquivo, gitignorado) quando o wrapper passa
  `arquivo=` — sem ela, duas leituras simultâneas (tela + bot) perdem marcação.
  A trava degrada suavemente; o `.tmp` do `gravar_json` inclui o PID. A **poda por
  idade** que regrava o arquivo (`carregar(persistir_poda=True)`, ML **e** Shopee
  desde 5.7 — antes a Shopee só podava em memória e o `estado_shopee.json` crescia
  sem limite) usa a mesma trava e **relê o disco** antes de gravar — senão um
  Atualizar apagaria uma marcação que o bot gravasse no meio-tempo (mesma corrida,
  por uma porta lateral).
- **Multi-conta (ML):** arquivos por conta em `contas/{nome}/`; `definir_conta()`
  troca os globais. Shopee é **uma loja só** (`credenciais_shopee.json`).
- **Config sempre via `aplicar_config()`** — é o ponto único de **saneamento** do
  `config.json` (`_sanear_config`): valor de tipo/valor inválido é descartado e
  cai no default (um config editado à mão não pode derrubar a GUI/bot na
  abertura). Valores válidos de identificação: `MODOS_IDENT`.
- **Gravar config por chave via `atualizar_config(**chaves)`, não `salvar_config`
  do dict inteiro:** cada GUI mantém `self.config` desde a abertura; regravar o
  dicionário inteiro reverte em silêncio as chaves que outra instância mudou
  (lost update — fechar uma GUI de manhã desfazia a conta/marketplace da outra,
  5.4). `atualizar_config` relê o disco **sob `estado.trava`**, aplica só as
  chaves do evento e saneia. A GUI mantém `self.config[chave]` local (sua própria
  visão) e persiste via `atualizar_config(chave=valor)`. `salvar_config` (dict
  inteiro) fica só para o bot/testes.
- **Modo "🌐 Ambas" (ML):** radio extra no seletor de conta (dia de motorista
  único). `ProvedorMLAmbas` coleta as contas em sequência e **funde** grupos de
  mesmo SKU+qtd (`fundir_grupos`; sub-grupos em `.por_conta`); imprime cada
  conta com o token dela num ZIP único; estado segue **por conta** (o
  `marcar_impresso` roteia com `definir_conta` antes de cada gravação). A GUI
  consulta status/pendentes **via provedor** (`prov.status_grupo`, não o core
  direto). Não é persistido no config (escolha pontual).
- **Token: sempre `obter_token(cred)`** (ML e Shopee) — cache + lock double-checked.
  Nunca chamar `renovar_token` direto: o refresh_token **rotaciona** e uma corrida
  pode invalidá-lo (travando a conta). O lock de thread só cobre **threads**;
  dentro dele o ciclo relê-ou-renova roda sob a **trava de arquivo**
  (`estado.trava`, `.lock` ao lado das credenciais) que serializa **processos**
  (GUI + bot na mesma conta): quem chega depois espera, **relê o disco**
  (`_ler_json(ARQUIVO_CRED)`) e adota o token salvo pelo primeiro — nunca dois
  refreshes em paralelo. A trava degrada suave (sem ela, relê o disco como
  antes), mas no caminho do token ela é adquirida com **`espera=2*TIMEOUT`**: no
  Windows o `msvcrt.LK_LOCK` desiste sozinho em ~10s e, sem a espera estendida,
  o segundo processo degradaria **no meio** do refresh do primeiro (HTTP de até
  30s) — re-tentando até superar a duração máxima da operação, degradar depois
  disso é seguro (o detentor já salvou; a releitura adota).
  `renovar_token` **não re-tenta** (`tentativas=1`): re-tentar o refresh grant após
  o servidor já ter rotacionado gastaria um token de uso único.
- **Escrita de JSON é atômica e durável** (`.tmp` + `flush`/`fsync` → `replace`) e
  leitura tolerante. Credenciais têm espelho **`.bak`** com auto-recuperação
  (queda de energia não exige refazer o token); `.bak` é gitignorado. O `.bak`
  só vale **ao lado do principal** (a migração de conta o leva junto e remove
  órfãos da raiz) — um `.bak` desgarrado tem refresh_token já rotacionado (morto).
- **Estado de impressão lê por `estado.ler_estado`, não `ler_json`:** `ler_json`
  silencia qualquer falha como `{}` (certo p/ config → `_sanear_config`, cred →
  `.bak`, caches → refazer). No **estado** isso é perigoso: corrompido lido como
  `{}` faz todos os grupos voltarem a PENDENTE e a **próxima marcação grava por
  cima**, destruindo o recuperável. `ler_estado` distingue **corrupção**
  (existe mas não parseia, ou não é dict → move p/ `.corrupto` com aviso e
  recomeça vazio, sem apagar o antigo) de **ausência** (`{}` silencioso) e de
  **falha transitória** (OSError → `{}` sem renomear; o arquivo pode estar só
  preso pelo OneDrive). Usado por `carregar` e pelo `ler` injetado no
  `marcar_impresso` (núcleo e Shopee). `.corrupto` é gitignorado.
- **Fuso:** sempre Brasília (`TZ_BR`, `_hoje_br()`, `_amanha_br()`).
- **Dia de despacho:** a GUI mostra os próximos **dias úteis** (`proximos_dias_uteis()`
  + `rotulo_dia()`) e passa a data escolhida como `dia=` (ML e Shopee filtram igual;
  `dia=""` filtra os sem data). Após um Atualizar, o provedor preenche
  `contagem_dias` ({data: n}, da MESMA busca — `resumo_por_dia` no ML,
  `contagem_por_dia` na Shopee) e o seletor mostra a contagem por dia + a linha
  "Outras datas" (fim de semana/atrasadas/sem data) — nenhum pedido fica invisível.
- **Nomes amigáveis:** `nomes_sku.json` (versionado; sincroniza via git) mapeia
  SKU → nome. Editável na GUI pelo botão **✏ Nomes** (`EditorNomes`, com setas
  ↑/↓); use `carregar_nomes()`/`salvar_nomes()` (apara, descarta vazios). A **ordem
  das chaves é significativa e PRESERVADA** (não alfabética) — é a ordem de
  separação (ver ordenação abaixo). **Editores são instância única e travados na
  operação (5.5):** `EditorNomes`/`EditorSkusAnuncio` são editores de
  *substituição total* (a ordem importa, não dá para mesclar duas edições); um 2º
  clique traz a janela aberta para frente (`_focar_editor_aberto`) em vez de abrir
  outra que sobrescreveria a primeira. Os botões ✏ Nomes / 🏷 SKUs / inline 🏷
  Atribuir SKU ficam **desabilitados durante `ocupado`** e nada muta `self.grupos`
  no meio de uma impressão (`_atribuir_sku` e o `_fechar` do EditorNomes checam
  `ocupado`; o arquivo já foi salvo, reflete no próximo render).
- **Anúncio ML sem SKU → SKU:** anúncios antigos sem `seller_sku` caem no código
  do anúncio (`{item_id}:{var_id}` ou `GTIN:…`) como chave e usam o título como
  nome. O de-para **`skus_por_anuncio.json`** (versionado) os **adota** num SKU do
  sistema: `identidade(item, cache, skus_anuncio)` reescreve a chave para o SKU
  (aí agrupa/ordena/carimba/nomeia igual); `extrair_itens` carrega o mapa e repassa.
  Editável na GUI de dois jeitos: botão **🏷 Atribuir SKU** no grupo sem SKU
  (`_sem_sku` = `':'` na chave, só ML, sem combo) e a janela **🏷 SKUs**
  (`EditorSkusAnuncio`). Use `carregar_skus_anuncio()`/`salvar_skus_anuncio()`.
  O **botão inline aplica na hora, em memória** (`_aplicar_mapa_anuncios_local`
  reescreve a chave e **funde** por SKU+qtd — sem re-buscar na API); a **janela
  gerenciadora re-coleta** ao fechar (permite remover/editar, que precisa refazer
  a identidade do zero). **Exceção: no modo 🌐 Ambas o botão inline RE-COLETA**
  (`_aplicar_adocao` roteia para `atualizar`) — os sub-grupos `.por_conta` não
  são reescritos em memória; aplicar local esconderia envios do lote e marcaria
  o estado na chave antiga do anúncio (reimpressão na coleta seguinte).
- **Ordem dos grupos (tela + impressão):** `ordenar_grupos` (usado por `agrupar` e
  `fundir_grupos`) ordena por **quantidade primeiro** (mantém os blocos "qtd 1",
  "qtd 2"…) e, **só no bloco de qtd 1**, segue a **ordem da aba Nomes**; SKU não
  cadastrado vai pro fim em ordem **natural** (`A2` antes de `A10`). Blocos de 2+
  seguem por nome (inalterado). A GUI não reordena — usa a ordem que `agrupar`
  devolve; o `EditorNomes` reordena `app.grupos` ao fechar pra refletir na hora.
- **Identificação na impressão** (`MODO_IDENT`): `carimbo` (SKU na DANFE),
  `carimbo_nome` (nome da aba Nomes; fonte adaptativa via `_fonte_nome` — curto
  maior, longo menor até 3 linhas; sem nome cadastrado cai no SKU; pedido com
  2+ unidades ganha "2x"/"3x" em destaque abaixo do nome), `divisoria`,
  `nenhuma`. `CARIMBAR_SKU` é legado (compat de config antigo). **Encoding:** o
  nome vai em UTF-8 e o campo do carimbo é envolto por `^CI28`…`^CI0` (`^CI28` só
  antes do `^FD`, reset logo após o `^FS`) — sem isso os acentos saem embolados na
  Zebra; o `^CI0` evita vazar o encoding para a etiqueta de envio (o `^CI`
  persiste). A `divisoria` liga `^CI28` e **fecha com `^CI0` antes do `^XZ`**
  (5.8) — sem o reset, o `^CI` persistente vazaria UTF-8 para as DANFEs/etiquetas
  do lote seguintes. **Não** converta o nome para CP850 (o app da Zebra lê o ZPL
  como UTF-8).
- **Identificação na Shopee (sem carimbo):** a etiqueta Shopee é uma imagem pronta
  **sem o nome do produto** (e não há faixa livre estável para carimbar — validado
  com 10 etiquetas: o miolo varia com a rota). Então a **tela** substitui o carimbo
  listando o **código de rastreio (AWB) de cada etiqueta já impressa** do grupo
  (`Grupo.rastreios`), à esquerda, embaixo do nome — o operador cruza o código da
  etiqueta física com o produto. Preenchido no `preencher_rastreios` (todos os
  envios impressos) e na hora da impressão (dos `awbs`, via `_somar_rastreios` —
  **UNE** aos já exibidos; substituir apagaria os códigos antigos de um grupo
  parcial até a próxima coleta). O AWB é imutável, então é **cacheado no momento
  da impressão** (`_cachear_awbs` → `awb_cache_shopee.json`, local); o
  `preencher_rastreios` lê do cache primeiro (menos rede e códigos confiáveis,
  vindos da impressão e não de um refetch que pode falhar) e só busca os
  ausentes, podando o cache junto com o estado.
  Pendentes não têm AWB (só existe após organizar), então não mostram código.
- **Impressão:** ZPL → `.zip` em `PASTA_DOWNLOADS` com nome que a Zebra reconhece
  (prefixos: `etiqueta de envio` p/ ML, `etiqueta shopee` p/ Shopee). O nome
  carrega um **carimbo de tempo único** (`nome_saida_unico`, no núcleo; a Shopee
  chama `core.nome_saida_unico`) — nome determinístico + `replace` apagava em
  silêncio um lote que o monitor ainda não consumiu (dois trabalhos com o mesmo
  rótulo escreviam no mesmo arquivo). O **prefixo é o que o monitor casa**, então
  o sufixo é livre; a correção vem do laço que busca um nome inexistente (soma
  `-1`, `-2`… na colisão), o carimbo só o torna legível. **Antes de gerar, a GUI
  relê o estado do disco** (`prov.carregar_estado()` em `_gerar_sem_marcar_thread`):
  os pendentes vêm de `self.estado` da última coleta — sem reler, uma marcação
  gravada por fora (CLI/2ª GUI) sairia em dobro. Releitura é best-effort (falhou
  → segue com o estado em memória). A gravação é atômica via **`tmp_saida`**
  (`tmp_{nome}.part`): o temporário **não pode casar** com os prefixos nem com as
  extensões (`*.zip`/`*.plain`) que o monitor vigia — exigência do contrato do
  app Zebra v1.25.5+ (item B); teste-guardião
  `test_tmp_saida_nao_casa_o_que_o_monitor_vigia`.
- **Segredos nunca versionados** (ver `.gitignore`): credenciais, estado, caches,
  `config.json`, `bot_config.json`, logs (`bot.log`, `shopee_tempos.log`,
  `separador.log`).
- **Log operacional (`separador.log`, via `registro.py`):** a GUI registra
  loja/conta/dia, contagens, confirmação (sim/não) e falhas — para diagnóstico
  sem debugger. Duas regras: (1) log **nunca** atrapalha a operação (defensivo,
  `try/except`, `delay=True`); (2) **nunca** logue segredos — passe todo texto de
  exceção por `registro.sem_segredos()` antes (um `HTTPError` da Shopee carrega a
  URL com `access_token`/`sign`). O ponto único de erro da GUI (`_erro`) já redige.
- **Toda impressão pela GUI confirma antes de marcar:** gera mas NÃO marca; a
  tela pergunta "as etiquetas saíram certo?" e só então marca (vale p/ ML e
  Shopee, lote E individual — o individual roteia pelo fluxo do lote). Bot/CLI
  marcam direto (não têm como ver a impressora).
- **Trava de ponta a ponta na impressão (anti-duplicata):** o app fica `ocupado`
  **desde a confirmação de "Organizar envio" até você responder "saíram certo?"**
  — `imprimir_lotes`/`imprimir` chamam `_ocupar(True)` antes do
  `_confirmar_organizar` e o `_ocupar(False)` só roda no **`finally` de
  `_confirmar_e_marcar`** (por isso ele delega o corpo a
  `_confirmar_e_marcar_corpo`). Sem essa trava havia uma janela perigosa: na
  Shopee a etiqueta **já sai fisicamente durante a busca** (ZIP→Downloads→Zebra),
  mas o estado só é marcado depois da confirmação — com o botão reabilitado nesse
  meio, um 2º clique reimprimia o mesmo lote (o `if self.ocupado: return` não
  pegava porque o `ocupado` já tinha voltado a `False`). Cancelar o organizar
  libera a trava; o `finally` libera mesmo se a confirmação estourar.

## Pegadinhas de domínio (Shopee) — validadas com loja real

- `get_shipping_parameter` e `get_tracking_number` são **GET** (POST → 404).
- `create_shipping_document` **exige `tracking_number`** (AWB) no corpo, buscado via
  `get_tracking_number`; sem ele → `logistics.tracking_number_invalid`.
- A etiqueta só existe **depois de "Organizar Envio"** (gera o AWB). O app organiza
  como **Postagem (drop-off)** via `ship_order` — sempre essa opção, nunca buyer-pickup.
  `info_needed.dropoff` lista os campos exigidos (geralmente vazio; às vezes
  `branch_id`/`sender_real_name`).
- **Já organizado ≠ sem drop-off:** um pedido já organizado (no painel, ou pelo
  lote) tem `info_needed={}` até o AWB sair. `organizar_envio` consulta
  `envio_ja_arranjado(param)` **antes** de recusar: se já arranjado, **pula o
  `ship_order` e só aguarda o AWB**; só levanta "não oferece Postagem (drop-off)"
  quando o envio **não** está arranjado E não oferece drop-off. Sem isso,
  `info_needed={}` disparava um falso erro mandando reorganizar o que já estava
  organizado (achado 5.3). `envio_ja_arranjado` = nenhum de
  pickup/dropoff/non_integrated em `info_needed`.
- **Organizar em lote:** `_organizar_varios` é em camadas — AWB existente
  (idempotência) → `batch_ship_order` (até 50 num request) → confirmação **pelo
  AWB** (não confiar no formato da resposta do batch) → fallback individual
  (`organizar_envio`) pra quem ficar sem AWB. Se o batch falhar por inteiro,
  não espera polling: vai direto ao individual.
- **Desempenho (medido, ver `docs/ARQUITETURA.md`):** organizar é **~14s fixos**
  (latência da Shopee emitir o AWB — piso intransponível, NÃO é o número de
  chamadas, então **batch não acelera**). O ganho está em **gerar os documentos
  em paralelo por pedido** (`_gerar_lote`; a Shopee processa requests
  concorrentes em paralelo) — mediu ~70% menos na fase de gerar. Cronometragem
  por fase em `shopee_tempos.log` (`_log_tempos`, gitignorado).
- A etiqueta térmica vem como **ZIP com ZPL (`~DGR/Z64`) dentro** — a Zebra imprime
  direto; não reembrulhar.
- **Erro da Shopee não pode vazar o token (HTTP E transporte):** a URL assinada
  leva `access_token`/`sign` na query. Erros HTTP com resposta passam por
  `_levantar_se_erro` (nunca `raise_for_status()`, cuja mensagem inclui a URL);
  falhas de **transporte** (queda de conexão/timeout — a exceção crua do requests
  carrega "Max retries exceeded with url: …") passam por **`_rede_limpa`**, que as
  converte em `SeparadorError` limpo com `from None` (corta o encadeamento — um
  `log.exception` não arrasta a URL no traceback). Defesa em profundidade nos
  limites: a GUI redige com `sem_segredos` o que mostra (`_erro`, avisos de falha
  parcial) e o bot redige o que manda pro chat. Mantenha as duas camadas.
  `sem_segredos` cobre a forma **query** (`chave=valor`) **e** a forma **JSON/repr
  de dict** (`"chave": "valor"`), e as chaves incluem `client_secret`/`partner_key`
  além de token/sign/code (5.11) — assim um corpo de request serializado por
  engano num texto de erro também é redigido.

## Antes de fechar uma mudança (mantenha o repertório em dia)

O repertório (docs + grafo) é o que um chat novo lê para entender o projeto — se
ele defasa, a próxima sessão parte de informação errada. Por isso, ao terminar
uma mudança, atualize **o que se aplicar** (faz parte do "pronto", não é opcional):

- **`docs/CHANGELOG.md`** — uma entrada em `[Não lançado]` para toda mudança que
  o dono perceberia (feature, correção, segurança, doc relevante).
- **`AGENTS.md` + espelho `CLAUDE.md`** — se criou/removeu convenção, módulo ou
  pegadinha de domínio, ou mexeu no **mapa do código**.
- **`docs/ARQUITETURA.md`** — se tocou numa invariante crítica, fluxo ou área de
  risco (confira o **contador de invariantes** no `AGENTS.md`).
- **`graphify-out/graph.json` + `GRAPH_REPORT.md`** — nós dos módulos/funções
  novos e os "porquês" como `rationale`/`concept` (ver "SEMPRE atualize o grafo"
  acima); valide **0 arestas órfãs**.
- **`docs/PRIORIDADES_TECNICAS.md`** — se concluiu um item ou registrou uma
  decisão de "não fazer agora".

Regra de ouro: **mudou algo neste guia, replique no espelho `CLAUDE.md`.** Cada
item é barato; a soma evita as brechas (ex.: o CHANGELOG ficar dezenas de commits
atrás do código).

## Fluxo de trabalho (git)

- Desenvolver na branch designada; **um PR por feature**. Não mergear PR sem o dono pedir.
- **Verifique o estado antes de empurrar follow-up:** `git fetch origin main` e
  cheque se a branch/PR já foi mergeada. **Não empilhe commits** numa branch que o
  dono pode mergear a qualquer momento — o commit extra vira **órfão** (o dono
  merge antes de o push chegar). Prefira **terminar a mudança e fazer um commit
  só** por PR, em vez de abrir o PR e ir acrescentando.
- **Depois que o dono mergear, confira o `main`** (`git merge-base --is-ancestor`)
  e, se algum commit ficou de fora, recupere-o numa **branch nova a partir do
  `main` atual** (cherry-pick) e abra outro PR — não reabra a branch já mergeada.
- Trailer de commit (já automático): `Co-Authored-By` + `Codex-Session`.
- O dono usa a pasta fora do OneDrive (`C:\contador`) com `git config gc.auto 0`
  (o OneDrive travava o `.git`).
