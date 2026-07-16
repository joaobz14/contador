# Changelog

Histórico das principais mudanças do projeto.

## [Não lançado]

### Interface
- **Seletor de dias quebra em linha em vez de cortar** (achado da auditoria):
  numa janela estreita (ou com contagens de 2+ dígitos) o 5º dia útil sumia à
  direita. Agora os chips de dia reposicionam em várias linhas conforme a
  largura (`_reflow`) — nenhum dia fica invisível, em qualquer tamanho de
  janela. Verificado por screenshot headless a 460px e 580px.

### Separação e identificação
- **Ordem de separação pessoal por SKU:** a tela e a impressão seguem a ordem
  da aba **Nomes** no bloco "Quantidade por pedido = 1" (`ordenar_grupos`), com
  setas ↑/↓ no editor de Nomes para reordenar. Os blocos de 2+ unidades
  continuam agrupados como antes; SKU sem nome cadastrado vai para o fim em
  ordem natural (`A2` antes de `A10`).
- **Carimbo do nome com acentos:** o campo do nome na DANFE do ML passa a ser
  envolto por `^CI28`…`^CI0` (UTF-8) — nomes como "FOGÃO" saem corretos na
  Zebra (antes os acentos embolavam). Cirúrgico: não afeta a nota fiscal acima
  nem vaza encoding para a etiqueta de envio.
- **Nomes por SKU:** ordem inicial dos SKUs mais usados no topo do
  `nomes_sku.json` + novos produtos cadastrados. A ordem das chaves passou a
  ser **preservada** (é a ordem de separação, não alfabética).
- **Códigos de rastreio de todos os grupos Shopee (não só os de 1 etiqueta):**
  como a etiqueta Shopee não tem o nome do produto, a tela lista o **código
  (AWB) de cada etiqueta já impressa** do grupo, alinhado à esquerda embaixo do
  nome — para conferir qual etiqueta é qual produto ao separar o lote. Em grupos
  de alto volume a área cresce em altura (não espreme). Pendentes não mostram
  código (o AWB só existe depois de organizar/imprimir o envio).
- **Códigos de rastreio (AWB) da Shopee agora vêm de um cache confiável**
  (achado da auditoria): a tela re-buscava o AWB de cada etiqueta impressa a
  cada Atualizar (N chamadas), e uma busca que falhasse (timeout/rate-limit)
  sumia da lista **sem aviso** — o operador conferia contra uma lista
  incompleta sem saber. Agora o AWB (imutável depois de emitido) é **cacheado
  no momento da impressão**; a coleta seguinte lê do cache (menos rede) e os
  códigos são confiáveis (vêm da impressão, não de um refetch falível). Só os
  ausentes vão à rede; o cache (`awb_cache_shopee.json`, local) é podado junto
  com o estado.
- **Impressão parcial não apaga mais os códigos antigos** (achado P2 da revisão
  técnica): imprimir os faltantes de um grupo parcial substituía a lista de
  rastreios da tela pelos recém-impressos, sumindo com os códigos antigos até a
  próxima coleta. Agora `_somar_rastreios` **une** (sem duplicar, preservando a
  ordem).
- **Anúncio com SKU só de espaços não vira mais grupo sem nome** (achado da
  auditoria): um `seller_sku` de whitespace virava chave/nome **vazios** (linha
  sem rótulo na tela, estado sob `dia||q1`). Agora é tratado como anúncio sem
  SKU — cai no código do anúncio e pode ser adotado pelo de-para normalmente.
- **Adotar anúncios ML sem SKU num SKU do sistema:** anúncios antigos sem
  `seller_sku` apareciam pelo título e carimbavam o código do anúncio (MLB…).
  Agora um de-para **`skus_por_anuncio.json`** (versionado) mapeia o código do
  anúncio → SKU, e o anúncio passa a **agrupar/ordenar/carimbar/nomear igual** a
  esse SKU. Editável na GUI de dois jeitos: botão **🏷 Atribuir SKU** no próprio
  grupo sem SKU (à esquerda, embaixo do nome) e uma **janela gerenciadora**
  (**🏷 SKUs** na barra) para adotar os anúncios da tela e editar/remover os
  mapeamentos salvos. O botão inline **aplica na hora, em memória** (funde os
  grupos sem re-buscar na API — não precisa clicar em Atualizar); a janela
  gerenciadora re-coleta ao fechar (por causa das remoções/edições).
- **Adotar SKU pelo botão inline no modo 🌐 Ambas re-coleta em vez de aplicar
  em memória** (achado da auditoria): os grupos fundidos do Ambas carregam
  sub-grupos por conta que a aplicação em memória não reescrevia — envios de
  uma conta ficavam invisíveis para a impressão em lote e a confirmação
  marcava o estado na chave antiga do anúncio (na coleta seguinte o grupo
  voltava como pendente, com risco de reimpressão). No ML normal o botão
  continua instantâneo (em memória), agora com testes.

