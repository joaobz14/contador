# Graph Report - .  (2026-07-08)

## Atualizações manuais (pós-build)

> Enriquecimentos da camada de docs feitos à mão (o CLI `graphify` não roda neste
> ambiente e reconstruiria só o AST, apagando esta camada). O `graph.json` é a
> fonte consultável; os números do relatório abaixo refletem o build automático.

- **2026-07-14 — Adotar anúncio ML sem SKU num SKU do sistema:** de-para
  `skus_por_anuncio.json` (código do anúncio → SKU) aplicado em `identidade`
  (reescreve a chave); editável na GUI (botão inline 🏷 Atribuir SKU +
  `EditorSkusAnuncio`). Nó `anuncio_sem_sku_adota` (rationale) ligado a
  `identidade`, `extrair_itens`, `separador_gui` e ao conceito
  `ordem_separacao_pessoal`.

- **2026-07-14 — Rastreio (AWB) de todos os grupos Shopee na tela:** como a
  etiqueta Shopee não tem o nome do produto (e não há faixa livre estável para
  carimbar — validado com 10 etiquetas: o miolo varia com a rota), a tela lista o
  código de cada etiqueta impressa do grupo (`Grupo.rastreios`). Nó
  `shopee_rastreio_todos_grupos` (rationale) ligado a `preencher_rastreios`,
  `imprimir_lotes`, `separador_gui` e ao conceito `carimbo_encoding_ci28`.

