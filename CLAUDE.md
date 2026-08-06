# Guia do projeto (para o Claude Code)

> **Comece por aqui (chat novo):**
> 1. Leia este guia inteiro — convenções + pegadinhas de domínio.
> 2. Para **arquitetura/relações** ("quem chama X?", "o que quebra se eu mexer em
>    Y?"), **consulte o grafo `graphify-out/`** (skill graphify: `query`/`path`/
>    `explain`; sem o CLI, leia `graph.json`) e `docs/ARQUITETURA.md` — **antes**
>    de reler arquivos crus. Já para **comportamento/desempenho** ("por que está
>    lento", "o que este código faz de fato"), leia a **fonte**: o grafo orienta
>    (onde olhar e por quê), mas número e fluxo exato (workers, timeouts, laços,
>    semântica de cache) só o código tem — a **camada AST** do grafo é um snapshot
>    e pode defasar. Regra curta: grafo p/ orientar, código p/ decidir/mudar.
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
| `historico.py` | Registro de impressão por **dia de ação** (carimbo de tempo) + resumo diário (`resumo_do_dia`/`formatar_resumo`). Separado do estado. |
| `registro.py` | Log operacional (`separador.log`) + redação de segredos (`sem_segredos`). |
| `shopee_api.py` | Integração Shopee (API v2): listar, organizar envio, etiqueta, estado. |
| `provedores.py` | Abstração de marketplace (`ProvedorML`/`ProvedorShopee`) usada pela GUI. |
| `separador_gui.py` | Tela Tkinter (loja + conta + dia útil, busca, marcar todos, editor de Nomes). Usa `provedores`. |
| `bot_telegram.py` | Bot do Telegram: **consulta** (ML e Shopee) e **impressão só do ML** (com confirmação; marca direto — não vê a impressora). Também roda o **alerta pós-horário** (job a cada 5 min, todas as contas: avisa venda nova já `ready_to_print` com despacho hoje) e o aviso da manhã (`job_bom_dia`, 1x/dia). Tem ainda o **`/perguntas`**, que só dispara um fluxo do n8n (não responde nada — ver a convenção) e o **`/atualizar`** (`git pull` + reinício pelo celular). |
| `relatorio.py` | Formata textos para o bot. |
| `pegar_token.py` / `pegar_token_shopee.py` | OAuth inicial (gera credenciais). |
| `pegar_token_tiktok.py` | OAuth inicial do TikTok Shop. **Escrito, mas nunca rodou com sucesso** — a integração está ARQUIVADA (ver `docs/TIKTOK_SHOP_API.md`). |
| `tools/` | Ferramentas de dev: `gui_screenshot.py` (screenshot GUI headless), `graph_sync.py` (sincronizador seguro do grafo Graphify), `validar_obsidian.py` (validador do cofre `obsidian/`) e `diag_zpl.py` (estrutura do lote impresso — caça etiqueta em branco; ver a pegadinha abaixo). |
| `api-monitor/` | **DESATIVADO em 05/08/2026** (código preservado; os dois `.ps1` saem logo no começo). Era a rotina **semanal** que checava mudanças nas docs/políticas públicas das APIs. Nunca se conseguiu acesso confiável às fontes — ML Novidades exige login, a Shopee é SPA — então o relatório nascia "bloqueada" e ainda gastava uma chamada paga de IA por semana. Pesou mais o **risco**: rodava `claude -p` **sem restrição de ferramenta**, sem supervisão, com o `cwd` na pasta das credenciais, tendo **conteúdo da web como entrada**. Ao reativar (ver `api-monitor/README.md`), resolva as fontes primeiro e **não** volte com `bypassPermissions`. |
| `ads-monitor/` | Monitor **determinístico** (sem IA no núcleo) do Product Ads (Mercado Ads), 3 camadas: **coleta** (`coletar.py`, agendada diariamente — `registrar-tarefa.ps1`, mesmo padrão do `api-monitor/`) grava snapshot de campanha **e de ad_group/item dentro dela** (atribuição por SKU, best-effort) num SQLite local, incluindo o detalhe por campanha (`lost_impression_share_by_budget`/`_by_ad_rank`); **recomendação** (`recomendar.py`) gera ações a partir do histórico usando só os sinais que não dependem de margem (orçamento/ranking/ROAS vs. alvo). Falta a fonte de custo/margem por SKU para as recomendações condicionadas a ela (ver `ads-monitor/README.md`). **Camada 4 opcional (`narrar.py`)** narra em português, via `claude -p`, o que as camadas 1-3 já calcularam — aditiva, não muda o motor de regras. |

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
  `docs/ARQUITETURA.md` **antes** de reler os arquivos crus. Sem o CLI
  `graphify` no ambiente, leia o `graph.json` direto.
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
  **`docs/TIKTOK_SHOP_API.md`**: idem para o TikTok Shop — **ARQUIVADO em
  30/07/2026** (pausa, não desistência). O objetivo era **só aviso de venda no
  Telegram**, não imprimir. Travou antes do 1º byte de API: o **Service ID** não
  aparece no painel e o link de autorização responde "This service does not
  exist". O documento diz **onde parou** e **qual é o passo que destrava** —
  leia-o inteiro antes de mexer, inclusive a "Força da evidência" (a doc oficial
  é **inacessível** do ambiente de sessão) e a "armadilha dos portais parecidos".
  Já existem `pegar_token_tiktok.py` e a página de retorno: **não refaça**.
- **`obsidian/` é a base de contexto humano e operacional** (cofre versionado):
  decisões, conceitos, estado atual, incidentes, runbooks, funcionalidades e
  orientação para agentes. **Graphify continua sendo a base estrutural/semântica**;
  o Obsidian não a substitui. Ao **iniciar** uma tarefa, leia `obsidian/IA/Comece
  aqui.md`, `Fontes de verdade.md` e `Estado atual.md` (o cofre é público — **nunca**
  ponha segredos nele). Valide com `python tools/validar_obsidian.py` (roda no CI).
- **`AGENTS.md` é espelho deste arquivo** (adaptado para o Codex: título e
  trailer). Alterou uma convenção aqui? Replique lá.
- **NÃO rode `graphify hook install`**: o hook reconstrói o grafo só com código
  (AST) e apagaria a camada de docs/arquitetura — foi desinstalado de propósito.
- **Manutenção segura do grafo via `tools/graph_sync.py` (não edite centenas de
  nós à mão):** o `graph.json` tem 2 camadas — **AST** (código, regenerável) e
  **semântica** (`rationale`/`concept`, mantida à mão, espelhada em
  `graphify-out/semantic.json`). O sincronizador reconcilia por **IDs estáveis**:
  refaz a estrutura (`contains`/`method`/`imports`), **preserva** `calls` e toda a
  semântica, corrige números de linha, remove nó de símbolo morto e reconecta
  âncora manual quebrada (nunca deixa aresta órfã); grava atômico. Fluxo:
  `python tools/graph_sync.py --check` (detecta defasagem; roda no CI via
  `tests/test_graphify_sync.py`; enxerga **arquivo novo ainda não commitado** —
  antes usava só `git ls-files` e um arquivo novo ficava invisível até o `git
  add`, o que fazia o guardião passar local e **quebrar na CI**, de forma
  intermitente conforme a ordem de stage) → `--update` (aplica; re-emite `semantic.json` +
  `manifest.json`) → `--validate`. `built_at_commit` passa a ser o HEAD
  sincronizado. `graph.html` só o CLI regenera (fica defasado — pendência conhecida).
- **SEMPRE atualize o grafo com o que aprender:** ao terminar uma tarefa, rode
  `tools/graph_sync.py --update` (cobre módulos/funções/linhas/estrutura) **e**
  acrescente **à mão** os nós de `rationale`/`concept` com as **descobertas,
  barreiras e soluções** (ligue-as por `rationale_for`/`conceptually_related_to`);
  rode `--update` de novo para canonizar. Registre um resumo em "Atualizações
  manuais (pós-build)" no `GRAPH_REPORT.md`. Valide com `--validate` (0 arestas
  órfãs). Isso preserva a camada de docs até o próximo rebuild completo do CLI.

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
- **Histórico de impressão por dia de AÇÃO (`historico.py`):** o estado acima é por
  **dia de despacho** e **não guarda quando** a etiqueta saiu — então NÃO responde
  "o que imprimi hoje". Para isso há um **log separado** com carimbo de tempo
  (Brasília), gravado no momento da marcação confirmada. O hook é único: o callback
  **`registrar`** de `estado.marcar_impresso` recebe **só o delta** (ids realmente
  novos daquela marcação) — reimpressão/re-marcação do mesmo id **não** gera evento
  (nada de contagem dobrada). Os wrappers do núcleo (ML, com `conta_ativa()`) e do
  Shopee (loja única, `conta=""`) passam esse callback, então **GUI, bot e CLI**
  ficam cobertos de uma vez. A gravação é **best-effort** — roda **fora** da trava
  do estado (arquivo próprio, trava própria) e **nunca levanta** (uma falha aqui
  não pode derrubar uma marcação já gravada; filosofia do `_log_tempos`). Arquivo
  **único por máquina** (`historico_impressao.json`, ML de todas as contas +
  Shopee), gitignorado, podado por idade (`DIAS_HISTORICO=60`); **não** é trocado
  por `definir_conta` (o resumo agrega tudo). A GUI mostra `resumo_do_dia` +
  `formatar_resumo` no botão **📋 Resumo do dia** (`JanelaResumo`, só leitura —
  não toca estado/grupos, fica habilitado durante a operação). A **tela** é o
  detalhado por marketplace/conta; a **impressão** é um **PDF compacto com a soma
  por produto (SKU)** — `linhas_consolidado` + `gerar_pdf` (PDF em Python puro,
  Helvetica/WinAnsi, sem dependência externa) —, consolidando **todas as contas
  ML + Shopee** num só SKU (é a lista de produção/separação: `A01 - 2L 110 - 5`).
  Tela e PDF seguem a **ordem da aba Nomes** (`resumo_do_dia(ordem=...)`, a mesma
  ordem de separação; SKU fora dela vai ao fim em ordem natural). Ainda há um
  "Detalhado (.txt)" para arquivar. **Reimpressão não passa por `marcar_impresso`,
  então não entra no resumo** (decisão de v1).
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
  **No ML, as credenciais são AMARRADAS ao arquivo de origem** (auditoria de
  APIs 2026-07): `carregar_credenciais` grava o caminho no dict (chave volátil
  `_arquivo`, nunca persistida) e trava/releitura/refresh/salvamento usam a
  amarra (`_arquivo_das_credenciais`), não a global `ARQUIVO_CRED` — que
  `definir_conta` re-aponta a qualquer momento (o job do alerta do bot troca
  de conta em outra thread). Sem a amarra, um refresh em voo durante a troca
  podia gravar as credenciais de uma conta no arquivo da OUTRA (e o `.bak`
  junto): conta travada. Não "simplifique" voltando a usar a global.
