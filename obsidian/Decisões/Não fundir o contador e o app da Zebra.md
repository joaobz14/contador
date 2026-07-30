---
tags: [decisao, zebra, arquitetura, impressao, acoplamento]
type: decision
status: current
aliases: [não fundir os apps, fusão contador Zebra, um app só, monolito da impressão]
source_files: [separador_etiquetas_ml.py]
source_docs: [docs/ARQUITETURA.md, CLAUDE.md, docs/CHANGELOG.md]
verified_at_commit: 7cf993e
---

# 🧭 Decisão: os dois apps continuam separados

> [!abstract]
> **Decisão:** manter `contador` e `impressora-zebra-usb` como **dois programas
> distintos**, ligados pelo arquivo largado na pasta Downloads. **Estado:** decidida
> em 30/07/2026, a pedido do dono, depois de avaliar a fusão. O único ganho real que
> a fusão traria (canal de retorno) foi obtido **sem** fundir → [[Ponte com a Zebra]].

## Contexto
Os dois apps "trabalham juntos" e são do mesmo dono. Com o repositório da Zebra
acessível, surgiu a pergunta natural: por que não são um só? A entrega entre eles é de
mão única — o contador grava um `.zip` na Downloads e vai embora —, o que na época
significava **nenhuma resposta de volta** e um contrato frágil espalhado por dois
repositórios.

## O que decidiu a questão
O app da Zebra **não é back-end do contador**. Ele é um serviço de impressão que o
contador *também* alimenta:

- Os `PREFIXOS` que ele vigia incluem `etiqueta mercadoenvios`, `shipping-label` e
  `danfe-simplificado-` — os nomes que o **próprio site do Mercado Livre** dá quando
  se baixa uma etiqueta direto do painel. Ele imprime **sem o contador existir**, e é
  o plano B no dia em que o contador estiver quebrado. Fundir mataria esse caminho.
- Tem funcionalidade própria: as **etiquetas separadoras** (`gerar_zpl_separador`,
  `PopupSeparadora`, `JanelaProdutos`), com lista de produtos e busca próprias, sem
  relação nenhuma com marketplace.

## Três impedimentos técnicos
| Impedimento | Onde vive | Custo da fusão |
|---|---|---|
| Roda **elevado** (UAC) | `elevar_privilegios()` — precisa de admin para limpar a fila do spooler | A tela e o bot herdariam UAC, ou a separação teria de ser recriada por dentro |
| **Ciclos de vida opostos** | App de bandeja, instância única (mutex), ligado desde o logon | A tela abre sob demanda e fecha; o bot é 3º processo pelo Agendador — fundir exigiria um supervisor |
| **Plataforma** | `pywin32`, `pystray`, `pillow` — Windows-only | O núcleo daqui é portátil e o CI roda no Linux; a fusão arrastaria dependência Windows para o CI |

## O que a separação dá de graça
A pasta Downloads é uma **fila com persistência**. Se a tela travar no meio de um lote,
o que já caiu lá continua imprimindo; se a impressora engasgar, o contador não fica
pendurado. Num processo único, cada uma dessas falhas derruba a outra metade.

## O custo real — e como foi pago
O preço da separação era a **ausência de canal de volta**, sentida no falso alarme do
⚠️ (incidente de 30/07/2026). Resolvido **sem fundir**: o app da Zebra passou a publicar
`~/zebra_usb_status.json` a cada arquivo processado, e o contador lê essa resposta antes
de recorrer às pistas → [[Ponte com a Zebra]].

## Quando reavaliar
Se o app da Zebra deixar de precisar de admin **e** perder a função de imprimir o
download manual **e** as separadoras saírem dele. Hoje nenhum dos três é verdade.

## Relacionado
- [[Ponte com a Zebra]] · [[Sistemas externos]] · [[Zebra e pasta Downloads]] · [[Impressão de etiquetas]] · [[Confirmação física antes de marcar]]