### Arquitetura interna
- **Camada comum de estado (`estado.py`):** a lógica de "já impresso" (antes
  duplicada entre núcleo e Shopee) virou um módulo-folha, com IO JSON atômico.
  O núcleo e o `shopee_api` passam a usar wrappers finos que injetam o próprio
  `salvar_estado` — sem reimplementar o merge.
- **Contrato de impressão da GUI explícito:** métodos renomeados
  (`_gerar_sem_marcar_thread`, `_confirmar_e_marcar`) deixam claro o fluxo
  **gera → confirma fisicamente → marca**, que é a invariante nº 1.
- **DRY do retry HTTP:** `_com_retry` unifica a lógica de re-tentativa de
  GET/POST no núcleo; remoção de imports mortos.
- **Interface de provedor sem `imprimir_grupo`** (achado da auditoria): os
  quatro métodos eram código **morto** (a GUI imprime tudo por
  `imprimir_lotes`; bot/CLI usam as funções de módulo) e **marcavam estado
  direto** — se um botão novo os chamasse, furaria a invariante nº 1 (grupo
  constaria impresso sem confirmação física). Removidos, com teste-guardião
  que impede o método de voltar.

### Segurança
- **Erro da Shopee não vaza mais o token:** os erros HTTP da Shopee passam por
  `_levantar_se_erro` (em vez de `raise_for_status`), que carregava a URL
  assinada com `access_token`/`sign` para o log, a tela e o chat do bot.
- **Falha de transporte da Shopee também não vaza o token** (achado P1 da
  revisão técnica): queda de conexão/timeout gerava exceção crua do requests com
  a URL assinada inteira ("Max retries exceeded with url: …access_token=…"),
  que chegava à tela, ao `bot.log` (traceback) e ao chat do Telegram. Agora
  `_rede_limpa` converte em erro limpo (com `from None`, cortando o traceback
  encadeado) em `_get_shop`/`_post_shop`/`_download_shop`/`renovar_token`; e,
  como defesa em profundidade, a GUI e o bot redigem com `sem_segredos` tudo o
  que mostram/enviam.
- **Refresh de token robusto:** `obter_token` relê o disco dentro do lock,
  protegendo contra corrida de refresh **entre processos** (GUI + bot na mesma
  conta); `renovar_token` não re-tenta (o `refresh_token` rotaciona e é de uso
  único — re-tentar travaria a conta).
- **Refresh de token serializado também ENTRE PROCESSOS** (achado da
  auditoria): a releitura do disco fechava quase toda a janela, mas se GUI e
  bot chegassem **simultaneamente** sem token válido, os dois renovavam — e o
  segundo mandava um refresh_token já rotacionado (a corrida que pode travar a
  conta). Agora o ciclo relê-ou-renova roda sob a **trava de arquivo**
  (`estado.trava`, a mesma do estado) ao lado das credenciais: quem chega
  depois espera e **adota** o token salvo pelo primeiro. Degrada suave (sem
  trava, comportamento anterior). Vale para ML e Shopee.

### Diagnóstico
- **Log operacional (`separador.log`, via `registro.py`):** a GUI registra
  loja/conta/dia, contagens, confirmação (sim/não) e falhas — para diagnóstico
  sem debugger. Nunca atrapalha a operação (defensivo) e **nunca loga segredos**
  (redação por `sem_segredos`).

### Bot do Telegram
- **Teclado de impressão fatiado no limite do Telegram** (achado da auditoria):
  num dia com muitos grupos, o teclado de botões "Imprimir" passava de ~100
  botões e o Telegram recusava o envio — o teclado simplesmente não aparecia.
  Agora os botões são fatiados em vários teclados (≤ 90 cada), sem deixar
  cabeçalho de quantidade órfão no fim de um teclado; os índices dos botões
  continuam apontando para a lista guardada (nada muda no que se imprime).
- **Aviso da manhã blindado** (achado da auditoria): o texto de falha ao montar
  o aviso agora passa por `sem_segredos` antes de ir pro chat (fecha o último
  ponto do bot que enviava exceção crua), e uma falha de envio num chat (ex.:
  bot bloqueado) não cala mais o aviso dos demais chats.
- **Resumo respeita a loja ativa** (achado P2 da revisão técnica): com a Shopee
  selecionada, o `/resumo` (e o botão 📊 Resumo) trazia dados do **Mercado
  Livre**. Agora consulta a loja do chat (Shopee usa a `contagem_por_dia` da
  mesma busca, sem rede extra), o título do resumo **identifica a loja** e a
  mensagem "Consultando…" também usa a loja ativa.