- **2026-07-14 — Auditoria de sincronia código × grafo:** conferido nó a nó
  (funções/métodos/classes) o `graph.json` contra o código atual. A camada AST
  está congelada no commit `5233aef` (build de PR #93); de lá até hoje 31 commits
  mexeram no núcleo (estado.py/registro.py novos, etc.). Achados e correções:
  - **6 funções novas sem nó → adicionadas** (com arestas `calls`/`method`/
    `contains` reais): core `_natural`, `_ordem_nomes`, `_chave_ordem` (ordenação
    por Nomes); `estado._hoje_br`; GUI `SeparadorApp._ctx_log`,
    `EditorNomes._mover`. Resultado: **0 função do código sem nó**.
  - **7 "nós órfãos" aparentes eram falso-positivo:** `status_grupo`,
    `envios_pendentes`, `_ler_json`, `_gravar_json`, `_chave_estado`, `_impressos`,
    `_limpar_estado_antigo` continuam existindo no núcleo como **aliases/re-exports**
    de `estado.py` (linhas 153-154 e 1133-1137) — nós válidos, não stale.
  - Estado final: **884 nós, 1577 arestas, 0 arestas órfãs** (validado).
  - **Limites (precisam do CLI `graphify` p/ 100%):** (1) o `graph.html` é uma
    **visualização baked antiga** (embute os dados; não lê o `graph.json`) — está
    defasado e só um rebuild o regenera; (2) mudanças de **corpo** de funções nesses
    31 commits (ex.: `obter_token` relê disco, `renovar_token` `tentativas=1`,
    carimbo `^CI28`) podem ter deixado alguma aresta `calls`/`imports` levemente
    desatualizada mesmo com o nó certo — só um rebuild completo re-deriva todas.
    O inventário de **nós** está fiel; a topologia de **arestas** do AST antigo não
    foi 100% re-derivada.

- **2026-07-14 — Levantamento Amazon SP-API (pesquisa, nada implementado):** doc
  `docs/AMAZON_SP_API.md` sobre como a API da Amazon encaixaria no app no futuro.
  Nós novos: `docs_amazon_sp_api` (document) + conceitos
  `amazon_fbm_vs_fba` (**só FBM/MFN gera etiqueta; FBA/DBA não** — risco de
  negócio/BR, o teste decisivo antes de codar), `amazon_zpl_termico` (Amazon
  devolve **ZPL203 térmico** em Base64/GZIP — mesmo fluxo ZPL→zip→Downloads da
  Shopee) e `amazon_lwa_auth` (OAuth2 LWA com `refresh_token`, reauth 365d — reusa
  o padrão `obter_token`). Ligados por `rationale_for`/`conceptually_related_to` a
  `provedores`, `provedores_provedorshopee` e `obter_token`.
- **2026-07-08 — Camada comum de estado (`estado.py`):** extraída a lógica de
  "já impresso" (antes duplicada entre núcleo e `shopee_api`). Nós novos:
  `estado` (arquivo) + funções (`marcar_impresso`, `carregar`, `status_grupo`,
  `chave_estado`, `impressos`, `envios_pendentes`, `limpar_antigo`, `salvar`,
  `ler_json`, `gravar_json`). Descobertas registradas como nós:
  - `estado_camada_comum` — módulo-folha, path-parametrizado, dono único do merge.
  - `estado_seam_salvar_injetado` — **barreira→solução**: delegar `marcar_impresso`
    direto contornava o seam `salvar_estado` que os testes interceptam, escrevendo
    o `estado_shopee.json` real e contaminando re-execuções; resolvido injetando
    `ler`/`salvar` (a gravação segue pela função de módulo de cada marketplace).
  - `estado_prio_concluida` — a prioridade #1 (`prio_camada_estado`) foi concluída.
- **2026-07-10 — Contrato de impressão da GUI explícito:** renomeados os métodos
  do fluxo em `separador_gui.py` — `_imprimir_lotes_thread` → `_gerar_sem_marcar_thread`
  (passo 1: gera sem marcar) e `_pos_lotes` → `_confirmar_e_marcar` (passos 2-3:
  confirma e só então marca, único ponto que chama `marcar_impresso`). Nó novo
  `gui_contrato_explicito` ligado a `inv_confirma_antes_marcar` e à prioridade
  `prio_contrato_impressao` (concluída). Sem mudança de comportamento.
- **2026-07-10 — Log operacional (`registro.py`):** módulo-folha com o logger
  `separador.log` + `sem_segredos()`. Nós: `registro` (arquivo), `sem_segredos`,
  `log`, `log_operacional` e `registro_redige_segredos`. Descoberta de segurança
  registrada: a Shopee assina URLs com `access_token`/`sign` na query e um
  `raise_for_status` propaga a URL até o `_erro` da GUI — `sem_segredos()` redige
  os segredos **antes** de logar, para o token nunca cair no `separador.log`.
- **2026-07-10 — Auditoria/segurança: erro HTTP da Shopee não vaza o token:**
  `_get_shop`/`_post_shop`/`_download_shop` deixaram de usar `raise_for_status()`
  (cuja mensagem inclui a URL assinada com `access_token`/`sign`) e passam por
  `_levantar_se_erro`, que lança um `SeparadorError` limpo (path + status + erro do
  corpo). Como vira `SeparadorError`, o bot passa a tratá-lo pelo ramo limpo — o
  token não vai mais para `bot.log` nem para o chat do Telegram. Nós:
  `shopee_api_levantar_se_erro`, `shopee_erro_sem_token`.

- **2026-07-10 — Auditoria/segurança: robustez do refresh de token.** (1)
  Corrida de refresh **entre processos** (GUI + bot na mesma conta): o
  `threading.Lock` só cobre threads, então `obter_token` passou a **reler o disco**
  dentro do lock e adotar o token salvo por outro processo (nós:
  `token_corrida_multiprocesso`). (2) `renovar_token` **não re-tenta**
  (`tentativas=1`) — evita gastar o refresh_token de uso único num retry após
  rotação (nó: `token_refresh_sem_retry`). Ligados a `obter_token`/`renovar_token`
  de ML e Shopee.

- **2026-07-10 — Ordem de separação pessoal (por SKU no bloco "qtd 1").**
  `ordenar_grupos` (usado por `agrupar` e `fundir_grupos`) mantém os blocos por
  quantidade e, só no bloco de qtd 1, segue a **ordem da aba Nomes** (setas ↑/↓ no
  `EditorNomes`; `nomes_sku.json` passou a ser order-significant — `salvar_nomes`
  preserva a ordem). SKU não cadastrado vai pro fim em ordem natural. Vale tela +
  impressão, ML + Shopee. Nós: `ordenar_grupos`, `ordem_separacao_pessoal`.

- **2026-07-10 — Melhorias de qualidade (sem features novas).** (1) DRY do retry
  HTTP: `_requisicao_get`/`_requisicao_post` compartilham `_com_retry` +
  `_STATUS_RETRY` (nó `retry_dry`). (2) Removido import morto (`pathlib.Path` no
  `shopee_api`). (3) **Lacuna de teste fechada**: o nome do `.zip` do ML
  ("etiqueta de envio - ") que o app da Zebra detecta era sempre mockado — agora
  há teste fixando o prefixo + o ZPL interno (nó `zebra_prefixo_testado`).
  Auditoria não achou código morto (0 funções sem uso). Deliberadamente NÃO
  refatorei o caminho crítico de token (recém-mexido) nem os wrappers async do
  bot (sem cobertura de teste) — risco > ganho.

- **2026-07-10 — Encoding do carimbo (acentos na DANFE, integração com o app da
  Zebra).** `carimbar_zpl` estampava o nome em UTF-8 **sem `^CI28`** → nomes
  acentuados (FOGÃO, CANHÃO…) saíam embolados na impressora. Fix cirúrgico:
  `^CI28` só antes do `^FD{nome}` e `^CI0` de reset logo após o `^FS` — não afeta a
  nota fiscal acima (conteúdo do ML) nem vaza para a etiqueta de envio abaixo (o
  `^CI` persiste entre etiquetas). Validado com o chat do app da Zebra (que lê o
  ZPL com decode UTF-8, então o nome deve seguir em UTF-8). Nó: `carimbo_encoding_ci28`.

## Corpus Check
- Corpus is ~39,735 words - fits in a single context window. You may not need a graph.

## Summary
- 844 nodes · 1498 edges · 51 communities (38 shown, 13 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 133 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Interface gráfica (Tkinter)|Interface gráfica (Tkinter)]]
- [[_COMMUNITY_Bot do Telegram|Bot do Telegram]]
- [[_COMMUNITY_Camada de provedor (MLShopeeAmbas)|Camada de provedor (ML/Shopee/Ambas)]]
- [[_COMMUNITY_Fixtures de teste (conftest)|Fixtures de teste (conftest)]]
- [[_COMMUNITY_Testes da Shopee|Testes da Shopee]]
- [[_COMMUNITY_Mock HTTP dos testes|Mock HTTP dos testes]]
- [[_COMMUNITY_Testes de impressão do bot|Testes de impressão do bot]]
- [[_COMMUNITY_Shopee API assinatura HMAC|Shopee API: assinatura HMAC]]
- [[_COMMUNITY_Modelo Grupo + agrupamento + ZIP|Modelo Grupo + agrupamento + ZIP]]
- [[_COMMUNITY_Carimbo por nomeSKU|Carimbo por nome/SKU]]
- [[_COMMUNITY_Erros, credenciais e retry|Erros, credenciais e retry]]
- [[_COMMUNITY_Testes de carimbo (DANFE)|Testes de carimbo (DANFE)]]
- [[_COMMUNITY_Datas BR + busca + cache|Datas BR + busca + cache]]
- [[_COMMUNITY_Testes do modo Ambas|Testes do modo Ambas]]
- [[_COMMUNITY_Shopee organização em lote + AWB|Shopee: organização em lote + AWB]]
- [[_COMMUNITY_Dias úteis, resumo e docs|Dias úteis, resumo e docs]]
- [[_COMMUNITY_Núcleo contas e cache|Núcleo: contas e cache]]
- [[_COMMUNITY_Persistência JSON (backup atômico)|Persistência JSON (backup atômico)]]
- [[_COMMUNITY_Token (cache + lock)|Token (cache + lock)]]
- [[_COMMUNITY_Shopee detalhesagrupamento|Shopee: detalhes/agrupamento]]
- [[_COMMUNITY_Testes de lotescarimbo|Testes de lotes/carimbo]]
- [[_COMMUNITY_Shopee ship_orderrastreioformato|Shopee: ship_order/rastreio/formato]]
- [[_COMMUNITY_Impressão em lote + cronometragem|Impressão em lote + cronometragem]]
- [[_COMMUNITY_Busca de pedidos (ML)|Busca de pedidos (ML)]]
- [[_COMMUNITY_Relatórios de texto|Relatórios de texto]]
- [[_COMMUNITY_Config e multi-conta (núcleo)|Config e multi-conta (núcleo)]]
- [[_COMMUNITY_Editor de nomes (GUI)|Editor de nomes (GUI)]]
- [[_COMMUNITY_Testes de multi-conta|Testes de multi-conta]]
- [[_COMMUNITY_Testes do pipeline de coleta|Testes do pipeline de coleta]]
- [[_COMMUNITY_Testes de impressãoestado|Testes de impressão/estado]]
- [[_COMMUNITY_Testes de agrupamento|Testes de agrupamento]]
- [[_COMMUNITY_Testes de datas|Testes de datas]]
- [[_COMMUNITY_OAuth Shopee (setup)|OAuth Shopee (setup)]]
- [[_COMMUNITY_Shopee geração paralela de etiqueta|Shopee: geração paralela de etiqueta]]
- [[_COMMUNITY_Testes de avaliação de pedido|Testes de avaliação de pedido]]
- [[_COMMUNITY_Testes de paginação de busca|Testes de paginação de busca]]
- [[_COMMUNITY_Testes de cache de envios|Testes de cache de envios]]
- [[_COMMUNITY_Testes de identidade do produto|Testes de identidade do produto]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]