- **Escrita de JSON é atômica e durável** (`.tmp` + `flush`/`fsync` → `replace`) e
  leitura tolerante. `gravar_json` abre com **`newline="\n"`** — grava **LF**
  mesmo no Windows; sem isso a GUI reescrevia os JSONs **versionados**
  (`nomes_sku.json`, `skus_por_anuncio.json`, que o repo mantém em LF via
  `.gitattributes eol=lf`) em CRLF e eles ficavam "modificados" para sempre,
  colidindo em todo `git pull` da máquina de operação. Credenciais têm espelho
  **`.bak`** com auto-recuperação (queda de energia não exige refazer o token);
  `.bak` é gitignorado. O `.bak` só vale **ao lado do principal** (a migração de
  conta o leva junto e remove órfãos da raiz) — um `.bak` desgarrado tem
  refresh_token já rotacionado (morto).
- **Falha de API é "NÃO SEI", nunca "não está pronto" (incidente 2026-07-31):**
  `buscar_envio` devolve **`None`** quando o ML recusa a consulta (depois das
  re-tentativas do `_com_retry`) — antes devolvia `{}`, e o `{}` percorria o
  fluxo **igual a um envio que não está pronto**: `_avaliar_pedido` descartava o
  pedido **em silêncio** e a tela mostrava o lote como completo. Num dia de API
  instável o operador despachou **5 de 7** vendas do mesmo SKU. Hoje
  `_avaliar_pedido` devolve `verificado=False`, `filtrar_para_imprimir` conta em
  `stats["nao_verificados"]`, `Coleta` e os provedores propagam (o modo **Ambas
  soma** as contas) e a **tela avisa antes de imprimir**. É a mesma regra do
  `_mtime_log_monitor` (`None` = não sei), aplicada ao contrário: lá o risco era
  avisar sem prova, aqui era **calar com prova na mão**. Ao adicionar consulta
  nova à API, **não devolva dicionário vazio em erro** — o vazio é
  indistinguível de uma resposta legítima e some dentro do fluxo.
  A varredura de 2026-08-03 achou o mesmo padrão em mais dois pontos, já
  corrigidos: **`_sla`** (falha → `expected_date=""` → a venda de hoje caía em
  "Outras datas"; hoje devolve `None`, o pedido **continua entrando** marcado com
  `data_incerta` e a tela avisa — excluí-lo seria pior que datá-lo errado) e
  **`_detalhe_item`** (ver abaixo).
- **Erro de CREDENCIAL (401/403) estoura; erro transitório vira "não sei":**
  as duas coisas pedem ações opostas, e tratar credencial recusada como "não
  sei" fazia a tela dar um conselho que **nunca** funcionaria — com o token
  revogado toda consulta falha, e o operador lia "a API não respondeu sobre 150
  envios, clique em Atualizar de novo" e clicaria para sempre, com a causa real
  escondida atrás do aviso. `_propagar_se_auth` re-levanta 401/403 como
  `SeparadorError` dizendo **o que fazer** (`pegar_token.py`); o resto continua
  virando `None`. É a mesma lógica do `_STATUS_RETRY`, que já não re-tenta
  401/403 porque re-tentar não ajuda. Aplicado em `buscar_envio`, `_sla` e
  `_detalhe_item`.
- **Lote de etiquetas é conferido pela QUANTIDADE, não só pelo HTTP 200
  (achado 2026-08-03):** `baixar_zpl` aceitava um 200 com **menos etiquetas do
  que envios pedidos** — o ZIP saía curto e `preparar_lotes` devolvia **todos**
  os envios como impressos. Etiqueta que não existe constando como impressa é
  exatamente o que a **invariante 1** proíbe, e no caminho do **bot/CLI** (que
  marcam sem confirmação humana) esta guarda é a única defesa. A comparação é
  `blocos ^XA >= nº de envios`, **não** igualdade: o ML manda 1 etiqueta + 1
  DANFE por venda, e amarrar no número exato tornaria o app refém de um formato
  que ele não controla — menos blocos que envios, porém, é erro em qualquer
  formato.
- **Falha de rede NUNCA pode ser gravada em cache (achado 2026-08-03):**
  `_detalhe_item` devolvia entrada vazia no erro e `buscar_detalhes` a gravava no
  `itens_cache.json`. Como o cache só busca o que **ainda não está nele**, uma
  falha **transitória virava permanente**: o item ficava sem GTIN — logo com a
  chave `{item_id}:{var}` em vez de `GTIN:…` — e sem `seller_sku`, o que
  **derruba a adoção** guardada em `skus_por_anuncio.json` (ela está sob a chave
  antiga) e faz o produto reaparecer como grupo separado sem SKU. Só limpando o
  cache na mão para consertar. Hoje `_detalhe_item` devolve `None` e
  `buscar_detalhes` **pula** — na próxima busca tenta de novo. Regra geral: cache
  guarda **resposta**, nunca **ausência de resposta**.
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
  `test_tmp_saida_nao_casa_o_que_o_monitor_vigia`. **O outro lado tem teste do
  mesmo contrato** desde 2026-07-29 (repo `impressora-zebra-usb`,
  `tests/test_contrato_com_o_contador.py`) — contrato documentado só de um lado
  é meio contrato.
- **Retorno do monitor (`aguardar_impressao`): 3 fontes, resposta antes de pista.**
  A entrega é por arquivo e não havia canal de volta — com o monitor fechado, os
  ZIPs se acumulavam e o dono só descobria pelo papel que não saía. Hoje o app da
  Zebra (**≥ v1.26.0**) publica uma **resposta**: um mural
  (`ARQUIVO_STATUS_MONITOR` = `~/zebra_usb_status.json`, gravado por
  `registrar_status_trabalho` no outro repo) com `{arquivo, quando, etiquetas,
  ok}` por arquivo processado. `_veredito_do_status` é consultado **primeiro** no
  laço, e só ele distingue **`falhou`** de "ainda não terminou" — um arquivo que
  falhou **não é apagado** pelo monitor, então sem o mural a falha ficava
  indistinguível de um lote demorado. Ele também é a única fonte que funciona com
  a opção **"Excluir após imprimir" DESLIGADA** (sem ela o arquivo nunca some).
  Sem o mural (**monitor antigo**), tudo degrada para as duas **pistas** de antes,
  que o monitor **já produzia**: o arquivo **sair da pasta** (o que ele imprime,
  ele tira dali) e o **log dele avançar** (`ARQUIVO_LOG_MONITOR`), que cobre o
  lote grande em que o ZIP só some na última etiqueta. **Sair da pasta ≠ ser
  apagado** (app Zebra **≥ v1.26.2**): o que imprimiu com sucesso é **movido**
  para `~/zebra_usb_concluidos/AAAA-MM-DD/` — retenção para reimprimir quando a
  impressora falha FISICAMENTE depois de o spooler aceitar. Para a pista dá no
  mesmo (saiu = impresso), mas ao investigar um lote perdido **o arquivo existe**:
  procure lá antes de concluir que sumiu. O que a pista exige é a **assimetria**,
  contratada dos dois lados: **sucesso sai da pasta, falha permanece nela** — se
  a falha também saísse, ela viraria "impresso" aqui. O corte por `desde` no mural não é opcional:
  ele guarda os últimos trabalhos, e um registro **anterior** de mesmo nome não
  pode responder pela impressão atual. Descobre quais arquivos são dela por **diferença de dois
  instantâneos** (`saidas_na_pasta` antes/depois de gerar) — `gerar_zip_lotes`
  devolve os pendentes, não o caminho, e propagá-lo mexeria em núcleo,
  provedores, bot e CLI de uma vez. **Na dúvida, calado:** se o monitor consumiu
  antes do 2º instantâneo (ele varre a cada 1s) o veredito é `imprimindo`,
  **nunca** `impresso`; e `OSError` no `exists()` responde "ainda está lá". O
  sinal **informa e nunca decide** — quem responde "saíram certo?" continua
  sendo o operador (invariante 1), porque o monitor confirma que MANDOU
  imprimir, não que a etiqueta saiu legível. Roda na thread de trabalho (nunca
  na do Tk) e é best-effort: falha vira aviso a menos, jamais impressão a menos.
  **O ⚠️ exige PROVA (incidente 2026-07-30):** `_mtime_log_monitor` devolve
  `None` para "não sei" (log ausente/ilegível) — distinto de "log parado". Um
  lote de 12 avisou "monitor NÃO deu sinal" imprimindo normal, porque em lote
  grande o arquivo não some dentro do teto (só é apagado na última etiqueta) e
  o log não pôde ser lido; a versão anterior colapsava os dois casos num
  booleano. `None` → `sem_saida` (silêncio); só log **encontrado e sem avanço**
  vira `sem_sinal`. **Falso alarme é pior que aviso nenhum:** ensina o operador
  a ignorar o ⚠️, e ele perde a utilidade no dia em que estiver certo. O mural
  respeita a mesma regra: status **ilegível/ausente/parcial** nunca vira veredito
  (`_status_do_monitor` devolve `{}` e o laço cai nas pistas), e o `try/except
  OSError` em volta do `ler_json` **não é redundante** — o `exists()` dele fica
  fora do próprio `try`, e um arquivo preso pelo OneDrive escaparia como exceção
  numa checagem que roda **depois** de a etiqueta já ter saído.
