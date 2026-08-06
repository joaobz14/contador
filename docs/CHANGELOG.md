# Changelog

Histórico das principais mudanças do projeto.

## [Não lançado]

### Adicionado
- **`python tools/diag_zpl.py` — descobre de onde vem a etiqueta em branco.**
  Quando a impressão "pula uma etiqueta", ele lê o lote que já foi impresso
  (o app da Zebra guarda em `~/zebra_usb_concluidos/`) e diz, página por
  página, o que o arquivo realmente mandou para a impressora. Rode sem
  argumento nenhum que ele pega o lote mais recente sozinho.
  - Serve para separar as três causas possíveis: uma página em branco dentro
    do arquivo, uma troca de configuração de mídia no meio do lote, ou o
    avanço de etiqueta que o próprio app da Zebra faz ao ser iniciado.
  - **Ele também avisa quando uma etiqueta de envio não vem seguida da nota.**
    O Mercado Livre manda uma etiqueta e uma nota por venda; o relatório aponta
    o número exato do bloco quando isso não bate. O primeiro lote conferido de
    verdade tinha 19 etiquetas e 18 notas. O aviso **não afirma o motivo** —
    pode ser nota que faltou ou venda de vários volumes (que tem duas etiquetas
    para uma nota só) —, ele manda você conferir no painel do Mercado Livre.
  - **Não mostra nome, endereço nem CEP de comprador** — só a estrutura.
- **Os comandos `/perguntas` e `/anuncios` passam a mandar uma senha ao n8n.**
  Hoje qualquer pessoa que descobrisse o endereço do fluxo conseguia dispará-lo
  — não veria os dados (a resposta sempre vai para o seu chat), mas podia gastar
  a cota da API do Mercado Livre e encher o seu Telegram.
  - **Nada muda até você configurar.** Enquanto a senha não estiver no
    `bot_config.json`, o bot funciona exatamente como antes. Isso é de
    propósito: permite atualizar o programa agora e ligar a proteção quando
    quiser, sem os dois lados terem que mudar no mesmo instante.
  - **Quando for ligar** (o passo é seu, junto com quem cuida do n8n): gere a
    senha na sua máquina com
    `python -c "import secrets; print(secrets.token_urlsafe(32))"`, cole o mesmo
    valor nos dois lados e acrescente ao `bot_config.json`:
    `"n8n_segredo": "o_valor_gerado"`. Depois reinicie o bot.
  - Se a senha ficar errada, o bot avisa **isso** — não manda mais você conferir
    o workflow à toa.

### Alterado
- **`/atualizar` agora reinicia quando o bot está rodando código antigo, mesmo
  que não haja nada para baixar.** Antes, se você tivesse feito o `git pull` no
  PC, o comando respondia "já está atualizado" e **não reiniciava** — e você
  ficava convencido de que atualizou enquanto o bot seguia na versão velha.
  Também: quando há alterações locais travando o pull, ele agora avisa se o
  código da pasta já é mais novo que o que está rodando.
- **Venda da Shopee sem prazo definido não some mais do aviso do dia.** A Shopee
  demora a atribuir a data de despacho, e o app preenchia essa lacuna com uma
  conta própria — que, medida contra um pedido real, errava **um dia para a
  frente**. Resultado: a venda que vencia hoje ficava fora do aviso de hoje,
  em silêncio. Agora, quando a Shopee ainda não datou, a venda **entra** no
  aviso e vem marcada com "🗓 inclui venda que a Shopee ainda não datou".
  Venda com prazo conhecido de outro dia continua fora.
- **Correção no alerta do Telegram: uma falha de rede podia virar um despejo de
  mensagens.** O bot marca, uma vez por dia, quais vendas ele "já conhece",
  para depois só avisar do que aparecer de novo. Essa marca era única e era
  ligada mesmo quando a consulta de uma das lojas tinha falhado — e aí, no ciclo
  seguinte, todas as vendas daquela loja apareciam como novas e saíam juntas.
  Agora a marca é por loja/conta e só é gravada quando a consulta dá certo.
  Quem falhou tenta de novo em silêncio, sem calar as outras.
- **O aviso "sem NF-e" agora espera o seu faturador trabalhar.** Ele estava
  disparando assim que a venda caía — antes de o UpSeller puxar o pedido — e
  minutos depois se desmentia com o "✅ liberada". Agora o bot só avisa quando a
  venda passa de **30 minutos** e **continua** sem nota, que é quando o motivo
  provável é o único que interessa: **o ERP não achou estoque e por isso não
  faturou**.
  - A mensagem passa a dizer **há quanto tempo** a venda está parada. Isso ajuda
    a distinguir os dois casos: uma venda parada há 40 min é falta de estoque;
    várias de uma vez é o faturador com problema.
  - Para ajustar o tempo, acrescente `"carencia_nf_min": 45` (ou o valor que
    preferir) ao `bot_config.json`. O número certo depende do seu ERP.
  - **Bônus:** isso também acaba com o aviso disparado quando a Shopee ainda
    está só processando o pedido — que resolve sozinho em minutos e nunca
    precisou de aviso.
- **Os avisos de venda do bot pararam de poluir o chat.** Três mudanças, todas
  no alerta automático:
  - **Uma mensagem por vez, não uma por conta.** Cozilatti, Gastromaq e Shopee
    agora aparecem como blocos de um aviso só. Antes, cada uma mandava a sua — e
    com o aviso de "falta NF-e" somado, dava até **6 mensagens a cada 5 minutos**.
  - **Os avisos começam às 8:30**, não mais às 7h. Antes das 8:30 você está na
    tela e já recebeu o resumo da manhã; o alerta só repetia o que você acabou
    de ler.
  - **O primeiro aviso do dia não vem.** Ele só anota o que já existe, para que
    dali em diante o aviso signifique literalmente **"apareceu agora"**. Nada se
    perde: essas vendas estão no resumo das 8:00 e na tela.
  - A explicação do "falta NF-e" agora aparece **uma vez** no fim, e a venda que
    estava travada e foi liberada vem marcada com **✅** — antes ela reaparecia
    igual à primeira e parecia mensagem repetida.

### Removido
- **A checagem semanal das APIs (`api-monitor`) foi desativada.** Ela nunca
  conseguiu ler as fontes de verdade — a página de novidades do Mercado Livre
  exige login e as da Shopee dependem de renderizar a página inteira, o que
  falhava — então o relatório saía "bloqueada" toda semana, sem informação
  nenhuma, e ainda gastava uma consulta paga de IA a cada execução. Também havia
  um risco: ela rodava sozinha, sem restrição, na pasta onde ficam as
  credenciais, usando conteúdo baixado da internet.
  - **O que você precisa fazer na máquina:** remover a tarefa do Agendador —
    `Unregister-ScheduledTask -TaskName 'Contador - Monitor APIs (semanal)' -Confirm:$false`.
    Enquanto ela existir, vai continuar rodando semanalmente (agora só para
    imprimir o aviso de desativado).
  - O código ficou guardado, com o motivo escrito e o que precisaria mudar para
    voltar (`api-monitor/README.md`).

### Corrigido
- **O "Reiniciar Bot.bat" agora reinicia na primeira vez.** Era preciso abrir
  duas vezes: na primeira ele derrubava o bot mas não conseguia subir de novo —
  a tarefa do Agendador ainda estava terminando, o Windows recusava iniciá-la, e
  o script dizia "reiniciado" mesmo assim. Agora ele espera a tarefa liberar,
  confere se conseguiu, e **só avisa que reiniciou depois de ver o bot de pé**.
  Se nem assim subir, ele sobe pelo lançador direto; e se ainda assim falhar,
  diz que falhou em vez de dar sucesso por engano.
- **Quando a tela não abre, agora dá para saber por quê.** O atalho sobe o
  programa sem janela preta — então, se algo quebrasse na abertura, o
  duplo-clique não fazia **nada**: sem tela, sem mensagem, sem nenhum registro.
  Agora aparece uma caixa de erro dizendo o que houve, e o erro completo fica
  no `logs/separador.log`. Erros que acontecem com a tela já aberta (e que antes
  se perdiam) também passam a ser registrados lá.
- **A coleta diária do Product Ads não anuncia mais sucesso quando falha.**
  Quando o Mercado Livre não respondia à busca de campanhas, o coletor gravava
  o dia como "nenhuma campanha", dizia que tinha dado certo e saía com código de
  sucesso — o dia ficava vazio no histórico e ninguém ficava sabendo. Agora ele
  informa a falha e termina com erro (que é o que o Agendador de Tarefas do
  Windows registra sozinho). Para recuperar um dia perdido:
  `python ads-monitor/coletar.py --dia AAAA-MM-DD`.
- **Uma conta com problema não derruba mais a coleta da outra.** Um erro
  inesperado na Cozilatti (banco travado, resposta estranha) fazia o programa
  parar antes de tentar a Gastromaq. Agora cada conta é isolada de verdade.
- **Token vencido não é mais confundido com "conta sem Product Ads".** A
  mensagem agora diz o que fazer: rodar `pegar_token.py` para aquela conta.
- **Campanha grande não é mais gravada pela metade.** Se a listagem de anúncios
  de uma campanha for interrompida no meio, o dia dela fica marcado como
  incompleto em vez de registrar só a primeira parte como se fosse o total.

