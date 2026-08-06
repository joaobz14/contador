---
tags: [conceito, impressao, zebra, zpl, downloads]
aliases: [pasta Downloads, nome_saida_unico, tmp_saida, monitor Zebra]
type: concept
---

# 🖨️ Ponte com a Zebra (pasta Downloads)

> [!abstract]
> O app **não** fala com a impressora direto: grava um `.zip` na pasta **Downloads** e
> um app externo (`impressora_zebra_usb.py`) monitora a pasta e imprime. Ver [[Sistemas externos]].

## O contrato do nome do arquivo
- **Prefixo** que o monitor casa: `etiqueta de envio` (ML) / `etiqueta shopee` (Shopee). **Mudar o prefixo quebra a detecção** — o papel não sai.
- O resto é livre, mas precisa ser **único** por trabalho: `nome_saida_unico` (carimbo de tempo + `-1`,`-2`… na colisão). Nome determinístico + `replace` apagava em silêncio um lote que o monitor ainda não consumira.
- Temporário `tmp_saida` → `tmp_*.part`: **não pode casar** prefixo nem extensão vigiada (`*.zip`/`*.plain`). Teste-guardião `test_tmp_saida_nao_casa_o_que_o_monitor_vigia`.

## Antes de gerar
A GUI **relê o estado do disco** (`prov.carregar_estado()`) — pendente sobre estado
defasado imprimiria em dobro o que foi marcado por fora (CLI/2ª GUI) → [[Estado já impresso]].

## Contrato do app Zebra (v1.25.7, verificado 20/07/2026)
Polling de 1s; aceita `*.zip` (prefixos) e `*.plain` (DANFE); **duplicata** por
`nome+tamanho+mtime` (nomes únicos nunca colidem); arquivos **devem estar em UTF-8**
(decode `errors="ignore"`) → não converter → [[Identificação na impressão (carimbo)]].

> O app da Zebra é do **mesmo dono** (repo `impressora-zebra-usb`) e desde
> 2026-07-29 tem **teste do contrato do lado dele também** — contrato documentado
> só de um lado é meio contrato.

## Retorno do monitor: 3 fontes, resposta antes de pista
A entrega é por arquivo e não havia canal de volta: com o monitor fechado, os ZIPs
só se acumulavam e o dono descobria pelo papel que não saía. `aguardar_impressao`
consulta, **nesta ordem**:

1. **A resposta** (desde 2026-07-30, app Zebra **≥ v1.26.0**): o mural
   `~/zebra_usb_status.json`, que o monitor publica a cada arquivo processado
   (`registrar_status_trabalho`, no outro repo) com `{arquivo, quando, etiquetas,
   ok}` → `impresso` ou **`falhou`**;
2. **Pista** — o arquivo **sai da pasta** (o que ele imprime, ele tira dali) → `impresso`;
3. **Pista** — o **log dele avança** (`~/zebra_usb_log.txt`) → `imprimindo` (cobre o
   lote grande, em que o ZIP só some na última etiqueta);
- nenhum dos três → `sem_sinal` (provavelmente fechado) ou `sem_saida` (não sei).

> [!tip] Por que a resposta vem primeiro
> Um arquivo que **falhou não é apagado** pelo monitor: ele fica na pasta com o log
> avançando — o retrato exato de um lote demorado. Só o mural distingue os dois.
> Ele também é a única fonte que funciona com a opção **"Excluir após imprimir"
> DESLIGADA**, em que o arquivo nunca some e as pistas nunca fecham.
>
> Duas salvaguardas na leitura: corte por `desde` (o mural guarda os últimos 50
> trabalhos, e um registro **anterior** de mesmo nome não pode responder por esta
> impressão) e exigência de pronunciamento sobre **todos** os nossos arquivos
> (parcial = ainda em curso). Mural ausente, ilegível ou parcial **degrada para as
> pistas** — compatibilidade com monitor antigo sai de graça, e este canal só pode
> **adicionar** certeza, nunca tirar.