- **Os dois apps são separados de propósito — não junte (debate de 2026-07-30).**
  O app da Zebra não é back-end do contador: seus `PREFIXOS` incluem
  `etiqueta mercadoenvios`/`shipping-label`/`danfe-simplificado-`, os nomes que o
  **site do ML** dá ao baixar etiqueta na mão (funciona sem o contador existir), e
  ele tem funcionalidade própria (etiquetas separadoras, `gerar_zpl_separador`).
  Além disso ele roda **elevado** (UAC, para limpar a fila do spooler), é app de
  bandeja de **instância única** ligado o dia todo, e depende de
  `pywin32`/`pystray`/`pillow` (**só Windows**) — enquanto o núcleo daqui é
  portátil e o CI roda no Linux. A pasta Downloads é uma **fila com persistência
  de graça**: a tela pode cair no meio do lote que a impressão continua. O único
  ganho real da fusão era o canal de volta, e ele foi obtido **sem** fundir (mural
  de status, acima).
- **Etiqueta em branco no meio do lote: este app não sabe criar uma
  (06/08/2026).** Reclamação recorrente do dono ("às vezes pula uma etiqueta").
  Antes de investigar aqui, saiba o que já foi **descartado com leitura de
  código**: (1) o núcleo daqui **nunca cria página** — passa o ZPL do ML adiante e
  só insere um `^FO…^FS` dentro do bloco da DANFE (`carimbar_zpl`); não há um
  único `^LL`/`^PQ`/`^MN`/`^LH` no repositório; (2) mesmo que o ML mandasse um
  `^XA^XZ` vazio, o app da Zebra o **descarta** antes de imprimir
  (`_validar_e_extrair_blocos_zpl` loga "conteúdo vazio entre ^XA e ^XZ —
  ignorado"). Sobram três causas, e elas se separam **por evidência, não por
  palpite**: **(a)** o **auto-feed de início de sessão** do app da Zebra, que
  imprime um `^XA^XZ` de propósito para posicionar o sensor de gap — reaparece a
  **cada "Iniciar"** (o `MonitorEtiquetas` é recriado), e deixa a linha
  "Avançando etiqueta — posicionando sensor" no `~/zebra_usb_log.txt`; só cai
  **antes** do primeiro bloco, nunca no meio de uma venda; **(b)** `^MN`/`^LL`
  divergindo entre os blocos do ML — trocar de modo de mídia obriga a impressora a
  procurar o próximo gap, e esse avanço sai como etiqueta em branco (o app da
  Zebra já tem cicatriz vizinha disso: o comentário do `^MCN` que "retém o buffer
  e sobrepõe a DANFE na etiqueta seguinte"); **(c)** calibração da mídia
  (botão *Calibrar mídia* / `~JC` no app da Zebra). **`python tools/diag_zpl.py`
  decide entre (b) e o resto** lendo o lote já impresso, que o app da Zebra
  **retém** em `~/zebra_usb_concluidos/AAAA-MM-DD/` — a pasta de retenção
  contratada em 2026-08 existe justamente para investigar depois do fato. Ele
  reporta só **estrutura** (comando, contagem, tamanho): a etiqueta carrega nome,
  endereço e CEP do comprador, então **nunca** imprima conteúdo de `^FD`.
  **Ele também confere o emparelhamento ENVIO→DANFE — e isso não estava na v1
  (06/08/2026).** O primeiro lote real analisado tinha **19 etiquetas e 18
  notas** (blocos `#31` e `#32` ambos de envio; o perfil de tamanho confirma —
  envio ~2600 B/33 campos, nota ~1600 B/37) e a ferramenta imprimiu **"OK"**:
  ela só procurava página em branco, então calou diante de uma anomalia **maior**
  no mesmo arquivo. É a família "falha que reporta sucesso" aplicada a um
  **diagnóstico**, onde o dano é próprio: o OK não é neutro, ele **manda procurar
  no lugar errado** — teria feito calibrar a impressora enquanto o arquivo tinha
  outra coisa a dizer. Regra: **ferramenta de diagnóstico responde sobre o arquivo
  inteiro, não só sobre a pergunta que a motivou.**
  **Mas o aviso NÃO crava a causa:** a estrutura não distingue "o ML não mandou a
  nota" de "venda de **vários volumes**" (que legitimamente tem 2 etiquetas para 1
  nota). Ele entrega o fato e manda conferir no painel — mesma disciplina do aviso
  de NF-e da Shopee, que diz o efeito e não afirma o porquê.
  A checagem é a mesma do `_verificar_sequencia_ml` do outro repo, feita aqui
  também porque este lado vê o arquivo **antes** de imprimir. Não vale para a
  Shopee (1 etiqueta por venda, sem nota junto) — exigir par ali seria alarme
  falso. E o `baixar_zpl` **continua com `>=`**: a guarda dele é contra lote
  **curto**, e amarrar no número exato tornaria o app refém de um formato que ele
  não controla.
  **Ordem dos blocos do ML: ENVIO → DANFE** (é o que `_verificar_sequencia_ml`
  do outro repo cobra) — some isso ao fato de a impressora empurrar o papel para
  fora e a ordem física fica **invertida** em relação à foto: o que está mais
  perto da impressora foi impresso por ÚLTIMO. Ler a foto na ordem errada
  troca "veio antes de tudo" (auto-feed) por "veio no meio da venda" (mídia),
  que são causas diferentes.
- **Segredos nunca versionados** (ver `.gitignore`): credenciais, estado, caches,
  `historico_impressao.json`, `config.json`, `bot_config.json`, logs (`bot.log`,
  `shopee_tempos.log`, `ml_tempos.log`, `separador.log`).
- **Onde os arquivos ficam: `dados/` e `logs/`, nunca soltos na raiz.** Tudo que
  o app lê/escreve fica em **`dados/`** (`PASTA_DADOS`: credenciais, estado,
  caches, de-paras, `contas/{nome}/`) e todo registro em **`logs/`**
  (`PASTA_LOGS`). Arquivo novo entra numa dessas — **não** na raiz, que é só
  para o que se abre (`separador_gui.py`), os módulos `.py` e o que as
  ferramentas exigem lá (`README`/`CLAUDE`/`AGENTS.md`, `.gitignore`,
  `pyproject.toml`, `ruff.toml`). Quem vinha da versão antiga não move nada:
  **`migrar_para_pastas()`** roda no **import** do núcleo (antes de qualquer
  leitura) e migra o que estava solto — leva `.bak`/`.corrupto` **junto** (um
  `.bak` desgarrado guarda refresh já rotacionado, morto), move `contas/`
  inteira, **nunca sobrescreve** destino existente (o dado em uso vence) e
  **nunca levanta** (best-effort: falha de IO não pode impedir o app de abrir).
  **Cada movimentação é ISOLADA e `contas/` vai PRIMEIRO** (incidente
  2026-07-29): o `try/except` mora dentro de `_mover_se_preciso`, não em volta
  do laço — no Windows o bot sobe no logon pelo Agendador e mantém o `bot.log`
  **aberto**, e renomear arquivo aberto levanta `WinError 32`; com um
  `try/except` só, essa falha abortava em silêncio tudo o que vinha depois e a
  pasta `contas/` (que vinha após os logs) ficava na raiz — a tela abria **sem
  nenhuma conta ML**, seletor e modo 🌐 Ambas sumidos. Lição geral: em rotina
  best-effort que percorre uma **fila**, o `try/except` pertence a cada item.
  `migrar_conta_legado` lê de `PASTA_DADOS` (o "solto" de hoje é `dados/`). No
  `.gitignore` a regra é **invertida**: ignora `dados/*` e `logs/` inteiros e
  libera explicitamente só os 2 versionados (`nomes_sku.json`,
  `skus_por_anuncio.json`) — assim um arquivo local novo nunca escapa por
  esquecimento. **Não mova os módulos `.py` para uma subpasta**: exigiria tocar
  os 26 arquivos que os importam, 8 `.bat`, o CI e re-ancorar `PASTA_SCRIPT`
  (de onde sai todo caminho de token/estado), e a raiz continuaria com os
  arquivos de ferramenta de qualquer jeito — ganho parcial, risco alto.
- **Segredo NUNCA vai para o log — nem por dentro de biblioteca:** o
  `sem_segredos` do `registro.py` só cobre o texto que o PROJETO escreve. O
  token do bot vazava por fora dele: a URL da API do Telegram carrega o token no
  próprio caminho (`.../bot<TOKEN>/getUpdates`) e o `httpx` registra cada
  requisição em **INFO** — com o `basicConfig` do bot em INFO, o token ia
  inteiro para o `bot.log` e para o console, a cada chamada. Por isso
  `bot_telegram.py` sobe `httpx` e `httpcore` para **WARNING** logo após o
  `basicConfig` (erro de rede continua visível; só o INFO de requisição sai).
  Regra geral: ao adicionar uma biblioteca que fale HTTP com credencial na URL,
  **suba o logger dela** — redigir na saída não alcança o que ela escreve
  sozinha. Guardas em `tests/test_bot_segredo_no_log.py`.
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
- **A marca de "1º ciclo já rodou" é POR FONTE, não uma só (06/08/2026).**
  Ela era um booleano ligado **no fim** do ciclo — inclusive quando a checagem
  de uma fonte tinha **falhado**. A fonte que falhou não registrou nada, então
  no ciclo seguinte todas as vendas dela apareciam como "novas" e saíam **de
  uma vez**: uma falha de rede transformava a garantia de "nada de despejo"
  exatamente no despejo que ela existe para evitar. Hoje `iniciado` é a
  **lista** de fontes que completaram a rodada (`_fonte_iniciada` /
  `_marcar_fonte_iniciada`), marcada só **depois** do sucesso — quem falhou
  repete o ciclo **calado** na próxima rodada. Por fonte, e não global, porque
  o global trocaria o despejo por **silêncio geral**: a Shopee fora do ar
  calaria os alertas do ML o dia inteiro (mesma filosofia do isolamento de
  falha por conta, que já existia logo acima no laço). O **formato antigo
  (booleano `True`) continua valendo** para o dia já gravado: o bot pode ser
  atualizado no meio do dia, e rebaixar `True` para lista vazia produziria o
  despejo de novo.
  **ATENÇÃO — o caso de campo que levou até aqui NÃO está explicado.** O que
  motivou a investigação foi um aviso de venda Shopee às **09:42** de 06/08 que,
  pelo desenho, o primeiro ciclo das 08:32 deveria ter calado. O `bot.log`
  **descarta** esta correção como causa: registrou o primeiro ciclo às 08:32:41 e
  **nenhuma** linha de "Falha ao checar alerta pos-horario". Ou seja, o furo
  acima é real e foi corrigido por mérito próprio, mas **não é** o que aconteceu
  naquele dia — falta explicar por que o pedido `260805JCWTKH9K` (pago 05/08
  09:40, `ship_by_date` 06/08, `invoice_data.status=pending`, `update_time`
  igual ao `pay_time`, ou seja **sem mudança de estado** desde a véspera) não foi
  registrado no balde `Shopee`+`SUFIXO_ALERTA_NF` no ciclo das 08:32. O estado
  (`dados/alertas_pos_horario.json`) confirma a dedução: o pedido **está** no
  balde, mas foi acrescentado **por último** — ou seja, entrou às 09:42 e não às
  08:32, senão o dedup teria calado a mensagem. **Não trate como encerrado.**
- **O fallback de `dia_previsto` erra por UM DIA (medido, 06/08/2026).** A
  docstring diz que `ship_by_date` = fim do dia de `pay_time + days_to_ship`, e
  diz ter sido "conferida contra um pedido real". O pedido `260805JCWTKH9K`
  **contradiz**: `pay_time` 05/08 09:40, `days_to_ship` **2**, e `ship_by_date`
  real **06/08** 23:59:59 — a fórmula daria **07/08**. Dois pedidos reais
  discordam, então **não existe fórmula confirmada**: não "conserte" trocando por
  `days_to_ship - 1` com base numa amostra. O que importa é a **forma do erro**:
  o fallback existe para que uma venda sem prazo não fique fora do filtro por dia
  ("o aviso nasceria mudo") e, errando para a frente, ele produz **exatamente o
  silêncio que deveria evitar** — mesma família do `OK` que cala. A saída correta
  não é adivinhar a data e sim tratar **ausência de `ship_by_date` como data
  incerta**, que nunca pode EXCLUIR em silêncio (a regra do `_sla` no ML:
  "excluí-lo seria pior que datá-lo errado"). **Foi o que se fez:** o fallback
  saiu, `dia_previsto` devolve `""` para "não sei" e `pedidos_prontos_novos`
  **inclui** o incerto no lote de hoje — nos **dois** avisos (pronta e
  falta-NF-e), por decisão do dono. Prazo **conhecido** e diferente de hoje
  continua de fora, senão o alerta viraria "todas as vendas abertas". O ruído
  extra é baixo porque a **carência de 30 min** já segura a venda recém-criada,
  que é justamente a que costuma vir sem prazo; e o lote leva
  `relatorio.AVISO_SEM_PRAZO`, que diz **por que** aquela venda entrou sem
  afirmar o dia (mesma disciplina do aviso de NF-e).
- **Alerta pós-horário: UMA mensagem por ciclo, e o 1º ciclo do dia é calado
  (05/08/2026).** O envio era **por origem e por tipo** — com 2 contas ML +
  Shopee, cada uma podendo ter "pronta" e "falta NF-e", o pior caso eram **6
  mensagens a cada 5 min**, e o chat virava parede (reclamação do dono, com
  print). Hoje as origens viram **seções** de um texto só
  (`relatorio.BlocoAlerta` + `texto_alerta_pos_horario`), com a seção de NF-e no
  fim e a explicação **uma vez** (antes repetia inteira em cada mensagem).
  **O dedup e a persistência continuam POR ORIGEM** (`_registrar_alerta`); só o
  envio (`_enviar_alerta`) passou a ser um — misturar os baldes faria o
  `shipment_id` já avisado calar o "está pronta" de depois. A janela começa às
  **8:30** (`ALERTA_INICIO`, antes 7h): é a hora em que o dono para de olhar a
  tela — antes disso ele está no Atualizar e já leu o aviso das 08:00, então o
  alerta repetia o que ele acabara de ver. E o **primeiro ciclo do dia não
  envia**: só registra o que já existe (`iniciado` no estado). Sem isso, subir a
  janela trocaria a parede de mensagens por um despejo único com o dia inteiro —
  o oposto de "apareceu agora"; essas vendas estão no aviso da manhã e na tela.
  Venda antes travada por NF-e que ficou pronta vem marcada com **✅** (`liberadas`):
  sem isso o mesmo SKU reaparecendo minutos depois parece duplicata.
- **Alerta pós-horário do bot (venda nova pronta pra hoje, ML + Shopee):**
  motivado por um problema real do dono — venda que cai depois das 8:30
  (quando ele já parou de checar a tela) só é vista tarde demais, e o
  fornecedor já não tem mais o produto pra repor no mesmo dia.
  `job_alerta_pos_horario` (`bot_telegram.py`, `JobQueue.run_repeating` a
  cada 5 min) percorre **todas** as contas ML (`core.listar_contas()`) MAIS
  a **Shopee** (loja única) e avisa — uma vez por envio/pedido — quando surge
  algo novo já pronto pra despachar hoje (`ready_to_print`+`expected_date`
  no ML, `READY_TO_SHIP`+`ship_by_date` na Shopee — sinais equivalentes;
  `shopee_api.pedidos_prontos_novos` é o par Shopee de
  `filtrar_para_imprimir`+`extrair_itens`, reusando `_itens_de_detalhes`
  extraído de dentro de `grupos_de_detalhes` pra não duplicar a extração de
  SKU/quantidade). Roda sozinho, **independente** do botão Atualizar da tela
  e de qualquer comando manual. Dedup num estado próprio
  (`alertas_pos_horario.json`, gitignorado) que reseta sozinho na virada do
  dia — por `shipment_id` (numérico) no ML, por `order_sn` (string) na
  Shopee, tratada como mais uma chave (`"Shopee"`) nesse mesmo estado.
  A checagem da Shopee **pula em silêncio** se não houver
  `credenciais_shopee.json` (setup só-ML é válido; sem isso, logaria erro a
  cada 5 min pra sempre). Isola falha por conta/loja (mesmo espírito do
  `ads-monitor/coletar.py`) — `_disparar_alerta` (envio + persistência) é
  **compartilhada** entre ML e Shopee, pra não duplicar essa lógica em dois
  lugares. **`_dados_alerta_da_conta` faz a checagem + o detalhe dos itens
  NUM SÓ bloco de troca de conta** — separar em duas chamadas arriscaria a
  2ª rodar já com a conta ORIGINAL restaurada pela 1ª (bug sutil de conta
  errada: `definir_conta` troca globais do núcleo compartilhadas com o
  resto do bot; ver "Áreas de risco" em `docs/ARQUITETURA.md`) — a Shopee
  não tem esse risco (loja única, sem troca de conta). Cada alerta mostra
  SKU + quantidade **somada por SKU** (`relatorio.texto_alerta_pos_horario`,
  ex.: `A01 - 2L 110 - 1`), sem número de envio/pedido — pedido explícito
  do dono, que só precisa saber O QUE repor. Cada disparo também persiste
  os itens em `alertas_pos_horario.json` (junto do dedup); **`/vendasapos`**
  (comando e botão "🔔 Vendas após" no `/menu`) junta **tudo que já foi
  avisado hoje**, por conta/loja + um TOTAL por SKU no final
  (`relatorio.texto_resumo_vendas_apos`) — sem isso, várias vendas caindo em
  sequência depois das 8:30 poluiriam o chat com um alerta cada. Só relê o
  estado já persistido, não refaz chamada de API nenhuma.
- **Shopee: "Enviar NF-e" é o espelho INVERTIDO do ML.** Lá a venda travada
  **some** do app; aqui ela continua em `READY_TO_SHIP`, aparece na tela e o
  alerta **já a chamava de "pronta"** — sendo que a Shopee **recusa o
  `ship_order`** com a nota pendente (`error_pending_invoice`, confirmado com o
  suporte deles em 2026-08-04). Era dizer que está pronto o que a própria Shopee
  nega. Sinal: `invoice_data.status != "valid"` (campo **opcional** — só vem se
  pedido pelo nome; entrou no `CAMPOS_DETALHE` junto com `pay_time`, na chamada
  de detalhe que já era feita, **custo zero**). **`pending` sozinho NÃO serve de
  alerta**: é o estado inicial de toda venda paga até o faturador subir o XML
  (confirmado e observado — um pedido virou `valid` sozinho em minutos). Quem
  separa a travada da recém-criada é o **dia**. **O suporte errou sobre a causa,
  e o painel desmentiu:** as 20 `pending` da loja apareciam como **"Em
  processamento"** (a Shopee ainda processando; a etiqueta libera num horário que
  ela anuncia) e as 3 `valid` como "Em aberto" — casamento exato, 20/20 e 3/3.
  Então `pending` cobre **pelo menos dois casos** (processando × nota faltando), e
  por isso a função chama-se `nota_nao_validada`, testa `!= "valid"` (a lista de
  valores não é exaustiva; errar para o lado de não imprimir) e **o aviso não
  afirma a causa** — diz o efeito e manda conferir no painel. **Armadilha da
  data:** a Shopee
  demora a atribuir `ship_by_date`, então venda recém-paga vem **sem prazo** e
  ficaria fora de qualquer filtro por dia — o aviso nasceria mudo. Daí
  `dia_previsto`: usa o `ship_by_date` quando existe, senão deriva de
  `pay_time + days_to_ship` (fórmula **conferida** contra pedido real —
  `ship_by_date` é o fim do dia, 23:59:59 de Brasília). **Duas respostas do
  suporte NÃO valem:** a de que `ship_by_date` só é atribuído após a nota virar
  válida **contradiz o dado real**, e o push `fbs_br_invoice_issued_push` (código
  31) é de **FBS**, enquanto os pedidos do dono são `fulfilled_by_local_seller`.
