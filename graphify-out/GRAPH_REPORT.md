# Graph Report - .

## Estado de sincronização (leia primeiro)

O grafo tem **duas camadas** com origens diferentes — não confunda as datas:

| Camada | O que é | Origem / data | Contagem |
|---|---|---|---|
| **AST + estrutura** | nós de arquivos/classes/funções/métodos + `contains`/`method`/`imports`/`calls` | **último build completo do CLI:** commit `5233aef` (2026-07-08). **Re-sincronizada** com o código por `tools/graph_sync.py` no commit `f1dd2d0` (2026-07-22). | reflete o código atual |
| **Semântica** | `rationale`/`concept`/`document` + `rationale_for`/`conceptually_related_to`/`shares_data_with` | mantida **à mão**, contínua (ver "Atualizações manuais" abaixo). Espelhada em `graphify-out/semantic.json`. | preservada 100% |

- **`built_at_commit` do `graph.json`** = HEAD analisado nesta sincronização.
- **Contagens atuais do `graph.json` (pós-sync, autoritativas):**
  **1848 nodes · 3532 edges · 10 hyperedges** — inclui a remoção do auto-start
  do bot pela tela (2 achados reais de mesma causa-raiz) e a troca pro
  Agendador de Tarefas do Windows (`atalhos/registrar-tarefa-bot.ps1`), o CLI
  de teste do alerta pós-horário (`bot_telegram.py testar-alerta`), o
  formato enxuto + resumo agregado do alerta (`/vendasapos`), o alerta
  pós-horário estendido pra Shopee, a correção de compliance do
  `v2.logistics.ship_order` em 2 rodadas (`_filtrar_ja_arranjados` +
  correção do fallback individual pós-batch, após respostas do suporte da
  Shopee) e as 3 correções da auditoria de APIs (amarra credencial→arquivo,
  dieta do alerta, higiene), a reorganização da raiz em `dados/` + `logs/` e a
  correção do incidente em que as contas ML sumiam da tela (isolamento de falha
  por item na migração + `contas/` na frente da fila).
  Ver "Atualizações manuais" abaixo pro histórico completo.
- O **Summary** mais abaixo (844 nodes · 1498 edges · comunidades · God Nodes ·
  centralidade) é do **build do CLI de 2026-07-08** e **só um rebuild completo do
  CLI o re-deriva** — comunidades/centralidade/"perguntas sugeridas" não são
  recalculadas pelo sincronizador.
- **`graph.html` está DEFASADO** (visualização *baked* do build de 2026-07-08, embute
  os dados antigos; não lê o `graph.json`). **Pendência conhecida:** só um
  `graphify` CLI o regenera com segurança — não editar o HTML gigante à mão.

### Como validar e re-sincronizar (reprodutível, sem o CLI)

```bash
python tools/graph_sync.py --check      # detecta defasagem (exit!=0 se houver)
python tools/graph_sync.py --update     # re-deriva AST, preserva semântica, grava atômico
python tools/graph_sync.py --validate   # valida integridade do graph.json atual
pytest tests/test_graphify_sync.py -q   # guarda no CI (defasagem + camada semântica)
```

**NUNCA** rodar `graphify hook install` (reconstruiria só o AST e apagaria a camada
semântica). Ver `tools/graph_sync.py` para o modelo das duas camadas.

## Atualizações manuais (pós-build)

> Enriquecimentos da camada de docs feitos à mão (o CLI `graphify` não roda neste
> ambiente e reconstruiria só o AST, apagando esta camada). O `graph.json` é a
> fonte consultável; os números do **Summary** abaixo refletem o build automático de
> 2026-07-08 (ver "Estado de sincronização" no topo para as contagens atuais).

- **2026-08-06 (2h depois) — corrigido: campo ausente na Shopee NÃO é "não sei", é a resposta.**
  Eu havia removido o fallback de data (certo) e, por analogia com o `_sla` do ML, passado a
  **incluir** a venda sem `ship_by_date` no lote de hoje. **Errado.** O painel da Shopee, numa venda
  sem prazo, escreve: *"A emissão de etiqueta estará disponível a partir de 07/08 13:07. O prazo de
  envio começará a contar APENAS APÓS essa data"* — campo ausente é **estado declarado**, não
  ignorância. No ML a data ausente é o ML não ter respondido; aqui é a Shopee dizendo "ainda não
  liberei". O custo não foi teórico: em menos de duas horas o dono recebeu *"Ainda sem NF-e"* de uma
  venda criada às 13:04 que a Shopee só libera no dia seguinte — e a **carência de 30 min não
  alcança** esse caso (o "Em processamento" dura ~24h), ao contrário do que eu previra ao propor a
  mudança. Alarme diário garantido. Revertido para `== hoje`; o `AVISO_SEM_PRAZO` criado junto foi
  **removido** em vez de virar código morto. O fallback continua fora — essa parte estava certa.
  Entrou também a chave **`alerta_shopee`** para desligar só o alerta da Shopee (nó
  `alerta_shopee_desligavel`). **Método:** antes de tratar campo ausente como "não sei", pergunte se
  a API não está **dizendo** algo com a ausência — e desconfie de previsão de ruído feita por quem
  propôs a mudança.
  Depois do `--update`: **1848 nós, 3532 arestas, 0 órfãs**.
- **2026-08-06 — varredura de segurança do repositório PÚBLICO: fica público, e a CI perde
  a permissão de escrita.** 428 commits varridos: nenhum segredo real jamais entrou (as 4
  ocorrências são fixtures declaradamente falsos), o `.gitignore` cobre os 19 caminhos sensíveis
  testados um a um, e não há dado pessoal de comprador nos 198 arquivos rastreados — apesar de a
  etiqueta carregar nome, endereço e CEP. Dois pontos da CI ficaram registrados: o gatilho é
  `pull_request` e **nunca** `pull_request_target`, e o workflow passou a declarar
  `permissions: contents: read` (nenhum job escreve; sem o bloco o `GITHUB_TOKEN` herda o padrão
  do repositório, que pode incluir escrita). E a amarra que impede privar sem preparo:
  `docs/index.html` é a **Redirect URL do OAuth** cadastrada no painel da Shopee e servida pelo
  Pages — no plano gratuito, privar derruba a página e quebra o caminho de refazer o OAuth,
  que é exatamente o que se precisa quando o refresh token morre. Nó `repositorio_publico_varredura`.
  Depois do `--update`: **1844 nós, 3516 arestas, 0 órfãs**.
- **2026-08-06 — `/atualizar` passa a reiniciar por DEFASAGEM, não por "o pull trouxe algo".**
  O comando decidia o reinício pelo resultado do `git pull`: pull vazio ⇒ *"nada a fazer"*, sem
  reiniciar. Mas pull vazio **não** significa processo em dia — quem resolveu a árvore suja com um
  `git pull` na mão (ou rodou o `Atualizar programa.bat`) já trocou os arquivos, e o bot no ar segue
  com o que carregou no logon. O dono lia "já está atualizado" e ficava **convencido de que
  atualizou**, rodando o código antigo: o comando reportava sucesso sem entregar o efeito. Pegou-o
  duas vezes. Agora quem decide é `_desatualizado()` — ponto único usado por `/versao` e
  `/atualizar` —, comparando a pasta com `COMMIT_EM_USO`. Na dúvida (commit desconhecido de um dos
  lados) devolve **False**: "não sei" nunca vira ação, porque reinício em falso derruba o bot por
  15s à toa (regra do `_mtime_log_monitor`). A árvore suja continua bloqueando o pull, mas agora
  **avisa** quando o processo também está atrasado — dizer só "não atualizei" escondia metade do
  problema. Nó `atualizar_reinicia_por_defasagem`.
  Depois do `--update`: **1843 nós, 3514 arestas, 0 órfãs**.
- **2026-08-06 — `dia_previsto` da Shopee: fallback removido por MEDIÇÃO, e data incerta
  passa a INCLUIR.** O pedido real `260805JCWTKH9K` (pago 05/08 09:40, `days_to_ship` 2,
  `ship_by_date` **06/08**) contradiz a fórmula `pay_time + days_to_ship`, que daria 07/08 —
  e a docstring dizia tê-la "conferido contra um pedido real". Dois pedidos reais discordam:
  **não existe fórmula confirmada**, e trocar por `days_to_ship - 1` seria repetir o erro com
  outra amostra. O que condenou o fallback foi a **direção** do erro: ele existia para que uma
  venda sem prazo não ficasse fora do filtro por dia e, empurrando-a para a frente, produzia
  **exatamente o silêncio que devia evitar** — a venda que vencia HOJE saía do filtro de hoje.
  Hoje `dia_previsto` devolve `""` para "não sei" e `pedidos_prontos_novos` **inclui** o
  incerto (regra do `_sla` no ML: excluir em silêncio é pior que datar errado); o alerta marca
  o lote com `AVISO_SEM_PRAZO` para o dono não estranhar uma venda que talvez seja de amanhã.
  A carência de 30 min é o que torna isso barato: a venda recém-criada, justamente a que vem
  sem prazo, já é segurada por ela. Nó `data_incerta_shopee`.
  Depois do `--update`: **1837 nós, 3497 arestas, 0 órfãs**.
- **2026-08-06 — o "1º ciclo do dia é calado" virou marca POR FONTE, e só após sucesso.**
  Achado a partir de **evidência de campo**: o dono recebeu às 09:42 um aviso de venda Shopee
  parada há 24h01 — mensagem que, pelo desenho, o primeiro ciclo do dia (08:30) deveria ter
  calado. A divergência entre o observado e o código expôs o furo: `iniciado` era um **booleano
  ligado no fim do ciclo**, inclusive quando a checagem de uma fonte tinha **falhado**. A fonte
  que falhou não registrou nada, então no ciclo seguinte todas as vendas dela apareciam como
  "novas" e saíam de uma vez — uma falha de rede transformava a garantia de *"nada de despejo"*
  exatamente no despejo que ela existe para evitar (a família *"falha que reporta sucesso"*, aqui
  na forma de **falha que marca progresso**). Hoje é a **lista** de fontes que completaram a
  rodada, gravada só depois do sucesso. **Por fonte e não global**, senão a Shopee fora do ar
  calaria os alertas do ML o dia inteiro. Nó `primeiro_ciclo_por_fonte` (4 `rationale_for` +
  2 `conceptually_related_to`).
  Depois do `--update`: **1831 nós, 3482 arestas, 0 órfãs**.
- **2026-08-06 — etiqueta em branco no meio do lote: este app não sabe criar
  uma.** Reclamação recorrente do dono ("às vezes pula uma etiqueta"), trazida
  com foto. Investigado lendo os **dois** repos, e o que se descartou foi
  descartado **com leitura de código**: o núcleo daqui nunca cria página (só
  insere um `^FO…^FS` dentro do bloco da DANFE que já existe; **zero** ocorrências
  de `^LL`/`^PQ`/`^MN`/`^LH` no repositório), e o app da Zebra **descarta** bloco
  vazio antes de imprimir. Sobram três causas — o **auto-feed de início de
  sessão** do app da Zebra (`^XA^XZ` proposital, reaparece a cada "Iniciar"),
  `^MN`/`^LL` divergindo entre os blocos do ML, e calibração da mídia — e elas se
  separam por evidência: `tools/diag_zpl.py` (novo) lê o lote já impresso e o log
  da Zebra mostra o auto-feed. Registrada também a **armadilha de leitura da
  foto**: a ordem do ML é ENVIO → DANFE e a impressora empurra o papel para fora,
  então o mais perto da impressora foi impresso por **último** — ler a tira ao
  contrário troca uma causa pela outra. Nó `etiqueta_em_branco_no_lote`
  (3 `rationale_for` + 3 `conceptually_related_to`). Primeiro uso real da pasta de
  retenção `~/zebra_usb_concluidos/` contratada em 2026-08: ela foi negociada para
  reimpressão, e serviu para **investigar depois do fato**.
  **Primeiro uso real (mesmo dia) achou outra coisa e ensinou a lição maior:** rodado no lote do dono,
  o diagnóstico escreveu **"OK"** — e o mesmo arquivo tinha **19 etiquetas de envio para 18 DANFEs**
  (uma venda sairia **sem nota fiscal**). Ele calou porque só procurava a página em branco que motivou
  sua criação: é a família *"falha que reporta sucesso"* aplicada a um **diagnóstico** — o OK não é
  neutro, manda procurar no lugar errado. Regra registrada: **ferramenta de diagnóstico responde sobre
  o arquivo inteiro, não só sobre a pergunta que a motivou.**
  Depois do `--update`: **1824 nós, 3459 arestas, 0 órfãs** (antes deste lote).
