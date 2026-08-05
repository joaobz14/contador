# Prioridades Tecnicas Sugeridas

Este documento registra uma lista de melhorias recomendadas para evoluir o projeto
com baixo risco. O sistema ja esta operacional; portanto, a ideia nao e reescrever
o que funciona, mas fortalecer a base para manutencao futura.

## Principio geral

Evitar refatoracoes grandes e esteticas. As mudancas devem ser pequenas,
testaveis e sempre preservar as regras operacionais mais importantes:

- A GUI gera etiquetas primeiro e so marca como impresso depois da confirmacao fisica.
- Reimpressao nao altera o estado de impresso.
- O estado de impressao e separado por marketplace, conta e dia de despacho.
- Tokens e credenciais devem continuar sendo tratados com cuidado, sem corridas de refresh.
- Shopee e Mercado Livre devem continuar escondidos atras da interface de provedores.

## 1. Separar responsabilidades do nucleo ML

O arquivo `separador_etiquetas_ml.py` concentra muitas responsabilidades:

- API do Mercado Livre.
- Token e credenciais.
- Estado de impresso.
- Cache de produtos e envios.
- Agrupamento de pedidos.
- Geracao de ZPL.
- Carimbo e etiqueta divisoria.
- ZIP final para a Zebra.
- CLI.

Ele funciona, mas virou o ponto de maior risco para mudancas. A sugestao e extrair
aos poucos partes pequenas para modulos dedicados, por exemplo:

- `estado.py`
- `zpl.py`
- `ml_api.py`
- `agrupamento.py`

Essa separacao deve ser incremental: mover uma responsabilidade por vez, mantendo
os testes existentes passando antes de seguir para a proxima.

## 2. Criar uma camada comum de estado de impressao

ML e Shopee compartilham conceitos muito parecidos:

- `marcar_impresso`
- `status_grupo`
- `envios_pendentes`
- leitura tolerante do estado
- mescla com o disco antes de gravar
- limpeza de registros antigos

Como estado de impressao e uma parte critica do sistema, vale criar um modulo
dedicado e bem testado para essa regra. Isso reduziria duplicacao e deixaria mais
dificil quebrar a garantia de que nenhum envio sera marcado errado.

Esta e a melhoria estrutural mais recomendada para comecar.

## 3. Explicitar melhor o contrato de impressao da GUI

A GUI ja segue o fluxo correto:

1. Gera as etiquetas.
2. Envia o ZIP para a pasta monitorada pela Zebra.
3. Pergunta se as etiquetas sairam corretamente.
4. So entao marca os grupos como impressos.

Esse contrato deveria ficar ainda mais evidente no codigo, com nomes de metodos
e comentarios que dificultem alteracoes acidentais. Exemplos de nomes mais
explicitos:

- `gerar_etiquetas_sem_marcar`
- `confirmar_e_marcar_impressas`
- `reimprimir_sem_alterar_estado`

O objetivo nao e mudar comportamento, apenas deixar a intencao mais protegida
para quem for mexer no codigo depois.

## 4. Melhorar logs e diagnostico operacional

Como o projeto roda em operacao real, logs simples ajudariam a entender problemas
sem precisar reproduzir tudo no debugger. Eventos uteis para registrar:

- marketplace usado
- conta ativa
- dia de despacho escolhido
- quantidade de grupos e etiquetas geradas
- caminho do ZIP criado
- se o usuario confirmou ou nao a impressao
- falhas de API da Shopee ou do Mercado Livre
- pedidos que falharam em lote parcial

Um arquivo como `logs/app.log` ou `separador.log` ja seria suficiente, desde que
nao registre segredos, tokens ou dados sensiveis.

## 5. Criar uma tela ou modo de diagnostico na GUI

Uma pequena area de diagnostico ajudaria no suporte do dia a dia. Ela poderia
mostrar informacoes como:

- marketplace atual
- conta ativa
- arquivo de estado em uso
- pasta Downloads usada para os ZIPs
- modo de identificacao atual
- ultima atualizacao
- total de grupos pendentes, parciais e impressos
- versao do Python

Isso nao precisa aparecer para todo usuario o tempo todo. Pode ser uma janela
simples aberta por um botao discreto ou por um modo de diagnostico.

## 6. Isolar melhor o modo Mercado Livre "Ambas"

O modo `ProvedorMLAmbas` e poderoso, mas delicado. Ele alterna conta, token,
estado e impressao por conta, enquanto apresenta uma lista unica para o usuario.

Por isso, ele merece tratamento de area critica:

- manter testes fortes para fusao de grupos
- garantir que cada envio seja impresso com o token da conta correta
- garantir que o estado seja marcado no arquivo da conta correta
- evitar persistir o modo "Ambas" por acidente
- considerar mover essa classe para um modulo proprio se ela continuar crescendo

### 6.1. Otimizacao futura: coletar as contas em paralelo (baixa prioridade)

