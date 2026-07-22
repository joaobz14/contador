---
tags: [funcionalidade, impressao, ml, shopee]
type: feature
status: current
aliases: [Impressão de etiquetas, imprimir etiquetas, gerar etiquetas]
source_files: [separador_etiquetas_ml.py, shopee_api.py, separador_gui.py]
source_docs: [docs/ARQUITETURA.md]
verified_at_commit: bcab879
---

# 🖨️ Impressão de etiquetas (funcionalidade)

> [!abstract]
> O coração do app: transformar pedidos prontos em **pilhas de etiquetas por produto**,
> na ordem de separação do operador, e imprimi-las na Zebra sem imprimir em dobro.

## Fluxo que o operador percebe
1. Escolhe **marketplace** (e, no ML, a **conta** ou o modo **Ambas**) e o **dia de despacho**.
2. **Atualizar** → o app coleta os pedidos prontos e mostra **grupos** (produto × quantidade),
   separados em **pendente / parcial / impresso**, na **ordem da aba Nomes**.
3. Seleciona os grupos → o app **gera** o `.zip` na pasta **Downloads** (a Zebra imprime).
4. Responde **"as etiquetas saíram certo?"** → só então o app **marca como impresso**.

## Identificação impressa
- **ML:** carimbo na **DANFE** (SKU ou nome), sem tocar a etiqueta de envio → [[Identificação na impressão (carimbo)]].
- **Shopee:** a etiqueta já vem pronta, sem nome → a tela lista o **AWB** para conferência → [[Conferência na Shopee (rastreio)]].

## Garantias (invariantes)
- **Nunca marca antes da confirmação física** (inv. 1) → [[Confirmação física antes de marcar]].
- **Reimpressão não altera o estado** (inv. 2).
- **Trava de ponta a ponta** impede imprimir o mesmo lote duas vezes → [[Impressão dupla na Shopee]].

## Limitações
- Depende do app externo da Zebra monitorando a Downloads (o prefixo do `.zip` é o contrato) → [[Ponte com a Zebra]].
- Shopee: a etiqueta só existe **após organizar o envio** (emite o AWB) → [[Shopee — organizar envio e AWB]].

## Relacionado
- [[Fluxos de operação]] · [[Agrupamento e identidade do produto]] · [[Estado já impresso]] · [[Ponte com a Zebra]] · [[Modo Ambas (ML)]]