- **Carência do aviso "sem NF-e" (05/08/2026): o sinal é o TEMPO, não o
  estado.** O faturador do dono (ERP UpSeller) consulta as APIs do ML/Shopee,
  puxa a venda, confere o **estoque interno** e só então sobe o XML. Toda venda
  nova passa alguns minutos sem NF-e — então avisar sobre o estado disparava
  dentro da janela normal do ERP e se desmentia minutos depois com o ✅ (relato
  do dono, com print). O aviso não existe para dizer "está sem NF-e"; existe
  para dizer **"está sem NF-e há tempo demais para ser processamento normal"**,
  que no fluxo dele significa uma coisa só: o ERP olhou, **não achou estoque** e
  por isso não faturou. `_fora_da_carencia` corta por `CARENCIA_NF_MIN` (30 min,
  ajustável em `carencia_nf_min` no `bot_config.json` — o número certo depende
  do ERP, não do app). Três decisões que não são detalhe: **(1)** o relógio conta
  do carimbo da VENDA (`pay_time` na Shopee, `date_closed`/`date_created` no ML),
  não de quando o bot olhou — bot fora do ar a noite toda, venda travada desde as
  23h já nasce com 9h de idade e é avisada na hora; **(2)** quem está **na
  carência NÃO é registrado** no dedup, senão ficaria calado para sempre; **(3)**
  sem carimbo de tempo, **avisa** — calar por falta de informação esconderia
  justamente a venda sem estoque (regra de 2026-07-31: nunca calar com prova na
  mão). O corte é no **bot**, não no núcleo: `filtrar_para_imprimir` continua
  respondendo "quem está em `invoice_pending`"; quem decide "sobre quem vale
  avisar" é o alerta. **Efeito colateral bom:** mata também o falso positivo do
  "Em processamento" da Shopee, que `invoice_data.status=pending` não distingue
  de nota faltando — um mecanismo, dois ruídos. A mensagem leva **há quanto
  tempo** (`espera_min`): uma venda parada há 40 min é falta de estoque, várias
  de uma vez é o faturador fora do ar — o texto entrega o dado e não conclui.