### Adicionado
- **Etiqueta já impressa agora dá para recuperar** (exige o app da Zebra
  **v1.26.2** ou mais novo). Antes, com "Excluir após imprimir" ligado, o arquivo
  era apagado assim que a impressão era mandada — se a impressora travasse
  **depois disso** (papel preso, ribbon rasgado), o lote estava perdido. Agora ele
  é **movido** para `C:\Users\<você>\zebra_usb_concluidos\AAAA-MM-DD\` e pode ser
  reimpresso. Atalho: **bandeja do app da Zebra → "Abrir pasta de concluídos"**.
  - **Nada muda na tela daqui** — ela continua lendo "o arquivo saiu da pasta" como
    "foi impresso", e mover satisfaz isso igual a apagar.
  - A pasta **não é limpa sozinha** (é o ponto: guardar). Para limpar, apague as
    pastas de datas antigas pelo Explorer.
- **Comando `/anuncios` no bot** — saúde dos anúncios das **duas** contas
  (Cozilatti e Gastromaq) numa resposta só. Funciona igual ao `/perguntas`: o bot
  aciona o fluxo do n8n, manda um "🔎 Consultando..." e a resposta chega em uns
  segundos, escrita pelo n8n. Também tem botão **📦 Anúncios** no `/menu`.
  - Para ligar, acrescente `"webhook_anuncios"` ao `bot_config.json` com o
    endereço do fluxo. O chat autorizado é o mesmo do `/perguntas` — não precisa
    configurar de novo.
- **O bot separa as vendas da Shopee que ainda não podem ser impressas.** Mesma
  regra do Mercado Livre: só as que precisam sair **no dia**, uma vez cada, em
  mensagem separada.
  - **Corrige algo que estava errado:** essas vendas já eram avisadas — só que
    como **"pronta"**. A Shopee **recusa** organizar o envio enquanto a nota não
    estiver validada, então o bot dizia que estava pronto o que ela mesma nega.
  - O aviso **não chuta o motivo**: pode ser a NF-e faltando (venda sem estoque)
    ou só a Shopee ainda processando o pedido — o painel mostra os dois do mesmo
    jeito na API. Ele diz que a etiqueta não foi liberada e manda você conferir.
  - Quando a nota é validada, você recebe o aviso normal de venda pronta também.
- **Diagnóstico dos estados da Shopee** (`python shopee_api.py status`) — passo
  antes de levar o aviso de "falta NF-e" para a Shopee. Ele lista os estados que
  existem na sua loja agora, com contagem, e mostra o que a API devolve sobre os
  pedidos que **não** estão em "pronto para enviar" — que é onde uma venda
  travada esperando a nota fica. O app hoje só pergunta pelos prontos, então
  essas vendas são invisíveis para ele, igual acontecia no Mercado Livre.
- **Contrato com o n8n registrado** (só documentação, nada muda no que já roda).
  Ficou acordado com o outro lado, antes de existir a 2ª função: um endereço de
  webhook por fluxo, parâmetros num campo `args`, nada de botão vindo do n8n
  (o toque não funcionaria), e — o que mais importa — **os relatórios de Ads
  gastam dinheiro** (~US$ 0,04 e ~5 minutos por execução). Se um dia virarem
  comando, ficam restritos ao seu chat e com limite de frequência.
- **O `/perguntas` passou a mandar o seu chat id para o n8n.** Preparação para as
  próximas integrações: com o chat id no pedido, o fluxo do n8n responde a **quem
  perguntou**, em vez de ter um chat fixo escrito dentro dele. O fluxo de hoje
  continua funcionando igual — é um campo a mais, que ele pode ignorar.
- **O aviso de vendas passou a incluir as que estão em "Informe a NF-e".** Antes
  ele só avisava das vendas prontas para imprimir — e justamente a venda de um
  produto **sem estoque** nunca chega nesse estado, porque o faturador não sobe o
  XML da NF-e. Era a venda que você mais precisava ver cedo, e era a única
  invisível. Agora ela também avisa, no mesmo esquema de sempre: **só o que
  precisa sair no dia**, uma vez por venda.
  - Vem numa mensagem **separada**, com o rótulo `· falta NF-e` e a observação de
    que a etiqueta só libera depois que o XML subir — para não se confundir com
    uma venda que já dá para imprimir.
  - Quando o XML sobe e a venda fica pronta, você recebe o aviso normal também.
    São dois recados com ações diferentes; um não cala o outro.
  - Aparece no `/vendasapos` como um bloco próprio.
  - **A impressão não mudou em nada**: essas vendas não entram em lote nenhum (o
    Mercado Livre não libera a etiqueta delas).
- **Comando `/atualizar` no bot** — baixa a versão nova e reinicia, **sem você
  precisar estar no PC**. Ele responde o que aconteceu: "já estava na versão mais
  nova", "atualizado: `abc1234` → `def5678` — reiniciando, volto em uns 15
  segundos" e, quando volta, um "✅ Voltei — agora rodando a versão `def5678`".
  Três cuidados:
  - **Nunca perde o seu trabalho.** Se houver alteração local não salva na pasta
    (tipicamente os nomes de SKU editados na tela), ele **não puxa nada** e diz
    quais arquivos travaram. Você resolve no PC e manda `/atualizar` de novo.
  - **Não atropela uma operação.** Se estiver no meio de uma impressão, responde
    "tente de novo em instantes" em vez de reiniciar no pior momento.
  - **Só sai do ar se alguém for reiniciá-lo.** Se o bot tiver sido aberto na mão
    (sem o lançador automático), ele atualiza mas avisa que continua na versão
    antiga — um bot mudo é pior que um bot desatualizado.
  - A **tela** não é atualizada por ele: se estiver aberta no PC, continua na
    versão antiga até você fechar e abrir.
- **Comando `/perguntas` no bot** — dispara o fluxo do n8n que lista as
  perguntas e mensagens sem resposta da conta 3. O bot **não responde nada**: ele
  aciona o fluxo, manda um "🔎 Consultando..." na hora e a resposta chega alguns
  segundos depois, escrita pelo próprio n8n no mesmo chat. Também dá para tocar
  no botão **🔎 Perguntas** do `/menu`. O comando é restrito a **um** chat (o
  seu); de qualquer outro é ignorado em silêncio.
  - Para ligar, acrescente duas linhas ao `bot_config.json` (na pasta `dados/`,
    que não vai para o GitHub): `"webhook_perguntas"` com o endereço do webhook
    e `"chat_perguntas"` com o seu chat id — o `/id` mostra o número. **O
    endereço do webhook não pode ir para o código**: quem tem o link dispara o
    fluxo, e este repositório é público. Depois reinicie o bot (`/versao` avisa
    se ele ainda está na versão antiga).
  - Nada mudou na forma como o bot **recebe** as mensagens: ele continua lendo
    por polling, e o n8n só escreve. Os dois sistemas dividem o mesmo bot
    exatamente por isso.
- **Menu de comandos no app do Telegram** (o botão "/"). A lista é publicada
  **por chat**, não globalmente — no escopo global qualquer estranho que abrisse
  o bot veria todos os comandos, o oposto da correção do `/menu` abaixo. O
  `/perguntas` só aparece no menu de quem pode usá-lo.

### Corrigido
- **Erro no `bot_config.json` agora diz o que está errado — e onde.** Se o
  arquivo tiver um problema de formato (uma chave fora das chaves `{ }`, uma
  vírgula faltando), o bot passa a dizer exatamente isso, com a **linha e a
  coluna**. Antes ele reclamava de "token ausente", mandando você procurar no
  lugar errado.
- **O motivo de o bot não subir agora aparece no `bot.log`.** Como ele roda numa
  janela oculta, a mensagem de erro não era vista por ninguém e o log só mostrava
  a última linha *antes* da falha. O sintoma virava "o bot reinicia sozinho a
  cada 15 segundos" sem nenhuma pista — e a suspeita caía no lugar errado.
- **Reiniciar o bot não reiniciava nada.** O par de comandos que o `/versao`
  mandava rodar (`schtasks /end` + `/run`) não funcionava: o lançador soltava o
  bot e saía, então para o Agendador a tarefa já tinha terminado e o bot ficava
  fora do alcance dela. O `/end` não matava nada e o `/run` subia um **segundo**
  bot por cima do primeiro — os dois brigavam, e o **antigo** continuava
  respondendo. Por isso a versão nunca mudava, mesmo "reiniciando".
  - Agora existe **`atalhos\Reiniciar Bot.bat`**: um duplo clique derruba o que
    estiver de pé (inclusive uma instância antiga perdida) e sobe **um** só.
  - O `/versao` e o `/atualizar` passaram a indicar esse atalho, e o
    `Atualizar programa.bat` usa ele para reiniciar.
- **Sincronizador do grafo abortava com arquivo novo** (só afeta o
  desenvolvimento). A correção anterior ensinou o coletor a enxergar arquivo
  ainda não commitado, mas a *validação* continuou perguntando de outro jeito:
  ele criava os nós do arquivo novo e em seguida os rejeitava, travando o
  `--update` até alguém rodar `git add`. As duas metades agora perguntam igual.
- **`/menu` respondia a qualquer pessoa** (varredura de segurança). O bot é a
  única parte do projeto que alguém de fora alcança — basta achar o @usuário
  dele. Os comandos que mostram pedidos já exigiam autorização, mas `/start`,
  `/menu` e `/ajuda` respondiam a estranhos com a lista de comandos e **qual
  loja está ativa**. Nenhum dado de venda vazava (todo botão continua exigindo
  autorização), mas era informação de graça para quem estivesse sondando. Agora
  também exigem autorização. `/id` continua aberto de propósito — é como você
  descobre o próprio número para se liberar.
- **Duas brechas na redação de segredos do log** (varredura dos módulos que as
  auditorias nunca olharam — todas entravam pelo núcleo). O `registro.py` tem 64
  linhas e é a **última** defesa contra token em arquivo de log:
  - o **`app_secret` do TikTok** não estava na lista de chaves — e o
    `pegar_token_tiktok.py`, escrito hoje, manda ele na URL. Um erro de conexão
    imprimiria o segredo no console;
  - o **token do Telegram** fica no *caminho* da URL (`/bot<ID>:<TOKEN>/`), onde
    a regra de `chave=valor` não alcança.
  Somado o cabeçalho `Bearer` do Mercado Livre, por precaução. O que **não** é
  segredo (`app_key`, `shop_id`) continua aparecendo, para dar diagnóstico.
- **Screenshots da tela podiam ser commitados.** `out.png` (documentado no
  `CLAUDE.md`) e os `tela_*.png` da CI mostram **pedidos e SKUs reais** e não
  estavam no `.gitignore`. Os snapshots do `api-monitor` também passaram a ser
  ignorados por inteiro, e não só os `.md` — mesma regra invertida que já protege
  a pasta `dados/`, para arquivo novo não escapar por esquecimento.
- **Bot podia usar a conta ERRADA** (varredura por blocos). O bot faz várias
  coisas ao mesmo tempo: o alerta de vendas percorre **todas** as suas contas do
  Mercado Livre a cada 5 minutos, e você pode mandar `/imprimir` no meio disso.
  Como trocar de conta mexe numa configuração compartilhada, o comando podia ler
  a credencial e o histórico da conta que o **alerta** estava consultando naquele
  instante — imprimindo com o login errado e anotando o "já impresso" na conta
  errada. Simulado em bancada: **39 de 40** leituras pegaram a conta errada.
  Agora as operações do bot esperam uma pela outra (são segundos), e um teste
  falha se alguém adicionar um caminho novo que esqueça essa espera. **A tela
  nunca teve esse problema** — ela faz uma coisa de cada vez.
- **Varredura atrás de outras falhas silenciosas** (pedido do dono depois do
  incidente abaixo). Quatro encontradas, todas reproduzidas antes de corrigir:
  - **Venda de hoje indo parar em "Outras datas".** Quando o Mercado Livre
    recusava informar o *prazo* de um envio, o app tratava como "sem data" — e a
    venda sumia do dia selecionado, aparecendo num balde onde ninguém olha na
    hora de imprimir. Era o mesmo problema por outra porta, mais discreta. Agora
    o pedido continua na lista (ele **está** pronto) e a tela avisa que o prazo
    não pôde ser confirmado.
  - **Falha passageira do ML virando permanente.** Se a consulta de um produto
    falhasse, o app gravava uma entrada **vazia** no cache — e como o cache só
    busca o que ainda não tem, aquele produto ficava quebrado **para sempre**:
    perdia o código de barras, perdia o SKU, e um anúncio que você já tinha
    adotado num SKU voltava a aparecer como grupo separado, sem SKU. Só limpando
    o cache na mão resolvia. Agora falha não é gravada — a próxima busca tenta
    de novo.
  - **Token revogado dando o conselho errado.** Se a credencial do Mercado Livre
    perdesse a validade, *todas* as consultas falhavam e a tela dizia "a API não
    respondeu sobre 150 envios, clique em Atualizar de novo" — e Atualizar de
    novo nunca ia resolver. Agora credencial recusada aparece como erro claro,
    dizendo para rodar o `pegar_token.py`.
  - **Lote de etiquetas vindo curto sem ninguém notar.** O app conferia se o
    Mercado Livre respondeu, mas não **quantas etiquetas** vieram. Se viessem
    menos que os pedidos, o lote saía curto e todos eram marcados como impressos.
    Na tela você perceberia ao conferir o papel; no **bot**, que marca sozinho,
    não. Agora o app confere a quantidade e recusa o lote curto sem marcar nada.
- **Vendas sumindo do lote quando a API do Mercado Livre falha.** Num dia de API
  instável, a tela mostrou **5 de 7** vendas do mesmo SKU; imprimiu as 5, e as
  outras 2 só apareceram depois de clicar em Atualizar de novo. A causa era do
  app: quando o ML recusava a consulta de um envio (mesmo depois das
  re-tentativas), o programa tratava a falha como *"esse envio não está pronto"*
  e descartava o pedido **sem avisar nada** — o lote aparecia completo.
  Agora "a API não respondeu" é uma coisa distinta de "não está pronto". Esses
  envios são contados e, se houver algum, a tela **avisa antes de você
  imprimir**: *"A API do Mercado Livre não respondeu sobre N envios nesta busca.
  Clique em Atualizar de novo ANTES de imprimir."* Vale para o modo 🌐 Ambas
  também, somando as duas contas. O aviso não bloqueia nada — só devolve a
  decisão a quem está operando.

### Adicionado
- **Canal de volta com o app da Zebra: ele responde, a tela para de adivinhar.**
  A entrega entre os dois apps é por arquivo (ZIP na Downloads) e não havia
  resposta nenhuma. A tela deduzia o que tinha acontecido por dois sinais
  indiretos — o ZIP sumir e o log do monitor avançar —, e "sumir" só funciona com
  a opção **"Excluir após imprimir" ligada**: com ela desligada, a tela nunca
  conseguia confirmar uma impressão. Agora o app da Zebra (**v1.26.0**) publica o
  resultado de cada arquivo processado, e a tela lê essa resposta antes de
  recorrer aos palpites. Ganhos concretos:
  - a confirmação passa a dizer **"o monitor confirmou"** com base num fato, e
    funciona independente daquela opção;
  - existe um aviso novo para **falha de impressão**, que antes era invisível: um
    arquivo que falha **não é apagado** pelo monitor, então ele ficava
    indistinguível de um lote grande ainda imprimindo.
  Com um app da Zebra anterior à v1.26.0 nada muda — a tela cai exatamente no
  comportamento de antes.

### Pesquisado
- **Levantamento do TikTok Shop (`docs/TIKTOK_SHOP_API.md`)** — pesquisa, nada
  implementado, nos moldes do que já existe para a Amazon. **O objetivo imediato
  é só receber aviso de venda no Telegram**, não imprimir — o que dispensa as
  perguntas em aberto sobre etiqueta e reduz o trabalho a uma função nova, do
  mesmo feitio da que a Shopee usa no alerta pós-horário. Boas notícias: a
  etiqueta sai em **ZPL** no Brasil (confirmado no painel, em produção), o envio
  por Correios é "TikTok Shipping" (o caso que a API cobre) e a autenticação é
  irmã da Shopee — encaixaria como mais um provedor, sem caminho de impressão
  novo. Dois pontos ficaram **em aberto** e estão marcados como tal: se a **API**
  também entrega ZPL (o painel entrega, mas são coisas diferentes) e se ela
  entrega a **NF-e** — porque o painel imprime etiqueta **e** nota, o que põe o
  TikTok no formato 2-por-venda do Mercado Livre e mexeria na validação de
  paridade do app da Zebra. O documento marca a força da evidência item a item e
  registra os becos sem saída, inclusive uma IA de suporte que respondeu pela
  documentação de outro produto.

  **ARQUIVADO no mesmo dia, a pedido do dono — pausa, não desistência.** A
  integração travou **antes do primeiro byte de API**: não há como autorizar a
  loja porque o **Service ID não aparece** no painel (e não é a "Chave do
  aplicativo"), e o link de autorização responde *"This service does not exist"*.
  Ficaram prontos e **não devem ser refeitos**: o levantamento,
  `pegar_token_tiktok.py`, a página de retorno do OAuth (que agora serve à Shopee
  **e** ao TikTok) e o app criado no painel com chave, segredo e URL de
  redirecionamento. O documento registra **onde parou** e **qual é o passo que
  destrava** — rodar `POST /order/202309/orders/search` na Ferramenta de teste de
  API do painel, que de uma vez prova se a API responde e entrega a forma real do
  payload.

### Decidido
- **Os dois apps continuam separados** (avaliado a pedido do dono). O app da
  Zebra não é back-end deste: ele também imprime o que você baixa **na mão** pelo
  painel do ML, tem funcionalidade própria (etiquetas separadoras), roda como
  administrador (para limpar a fila de impressão) e fica ligado o dia todo na
  bandeja. Juntar mataria o download manual, arrastaria a tela e o bot para o
  UAC e fundiria três ciclos de vida diferentes. A pasta Downloads ainda serve
  de fila: a tela pode fechar no meio do lote que a impressão continua. O único
  ganho real da fusão era o canal de volta — obtido acima, sem fundir.

### Melhorado
- **`Atualizar programa.bat` reinicia o bot sozinho.** O `git pull` troca os
  arquivos, mas o bot que já está no ar continua com o código que carregou no
  logon — o sintoma é "a atualização não pegou", sem nenhum sinal do porquê.
  Aconteceu duas vezes (o `/vendasapos` e o layout do resumo de vendas). Agora
  o atualizador detecta se o `pull` trouxe algo novo e, em caso positivo,
  reinicia a tarefa do Agendador. Se o bot não estiver registrado lá, avisa que
  ele segue com a versão antiga e diz como registrar.
- **Comando `/versao` no bot.** Mostra a versão que o processo está rodando e a
  que está na pasta; se forem diferentes, avisa que está desatualizado e dá o
  comando de reinício. Cobre o caso de você atualizar com `git pull` na mão, em
  que o `.bat` não entra na história. Lê o commit direto do `.git` (dois
  arquivos de texto) — nada de `subprocess`, que sob `pythonw` herda handles
  inválidos e falha com WinError 6.

- **Resumo de vendas do bot (`/vendasapos`) com layout legível no celular.** Era
  uma lista crua de "SKU - quantidade", uma linha embaixo da outra, em ordem de
  chegada. Agora:
  - cabeçalho com a janela (`desde 08h30`) e o horário do envio;
  - **um bloco por conta**, com subtotal no título (`COZILATTI · 59 unidades ·
    26 SKUs`) e divisor entre eles;
  - lista **alinhada** — quantidade encostada à direita, largura da coluna vinda
    do SKU mais longo daquele bloco;
  - **ordenado pelo que mais vendeu**, não mais pela ordem em que a venda caiu;
  - conta sem venda aparece como "nenhuma venda" em vez de sumir — ausência
    também é informação;
  - total geral no rodapé.

  A mensagem vai **sempre em uma só**: se a lista passar do limite do Telegram,
  mostra os maiores e acrescenta "… e mais X SKUs (Y un)".
  - bloco **📦 TOTAL POR SKU** somando as contas, antes do rodapé: é a lista de
    reposição (sem ele, um SKU que vendeu nas duas contas obriga a somar de
    cabeça). Aparece só quando há mais de uma conta com venda — com uma só,
    repetiria a lista dela. Ele segue a **ordem da aba ✏ Nomes** (a mesma da
    tela e do PDF do resumo do dia), porque é uma lista de separação: a ordem
    em que você anda pelo estoque. SKU não cadastrado na aba vai ao fim.
  Novo comando `python bot_telegram.py testar-resumo` manda o resumo para os
  chats liberados na hora, para conferir o layout sem esperar uma venda.

### Investigado e descartado
- **Detectar sozinho se o motorista da coleta é o mesmo nas duas contas ML: não
  é possível pela API pública.** A ideia era o app avisar (sem selecionar nada)
  quando o mesmo motorista atende as duas contas, sinal de que o modo 🌐 Ambas
  faz sentido no dia. A premissa estava certa — no mesmo dia, os painéis das
  duas contas mostraram o mesmo motorista e a mesma placa. Mas as duas fontes
  plausíveis foram testadas com dado real e nenhuma entrega o dado: o
  cronograma de coleta é um **gabarito semanal** (os campos de motorista,
  transportadora e veículo existem na estrutura mas vêm vazios em todos os
  dias), e o detalhe do envio **não tem nem esses campos**. O painel do
  vendedor mostra a informação, então ela existe do lado do Mercado Livre —
  por endpoint interno, fora da API pública.
  **Nada muda na operação:** o 🌐 Ambas continua sendo escolha manual, como
  sempre foi. O percurso completo, o desenho que teria sido usado e o que
  reabriria a questão ficaram registrados no item 12 do
  `docs/PRIORIDADES_TECNICAS.md`, para a ideia não voltar do zero a cada
  poucos meses.

### Adicionado
- **A tela agora sabe se o app da Zebra pegou o lote.** A entrega das etiquetas
  é por arquivo (o `.zip` vai para a Downloads e o app da impressora o consome),
  e até agora não havia retorno nenhum: com o monitor fechado, os ZIPs só se
  acumulavam e você descobria pelo papel que não saía. Nada se perdia — a
  marcação só acontece depois do seu "saíram certo?" —, mas você descobria
  tarde. Agora a confirmação traz uma linha a mais:
  - **✅ confirmou** — o arquivo foi consumido e apagado (o app apaga após
    imprimir);
  - **⏳ ativo e ainda imprimindo** — lote grande, o arquivo só some na última
    etiqueta;
  - **⚠️ não deu sinal** — o arquivo continua na Downloads e o app não escreveu
    nada: provavelmente está fechado.

  Não foi preciso mudar nada no app da impressora — os dois sinais (o arquivo
  sumir e o log dele avançar) já existiam. **O aviso informa, nunca decide:**
  quem responde se as etiquetas saíram corretamente continua sendo você, olhando
  o papel — o monitor confirma que *mandou* imprimir, não que a etiqueta saiu
  legível e no lugar.

### Segurança
- **O token do bot parou de ser gravado no `bot.log` e no console.** A URL da API
  do Telegram carrega o token no próprio caminho
  (`https://api.telegram.org/bot<TOKEN>/getUpdates`), e a biblioteca HTTP
  registrava cada requisição em INFO — com o log do bot em INFO, o token ia
  inteiro para o arquivo e para a tela, a cada chamada, para sempre. Bastava
  colar um trecho do log pedindo ajuda para entregar o token junto (foi o que
  aconteceu em 30/07/2026). O `sem_segredos` do `registro.py` não cobria isso:
  esses registros nascem dentro da biblioteca, sem passar pelo código do
  projeto.
  Agora `httpx` e `httpcore` ficam em WARNING — **erro de rede continua
  aparecendo** (é o que importa para diagnóstico), só o INFO de requisição sai.
  Nada do que o bot registra mudou.
  Um token que apareceu num log deve ser trocado no BotFather (`/revoke`) por
  precaução; esta correção garante que o novo não vaze do mesmo jeito.