## God Nodes (most connected - your core abstractions)
1. `SeparadorApp` - 44 edges
2. `Grupo` - 28 edges
3. `main()` - 19 edges
4. `main()` - 19 edges
5. `ProvedorMLAmbas` - 18 edges
6. `Provedor` - 17 edges
7. `marcar_impresso()` - 17 edges
8. `cb_botao()` - 16 edges
9. `make_grupo()` - 16 edges
10. `obter_token()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Telegram Bot API (sistema externo)` --conceptually_related_to--> `main()`  [INFERRED]
  docs/ARQUITETURA.md → bot_telegram.py
- `UI: seções 'Para imprimir' e 'Já impressas — arquivadas'` --conceptually_related_to--> `envios_pendentes()`  [INFERRED]
  docs/img/tela.png → separador_etiquetas_ml.py
- `Dependência: requests (HTTP)` --conceptually_related_to--> `obter_token()`  [INFERRED]
  requirements.txt → shopee_api.py
- `INVARIANTE: bot não imprime Shopee (só consulta); e não imprime grupo antigo se conta/loja mudou` --rationale_for--> `cb_botao()`  [EXTRACTED]
  docs/ARQUITETURA.md → bot_telegram.py
- `Dependência: python-telegram-bot[job-queue]` --rationale_for--> `main()`  [EXTRACTED]
  requirements-bot.txt → bot_telegram.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Sistemas externos (fora do repositório)** — ext_ml_api, ext_shopee_api, ext_telegram_api, ext_zebra, ext_zebra_app, ext_downloads [INFERRED 0.85]
