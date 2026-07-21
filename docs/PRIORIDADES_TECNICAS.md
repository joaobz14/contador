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