- **2026-08-05 — compliance da Shopee encerrado (resposta final do suporte).**
  O requisito (success rate > 90% por 7 dias consecutivos em
  `v2.logistics.ship_order`, com prazo e risco de penalidade) foi o que motivou
  as duas rodadas de correção de 2026-07. O e-mail final: *"se houver dias **sem
  chamada**, quebra o ciclo. Isso já está em melhoria interna e **não há
  penalização ativa no momento**."* **Sem prazo e sem risco** — as correções
  ficam porque estão certas, não porque são exigidas. E a frase sobre "dias sem
  chamada" revela o resto: a sequência de 7 dias é **inalcançável nesta operação
  por construção, e não por falha** — o app manda tudo pelo `batch_ship_order`
  (que não conta para a métrica) e o individual **pula** o `ship_order` quando o
  envio já está arranjado; o singular só é chamado quando o lote está
  indisponível por inteiro. Sem chamadas, não há o que medir. **Armadilha a
  evitar:** forçar chamadas para manter o ciclo se autodestrói — seria preciso
  chamar o singular em pedido **já organizado**, que produz exatamente
  `package_already_shipped`, o erro que a métrica penaliza. Novo nó
  `compliance_shopee_encerrado`. **Método:** a métrica media um endpoint que
  este app deliberadamente quase não usa — vale conferir **se** o comportamento
  medido existe antes de otimizar para a medida.
  Depois do `--update`: **1799 nós, 3425 arestas, 0 órfãs**.
- **2026-08-05 — webhook do n8n autenticado por `Authorization: Bearer`.**
  Proposto pelo lado n8n, negociado nos dois. Os webhooks eram endpoints sem
  autenticação — vazamento de **dado** já estava fechado (o `chat_id` passa por
  allowlist lá, a resposta sempre vai ao dono), mas sobrava **abuso por
  repetição**: cota do ML (16 chamadas por `/anuncios`), flood e ruído. Três
  decisões: **um** segredo para os dois fluxos (se o config vazar, as duas URLs
  vazam juntas); **`Authorization`** e não cabeçalho próprio, porque o
  `sem_segredos` **já** redige `Bearer <token>` — verificado contra segredos
  reais de `token_urlsafe(32)`, que caem inteiros na regex; e **segredo ausente
  = não manda cabeçalho**, o que viabiliza a implantação em 4 passos sem janela
  (código inerte → dono configura e reinicia → n8n **confirma** o cabeçalho
  chegando → só então exige). O passo do reinício era o furo do plano original,
  que o tratava como automático. **Nota de método:** o argumento inicial deste
  lado contra a alternativa `onlyRunIf` (que ela criaria execução e gastaria
  cota) estava **errado**, e o lado n8n corrigiu com a doc do nó. O motivo real
  é melhor: ela **falha aberto** — erro na avaliação **libera** a requisição.
  Controle de acesso que autoriza quando quebra não é controle de acesso, e é a
  mesma família dos outros achados do dia (o `gui-smoke` verde com a tela
  quebrada, o reinício anunciando sucesso sem subir nada): o defeito nunca é
  falhar, é **passar** quando deveria barrar. Novo nó `webhook_n8n_autenticado`.
  Depois do `--update`: **1798 nós, 3422 arestas, 0 órfãs**.
- **2026-08-05 — carência do aviso "sem NF-e": o sinal é o TEMPO, não o
  estado.** Relato do dono, com print: o alerta avisava "sem NF-e" e minutos
  depois se desmentia com o ✅. Causa: o ERP dele (UpSeller) consulta as APIs,
  puxa a venda, confere o **estoque interno** e só então sobe o XML — então
  **toda** venda nova passa alguns minutos sem nota, e o alerta disparava dentro
  dessa janela normal. O aviso não existe para dizer "está sem NF-e"; existe
  para dizer **"está sem NF-e há tempo demais para ser processamento normal"**,
  que no fluxo dele significa **falta de estoque**. Este era o discriminador que
  **faltava**: já se sabia que `invoice_data.status=pending` é ambíguo (por isso
  o texto nunca afirmou a causa) — o que não se tinha era como separar os casos.
  O tempo separa, e de quebra mata o falso positivo do "Em processamento" da
  Shopee: **um mecanismo, dois ruídos**. Três decisões: o relógio conta do
  carimbo da **venda** (não de quando o bot olhou); quem está **na carência não
  é registrado** no dedup (senão ficaria calado para sempre); e **sem carimbo,
  avisa** (nunca calar com prova na mão). O corte fica no **bot**, não no núcleo.
  A mensagem leva **há quanto tempo** — uma parada há 40 min é estoque, várias de
  uma vez é o faturador fora do ar; entrega o dado e não conclui. Novo nó
  `carencia_do_aviso_sem_nf`.
  Depois do `--update`: **1789 nós, 3404 arestas, 0 órfãs**.
- **2026-08-05 — Entrega Instantânea da Shopee não se aplica (decisão do
  dono).** A Shopee anunciou por e-mail que espera adoção crescente da Instant
  Delivery (mercados incluindo BR) e pede suporte de apps de fulfillment.
  Modelo: pedido processado **individualmente**, em minutos, rider despachado
  logo após a compra — oposto do app inteiro, feito para lote por dia de
  despacho. O catálogo (fritadeiras industriais, engenho de 3 moendas) já
  sugeria baixa relevância, mas o que **decide** é outro: Instant Delivery
  depende de um rider que **busca na porta do vendedor**; o dono **leva os
  pacotes num ponto de coleta** (drop-off, a mesma opção que `organizar_envio`
  já usa sempre) — duas logísticas incompatíveis por definição, não uma opção
  que se liga. Confirmado pelo dono, não suposição. Ficou um diagnóstico
  (`python shopee_api.py canais`) para o dia em que o **modelo de envio** mudar,
  mas a resposta de hoje já é conhecida por fora da API. Novo nó
  `entrega_instantanea_nao_se_aplica`. **Método:** é o mesmo tratamento dado ao
  TikTok Shop e à Amazon SP-API — registrar a decisão evita que uma sessão
  futura reabra a investigação ao ver o mesmo tipo de e-mail de novo.
  Depois do `--update`: **1775 nós, 3375 arestas, 0 órfãs**.
- **2026-08-05 — "tenho que abrir o Reiniciar Bot.bat 2x".** Relato do dono. O
  bot roda numa árvore `powershell`(tarefa) → `cmd.exe`(laço) → `python.exe`. O
  script matava o `cmd.exe` e o `python`, mas o `powershell` da tarefa só termina
  **depois** que o `Start-Process -Wait` dele percebe que o `.bat` morreu — e até
  lá a tarefa continua "Em execução", estado em que o Agendador **recusa**
  `schtasks /run`. Dois defeitos somados: a espera olhava só os processos
  **python** (já mortos, então saía na hora) e o **código de saída do `/run` era
  descartado**, com a mensagem verde saindo de qualquer jeito. Por isso o sintoma
  não era erro e sim "abre de novo que aí vai". Hoje espera o lançador sair e a
  tarefa liberar, confere o `$LASTEXITCODE` e — acima de tudo — **verifica que um
  bot apareceu** antes de anunciar sucesso, com fallback para o `.bat` direto.
  Guardião de **texto** (PowerShell não roda na CI): não prova que funciona, só
  impede que as três defesas sumam sem ninguém notar. Novo nó
  `reiniciar_bot_duas_vezes`. **Mesma família** do `gui-smoke` e do `bot_config`
  inválido: o defeito não era falhar, era **reportar sucesso sem ter verificado**.
  Depois do `--update`: **1774 nós, 3374 arestas, 0 órfãs**.
- **2026-08-05 — alerta pós-horário: uma mensagem por ciclo, janela às 8:30 e 1º
  ciclo calado.** Veio de um print do próprio dono. O envio era **por origem e
  por tipo**: com 2 contas ML + Shopee, cada uma podendo ter "pronta" e "falta
  NF-e", o pior caso eram **6 mensagens a cada 5 minutos**. Três correções:
  **(1)** as origens viram **seções** de um texto só — mas o **dedup e a
  persistência continuam por origem**, só o envio virou um; juntar os baldes
  faria o `shipment_id` já avisado como "falta NF-e" calar o aviso de quando a
  venda ficasse pronta. **(2)** a janela começa às **8:30** (era 7h): das 7h às
  8:30 o dono está no Atualizar e já leu o aviso das 08:00 — o alerta repetia o
  que ele acabara de ver. **(3)** o **primeiro ciclo do dia não envia**, só
  registra: sem isso, subir a janela trocaria a parede de mensagens por um
  **despejo único** com o dia inteiro, o oposto de "apareceu agora". Venda antes
  travada por NF-e que ficou pronta vem marcada com **✅**. Novo nó
  `alerta_uma_mensagem_por_ciclo`. **Lição:** ruído em canal de alerta não é
  cosmético — ensina o dono a ignorar o canal, e aí ele perde a utilidade no dia
  em que a mensagem importar (mesma lógica do falso alarme do monitor da Zebra).
  Depois do `--update`: **1772 nós, 3370 arestas, 0 órfãs**.
- **2026-08-05 — `api-monitor` desativado (pausa, não desistência).** Duas
  razões, e a segunda é a que decide. **(1) Não funcionava:** ML Novidades exige
  login e não tem equivalente público; as fontes da Shopee são SPAs que nem
  sempre renderizavam. O relatório saía "bloqueada" toda semana — rotina que
  nunca responde não monitora — e ainda custava uma chamada paga de IA por
  semana. **(2) Risco:** rodava `claude -p --permission-mode bypassPermissions`,
  **sem supervisão**, com `cwd` na raiz do projeto (a pasta das credenciais do
  ML, da Shopee e do bot), tendo **conteúdo baixado da web como entrada**.
  Probabilidade baixa, raio de alcance igual às credenciais do negócio. Os dois
  `.ps1` saem no começo com aviso e o código ficou inteiro — reativar é apagar o
  bloco. O `registrar-tarefa.ps1` foi travado **de propósito**: sem isso,
  reativar seria um duplo-clique distraído num script esquecido, e não uma
  decisão. A flag virou `--allowedTools` **antes** de arquivar, para que uma
  reativação futura não reinstale o risco por descuido. Novo nó
  `api_monitor_desativado`. **Lição:** agente automático sem supervisão herda o
  alcance da pasta em que roda; quando a entrada dele é conteúdo de terceiros,
  restringir ferramenta é o mínimo — e desligar o que não entrega valor é sempre
  mais barato que proteger.
  Depois do `--update`: **1759 nós, 3327 arestas, 0 órfãs**.
- **2026-08-05 — a tela que não abre sem deixar rastro, e o guardião que não
  guardava.** Auditoria feita por um critério novo: procurar por
  **invisibilidade** (onde uma falha não apareceria para ninguém), não por
  complexidade — o que o incidente do `bot_config.json` ensinou. Dois achados,
  mesma causa: o Tk **captura** exceção de callback (`after`/clique/`trace`),
  imprime no stderr e segue — e nem sob `pythonw` (como o atalho sobe a tela)
  nem no job da CI existe alguém lendo esse stderr. **(1) Na tela:** `main()`
  eram quatro linhas sem `try/except` e sem log; falha ao montar fazia o
  duplo-clique não produzir **nada**. Idêntico ao incidente do bot, no app que
  abre toda manhã. **(2) Na CI:** o `gui-smoke` pegava só erro de **construção**
  — erro em callback deixava o `gui_screenshot.py` tirar o screenshot e sair com
  0, job **verde** com a tela quebrada (reproduzido antes de corrigir). Hoje o
  script instala `report_callback_exception` e reprova, **com o screenshot
  tirado antes** (a imagem é a primeira pista e sumiria se ele morresse antes),
  e a CI ganhou um passo `--autoteste` que exige que ele reprove: guardião sem
  prova de que reprova não é guardião, e descobrir que ele parou de guardar não
  pode depender de um bug chegar na produção. Novo nó
  `falha_silenciosa_na_abertura_da_tela`.
  Depois do `--update`: **1758 nós, 3324 arestas, 0 órfãs**.
