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

## 7. Padronizar encoding e ambiente Windows

O projeto e usado em Windows e alguns textos com acento podem aparecer quebrados
dependendo do terminal. Vale garantir:

- arquivos fonte e docs em UTF-8
- scripts `.bat` chamando Python de forma consistente
- logs gravados com `encoding="utf-8"`
- mensagens criticas sem depender de configuracao especial do console

Essa mudanca nao afeta regra de negocio, mas melhora manutencao e suporte.

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