- **Alerta de venda parada em "Informe a NF-e" (`invoice_pending`):** o dono
  controla estoque; quando vende um item que não tem, o faturador **não sobe o
  XML** e o envio nunca chega a `ready_to_print` — a venda que mais precisa de
  aviso era a única invisível para um app que só olha esse substatus.
  `filtrar_para_imprimir` ganhou `pendentes_nf` (lista opcional) e
  `_avaliar_pedido` um `substatus_extra`; os dois grupos saem da **mesma
  passada** (o detalhe do envio já foi buscado — zero chamada a mais, e a
  economia do alerta custou uma auditoria inteira). **O retorno continua sendo só
  `ready_to_print`** — a separação lá dentro é por SUBSTATUS, não por "veio
  preenchido": o ML não libera a etiqueta desse envio, e contá-lo como pronto
  poria no lote uma etiqueta que não existe (família da invariante 1). Sem o
  parâmetro, o caminho da impressão é idêntico ao de sempre. O aviso vai
  **separado**, em balde de dedup próprio (`conta + SUFIXO_ALERTA_NF`): dividir o
  balde faria o `shipment_id` já avisado **calar** o "está pronta" de quando o XML
  subisse — são dois recados com ações diferentes (repor × imprimir). O texto leva
  uma linha dizendo que a etiqueta só libera depois do XML; sem ela seria
  indistinguível de uma venda pronta. **O nome do substatus é contrato do ML**:
  `python separador_etiquetas_ml.py substatus` lista os que existem na conta, com
  contagem — rode isso **antes** de mexer no código se o alerta parar de avisar.
- **`/perguntas`: dois sistemas, um bot só (o bot dispara, o n8n responde).** O
  dono tem um fluxo no **n8n** que lista perguntas/mensagens sem resposta de outra
  conta e quer acioná-lo pelo mesmo bot. A restrição que desenha tudo: o Telegram
  entrega os updates de um bot a **um consumidor só** — quem **lê** os comandos é
  este projeto (polling, em `main`), e o n8n entra apenas como **remetente**
  (`sendMessage`). Por isso o `/perguntas` **não responde com dado nenhum**: faz um
  POST no webhook (`_disparar_perguntas`, `{"origem","comando","chat_id"}`), manda um "🔎
  Consultando..." imediato (o fluxo leva ~4s) e sai de cena; a resposta chega
  depois, escrita pelo n8n no mesmo chat. **Não mexa na forma de RECEBER updates**
  (trocar polling por webhook aqui derruba um dos dois lados). Restrito a **um**
  chat (`chat_perguntas`), não à whitelist inteira — o comando fala de uma conta
  específica do dono; chat não autorizado é ignorado **em silêncio** (responder
  "não autorizado" já confirmaria que o comando existe). Falha de rede vira aviso
  no chat, nunca exceção subindo pelo handler.