- **2026-08-05 — coletor do Ads: "não sei" e isolamento por conta.** Três
  defeitos da mesma família, todos já conhecidos do projeto e nunca aplicados
  nesta pasta. (1) `coletar_conta` **prometia no docstring** um isolamento que
  não entregava: o `try/except` cobria só a autenticação, e um `sqlite3.Error`
  na 1ª conta derrubava o run antes de a 2ª ser tentada — mesma causa-raiz do
  `migrar_para_pastas` (2026-07-29). (2) `buscar_campanhas_do_dia` devolvia
  `[]` no erro, então o dia era dado por coletado com `campanhas: 0` e o run
  **anunciava sucesso** com código de saída 0, deixando um buraco que nunca era
  preenchido (o coletor só busca "ontem"). **Calibração do dano:** nenhuma linha
  era gravada, então não havia "dia zerado" distorcendo médias — `AVG()` ignora
  linha ausente; o efeito no `recomendar.py` é cair abaixo de `MIN_DIAS` e virar
  "monitorando", ou seja, o motor fica mais **calado**, não mais errado. Mesma
  correção na paginação de ad_groups (falha na 2ª página devolvia as 50
  primeiras como se fossem o total) e na busca de itens. (3) 401/403 virava
  "conta sem Product Ads?", mandando mexer no Mercado Ads em vez de rodar
  `pegar_token.py`. **Exceção deliberada preservada:** `buscar_detalhe_campanha`
  continua devolvendo `{}` — vira NULL, e `AVG()` ignora NULL, então falha ali
  já significa "sem sinal" e nunca "campanha saudável". Novo nó
  `coletor_ads_nao_sei_e_isolamento`. **Método:** os achados vieram de uma
  auditoria feita por outra ferramenta de agente, conferida linha a linha aqui —
  ela reconheceu os padrões e acertou 4 de 6, mas **inventou a consequência** do
  achado principal. Revisor que aponta onde olhar, não autoridade sobre o que
  acontece.
  Depois do `--update`: **1744 nós, 3306 arestas, 0 órfãs**.
- **2026-08-04 — a pista do monitor é "SAIR da pasta", não "ser apagado"
  (app Zebra v1.26.2).** O outro lado passou a **mover** o arquivo impresso com
  sucesso para `~/zebra_usb_concluidos/AAAA-MM-DD/` em vez de apagá-lo: quando a
  impressora aceita o job no spooler e falha **fisicamente** depois (papel preso,
  ribbon), o lote agora pode ser reimpresso — antes o arquivo já tinha sumido.
  **Nada muda no código daqui** (a pista lê o caminho não existir mais, e mover
  satisfaz isso), mas sete pontos do repertório descreviam o mecanismo como
  "ele apaga após imprimir" — descrição que virou falsa e cara: quem investigasse
  um lote perdido procuraria um arquivo apagado que na verdade **existe**. Trocado
  por "sai da pasta", que descreve o que a pista de fato exige. O que ela exige
  mesmo é a **assimetria** — *sucesso sai, falha permanece* —, agora contratada
  explicitamente dos dois lados: se a falha também fosse movida (a ideia de uma
  pasta `.erros/`, considerada e descartada lá), ela seria lida aqui como
  **impressa**. A pasta de retenção fica **fora** da vigiada e na raiz do perfil
  por dois motivos que valem registrar: o OneDrive não sincroniza a raiz do perfil
  (o *Known Folder Move* só redireciona Desktop/Documentos/Downloads) e um arquivo
  já impresso deixa de poder ser **reingerido** pelo monitor sem depender de o
  filtro do polling continuar não-recursivo. Novo nó
  `retencao_de_concluidos_zebra`. Lição de método: **contrato mudado de um lado
  envelhece a documentação do outro em silêncio** — nenhum teste falha, porque a
  descrição não é executável.
  Depois do `--update`: **1735 nós, 3279 arestas, 0 órfãs**.