- **Reinício automático:** lançador `Iniciar Bot (auto).bat` que religa o bot
  sozinho se ele cair (erro/queda de rede), em vez de ficar fora do ar. No modo
  automático o bot não pausa pedindo Enter (`BOT_SEM_PAUSA`); o motivo da queda
  fica no `bot.log`.
- Impressão pelo bot: botão **🖨 Imprimir** por grupo nas listagens, com
  confirmação (Confirmar/Cancelar) antes de gerar a etiqueta. Reaproveita
  `imprimir_pendentes` do núcleo (imprime só os pendentes e marca o estado).
- O bot passa a aplicar a config do núcleo (`aplicar_config`): usa a **conta
  ativa** e respeita o `carimbar_sku` do `config.json`, igual à tela.
- **Multi-conta no bot:** comando `/conta` para ver/trocar a conta ativa pelo
  Telegram (com 2+ contas) e fallback para a primeira conta quando a salva
  some/é inválida (antes o bot caía no `credenciais.json` da raiz e falhava).
  A impressão recusa grupos de uma conta diferente da ativa (evita imprimir
  com o token errado depois de trocar de conta).

### Robustez
- **Migração de conta leva o `credenciais.json.bak` junto** (achado da
  auditoria) e remove um `.bak` órfão deixado na raiz por migrações antigas:
  um `.bak` desgarrado guarda um refresh_token **já rotacionado** (morto) — a
  auto-recuperação poderia um dia "restaurar" um `credenciais.json` zumbi na
  raiz (refresh inválido + o prompt de migração voltando a cada abertura).
  Um par completo (principal + `.bak`) na raiz nunca é apagado.
- **`config.json` com valor inválido não impede mais o app de abrir** (achado
  da auditoria): um `modo_identificacao` desconhecido, `marketplace`/
  `conta_ativa` de tipo errado ou `geometria` malformada derrubavam a GUI (e o
  bot) na inicialização — e com o atalho normal (pythonw, sem console) o app
  simplesmente "não abria", sem mensagem. Agora `aplicar_config` **saneia** o
  config (valor inválido cai no padrão, como se a chave não existisse) e a GUI
  tolera geometria inválida. Config ausente/corrompido já era bem tratado.
- **Imprimir com a tela aberta há horas não falha mais por token vencido**
  (achado da auditoria): o Mercado Livre imprimia com o token guardado na
  última coleta, sem checar a validade (~6h) — o 401 se repetia até um novo
  Atualizar. Agora os caminhos de imprimir/reimprimir revalidam via
  `obter_token` (que só renova quando preciso). Ambas e Shopee já faziam certo.
- `marcar_impresso` recarrega o estado do disco e **mescla** antes de gravar:
  a tela e o bot na mesma conta ao mesmo tempo não apagam mais a marcação um
  do outro (last-writer-merge em vez de last-writer-wins).
- **Trava entre processos no estado** (achado P1 da revisão técnica): o merge
  sozinho só cobria o caso sequencial — se a tela e o bot **lessem ao mesmo
  tempo**, a última gravação vencia e uma marcação se perdia (reproduzido em
  teste: sem a trava, 6 marcações concorrentes viravam 1). Agora o ciclo
  ler→mesclar→salvar roda sob `estado.trava` (arquivo `.lock` ao lado, com
  `msvcrt`/`fcntl` e degradação suave), e o `.tmp` da gravação atômica inclui o
  PID (dois processos não disputam o mesmo temporário).
- **A poda por idade também não apaga mais marcação concorrente:** a regravação
  do estado podado (`carregar(persistir_poda=True)`, no Atualizar do ML) escrevia
  **fora da trava**, então um Atualizar podia apagar uma marcação que o bot
  gravasse nesse meio-tempo (a mesma corrida da trava, por uma porta lateral).
  Agora a poda roda sob a mesma `estado.trava` e **relê o disco** antes de gravar.
- **Falha ao salvar o estado após a confirmação não passa mais em silêncio**
  (achado P2 da revisão técnica): se a gravação falhar depois do "sim" (disco,
  permissão, arquivo preso pelo OneDrive/antivírus), a GUI agora oferece
  **Repetir** na hora, continua marcando os demais grupos do lote (uma falha
  não derruba o resto) e, se persistir, avisa com clareza que as etiquetas
  **saíram mas não foram marcadas** — para o operador **não reimprimir**. Erros
  exibidos/logados passam por `sem_segredos`.