- **Contrato com o n8n (fechado com o outro lado em 2026-08-04).** O que ficou
  acordado, para não se re-decidir daqui a um mês:
  - **`chat_id` é uma CAPACIDADE, não um dado.** O n8n manda a resposta para o
    chat que vier no corpo — e cai no chat do dono quando o campo falta. Logo
    **a autorização é responsabilidade deste lado**: só pode ir para o POST um
    `chat_id` que já passou por `_autorizado` (e pela restrição do comando).
    Mandar um id não validado faria o n8n entregar dado da conta a um terceiro.
    Guardião: `test_chat_id_enviado_e_o_de_quem_disparou`.
  - **Um webhook POR FLUXO**, não um roteador — no n8n o webhook pertence ao
    workflow, e rotear exigiria um monolito (uma função quebrada derrubaria as
    outras). O campo `comando` continua indo no corpo, para log/conferência do
    lado deles. Consequência aqui: **uma chave de config por comando**; passando
    de ~3, trocar `webhook_perguntas` por um bloco `webhooks: {nome: url}`.
  - **Nada de botão vindo do n8n.** Eles não mandam `InlineKeyboardMarkup` nem
    `ReplyKeyboardMarkup`, porque o toque vira `callback_query` — que é update e
    vai para o consumidor do polling (este projeto), que não conhece aquele
    `callback_data` e não faz nada. Botão numa resposta do n8n exige handler
    **deste lado**.
  - **Parâmetro vai em `args`**: string crua com o que veio depois do comando,
    já com `trim`, `""` quando não houver. Crua e não lista de propósito — a
    sintaxe de um comando pode evoluir sem pedir mudança nos dois lados.
  - **Um comando por função enquanto forem ≲5.** Submenu só compensa depois
    disso (e aí exige tratar `callback_query` aqui — mais acoplamento).
  - **Fluxo caro precisa de freio.** Os relatórios de Ads levam ~5 min e gastam
    dinheiro (~US$ 0,04/conta, chamadas pagas de IA): o aviso imediato tem de
    dizer que demora, o comando fica restrito ao chat do dono e o limite de
    frequência é responsabilidade deste lado. **Esse limite tem de ser
    PERSISTIDO** (arquivo, como o dedup do alerta) — em memória ele zera a cada
    reinício, e o bot reinicia a cada `/atualizar`.
- **Integração nova do n8n é UMA LINHA (`INTEGRACOES`).** A tabela
  `IntegracaoN8N` descreve cada fluxo (comando, descrição do menu, rótulo do
  botão) e dela saem a chave de config (`webhook_<comando>`), a variável de
  ambiente (`N8N_WEBHOOK_<COMANDO>`), a linha do `/menu` e o botão inline;
  `_acionar_n8n` é o corpo único (autorização, "Consultando…", disparo em
  thread, erro contido). **Mas cada comando tem um handler NOMEADO** que só
  delega (`cmd_perguntas`, `cmd_anuncios`) — um handler genérico registrado em
  laço passaria batido pelo guardião `test_todo_handler_registrado_checa_autorizacao`,
  que varre o `main` por AST: a generalização teria furado a rede de segurança da
  autorização. A chave de chat continua `chat_perguntas` mesmo valendo para todas
  as integrações — renomear obrigaria a reeditar o config da máquina de produção,
  por ganho cosmético.
- **Webhook do n8n autenticado por `Authorization: Bearer` (05/08/2026).** A URL
  sozinha não bastava: quem a obtivesse disparava os fluxos à vontade, e o abuso
  por **repetição** custa cota da API do ML e enche o chat do dono. O lado n8n
  liga `authentication: headerAuth` nos dois nós; este lado manda o cabeçalho
  (`n8n_segredo` no `bot_config.json`, ou `N8N_SEGREDO`). **Um segredo só para
  os dois fluxos:** se o config vazar, as duas URLs vazam juntas — dois segredos
  não comprariam nada e dobrariam a chance de errar ao colar. **`Authorization`
  e não um cabeçalho próprio** porque o `sem_segredos` **já** redige a forma
  `Bearer <token>` (uma das seis que ele conhece, criada para o ML): o segredo
  nasce protegido em log e erro, sem regra nova — verificado contra segredos
  reais de `secrets.token_urlsafe(32)`, cujos 43 caracteres caem inteiros na
  regex. **Segredo ausente = não manda cabeçalho**, de propósito: é o que
  permite subir este código **antes** de o n8n exigir (cabeçalho extra é
  ignorado por quem não o exige), fechando a janela em que um lado exigiria e o
  outro ainda não mandaria. E **401/403 tem mensagem própria** — apontar o
  workflow diante de um segredo errado faria o dono ligar e desligar fluxo sem
  chegar a lugar nenhum (mesmo conselho inútil que o `_propagar_se_auth`
  corrigiu no coletor do Ads). **Descartadas:** allowlist de IP (o IP é dinâmico
  e a falha chega de madrugada disfarçada de "o n8n caiu"; e autentica a rede,
  não o chamador) e segredo no corpo via `onlyRunIf` — este último **não** por
  consumir execução (não consome; eu estava errado e o lado n8n corrigiu), mas
  porque **falha aberto**: erro na avaliação da expressão libera a requisição.
  Controle de acesso que autoriza quando quebra não é controle de acesso.
- **URL de webhook é CREDENCIAL — e este repositório é público.** O webhook do
  n8n não pede token nem cabeçalho: quem tem o link dispara o fluxo (por isso o
  caminho leva um sufixo aleatório). Então a URL segue a regra dos segredos: mora
  no `bot_config.json` (`webhook_<comando>`) ou na variável
  `N8N_WEBHOOK_<COMANDO>`, **nunca no código**, e não pode entrar em texto de
  erro nenhum — nada de `raise_for_status()` (a mensagem dele inclui a URL) nem
  de propagar a exceção crua do `requests` ("Max retries exceeded with url: …");
  é o mesmo `_rede_limpa` da Shopee, com `from None`. Terceira camada:
  `sem_segredos` redige o caminho depois de `/webhook/`. Vale para **qualquer**
  integração futura por URL-segredo (Zapier, Make, n8n).
- **Menu de comandos (`setMyCommands`) é POR CHAT, nunca global.** O menu "/" do
  app é publicado no `post_init` com `BotCommandScopeChat`, um por chat
  autorizado. No escopo **global** a lista apareceria para qualquer pessoa que
  abrisse o bot — desfazendo, por uma porta lateral, a correção de 2026-08-03 (o
  `/menu` revelava comandos e loja ativa a estranhos). Duas armadilhas: o
  `setMyCommands` **substitui a lista inteira**, então comando novo tem de entrar
  em `COMANDOS_MENU` (guardião em `tests/test_bot_perguntas.py`), e a publicação é
  **best-effort** (roda antes do polling — falhar ali não pode impedir o bot de
  subir por um detalhe cosmético).
- **Todo handler do Telegram checa `_autorizado` (varredura de segurança
  2026-08-03):** o bot é a **única superfície do projeto que qualquer pessoa na
  internet alcança** — basta descobrir o @usuário. A checagem vive em dois pontos
  de estrangulamento (`_responder` e `_listar_grupos`) e a maioria dos comandos
  delega para eles; `cmd_start` (`/start`, `/menu`, `/ajuda`) **não checava** e
  respondia a estranhos com a lista de comandos e a **loja ativa** — não dava
  acesso a dado nem a ação (todo botão passa por `cb_botao`, que checa), mas era
  reconhecimento de graça. O risco real não é o código de hoje e sim **o handler
  de amanhã**: um comando novo que não delegue nasce **aberto** e nada acusaria.
  Por isso o teste `test_todo_handler_registrado_checa_autorizacao` varre os
  handlers do `main` por AST e falha em qualquer um desprotegido. Ficam abertos
  de propósito, com o motivo escrito no `ABERTOS`: **`/id`** (porta de entrada —
  devolve só o chat id de quem perguntou) e o catch-all de texto solto. Mexer
  nessa lista é decisão de segurança, não atalho para teste vermelho.
- **No BOT, tudo que depende da conta ativa roda sob `TRAVA_CONTA`
  (achado 2026-08-03):** `core.definir_conta()` troca **globais** do núcleo, e o
  bot roda várias coisas em paralelo via `asyncio.to_thread` — o job do alerta
  percorre **todas** as contas (trocando os globais a cada uma) enquanto o dono
  pode mandar `/imprimir` de outra. Sem trava, o comando lia a credencial e o
  estado da conta que o **job** apontou naquele instante: imprimia com o token
  errado e gravava no `estado_grupos.json` da **outra conta**. Reproduzido: **39
  de 40** leituras pegaram a conta errada. `TRAVA_CONTA` é um **RLock** (não
  `Lock`): `_dados_alerta_da_conta` roda dentro dela e chama funções que também a
  pegam. Estão sob ela: `_coletar`, `_imprimir_grupo`, `_prontos`,
  `_trocar_conta` e o bloco de troca do alerta. **Caminho novo que leia ou grave
  por conta entra na trava** — o teste `test_caminhos_que_dependem_da_conta_estao_travados`
  falha se esquecerem. A GUI não precisa: ela roda uma operação por vez
  (`ocupado`), e entre PROCESSOS quem protege são as travas de arquivo.
- **Config do bot inválida tem de DIZER isso (incidente 2026-08-04, 2ª vez).**
  `bot_telegram._ler_bot_config` distingue **inválido** de **ausente** e informa
  linha/coluna — o `_ler_json` do núcleo devolve `{}` para qualquer falha (certo
  para cache e para o config da tela, errado aqui): um JSON malformado fazia o
  token "sumir" e a mensagem virava "Token ausente", mandando procurar o token e
  não a vírgula. **E toda falha de inicialização vai para o `bot.log`**
  (`log.error`/`log.exception`), não só para o `print`: sob o lançador o bot roda
  em **janela oculta**, então o print não é visto por ninguém e o log só mostrava
  a linha *anterior* ao crash — o único sintoma visível era "reinicia a cada 15s"
  (o laço do `.bat`), e a suspeita caiu no script de reinício, que era inocente.
  **Uma falha que só aparece onde ninguém olha é uma falha silenciosa**; sob
  janela oculta, "imprimir o erro" não conta como reportar.
