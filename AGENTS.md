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
| `bot_telegram.py` | Bot de **consulta** (somente leitura). |
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
  `envios_pendentes`, `marcar_impresso`) — não reimplemente o merge.
- **Multi-conta (ML):** arquivos por conta em `contas/{nome}/`; `definir_conta()`
  troca os globais. Shopee é **uma loja só** (`credenciais_shopee.json`).
- **Modo "🌐 Ambas" (ML):** radio extra no seletor de conta (dia de motorista
  único). `ProvedorMLAmbas` coleta as contas em sequência e **funde** grupos de
  mesmo SKU+qtd (`fundir_grupos`; sub-grupos em `.por_conta`); imprime cada
  conta com o token dela num ZIP único; estado segue **por conta** (o
  `marcar_impresso` roteia com `definir_conta` antes de cada gravação). A GUI
  consulta status/pendentes **via provedor** (`prov.status_grupo`, não o core
  direto). Não é persistido no config (escolha pontual).
- **Token: sempre `obter_token(cred)`** (ML e Shopee) — cache + lock double-checked.
  Nunca chamar `renovar_token` direto: o refresh_token **rotaciona** e uma corrida
  pode invalidá-lo (travando a conta). Como o lock só cobre **threads**, dentro
  dele `obter_token` **relê o disco** (`_ler_json(ARQUIVO_CRED)`) e adota o token
  salvo — protege também **processos** distintos na mesma conta (GUI + bot).
  `renovar_token` **não re-tenta** (`tentativas=1`): re-tentar o refresh grant após
  o servidor já ter rotacionado gastaria um token de uso único.
- **Escrita de JSON é atômica e durável** (`.tmp` + `flush`/`fsync` → `replace`) e
  leitura tolerante. Credenciais têm espelho **`.bak`** com auto-recuperação
  (queda de energia não exige refazer o token); `.bak` é gitignorado.
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
  separação (ver ordenação abaixo).
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
  persiste). A `divisoria` já emite `^CI28`. **Não** converta o nome para CP850 (o
  app da Zebra lê o ZPL como UTF-8).
- **Identificação na Shopee (sem carimbo):** a etiqueta Shopee é uma imagem pronta
  **sem o nome do produto** (e não há faixa livre estável para carimbar — validado
  com 10 etiquetas: o miolo varia com a rota). Então a **tela** substitui o carimbo
  listando o **código de rastreio (AWB) de cada etiqueta já impressa** do grupo
  (`Grupo.rastreios`), à esquerda, embaixo do nome — o operador cruza o código da
  etiqueta física com o produto. Preenchido no `preencher_rastreios` (todos os
  envios impressos, em paralelo) e na hora da impressão (dos `awbs`, sem re-buscar).
  Pendentes não têm AWB (só existe após organizar), então não mostram código.
- **Impressão:** ZPL → `.zip` em `PASTA_DOWNLOADS` com nome que a Zebra reconhece
  (prefixos: `etiqueta de envio` p/ ML, `etiqueta shopee` p/ Shopee).
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

## Pegadinhas de domínio (Shopee) — validadas com loja real

- `get_shipping_parameter` e `get_tracking_number` são **GET** (POST → 404).
- `create_shipping_document` **exige `tracking_number`** (AWB) no corpo, buscado via
  `get_tracking_number`; sem ele → `logistics.tracking_number_invalid`.
- A etiqueta só existe **depois de "Organizar Envio"** (gera o AWB). O app organiza
  como **Postagem (drop-off)** via `ship_order` — sempre essa opção, nunca buyer-pickup.
  `info_needed.dropoff` lista os campos exigidos (geralmente vazio; às vezes
  `branch_id`/`sender_real_name`).
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
- **Erro HTTP da Shopee não pode vazar o token:** a URL assinada leva
  `access_token`/`sign` na query, então `_get_shop`/`_post_shop`/`_download_shop`
  **não** usam `raise_for_status()` (a mensagem dele inclui a URL) — passam por
  `_levantar_se_erro`, que lança `SeparadorError` limpo (path + status + erro do
  corpo). Mantenha assim: sem isso o token cai no log/tela e no chat do bot.

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