Hoje o `ProvedorMLAmbas.coletar` roda as contas EM SERIE (um `for conta`), entao o
"Atualizar" leva `tempo(conta1) + tempo(conta2)`. Dentro de cada conta a coleta ja
e bem paralela (paginas 8x, envios 12x, detalhes 8x), entao o unico ganho relevante
seria rodar as DUAS contas em paralelo -> cairia para `~max(conta1, conta2)`,
aproximadamente a metade (com 2 contas).

**Por que NAO fazer agora:** ganho pequeno e pontual (o modo Ambas so e usado nos
dias de motorista unico; poucos segundos). E o custo mexe justo na parte sensivel:
o nucleo guarda os caminhos de cache por conta em GLOBAIS (`ARQUIVO_CACHE`,
`ARQUIVO_ENVIOS_CACHE`), trocadas por `definir_conta()`. Paralelizar ingenuamente
faz as threads disputarem essas globais -> uma conta grava o cache da outra
(corrupcao silenciosa de cache/estado). Risco alto para ganho baixo.

**Como fazer com seguranca, SE valer a pena um dia:** passar os caminhos de cache
como PARAMETRO (default = global atual, retrocompatível) por `coletar_grupos`,
`filtrar_para_imprimir`, `extrair_itens`/`buscar_detalhes` e os 4 helpers de cache;
no Ambas, pegar os tokens em serie (instantaneo, em cache) e disparar as duas
coletas em paralelo com o caminho de cache de cada conta explicito (nenhuma global
tocada na parte paralela). Tratar tambem a barra de progresso (agregar as duas) e o
aumento de requisicoes concorrentes (o `_com_retry` ja faz backoff em 429).

**Quando reconsiderar:** se o Ambas virar uso diario, ou ao adicionar mais contas
(com 3-4 contas o serial comeca a incomodar de verdade).

## 7. Padronizar encoding e ambiente Windows

O projeto e usado em Windows e alguns textos com acento podem aparecer quebrados
dependendo do terminal. Vale garantir:

- arquivos fonte e docs em UTF-8
- scripts `.bat` chamando Python de forma consistente
- logs gravados com `encoding="utf-8"`
- mensagens criticas sem depender de configuracao especial do console

Essa mudanca nao afeta regra de negocio, mas melhora manutencao e suporte.

## 8. Cache de TTL curto para envios ML nao-prontos (desempenho do Atualizar)

A fase mais cara do "Atualizar" do ML e o filtro de envios (`filtrar_para_imprimir`):
uma chamada `GET /shipments/{id}` por pedido nao-terminal. O cache `envios_cache.json`
so guarda status **terminais**, entao um pedido `paid` que ainda nao virou
`ready_to_print` e re-consultado a **cada** Atualizar. Conforme o volume de pedidos
pagos-nao-despachados na janela de `DIAS_JANELA=30` cresce, essa fase cresce junto.

Ja feito (baixo risco): filtro subiu para 20 workers e `coletar_grupos` registra os
tempos por fase em `ml_tempos.log` (via `_log_tempos`) — inclui quantos envios foram
re-consultados vs. pulados pelo cache. **Meca com esse log antes de decidir o passo
seguinte.**

Passo seguinte (medio risco, adiado): guardar tambem os **nao-terminais-e-nao-prontos**
com um **TTL curto** (ex.: algumas horas), para o Atualizar repetido no mesmo dia nao
re-consultar todos. O risco e **esconder um envio que virou `ready_to_print` dentro do
TTL** — o operador nao veria o pronto ate o TTL expirar. So implementar apos definir um
TTL conservador e aceitar explicitamente o trade-off (ou dar um "forcar releitura" que
ignora o cache curto). Nao mexer sem essa decisao.

**Urgencia reduzida (auditoria de APIs, 2026-07):** o maior consumidor dessa fase
era o **alerta pos-horario do bot** (ciclo de 5 min, 24h, janela cheia de 30 dias —
~90-100 mil chamadas/dia). Ele agora roda so das 07:00 as 20:59 e busca com janela
dedicada de 5 dias (`DIAS_JANELA_ALERTA`), cortando ~95% disso. O TTL continua
valendo para o **Atualizar manual** (que segue com a janela cheia), mas sem a
pressao de antes.

## 9. Resumo do dia: incluir reimpressao (decisao de v1)

O "📋 Resumo do dia" (`historico.py`) conta o que foi impresso pela primeira vez
— o gancho e o callback `registrar` de `estado.marcar_impresso`, que recebe so o
delta de ids novos. **Reimpressao nao passa por `marcar_impresso`** (por design,
para nao alterar o estado), entao **nao aparece no resumo**. Ficou assim de
proposito na v1 (o caso comum e "o que preparei/despachei hoje", que a marcacao
cobre). Se um dia o resumo precisar refletir tambem reimpressoes fisicas, o passo
e chamar `historico.registrar` tambem no caminho de reimpressao (com um marcador
`reimpressao=True` para distinguir na agregacao) — sem tocar no estado.

## 10. Monitor de Product Ads: margem por SKU (bloqueado — atribuicao ja pronta)