- **Reiniciar o bot: NUNCA `schtasks /end` + `/run` (incidente 2026-08-04).**
  Aquele par **não reiniciava nada**: o `rodar-bot-oculto.ps1` subia o `.bat` com
  `Start-Process` **sem `-Wait`**, o Agendador dava a tarefa por terminada no 1º
  segundo e o bot ficava **órfão** da árvore da tarefa — o `/end` não tinha o que
  matar e o `/run` subia um **segundo** bot por cima do primeiro (409 do Telegram
  não derruba nenhum dos dois, e o **antigo** seguia respondendo: "reiniciei e a
  versão não mudou"). Hoje: `-Wait` no lançador **e** `atalhos/reiniciar-bot.ps1`
  (+ `Reiniciar Bot.bat`), que não depende disso — identifica os processos pelo
  **nome** (`python`/`pythonw` com `bot_telegram` na linha de comando; filtrar só
  pela linha de comando faria o próprio PowerShell do script se matar), derruba
  **o lançador primeiro** (senão o laço ressuscita o bot antigo em 15s), espera
  a fila esvaziar e sobe **um** só. A receita vive em `RECEITA_REINICIO`, um
  lugar só — ela estava duplicada em 3 e consertar um deixaria a armadilha viva
  (guardião em `tests/test_bot_atualizar.py`). **Lição geral: "disparar e sair"
  (`Start-Process` sem `-Wait`, `nohup`, `&`) quebra qualquer supervisor que
  gerencie por árvore de processos** — e o sintoma não é erro, é um comando que
  parece funcionar e não faz nada. O `/atualizar` não sofre disso porque não mata
  ninguém: o próprio bot sai e o laço do `.bat` o traz de volta.
- **`/atualizar` (git pull pelo Telegram) NÃO dispara processo para se
  reiniciar.** O bot roda sob o `Iniciar Bot (auto).bat`, que é um **laço**: se o
  processo morre, ele sobe de novo 15s depois, já com o código novo. Então o
  comando só **sai** (`logging.shutdown()` + `os._exit(0)`) — nada de `schtasks`
  disparado daqui, que é exatamente o terreno minado do WinError 6 (processo sem
  console herdando handles inválidos) que fez o auto-start pela tela ser
  abandonado. **`BOT_SEM_PAUSA` é o sinal** de que quem subiu o bot foi esse
  lançador (só ele define a variável): sem ela, sair deixaria o bot **fora do
  ar**, então o comando atualiza e manda reiniciar na mão — bot mudo é pior que
  bot desatualizado. O ciclo fecha com um recado em `dados/reinicio_pendente.json`
  lido no `post_init` (`_avisar_reinicio`, "✅ Voltei"): quem pediu está no
  celular e não vê a máquina. O recado é **apagado antes do envio** — um recado
  sobrevivente avisaria a cada reinício, para sempre.
- **Atualização remota não pode destruir trabalho local nem atropelar operação.**
  Duas guardas, ambas por dano irreversível: (1) **árvore suja** —
  `nomes_sku.json` e `skus_por_anuncio.json` são **versionados e editados pela
  tela** na máquina de operação; com alteração não commitada o comando **não puxa
  nada** e lista os arquivos. Nada de `stash`/`checkout`/`reset` automático: o
  "conflito" aqui é a ordem de separação e os nomes de produto que o dono digitou.
  (2) **`TRAVA_CONTA` com `blocking=False`** — o pull troca os `.py` sob um
  processo que já os carregou, e o reinício poderia matar o bot **entre gerar o
  ZIP e marcar o estado** (invariante 1); ocupado responde "tente em instantes"
  em vez de ficar mudo esperando. O pull é **`--ff-only`** (numa pasta de operação
  o histórico só anda para a frente; sem fast-forward há commit local, e isso pede
  um humano) e o git roda com **`stdin=DEVNULL` + `GIT_TERMINAL_PROMPT=0`** —
  senão ficaria esperando usuário/senha para sempre num processo sem console.
- **`/atualizar` reinicia por DEFASAGEM, não por "o pull trouxe algo"
  (06/08/2026).** O comando decidia pelo resultado do `git pull`: pull vazio →
  *"nada a fazer"*, sem reiniciar. Mas pull vazio **não** significa processo em
  dia — quem resolveu a árvore suja com um `git pull` na mão (caminho
  **obrigatório** quando há `nomes_sku.json`/`skus_por_anuncio.json` editados
  pela tela) já trocou os arquivos, e o bot no ar segue com o que carregou no
  logon. O dono lia "já está atualizado" e ficava **convencido de que
  atualizou**, rodando o código antigo — sucesso reportado sem o efeito
  entregue, e com o agravante de que o `/versao` existe justamente para
  diagnosticar esse sintoma. Hoje quem decide é **`_desatualizado()`**, o
  **ponto único** da pergunta (antes o `/versao` a tinha inline e o
  `/atualizar` não a fazia). Na dúvida devolve **False**: commit desconhecido
  de um dos lados não é prova, e reinício em falso derruba o bot por 15s à toa
  (regra do `_mtime_log_monitor`). A árvore suja continua bloqueando o pull,
  mas **avisa** quando o processo também está atrasado.
- **Código novo só vale depois de REINICIAR o processo:** `git pull` troca os
  arquivos; o bot que já está no ar segue com o que carregou no logon. O sintoma
  é "a mudança não pegou", sem sinal nenhum do porquê — aconteceu **duas vezes**
  (o `/vendasapos` e o layout do resumo de vendas). Duas defesas: o
  `Atualizar programa.bat` compara o commit antes/depois e reinicia a tarefa do
  Agendador quando algo mudou; e o **`/versao`** compara o commit que o processo
  carregou (`COMMIT_EM_USO`, fixado no import) com o que está na pasta agora,
  avisando quando divergem. O leitor de commit lê o `.git` **direto** (dois
  arquivos de texto) — nunca `subprocess`, que sob `pythonw` herda handles
  inválidos (WinError 6, ver "Áreas de risco"). A **tela** tem o mesmo problema,
  mas se resolve fechando e abrindo.
- **O bot sobe sozinho no login do Windows (Agendador de Tarefas), não pela
  tela:** o alerta acima só funciona com o bot rodando. A 1ª versão fazia a
  tela (`separador_gui.py`) subir o bot sozinha ao abrir — **abandonada**
  depois de 2 bugs reais de mesma causa-raiz (a tela roda via `pythonw`, sem
  console, e qualquer `subprocess` disparado dali herda handles de
  stdin/stdout/stderr inválidos — ver "Áreas de risco" em
  `docs/ARQUITETURA.md` pro histórico completo). Corrigir cada sintoma não
  resolvia a causa, então a solução foi trocar de mecanismo: rode **uma vez**
  `atalhos/registrar-tarefa-bot.ps1` (gatilho `AtLogOn` do Agendador de
  Tarefas) — sobe `atalhos/'Iniciar Bot (auto).bat'` (reusa o lançador com
  reinício automático já existente) sem janela visível, num processo criado
  do zero pelo Windows (sem herdar nada quebrado), independente da tela
  estar aberta. Sem lock de PID: uma duplicata eventual é autolimitada pelo
  próprio Telegram (erro 409 ao pollar duas instâncias do mesmo bot).

## Pegadinhas de domínio (Shopee) — validadas com loja real

- `get_shipping_parameter` e `get_tracking_number` são **GET** (POST → 404).
- `create_shipping_document` **exige `tracking_number`** (AWB) no corpo, buscado via
  `get_tracking_number`; sem ele → `logistics.tracking_number_invalid`.
- A etiqueta só existe **depois de "Organizar Envio"** (gera o AWB). O app organiza
  como **Postagem (drop-off)** via `ship_order` — sempre essa opção, nunca buyer-pickup.
  `info_needed.dropoff` lista os campos exigidos (geralmente vazio; às vezes
  `branch_id`/`sender_real_name`).
- **Entrega Instantânea NÃO se aplica — decisão do dono, não achado técnico
  (05/08/2026).** A Shopee anunciou a iniciativa por e-mail (mercados incluindo
  BR) pedindo que apps de fulfillment suportem o fluxo. O modelo é incompatível
  por definição com a operação: Instant Delivery depende de um **rider que a
  Shopee despacha para buscar na porta do vendedor** logo após a venda; o dono
  **leva os pacotes num ponto de coleta** (Postagem/drop-off, a cláusula acima) —
  são duas logísticas diferentes, não uma opção que se liga. `python
  shopee_api.py canais` existe como diagnóstico (`v2.logistics.get_channel_list`,
  `service_type_identifier == "instant"`), mas a resposta já é conhecida por
  fora da API: não rode para "confirmar", rode só se o **modelo de envio**
  mudar algum dia.
- **Já organizado ≠ sem drop-off:** um pedido já organizado (no painel, ou pelo
  lote) tem `info_needed={}` até o AWB sair. `organizar_envio` consulta
  `envio_ja_arranjado(param)` **antes** de recusar: se já arranjado, **pula o
  `ship_order` e só aguarda o AWB**; só levanta "não oferece Postagem (drop-off)"
  quando o envio **não** está arranjado E não oferece drop-off. Sem isso,
  `info_needed={}` disparava um falso erro mandando reorganizar o que já estava
  organizado (achado 5.3). `envio_ja_arranjado` = nenhum de
  pickup/dropoff/non_integrated em `info_needed`.
- **Organizar em lote:** `_organizar_varios` é em camadas — AWB existente
  (idempotência) → **`_filtrar_ja_arranjados`** (quem já foi arranjado, só
  falta o AWB, NUNCA vai pro batch — ver "compliance" abaixo) → `batch_ship_order`
  (até 50 num request, só quem sobrou) → confirmação **pelo AWB** (não confiar
  no formato da resposta do batch). Quem sobra sem AWB **depois do batch**
  vira `falhas` ("aguardando confirmação, tente de novo") — **não** cai no
  individual (ver por quê abaixo). O fallback individual (`organizar_envio`)
  só recebe quem veio do `_filtrar_ja_arranjados` (1.5) ou quem o batch nunca
  chegou a tentar (endpoint indisponível por inteiro).
- **Compliance da Shopee — success rate do `v2.logistics.ship_order` (achado
  2026-07, 2 rodadas; ENCERRADO em 05/08/2026).** A Shopee pedia success rate
  > 90% por 7 dias consecutivos **nesse endpoint** (só o singular — confirmado
  com o suporte que `batch_ship_order` **não** conta pra mesma métrica).
  **A resposta final do suporte (e-mail de 05/08/2026) fecha o assunto:** "não
  há penalização ativa no momento", e a tarefa "se houver dias **sem chamada**,
  quebra o ciclo" — defeito que eles dizem estar em melhoria interna. Some o
  prazo e some o risco; **não trate como urgência**.
  E o achado que decorre disso: **a sequência de 7 dias é inalcançável nesta
  operação por construção, e não por falha.** O caminho normal manda tudo pelo
  `batch_ship_order` (que não conta), e o individual, quando acionado, cai no
  ramo `envio_ja_arranjado` e **pula** o `ship_order` — o singular só é chamado
  de fato quando o endpoint de lote está indisponível por inteiro. Sem chamadas,
  não há o que medir; fim de semana sem despacho já quebraria o ciclo sozinho.
  **NÃO "conserte" isso forçando chamadas:** para manter o ciclo vivo o app
  teria de chamar o singular em pedido já organizado, que é exatamente o que
  produz `package_already_shipped` — o erro que a métrica penaliza. Manipular o
  indicador o derrubaria, e o comportamento atual (lote + não reenviar o que já
  está arranjado) é o correto, construído pelas duas rodadas abaixo. O FAQ lista "This
  parcel has already been shipped" (`logistics.package_already_shipped`) e
  "The order is being allocated, please wait until the allocate is
  completed" (`logistics.error_param`) como causas de erro documentadas —
  mensagens exatas confirmadas com o suporte.
  **Rodada 1** (achado inicial): só o caminho individual checava
  `envio_ja_arranjado` antes de (re)enviar; o caminho em lote mandava
  **todos** os `restantes` pro `batch_ship_order` sem essa checagem.
  Corrigido com `_filtrar_ja_arranjados` (consulta `parametros_envio` em
  paralelo antes do batch).
  **Rodada 2** (revisão depois de respostas do suporte da Shopee — ver
  `docs/PRIORIDADES_TECNICAS.md` item 11): a propagação de
  `fulfillment_status`/`is_shipment_arranged` após um ship aceito pode levar
  **até 15-20 minutos** — bem mais que os ~40s de polling deste módulo. Isso
  revelava que a rodada 1 não resolvia o problema de verdade: um pedido que
  passa pelo batch mas fica sem AWB (só por causa do timeout curto, não
  porque falhou) caía no fallback individual, que consultava
  `parametros_envio` ainda com o status **antigo** (não propagado) e
  chamava `ship_order` **de novo** — exatamente o cenário "already shipped"
  que conta contra a métrica. Corrigido de verdade: esses pedidos não vão
  mais pro individual, viram `falhas` pendentes de confirmação (a próxima
  tentativa, minutos depois, já vê o status atualizado via
  `_filtrar_ja_arranjados` e não reenvia). Defesa em profundidade adicional
  em `organizar_envio`: catch específico pra "already been shipped" (não
  propaga como erro, só passa a aguardar o AWB) e retry com backoff curto
  (3 tentativas, 3s) pra "being allocated" (documentado como transiente
  pela própria Shopee). A migração mais completa que a Shopee recomenda
  (`v2.order.search_package_list` + `v2.order.get_package_detail`,
  `is_shipment_arranged` já vem por pacote na busca; `package_number` pode
  ser 1:N com `order_sn`) é uma mudança maior (novo modelo de identidade por
  pacote) e ficou registrada como item de backlog — não é urgente pra
  fechar o requisito de compliance com a correção acima.
- **Desempenho (medido, ver `docs/ARQUITETURA.md`):** organizar é **~14s fixos**
  (latência da Shopee emitir o AWB — piso intransponível, NÃO é o número de
  chamadas, então **batch não acelera**). O ganho está em **gerar os documentos
  em paralelo por pedido** (`_gerar_lote`; a Shopee processa requests
  concorrentes em paralelo) — mediu ~70% menos na fase de gerar. Cronometragem
  por fase em `shopee_tempos.log` (`_log_tempos`, gitignorado).
- **Desempenho do "Atualizar" ML:** as 3 fases (`buscar_pedidos` → `filtrar_para_imprimir`
  → `extrair_itens`+`agrupar`) já são paralelas. A fase cara é o **filtro** — uma
  chamada `GET /shipments/{id}` por pedido **não-terminal** (o cache de envios
  `envios_cache.json` só guarda status **terminais**, então pedido `paid` ainda não
  `ready_to_print` é re-consultado a cada Atualizar; cresce com o volume da janela
  de `DIAS_JANELA=30`). `filtrar_para_imprimir` roda com **20 workers** e aceita um
  `stats={}` opcional (checados/cache_hits/prontos) que `coletar_grupos` loga por
  fase em `ml_tempos.log` (`_log_tempos` do núcleo, gitignorado; espelha o da
  Shopee — nunca levanta, só contagens/segundos). Para cortar a re-consulta que
  cresce, o próximo passo é um **cache de TTL curto** para envios não-terminais-e-não-prontos
  (backlog em `PRIORIDADES_TECNICAS.md`) — mexe em área de risco (não pode esconder
  um envio que virou `ready_to_print` dentro do TTL), por isso ficou fora deste lote.
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
  `sem_segredos` cobre **quatro formas** (varredura 2026-08-03): **query**
  (`chave=valor`), **JSON/repr de dict** (`"chave": "valor"`), **segredo no
  CAMINHO da URL** e o cabeçalho **Bearer**. As duas últimas existem porque a
  regex de `chave=valor` não as alcança: o token do **Telegram** viaja em
  `/bot<ID>:<TOKEN>/` (por isso o `httpx` é silenciado no bot — isto é a rede de
  baixo) e o do **ML** em `Authorization: Bearer …`. As chaves incluem
  `client_secret`/`partner_key`/**`app_secret`** além de token/sign/code.

## Antes de fechar uma mudança (mantenha o repertório em dia)

O repertório (docs + grafo) é o que um chat novo lê para entender o projeto — se
ele defasa, a próxima sessão parte de informação errada. Por isso, ao terminar
uma mudança, atualize **o que se aplicar** (faz parte do "pronto", não é opcional):

- **`docs/CHANGELOG.md`** — uma entrada em `[Não lançado]` para toda mudança que
  o dono perceberia (feature, correção, segurança, doc relevante).
- **`CLAUDE.md` + espelho `AGENTS.md`** — se criou/removeu convenção, módulo ou
  pegadinha de domínio, ou mexeu no **mapa do código**.
- **`docs/ARQUITETURA.md`** — se tocou numa invariante crítica, fluxo ou área de
  risco (confira o **contador de invariantes** no `CLAUDE.md`).
- **`graphify-out/graph.json` + `GRAPH_REPORT.md`** — nós dos módulos/funções
  novos e os "porquês" como `rationale`/`concept` (ver "SEMPRE atualize o grafo"
  acima); valide **0 arestas órfãs**.
- **`docs/PRIORIDADES_TECNICAS.md`** — se concluiu um item ou registrou uma
  decisão de "não fazer agora".
- **`obsidian/`** — verifique/atualize as notas afetadas quando houver mudança de
  **comportamento, arquitetura, decisão, integração, incidente ou procedimento**
  operacional (ex.: nova funcionalidade → nota em `Funcionalidades/`; nova decisão →
  `Decisões/`). Mudança **cosmética/interna sem impacto documental não exige** tocar
  as notas. Rode `python tools/validar_obsidian.py` (links, frontmatter, segredos).

Regra de ouro: **mudou algo neste guia, replique no espelho `AGENTS.md`.** Cada
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
- Trailer de commit (já automático): `Co-Authored-By` + `Claude-Session`.
- O dono usa a pasta fora do OneDrive (`C:\contador`) com `git config gc.auto 0`
  (o OneDrive travava o `.git`).