- **2026-08-04 — `/perguntas`: o bot dispara o n8n (e não responde nada).** O dono
  tem um fluxo no n8n que lista perguntas/mensagens sem resposta de outra conta e
  quer acioná-lo pelo mesmo bot. A restrição que desenha tudo: **o Telegram
  entrega os updates de um bot a UM consumidor só** — quem lê os comandos é este
  projeto (polling), e o n8n entra apenas como **remetente**. Por isso o comando
  faz um POST no webhook, manda um "🔎 Consultando..." e sai de cena; a resposta
  chega depois, escrita pelo n8n no mesmo chat. Nós novos: `bot_perguntas_n8n`,
  `webhook_url_e_segredo` (a URL **é** a credencial — o endpoint não pede
  autenticação, e este repositório é público: fica no `bot_config.json`/env e
  fora de todo texto de erro, com `sem_segredos` redigindo `/webhook/…` como 3ª
  camada), `bot_menu_comandos_por_chat` (o `setMyCommands` **global** mostraria a
  lista de comandos a qualquer estranho, desfazendo a correção do `/menu` de
  03/08 — por isso `BotCommandScopeChat`) e
  `graph_sync_versioned_set_consistente` (a validação ainda usava `git ls-files`
  puro: o coletor criava nós para arquivo novo e a validação os rejeitava —
  mesma intermitência por ordem-de-stage do #208, pela porta dos fundos).
  Depois do `--update`: **1631 nós, 3067 arestas, 0 órfãs**.

- **2026-08-04 (incidente) — reiniciar o bot não reiniciava nada.** Relato do
  dono: *"mandei /versao e deu aviso de desatualizado, rodei os comandos e mesmo
  assim não atualizou"*. O `rodar-bot-oculto.ps1` subia o `.bat` com
  `Start-Process` **sem `-Wait`**: o PowerShell saía no primeiro segundo, o
  Agendador dava a tarefa por terminada e o bot ficava **órfão** da árvore da
  tarefa. Consequência dupla — o `/end` não tinha o que matar **e** o `/run`
  subia um **segundo** bot por cima do primeiro; os dois pollavam o mesmo token
  (409, que não derruba nenhum) e o **antigo** seguia respondendo. A receita
  errada estava em **três** lugares (mensagem do `/versao`, do `/atualizar` sem
  lançador, e o `Atualizar programa.bat`), então consertar um só deixaria a
  armadilha viva. Nó novo: `reinicio_do_bot_orfao`. Lição geral registrada nele:
  **"disparar e sair" quebra qualquer supervisor que gerencie por árvore de
  processos** — e o sintoma não é um erro, é um comando que parece funcionar e
  não faz nada. O `/atualizar` nunca sofreu disso porque não mata ninguém: o
  próprio bot sai e o laço do `.bat` o traz de volta.
  Depois do `--update`: **1696 nós, 3190 arestas, 0 órfãs**.

- **2026-08-04 — `/perguntas` manda o `chat_id` (preparação para as próximas
  integrações do n8n).** Sem ele, cada fluxo do n8n precisa ter um chat **fixo**
  escrito por dentro — o que funciona com um comando e um chat, e vira dívida
  assim que houver vários. É aditivo (campo a mais, o fluxo atual ignora).
  Registradas no nó `bot_perguntas_n8n` as três armadilhas do crescimento:
  **botão inline mandado pelo n8n não funciona** (o `callback_query` é um update
  e vai para o consumidor do polling — este projeto —, que não conhece aquele
  `callback_data`), teclado persistente idem (cai no catch-all "Não entendi"), e
  **o n8n não consegue reagir a comando nenhum**: toda função nova precisa de um
  handler deste lado, mesmo que o trabalho todo seja dele.
  Depois do `--update`: **1694 nós, 3185 arestas, 0 órfãs**.

- **2026-08-04 (incidente) — config do bot inválida: a falha que não aparece em
  lugar nenhum.** Relato: *"reiniciei, esperei, mandei /atualizar e não
  respondeu — acho que o Reiniciar Bot.bat está com problema"*. O script estava
  certo. A URL de um webhook foi parar **fora das chaves** do `bot_config.json`,
  e três camadas de silêncio se somaram: o `_ler_json` devolve `{}` para
  qualquer falha (JSON malformado → token "some"); a mensagem que sobrava era
  "Token ausente", mandando procurar o **token** e não a vírgula; e sob o
  lançador o bot roda em **janela oculta**, então o `print` não era visto e o
  `bot.log` só mostrava a linha *anterior* ao crash. O único sintoma visível
  virava "reinicia a cada 15s". Nó novo: `config_bot_invalida_silenciosa`.
  Corrigido com `_ler_bot_config` (invalido ≠ ausente, com **linha e coluna**) e
  com as falhas de inicialização indo para o `bot.log`. Lição: **uma falha que
  só aparece onde ninguém olha é uma falha silenciosa** — sob janela oculta,
  "imprimir o erro" não conta como reportar.
  Depois do `--update`: **1734 nós, 3273 arestas, 0 órfãs**.

- **2026-08-04 — `/anuncios`: a segunda integração vira tabela.** Com o segundo
  fluxo do n8n, o copiar-colar deixaria de ser barato. Entrou `IntegracaoN8N`
  (dataclass) + a tupla `INTEGRACOES`, de onde saem a chave de config, a variável
  de ambiente, o menu e o botão; `_acionar_n8n` virou o corpo único. Comando novo
  é **uma linha** na tupla + a URL no `bot_config.json`. Duas decisões que
  parecem detalhe e não são, registradas no nó `bot_perguntas_n8n`: cada comando
  tem um **handler nomeado** que só delega (um genérico registrado em laço
  passaria batido pelo guardião de autorização, que varre o `main` por AST — a
  generalização teria furado a rede de segurança), e a chave de chat continua
  `chat_perguntas` mesmo valendo para todas (renomear obrigaria a reeditar o
  config da máquina de produção, por ganho cosmético).
  Depois do `--update`: **1728 nós, 3263 arestas, 0 órfãs**.

- **2026-08-04 — alerta de NF-e na Shopee: o espelho invertido do ML.** No ML a
  venda travada **some** do app. Na Shopee é o contrário: ela continua em
  `READY_TO_SHIP`, já aparece na tela, e o alerta **já a chamava de "pronta"** —
  sendo que a Shopee **recusa o `ship_order`** enquanto a nota estiver pendente
  (`error_pending_invoice`, confirmado com o suporte). Era dizer que está pronto
  o que a própria Shopee nega: mesma família do incidente de 31/07. Nó novo:
  `alerta_nf_shopee`. Registrado nele o que **não** confiar em duas respostas do
  suporte — a de que `ship_by_date` só é atribuído após a nota virar válida
  **contradiz o dado real** (havia pedido `pending` **com** `ship_by_date`), e o
  push `fbs_br_invoice_issued_push` é de FBS, enquanto os pedidos do dono são
  `fulfilled_by_local_seller`.
  **Corrigido no mesmo dia, antes de mergear:** o painel do dono desmentiu o
  suporte — as 20 `pending` apareciam como **"Em processamento"** e as 3 `valid`
  como "Em aberto" (casamento exato, 20/20 e 3/3). Logo `pending` cobre **dois**
  casos, a função virou `nota_nao_validada` (`!= "valid"`, errando para o lado de
  não imprimir) e o aviso **parou de afirmar a causa**. Lição registrada:
  resposta de suporte é evidência fraca perto do painel e da API da conta real;
  quando divergem, vence o dado.
  Depois do `--update`: **1713 nós, 3232 arestas, 0 órfãs**.

- **2026-08-04 — diagnóstico de estados da Shopee (antes do alerta).** O dono
  pediu o mesmo alerta de NF-e para a Shopee. O sinal, porém, é **contrato
  deles** e não está documentado de forma confiável — e o app hoje só pede
  `order_status=READY_TO_SHIP`, então uma venda travada em outro estado é
  invisível exatamente como o `invoice_pending` era no ML. Em vez de adivinhar,
  entrou `listar_pedidos_com_status` + o comando `python shopee_api.py status`,
  que lista os estados existentes na loja com contagem e mostra os **campos**
  que a API devolve para os pedidos fora de `READY_TO_SHIP` — é lá que aparece
  o sinal, qualquer que seja o nome dele. Mesmo método que confirmou o
  `invoice_pending` no ML.
  Depois do `--update`: **1699 nós, 3195 arestas, 0 órfãs**.

- **2026-08-04 — alerta de venda parada em "Informe a NF-e".** O dono controla
  estoque: quando vende um item que não tem, o faturador não sobe o XML e o
  envio fica em `invoice_pending` — **nunca** chega a `ready_to_print`. Ou seja,
  a venda que mais precisa de aviso (a que exige reposição no mesmo dia) era a
  única invisível para o app inteiro. Nó novo: `alerta_nf_pendente`. A regra que
  não pode cair está escrita nele: `filtrar_para_imprimir` **continua devolvendo
  só `ready_to_print`** — a separação lá dentro é por SUBSTATUS, não por "veio
  preenchido"; o ML não libera a etiqueta desse envio, e contá-lo como pronto
  poria no lote uma etiqueta que não existe (família da invariante 1). Os dois
  grupos saem da **mesma passada** (zero chamada de API a mais) e o aviso vai em
  **balde de dedup próprio** — dividir o balde faria o `shipment_id` já avisado
  calar o "está pronta" de quando o XML subisse. A CLI ganhou o diagnóstico
  `substatus` para confirmar o nome na conta real, já que ele é contrato do ML.
  Depois do `--update`: **1693 nós, 3183 arestas, 0 órfãs**.

- **2026-08-04 — `/atualizar`: `git pull` pelo Telegram.** Pedido do dono: *"às
  vezes estou no celular e não consigo dar `git pull` na pasta, queria não ficar
  refém de estar no computador"*. A peça que torna isso simples já existia — o
  `Iniciar Bot (auto).bat` é um **laço**: se o processo morre, ele sobe de novo
  15s depois. Então o bot **não dispara processo nenhum** para se reiniciar
  (nada de `schtasks` daqui, que é o terreno do WinError 6): ele **sai**, e o
  laço o traz de volta na versão nova. Nós novos: `bot_atualizar_remoto` e
  `atualizar_guardas` — as duas guardas por dano irreversível: **árvore suja**
  (`nomes_sku.json`/`skus_por_anuncio.json` são versionados **e** editados pela
  tela; com alteração local o comando não puxa nada e lista os arquivos — nada
  de `stash`/`reset` automático em cima do trabalho do dono) e **`TRAVA_CONTA`
  com `blocking=False`** (o reinício não pode cair entre gerar o ZIP e marcar o
  estado — invariante 1). Achado ao escrever o teste: o `.strip()` na saída
  inteira do `git status --porcelain` **comia a primeira letra** do primeiro
  arquivo (`nomes_sku.json` → `omes_sku.json`).
  Depois do `--update`: **1675 nós, 3149 arestas, 0 órfãs**.

- **2026-07-30 — Canal de volta com o app da Zebra (mural de status) + decisão
  de NÃO fundir os dois apps.** A entrega entre contador e app da Zebra é por
  arquivo e não tinha resposta: a tela adivinhava por duas pistas (o ZIP sumir,
  o log do monitor avançar). Duas limitações reais: "sumir" só existe com
  *Excluir após imprimir* **ligada**, e nenhuma das pistas distingue **falha**
  de "ainda imprimindo" (o monitor **não apaga** o que falhou). Agora o app
  publica `~/zebra_usb_status.json` (`registrar_status_trabalho`, v1.26.0) e
  `_veredito_do_status` o consulta **antes** das pistas. Nós novos:
  `canal_de_volta_status_zebra`, `veredito_resposta_antes_de_pista`,
  `status_ler_json_exists_fora_do_try` (o `except OSError` extra não é
  redundante — o `exists()` do `ler_json` fica fora do try dele) e o conceito
  `nao_fundir_contador_e_zebra` (evidência decisiva: os `PREFIXOS` do monitor
  cobrem o download manual do painel do ML, então ele funciona sem o contador;
  mais UAC, instância única de bandeja e dependências Windows-only). Depois do
  `--update`: **1557 nós, 2943 arestas, 0 órfãs**.

- **2026-08-03 (segurança) — varredura com modelo de ameaça explícito.** Achado:
  **`cmd_start` (`/start`, `/menu`, `/ajuda`) não checava autorização** e
  respondia a qualquer estranho com a lista de comandos e a **loja ativa** — o
  bot é a única superfície que qualquer pessoa na internet alcança. Nenhum dado
  de venda vazava (todo botão passa por `cb_botao`, que checa), mas era
  reconhecimento de graça. O risco real não era o código de hoje e sim **o
  handler de amanhã**: a checagem vive em 2 pontos de estrangulamento
  (`_responder`/`_listar_grupos`) e um comando novo que não delegue nasce aberto.
  Daí o guardião `test_todo_handler_registrado_checa_autorizacao`, que varre os
  handlers do `main` por AST — **verificado que ele pega a regressão** (handler
  falso injetado → teste vermelho). `ABERTOS` lista os 2 abertos de propósito
  (`/id`, catch-all) com o motivo.
  **Verificados OK, por teste e não por leitura:** nenhuma credencial real em
  **353 commits** de história (os 2 hits são fixtures, uma chamada `TOKEN_FALSO`);
  zero `eval`/`exec`/`pickle`/`shell=True`/`verify=False`/`http://`; injeção de
  ZPL barrada nos dois pontos que recebem texto de produto (`carimbo` e
  `divisoria` removem `^` e `~`, os dois prefixos de comando); nome de arquivo
  saneado por `isalnum`; cofre público sem segredo (e o validador do CI procura
  ativamente); dependências com teto de major. **Risco aceito e registrado:**
  credenciais gravadas sem `chmod 0600` — no Windows do dono o `os.chmod` só
  mexe no bit de somente-leitura, então não agregaria proteção real.
  Depois do `--update`: **1590 nós, 2985 arestas, 0 órfãs**.

- **2026-08-03 (periferia) — o que as auditorias nunca olharam.** Pergunta do
  dono: todas as auditorias entraram pelo NÚCLEO; ~3.000 linhas de periferia
  (`tools/`, `ads-monitor/`, `pegar_token*`, `registro.py`, `.gitignore`, CI)
  nunca foram vistas. Priorizado por **dano irreversível**, não por tamanho.
  Achados: (a) **`registro.sem_segredos` tinha 2 brechas** — `app_secret` (do
  TikTok, aberta no mesmo dia) e o token do **Telegram no CAMINHO** da URL
  (`/bot<ID>:<TOKEN>/`), que a regex de `chave=valor` não alcança; somado o
  `Bearer` do ML por precaução. São 64 linhas que são a ÚLTIMA defesa contra
  token em log. (b) **screenshots da GUI não gitignorados** (`out.png`,
  `tela_*.png`) — mostram pedidos/SKUs reais; e `api-monitor/snapshots/` só
  ignorava `.md`, padrão permissivo ao contrário do `dados/*` endurecido.
  **Verificados OK:** nenhum segredo rastreado no git, todos os arquivos de
  credencial/estado/log ignorados (teste empírico com `git check-ignore`), e o CI
  barra de verdade (pytest em 3.11+3.12, lint, cofre, smoke da GUI).
  Depois do `--update`: **1584 nós, 2978 arestas, 0 órfãs**.

- **2026-08-03 (por blocos) — CORRIDA DE CONTA no bot.** Varredura completa
  dividida por dano potencial (estado/marcação, agrupamento, token, GUI, bot,
  Shopee) + passada automática de lint com regras além das do CI. Achado grave:
  `core.definir_conta()` troca **globais** do núcleo, e o bot roda em paralelo via
  `asyncio.to_thread` — o job do alerta percorre todas as contas enquanto o dono
  pode mandar `/imprimir` de outra. O comando lia credencial/estado da conta que o
  JOB apontou: token errado e marcação no `estado_grupos.json` da outra conta
  (reproduzido: **39 de 40** leituras erradas). Corrigido com
  `bot_telegram.TRAVA_CONTA` (RLock) em `_coletar`, `_imprimir_grupo`, `_prontos`,
  `_trocar_conta` e o bloco do alerta, com teste-guardião que falha se um caminho
  novo esquecer a trava. **Julgados OK na mesma varredura:** disciplina de fuso
  (todos os `datetime.now()` sem tz são de log/exibição — nenhuma decisão),
  thread-safety da GUI (as 5 threads voltam por `root.after`), a trava
  ponta-a-ponta do `ocupado` (liberada em todos os caminhos de erro),
  `fundir_grupos`, `estado.marcar_impresso` e `historico.registrar`.
  Depois do `--update`: **1581 nós, 2975 arestas, 0 órfãs**.

- **2026-08-03 — Varredura atrás do mesmo padrão: mais 2 falhas silenciosas.**
  Pedido do dono depois do incidente de 31/07 ("procure outros erros silenciosos").
  Achados e corrigidos, ambos **reproduzidos antes**:
  (1) **`_sla` devolvia `{}`** ao falhar → `expected_date=""` → a venda de HOJE
  não casa com o filtro do dia e cai em "Outras datas". Era o mesmo incidente por
  uma segunda porta, mais discreta (o pedido continua visível, só no balde
  errado). Agora `None` = "não sei", o pedido **continua entrando** (ele está
  pronto — excluir seria pior) marcado com `data_incerta`, contado e avisado.
  (2) **`_detalhe_item` gravava a falha no cache**: entrada vazia ia para o
  `itens_cache.json`, e como `buscar_detalhes` só busca o que não está em cache,
  uma falha **transitória virava permanente** — item sem GTIN (logo chave
  `{item_id}:{var}` em vez de `GTIN:…`) e sem `seller_sku`, derrubando a adoção
  feita em `skus_por_anuncio.json`. Só limpando o cache na mão para consertar.
  Agora falha não é gravada.
  **Segunda passada (mesmo dia), atrás de outros formatos de erro:**
  (3) **401/403 viravam "não sei"** — com o token revogado TODA consulta falha e
  a tela dizia "a API não respondeu sobre 150 envios, clique em Atualizar de
  novo", conselho que nunca funcionaria, com a causa real escondida.
  `_propagar_se_auth` re-levanta credencial recusada dizendo o que fazer;
  transitório segue virando `None`. Nota: esse *conselho enganoso* foi
  **introduzido pelo próprio aviso do #205** — corrigir uma falha silenciosa
  criou uma falha ruidosa e errada.
  (4) **`baixar_zpl` conferia o HTTP 200 mas não a QUANTIDADE**: um lote com
  menos etiquetas que envios saía do jeito que veio e `preparar_lotes` devolvia
  todos os envios como impressos — o que a **invariante 1** proíbe, e no caminho
  do bot/CLI (que marcam sem confirmação humana) essa guarda é a única defesa.
  Comparação `>=`, não `==`, para não amarrar no formato do ML.
  Depois do `--update`: **1576 nós, 2968 arestas, 0 órfãs**.

- **2026-07-31 — INCIDENTE: lote incompleto em silêncio (envio não verificado).**
  Num dia de API do ML instável, o operador imprimiu **5 de 7** vendas do mesmo
  SKU; um 2º "Atualizar" trazia as faltantes. Causa: `buscar_envio` devolvia
  `{}` quando a API recusava (depois das re-tentativas do `_com_retry`), e o
  `{}` percorria o fluxo **exatamente como um envio que não está pronto** —
  `_avaliar_pedido` descartava o pedido sem uma linha de aviso. Mesma família do
  falso alarme do monitor (2026-07-30), ao contrário: lá avisava sem prova, aqui
  calava **com** prova na mão. Corrigido com `None` = "não sei" (como o
  `_mtime_log_monitor` já fazia), `verificado` no retorno de `_avaliar_pedido`,
  contagem em `filtrar_para_imprimir`/`Coleta`/provedores (o modo Ambas **soma**
  as contas) e aviso na tela antes de imprimir. Depois do `--update`:
  **1567 nós, 2956 arestas, 0 órfãs**.

- **2026-07-30 (fim do dia) — TikTok Shop ARQUIVADO.** Pausa a pedido do dono,
  não desistência. Travou **antes do 1º byte de API**: o **Service ID** não
  aparece no painel (e não é a "Chave do aplicativo"), então
  `services.tiktokshop.com/open/authorize` responde *"This service does not
  exist"*. Ficam prontos e **não devem ser refeitos**: levantamento,
  `pegar_token_tiktok.py`, a página de retorno do OAuth (serve à Shopee **e** ao
  TikTok) e o app no painel. **Passo que destrava na retomada:**
  `POST /order/202309/orders/search` na Ferramenta de teste de API — prova se a
  API responde e entrega a forma real do payload. Estado registrado em
  `docs/TIKTOK_SHOP_API.md`, `CLAUDE.md`/`AGENTS.md` e no cofre
  (`obsidian/IA/Estado atual.md`). Depois do `--update`: **1562 nós, 2950 arestas,
  0 órfãs**.

- **2026-07-30 — TikTok Shop: levantamento + bootstrap do OAuth.** O dono quer,
  **por agora, só aviso de venda nova no Telegram** — não imprimir —, o que
  contorna as perguntas em aberto sobre etiqueta (ZPL? NF-e?) e reduz o trabalho
  a uma função do mesmo feitio da que a Shopee usa no alerta pós-horário.
  Entraram `docs/TIKTOK_SHOP_API.md` e `pegar_token_tiktok.py` (o TikTok Shop
  **não tem botão de "autorizar loja"**: o link é montado com o **Service ID**,
  não com o `app_key`). Registrada também a **armadilha dos portais parecidos**,
  que custou tempo 3× num dia — `developers.tiktok.com` (Client key/Client
  secret, Login Kit) **não é** `partner.tiktokshop.com` (App key/App secret,
  Service ID). Depois do `--update`: **1562 nós, 2950 arestas, 0 órfãs**.

- **2026-07-30 — Teste do item 12 feito: resultado NEGATIVO no endpoint.** O
  `--comparar` rodou nas duas contas num dia com coleta real e devolveu
  `HTTP 200` sem `driver.id`. Mas o painel do ML mostrava, nas DUAS contas, o
  MESMO motorista e a mesma placa — a premissa de negócio está **confirmada**;
  o que falhou foi a fonte escolhida. Pista: o card diz "Requer o código de
  autorização", dado que costuma viver no **envio**, não no cronograma semanal
  da conta. `tools/diag_coleta.py` ganhou `_porque_sem_driver` (separa as 4
  causas possíveis, porque cada uma pede ação diferente) e `--cru` (despejo da
  resposta com nome/placa **mascarados** por `_mascarar_fundo`, que preserva a
  estrutura e esconde a pessoa). O item 12 **não morreu** — está esperando o
  `--cru` dizer qual dos 4 casos é o nosso.
  **VEREDITO do `--cru` (mesmo dia):** o endpoint é um GABARITO semanal —
  `driver`, `carrier` e `vehicle` existem na estrutura mas vêm vazios em TODOS
  os 7 dias (`date: ""` também). Nenhum ajuste de campo resolve: a fonte está
  errada. A pista do "código de autorização" também caiu — a doc oficial diz que
  é um código FIXO do vendedor (Preferências de venda), não por motorista.
  Último candidato barato: `GET /shipments/{id}`, que o núcleo JÁ chama —
  `--envio` + `_caminhos_de_interesse` varrem o payload sem despejá-lo inteiro
  (envio carrega nome e endereço do COMPRADOR; despejo cru ali vazaria dado de
  terceiro). Se também não vier, o item 12 vira "não fazer".
  **ENCERRADO (mesmo dia):** o `--envio` provou que o payload do envio não tem
  nem a chave `driver`/`vehicle`/`carrier` (apareceriam vazias se existissem).
  As duas fontes plausíveis da API pública são negativas → **item 12 = "não
  fazer"**. O painel do vendedor mostra o dado, logo ele existe do lado do ML,
  mas por endpoint interno. A premissa de negócio estava CERTA; falta o canal.
  Nada muda: o 🌐 Ambas segue manual. `--chaves` (lista todos os caminhos de
  chave, sem valores — nome de chave não é dado pessoal) fica registrado como o
  que reabriria o item, caso o campo exista com outro nome (`courier`,
  `collector`, `operator`).
- **2026-07-30 — Resumo de vendas do bot reformatado (HTML do Telegram).** A
  mensagem era uma lista crua "SKU - qtd" em ordem de chegada, cansativa de ler
  no celular. Agora: cabeçalho com janela e horário, um bloco por conta com
  subtotal, lista **dentro de `<pre>`** (única forma de alinhar coluna no
  Telegram — fora dele a fonte é proporcional) ordenada por **quantidade
  decrescente**, e total geral. Detalhes que o `relatorio.py` documenta: escape
  de `& < >` é obrigatório (erro → 400 e a mensagem não chega); **maiúscula
  antes de escapar**, senão o `.upper()` produz `&AMP;` (entidade quebrada —
  bug pego em teste); **largura medida no texto CRU**, porque o Telegram
  renderiza `&amp;` como 1 caractere; e mensagem **única**, porque
  `dividir_mensagem` partiria um `<pre>` no meio. O corte por limite mostra os
  maiores + "… e mais X SKUs (Y un)". Novo CLI `bot_telegram.py testar-resumo`
  para conferir no celular sem esperar venda.
  Traz também o bloco **📦 TOTAL POR SKU** somando as contas (a lista de
  reposição — sem ele o dono somaria de cabeça o mesmo SKU que aparece em duas
  contas). Só aparece com **2+ contas com venda**: com uma só, repetiria a
  lista dela e viraria ruído.
  O consolidado segue a **ordem da aba Nomes** (a de separação, a mesma da tela
  e do PDF do resumo do dia); SKU não cadastrado vai ao fim em ordem natural.
  O corte por limite escolhe **quem** aparece pela quantidade e mantém a ordem
  da prateleira na exibição — cortar por posição jogaria fora o fim da
  caminhada, e o maior de todos pode estar na última prateleira.
- **2026-07-30 — O token do bot saiu do log (segredo por dentro de biblioteca).**
  A URL da API do Telegram carrega o token no próprio caminho e o `httpx`
  registra cada requisição em INFO — com o log do bot em INFO, o token ia
  inteiro para o `bot.log` e o console, a cada chamada. O `sem_segredos` do
  `registro.py` **não alcançava**: esses registros nascem dentro da biblioteca,
  sem passar pelo código do projeto. `httpx` e `httpcore` passaram a WARNING
  (erro de rede continua visível). Convenção nova no `CLAUDE.md`: biblioteca que
  fale HTTP com credencial na URL tem o **logger** subido, porque redigir na
  saída não cobre o que ela escreve sozinha. Guardas em
  `tests/test_bot_segredo_no_log.py`.
- **2026-07-30 — Falso alarme do aviso do monitor: o ⚠️ passou a exigir prova.**
  Em produção, um lote de 12 avisou "o monitor da Zebra NÃO deu sinal" com a
  impressora trabalhando normalmente; lotes pequenos acertavam. Dois fatos
  somados: em lote grande o ZIP não some dentro do teto (só é apagado na última
  etiqueta) **e** o log do monitor não pôde ser lido — e `_monitor_vivo_desde`
  devolvia um booleano que colapsava "não sei" com "log parado". Corrigido com
  `_mtime_log_monitor` → `None` para "não sei" (silêncio, `sem_saida`); só log
  **encontrado e sem avanço** vira `sem_sinal`. A tela passou a registrar no
  `separador.log` se o log foi encontrado e em qual caminho. Lição:
  **falso alarme é pior que aviso nenhum** — ensina o operador a ignorar o
  aviso, e ele perde a utilidade no dia em que estiver certo.
- **2026-07-29 — Confirmação de impressão: o retorno do app da Zebra.** A
  entrega das etiquetas é por arquivo (ZIP na Downloads) e não havia canal de
  volta: com o monitor fechado, os ZIPs se acumulavam e o dono só descobria pelo
  papel que não saía. `aguardar_impressao` passou a observar dois sinais que o
  monitor **já produzia** — o arquivo sumir (ele apaga após imprimir) e o log
  dele avançar — sem mudar nada do outro lado. A tela identifica os arquivos
  dela por diferença de dois instantâneos (`saidas_na_pasta`). Corrida conhecida
  (achada por teste): consumo antes do 2º instantâneo devolve `imprimindo`,
  nunca `impresso`. O sinal informa e **nunca decide** — a resposta ao "saíram
  certo?" continua sendo do operador (invariante 1). Novo nó
  `confirmacao_de_impressao_monitor_zebra`.
- **2026-07-29 — Incidente: as contas do ML sumiram da tela.** Na primeira
  abertura após a reorganização, o seletor de conta e o modo 🌐 Ambas
  desapareceram (`listar_contas()` devolvia `[]`). Causa: `migrar_para_pastas`
  rodava o corpo inteiro sob **um** `try/except OSError`, então a primeira
  falha de IO abortava em silêncio o resto da fila — e no Windows o bot (que
  sobe no logon pelo Agendador) mantém o `bot.log` **aberto**, o que faz o
  rename levantar `WinError 32`. Como os logs eram movidos **antes** de
  `contas/`, as credenciais ficavam para trás. Correção: o `try/except` desceu
  para dentro de `_mover_se_preciso` (um item travado não leva os outros) e
  `contas/` virou o **primeiro** move da fila. Teste-guarda
  `test_migrar_para_pastas_arquivo_travado_nao_leva_o_resto_junto`. Novo nó
  `migracao_pastas_isolamento_de_falha`.
- **2026-07 — Reorganização da raiz em `dados/` + `logs/`:** pedido do dono —
  a raiz tinha ~35 arquivos misturando código, docs, config de ferramenta e
  todo o dado local (tokens, estado, caches, 4 logs que crescem), e achar o
  `separador_gui.py` que ele abre todo dia virou garimpo. Agora `dados/`
  guarda o que o app lê/escreve (credenciais, estado, caches, de-paras,
  `contas/`) e `logs/` os registros. **Deliberadamente NÃO movidos:**
  `README`/`CLAUDE`/`AGENTS.md` e os configs de ferramenta
  (`.gitignore`, `pyproject.toml`, `ruff.toml`, …) — as ferramentas só os
  procuram na raiz; e os **módulos `.py`**, porque movê-los exigiria tocar
  os 26 arquivos que os importam, 8 `.bat`, o CI e re-ancorar
  `PASTA_SCRIPT` (de onde sai todo caminho de token/estado), e ainda assim a
  raiz não ficaria com um arquivo só (os de ferramenta ficam) — ganho
  parcial, risco alto. **Migração automática** (`migrar_para_pastas`, no
  import do núcleo): move o que estava solto, leva `.bak`/`.corrupto` junto
  (um `.bak` desgarrado guarda refresh já rotacionado) e a pasta `contas/`
  inteira; nunca sobrescreve destino existente e nunca levanta
  (best-effort). `migrar_conta_legado` passou a ler de `PASTA_DADOS`. O
  `.gitignore` inverteu a lógica (ignora `dados/*` e libera os 2
  versionados) para arquivo local novo nunca escapar. Novo nó
  `reorganizacao_pastas_dados_logs`.

- **2026-07 — Auditoria de APIs (ML + Shopee): 3 correções.** Leitura
  integral dos caminhos de rede dos dois marketplaces atrás de
  falhas/quebras/melhorias. (1) **Amarra credencial→arquivo** (a mais
  séria): a "área de risco" aceitava a corrida de `definir_conta` no bot
  como "só leitura", mas o refresh de token é uma ESCRITA que resolvia a
  global `ARQUIVO_CRED` na hora da chamada — um refresh em voo durante a
  troca de conta podia gravar as credenciais de uma conta no arquivo da
  outra (e o `.bak` junto: conta travada). `carregar_credenciais` agora
  grava o arquivo de origem no dict (chave volátil `_arquivo`) e
  trava/releitura/refresh/salvamento usam `_arquivo_das_credenciais`.
  (2) **Dieta do alerta pós-horário**: ~90-100 mil chamadas/dia (ciclo de
  5 min, 24h, janela cheia de 30 dias) cortadas em ~95% com janela de
  horário (07:00–20:59 BR, `_alerta_no_horario`) + janela de busca
  dedicada (`buscar_pedidos(dias=)`, `DIAS_JANELA_ALERTA=5`).
  (3) **Higiene**: reimpressão Shopee lê o cache de AWB antes da rede;
  `resp.json()` com guarda limpa nos dois lados (`_json_limpo`);
  `_aguardar_awbs` com backoff (mesmo teto, ~40% menos chamadas); dedup
  por id na paginação do `buscar_pedidos`. Novo nó `auditoria_apis_2026_07`.

- **2026-07 — Compliance da Shopee, RODADA 2: correção de verdade da taxa
  de sucesso do `v2.logistics.ship_order`:** depois do dono levar as
  perguntas da rodada 1 (abaixo) ao suporte da Shopee, 3 fatos novos
  mudaram o diagnóstico: (a) `batch_ship_order` **não conta** pra mesma
  métrica de sucesso do `ship_order` singular; (b) propagação de
  `fulfillment_status`/`is_shipment_arranged` pode levar **até 15-20
  minutos** (bem mais que os ~40s de polling deste módulo); (c) códigos de
  erro exatos confirmados: `logistics.package_already_shipped`/"This
  parcel has already been shipped" e `logistics.error_param`/"The order is
  being allocated, please wait until the allocate is completed.". Isso
  revelou que a rodada 1 **não** resolvia o problema de verdade: um pedido
  que passa pelo batch mas fica sem AWB (só pelo timeout curto, não porque
  falhou) caía no fallback individual, que consultava `parametros_envio`
  ainda com o status **antigo** (não propagado) e chamava `ship_order` de
  novo — exatamente o cenário "already shipped" que conta contra a
  métrica. Corrigido: `_organizar_varios` não manda mais pro individual
  quem passou pelo batch sem AWB — vira `falhas` pendente de confirmação
  ("tente de novo em alguns minutos"; na próxima tentativa, minutos
  depois, `_filtrar_ja_arranjados` já veria o status atualizado e não
  reenviaria). Individual só recebe quem já estava arranjado ANTES desta
  chamada (1.5, sem risco de propagação) ou quem o batch nunca chegou a
  tentar (endpoint indisponível por inteiro). Defesa em profundidade
  adicional em `organizar_envio`: catch específico pra "already been
  shipped" (não propaga como erro, só passa a aguardar o AWB) e retry com
  backoff curto (3 tentativas, 3s) pra "being allocated" (documentado como
  transiente pela própria Shopee). Migração completa
  (`v2.order.search_package_list` + `v2.order.get_package_detail`) segue
  de backlog — mudança maior de modelo (`package_number` pode ser 1:N com
  `order_sn`), não urgente pro compliance (`docs/PRIORIDADES_TECNICAS.md`
  item 11, com as 6 respostas do suporte documentadas).

- **2026-07 — Compliance da Shopee, RODADA 1: correção inicial da taxa de
  sucesso do `v2.logistics.ship_order`:** a Shopee mandou um requisito de
  qualidade **obrigatório** (prazo curto, risco de penalidade) exigindo
  success rate > 90% por 7 dias consecutivos nesse endpoint. O FAQ deles
  documenta "This parcel has already been shipped" como causa de erro —
  reenviar um pedido já arranjado. Investigando `_organizar_varios`, achei
  uma lacuna real: o caminho individual (`organizar_envio`) já checava
  `envio_ja_arranjado` antes de (re)enviar, mas o caminho em **lote**
  mandava todos os `restantes` pro `batch_ship_order` sem essa checagem —
  um pedido arranjado numa tentativa anterior (AWB demorou mais que o
  timeout do polling, ou uma 2ª impressão do mesmo grupo) seria reenviado
  via batch e provavelmente rejeitado. Corrigido com `_filtrar_ja_arranjados`
  (nova etapa 1.5, antes do batch, consulta `parametros_envio` em
  paralelo; em dúvida — falha de rede — NÃO assume arranjado, mesmo
  espírito conservador de `envio_ja_arranjado`/`_rede_limpa`). A migração
  mais completa que a própria Shopee recomenda ficou **pendente** —
  `open.shopee.com` está bloqueado neste ambiente, sem o schema real
  desses endpoints não dá pra implementar com segurança numa ação que
  compromete o envio de verdade — perguntas formuladas pro dono levar ao
  suporte (respondidas na rodada 2 acima). Nó `shopee_compliance_ship_order`
  (atualizado na rodada 2 com o diagnóstico completo).

- **2026-07-24 — Alerta pós-horário estendido pra Shopee:** pedido do dono
  depois de eu confirmar viabilidade — a Shopee tem sinal equivalente ao
  `ready_to_print` do ML: `READY_TO_SHIP` (já filtrado por
  `listar_order_sns`) + despacho hoje via `ship_by_date`. Nova
  `shopee_api.pedidos_prontos_novos(cred, token, avisados, hoje)` (par
  Shopee de `filtrar_para_imprimir`+`extrair_itens`), reusando
  `_itens_de_detalhes` extraído de dentro de `grupos_de_detalhes` (evita
  duplicar a extração de SKU/quantidade entre agrupamento e alerta).
  `job_alerta_pos_horario` agora checa a Shopee depois do loop das contas
  ML, tratando `"Shopee"` como mais uma chave no mesmo
  `alertas_pos_horario.json` — dedup por `order_sn` (string), não
  `shipment_id`. Pula em silêncio se `credenciais_shopee.json` não existir
  (setup só-ML continua válido, sem log de erro a cada 5 min). Envio +
  persistência extraídos pra `_disparar_alerta`, compartilhada entre ML e
  Shopee. `/vendasapos` ganha a seção Shopee automaticamente (já era
  genérico por "conta"). Novo nó `bot_alerta_shopee`.

- **2026-07-24 — Alerta pós-horário: formato enxuto + resumo agregado
  (`/vendasapos`):** pedido do dono depois de testar na máquina real. O
  alerta parou de mostrar o número do envio — agora é só `SKU - quantidade`
  (`relatorio.texto_alerta_pos_horario`, somado quando o mesmo SKU aparece
  em mais de um envio). Cada disparo também passou a persistir os itens em
  `alertas_pos_horario.json` (junto do dedup); o novo comando/botão
  `/vendasapos` (`bot_telegram.cmd_vendas_apos`) junta tudo que já foi
  avisado hoje, por conta, com um TOTAL por SKU no final
  (`relatorio.texto_resumo_vendas_apos`) — evita poluir o chat quando várias
  vendas caem em sequência depois das 8:30. Só relê o estado persistido, sem
  chamada de API. Novo nó `bot_vendas_apos_resumo`.

- **2026-07-24 — CLI pra testar o alerta pós-horário na hora:**
  `python bot_telegram.py testar-alerta` (ou `atalhos/'Testar Alerta
  Pos-Horario.bat'`) monta um `Application` de verdade e chama
  `job_alerta_pos_horario()` uma única vez, fora do agendamento de 5 min —
  reusa 100% a lógica já validada, sem reimplementar filtro nem envio.
  Motivado por confirmar que o envio funciona depois de trocar o mecanismo
  de auto-start (nó abaixo) sem precisar esperar o próximo ciclo E uma
  venda real cair. Novo nó `bot_testar_alerta_cli`.

- **2026-07-24 — Auto-start pela tela abandonado; bot agora sobe no login do
  Windows:** os dois achados abaixo tratavam sintomas de uma mesma
  causa-raiz (qualquer `subprocess` disparado a partir de `pythonw` herda
  handles de stdin/stdout/stderr inválidos) que continuava reaparecendo de
  formas novas. Em vez de seguir caçando o próximo achado, todo o mecanismo
  de auto-start pela tela foi **removido**:
  `core.bot_ja_rodando`/`_pid_vivo`/`core.iniciar_bot_em_segundo_plano`,
  `bot_telegram._escrever_lock_bot`/`_limpar_lock_bot`, `ARQUIVO_LOCK_BOT`
  e `tests/test_bot_lock.py`. No lugar: `atalhos/registrar-tarefa-bot.ps1`
  (rodado uma vez) registra uma tarefa no Agendador de Tarefas do Windows
  (gatilho `AtLogOn`, mesmo padrão do `ads-monitor/registrar-tarefa.ps1`)
  que sobe `atalhos/'Iniciar Bot (auto).bat'` sem janela visível via
  `atalhos/rodar-bot-oculto.ps1` (`Start-Process -WindowStyle Hidden`) a
  cada login — um processo criado do zero pelo Windows, sem herdar nada
  quebrado do `pythonw`, independente da tela estar aberta. Nó
  `bot_segundo_plano_junto_com_tela` reescrito como registro histórico (o
  que foi tentado e por que não funcionou); novo nó
  `bot_agendador_tarefas_logon` documenta o mecanismo atual. Contagens:
  **1373 nós, 2513 arestas, 0 órfãs** (3 arestas manuais pra código removido
  descartadas; 6 arestas de `calls` para símbolos removidos reancoradas nos
  nós de arquivo pelo sincronizador).

- **2026-07-24 — Correção real 2 (mesma causa-raiz, código desde removido
  acima): "subiu" duas vezes, bot nunca respondia no Telegram:** mesmo com o `stdin` já corrigido (achado
  abaixo), o log da tela mostrava `Bot em segundo plano: subiu` em duas
  aberturas seguidas e o bot nunca respondia às mensagens. Causa: o `Popen`
  que sobe o `.bat` só redirecionava `stdin`, não `stdout`/`stderr` — o
  `print("Bot rodando... Ctrl+C para parar.")` em `bot_telegram.py`, **fora**
  do `try/finally` que limpa `bot.lock`, derrubava o processo com exceção
  não tratada ao herdar um stdout inválido do `pythonw`, logo após gravar o
  lock. O lock ficava preso num PID já morto; a tela seguinte via
  `bot_ja_rodando()==False` e subia outro bot por cima, em loop, sem nunca
  chegar a `app.run_polling()`. Corrigido com
  `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` no mesmo `Popen` (o
  log de verdade já vai pro arquivo via `FileHandler`). Nó
  `bot_segundo_plano_junto_com_tela` atualizado com o 2º achado.

- **2026-07-24 — Correção real: auto-start do bot travava pra sempre com
  `pythonw`:** testando na máquina do dono, o bot funcionava manual
  (`Iniciar Bot.bat`) mas nunca subia sozinho pela tela — e sem log nenhum.
  Causa raiz: a tela roda via `pythonw` (sem console/handles padrão
  válidos); sem `stdin=subprocess.DEVNULL`, o `subprocess.run` do `tasklist`
  em `_pid_vivo` falhava sempre com `WinError 6`, e o default antigo "em
  dúvida assume vivo" fazia um `bot.lock` travado (de um teste manual
  anterior) bloquear o auto-start **para sempre** (PID confirmado morto no
  Gerenciador de Tarefas, mas `bot_ja_rodando()` sempre devolvia `True`).
  Corrigido: `stdin=subprocess.DEVNULL` no `tasklist` e no `Popen` do `.bat`
  (evita herdar o handle quebrado do `pythonw`); default invertido pra "em
  dúvida assume MORTO" (o Telegram já rejeita 2 instâncias do mesmo bot
  pollando ao mesmo tempo — erro 409, autolimitado — bem menos grave que
  travar pra sempre); `iniciar_bot_em_segundo_plano()` passou a devolver uma
  string curta (`subiu`/`ja_rodando`/`nao_windows`/`bat_ausente`) que a tela
  sempre loga, não só a exceção — sem isso, o diagnóstico deste mesmo bug
  ficou mais lento (nada aparecia no log). Nó `bot_segundo_plano_junto_com_tela`
  atualizado com o achado. Contagens: **1394 nós, 2538 arestas, 0 órfãs**.