- **Ponte de impressão: ZIP → Downloads → app Zebra → impressora** — impressao_zip, ext_downloads, ext_zebra_app, ext_zebra [INFERRED 0.85]
- **Invariantes críticas de negócio** — inv_confirma_antes_marcar, inv_reimpressao_nao_altera, inv_marcar_merge, inv_token_via_obter, inv_shopee_awb, inv_bot_shopee_readonly [INFERRED 0.80]
- **Arquivos locais não versionados (por máquina/conta)** — file_credenciais, file_credenciais_shopee, file_estado_grupos, file_estado_shopee, file_config, file_bot_config [INFERRED 0.85]
- **Camada de provedor (ML / Shopee / Ambas)** — provider_abstraction, provedores_provedor, provedores_provedormlambas, separador_gui_separadorapp [INFERRED 0.85]
- **Shopee Fase 2: organizar → AWB → etiqueta** — organizar_camadas, shopee_api_organizar_varios, shopee_api_batch_ship_order, shopee_api_gerar_etiqueta, shopee_api_numero_rastreio [INFERRED 0.85]
- **Token seguro (cache + lock, sem corrida de refresh)** — token_obter_lock, separador_etiquetas_ml_obter_token, shopee_api_obter_token, shopee_api_renovar_token [INFERRED 0.75]
- **Desempenho Shopee: AWB é piso fixo; ganho vem de gerar em paralelo** — awb, perf_organizar_piso, perf_gerar_paralelo, cron_tempos, shopee_api_gerar_lote [INFERRED 0.85]
- **Prioridades técnicas (evolução de baixo risco)** — prio_camada_estado, prio_contrato_impressao, prio_isolar_ambas, prio_nucleo_ml_god [INFERRED 0.80]

## Communities (51 total, 13 thin omitted)

### Community 0 - "Interface gráfica (Tkinter)"
Cohesion: 0.05
Nodes (30): CI: smoke da GUI headless (xvfb) nos 2 marketplaces, CI: pytest em Python 3.11 e 3.12, GUI confirma 'saiu certo?' antes de marcar impresso, GitHub Actions (CI externo), CI: workflow de testes (GitHub Actions), INVARIANTE: GUI só marca impresso após confirmação física, main(), separador_gui.py Telinha do Separador de Etiquetas do Mercado Livre. Mostra os g (+22 more)

### Community 1 - "Bot do Telegram"
Cohesion: 0.07
Nodes (66): _agendar_aviso(), _autorizado(), carregar_config(), cb_botao(), cmd_amanha(), cmd_conta(), cmd_desconhecido(), cmd_detalhar() (+58 more)