### Corrigido
- **O aviso do app da Zebra dava falso alarme em lote grande.** Num lote de 12 a
  confirmação dizia "⚠️ o monitor da Zebra NÃO deu sinal" com a impressora
  trabalhando normalmente; em lotes pequenos acertava. Dois fatos se somavam: em
  lote grande o ZIP **não** desaparece dentro do tempo de espera (o app da
  impressora só o apaga depois da última etiqueta), e o segundo sinal — o log
  dele — não pôde ser lido. A versão anterior tratava "não consegui ler o log"
  como "o monitor está parado".
  Agora o ⚠️ **exige prova**: só aparece quando o log é encontrado E
  provadamente não avançou. Se não há log para consultar, o app fica **calado** —
  que é o comportamento de antes desta funcionalidade, com você conferindo o
  papel. Falso alarme é pior que aviso nenhum: ensina a ignorar o aviso, e aí ele
  perde a utilidade justamente no dia em que estiver certo.
  O `separador.log` passou a registrar se o log do monitor foi encontrado e em
  qual caminho, para diagnóstico futuro sem precisar reproduzir.
- **Contas do ML sumiam da tela depois da reorganização de pastas** (incidente
  real, 2026-07-29). Na primeira abertura após a atualização, o seletor de conta
  e o modo **🌐 Ambas** desapareciam: a tela abria como se não houvesse nenhuma
  conta cadastrada. Causa: a migração automática rodava inteira sob um único
  `try/except`, então a **primeira** falha de IO abortava tudo o que vinha
  depois. No Windows o bot sobe no logon pelo Agendador de Tarefas e mantém o
  `bot.log` **aberto** — e arquivo aberto não pode ser renomeado (WinError 32).
  Como os logs eram movidos **antes** da pasta `contas/`, essa única falha
  deixava as credenciais das contas para trás na raiz. Agora cada movimentação é
  independente (uma que falhe não leva as outras junto) e a pasta `contas/` —
  o dado mais caro de refazer, porque exigiria refazer o OAuth — é a **primeira**
  da fila. **Nada foi perdido**: os arquivos continuavam na raiz e voltam
  sozinhos na próxima abertura.