- **2026-07-24 — Alerta pós-horário do bot + tela sobe o bot sozinha:**
  motivado por um problema real do dono — venda que cai depois das 8:30
  (quando ele já parou de checar a tela) só é vista tarde demais pra repor
  com o fornecedor no mesmo dia. `job_alerta_pos_horario` (`bot_telegram.py`,
  `JobQueue.run_repeating` a cada 5 min) percorre todas as contas e avisa —
  uma vez por envio — quando surge um envio novo já `ready_to_print` com
  despacho hoje; independente do botão Atualizar da tela. Dedup por
  `shipment_id` em `alertas_pos_horario.json` (reseta sozinho na virada do
  dia); isola falha por conta. `_dados_alerta_da_conta` faz a checagem e o
  detalhe dos itens NUM SÓ bloco de troca de conta (evita bug sutil de conta
  errada — `definir_conta` mexe em globais compartilhadas com o resto do
  bot). `separador_gui.py`, ao abrir, sobe o bot sozinha sem janela visível
  (`core.iniciar_bot_em_segundo_plano`, lock de PID em `bot.lock` checado
  contra o processo de verdade via `tasklist`) se ainda não estiver rodando
  — decisão do dono, que deixa a tela sempre aberta. Nós semânticos novos
  `bot_alerta_pos_horario` e `bot_segundo_plano_junto_com_tela` (concept),
  ligados por `rationale_for` às funções centrais e por
  `conceptually_related_to` entre si e ao `job_bom_dia` (mesmo padrão de
  `JobQueue`). Contagens: **1393 nós, 2537 arestas, 0 órfãs**.