### Community 2 - "Camada de provedor (ML/Shopee/Ambas)"
Cohesion: 0.06
Nodes (18): INVARIANTE: modo Ambas usa o token da conta certa e grava no estado da conta certa, Modo 'Ambas' (funde grupos SKU+qtd entre contas ML), PRIORIDADE: isolar melhor o modo Ambas (área crítica), criar_provedor(), fundir_grupos(), Provedor, ProvedorML, ProvedorMLAmbas (+10 more)

### Community 3 - "Fixtures de teste (conftest)"
Cohesion: 0.07
Nodes (24): make_grupo(), Configuracao comum dos testes., _d(), Estado de impressao por shipment_ids e limpeza por idade., Simula a tela e o bot juntos: um marca [5], o outro (que carregou o     estado A, test_carregar_estado_poda_e_persiste(), test_compatibilidade_formato_antigo_string(), test_envio_novo_reabre_como_parcial() (+16 more)

### Community 5 - "Mock HTTP dos testes"
Cohesion: 0.08
Nodes (16): FakeResp, Resposta HTTP falsa para simular requests.get sem rede., Camada HTTP: retry/backoff e download de etiquetas ZPL., Faz requests.get devolver as respostas em ordem; conta as chamadas., _sequencia(), test_baixar_zpl_aceita_zip(), test_baixar_zpl_sucesso_texto(), test_espera_retry_header_invalido_cai_no_backoff() (+8 more)

### Community 6 - "Testes de impressão do bot"
Cohesion: 0.12
Nodes (21): INVARIANTE: bot não imprime Shopee (só consulta); e não imprime grupo antigo se conta/loja mudou, _criar_conta(), _Ctx, _grupo(), _patch_contas(), Testes das funcoes de impressao pelo bot do Telegram.  So a UI (botoes) e testad, test_coletar_grupos_ml_usa_nucleo(), test_coletar_grupos_shopee_usa_shopee_api() (+13 more)

### Community 7 - "Shopee API: assinatura HMAC"
Cohesion: 0.11
Nodes (26): _assinar(), _assinatura_publica(), _assinatura_shop(), baixar_documento(), carregar_credenciais(), criar_documento(), _download_shop(), _gerar_bloco() (+18 more)

### Community 8 - "Modelo Grupo + agrupamento + ZIP"
Cohesion: 0.13
Nodes (25): Estado 'já impresso' por marketplace + dia de despacho, estado_grupos.json (ML · estado impresso · por-conta+dia · local · NÃO versionar), INVARIANTE: envio novo em grupo já impresso reabre o grupo como parcial, INVARIANTE: estado de impresso é por marketplace + conta + dia de despacho, PRIORIDADE: extrair camada comum de estado de impressão (a mais recomendada), PRIORIDADE: tornar o contrato de impressão da GUI explícito (gerar→confirmar→marcar), PRIORIDADE: separar responsabilidades de separador_etiquetas_ml.py (god file), PRIORIDADES_TECNICAS (melhorias sugeridas de baixo risco) (+17 more)

### Community 9 - "Carimbo por nome/SKU"
Cohesion: 0.10
Nodes (25): ÁREA DE RISCO: geração de lote × marcação de estado, FEATURE: carimbo por nome com quantidade em destaque (2x/3x para 2+ unidades), nomes_sku.json (SKU→nome · VERSIONADO e sincronizado por Git), MODO_IDENT: carimbo / carimbo_nome / divisoria / nenhuma, Nomes amigáveis (SKU→nome), editável na GUI, _carimbar_grupo(), carimbar_zpl(), carregar_nomes() (+17 more)

### Community 10 - "Erros, credenciais e retry"
Cohesion: 0.10
Nodes (24): CHANGELOG, INVARIANTE: reimpressão nunca altera o estado de impresso, marcar_impresso: last-writer-merge (tela+bot não se apagam), Response, Retry com backoff (downloads e rede), baixar_zpl(), carregar_credenciais(), _espera_retry() (+16 more)

### Community 11 - "Testes de carimbo (DANFE)"
Cohesion: 0.13
Nodes (15): _grupo(), Carimbo do SKU na DANFE (area livre central), sem rede., test_carimbar_grupo_modo_nenhuma_nao_altera(), test_carimbar_grupo_modo_nome_usa_nome_e_fonte_menor(), test_carimbar_grupo_modo_sku_inalterado(), test_carimbar_grupo_nome_curto_usa_fonte_maior(), test_carimbo_nome_qtd_1_sem_linha_de_quantidade(), test_carimbo_nome_qtd_2_ganha_linha_2x() (+7 more)

### Community 12 - "Datas BR + busca + cache"
Cohesion: 0.11
Nodes (23): date, envios_cache.json (cache de envios finalizados · local · NÃO versionar), achar_grupo(), _amanha_br(), buscar_pedidos(), _carregar_envios_cache(), Coleta, coletar_grupos() (+15 more)

### Community 13 - "Testes do modo Ambas"
Cohesion: 0.15
Nodes (16): core(), Modulo do nucleo com time.sleep neutralizado (testes de retry rapidos)., _g(), Modo "Ambas": fusao das contas ML num grupo por produto (dia de motorista unico), test_coletar_funde_e_soma_contagem(), test_fundir_grupos_junta_por_sku_e_quantidade(), test_fundir_nao_mistura_quantidades_diferentes(), test_imprimir_lotes_nada_pendente_nao_gera_zip() (+8 more)

### Community 14 - "Shopee: organização em lote + AWB"
Cohesion: 0.13
Nodes (22): ÁREA DE RISCO: organização de envio e AWB na Shopee, AWB / tracking_number (piso de latência da Shopee), ARQUITETURA (notas operacionais), Shopee Open Platform API (sistema externo), Telegram Bot API (sistema externo), credenciais.json (ML · segredo · por-conta · local · NÃO versionar), estado_shopee.json (Shopee · estado impresso · por-dia · local · NÃO versionar), INVARIANTE: marcar_impresso recarrega do disco e mescla (não perde marcação concorrente) (+14 more)

### Community 15 - "Dias úteis, resumo e docs"
Cohesion: 0.10
Nodes (21): AGENTS.md (guia do projeto para o Codex), CLAUDE.md (guia do projeto), Dia de despacho: próximos dias úteis + contagem por dia, Tela principal (screenshot da GUI), Página do repositório (GitHub Pages), Pasta Downloads (ponte de impressão, por máquina), Impressora térmica Zebra (hardware externo), App impressora_zebra_usb.py (externo, monitora Downloads) (+13 more)

### Community 16 - "Núcleo: contas e cache"
Cohesion: 0.15
Nodes (19): aplicar_nomes(), buscar_detalhes(), carregar_cache(), _detalhe_item(), extrair_itens(), identidade(), ItemPedido, _largura_zpl() (+11 more)

### Community 17 - "Persistência JSON (backup atômico)"
Cohesion: 0.15
Nodes (18): Path, _caminho_backup(), _carregar_credenciais_com_backup(), carregar_estado(), _gravar_credenciais_com_backup(), _gravar_json(), _ler_json(), _limpar_estado_antigo() (+10 more)

### Community 18 - "Token (cache + lock)"
Cohesion: 0.17
Nodes (15): ÁREA DE RISCO: obtenção/renovação de token, Mercado Livre API (sistema externo), credenciais_shopee.json (Shopee · segredo · por-loja · local · NÃO versionar), INVARIANTE: token sempre via obter_token (lock); nunca renovar_token direto (refresh rotaciona), obter_token(), Token valido do cache, ou renova. Serializa o refresh com um lock e     re-checa, _token_valido(), obter_token() (+7 more)

### Community 19 - "Shopee: detalhes/agrupamento"
Cohesion: 0.16
Nodes (15): buscar_detalhes(), coletar_grupos(), contagem_por_dia(), _data_envio(), _get_shop(), grupos_de_detalhes(), listar_order_sns(), parametros_envio() (+7 more)

### Community 20 - "Testes de lotes/carimbo"
Cohesion: 0.26
Nodes (11): _grupo(), _mocka_download(), Impressao em lote + divisoria + carimbo centralizado (sem rede)., test_gerar_zip_lotes_aborta_em_zpl_invalido(), test_gerar_zip_lotes_nao_marca_estado(), test_preparar_lotes_carimbo_carimba_danfe(), test_preparar_lotes_carimbo_nome_carimba_o_nome(), test_preparar_lotes_divisoria_insere_separador() (+3 more)

### Community 21 - "Shopee: ship_order/rastreio/formato"
Cohesion: 0.14
Nodes (14): Organizar envio em lote por camadas (idempotência→batch→AWB→fallback), detectar_formato(), envio_ja_arranjado(), _montar_dropoff(), numero_rastreio(), organizar_envio(), get_tracking_number (GET): numero de rastreio/AWB do pedido. So existe depois, Finaliza o arranjo de envio (pickup OU dropoff) antes de gerar a etiqueta.     A (+6 more)

### Community 22 - "Impressão em lote + cronometragem"
Cohesion: 0.18
Nodes (13): Cronometragem por fase (_log_tempos → shopee_tempos.log), shopee_tempos.log (diagnóstico de tempos por fase · local · NÃO versionar), imprimir_grupo(), imprimir_lotes(), _log_tempos(), Anexa uma linha com os tempos de cada fase da impressao Shopee. Nunca     levant, Grava a etiqueta na pasta Downloads e devolve (caminho, formato detectado)., Organiza (se preciso e organizar=True, em paralelo), gera/baixa a etiqueta     d (+5 more)

### Community 23 - "Busca de pedidos (ML)"
Cohesion: 0.21
Nodes (13): _avaliar_pedido(), buscar_envio(), buscar_pedidos_amplo(), _data_despacho(), _get(), _prazo_do_envio(), rastrear_sku(), Converte o expected_date da API para o dia (YYYY-MM-DD) no horario de     Brasil (+5 more)

### Community 24 - "Relatórios de texto"
Cohesion: 0.18
Nodes (11): dividir_mensagem(), relatorio.py Monta textos legiveis (para o bot do Telegram) a partir dos dados d, Lista os grupos (SKU + quantidade) agrupados por quantidade do pedido., Quantos pacotes ha em cada dia de despacho., Mensagem do aviso automatico da manha: manchete com a contagem de hoje     segui, Composicao de um SKU: quais produtos/variacoes/voltagens o formam e     quantos, Divide um texto em blocos <= limite (o Telegram corta em ~4096), quebrando     p, texto_bom_dia() (+3 more)

### Community 25 - "Config e multi-conta (núcleo)"
Cohesion: 0.18
Nodes (11): config.json (preferências do app · local · NÃO versionar), aplicar_config(), carregar_config(), conta_ativa(), definir_conta(), migrar_conta_legado(), Preferencias do app (config.json). Vazio/ausente -> {}., Atualiza as globais de arquivo para apontar para contas/{nome}/. (+3 more)

### Community 26 - "Editor de nomes (GUI)"
Cohesion: 0.29
Nodes (3): EditorNomes, Janela para incluir/alterar/remover os nomes amigaveis (SKU -> nome)         sem, Janelinha de edicao do de-para SKU -> nome amigavel.

### Community 27 - "Testes de multi-conta"
Cohesion: 0.33
Nodes (10): _patch_pastas(), Suporte a multiplas contas: subpastas, migracao e selecao., test_aplicar_config_define_conta(), test_definir_conta_cria_pasta_e_atualiza_arquivos(), test_listar_contas_com_duas_contas(), test_listar_contas_ignora_pastas_sem_credenciais(), test_listar_contas_sem_pasta_retorna_vazio(), test_migrar_conta_legado_idempotente() (+2 more)

### Community 28 - "Testes do pipeline de coleta"
Cohesion: 0.36
Nodes (9): _prepara(), _prontos(), Pipeline coletar_grupos: filtro do dia e repasse de progresso., test_coletar_grupos_carimba_dia_de_despacho(), test_coletar_grupos_hoje_nao_carimba_dia(), test_coletar_grupos_por_dia_especifico(), test_coletar_grupos_repassa_progresso(), test_coletar_grupos_somente_hoje() (+1 more)

### Community 29 - "Testes de impressão/estado"
Cohesion: 0.29
Nodes (10): _forca_individual(), _grupo(), Leva _organizar_varios direto ao caminho individual (sem AWB previo e sem     ba, test_imprimir_grupo_organiza_gera_marca(), test_imprimir_grupo_pula_ja_impressos(), test_imprimir_lotes_cronometra(), test_imprimir_lotes_gera_um_unico_zip(), test_imprimir_lotes_nao_marca_estado() (+2 more)

### Community 30 - "Testes de agrupamento"
Cohesion: 0.43
Nodes (7): _item(), Agrupamento por envio: 1 envio = 1 etiqueta (inclui combos multi-SKU)., test_aplicar_nomes_em_combo(), test_combos_iguais_agrupam_juntos(), test_envio_combo_vira_um_grupo_com_uma_etiqueta(), test_envios_de_um_unico_sku_agrupam_por_sku_e_quantidade(), test_mesmo_sku_em_duas_linhas_soma_quantidade()

### Community 31 - "Testes de datas"
Cohesion: 0.25
Nodes (4): Datas no horario de Brasilia (filtro de despacho)., test_proximos_dias_uteis_comeca_no_proximo_util_no_sabado(), test_proximos_dias_uteis_dia_comum(), test_proximos_dias_uteis_numa_sexta_pula_o_fim_de_semana()

### Community 32 - "OAuth Shopee (setup)"
Cohesion: 0.43
Nodes (6): assinar(), extrair(), main(), perguntar(), pegar_token_shopee.py Programa de UMA VEZ SO. Autoriza sua loja na Shopee Open P, Aceita a URL inteira de retorno OU so o code. Devolve (code, shop_id).

### Community 33 - "Shopee: geração paralela de etiqueta"
Cohesion: 0.29
Nodes (7): DESEMPENHO: _gerar_lote gera 1 documento por pedido EM PARALELO (8 por vez) — ganho medido ~70% na fase de gerar, _combinar_etiquetas(), _gerar_lote(), Extrai o ZPL (em BYTES, sem reencodar — evita corromper o ~DG/Z64) de dentro, Junta o ZPL de varias etiquetas Shopee num UNICO .zip (um TXT) — para a     Zebr, Gera as etiquetas dos pedidos `alvo` num so ZIP, tolerando falha parcial.      G, _zpl_do_zip()

### Community 35 - "Testes de paginação de busca"
Cohesion: 0.43
Nodes (6): _fake_get_paginado(), Busca de pedidos: paginacao paralela cobre todas as paginas., Simula orders/search: 50 por pagina, ids sequenciais, paging.total fixo., test_busca_todas_as_paginas(), test_respeita_max_pedidos(), test_uma_pagina_so()

### Community 36 - "Testes de cache de envios"
Cohesion: 0.52
Nodes (6): _envio(), _hoje(), Cache de envios finalizados: pula os terminais e nao deixa de ver os prontos., test_filtrar_nao_cacheia_ready_to_print(), test_filtrar_pula_cacheados_e_cacheia_terminais(), test_limpar_envios_cache_remove_antigos()

### Community 38 - "Community 38"
Cohesion: 0.33
Nodes (3): Dependência: python-telegram-bot[job-queue], Dependência: pytest, Dependência: requests (HTTP)

### Community 39 - "Community 39"
Cohesion: 0.47
Nodes (5): extrair_code(), main(), perguntar(), pegar_token.py Programa de UMA VEZ SO. Pega a autorizacao do Mercado Livre e sal, Aceita a URL inteira colada OU so o codigo.

### Community 41 - "Community 41"
Cohesion: 0.40
Nodes (3): _pronto(), Resumo por dia de despacho (contagem de pacotes por dia)., test_resumo_conta_e_ordena_por_dia()

## Knowledge Gaps
- **18 isolated node(s):** `session-start.sh script`, `session-start.sh script`, `separador-etiquetas-ml`, `setup_gui_tests.sh script`, `Página do repositório (GitHub Pages)` (+13 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeparadorApp` connect `Interface gráfica (Tkinter)` to `Editor de nomes (GUI)`, `Dias úteis, resumo e docs`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Why does `marcar_impresso()` connect `Modelo Grupo + agrupamento + ZIP` to `Interface gráfica (Tkinter)`, `Carimbo por nome/SKU`, `Erros, credenciais e retry`, `Shopee: organização em lote + AWB`, `Núcleo: contas e cache`, `Persistência JSON (backup atômico)`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `INVARIANTE: GUI só marca impresso após confirmação física` connect `Interface gráfica (Tkinter)` to `Modelo Grupo + agrupamento + ZIP`, `Testes de lotes/carimbo`, `Shopee: organização em lote + AWB`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `SeparadorApp` (e.g. with `CI: smoke da GUI headless (xvfb) nos 2 marketplaces` and `Tela principal (screenshot da GUI)`) actually correct?**
  _`SeparadorApp` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `main()` (e.g. with `cb_botao()` and `cmd_amanha()`) actually correct?**
  _`main()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `session-start.sh script`, `session-start.sh script`, `bot_telegram.py Bot do Telegram para CONSULTAR e IMPRIMIR os pedidos de qualquer` to the rest of the system?**
  _206 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Interface gráfica (Tkinter)` be split into smaller, more focused modules?**
  _Cohesion score 0.05217391304347826 - nodes in this community are weakly interconnected._