### Organização da pasta
- **Raiz reorganizada em `dados/` + `logs/`.** A pasta do projeto tinha ~35
  arquivos misturando código, documentação, config de ferramenta e todo o
  dado local do app (tokens, estado, caches, histórico e 4 logs que crescem
  sem parar) — achar o `separador_gui.py` do dia a dia virou garimpo. Agora:
  - **`dados/`** — o que o app lê e escreve: `credenciais*.json` (+`.bak`),
    `config.json`, `bot_config.json`, estados, caches, `historico_impressao.json`,
    `alertas_pos_horario.json`, os de-paras versionados (`nomes_sku.json`,
    `skus_por_anuncio.json`) e a pasta `contas/`.
  - **`logs/`** — `separador.log`, `bot.log`, `ml_tempos.log`, `shopee_tempos.log`.
  - **Raiz** — o que você abre (`separador_gui.py`), os módulos `.py`, e o que
    as ferramentas exigem lá (`README`/`CLAUDE`/`AGENTS.md`, `.gitignore`,
    `pyproject.toml`, `ruff.toml`).

  **Migração automática:** na primeira abertura (tela, bot ou CLI) os arquivos
  antigos da raiz são movidos sozinhos — **não precisa refazer token nem
  perder estado**. A migração leva o `.bak` das credenciais junto (um `.bak`
  desgarrado do principal guarda um refresh já rotacionado, morto), move a
  pasta `contas/` inteira, **nunca sobrescreve** um arquivo que já exista no
  destino e **nunca derruba a abertura** se falhar. Também remove o
  `bot.lock` órfão (sobra do auto-start pela tela, removido em 2026-07).
  O `.gitignore` passou a ignorar `dados/*` e `logs/` inteiros, liberando
  explicitamente só os dois de-paras versionados — assim um arquivo local
  novo nunca escapa por esquecimento de regra.

