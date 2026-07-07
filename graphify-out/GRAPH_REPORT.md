# Graph Report - .  (2026-07-07)

## Corpus Check
- Corpus is ~37,267 words - fits in a single context window. You may not need a graph.

## Summary
- 821 nodes · 1450 edges · 50 communities (41 shown, 9 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 113 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Interface gráfica (Tkinter)|Interface gráfica (Tkinter)]]
- [[_COMMUNITY_Bot do Telegram|Bot do Telegram]]
- [[_COMMUNITY_Camada de provedor (MLShopeeAmbas)|Camada de provedor (ML/Shopee/Ambas)]]
- [[_COMMUNITY_Testes da Shopee|Testes da Shopee]]
- [[_COMMUNITY_Fixtures de teste (conftest)|Fixtures de teste (conftest)]]
- [[_COMMUNITY_Mock HTTP dos testes|Mock HTTP dos testes]]
- [[_COMMUNITY_Núcleo despacho, contas, busca|Núcleo: despacho, contas, busca]]
- [[_COMMUNITY_Carimbo, dias úteis e editor de nomes|Carimbo, dias úteis e editor de nomes]]
- [[_COMMUNITY_Modelo Grupo + identificação|Modelo Grupo + identificação]]
- [[_COMMUNITY_Testes de impressão do bot|Testes de impressão do bot]]
- [[_COMMUNITY_Testes de carimbo (DANFE)|Testes de carimbo (DANFE)]]
- [[_COMMUNITY_Testes do modo Ambas|Testes do modo Ambas]]
- [[_COMMUNITY_Erros, credenciais e ZPL|Erros, credenciais e ZPL]]
- [[_COMMUNITY_Persistência JSON (backup atômico)|Persistência JSON (backup atômico)]]
- [[_COMMUNITY_Shopee API assinatura HMAC|Shopee API: assinatura HMAC]]
- [[_COMMUNITY_Testes de lotescarimbo|Testes de lotes/carimbo]]
- [[_COMMUNITY_Shopee geração de etiqueta|Shopee: geração de etiqueta]]
- [[_COMMUNITY_Shopee ship_order e rastreio|Shopee: ship_order e rastreio]]
- [[_COMMUNITY_Datas BR + cache de envios|Datas BR + cache de envios]]
- [[_COMMUNITY_Relatórios de texto|Relatórios de texto]]
- [[_COMMUNITY_Token (renovaçãoretry)|Token (renovação/retry)]]
- [[_COMMUNITY_Coleta de pedidos + nomes|Coleta de pedidos + nomes]]
- [[_COMMUNITY_Shopee organização em lote|Shopee: organização em lote]]
- [[_COMMUNITY_Testes de multi-conta|Testes de multi-conta]]
- [[_COMMUNITY_Testes do pipeline de coleta|Testes do pipeline de coleta]]
- [[_COMMUNITY_Config e multi-conta (núcleo)|Config e multi-conta (núcleo)]]
- [[_COMMUNITY_Shopee detalhesagrupamento|Shopee: detalhes/agrupamento]]
- [[_COMMUNITY_Shopee documento em lote (batch)|Shopee: documento em lote (batch)]]
- [[_COMMUNITY_Shopee token e rastreios|Shopee: token e rastreios]]
- [[_COMMUNITY_Testes de agrupamento|Testes de agrupamento]]
- [[_COMMUNITY_Testes de datas|Testes de datas]]
- [[_COMMUNITY_OAuth Shopee (setup)|OAuth Shopee (setup)]]
- [[_COMMUNITY_Testes de avaliação de pedido|Testes de avaliação de pedido]]
- [[_COMMUNITY_Testes de paginação de busca|Testes de paginação de busca]]
- [[_COMMUNITY_Testes de cache de envios|Testes de cache de envios]]
- [[_COMMUNITY_Testes de identidade do produto|Testes de identidade do produto]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
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

## God Nodes (most connected - your core abstractions)
1. `SeparadorApp` - 44 edges
2. `Grupo` - 28 edges
3. `main()` - 19 edges
4. `main()` - 19 edges
5. `Provedor` - 17 edges
6. `ProvedorMLAmbas` - 17 edges
7. `cb_botao()` - 16 edges
8. `make_grupo()` - 16 edges
9. `marcar_impresso()` - 15 edges
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

## Communities (50 total, 9 thin omitted)

### Community 0 - "Interface gráfica (Tkinter)"
Cohesion: 0.05
Nodes (30): CI: smoke da GUI headless (xvfb) nos 2 marketplaces, CI: pytest em Python 3.11 e 3.12, GUI confirma 'saiu certo?' antes de marcar impresso, GitHub Actions (CI externo), CI: workflow de testes (GitHub Actions), INVARIANTE: GUI só marca impresso após confirmação física, main(), separador_gui.py Telinha do Separador de Etiquetas do Mercado Livre. Mostra os g (+22 more)

### Community 1 - "Bot do Telegram"
Cohesion: 0.07
Nodes (66): _agendar_aviso(), _autorizado(), carregar_config(), cb_botao(), cmd_amanha(), cmd_conta(), cmd_desconhecido(), cmd_detalhar() (+58 more)

### Community 2 - "Camada de provedor (ML/Shopee/Ambas)"
Cohesion: 0.06
Nodes (17): INVARIANTE: modo Ambas usa o token da conta certa e grava no estado da conta certa, Modo 'Ambas' (funde grupos SKU+qtd entre contas ML), criar_provedor(), fundir_grupos(), Provedor, ProvedorML, ProvedorMLAmbas, ProvedorShopee (+9 more)

### Community 3 - "Testes da Shopee"
Cohesion: 0.05
Nodes (14): RuntimeError, _detalhes_exemplo(), _forca_individual(), _grupo(), Shopee (Fase 1): assinatura HMAC e mapeamento pedido -> grupo (sem rede)., Leva _organizar_varios direto ao caminho individual (sem AWB previo e sem     ba, test_grupos_filtra_por_dia_e_agrupa_por_sku_quantidade(), test_imprimir_grupo_organiza_gera_marca() (+6 more)

### Community 4 - "Fixtures de teste (conftest)"
Cohesion: 0.07
Nodes (24): make_grupo(), Configuracao comum dos testes., _d(), Estado de impressao por shipment_ids e limpeza por idade., Simula a tela e o bot juntos: um marca [5], o outro (que carregou o     estado A, test_carregar_estado_poda_e_persiste(), test_compatibilidade_formato_antigo_string(), test_envio_novo_reabre_como_parcial() (+16 more)

### Community 5 - "Mock HTTP dos testes"
Cohesion: 0.08
Nodes (16): FakeResp, Resposta HTTP falsa para simular requests.get sem rede., Camada HTTP: retry/backoff e download de etiquetas ZPL., Faz requests.get devolver as respostas em ordem; conta as chamadas., _sequencia(), test_baixar_zpl_aceita_zip(), test_baixar_zpl_sucesso_texto(), test_espera_retry_header_invalido_cai_no_backoff() (+8 more)

### Community 6 - "Núcleo: despacho, contas, busca"
Cohesion: 0.12
Nodes (21): INVARIANTE: bot não imprime Shopee (só consulta); e não imprime grupo antigo se conta/loja mudou, _criar_conta(), _Ctx, _grupo(), _patch_contas(), Testes das funcoes de impressao pelo bot do Telegram.  So a UI (botoes) e testad, test_coletar_grupos_ml_usa_nucleo(), test_coletar_grupos_shopee_usa_shopee_api() (+13 more)

### Community 7 - "Carimbo, dias úteis e editor de nomes"
Cohesion: 0.12
Nodes (26): agrupar(), aplicar_nomes(), buscar_detalhes(), buscar_pedidos(), carregar_cache(), Coleta, coletar_grupos(), _detalhe_item() (+18 more)

### Community 8 - "Modelo Grupo + identificação"
Cohesion: 0.14
Nodes (22): Estado 'já impresso' por marketplace + dia de despacho, INVARIANTE: envio novo em grupo já impresso reabre o grupo como parcial, INVARIANTE: estado de impresso é por marketplace + conta + dia de despacho, achar_grupo(), _chave_estado(), debug_envios(), detalhar(), envios_pendentes() (+14 more)

### Community 9 - "Testes de impressão do bot"
Cohesion: 0.13
Nodes (15): _grupo(), Carimbo do SKU na DANFE (area livre central), sem rede., test_carimbar_grupo_modo_nenhuma_nao_altera(), test_carimbar_grupo_modo_nome_usa_nome_e_fonte_menor(), test_carimbar_grupo_modo_sku_inalterado(), test_carimbar_grupo_nome_curto_usa_fonte_maior(), test_carimbo_nome_qtd_1_sem_linha_de_quantidade(), test_carimbo_nome_qtd_2_ganha_linha_2x() (+7 more)

### Community 10 - "Testes de carimbo (DANFE)"
Cohesion: 0.14
Nodes (21): _assinar(), _assinatura_publica(), _assinatura_shop(), baixar_documento(), criar_documento(), _download_shop(), _gerar_bloco(), _params_assinados() (+13 more)

### Community 11 - "Testes do modo Ambas"
Cohesion: 0.15
Nodes (16): core(), Modulo do nucleo com time.sleep neutralizado (testes de retry rapidos)., _g(), Modo "Ambas": fusao das contas ML num grupo por produto (dia de motorista unico), test_coletar_funde_e_soma_contagem(), test_fundir_grupos_junta_por_sku_e_quantidade(), test_fundir_nao_mistura_quantidades_diferentes(), test_imprimir_lotes_nada_pendente_nao_gera_zip() (+8 more)

### Community 12 - "Erros, credenciais e ZPL"
Cohesion: 0.11
Nodes (17): date, envios_cache.json (cache de envios finalizados · local · NÃO versionar), _amanha_br(), filtrar_para_imprimir(), _hoje_br(), _limpar_envios_cache(), _limpar_estado_antigo(), Data de hoje (YYYY-MM-DD) no horario de Brasilia, independente do     fuso/relog (+9 more)

### Community 13 - "Persistência JSON (backup atômico)"
Cohesion: 0.11
Nodes (20): CLAUDE.md (guia do projeto), Dia de despacho: próximos dias úteis + contagem por dia, Tela principal (screenshot da GUI), Página do repositório (GitHub Pages), Pasta Downloads (ponte de impressão, por máquina), Impressora térmica Zebra (hardware externo), App impressora_zebra_usb.py (externo, monitora Downloads), Fuso de Brasília sempre (+12 more)

### Community 14 - "Shopee API: assinatura HMAC"
Cohesion: 0.14
Nodes (20): Path, _caminho_backup(), carregar_credenciais(), _carregar_credenciais_com_backup(), _carregar_envios_cache(), carregar_estado(), _gerar_zip(), gerar_zip_etiquetas() (+12 more)

### Community 15 - "Testes de lotes/carimbo"
Cohesion: 0.12
Nodes (19): ÁREA DE RISCO: geração de lote × marcação de estado, nomes_sku.json (SKU→nome · VERSIONADO e sincronizado por Git), Nomes amigáveis (SKU→nome), editável na GUI, _carimbar_grupo(), carregar_nomes(), _fonte_nome(), gerar_zip_lotes(), preparar_lotes() (+11 more)

### Community 16 - "Shopee: geração de etiqueta"
Cohesion: 0.16
Nodes (15): buscar_detalhes(), coletar_grupos(), contagem_por_dia(), _data_envio(), _get_shop(), grupos_de_detalhes(), listar_order_sns(), parametros_envio() (+7 more)

### Community 17 - "Shopee: ship_order e rastreio"
Cohesion: 0.26
Nodes (11): _grupo(), _mocka_download(), Impressao em lote + divisoria + carimbo centralizado (sem rede)., test_gerar_zip_lotes_aborta_em_zpl_invalido(), test_gerar_zip_lotes_nao_marca_estado(), test_preparar_lotes_carimbo_carimba_danfe(), test_preparar_lotes_carimbo_nome_carimba_o_nome(), test_preparar_lotes_divisoria_insere_separador() (+3 more)

### Community 18 - "Datas BR + cache de envios"
Cohesion: 0.15
Nodes (14): CHANGELOG, INVARIANTE: reimpressão nunca altera o estado de impresso, marcar_impresso: last-writer-merge (tela+bot não se apagam), Retry com backoff (downloads e rede), baixar_zpl(), _modo_ident_efetivo(), Baixa as etiquetas ZPL via /shipment_labels (ate 50 envios por chamada).      Se, Reimprime TODAS as etiquetas do grupo, independente do estado.      Util quando (+6 more)

### Community 19 - "Relatórios de texto"
Cohesion: 0.19
Nodes (13): ÁREA DE RISCO: organização de envio e AWB na Shopee, Shopee Open Platform API (sistema externo), INVARIANTE: etiqueta Shopee só existe após organizar envio + obter AWB (tracking_number), _aguardar_awbs(), batch_ship_order(), imprimir_lotes(), _organizar_varios(), _rastreios_paralelo() (+5 more)

### Community 20 - "Token (renovação/retry)"
Cohesion: 0.21
Nodes (13): _avaliar_pedido(), buscar_envio(), buscar_pedidos_amplo(), _data_despacho(), _get(), _prazo_do_envio(), rastrear_sku(), Converte o expected_date da API para o dia (YYYY-MM-DD) no horario de     Brasil (+5 more)

### Community 21 - "Coleta de pedidos + nomes"
Cohesion: 0.17
Nodes (12): Organizar envio em lote por camadas (idempotência→batch→AWB→fallback), detectar_formato(), envio_ja_arranjado(), _montar_dropoff(), numero_rastreio(), organizar_envio(), get_tracking_number (GET): numero de rastreio/AWB do pedido. So existe depois, True se o envio ja foi organizado. info_needed traz as chaves dos metodos     (p (+4 more)

### Community 22 - "Shopee: organização em lote"
Cohesion: 0.18
Nodes (11): dividir_mensagem(), relatorio.py Monta textos legiveis (para o bot do Telegram) a partir dos dados d, Lista os grupos (SKU + quantidade) agrupados por quantidade do pedido., Quantos pacotes ha em cada dia de despacho., Mensagem do aviso automatico da manha: manchete com a contagem de hoje     segui, Composicao de um SKU: quais produtos/variacoes/voltagens o formam e     quantos, Divide um texto em blocos <= limite (o Telegram corta em ~4096), quebrando     p, texto_bom_dia() (+3 more)

### Community 23 - "Testes de multi-conta"
Cohesion: 0.22
Nodes (11): ÁREA DE RISCO: obtenção/renovação de token, ARQUITETURA (notas operacionais), Mercado Livre API (sistema externo), Telegram Bot API (sistema externo), credenciais.json (ML · segredo · por-conta · local · NÃO versionar), estado_grupos.json (ML · estado impresso · por-conta+dia · local · NÃO versionar), INVARIANTE: marcar_impresso recarrega do disco e mescla (não perde marcação concorrente), INVARIANTE: credenciais/estado/cache/config são locais e nunca versionados (+3 more)

### Community 24 - "Testes do pipeline de coleta"
Cohesion: 0.18
Nodes (11): config.json (preferências do app · local · NÃO versionar), aplicar_config(), carregar_config(), conta_ativa(), definir_conta(), migrar_conta_legado(), Preferencias do app (config.json). Vazio/ausente -> {}., Atualiza as globais de arquivo para apontar para contas/{nome}/. (+3 more)

### Community 25 - "Config e multi-conta (núcleo)"
Cohesion: 0.29
Nodes (3): EditorNomes, Janela para incluir/alterar/remover os nomes amigaveis (SKU -> nome)         sem, Janelinha de edicao do de-para SKU -> nome amigavel.

### Community 26 - "Shopee: detalhes/agrupamento"
Cohesion: 0.33
Nodes (10): _patch_pastas(), Suporte a multiplas contas: subpastas, migracao e selecao., test_aplicar_config_define_conta(), test_definir_conta_cria_pasta_e_atualiza_arquivos(), test_listar_contas_com_duas_contas(), test_listar_contas_ignora_pastas_sem_credenciais(), test_listar_contas_sem_pasta_retorna_vazio(), test_migrar_conta_legado_idempotente() (+2 more)

### Community 27 - "Shopee: documento em lote (batch)"
Cohesion: 0.36
Nodes (9): _prepara(), _prontos(), Pipeline coletar_grupos: filtro do dia e repasse de progresso., test_coletar_grupos_carimba_dia_de_despacho(), test_coletar_grupos_hoje_nao_carimba_dia(), test_coletar_grupos_por_dia_especifico(), test_coletar_grupos_repassa_progresso(), test_coletar_grupos_somente_hoje() (+1 more)

### Community 28 - "Shopee: token e rastreios"
Cohesion: 0.24
Nodes (10): credenciais_shopee.json (Shopee · segredo · por-loja · local · NÃO versionar), INVARIANTE: token sempre via obter_token (lock); nunca renovar_token direto (refresh rotaciona), obter_token(), preencher_rastreios(), Token valido do cache, ou renova. Serializa o refresh com um lock e     re-checa, Para grupos de UM unico pedido JA IMPRESSO, busca o AWB (get_tracking_number), renovar_token(), salvar_credenciais() (+2 more)

### Community 29 - "Testes de agrupamento"
Cohesion: 0.22
Nodes (10): imprimir_grupo(), marcar_impresso(), Grava a etiqueta na pasta Downloads e devolve (caminho, formato detectado)., Marca order_sns como impressos (ou todos do grupo). RECARREGA o estado do     di, Organiza (se preciso e organizar=True, em paralelo), gera/baixa a etiqueta     d, Regera a etiqueta de TODOS os envios do grupo, sem mexer no estado (util     qua, reimprimir_grupo(), _rotulo_lote() (+2 more)

### Community 30 - "Testes de datas"
Cohesion: 0.25
Nodes (9): estado_shopee.json (Shopee · estado impresso · por-dia · local · NÃO versionar), _combinar_etiquetas(), gerar_etiqueta(), _gerar_lote(), Gera (assincrono) e baixa as etiquetas dos pedidos. So baixa quando TODOS     os, Extrai o ZPL (em BYTES, sem reencodar — evita corromper o ~DG/Z64) de dentro, Junta o ZPL de varias etiquetas Shopee num UNICO .zip (um TXT) — para a     Zebr, Gera as etiquetas dos pedidos `alvo` num so ZIP, tolerando falha parcial.     Te (+1 more)

### Community 31 - "OAuth Shopee (setup)"
Cohesion: 0.28
Nodes (9): Response, _espera_retry(), Tempo de espera antes de re-tentar. Respeita o cabecalho Retry-After do     ML q, GET com retry em erros transitorios e em falhas de rede.      Re-tenta em respos, POST com retry em erros transitorios (408/429/5xx) e falhas de rede — mesma, renovar_token(), _requisicao_get(), _requisicao_post() (+1 more)

### Community 32 - "Testes de avaliação de pedido"
Cohesion: 0.43
Nodes (7): _item(), Agrupamento por envio: 1 envio = 1 etiqueta (inclui combos multi-SKU)., test_aplicar_nomes_em_combo(), test_combos_iguais_agrupam_juntos(), test_envio_combo_vira_um_grupo_com_uma_etiqueta(), test_envios_de_um_unico_sku_agrupam_por_sku_e_quantidade(), test_mesmo_sku_em_duas_linhas_soma_quantidade()

### Community 33 - "Testes de paginação de busca"
Cohesion: 0.43
Nodes (6): assinar(), extrair(), main(), perguntar(), pegar_token_shopee.py Programa de UMA VEZ SO. Autoriza sua loja na Shopee Open P, Aceita a URL inteira de retorno OU so o code. Devolve (code, shop_id).

### Community 35 - "Testes de identidade do produto"
Cohesion: 0.43
Nodes (6): _fake_get_paginado(), Busca de pedidos: paginacao paralela cobre todas as paginas., Simula orders/search: 50 por pagina, ids sequenciais, paging.total fixo., test_busca_todas_as_paginas(), test_respeita_max_pedidos(), test_uma_pagina_so()

### Community 36 - "Community 36"
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

### Community 42 - "Community 42"
Cohesion: 0.50
Nodes (4): imprimir_resumo(), Conta quantos envios prontos ha em cada dia de despacho, ordenado por     data., Mostra um panorama de quantos pacotes ha por dia de despacho., resumo_por_dia()

### Community 43 - "Community 43"
Cohesion: 0.50
Nodes (4): carregar_credenciais(), main(), parametros_documento(), Tipos de documento disponiveis para o pedido (para conferir o que da pra gerar).

## Knowledge Gaps
- **15 isolated node(s):** `session-start.sh script`, `separador-etiquetas-ml`, `setup_gui_tests.sh script`, `Página do repositório (GitHub Pages)`, `Dependência: pytest` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeparadorApp` connect `Interface gráfica (Tkinter)` to `Config e multi-conta (núcleo)`, `Persistência JSON (backup atômico)`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Why does `marcar_impresso()` connect `Modelo Grupo + identificação` to `Interface gráfica (Tkinter)`, `Carimbo, dias úteis e editor de nomes`, `Shopee API: assinatura HMAC`, `Testes de lotes/carimbo`, `Datas BR + cache de envios`, `Testes de multi-conta`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `INVARIANTE: GUI só marca impresso após confirmação física` connect `Interface gráfica (Tkinter)` to `Modelo Grupo + identificação`, `Shopee: ship_order e rastreio`, `Testes de multi-conta`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `SeparadorApp` (e.g. with `CI: smoke da GUI headless (xvfb) nos 2 marketplaces` and `Tela principal (screenshot da GUI)`) actually correct?**
  _`SeparadorApp` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `main()` (e.g. with `cb_botao()` and `cmd_amanha()`) actually correct?**
  _`main()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `session-start.sh script`, `bot_telegram.py Bot do Telegram para CONSULTAR e IMPRIMIR os pedidos de qualquer`, `Imprime os envios ainda pendentes do grupo (reusa o nucleo).      Roda em thread` to the rest of the system?**
  _202 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Interface gráfica (Tkinter)` be split into smaller, more focused modules?**
  _Cohesion score 0.05217391304347826 - nodes in this community are weakly interconnected._