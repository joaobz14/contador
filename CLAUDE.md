# Guia do projeto (para o Claude Code)

Ferramenta em Python para **separar e imprimir etiquetas de envio** de marketplaces
(Mercado Livre e Shopee) numa impressora térmica Zebra. Lê os pedidos prontos,
agrupa por **produto + quantidade**, gera **ZPL** e entrega um `.zip` na pasta
**Downloads**, que um app separado da Zebra (`impressora_zebra_usb.py`, fora deste
repo) monitora e imprime.

## Mapa do código

| Arquivo | Papel |
|---|---|
| `separador_etiquetas_ml.py` | Núcleo: API do ML, agrupamento, estado, ZPL, carimbo, CLI. |
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
  `docs/ARQUITETURA.md` **antes** de reler os arquivos crus. Sem o CLI
  `graphify` no ambiente, leia o `graph.json` direto.
- **`docs/ARQUITETURA.md`**: fluxos operacionais, **invariantes críticas**,
  arquivos locais e áreas de risco — leitura obrigatória antes de mexer em
  estado/token/impressão. **`docs/PRIORIDADES_TECNICAS.md`**: backlog técnico
  sugerido (ordem recomendada de evolução).
- **`AGENTS.md` é espelho deste arquivo** (adaptado para o Codex: título e
  trailer). Alterou uma convenção aqui? Replique lá.
- **NÃO rode `graphify hook install`**: o hook reconstrói o grafo só com código
  (AST) e apagaria a camada de docs/arquitetura — foi desinstalado de propósito.
  Após mudanças grandes, refaça a extração completa + a passada semântica dos
  docs manualmente.

## Convenções

- **Provedor, não `if marketplace`:** a GUI fala com `self.prov` (ML ou Shopee). Toda
  capacidade nova de impressão/coleta entra como método do provedor.
- **Estado de "já impresso"** é por marketplace e por **dia de despacho**: ML em
  `contas/{conta}/estado_grupos.json`, Shopee em `estado_shopee.json`. Chave:
  `{dia}|{chave}|q{qtd}`. Use os helpers do núcleo (`_chave_estado`, `_impressos`,
  `status_grupo`, `envios_pendentes`).
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
  entre threads pode invalidá-lo (travando a conta).
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
  SKU → nome. Editável na GUI pelo botão **✏ Nomes** (`EditorNomes`); use
  `carregar_nomes()`/`salvar_nomes()` (ordena chaves, apara, descarta vazios).
- **Identificação na impressão** (`MODO_IDENT`): `carimbo` (SKU na DANFE),
  `carimbo_nome` (nome da aba Nomes; fonte adaptativa via `_fonte_nome` — curto
  maior, longo menor até 3 linhas; sem nome cadastrado cai no SKU; pedido com
  2+ unidades ganha "2x"/"3x" em destaque abaixo do nome), `divisoria`,
  `nenhuma`. `CARIMBAR_SKU` é legado (compat de config antigo).
- **Impressão:** ZPL → `.zip` em `PASTA_DOWNLOADS` com nome que a Zebra reconhece
  (prefixos: `etiqueta de envio` p/ ML, `etiqueta shopee` p/ Shopee).
- **Segredos nunca versionados** (ver `.gitignore`): credenciais, estado, caches,
  `config.json`, `bot_config.json`.
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

## Fluxo de trabalho (git)

- Desenvolver na branch designada; **um PR por feature**. Não mergear PR sem o dono pedir.
- Trailer de commit (já automático): `Co-Authored-By` + `Claude-Session`.
- O dono usa a pasta fora do OneDrive (`C:\contador`) com `git config gc.auto 0`
  (o OneDrive travava o `.git`).