### Auditoria de APIs (ML + Shopee)
- **Correção real: refresh de token podia gravar credenciais no arquivo da
  conta ERRADA (corrida multi-conta do bot).** A "Área de risco" aceitava a
  corrida de `definir_conta` no job do alerta com a justificativa "só
  leitura" — mas o refresh de token é uma **escrita** que pode acontecer em
  qualquer caminho de rede. `obter_token`/`renovar_token`/`salvar_credenciais`
  resolviam a global `ARQUIVO_CRED` na hora da chamada: se o job do alerta
  trocasse a conta (outra thread) no meio de um refresh de um comando manual,
  as credenciais renovadas de uma conta eram gravadas no arquivo da outra
  (e o `.bak` junto — sem recuperação; conta travada, refazer `pegar_token`).
  Corrigido amarrando o arquivo de origem às credenciais no carregamento
  (chave volátil `_arquivo`, nunca persistida): trava, releitura, refresh e
  salvamento seguem todos no arquivo da conta dona das credenciais,
  independente da global. Probabilidade baixa (exigia coincidência de
  timing), impacto alto — nunca observado em produção.
- **Alerta pós-horário: ~95% menos chamadas à API do ML.** Cada ciclo de
  5 min refazia o pipeline completo com a janela cheia de 30 dias (~300+
  `GET /shipments` por ciclo, ~90-100 mil chamadas/dia, 24h/dia). Dois
  cortes: **janela de horário** (o job só trabalha das 07:00 às 20:59 de
  Brasília — fora disso é um no-op sem chamada nenhuma; de madrugada o
  aviso não tem utilidade, a venda da noite aparece no aviso da manhã) e
  **janela de busca dedicada** (`buscar_pedidos` ganhou `dias=`;
  `DIAS_JANELA_ALERTA=5` — um envio com despacho HOJE é sempre recente, e
  5 dias cobrem fim de semana + feriado; um caso raro que escape ainda
  aparece no aviso da manhã e em qualquer Atualizar, que seguem com a
  janela cheia de 30 dias).
- **Higiene de robustez/eficiência:** reimpressão Shopee lê o **cache de
  AWB** antes da rede (`gerar_etiqueta` com `rastreios=None` — reimpressão
  de grupo já impresso não pode falhar por um refetch; o AWB é imutável e
  conhecido desde a impressão); corpo **não-JSON** com status 200 (proxy
  interceptando) vira `SeparadorError` limpo em vez de `JSONDecodeError`
  cru (ML e Shopee, incluindo os refresh de token); `_aguardar_awbs` com
  **backoff** (1s×10 depois 2s, mesmo teto de ~40s, ~40% menos
  `get_tracking_number` por pedido preso); **dedup por id** na paginação do
  `buscar_pedidos` (com `sort=date_desc`, um pedido novo chegando no meio
  da paginação desloca os offsets e o mesmo pedido podia vir em duas
  páginas).

### CI
- **`gui-smoke` travava (às vezes) instalando dependências, sem nunca dar
  erro:** o `apt-get install` do `imagemagick` aciona o `needrestart`, que em
  runners `ubuntu-latest` recentes abre um prompt interativo (lista de
  serviços a reiniciar) mesmo com `-y` — sem terminal na CI, o job ficava
  preso até o timeout padrão de 6h, enquanto os outros jobs do mesmo run
  terminavam em segundos. Corrigido com `DEBIAN_FRONTEND=noninteractive` +
  `NEEDRESTART_MODE=a` no passo de instalação; adicionado também
  `timeout-minutes: 10` no job como rede de segurança contra travas futuras.

### Shopee
- **Correção real (2 rodadas): `_organizar_varios` podia reenviar um
  pedido já arranjado via `ship_order`.** Motivado por um requisito de
  qualidade **obrigatório** da Shopee (prazo curto, risco de penalidade):
  success rate > 90% por 7 dias consecutivos em `v2.logistics.ship_order`
  (só o endpoint singular — confirmado com o suporte deles que
  `batch_ship_order` não conta pra mesma métrica). O FAQ deles documenta
  "This parcel has already been shipped" (`logistics.package_already_shipped`)
  e "The order is being allocated, please wait" (`logistics.error_param`)
  como causas de erro — mensagens exatas confirmadas com o suporte.
  **Rodada 1:** o caminho individual (`organizar_envio`) já checava
  `envio_ja_arranjado` antes de (re)enviar, mas o caminho em **lote**
  mandava todos os `restantes` pro `batch_ship_order` sem essa checagem.
  Corrigido com `_filtrar_ja_arranjados` — nova etapa (1.5), entre a
  checagem de AWB existente e o batch, que consulta `parametros_envio` em
  paralelo e tira do batch quem já está arranjado.
  **Rodada 2 (revisão depois de respostas do suporte):** a rodada 1 não
  resolvia o problema de verdade — a propagação de
  `fulfillment_status`/`is_shipment_arranged` pode levar **até 15-20
  minutos**, bem mais que os ~40s de polling deste módulo. Um pedido que
  passava pelo batch mas ficava sem AWB (só pelo timeout curto) caía no
  fallback individual, que consultava o status ainda **desatualizado** e
  chamava `ship_order` **de novo** — exatamente o cenário rejeitado pela
  Shopee. Corrigido: esses pedidos não caem mais no individual, viram
  pendência de confirmação ("tente de novo em alguns minutos") em vez de
  arriscar reenviar. Defesa adicional em `organizar_envio`: catch
  específico pra "already been shipped" (não propaga como erro, só espera
  o AWB) e retry com backoff curto pra "being allocated" (transiente,
  segundo a própria Shopee). A migração mais completa que a Shopee
  recomenda (`v2.order.search_package_list` + `v2.order.get_package_detail`)
  segue como item de backlog — mudança maior (um `order_sn` pode ter mais
  de um `package_number`), não urgente pra fechar o requisito de
  compliance (ver `docs/PRIORIDADES_TECNICAS.md` item 11).

### Ferramentas de desenvolvimento
- **`ads-monitor/coletar.py` — coletor determinístico do Product Ads (Mercado
  Ads):** primeira camada de um futuro monitor de campanhas. Grava, uma vez
  por dia (default ontem — a plataforma fecha os dados às 10:00 GMT-3), o
  snapshot de métricas de cada campanha das contas configuradas num SQLite
  local (`historico_ads.sqlite3`, gitignorado). Reusa a autenticação do
  núcleo (`obter_token`/`definir_conta`), então herda a trava entre processos
  e nunca duplica lógica de refresh de token. Só leitura (GET) — não pausa,
  edita nem muda orçamento de campanha. Idempotente (regrava o mesmo dia, não
  duplica) e isola falha por conta. Endpoints confirmados na doc oficial
  "Product Ads" (via conector MercadoLibre), incluindo o sinal oficial de
  campanha limitada por orçamento (`lost_impression_share_by_budget`) —
  evita o cálculo caseiro custo÷orçamento, que a doc revela ser enganoso (o
  campo `budget` é média diária de um ciclo mensal com rollover). Ainda sem
  motor de recomendação nem dado de margem.
