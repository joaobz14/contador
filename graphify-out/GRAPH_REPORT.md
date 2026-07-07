# Graph Report - .  (2026-07-07)

## Corpus Check
- Corpus is ~37,267 words - fits in a single context window. You may not need a graph.

## Summary
- 789 nodes · 1391 edges · 47 communities (41 shown, 6 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 76 edges (avg confidence: 0.73)
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

## God Nodes (most connected - your core abstractions)
1. `SeparadorApp` - 44 edges
2. `Grupo` - 28 edges
3. `main()` - 19 edges
4. `main()` - 17 edges
5. `Provedor` - 17 edges
6. `ProvedorMLAmbas` - 16 edges
7. `make_grupo()` - 16 edges
8. `cb_botao()` - 15 edges
9. `FakeResp` - 15 edges
10. `_grupo()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Impressão: ZPL → .zip na Downloads (Zebra reconhece por prefixo)` --conceptually_related_to--> `baixar_zpl()`  [INFERRED]
  CLAUDE.md → separador_etiquetas_ml.py
- `UI: seções 'Para imprimir' e 'Já impressas — arquivadas'` --conceptually_related_to--> `envios_pendentes()`  [INFERRED]
  docs/img/tela.png → separador_etiquetas_ml.py
- `Dependência: requests (HTTP)` --conceptually_related_to--> `obter_token()`  [INFERRED]
  requirements.txt → shopee_api.py
- `Dependência: python-telegram-bot[job-queue]` --rationale_for--> `main()`  [EXTRACTED]
  requirements-bot.txt → bot_telegram.py
- `Fuso de Brasília sempre` --rationale_for--> `_hoje_br()`  [EXTRACTED]
  CLAUDE.md → separador_etiquetas_ml.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Camada de provedor (ML / Shopee / Ambas)** — provider_abstraction, provedores_provedor, provedores_provedormlambas, separador_gui_separadorapp [INFERRED 0.85]
- **Shopee Fase 2: organizar → AWB → etiqueta** — organizar_camadas, shopee_api_organizar_varios, shopee_api_batch_ship_order, shopee_api_gerar_etiqueta, shopee_api_numero_rastreio [INFERRED 0.85]
- **Token seguro (cache + lock, sem corrida de refresh)** — token_obter_lock, separador_etiquetas_ml_obter_token, shopee_api_obter_token, shopee_api_renovar_token [INFERRED 0.75]

## Communities (47 total, 6 thin omitted)

### Community 0 - "Interface gráfica (Tkinter)"
Cohesion: 0.06
Nodes (27): CI: smoke da GUI headless (xvfb) nos 2 marketplaces, CI: pytest em Python 3.11 e 3.12, CI: workflow de testes (GitHub Actions), main(), separador_gui.py Telinha do Separador de Etiquetas do Mercado Livre. Mostra os g, Reconstroi o seletor de dia de despacho.          Sem `contagem` (antes do 1º At, Reconstroi os radios de conta. So aparece no ML com 2+ contas., Mostra/esconde a Identificação conforme o provedor (Shopee não carimba). (+19 more)

### Community 1 - "Bot do Telegram"
Cohesion: 0.07
Nodes (65): _agendar_aviso(), _autorizado(), carregar_config(), cb_botao(), cmd_amanha(), cmd_conta(), cmd_desconhecido(), cmd_detalhar() (+57 more)

### Community 2 - "Camada de provedor (ML/Shopee/Ambas)"
Cohesion: 0.06
Nodes (16): Modo 'Ambas' (funde grupos SKU+qtd entre contas ML), criar_provedor(), fundir_grupos(), Provedor, ProvedorML, ProvedorMLAmbas, ProvedorShopee, provedores.py Abstrai o marketplace (Mercado Livre / Shopee) atras de uma interf (+8 more)

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
Cohesion: 0.08
Nodes (23): CLAUDE.md (guia do projeto), GUI confirma 'saiu certo?' antes de marcar impresso, Dia de despacho: próximos dias úteis + contagem por dia, Tela principal (screenshot da GUI), Página do repositório (GitHub Pages), Estado 'já impresso' por marketplace + dia de despacho, Fuso de Brasília sempre, Impressão: ZPL → .zip na Downloads (Zebra reconhece por prefixo) (+15 more)

### Community 7 - "Carimbo, dias úteis e editor de nomes"
Cohesion: 0.11
Nodes (28): achar_grupo(), _carimbar_grupo(), _chave_estado(), debug_envios(), detalhar(), envios_pendentes(), _fonte_nome(), gerar_zip_etiquetas() (+20 more)

### Community 8 - "Modelo Grupo + identificação"
Cohesion: 0.13
Nodes (20): _criar_conta(), _Ctx, _grupo(), _patch_contas(), Testes das funcoes de impressao pelo bot do Telegram.  So a UI (botoes) e testad, test_coletar_grupos_ml_usa_nucleo(), test_coletar_grupos_shopee_usa_shopee_api(), test_conta_mudou() (+12 more)

### Community 9 - "Testes de impressão do bot"
Cohesion: 0.12
Nodes (25): agrupar(), _avaliar_pedido(), buscar_detalhes(), buscar_envio(), carregar_cache(), _detalhe_item(), extrair_itens(), _get() (+17 more)

### Community 10 - "Testes de carimbo (DANFE)"
Cohesion: 0.13
Nodes (15): _grupo(), Carimbo do SKU na DANFE (area livre central), sem rede., test_carimbar_grupo_modo_nenhuma_nao_altera(), test_carimbar_grupo_modo_nome_usa_nome_e_fonte_menor(), test_carimbar_grupo_modo_sku_inalterado(), test_carimbar_grupo_nome_curto_usa_fonte_maior(), test_carimbo_nome_qtd_1_sem_linha_de_quantidade(), test_carimbo_nome_qtd_2_ganha_linha_2x() (+7 more)

### Community 11 - "Testes do modo Ambas"
Cohesion: 0.15
Nodes (16): core(), Modulo do nucleo com time.sleep neutralizado (testes de retry rapidos)., _g(), Modo "Ambas": fusao das contas ML num grupo por produto (dia de motorista unico), test_coletar_funde_e_soma_contagem(), test_fundir_grupos_junta_por_sku_e_quantidade(), test_fundir_nao_mistura_quantidades_diferentes(), test_imprimir_lotes_nada_pendente_nao_gera_zip() (+8 more)

### Community 12 - "Erros, credenciais e ZPL"
Cohesion: 0.12
Nodes (18): date, _amanha_br(), buscar_pedidos_amplo(), _data_despacho(), filtrar_para_imprimir(), _hoje_br(), _limpar_envios_cache(), _limpar_estado_antigo() (+10 more)

### Community 13 - "Persistência JSON (backup atômico)"
Cohesion: 0.13
Nodes (16): CHANGELOG, marcar_impresso: last-writer-merge (tela+bot não se apagam), Retry com backoff (downloads e rede), baixar_zpl(), carregar_credenciais(), preparar_lotes(), Etiqueta separadora (1 pagina ZPL) com SKU, nome e quantidade do lote,     centr, Baixa as etiquetas ZPL via /shipment_labels (ate 50 envios por chamada).      Se (+8 more)

### Community 14 - "Shopee API: assinatura HMAC"
Cohesion: 0.17
Nodes (16): Path, _caminho_backup(), _carregar_credenciais_com_backup(), _carregar_envios_cache(), carregar_estado(), _gravar_credenciais_com_backup(), _gravar_json(), _ler_json() (+8 more)

### Community 15 - "Testes de lotes/carimbo"
Cohesion: 0.19
Nodes (13): _assinar(), _assinatura_publica(), _assinatura_shop(), baixar_documento(), _download_shop(), marcar_impresso(), _params_assinados(), shopee_api.py Integracao com a Shopee Open Platform API v2 — FASE 1 (somente lei (+5 more)

### Community 16 - "Shopee: geração de etiqueta"
Cohesion: 0.26
Nodes (11): _grupo(), _mocka_download(), Impressao em lote + divisoria + carimbo centralizado (sem rede)., test_gerar_zip_lotes_aborta_em_zpl_invalido(), test_gerar_zip_lotes_nao_marca_estado(), test_preparar_lotes_carimbo_carimba_danfe(), test_preparar_lotes_carimbo_nome_carimba_o_nome(), test_preparar_lotes_divisoria_insere_separador() (+3 more)

### Community 17 - "Shopee: ship_order e rastreio"
Cohesion: 0.18
Nodes (14): detectar_formato(), envio_ja_arranjado(), gerar_etiqueta(), imprimir_grupo(), True se o envio ja foi organizado. info_needed traz as chaves dos metodos     (p, Gera (assincrono) e baixa as etiquetas dos pedidos. So baixa quando TODOS     os, Identifica o formato do arquivo baixado pelos primeiros bytes.      A etiqueta t, Grava a etiqueta na pasta Downloads e devolve (caminho, formato detectado). (+6 more)

### Community 18 - "Datas BR + cache de envios"
Cohesion: 0.15
Nodes (14): _get_shop(), listar_order_sns(), _montar_dropoff(), numero_rastreio(), organizar_envio(), parametros_envio(), GET assinado em uma API de loja, com a resiliencia de rede do core., Lista os order_sn em READY_TO_SHIP na janela de DIAS_JANELA dias. (+6 more)

### Community 19 - "Relatórios de texto"
Cohesion: 0.18
Nodes (11): dividir_mensagem(), relatorio.py Monta textos legiveis (para o bot do Telegram) a partir dos dados d, Lista os grupos (SKU + quantidade) agrupados por quantidade do pedido., Quantos pacotes ha em cada dia de despacho., Mensagem do aviso automatico da manha: manchete com a contagem de hoje     segui, Composicao de um SKU: quais produtos/variacoes/voltagens o formam e     quantos, Divide um texto em blocos <= limite (o Telegram corta em ~4096), quebrando     p, texto_bom_dia() (+3 more)

### Community 20 - "Token (renovação/retry)"
Cohesion: 0.20
Nodes (12): Response, _espera_retry(), obter_token(), Token valido do cache, ou renova. Serializa o refresh com um lock e     re-checa, Tempo de espera antes de re-tentar. Respeita o cabecalho Retry-After do     ML q, GET com retry em erros transitorios e em falhas de rede.      Re-tenta em respos, POST com retry em erros transitorios (408/429/5xx) e falhas de rede — mesma, renovar_token() (+4 more)

### Community 21 - "Coleta de pedidos + nomes"
Cohesion: 0.17
Nodes (12): aplicar_nomes(), buscar_pedidos(), carregar_nomes(), Coleta, coletar_grupos(), Le o de-para SKU -> nome do nomes_sku.json (vazio se nao existir)., Acrescenta o nome amigavel ao rotulo dos grupos cujo SKU esta no mapa.     Ex.:, Resultado do pipeline completo de uma atualizacao. (+4 more)

### Community 22 - "Shopee: organização em lote"
Cohesion: 0.24
Nodes (11): Organizar envio em lote por camadas (idempotência→batch→AWB→fallback), _aguardar_awbs(), batch_ship_order(), imprimir_lotes(), _organizar_varios(), _rastreios_paralelo(), Busca o AWB de varios pedidos EM PARALELO. Devolve {order_sn: awb} ('' em     fa, Organiza VARIOS envios num request so (ate LOTE_SHIP), como Postagem     (drop-o (+3 more)

### Community 23 - "Testes de multi-conta"
Cohesion: 0.33
Nodes (10): _patch_pastas(), Suporte a multiplas contas: subpastas, migracao e selecao., test_aplicar_config_define_conta(), test_definir_conta_cria_pasta_e_atualiza_arquivos(), test_listar_contas_com_duas_contas(), test_listar_contas_ignora_pastas_sem_credenciais(), test_listar_contas_sem_pasta_retorna_vazio(), test_migrar_conta_legado_idempotente() (+2 more)

### Community 24 - "Testes do pipeline de coleta"
Cohesion: 0.36
Nodes (9): _prepara(), _prontos(), Pipeline coletar_grupos: filtro do dia e repasse de progresso., test_coletar_grupos_carimba_dia_de_despacho(), test_coletar_grupos_hoje_nao_carimba_dia(), test_coletar_grupos_por_dia_especifico(), test_coletar_grupos_repassa_progresso(), test_coletar_grupos_somente_hoje() (+1 more)

### Community 25 - "Config e multi-conta (núcleo)"
Cohesion: 0.20
Nodes (10): aplicar_config(), carregar_config(), conta_ativa(), definir_conta(), migrar_conta_legado(), Preferencias do app (config.json). Vazio/ausente -> {}., Atualiza as globais de arquivo para apontar para contas/{nome}/., Move arquivos da raiz para contas/{nome}/ se necessario (uma unica vez). (+2 more)

### Community 26 - "Shopee: detalhes/agrupamento"
Cohesion: 0.28
Nodes (9): buscar_detalhes(), coletar_grupos(), contagem_por_dia(), _data_envio(), grupos_de_detalhes(), Detalhes dos pedidos (item_list, ship_by_date) em lotes de 50., ship_by_date (epoch em segundos) -> dia YYYY-MM-DD no horario de Brasilia., Converte os detalhes em ItemPedido, filtra pelo dia de envio e agrupa     por SK (+1 more)

### Community 27 - "Shopee: documento em lote (batch)"
Cohesion: 0.25
Nodes (9): criar_documento(), _gerar_bloco(), _post_shop(), POST assinado em uma API de loja (sign na query, dados no corpo JSON).     Passa, Cria o documento da etiqueta. A Shopee exige o tracking_number (AWB) de cada, Extrai {order_sn: status} do retorno do get_shipping_document_result., Cria/espera(READY)/baixa UM bloco de pedidos (<= TAMANHO_LOTE). So baixa com, resultado_documento() (+1 more)

### Community 28 - "Shopee: token e rastreios"
Cohesion: 0.29
Nodes (8): obter_token(), preencher_rastreios(), Token valido do cache, ou renova. Serializa o refresh com um lock e     re-checa, Para grupos de UM unico pedido JA IMPRESSO, busca o AWB (get_tracking_number), renovar_token(), salvar_credenciais(), _token_valido(), Token sempre via obter_token (cache + lock); nunca renovar_token direto

### Community 29 - "Testes de agrupamento"
Cohesion: 0.43
Nodes (7): _item(), Agrupamento por envio: 1 envio = 1 etiqueta (inclui combos multi-SKU)., test_aplicar_nomes_em_combo(), test_combos_iguais_agrupam_juntos(), test_envio_combo_vira_um_grupo_com_uma_etiqueta(), test_envios_de_um_unico_sku_agrupam_por_sku_e_quantidade(), test_mesmo_sku_em_duas_linhas_soma_quantidade()

### Community 30 - "Testes de datas"
Cohesion: 0.25
Nodes (4): Datas no horario de Brasilia (filtro de despacho)., test_proximos_dias_uteis_comeca_no_proximo_util_no_sabado(), test_proximos_dias_uteis_dia_comum(), test_proximos_dias_uteis_numa_sexta_pula_o_fim_de_semana()

### Community 31 - "OAuth Shopee (setup)"
Cohesion: 0.43
Nodes (6): assinar(), extrair(), main(), perguntar(), pegar_token_shopee.py Programa de UMA VEZ SO. Autoriza sua loja na Shopee Open P, Aceita a URL inteira de retorno OU so o code. Devolve (code, shop_id).

### Community 33 - "Testes de paginação de busca"
Cohesion: 0.43
Nodes (6): _fake_get_paginado(), Busca de pedidos: paginacao paralela cobre todas as paginas., Simula orders/search: 50 por pagina, ids sequenciais, paging.total fixo., test_busca_todas_as_paginas(), test_respeita_max_pedidos(), test_uma_pagina_so()

### Community 34 - "Testes de cache de envios"
Cohesion: 0.52
Nodes (6): _envio(), _hoje(), Cache de envios finalizados: pula os terminais e nao deixa de ver os prontos., test_filtrar_nao_cacheia_ready_to_print(), test_filtrar_pula_cacheados_e_cacheia_terminais(), test_limpar_envios_cache_remove_antigos()

### Community 36 - "Community 36"
Cohesion: 0.33
Nodes (3): Dependência: python-telegram-bot[job-queue], Dependência: pytest, Dependência: requests (HTTP)

### Community 37 - "Community 37"
Cohesion: 0.47
Nodes (5): extrair_code(), main(), perguntar(), pegar_token.py Programa de UMA VEZ SO. Pega a autorizacao do Mercado Livre e sal, Aceita a URL inteira colada OU so o codigo.

### Community 38 - "Community 38"
Cohesion: 0.33
Nodes (6): _combinar_etiquetas(), _gerar_lote(), Extrai o ZPL (em BYTES, sem reencodar — evita corromper o ~DG/Z64) de dentro, Junta o ZPL de varias etiquetas Shopee num UNICO .zip (um TXT) — para a     Zebr, Gera as etiquetas dos pedidos `alvo` num so ZIP, tolerando falha parcial.     Te, _zpl_do_zip()

### Community 40 - "Community 40"
Cohesion: 0.40
Nodes (3): _pronto(), Resumo por dia de despacho (contagem de pacotes por dia)., test_resumo_conta_e_ordena_por_dia()

### Community 41 - "Community 41"
Cohesion: 0.50
Nodes (4): _gerar_zip(), gerar_zip_lotes(), Monta um ZIP no formato que o impressora_zebra_usb.py reconhece:       - nome do, Gera UM ZIP com todos os lotes selecionados (com divisoria/carimbo conforme

### Community 42 - "Community 42"
Cohesion: 0.50
Nodes (4): imprimir_resumo(), Conta quantos envios prontos ha em cada dia de despacho, ordenado por     data., Mostra um panorama de quantos pacotes ha por dia de despacho., resumo_por_dia()

### Community 43 - "Community 43"
Cohesion: 0.50
Nodes (4): carregar_credenciais(), main(), parametros_documento(), Tipos de documento disponiveis para o pedido (para conferir o que da pra gerar).

## Knowledge Gaps
- **6 isolated node(s):** `session-start.sh script`, `separador-etiquetas-ml`, `setup_gui_tests.sh script`, `Página do repositório (GitHub Pages)`, `CI: pytest em Python 3.11 e 3.12` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeparadorApp` connect `Interface gráfica (Tkinter)` to `Núcleo: despacho, contas, busca`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Why does `Provedor` connect `Camada de provedor (ML/Shopee/Ambas)` to `Núcleo: despacho, contas, busca`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `SeparadorApp` (e.g. with `CI: smoke da GUI headless (xvfb) nos 2 marketplaces` and `Tela principal (screenshot da GUI)`) actually correct?**
  _`SeparadorApp` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `main()` (e.g. with `cb_botao()` and `cmd_amanha()`) actually correct?**
  _`main()` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `session-start.sh script`, `bot_telegram.py Bot do Telegram para CONSULTAR e IMPRIMIR os pedidos de qualquer`, `Imprime os envios ainda pendentes do grupo (reusa o nucleo).      Roda em thread` to the rest of the system?**
  _191 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Interface gráfica (Tkinter)` be split into smaller, more focused modules?**
  _Cohesion score 0.055178652193577565 - nodes in this community are weakly interconnected._
- **Should `Bot do Telegram` be split into smaller, more focused modules?**
  _Cohesion score 0.07365967365967366 - nodes in this community are weakly interconnected._