> [!info] Sair da pasta ≠ ser apagado (app Zebra ≥ v1.26.2)
> O sucesso não é mais apagado: é **movido** para `~/zebra_usb_concluidos/AAAA-MM-DD/`,
> retenção para reimprimir quando a impressora falha **fisicamente** depois de o
> spooler aceitar o job (papel preso, ribbon rasgado) — antes, nesse caso, o arquivo
> já tinha sido apagado. Para a pista 2 dá no mesmo (saiu = impresso); muda **onde
> procurar** o arquivo depois: num lote perdido, ele **existe** — veja lá antes de
> dá-lo por perdido (atalho: bandeja do app → "Abrir pasta de concluídos").
>
> O que a pista exige é a **assimetria**, contratada dos dois lados: **sucesso sai
> da pasta, falha permanece nela**. Se um dia a falha também passasse a ser movida
> (a ideia de uma pasta `.erros/`, considerada e descartada lá), ela seria lida
> aqui como **impressa** — lote falho aparecendo como concluído na tela.
> A pasta fica **fora** da vigiada e na raiz do perfil de propósito: o OneDrive não
> sincroniza (o *Known Folder Move* nunca redireciona `C:\Users\<você>`) e um
> arquivo já impresso nunca pode ser reingerido pelo monitor.

A tela sabe quais arquivos são dela por **diferença de dois instantâneos**
(`saidas_na_pasta` antes/depois de gerar) — `gerar_zip_lotes` devolve os pendentes,
não o caminho.

> [!warning] Na dúvida, calado
> O monitor varre a cada 1s e pode consumir o ZIP **antes** do 2º instantâneo — aí
> a diferença vem vazia. Nesse caso o veredito é `imprimindo`, **nunca** `impresso`:
> sem ter visto o nosso arquivo sumir, afirmar que ele saiu seria o erro que esta
> tela não pode cometer. Mesma regra se o `exists()` levantar (arquivo preso pelo
> antivírus/OneDrive): responde "ainda está lá".

> [!bug] O ⚠️ exige PROVA (incidente 2026-07-30)
> Um lote de 12 avisou "o monitor NÃO deu sinal" **imprimindo normalmente**; lotes
> pequenos acertavam. Dois fatos somados: em lote grande o arquivo não some dentro
> do teto (só é apagado na última etiqueta) **e** o log não pôde ser lido — e a
> versão anterior colapsava "não sei" e "log parado" num booleano.
> Agora `_mtime_log_monitor` devolve `None` para "não sei" → `sem_saida`
> (silêncio); só log **encontrado e sem avanço** vira `sem_sinal`.
> **Falso alarme é pior que aviso nenhum:** ensina o operador a ignorar o ⚠️, e ele
> perde a utilidade justamente no dia em que estiver certo.

> [!danger] O sinal informa, nunca decide
> Quem responde "as etiquetas saíram corretamente?" continua sendo o operador,
> olhando o papel → [[Invariantes críticas]]. O monitor confirma que **mandou**
> imprimir, não que a etiqueta saiu legível e no lugar. Vale inclusive para o
> mural: `impresso` ali é fato sobre o **envio ao spooler**, não sobre o papel.

## Por que os dois apps não viraram um só
Avaliado a pedido do dono em 2026-07-30 e **recusado** →
[[Não fundir o contador e o app da Zebra]]. Resumo: o app da Zebra também imprime o
que se baixa **na mão** pelo painel do ML, roda **elevado** (UAC) e é Windows-only.
O único ganho real da fusão era o canal de volta — obtido acima, sem fundir.

## Quando sai uma etiqueta em branco
O app da Zebra imprime **uma** de propósito ao iniciar (posiciona o sensor de gap),
e esse é só um dos três motivos possíveis → [[Etiqueta em branco na impressão]].

## Relacionado
- [[Sistemas externos]] · [[Escrita atômica de JSON]] · [[Identificação na impressão (carimbo)]] · [[separador_etiquetas_ml (núcleo)]] · [[Etiqueta em branco na impressão]]