- **2026-07-24 — Ads camada 4: narrativa opcional via IA (`narrar.py`):**
  motivada por um monitor irmão do mesmo Product Ads construído em paralelo
  pelo dono em n8n + DeepSeek (narrativa por IA + entrega automática de
  relatório); ao comparar os dois, decisão explícita foi manter papéis
  diferentes (n8n = narrativa/apresentação/entrega; `ads-monitor/` =
  histórico canônico + regras + SKU), mas trazer a narrativa também pra este
  lado, por cima do motor já existente (camada 3). `narrar.py` é aditivo e
  opcional: nunca altera `recomendar.py`, só narra em português o que ele já
  calculou (recomendações + campanhas "monitorando"), via `claude -p`
  (subprocess, mesmo padrão do `api-monitor/run-semanal.ps1` — sem
  credencial de LLM nova). Prompt com regras equivalentes ao motor: nunca
  concluir margem/lucratividade, nunca sugerir mudança automática, preservar
  "condicionada à validação da margem" tal como veio calculado. Se `claude`
  faltar/travar/falhar, devolve vazio e sai com aviso — nunca finge sucesso,
  e as camadas 1-3 continuam funcionando sozinhas. Nó semântico novo
  `ads_monitor_narrar_camada4` (concept), ligado por `rationale_for` ao
  módulo e às 4 funções centrais (`montar_dados`, `montar_prompt`,
  `chamar_claude`, `main`) e por `conceptually_related_to` à camada 3
  (`ads_monitor_motor_recomendacao_sem_margem`) e ao `api_monitor_sistema`
  (mesmo padrão de uso do `claude -p`). Contagens: **1344 nós, 2462 arestas,
  0 órfãs**.