- **`ads-monitor/coletar.py` — atribuição por ad_group/item dentro da
  campanha:** estende o coletor com a cadeia campanha → ad_group → item_id →
  SKU (tabelas novas `ad_groups_diarios` e `ad_group_itens_diarios`), usando
  o fluxo por `ad_group_id` que substituiu o antigo endpoint de métricas por
  item (descontinuado em 27/05/2026 — doc "Product Ads para Catálogo e User
  Products"), validado antes com chamada real de leitura. Só resolve
  item_id dos ad_groups com atividade no dia (poupa chamada). Achado
  confirmado com dado real: um ad_group não é 1:1 com item — tipos
  `FAMILY`/`CATALOG` podem agrupar vários `item_id` sem quebra de métrica
  por item dentro do grupo. Construído **antes** de existir a fonte de
  margem por SKU (decisão do dono, para não esperar); o motor de
  recomendação que cruza margem continua bloqueado até essa fonte existir.
- **`ads-monitor/coletar.py` — resolução de SKU via `seller_sku` real:**
  achado com dado real, rodando contra as contas: a resolução de SKU dava
  **0/468 itens resolvidos**, porque `skus_por_anuncio.json` é um mapa
  manual pequeno (só p/ anúncios sem SKU adotados na tela), não um
  resolvedor geral — a maioria dos produtos tem `seller_sku` cadastrado
  direto no anúncio, sem cache local pra isso. Corrigido estendendo o cache
  do núcleo (`itens_cache.json`, via `_detalhe_item`) com o campo
  `seller_custom_field` — **mesma chamada** `GET /items/{id}` que a
  impressão já faz, sem custo extra de rede. Nova função `_resolver_skus`
  prioriza esse `seller_sku` real e só cai pro mapa de adoção quando
  ausente, mesma prioridade de `identidade()` no núcleo; trata cache
  staleness (entrada antiga sem a chave nova é refeita, não assumida "sem
  SKU").
- **`ads-monitor/` — agendamento diário automático:** `run-diario.ps1` +
  `registrar-tarefa.ps1` (mesmo padrão do `api-monitor/`, `Register-
  ScheduledTask` nativo, sem Git Bash) registram uma tarefa diária às 11:00
  (depois das 10:00 GMT-3 de fechamento das métricas). Antes só havia 1 dia
  de histórico coletado manualmente; sem isso, nenhum próximo passo (motor
  de recomendação, com ou sem margem) teria dado suficiente — o pedido
  original é explícito: nunca recomendar em cima de 1 dia.
- **`ads-monitor/recomendar.py` — motor de recomendação (sinais sem
  margem):** gera recomendações no formato do pedido original (conta,
  campanha, problema, evidência, ação exata, justificativa, impacto
  esperado, risco, confiança, urgência, prazo de reavaliação, métrica de
  verificação), usando só os 3 sinais que a própria API já calcula e não
  dependem de margem — orçamento insuficiente, ranking baixo, ROAS abaixo
  do `roas_target` da campanha. Recomendação de aumentar investimento sai
  sempre marcada "Recomendação condicionada à validação da margem"; ROAS
  abaixo do alvo não precisa dessa ressalva (redução de risco, não aposta
  de investimento). Trava contra recomendar em dado fraco (regra do pedido
  original): campanha com menos de 3 dias distintos ou 20 cliques na janela
  fica "monitorando", sem recomendação — dado provisório já é impossível
  por construção, já que o coletor só grava dias fechados.
- **`ads-monitor/narrar.py` — camada de narrativa opcional (IA) sobre o
  motor de regras:** `ads-monitor/` continua propositalmente determinístico
  (`coletar.py` só grava fatos, `recomendar.py` só aplica regras fixas); este
  script novo é **aditivo e opcional**, narra em português o que
  `recomendar.py` já calculou (recomendações + campanhas "monitorando" sem
  dado suficiente) sem inventar nenhuma conclusão nova. Usa `claude -p`
  (mesmo padrão do `api-monitor/run-semanal.ps1`) em vez de uma API de LLM
  externa — sem credencial nova pra gerenciar. O prompt tem regras
  obrigatórias equivalentes às do motor: nunca concluir sobre margem/
  lucratividade, nunca sugerir mudança automática, preservar o aviso
  "condicionada à validação da margem" tal como veio calculado. Se `claude`
  não estiver instalado, travar ou falhar, devolve vazio e não derruba nada
  — `recomendar.py` continua funcionando sozinho normalmente. Saída salva em
  `ads-monitor/relatorios/` (gitignorado, mesmo padrão do `api-monitor/`).
  `--dry-run` mostra o prompt montado sem chamar a IA nem gravar arquivo.

### Documentação
- **Base de conhecimento `obsidian/` reorganizada e validada:** o cofre virou a camada
  de **contexto humano e operacional** (decisões, conceitos, estado atual, incidentes,
  runbooks, funcionalidades, marketplaces, integrações) com uma seção **IA/** de
  onboarding para agentes (`Comece aqui`, `Fontes de verdade`, `Estado atual`, `Mapa de
  tarefas`). Corrigidas afirmações desatualizadas (resumo do dia agora é PDF consolidado
  por SKU, não `.txt`; removidas métricas antigas do grafo e a nota vazia). Cada fonte
  tem um papel — o Graphify segue como base estrutural/semântica. Novo validador
  `tools/validar_obsidian.py` (links, frontmatter, vazios, colisões de nome, referências
  de fonte e **segredos**), com testes e um job de CI dedicado.

### Ferramentas de desenvolvimento
- **Grafo Graphify auditado e re-sincronizado + atualizador seguro:** a camada AST
  do grafo (`graphify-out/graph.json`) estava congelada no commit de 2026-07-08 e
  125 commits atrás do código (módulos `estado.py`, `historico.py`, `registro.py`,
  `api-monitor/`, dezenas de funções/testes sem nó; centenas de linhas erradas).
  Novo **`tools/graph_sync.py`**: re-deriva a camada estrutural do código atual e
  **preserva integralmente a camada semântica** (as decisões/invariantes mantidas à
  mão) por IDs estáveis — modos `--check` (detecta defasagem, exit≠0), `--update`
  (aplica, grava atômico) e `--validate`. A camada semântica ganhou um espelho
  durável em **`graphify-out/semantic.json`** e uma **guarda no CI**
  (`tests/test_graphify_sync.py`). Resultado da sincronização: +239 nós, −3 (testes
  renomeados), 405 localizações corrigidas, 0 aresta órfã; conhecimento novo do
  `api-monitor` e do próprio processo de manutenção do grafo. `graph.html` continua
  defasado (só o CLI `graphify` o regenera — pendência documentada no relatório).

### Interface
- **Resumo do dia (o que você imprimiu hoje):** novo botão **📋 Resumo do dia** na
  tela abre uma janela com tudo que saiu da impressora **hoje** (dia de ação, não
  de despacho), separado por Mercado Livre (por conta) e Shopee, na **ordem da aba
  Nomes** (a mesma ordem de separação). Para imprimir, o botão **Imprimir soma por
  produto (PDF)** gera um **PDF compacto** (economiza folha) com a **soma por SKU**
  consolidando todas as contas ML + Shopee — a lista de produção/separação
  (`A01 - 2L 110 - 5`), também na ordem da aba Nomes. Um botão **Detalhado (.txt)**
  guarda o detalhado por marketplace. Por baixo, um registro novo (`historico.py`,
  `historico_impressao.json`, local/gitignorado) grava cada impressão confirmada
  com carimbo de tempo, no mesmo ponto em que o estado é marcado — então **GUI,
  bot e CLI** entram no resumo. Conta só o que foi realmente impresso pela
  primeira vez (o delta): reimpressão/dupla marcação não infla o número.
  Reimpressão manual, que não passa pela marcação, fica de fora do resumo (v1).
  O PDF é gerado em **Python puro** (sem dependência nova para instalar).

### Desempenho
- **"Atualizar" do ML mais rápido + cronometragem por fase:** a fase cara do
  Atualizar é o filtro de envios (uma chamada `GET /shipments/{id}` por pedido
  não-terminal), que agora roda com **20 workers** (era 12) — mais concorrência
  encurta o tempo total, com o retry/`Retry-After` já existente absorvendo 429.
  Para saber onde o tempo vai antes de otimizar mais, `coletar_grupos` passou a
  registrar cada fase (busca / filtro / extrair, com nº de envios re-consultados
  vs. pulados pelo cache) em **`ml_tempos.log`** (gitignorado, só contagens e
  segundos — espelha o `shopee_tempos.log`). A causa de fundo (pedido `paid`
  ainda não `ready_to_print` é re-consultado a cada Atualizar) fica registrada em
  `PRIORIDADES_TECNICAS.md` como candidato a cache de TTL curto — adiado por tocar
  área de risco (não pode esconder um envio que ficou pronto dentro do TTL).

### Qualidade / operação
- **Fim da churn de git na máquina de operação:** dois atritos recorrentes que
  faziam todo `git pull` em `C:\contador` colidir foram removidos na origem.
  (1) `gravar_json` passa a gravar **LF** (`newline="\n"`) — a GUI reescrevia os
  JSONs versionados (`nomes_sku.json`, `skus_por_anuncio.json`) em CRLF no
  Windows e eles ficavam "modificados" para sempre contra o repo (que é LF).
  (2) as saídas geradas do monitor de APIs (`api-monitor/relatorios/`,
  `snapshots/*.md`, `fetched/`, `logs/`) agora são **gitignoradas** — só a infra
  é versionada; os baselines/relatórios são locais, recriados a cada run.

### Interface
- **Editores de Nomes e SKUs com instância única e travados durante a operação**
  (auditoria consolidada 5.5): abrir o mesmo editor duas vezes partia do mesmo
  snapshot e a última janela a salvar apagava o que a primeira gravou (perda
  silenciosa de nomes ou da **ordem de separação**). Agora um 2º clique no botão
  traz a janela já aberta para frente em vez de abrir outra. Os botões ✏ Nomes /
  🏷 SKUs (e o inline 🏷 Atribuir SKU) ficam **desabilitados durante coleta/
  impressão** — nenhuma edição muta `self.grupos` enquanto a thread de impressão
  os percorre; fechar o editor de Nomes durante uma impressão não reaplica na
  lista em memória (os nomes já foram salvos no arquivo, refletem no próximo
  render).
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
- **Etiqueta divisória reseta o encoding no fim** (auditoria 5.8): a divisória
  ligava `^CI28` (UTF-8) e não desligava; como o `^CI` persiste entre etiquetas,
  as DANFEs/etiquetas do lote impressas depois dela herdavam o encoding. Agora
  fecha com `^CI0` antes do `^XZ` (mesmo cuidado que o carimbo já tinha).
- **Nomes por SKU:** ordem inicial dos SKUs mais usados no topo do
  `nomes_sku.json` + novos produtos cadastrados. A ordem das chaves passou a
  ser **preservada** (é a ordem de separação, não alfabética).
- **Códigos de rastreio de todos os grupos Shopee (não só os de 1 etiqueta):**
  como a etiqueta Shopee não tem o nome do produto, a tela lista o **código
  (AWB) de cada etiqueta já impressa** do grupo, alinhado à esquerda embaixo do
  nome — para conferir qual etiqueta é qual produto ao separar o lote. Em grupos
  de alto volume a área cresce em altura (não espreme). Pendentes não mostram
  código (o AWB só existe depois de organizar/imprimir o envio).
- **A poda do cache de AWB roda mesmo sem códigos novos** (P2 da releitura
  técnica externa): a poda só era persistida quando um cache miss trazia AWB
  novo da rede — no regime normal pós-cache (tudo cache hit) ela nunca rodava
  e o arquivo cresceria para sempre. Agora a poda roda a cada coleta e só
  regrava quando o conteúdo muda. De quebra, o mapa do código passou a
  descrever o bot fielmente (consulta ML/Shopee + impressão só do ML — dizia
  "somente leitura").
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
- **Redação de segredos cobre também a forma JSON e mais chaves** (auditoria
  5.11): `sem_segredos` só redigia `chave=valor` (query-string). Agora também
  redige `"chave": "valor"` (JSON / repr de dict) e inclui `client_secret`/
  `partner_key` além de token/sign/code — defesa em profundidade caso um corpo
  de request seja serializado por engano num texto de erro. Valor numérico sem
  aspas (ex.: `"code": 200`) não é redigido (é status, não segredo).
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
- **A trava do refresh não desiste mais no meio do refresh (Windows)** (P1 da
  releitura técnica externa): o `msvcrt.LK_LOCK` desiste sozinho após ~10s,
  mas o refresh roda HTTP de até 30s dentro da trava — no Windows o segundo
  processo podia degradar **no meio** do refresh do primeiro e disparar um
  refresh paralelo (reabrindo a corrida). Agora a trava aceita `espera=` e o
  caminho do token re-tenta até superar `2×TIMEOUT` (60s > duração máxima):
  degradar depois disso é seguro (o detentor já salvou; a releitura adota).
  Falha rápida (FS sem suporte) continua degradando na hora, e os caminhos do
  estado mantêm o comportamento de sempre. POSIX (CI) já bloqueava
  indefinidamente — o cenário era exclusivo do Windows de produção.
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
- **Alerta pós-horário agora também na Shopee.** `job_alerta_pos_horario`
  percorre as contas ML e, na sequência, a Shopee (loja única) — sinal
  equivalente ao `ready_to_print` do ML: pedido `READY_TO_SHIP` com
  despacho **hoje** (`ship_by_date`). Nova função
  `shopee_api.pedidos_prontos_novos` (par Shopee de
  `filtrar_para_imprimir`+`extrair_itens`), reusando `_itens_de_detalhes`
  extraído de dentro de `grupos_de_detalhes` (sem duplicar a extração de
  SKU/quantidade). Dedup por `order_sn` (string), tratada como mais uma
  chave (`"Shopee"`) no mesmo `alertas_pos_horario.json`. Pula em
  **silêncio** se não houver `credenciais_shopee.json` (setup só-ML
  continua válido, sem logar erro a cada 5 min). `/vendasapos` também passa
  a incluir a seção da Shopee no resumo agregado, automaticamente (a
  função já era genérica por "conta").
- **Alerta pós-horário: formato mais enxuto + resumo agregado (`/vendasapos`).**
  Pedido do dono depois de testar na máquina real: o alerta não mostra mais o
  número do envio (`envio 123456789: ...`) — agora é só `SKU - quantidade`
  (somado quando o mesmo SKU aparece em mais de um envio no mesmo disparo),
  com um cabeçalho curto (`🔔 Venda {conta}`). Além disso, cada disparo passou
  a persistir os itens em `alertas_pos_horario.json` (junto do dedup já
  existente); o novo comando/botão **`/vendasapos`** (🔔 "Vendas após" no
  `/menu`) junta **tudo que já foi avisado hoje**, por conta, com um TOTAL
  por SKU no final — evita que várias vendas caindo em sequência depois das
  8:30 poluam o chat com um alerta cada. Só relê o estado já persistido, não
  refaz nenhuma chamada de API.
- **CLI pra testar o alerta na hora (`bot_telegram.py testar-alerta`):**
  `python bot_telegram.py testar-alerta` (ou `atalhos/'Testar Alerta
  Pos-Horario.bat'`) monta um `Application` de verdade e chama
  `job_alerta_pos_horario()` uma única vez, fora do agendamento de 5 min —
  reusa 100% a lógica já validada. Motivado por confirmar que o envio
  funciona sem precisar esperar o próximo ciclo E uma venda real cair.
- **Auto-start pela tela abandonado; bot agora sobe no login do Windows.**
  As duas "correções reais" abaixo tratavam sintomas de uma mesma causa-raiz
  (a tela roda via `pythonw`, sem console — qualquer `subprocess` disparado
  dali herda handles de stdin/stdout/stderr inválidos) que continuava
  reaparecendo de formas novas. Em vez de seguir caçando o próximo achado, o
  mecanismo de auto-start pela tela (`separador_gui.py` chamando
  `core.iniciar_bot_em_segundo_plano()`, lock de PID em `bot.lock`) foi
  **removido**. No lugar: rode **uma vez**
  `atalhos\registrar-tarefa-bot.ps1` — registra uma tarefa no Agendador de
  Tarefas do Windows (gatilho `AtLogOn`) que sobe `atalhos\'Iniciar Bot
  (auto).bat'` sem janela visível a cada login, num processo criado do zero
  pelo Windows (sem herdar nada quebrado), independente da tela estar
  aberta. Sem lock de PID: uma duplicata eventual é autolimitada pelo
  próprio Telegram (erro 409).
- **Correção real 2 (mesma causa-raiz da anterior, código desde removido):
  "subiu" duas vezes, bot nunca respondia no Telegram.** Mesmo com o `stdin` já corrigido, o `Popen`
  que sobe o `.bat` não redirecionava `stdout`/`stderr` — o `print("Bot
  rodando... Ctrl+C para parar.")` em `bot_telegram.py` (fora do
  `try/finally` que limpa `bot.lock`) derrubava o processo ao herdar um
  stdout inválido do `pythonw`, logo após gravar o lock. O lock ficava preso
  num PID já morto; a tela seguinte via `bot_ja_rodando()==False` e subia
  outro bot por cima, em loop, sem nunca chegar a `app.run_polling()`.
  Corrigido com `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` no
  mesmo `Popen` (o log de verdade já vai pro arquivo via `FileHandler`).
- **Correção real (achada testando na máquina do dono): auto-start do bot
  travava para sempre.** O bot funcionava manual (`Iniciar Bot.bat`) mas
  nunca subia sozinho pela tela, sem nenhum erro no log. Causa: a tela roda
  via `pythonw` (sem console/handles padrão válidos) — sem
  `stdin=subprocess.DEVNULL`, o `subprocess.run` do `tasklist` em
  `_pid_vivo` falhava sempre com `WinError 6`, e o default antigo "em dúvida
  assume vivo" fazia um `bot.lock` travado (de um teste manual anterior)
  bloquear o auto-start **permanentemente** — `bot_ja_rodando()` sempre
  devolvia `True` mesmo com o PID confirmado morto no Gerenciador de
  Tarefas. Corrigido: `stdin=subprocess.DEVNULL` no `tasklist` e no `Popen`
  do `.bat`; default invertido para "em dúvida assume MORTO" (o Telegram já
  rejeita duas instâncias do mesmo bot pollando ao mesmo tempo — erro 409,
  autolimitado — bem menos grave que travar pra sempre).
  `iniciar_bot_em_segundo_plano()` também passou a devolver uma string curta
  (`subiu`/`ja_rodando`/`nao_windows`/`bat_ausente`) que a tela sempre loga
  — antes, um "decidi não subir" sem exceção ficava mudo no log, o que
  atrasou o próprio diagnóstico deste bug.
- **Alerta pós-horário de venda nova pronta pra hoje:** motivado por um
  problema real do dono — venda que cai depois das 8:30 (quando ele já parou
  de checar a tela manualmente) só é vista tarde demais, e o fornecedor já
  não tem mais o produto pra repor no mesmo dia. Novo job
  `job_alerta_pos_horario` (`JobQueue.run_repeating`, a cada 5 min) percorre
  **todas** as contas configuradas e avisa — uma vez por envio — quando surge
  um envio novo já `ready_to_print` com despacho **hoje**; roda sozinho,
  independente do botão Atualizar da tela e de qualquer comando manual.
  Dedup por `shipment_id` num estado próprio (`alertas_pos_horario.json`,
  gitignorado, reseta sozinho na virada do dia) e isola falha por conta
  (mesmo espírito do `ads-monitor/coletar.py`). Reusa 100% a lógica já
  validada do núcleo (`ready_to_print` + `expected_date`,
  `buscar_pedidos`/`filtrar_para_imprimir`/`extrair_itens`) — sem
  reimplementar filtro nenhum da API do ML.
- **A tela sobe o bot sozinha, sem janela, ao abrir:** o alerta acima só
  funciona com o bot rodando, e era fácil esquecer de ligá-lo à parte.
  `separador_gui.py` agora chama `core.iniciar_bot_em_segundo_plano()` na
  abertura — sobe `atalhos/'Iniciar Bot (auto).bat'` (reusa o lançador com
  reinício automático já existente) **sem janela visível**
  (`subprocess.CREATE_NO_WINDOW`), só se o bot ainda não estiver rodando
  (novo lock de PID em `bot.lock`, checado contra o processo de verdade via
  `tasklist` no Windows — nunca duplica). `bot_telegram.py` grava o próprio
  PID ao subir e remove ao encerrar.
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
- **Temporário de saída não casa mais os padrões do monitor da Zebra
  (`tmp_saida` → `tmp_*.part`):** verificação de compatibilidade com o app Zebra
  v1.25.7 constatou que o temporário antigo (`nome.zip.tmp`) **começava com um
  prefixo aceito** pelo monitor — só a extensão `.tmp` o salvava do glob
  (dependência frágil do matching por extensão do outro app). Agora o temporário
  segue o formato que o contrato do Zebra pede (item B): prefixo `tmp_` +
  extensão `.part`, que não casa prefixo nem `*.zip`/`*.plain`. Teste-guardião
  novo; contrato v1.25.7 (duplicata por nome+tamanho+mtime, UTF-8 obrigatório,
  "Parar" descarta fila) registrado na ARQUITETURA. Fora isso, a verificação
  não achou conflito: nomes únicos, reimpressão gera arquivo novo, carimbo
  `^CI28`/`^CI0` já é o formato recomendado. **Compatibilidade confirmada
  formalmente pelos dois lados** (resposta do app Zebra, 20/07): nenhuma
  mudança exigida de nenhum app; o filtro por extensão do monitor é garantido
  estável, e a separadora do Zebra mantém `^CI28` persistente de propósito
  (inócuo para nós).
- **Trava de segurança contra imprimir o mesmo lote em dobro (Shopee/ML):** na
  Shopee a etiqueta sai fisicamente **durante a busca** (o ZIP cai na Downloads e
  a Zebra imprime na hora), mas o app só marca o estado **depois** que você
  responde "as etiquetas saíram certo?". No intervalo, o botão voltava a ficar
  clicável e o lote continuava "pendente" — um 2º clique (fácil de dar quando a
  gente esquece que já apertou) reimprimia tudo. Agora o app fica **travado de
  ponta a ponta**: `ocupado` desde a confirmação de "Organizar envio" até a
  resposta de "saíram certo?", então um clique no meio é recusado. Cancelar o
  organizar destrava; a trava também é liberada se a confirmação falhar.
- **`config.json` é atualizado por chave, não regravado inteiro** (auditoria
  consolidada 5.4): cada GUI guardava `self.config` desde a abertura e, ao salvar
  qualquer preferência, regravava o dicionário inteiro — a última gravação
  revertia em silêncio as chaves que outra instância havia mudado (ex.: fechar
  uma GUI aberta de manhã desfazia a conta/marketplace trocados na outra).
  Agora `core.atualizar_config(**chaves)` relê o disco **sob trava**, aplica só
  as chaves daquele evento e grava — a GUI não regrava preferência que não
  mexeu. O saneamento continua valendo na releitura.
- **`estado_shopee.json` agora é podado no disco, não só em memória**
  (auditoria 5.7): a Shopee usava `persistir_poda=False`, então cada marcação
  regravava o arquivo com as entradas antigas intactas e ele crescia sem limite.
  Agora usa `persistir_poda=True` como o ML (a regravação já roda sob trava e
  relendo o disco, então não apaga marcação concorrente).
- **`gerar_etiqueta` (Shopee) valida o AWB de TODOS os pedidos pedidos, não só
  as chaves do mapa** (auditoria 5.9): `order_sns=[A,B]` com `rastreios={A:…}`
  passava e B seguia sem `tracking_number` até o erro remoto
  `tracking_number_invalid`. Agora calcula os ausentes a partir de `order_sns`
  (compara por str), aborta antes do create citando o pedido sem AWB, e rejeita
  lista de pedidos vazia.
- **Pedido Shopee já organizado (mas com AWB ainda em processamento) não vira
  mais falso erro** (auditoria consolidada 5.3): se o envio já fora organizado
  — manualmente no painel, ou pelo lote com resposta ambígua — mas o AWB ainda
  não saíra, `numero_rastreio` voltava vazio e `info_needed` vinha `{}`; o
  código lia a ausência de `dropoff` como "não oferece Postagem" e mandava
  "organize manualmente" o que já estava organizado. Agora `organizar_envio`
  chama `envio_ja_arranjado` (helper que já existia, testado, mas **sem nenhum
  chamador de produção** — a falta de uso era o próprio bug): quando o envio já
  está arranjado, **pula o `ship_order` e só aguarda o AWB** em vez de recusar.
  Só recusa como incompatível o pedido que realmente exige outro método e ainda
  não foi organizado.
- **Estado corrompido não some mais em silêncio** (auditoria consolidada 5.2):
  um `estado_grupos.json`/`estado_shopee.json` ilegível (antivírus, disco,
  edição manual) era lido como `{}` — indistinguível de ausente — e a **próxima
  marcação gravava por cima**, destruindo o histórico recuperável (todos os
  grupos do dia voltavam a PENDENTE, sem explicação). Agora o caminho do estado
  usa `estado.ler_estado`: um arquivo que existe mas não parseia (ou não é um
  dict) é **movido para `.corrupto`** (conteúdo preservado) com aviso no
  `separador.log`, e a leitura recomeça vazia — a gravação seguinte cria um
  arquivo novo sem apagar o antigo. Ausência continua `{}` silencioso (caso
  legítimo); uma falha **transitória** de leitura (OneDrive/antivírus prendendo
  o arquivo) **não** renomeia (o arquivo pode estar intacto).
- **ZIP na Downloads nunca sobrescreve um lote que a Zebra ainda não imprimiu**
  (auditoria consolidada 5.1): o nome do arquivo era determinístico
  (`etiqueta de envio - PRODUTO.zip`), então dois trabalhos com o mesmo rótulo
  (dois lotes iguais seguidos, ou uma reimpressão) apontavam para o **mesmo
  arquivo** — se o monitor estivesse lento/desligado, o segundo `replace` comia
  o primeiro em silêncio e um lote se perdia. Agora cada saída recebe um carimbo
  de tempo único (`nome_saida_unico`, ML e Shopee), preservando o prefixo que o
  monitor reconhece; se colidir, soma `-1`, `-2`… até um nome livre.
- **A geração relê o estado do disco antes de calcular os pendentes**
  (auditoria 5.1): os pendentes vinham de `self.estado` fixado no último
  Atualizar — uma marcação gravada por fora (CLI, ou uma 2ª GUI aberta por
  engano) não era respeitada e o pedido sairia em dobro. Agora
  `_gerar_sem_marcar_thread` relê via `prov.carregar_estado()` antes de gerar;
  falha de releitura não trava a impressão (segue com o estado em memória).
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
- **Monitor semanal das APIs (`api-monitor/`):** checagem automática (uma vez por
  semana, via `claude -p` agendado no Windows) de mudanças na documentação/
  políticas das APIs do Mercado Livre e da Shopee — só páginas públicas, sem
  tocar dados da conta. Estrutura, prompt reutilizável, scripts PowerShell de
  execução e de registro no Agendador de Tarefas, e relatórios por data. O
  baseline é criado na primeira execução local (o ambiente de nuvem da
  configuração inicial não alcançava as fontes — ver `api-monitor/README.md`).
  As fontes da Shopee são SPAs (fetch direto vem vazio), então o
  `run-semanal.ps1` as **pré-renderiza via Playwright dirigindo o Edge do
  sistema** (`fetch-render.py`; `channel=msedge`, não baixa navegador — só
  `pip install playwright`) e o Claude compara os arquivos locais. (O Edge
  `--dump-dom` por linha de comando devolvia DOM vazio no `--headless=new`.)
  ML API Docs via WebFetch; ML Novidades exige login (sem alternativa pública)
  → marcada como bloqueada.
- **Build do GitHub Pages para de falhar (`docs/.nojekyll`):** o Pages publica a
  pasta `docs/` (a página estática de autorização da Shopee, `index.html`) e
  rodava o Jekyll em cima dela sem necessidade — o build quebrava e mandava um ❌
  a cada push no `main`. Um `.nojekyll` vazio desliga o Jekyll: os arquivos são
  publicados como estão (a página OAuth serve idêntica) e o build fica verde.
- **Linter no CI (`ruff`)** (auditoria 5.13): um job novo roda `ruff check .` em
  cada PR/push, pegando import morto / nome indefinido antes da revisão manual
  (a classe que já foi achada à mão). Config em `ruff.toml`, começando pelas
  regras `F` + `E9` (zero ruído hoje); `E501` (linha longa) fica deferido de
  propósito.
- **Ferramenta de screenshot da GUI usa `subprocess.run`, não `os.system`**
  (auditoria 5.15): o caminho de saída vinha de `sys.argv` e era concatenado sem
  escape num comando de shell — espaços quebravam, metacaracteres eram
  interpretados. Restrito à ferramenta de dev/CI, mas endurecido.
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
