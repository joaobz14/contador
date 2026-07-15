# Changelog

Histórico das principais mudanças do projeto.

## [Não lançado]

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

### Diagnóstico
- **Log operacional (`separador.log`, via `registro.py`):** a GUI registra
  loja/conta/dia, contagens, confirmação (sim/não) e falhas — para diagnóstico
  sem debugger. Nunca atrapalha a operação (defensivo) e **nunca loga segredos**
  (redação por `sem_segredos`).

### Bot do Telegram
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
- `marcar_impresso` recarrega o estado do disco e **mescla** antes de gravar:
  a tela e o bot na mesma conta ao mesmo tempo não apagam mais a marcação um
  do outro (last-writer-merge em vez de last-writer-wins).

### Documentação
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