- **2026-07-23 — Ads camada 3: motor de recomendação (sinais sem margem):**
  `ads-monitor/recomendar.py` lê `campanhas_diarias` numa janela de dias e gera
  recomendações no formato do pedido original (problema/evidência/ação/
  justificativa/impacto/risco/confiança/urgência/prazo de reavaliação/métrica
  de verificação), usando só os 3 sinais que a própria API já calcula e não
  dependem de margem (orçamento insuficiente, ranking baixo, ROAS abaixo do
  `roas_target`). Recomendação de aumentar investimento sai marcada
  "condicionada à validação da margem"; ROAS abaixo do alvo não (é redução de
  risco, não aposta). Trava contra recomendar em dado fraco: `MIN_DIAS=3` +
  `MIN_CLICKS=20` na janela — `avaliar_campanha()` é função pura, testada
  isoladamente. Construído **depois** do agendamento diário (PR #176) ficar
  pronto — sem coleta automática, `MIN_DIAS` nunca seria atingido
  organicamente. Nó semântico novo `ads_monitor_motor_recomendacao_sem_margem`
  (concept), ligado por `rationale_for` às 3 funções centrais e por
  `conceptually_related_to` às camadas 1/2. Contagens: **1319 nós, 2415
  arestas, 0 órfãs**.

- **2026-07-23 — Resolução de SKU via seller_sku real (não mais só best-effort):**
  achado com dado real: a resolução de SKU do `ads-monitor` (camada 2) dava
  **0/468 itens resolvidos** — `skus_por_anuncio.json` é um mapa manual pequeno
  (só p/ anúncios sem SKU adotados na tela), não um resolvedor geral; a maioria
  dos produtos tem `seller_sku` cadastrado direto no anúncio, sem cache local
  pra isso. Corrigido estendendo `_detalhe_item`/`itens_cache.json` do núcleo
  (`separador_etiquetas_ml.py`) com o campo `seller_custom_field` (mesma
  chamada `GET /items/{id}` já feita, sem custo extra de rede) e nova função
  `_resolver_skus` no coletor, que prioriza esse `seller_sku` real e só cai
  pro mapa de adoção quando ausente — mesma prioridade de `identidade()` no
  núcleo. Trata cache staleness (entrada antiga sem a chave `seller_sku` é
  refeita, não assumida "sem SKU"). Nó semântico `ads_monitor_ad_group_atribuicao`
  atualizado (texto + aresta `rationale_for` corrigida para
  `ads_monitor_coletar_resolver_sku_adocao`, que ficou pendurada no módulo
  após o rename `_resolver_sku` → `_resolver_sku_adocao`; nova aresta pra
  `_resolver_skus`). Contagens: **1287 nós, 2362 arestas, 0 órfãs**.

- **2026-07-23 — Ads camada 2: atribuição por ad_group/item dentro da campanha:**
  estende `ads-monitor/coletar.py` com a cadeia campanha -> ad_group -> item_id ->
  SKU (2 tabelas novas: `ad_groups_diarios`, `ad_group_itens_diarios`), usando o
  fluxo NOVO por `ad_group_id` (substituiu o endpoint de métricas por item,
  descontinuado em 27/05/2026 — doc "Product Ads para Catálogo e User Products").
  Validado antes com chamada real de leitura em `tools/diag_ads.py` (PR #167/#168).
  Só resolve item_id dos ad_groups com atividade no dia (poupa chamada); SKU é
  best-effort via `skus_por_anuncio.json` local, sem chamar a Items API. Construído
  **antes** de existir fonte de margem por SKU (decisão explícita do dono — "podemos
  construir a implementação mesmo sem as fontes, acrescentamos depois"; ver
  `docs/PRIORIDADES_TECNICAS.md` item 10). Nó semântico novo
  `ads_monitor_ad_group_atribuicao` (concept), ligado por `rationale_for` às 4
  funções novas e por `conceptually_related_to` a `ads_monitor_coletor_camada1`.
  Contagens: **1280 nós, 2351 arestas, 0 órfãs**.

- **2026-07-23 — Coletor determinístico do Product Ads (`ads-monitor/coletar.py`):**
  camada 1 do futuro monitor de Mercado Ads — grava snapshot diário das métricas de
  campanha por conta num SQLite local (sem motor de recomendação/margem ainda). Só
  leitura (GET), reusa `obter_token`/`definir_conta` do núcleo (mesma trava
  entre processos), idempotente por `(dia, conta, campaign_id)`, isola falha por
  conta. O `graph_sync --update` incluiu os nós AST do coletor e dos 15 testes
  novos (`tests/test_ads_monitor_coletar.py`); adicionado à mão o nó semântico
  `ads_monitor_coletor_camada1` (concept), ligado por `rationale_for` a
  `coletar_conta`/`salvar_campanha`/`buscar_advertiser` e por
  `conceptually_related_to` a `graph_sync_processo`/`api_monitor_sistema`.
  Contagens: **1262 nós, 2314 arestas, 0 órfãs**.

- **2026-07-22 — Base de conhecimento `obsidian/` + validador:** reorganização do cofre
  (camada de contexto humano; seção `IA/` de onboarding para agentes) e novo
  `tools/validar_obsidian.py` (+ testes). O `graph_sync --update` incluiu os nós AST do
  validador; adicionados à mão os nós semânticos `obsidian_base_conhecimento` (concept) e
  `validar_obsidian_ci` (rationale), ligados a `graph_sync_processo`/`api_monitor_sistema`.
  Contagens: **1215 nós, 2224 arestas, 0 órfãs**.

- **2026-07-22 — Auditoria completa + re-sincronização do grafo (AST 125 commits
  defasada):** a camada AST estava congelada em `5233aef` (2026-07-08); de lá até
  `f1dd2d0` (HEAD) 125 commits mexeram no código (módulos novos `estado.py`,
  `historico.py`, `registro.py`, `api-monitor/`, dezenas de funções/testes novos).
  Criado **`tools/graph_sync.py`** — reconciliador que re-deriva a camada estrutural
  e **preserva a semântica** por IDs estáveis. Aplicado: **+239 nós, −3 nós**
  (renomeações de teste), **405 localizações corrigidas**, `calls`/`imports_from`
  reconciliados (sem reconstrução destrutiva), **0 aresta órfã**. Camada semântica
  preservada 100% (todos os 306 `rationale_for` resolvem). Conhecimento novo:
  nós `api_monitor_sistema` (concept — monitor semanal das APIs) e
  `graph_sync_processo` (rationale — o modelo de manutenção em 2 camadas) +
  hyperedge `graph_manutencao`. Emitido **`graphify-out/semantic.json`** (backup
  durável da camada manual) e **`tests/test_graphify_sync.py`** (guarda no CI).
  `graph.html` fica defasado (pendência: só o CLI regenera).

- **2026-07-22 — Resumo do dia: impressão = soma por produto em PDF (ordem Nomes):**
  a impressão que interessa é a **soma por SKU** (lista de produção,
  `A01 - 2L 110 - 5`), consolidando todas as contas ML + Shopee — `linhas_consolidado`
  + `gerar_pdf` (PDF em Python puro, sem dependência). Saída em **PDF** no lugar do
  `.txt` (que gastava folha). Tela e consolidado seguem a **ordem da aba Nomes**
  (`resumo_do_dia(ordem=...)`). Nós: `historico_linhas_consolidado`,
  `historico_gerar_pdf`, rationale `resumo_soma_por_produto`.

- **2026-07-22 — Resumo do dia (histórico de impressão por dia de ação):** módulo
  novo `historico.py` (registro com carimbo de tempo + `resumo_do_dia`/
  `formatar_resumo`). O estado é por dia de despacho e não sabe QUANDO a etiqueta
  saiu; o histórico responde "o que imprimi hoje". Hook único via callback
  `registrar` de `estado.marcar_impresso`, que recebe **só o delta** (ids novos) —
  reimpressão não conta em dobro; cobre GUI, bot e CLI. Best-effort (fora da trava
  do estado, nunca levanta). GUI: botão 📋 Resumo do dia (`JanelaResumo`, só
  leitura) + salvar `.txt`. Nós: `historico` (+`registrar`/`resumo_do_dia`/
  `formatar_resumo`), `separador_gui_separadorapp_abrir_resumo_dia`,
  `separador_gui_janelaresumo`, rationale `historico_dia_de_acao`.

- **2026-07-21 — Desempenho do "Atualizar" ML (medir + acelerar sem risco):** a
  fase cara é o filtro de envios (`filtrar_para_imprimir`, uma chamada
  `GET /shipments/{id}` por pedido não-terminal); ficou mais lento com o tempo
  porque `envios_cache.json` só guarda status **terminais** — pedido `paid` ainda
  não `ready_to_print` é re-consultado a cada Atualizar e cresce com o volume da
  janela `DIAS_JANELA=30`. Feito: filtro 12→**20 workers** e `coletar_grupos` loga
  cada fase (checados vs. cache_hits, via `stats` opcional) em `ml_tempos.log`
  (`_log_tempos` do núcleo, gitignorado; espelha o da Shopee). Adiado (área de
  risco, `PRIORIDADES_TECNICAS #8`): cache de TTL curto para não-prontos. Nós:
  `ml_atualizar_desempenho` (rationale), `separador_etiquetas_ml_log_tempos`.

- **2026-07-15 — Persistência pós-confirmação tolerante (revisão P2):** falha ao
  gravar o estado depois do "sim" não estoura mais o callback do Tk nem passa em
  silêncio — `_marcar_lote_tolerante` (puro, testável sem display) oferece
  Repetir, isola a falha por grupo e o aviso deixa claro "impressas, mas NÃO
  marcadas — não reimprima". Nós `separador_gui_marcar_lote_tolerante` +
  `gui_persistencia_pos_confirmacao`.

- **2026-07-15 — Resumo do bot respeita a loja ativa (revisão P2):**
  `_exec_resumo(context)` consulta a loja do chat (Shopee via `contagem_por_dia`
  da mesma busca; ML pelo caminho original), título identifica a loja e a
  mensagem "Consultando…" usa a loja ativa. Nó `bot_resumo_por_loja`.

- **2026-07-15 — AWB na impressão parcial une, não substitui (revisão P2):**
  imprimir os faltantes de um grupo parcial apagava da tela os códigos antigos
  (referência do operador) até a próxima coleta. Nós `shopee_api_somar_rastreios`
  (união sem duplicar, ordem estável) + `awb_uniao_parcial` (rationale).

- **2026-07-16 — Editores instância única + travados na operação (auditoria
  consolidada 5.5):** `EditorNomes`/`EditorSkusAnuncio` são editores de
  substituição total (a ordem é a ordem de separação — não dá para mesclar); abrir
  dois clobbava. Agora um 2º clique foca a janela aberta (`_focar_editor_aberto`),
  os botões ficam desabilitados durante `ocupado`, e `_atribuir_sku`/`_fechar` do
  EditorNomes checam `ocupado` para não mutar `self.grupos` no meio da impressão.
  Nós `separador_gui_separadorapp_focar_editor_aberto` (code) +
  `editores_instancia_unica` (rationale).

- **2026-07-20 — Contrato do app Zebra v1.25.7 + temporário `tmp_*.part`:**
  verificação de compatibilidade com o app externo atualizado (doc do dono):
  duplicata por nome+tamanho+mtime, decode UTF-8 `errors=ignore`, "Parar"
  descarta a fila, fila interna de 200 — tudo sem conflito com o separador
  atual (nomes únicos, reimpressão gera arquivo novo, carimbo `^CI28`/`^CI0`
  já no formato recomendado). Única correção: o temporário antigo
  (`nome.zip.tmp`) começava com prefixo aceito pelo monitor; `tmp_saida` grava
  como `tmp_{nome}.part` (não casa prefixo nem extensão vigiada), com
  teste-guardião. **Compatibilidade confirmada pelos dois lados em 20/07**
  (resposta formal do Zebra): filtro por extensão garantido estável; a
  separadora do Zebra mantém `^CI28` persistente de propósito (inócuo). Nós
  `separador_etiquetas_ml_tmp_saida` (code) + `zebra_contrato_v1257`
  (rationale).

- **2026-07-16 — Trava de ponta a ponta na impressão (anti-duplicata Shopee/ML):**
  a etiqueta Shopee sai fisicamente durante a busca (ZIP→Downloads→Zebra), mas o
  estado só é marcado após "saíram certo?"; `_confirmar_e_marcar` reabilitava os
  botões antes da confirmação → um 2º clique no intervalo reimprimia o mesmo lote.
  Agora o app fica `ocupado` do "Organizar envio" até a confirmação
  (`imprimir_lotes`/`imprimir` ocupam antes; `_ocupar(False)` só no `finally` de
  `_confirmar_e_marcar`, que delega o corpo a `_confirmar_e_marcar_corpo`). Nós
  `separador_gui_separadorapp_confirmar_e_marcar_corpo` (code) +
  `trava_impressao_ponta_a_ponta` (rationale).

- **2026-07-16 — `config.json` atualizado por chave, sob trava (auditoria
  consolidada 5.4):** cada GUI regravava o dicionário inteiro a partir de um
  `self.config` velho — a última gravação revertia em silêncio as chaves de
  outra instância. `atualizar_config(**chaves)` relê o disco sob `estado.trava`,
  aplica só as chaves do evento e saneia; os 6 pontos da GUI passaram a persistir
  por chave. Nós `separador_etiquetas_ml_atualizar_config` (code) +
  `config_por_chave` (rationale).

- **2026-07-16 — Lote de higiene/endurecimento P3 (auditoria consolidada):**
  5.8 divisória fecha com `^CI0` (nós `divisoria_reset_ci0`); 5.7 Shopee poda o
  disco (`persistir_poda=True`, nó `shopee_poda_disco`); 5.9 `gerar_etiqueta`
  valida o AWB de todos os `order_sns` e rejeita lista vazia
  (`gerar_etiqueta_valida_todos`); 5.11 `sem_segredos` cobre a forma JSON +
  `client_secret`/`partner_key` (`sem_segredos_json`); 5.13 `ruff` no CI
  (`ci_ruff_lint`, config `ruff.toml` F+E9); 5.15 o screenshot usa
  `subprocess.run` em vez de `os.system` (sem nó — hardening de ferramenta de
  dev). 0 arestas órfãs.

- **2026-07-16 — Shopee já organizado sem AWB aguarda em vez de falso-errar
  (auditoria consolidada 5.3):** `envio_ja_arranjado` existia e era testado mas
  **sem chamador de produção** — a falta de uso era o bug. `organizar_envio`
  passou a consultá-lo: se o envio já está arranjado (info_needed sem
  pickup/dropoff/non_integrated), pula o `ship_order` e só aguarda o AWB, em vez
  de recusar `info_needed={}` como "não oferece drop-off". Nó
  `shopee_organizado_sem_awb` (rationale) + aresta `calls`
  `organizar_envio → envio_ja_arranjado`.

- **2026-07-16 — Estado corrompido preservado, não sobrescrito (auditoria
  consolidada 5.2):** `ler_json` silenciava corrupção como `{}` (indistinguível
  de ausente) e a próxima marcação gravava por cima, destruindo o recuperável.
  `ler_estado` move o corrompido para `.corrupto` (com aviso) e recomeça vazio;
  distingue ausência (`{}` silencioso) e falha transitória (OSError → `{}` sem
  renomear). Usado por `carregar` e pelo `ler` injetado no `marcar_impresso` do
  núcleo e da Shopee. Nós `estado_ler_estado` (code) +
  `estado_corrompido_visivel` (rationale).

- **2026-07-16 — ZIP com nome único + releitura de estado antes de gerar
  (auditoria consolidada 5.1):** o nome determinístico do ZIP + `tmp.replace`
  apagava em silêncio um lote que o monitor da Zebra ainda não consumira (dois
  trabalhos com o mesmo rótulo escreviam no mesmo arquivo); `nome_saida_unico`
  (núcleo; a Shopee chama `core.nome_saida_unico`) anexa um carimbo único ao
  nome, preservando o prefixo que o monitor casa, e soma `-1`/`-2` na colisão.
  A GUI ainda relê o estado do disco antes de gerar (não imprime em dobro o que
  foi marcado por fora). Nós `separador_etiquetas_ml_nome_saida_unico` (code) +
  `zip_nome_unico_pendencia_disco` (rationale).

- **2026-07-16 — Poda do cache de AWB independente de `novos` (P2 da releitura
  externa):** a poda só persistia quando um cache miss trazia AWB novo — no
  regime normal pós-cache (tudo hit) nunca rodava e o arquivo cresceria para
  sempre. Poda a cada coleta; regrava só se mudou. Teste que falha no código
  antigo. Também corrigido o mapa do código (§7 do relatório): o bot é
  consulta ML/Shopee + impressão só do ML, não "somente leitura". Nó
  `awb_cache_poda_sempre`.

- **2026-07-16 — Trava do refresh com espera calibrada no Windows (P1 da
  releitura técnica externa):** o `msvcrt.LK_LOCK` desiste em ~10s, mas o
  refresh roda HTTP de até 30s dentro da trava — no Windows o 2º processo
  degradava **no meio** do refresh do 1º (refresh paralelo; POSIX/CI bloqueia
  indefinidamente e nunca pegaria). `trava(espera=)` re-tenta apenas quando a
  falha é lenta (~10s = ocupada; rápida = FS sem suporte → degrada na hora) até
  superar `2×TIMEOUT`; degradar depois disso é seguro (o detentor já salvou).
  Lógica testada com msvcrt+relógio fakes (4 cenários) + espiões da `espera`
  nos dois `obter_token`. Nó `trava_espera_windows`.

- **2026-07-16 — Cache de AWB da Shopee (backlog da auditoria):** os códigos de
  rastreio da tela eram re-buscados a cada Atualizar (N chamadas) e uma busca
  falha sumia da lista sem aviso (conferência contra lista incompleta). AWB é
  imutável → cacheado na impressão (`_cachear_awbs` em imprimir_grupo/lotes),
  lido cache-first em `preencher_rastreios` (só os ausentes vão à rede), podado
  junto com o estado. Nós `shopee_api_cachear_awbs` + `shopee_awb_cache`;
  fixture autouse isola o cache nos testes (a impressão agora grava nele).

- **2026-07-16 — Seletor de dias com reflow / teclado do bot fatiado (backlog
  da auditoria):** GUI `_reflow` quebra os chips de dia em linhas (nada
  cortado, verificado a 460/580px); `_teclado_grupos` devolve lista de teclados
  ≤90 botões (limite do Telegram). Nós `seletor_dias_reflow`, `bot_teclado_fatiado`.

- **2026-07-16 — Lote de higiene da auditoria:** migração de conta leva o
  `.bak` junto e remove órfãos da raiz (nó `migracao_bak_zumbi` — a cadeia
  completa: `.bak` desgarrado tem refresh morto → auto-recuperação ressuscita
  um `credenciais.json` zumbi → refresh inválido + prompt de migração em
  loop); CLI Shopee com estado real e contagem de pedidos (não itens); bot
  redige também os erros esperados; pins de dependência (`requests<3`,
  `python-telegram-bot<23`); limitação "Sem data reabre na virada do dia"
  documentada como decisão na ARQUITETURA (mexer na chave de estado colidiria
  com a poda — só se o caso aparecer na operação real).

- **2026-07-16 — Refresh de token sob trava entre processos (achado da
  auditoria):** a releitura do disco não fechava a janela de GUI e bot
  chegarem **simultâneos** sem token válido — dois refreshes, o 2º com
  refresh_token já rotacionado (a corrida temida de travar a conta). O ciclo
  relê-ou-renova do `obter_token` (ML e Shopee) agora roda sob `estado.trava`
  ao lado das credenciais; quem espera adota o token salvo. 3 testes novos
  (2 determinísticos + 1 de concorrência real com flock) que falham no código
  antigo. Nó `token_refresh_trava_processos` (liga os dois `obter_token` e a
  `estado_trava`). Aprendizado de teste: a fixture `core` neutraliza o
  `time.sleep` do módulo `time` inteiro — testes de ordenação por sleep devem
  dispensá-la ou usar sequenciamento determinístico.

- **2026-07-16 — Interface de provedor sem `imprimir_grupo` (achado da
  auditoria):** os 4 métodos eram código morto (GUI usa só `imprimir_lotes`;
  bot/CLI usam as funções de módulo) e marcavam estado direto — risco latente
  à invariante 1. Removidos do código E do grafo (5 nós + 10 arestas do
  inventário AST, mantendo-o em dia); nó de decisão novo
  `provedor_sem_imprimir_grupo` + teste-guardião.

- **2026-07-16 — SKU só de espaços cai no fallback do anúncio (achado da
  auditoria, provado dinamicamente):** o `if sku` de `identidade()` testava
  antes do strip — whitespace virava chave/nome vazios. Strip antecipado; o
  caso vira "anúncio sem SKU" normal (adotável pelo mapa). Nó
  `identidade_sku_whitespace`.

- **2026-07-16 — Aviso da manhã blindado (achado da auditoria):** `job_bom_dia`
  era o único ponto do bot que enviava exceção crua ao chat (sem `sem_segredos`
  — hoje só-ML, sem segredo na URL; viraria vazamento se o aviso incluir a
  Shopee) e uma falha de envio num chat calava os demais. Redigido + isolado
  por chat. Nó `bot_aviso_blindado`; validado com stub do telegram (o pacote
  real não importa neste ambiente — os testes rodam no CI).

- **2026-07-16 — Config saneado na abertura (achado da auditoria):** provado
  com a GUI real (headless) que `modo_identificacao` desconhecido,
  `marketplace`/`conta_ativa` de tipo errado e `geometria` malformada
  derrubavam a GUI/bot na inicialização — sem mensagem com o pythonw do
  atalho. `aplicar_config` agora saneia (`_sanear_config`: valor inválido cai
  no default) e a GUI tolera geometria inválida. Os 8 casos da prova reabrem.
  Nós: `separador_etiquetas_ml_sanear_config` + `config_saneado_na_abertura`.

- **2026-07-16 — ProvedorML revalida o token ao imprimir (achado da auditoria):**
  os caminhos de imprimir/reimprimir usavam `self.token` cru da última coleta,
  sem checar a validade (~6h) — GUI aberta por horas → 401 repetido até um novo
  Atualizar. Novo `_token_atual()` revalida via `obter_token` (só renova quando
  preciso). Ambas (`_token`) e Shopee já revalidavam. Nós:
  `provedores_provedorml_token_atual` + `provedor_ml_token_revalidado`.

- **2026-07-16 — Adoção inline no modo Ambas re-coleta (achado da auditoria):**
  a auditoria completa provou (teste dinâmico) que o botão 🏷 Atribuir SKU em
  modo 🌐 Ambas, aplicado em memória, não reescrevia os sub-grupos `.por_conta`
  — envios de uma conta sumiam do lote e a marcação caía na chave antiga do
  anúncio (grupo voltava pendente na coleta seguinte → reimpressão). Novo
  `_aplicar_adocao` roteia: ML normal em memória (como era), Ambas re-coleta.
  Nós novos: `separador_gui_separadorapp_aplicar_adocao` (código) e
  `ambas_adocao_recoleta` (barreira→solução). Testes em `test_gui_adocao.py`
  (roteamento + primeira cobertura do `_aplicar_mapa_anuncios_local`).

- **2026-07-16 — Poda por idade também sob a trava (follow-up da revisão P1):**
  auditoria pós-merge achou uma porta lateral da corrida da trava — a regravação
  da poda em `carregar(persistir_poda=True)` (Atualizar do ML) escrevia FORA da
  trava e podia apagar uma marcação que o bot gravasse nesse meio-tempo. Agora a
  poda roda sob `estado.trava` relendo o disco antes de gravar. Nó novo:
  `estado_poda_sob_trava` (barreira→solução, liga `estado_carregar`+`estado_trava`).
  Teste determinístico que falha no código antigo e passa no novo.

- **2026-07-15 — Trava entre processos no estado (revisão P1):** o merge do
  `marcar_impresso` só cobria o caso sequencial; leituras simultâneas (tela+bot)
  perdiam marcação (reproduzido: 6 marcações concorrentes → 1). Nós novos:
  `estado_trava` (função `trava()`, `.lock` + msvcrt/fcntl, degradação suave) e
  `estado_trava_processos` (barreira→solução). O `.tmp` do `gravar_json` inclui o
  PID (dois processos não disputam o temporário).

- **2026-07-15 — Falha de transporte da Shopee não vaza token (revisão P1):**
  `_rede_limpa` converte exceções cruas do requests (que carregam a URL assinada)
  em `SeparadorError` limpo com `from None` (traceback encadeado cortado);
  defesa em profundidade com `sem_segredos` nos limites (GUI e bot). Nó
  `shopee_transporte_sem_token`, ligado a `shopee_erro_sem_token` (o fix
  anterior, que cobria só o erro HTTP com resposta).

- **2026-07-14 — Adoção de anúncio aplicada em memória:** o botão inline 🏷
  Atribuir SKU passou a aplicar na hora (`_aplicar_mapa_anuncios_local`: reescreve
  a chave e funde por SKU+qtd), sem re-buscar na API — não precisa clicar em
  Atualizar. A janela gerenciadora segue re-coletando ao fechar (remoções/edições
  precisam refazer a identidade). Nó `anuncio_adocao_em_memoria`.

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