**Atribuicao por ad_group/item — FEITO.** `ads-monitor/coletar.py` ja grava a
cadeia **campanha -> ad_group -> item_id -> SKU** (tabelas `ad_groups_diarios` e
`ad_group_itens_diarios`), via o fluxo por `ad_group_id` (substituiu o antigo
endpoint de metricas por item, descontinuado em 27/05/2026 — doc "Product Ads
para Catalogo e User Products"), validado antes com chamada real de leitura
(`tools/diag_ads.py`, passo 5, PR #167/#168). Paginacao coberta (`offset`/`total`).
Construido **antes** de existir a fonte de margem, por decisao explicita do dono
("podemos construir a implementacao mesmo sem as fontes, acrescentamos depois").

**Resolucao de SKU — corrigida com dado real.** A primeira versao so consultava
`skus_por_anuncio.json` local e resolveu **0 de 468 itens** rodando contra as
contas reais — esse mapa e manual e pequeno (so p/ anuncios sem SKU adotados na
tela), nao um resolvedor geral; a maioria dos produtos tem `seller_sku`
cadastrado direto no anuncio. Corrigido estendendo o cache do nucleo
(`itens_cache.json`, via `_detalhe_item` em `separador_etiquetas_ml.py`) com o
campo `seller_custom_field` — mesma chamada `GET /items/{id}` que a impressao ja
faz, sem custo extra de rede. `_resolver_skus` (ads-monitor) prioriza esse
`seller_sku` real e cai pro mapa de adocao so quando ausente, mesma prioridade
de `identidade()` no nucleo.

Ressalva que continua valendo: **`ad_group` nao e 1:1 com item.** `ad_group_type`
pode ser `FAMILY` (variacoes) ou `CATALOG` (**varios vendedores concorrendo no
mesmo anuncio** — visto 1 caso com 7 `item_id` diferentes num so ad_group). A API
nao quebra metrica por item dentro de um ad_group multi-item — a granularidade
mais fina que ela da e o ad_group, entao um SKU que so aparece dentro de um
ad_group multi-item nao tem gasto/venda exclusivo dele, so o do grupo inteiro.

**Limitacao aceita (nao vale a pena perseguir agora): item com variacoes de SKU
diferentes fica sem SKU exato.** Investigado com dado real (`tools/diag_seller_sku.py
--item`, PR #173): pra um item com 2 variacoes (127V=A01, 220V=A01F, confirmadas
no painel do vendedor), o campo `seller_custom_field` vem **vazio** nas duas
variacoes (a conta usa outro mecanismo pro SKU, possivelmente ligado a
`inventory_id`/`user_product_id` — nao investigado a fundo) — E a resposta de
`GET /ad_groups/{id}/ads` **nao tem `variation_id`**, entao mesmo achando o campo
certo nao daria pra saber se o anuncio e da variacao 127V ou 220V (Product Ads
opera no nivel do item_id, nao da variacao). **Confirmado oficialmente** (dono
perguntou ao assistente de IA do Mercado Livre): a API de Product Ads nao expoe
SKU nem variacao-SKU em nenhuma resposta; o agrupamento por variante usa so
`family_id`/`catalog_product_id`/`parent_id`/`ad_group_external_id` — pra SKU e
preciso relacionar `item_id` com "o recurso onde o SKU esteja disponivel" (fora
do Product Ads). Nao e bug nem falta de campo escondido — e a API mesmo. Aceito
como limitacao: esses itens ficam sem SKU no `ads-monitor`. Nao perseguir sem um
motivo concreto (a margem por SKU nem existe ainda).

**Agendamento diario — FEITO.** `ads-monitor/run-diario.ps1` +
`ads-monitor/registrar-tarefa.ps1` (mesmo padrao do `api-monitor/`,
`Register-ScheduledTask` nativo) registram uma tarefa diaria as 11:00 (depois
das 10:00 GMT-3 de fechamento das metricas). Sem isso, so havia 1 dia de
historico coletado manualmente — e o pedido original explicito e nunca
recomendar em cima de 1 dia de dado, entao isso destravava qualquer proxima
etapa (motor de recomendacao, com ou sem margem).

**Motor de recomendacao (sinais SEM margem) — FEITO.** `ads-monitor/recomendar.py`
gera recomendacoes no formato do pedido original (problema/evidencia/acao/
justificativa/impacto/risco/confianca/urgencia/prazo de reavaliacao/metrica de
verificacao) usando so os 3 sinais que a propria API ja calcula: orcamento
insuficiente, ranking baixo e ROAS abaixo do `roas_target`. Recomendacao de
aumentar investimento sai marcada "condicionada a validacao da margem"; ROAS
abaixo do alvo nao (reducao de risco, nao aposta). Trava contra dado fraco:
`MIN_DIAS=3` dias + `MIN_CLICKS=20` cliques na janela — campanha sem isso fica
"monitorando", sem recomendacao (regra do pedido original: nunca recomendar em
cima de 1 dia). Construido **depois** do agendamento diario (item acima) ficar
pronto, senao `MIN_DIAS` nunca seria atingido organicamente.

**Bloqueado por decisao do dono:** ainda nao existe fonte de custo/margem por SKU
organizada (confirmado — nao ha nada no projeto hoje: nenhum arquivo, nenhuma
constante). As recomendacoes de AUMENTAR investimento (as unicas que dependem de
margem) so podem sair de "condicionada a validacao" pra uma recomendacao plena
quando essa fonte existir (formato ainda em aberto: arquivo local tipo
`nomes_sku.json`, importador de planilha, ou outro).

**Camada de narrativa opcional (`narrar.py`) — FEITO.** Motivada por um monitor
irmao do mesmo Product Ads construido em paralelo (n8n + DeepSeek): ao comparar
os dois, decisao explicita foi manter ambos com papeis diferentes (n8n =
narrativa/apresentacao/entrega; `ads-monitor/` = historico canonico + regras +
SKU), mas trazer a narrativa em IA tambem pra este lado, por cima do motor ja
existente. `narrar.py` e aditivo/opcional (usa `claude -p`, mesmo padrao do
`api-monitor/`) — narra o que `recomendar.py` ja calculou sem inventar
conclusao nova; se falhar ou nao rodar, `recomendar.py` continua funcionando
sozinho, determinístico, como antes.

## 11. Shopee: migrar `ship_order` pra checar por `get_package_detail` (respostas recebidas — migração ainda não implementada)

**ENCERRADO em 05/08/2026 pela resposta final do suporte** — ver o desfecho no
fim deste item. O que segue e o historico, mantido porque as duas rodadas de
correcao continuam valendo por si (nao reenviar pedido ja arranjado e o
comportamento certo, com ou sem metrica).

**Contexto:** a Shopee mandou um requisito de qualidade obrigatorio (prazo,
risco de penalidade) exigindo success rate > 90% por 7 dias consecutivos em
`v2.logistics.ship_order`. O FAQ deles lista "This parcel has already been
shipped" e "The order is being allocated, please wait" como causas
documentadas de erro — reenviar um pedido ja arranjado, ou enviar cedo
demais.

**Corrigido em 2 rodadas (achado 2026-07) — ver `docs/ARQUITETURA.md` /
`CLAUDE.md` (seção "Compliance da Shopee") pro detalhe tecnico completo:**
- Rodada 1: `_organizar_varios` mandava todo pedido sem AWB pro
  `batch_ship_order` sem checar se ja estava arranjado (so o caminho
  individual `organizar_envio` checava). Corrigido com
  `_filtrar_ja_arranjados` (nova etapa 1.5, antes do batch).
- Rodada 2 (apos as respostas do suporte abaixo): a rodada 1 nao resolvia o
  problema de verdade — um pedido que passa pelo batch mas fica sem AWB (so
  por causa do timeout curto de ~40s) caia no fallback individual, que
  reenviava `ship_order` com o status ainda desatualizado (propagacao pode
  levar ate 15-20 min, confirmado pelo suporte). Corrigido: esses pedidos
  nao caem mais no individual, viram pendencia de confirmacao ("tente de
  novo em alguns minutos"). Defesa adicional em `organizar_envio`: catch pra
  "already been shipped" (nao propaga como erro) e retry curto pra "being
  allocated" (transiente, segundo a propria Shopee).

**Respostas do suporte da Shopee (2026-07, via IA de suporte deles):**
1. `search_package_list` aceita `package_status` (int) e `invoice_pending`
   (bool); a resposta **ja inclui `is_shipment_arranged` por pacote** —
   nao precisaria de `get_package_detail` separado so pra essa checagem.
2. `get_package_detail`: `fulfillment_status` (string, enum incluindo
   `LOGISTICS_READY` — lista completa nao confirmada), `is_shipment_arranged`
   (bool), `package_number` (**um `order_sn` pode ter mais de um
   `package_number`** — mudanca de modelo de identidade relevante).
3. Se `ship_order` passou a aceitar/exigir `package_number` alem de
   `order_sn`: **nao confirmado** pelo suporte, recomendaram testar/validar
   direto.
4. `batch_ship_order` **NAO conta** pra mesma metrica de sucesso do
   `ship_order` singular (confirmado) — o foco da correcao e so as chamadas
   ao endpoint singular.
5. Codigos/mensagens exatos: `logistics.package_already_shipped` / "This
   parcel has already been shipped"; `logistics.error_param` / "The order
   is being allocated, please wait until the allocate is completed." (ja
   usados na correcao da rodada 2).
6. Propagacao apos `ship_order`/`batch_ship_order`: suporte recomendou
   esperar **15-20 minutos** antes de reconsultar — usado pra decidir NAO
   reenviar no mesmo ciclo (rodada 2).

**DESFECHO (e-mail do suporte, 05/08/2026):** "A task completa-se sozinha com
7 dias consecutivos. Embora, atualmente, se houver dias **sem chamada**, quebra
o ciclo. Isso ja esta em melhoria interna e **nao ha penalizacao ativa no
momento**." Duas conclusoes:

1. **Sem prazo e sem risco.** A pressao que gerou as duas rodadas nao existe
   mais. As correcoes ficam porque estao certas, nao porque sao exigidas.
2. **A sequencia de 7 dias e inalcancavel nesta operacao — por construcao, nao
   por falha.** O app manda tudo pelo `batch_ship_order` (que o suporte ja
   confirmou nao contar pra metrica) e o caminho individual pula o `ship_order`
   quando o envio ja esta arranjado; o singular so e chamado quando o endpoint
   de lote esta indisponivel por inteiro. Nao havendo chamadas, nao ha o que
   medir — e fim de semana sem despacho quebraria o ciclo de qualquer jeito.

**NAO force chamadas para manter o ciclo.** Seria preciso chamar o singular em
pedido ja organizado, que produz exatamente `package_already_shipped` — o erro
que a metrica penaliza. Manipular o indicador o derrubaria.

**Ainda pendente (nao urgente — nunca foi, e agora menos ainda):** migrar de fato pra `search_package_list`/`get_package_detail`
em vez de `get_shipping_parameter`/`info_needed`. E uma mudanca maior do que
parece: `package_number` pode ser 1:N com `order_sn`, o que exigiria repensar
a identidade usada em `estado.py`/`Grupo.shipment_ids` (hoje tudo indexado
por `order_sn`). Vale uma avaliacao separada, com mais tempo, nao sob pressao
de prazo — a resposta #3 tambem ainda nao esta confirmada (se `ship_order`
precisa de `package_number`), o que e pre-requisito pra saber se da pra
migrar so a LEITURA (status) ou se a ESCRITA (`ship_order`) tambem muda.

## 12. Avisar o motorista do dia nas contas ML — NAO FAZER (a API publica nao expoe o dado)

**Ideia do dono:** hoje ele lembra na mao se "o motorista e o mesmo nas duas
contas" e clica (ou nao) no 🌐 Ambas. O app poderia perceber isso sozinho.

**Os DOIS lados interessam** (pedido do dono): avisar quando os motoristas sao
os MESMOS (sinal de que o Ambas faz sentido) **e** quando sao DIFERENTES (sinal
de que nao faz). O aviso negativo nao e redundante — hoje o "diferentes" e
implicito (o dono nao ve aviso nenhum e tem que lembrar sozinho), e um aviso
explicito transforma silencio em informacao confirmada. Em nenhum dos dois
casos o app seleciona coisa alguma: ele so informa, o dono confere e decide.

**A base tecnica ja existe e foi confirmada na doc oficial do ML (2026-07-23):**

```
GET /users/{USER_ID}/shipping/schedule/{LOGISTIC_TYPE}
```

devolve, por dia da semana, `detail[]` com `from`/`to`/`cutoff`, `carrier{id,name}`,
`vehicle{license_plate,...}` e `driver{id,name}`. Tem **`driver.id`** — ID estavel,
bem melhor que casar por nome.

**Ferramenta de diagnostico pronta** (so-leitura, nenhum POST, mascara nome do
motorista e placa):

```
python tools/diag_coleta.py --comparar Cozilatti Gastromaq
```

Responde `MESMO MOTORISTA hoje (driver.id X)` ou `MOTORISTAS DIFERENTES`.

### O BLOQUEIO — TESTE FEITO em 2026-07-30, resultado NEGATIVO neste endpoint

```
comparando coleta de HOJE (thursday) entre 'Cozilatti' e 'Gastromaq'
  Cozilatti: seller=560338057 logistica=cross_docking HTTP=200 driver.id=None carrier.id=None
  Gastromaq: seller=769139323 logistica=cross_docking HTTP=200 driver.id=None carrier.id=None
```

**O dado EXISTE — nossa consulta e que nao o traz.** No mesmo dia, o painel do ML
das DUAS contas mostrava o card "Proximo envio" com coleta programada
(13h45-15h45) e o **mesmo motorista** e a **mesma placa** nas duas. Ou seja: a
premissa de negocio esta **confirmada** (o mesmo motorista atende as duas contas
no mesmo dia, e o ML sabe disso); o que falhou foi a fonte que escolhemos.

O `GET /users/{id}/shipping/schedule/{logistic_type}` respondeu **200** no
`cross_docking` nas duas contas, mas sem `driver.id` nem `carrier.id`.

**Pista do proximo passo:** o card do painel diz **"Requer o codigo de
autorizacao"**. Codigo de autorizacao de coleta e dado que costuma viver no
**envio/coleta**, nao no cronograma SEMANAL da conta. Hipotese principal: o
motorista do dia esta numa API por envio (ou de coleta agendada), e o
`schedule/{logistic_type}` so descreve as JANELAS recorrentes da semana.

**Diagnostico que fecha a questao** (`--cru`, acrescentado em 2026-07-30):

```
python tools/diag_coleta.py --cru Cozilatti
```

Ele imprime o veredito de `_porque_sem_driver` — que separa as causas, porque
cada uma pede acao diferente:

| Veredito | O que significa | Acao |
|---|---|---|
| `detail[]` VAZIO | o cronograma semanal nao reflete a coleta do dia | endpoint errado → procurar a API por envio/coleta |
| `detail[]` sem a chave `driver` | o campo mudou de nome/lugar | achar o novo nome (o despejo cru lista as chaves) |
| `driver` sem `id` | vem o nome mas nao o ID | casar por nome + carrier (pior, mas possivel) |
| nao respondeu 200 | permissao/logistica | conferir escopo do token |

E despeja a resposta crua com nome/placa/telefone **mascarados**
(`_mascarar_fundo` preserva a ESTRUTURA e esconde a pessoa), entao a saida pode
ser colada numa conversa sem expor dado pessoal.

### VEREDITO DO `--cru` (2026-07-30): o endpoint e um GABARITO semanal

O despejo cru fechou a questao. O `schedule/{logistic_type}` devolve o **molde
das janelas recorrentes**, nao a coleta do dia:

| Vem preenchido | Vem VAZIO em TODOS os 7 dias |
|---|---|
| `from`, `to`, `cutoff` | `date: ""` |
| `facility_id` (`BRXSP14`) | `carrier.id`, `carrier.name` |
| `work`, `logistic_type` | `vehicle.id`, `license_plate`, `vehicle_type` |
| `milkrun_same_day` | **`driver.id`, `driver.name`** |

(Seg-sex 13h45-15h45 com corte 08h45; seg e ter com 2a janela 14h45-16h45;
sab/dom `work: false`. Bate com o horario do card do painel — e a mesma coleta,
sem a identificacao de quem vem.)

A estrutura TEM `driver`, mas o ML nunca a popula ai. **Nenhum ajuste de campo
resolve** — a fonte esta errada, ponto.

**A pista do "codigo de autorizacao" tambem caiu.** A doc oficial diz que ele e
um codigo **fixo do vendedor** (Configuracoes > Preferencias de venda > Codigos
de autorizacao) que o motorista digita — nao e por motorista nem por envio.

### Ultimo candidato barato: `GET /shipments/{id}`

O nucleo **ja chama** esse endpoint para todo pedido nao-terminal em
`filtrar_para_imprimir`. Se o motorista estiver no detalhe do envio, a
funcionalidade sai de **graca** (zero requisicao nova).

```
python tools/diag_coleta.py --envio Cozilatti
```

`_caminhos_de_interesse` varre o payload e reporta so as chaves de
coleta/motorista. **Nao despeja o payload inteiro de proposito:** envio carrega
nome e endereco do COMPRADOR, e um despejo cru ali vazaria dado pessoal de
terceiro. Nome do motorista, placa e o codigo de autorizacao saem mascarados; o
`driver.id` sai em claro, porque e o que precisamos comparar.

### VEREDITO FINAL do `--envio` (2026-07-30): ENCERRADO como "nao fazer"

```
envio 47640966807: status=ready_to_ship
  origin.shipping_address.agency.*       = (vazio)
  destination.shipping_address.agency.*  = (vazio)
  origin.node / .shipping_address.node   = (vazio)
  lead_time.pickup_promise.from / .to    = None
  lead_time.estimated_schedule_limit.date= (vazio)
```

**Nenhuma chave `driver`, `vehicle` ou `carrier` no payload do envio** — e elas
apareceriam mesmo VAZIAS, porque o varredor reporta chave de interesse ainda que
sem valor. Elas nao existem ali. O que existe (`agency`, `node`,
`pickup_promise`) vem todo vazio.

**Conclusao: a API publica do ML nao expoe o motorista da coleta do dia.** As
duas fontes plausiveis foram testadas com dado real e as duas sao negativas:

| Fonte | Resultado |
|---|---|
| `GET /users/{id}/shipping/schedule/{logistic_type}` | gabarito semanal; `driver`/`carrier`/`vehicle` sempre vazios |
| `GET /shipments/{id}` (que o nucleo JA chama) | nao tem nem a chave |

O painel do vendedor mostra motorista e placa, entao o dado existe do lado do ML
— mas por endpoint **interno**, fora da API publica. Nao ha como consumi-lo de
forma suportada.

### O que fica no lugar

**Nada muda:** o 🌐 Ambas continua sendo **escolha manual**, como sempre foi. O
dono ja sabe, olhando o painel, se o motorista e o mesmo — e clica. O custo de
nao ter a automacao e um clique consciente por dia de motorista unico.

### O que reabriria este item (o 1o ja foi descartado)

1. ~~`--chaves`~~ **JA RODADO em 2026-07-30 — nao reabre.** O despejo das
   **181 chaves** do envio nao tem `driver`, `vehicle`, `plate`, `courier`,
   `collector`, `operator` nem `motorista`. Os 3 "candidatos" que o filtro
   levantou nao servem:
   - `origin/destination.shipping_address.agency.carrier_id` — e a **agencia**
     (o Place/ponto), nao quem dirige; e vem vazio;
   - `lead_time.pickup_promise.from`/`.to` — e **janela de horario**, nao pessoa;
     e veio `None`.

   Ou seja: **nao ha campo de motorista com nome nenhum** no payload do envio.
   Nao precisa rodar de novo — este caminho esta fechado por evidencia, nao por
   suposicao.
2. **Perguntar ao suporte/IA do ML** se existe endpoint publico para o motorista
   da coleta do dia. Funcionou bem na rodada da Shopee (item 11) — a resposta
   deles derrubou uma conclusao nossa que estava errada.
3. **O ML publicar** um endpoint de coleta agendada com o motorista. Se isso
   acontecer, o `diag_coleta.py` ja tem toda a infra de comparacao pronta
   (`_comparar`, `_porque_sem_driver`, mascaramento) — e so trocar a fonte.

### Por que vale ter feito o percurso

A ideia era boa e a premissa de negocio estava **certa** (o mesmo motorista
atende as duas contas; confirmado nos dois paineis no mesmo dia). O que nao
existe e o CANAL. Sem este registro, a ideia voltaria a cada poucos meses e
alguem gastaria o mesmo dia de novo — foi exatamente o que aconteceu antes de
2026-07-29, quando a ferramenta ja existia mas o resultado nunca tinha sido
anotado.

### FASE 1 (o que construir primeiro): so avisar, nunca selecionar

**Avisar, nunca trocar sozinho.** O modo Ambas muda o que sai junto no ZIP e em
qual arquivo o estado e marcado; liga-lo em silencio e o tipo de automatismo que
acerta 20 dias e no 21o (dia atipico) imprime o lote errado. A convencao atual —
Ambas e escolha pontual, nao persistida no config — existe por isso e deve
continuar valendo enquanto a deteccao nao estiver provada.

Formato: apos o Atualizar, um aviso discreto ao lado do seletor de conta, com
**TRES estados** (o terceiro e o mais importante):

| `driver.id` das 2 contas hoje | Aviso na tela | O app seleciona algo? |
|---|---|---|
| iguais | "mesmo motorista hoje nas duas contas" | Nao |
| diferentes | "motoristas diferentes hoje" | Nao |
| faltando em uma ou nas duas | **nada** (silencio) | Nao |

O terceiro estado nao pode virar "motoristas diferentes". Ausencia de dado
(sem coleta programada, `logistic_type` diferente, token sem permissao, API
fora) **nao e** evidencia de motorista diferente — e um palpite disfarcado de
informacao, e o dono passaria a confiar num aviso que as vezes chuta. Silencio
e a resposta honesta: cai no comportamento de hoje, em que ele confere na mao.

Custo: 1 GET por conta, cacheado por dia (o cronograma e por dia da semana, nao
muda a cada Atualizar).

### FASE 2 (so depois de PROVADO): considerar automatizar

O dono quer chegar em automacao ("se o sistema de identificar motorista estiver
100%, colocar em producao automatica mais pra frente"). O caminho e esse mesmo,
mas **"100%" precisa ser medido, nao sentido** — senao a decisao vira impressao
("acho que nunca errou") depois de algumas semanas sem prestar atencao.

**Como medir de graca durante a fase 1:** a cada Atualizar, registrar no
`separador.log` (via `registro.py`) uma linha com o veredito e os ids
(`coleta: A=<driver.id> B=<driver.id> -> iguais|diferentes|indeterminado`).
Isso nao custa nada, nao aparece pro dono e produz o historico que a fase 2
exige. Ao fim do periodo de observacao da pra responder com evidencia:
- em quantos dias a deteccao foi conclusiva (nem sempre vai ser — ver 3o estado);
- em quantos ela bateu com o que o dono realmente fez;
- se houve algum dia em que ela disse "iguais" e o dia era de motorista diferente
  (esse e o erro CARO: e o que levaria a imprimir contas juntas indevidamente).

**Criterio sugerido pra abrir a fase 2:** varias semanas de operacao real sem
nenhum falso "iguais". Um unico falso "iguais" reabre a discussao — o erro nessa
direcao mistura lotes de contas diferentes, e o prejuizo nao e simetrico com o
falso "diferentes" (que so faz o dono conferir na mao, como ja faz hoje).

**Mesmo na fase 2, "automatico" nao precisa dizer "sem confirmacao":** um passo
intermediario e o app deixar o 🌐 Ambas **pre-selecionado** quando os motoristas
sao iguais, ainda visivel e reversivel antes do dono mandar imprimir. Ganha a
comodidade sem tirar a decisao dele — e a impressao ja tem a confirmacao
"as etiquetas sairam certo?" como ultima rede.

### Cuidados na implementacao (valem nas duas fases)

- A consulta precisa do token de CADA conta, entao passa por `definir_conta` —
  vale o mesmo cuidado do `_dados_alerta_da_conta` no bot: fazer tudo o que
  depende da conta NUM SO bloco de troca (ver "Areas de risco" na
  `ARQUITETURA.md`).
- Falha da consulta nao pode atrapalhar o Atualizar: sem resposta, cai no 3o
  estado (silencio), nunca em erro na tela.
- O aviso e **so leitura**: nao toca `self.grupos`, estado nem config.
- Nao logar nome do motorista nem placa (dado pessoal) — so `driver.id`, como o
  `diag_coleta.py` ja faz.

## 13. Melhorias de OPERACAO INTERNA (destilado da auditoria comercial de 2026-07-29)

**Origem:** o dono pediu uma analise do projeto "como se fosse virar produto
comercial". A conclusao dessa analise nao interessa aqui (ele NAO pretende
comercializar — e uso proprio). O que interessa e o **destilado**: das ~14
lacunas que a analise apontou, a maioria (OAuth centralizado, multi-inquilino,
cobranca, LGPD, instalador, telemetria, onboarding) so faz sentido com clientes
externos e foi **descartada**. Sobraram 7 itens que valem para UMA operacao.

**Nota de escopo:** "facilidade de uso" nao e prioridade enquanto o dono for o
unico usuario. Volta a ser se entrar um funcionario pra embalar — e ai o que
importa nao e onboarding bonito, e o app **impedir** que essa pessoa erre
(item 13.2).

### 13.1. Reduzir a dependencia do app externo da Zebra
Ver o debate/decisao proprios (secao "Pasta Downloads / app Zebra" da
`ARQUITETURA.md`). E o unico ponto do fluxo em que uma falha PARA a expedicao e
o conserto nao esta nas maos deste repo. Atencao: o contrato com o app **esta
documentado e foi verificado dos DOIS lados em 20/07/2026** — o risco NAO e
acoplamento obscuro; e **falta de retorno** (a tela nao sabe se o monitor esta
rodando nem se o arquivo foi consumido) e **ponto unico de falha**.

### 13.2. Conferencia por leitura de codigo de barras na embalagem
Hoje o app **reduz** erro de separacao (pilha por produto, na ordem da
prateleira). Ler o codigo antes de fechar a caixa **impede** o erro. E o unico
item que ataca diretamente o problema que originou o projeto. Autocontido: uma
tela, um leitor USB (que digita como teclado) e comparacao com o SKU esperado.
Nao depende de nada da infra descartada acima.

### 13.3. Registrar erro de separacao (o outro lado do historico)
`historico_impressao.json` ja grava o que foi impresso e quando. Falta o
contraponto: um registro de quando a separacao saiu errada. Com os dois, em 2-3
meses da pra responder com NUMERO se a ordem da aba Nomes esta boa, quais SKUs
concentram erro e se vale reordenar. Hoje isso e intuicao. Pre-requisito pra
medir o beneficio de 13.2.

### 13.4. Painel de produtividade a partir do dado que JA existe
Etiquetas por dia/conta/marketplace, evolucao por semana. **Melhor relacao
valor/esforco da lista inteira**: a coleta ja esta feita (`historico.py`), falta
so a apresentacao. Reusa `resumo_do_dia`/`formatar_resumo`.

### 13.5. Detectar pedido problematico ANTES de imprimir
Endereco incompleto, produto que acabou. Melhor descobrir na tela do que na hora
de embalar. Depende de definir quais sinais a API ja entrega (nao pesquisado).

### 13.6. Ordem de separacao aprendida (evolucao do que ja existe)
A ordem da aba Nomes e manual. Com o historico, da pra SUGERIR reordenacoes com
base no que realmente sai junto. Como e uso interno, da pra ser mais agressivo
que num produto — o dono valida na hora. Depende de 13.3/13.4 (dado).

### 13.7. Margem por SKU no ads-monitor (o item 10 SOBE de prioridade)
Numa leitura comercial isso seria "melhoria futura" (o modulo nao e vendavel).
**Internamente e o contrario:** e o dinheiro de anuncio do proprio dono, e a
atribuicao por SKU ja esta construida esperando exatamente essa fonte. Maior
retorno financeiro DIRETO da lista. Detalhes tecnicos no item 10.

### Ordem sugerida
1. **13.1** se o criterio for RISCO (unica falha que para a operacao).
2. **13.2** se o criterio for GANHO (ataca o problema original).
3. **13.4** (barato, dado ja existe) → **13.3** → **13.6** (dependem de dado).
4. **13.7** em paralelo — subsistema isolado, nao concorre com os outros.
5. **13.5** por ultimo (precisa de pesquisa de API antes de virar tarefa).

### Um achado nao-tecnico que continua valendo
O repositorio e **publico e sem `LICENSE`** (sem licenca, direitos reservados por
padrao). Sem intencao de vender, isso deixa de ser risco de concorrencia — mas as
pegadinhas da Shopee descobertas em loja real (AWB so apos organizar, os ~14s
fixos, o comportamento do `info_needed`) estao publicas. Nao e problema, e
escolha; so vale ser **consciente**, nao esquecimento.

## O que evitar por enquanto

Algumas mudancas parecem atraentes, mas provavelmente nao valem o risco agora:

- Reescrever a GUI em outra tecnologia.
- Trocar JSON local por banco de dados sem necessidade real.
- Fazer uma refatoracao grande de uma vez.
- Alterar o fluxo de impressao sem um motivo operacional claro.
- Misturar novas features com reorganizacao interna no mesmo pacote de mudancas.

## Recomendacao de ordem

Ordem sugerida para evoluir com seguranca:

1. Extrair e testar uma camada comum de estado de impressao.
2. Melhorar nomes/comentarios do contrato de impressao da GUI.
3. Adicionar logs operacionais basicos.
4. Criar uma tela ou modo de diagnostico.
5. Separar partes do `separador_etiquetas_ml.py` aos poucos.
6. Isolar melhor o modo "Ambas", se ele continuar crescendo.
7. Padronizar encoding e pequenos detalhes de ambiente.

Cada etapa deve ser pequena, revisavel e acompanhada de testes quando tocar regra
de negocio.