### Documentação
- **Higiene pós-auditoria:** CLI da Shopee mostra o status real de impressão
  (passava estado vazio — tudo aparecia `[PENDENTE]`) e conta **pedidos** (não
  itens) no modo `todos`; o bot passa `sem_segredos` também nos erros
  esperados (cinto-e-suspensório); dependências com teto de versão maior
  (`requests<3`, `python-telegram-bot<23`); limitação conhecida dos grupos
  "Sem data" documentada na `ARQUITETURA` (reabrem na virada do dia — decisão
  de documentar, não mexer na chave de estado); aviso sobre `.bak` desgarrado
  no README/ARQUITETURA.
- **README completo e atualizado:** cobre o estado atual do app (ordem de
  separação pela aba Nomes, adoção de anúncios sem SKU, rastreio Shopee em todos
  os grupos, log operacional) com **imagens novas** da tela (ML, Shopee, editor
  de Nomes e gerenciador de SKUs) e um índice navegável.
- **"Comece por aqui" no topo do `CLAUDE.md`/`AGENTS.md`:** sequência de
  arranque para um chat novo (ler o guia → consultar o grafo → `ARQUITETURA`
  antes de mexer em estado/token/impressão).
- **`docs/AMAZON_SP_API.md`:** levantamento (pesquisa, nada implementado) de
  como a Amazon SP-API encaixaria no app no futuro — o risco decisivo é de
  negócio/BR (só FBM/MFN gera etiqueta).
- **`docs/PRIORIDADES_TECNICAS.md`:** nota da otimização futura do modo Ambas
  (coletar as contas em paralelo — por que não agora, como fazer com segurança).
- **Grafo de conhecimento (`graphify-out/`):** camada de docs enriquecida a cada
  mudança (decisões e "porquês" como nós `rationale`) + auditoria de sincronia
  nó a nó com o código.
- **Checklist "manter o repertório em dia"** no `CLAUDE.md`/`AGENTS.md`: define o
  que atualizar ao fechar cada mudança (CHANGELOG, convenções, ARQUITETURA,
  grafo, prioridades) — para os docs não defasarem em relação ao código.
- **Regras de git para a IA** (`CLAUDE.md`/`AGENTS.md`): verificar o estado do
  `main`/PR antes de empurrar follow-up, não empilhar commits numa branch que
  pode ser mergeada (viram órfãos), e recuperar do `main` o que ficar de fora.

### Qualidade
- **CI (GitHub Actions):** roda o `pytest` em cada Pull Request e push no `main`
  (Python 3.11 e 3.12), mostrando um check verde/vermelho automático. Badge no
  topo do README.
- Novos testes: camada comum de estado, log operacional, ordenação por Nomes,
  carimbo com acentos, corrida de token e a blindagem do nome do `.zip` que a
  Zebra reconhece.

## [1.0.0]

### Organização e segurança
- Estrutura do repositório organizada; `.gitignore`, `README`, `requirements`.
- Remoção de segredos do versionamento (`credenciais.json`) e `credenciais.example.json`.
- `pyproject.toml`, `.gitattributes` e `.editorconfig`.

### Núcleo / API
- Núcleo lança `SeparadorError` em vez de encerrar o processo (CLI e GUI tratam o erro).
- Retry com backoff em downloads de etiquetas; aborta em falha parcial (não marca impresso).
- Pipeline de coleta unificado entre CLI e GUI.
- Datas no horário de Brasília (filtro de despacho correto independente do fuso da máquina).
- Caminhos de arquivos baseados na pasta do script.

### Desempenho
- Dispensa a chamada `/sla` por envio (prazo lido do próprio detalhe do envio).
- Cache de envios finalizados: pula os já enviados nas próximas buscas.
- Paginação da busca de pedidos em paralelo.
- Melhor convivência com o limite de requisições do ML (respeita `Retry-After` + jitter).

### Robustez
- Leitura tolerante e gravação atômica dos arquivos JSON (estado, caches, credenciais).
- Retry também em falhas de rede (conexão/timeout).
- Limpeza automática de entradas antigas do estado.

### Leitura dos pedidos
- Comandos `amanha` e `dia <AAAA-MM-DD>`; seletor Hoje/Amanhã na tela.
- Estado de impressão por dia de despacho.
- Nomes amigáveis por SKU (`nomes_sku.json`).
- Tela abre parada, deixando o usuário escolher o filtro.

### Lançadores (Windows)
- `Abrir Separador.bat`, `Abrir Separador (diagnostico).bat`, `Abrir Separador.pyw`.
- `Atualizar programa.bat` (git pull por duplo-clique).

### Qualidade
- Suíte de testes automatizados (pytest).
- SessionStart hook para preparar o ambiente nas sessões da web.
