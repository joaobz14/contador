---
tags: [runbook, impressao, zebra, zpl, diagnostico]
type: runbook
status: current
aliases: [etiqueta em branco, pulou uma etiqueta, etiqueta pulada, diag_zpl]
source_files: [tools/diag_zpl.py, separador_etiquetas_ml.py]
source_docs: [CLAUDE.md]
---

# 🖨️ Runbook: a impressão "pulou uma etiqueta"

> [!abstract]
> Sai uma etiqueta **totalmente em branco** no meio do lote. Acontece de vez em
> quando, não todo dia. Este runbook separa as causas **por evidência** — cada
> uma pede uma ação diferente, e chutar leva a calibrar a impressora quando o
> problema está no arquivo (ou o contrário).

## O que já está descartado (não reinvestigue)

> [!success] O contador não sabe criar uma página em branco
> O núcleo **repassa** o ZPL que o Mercado Livre manda e só insere um campo
> (`^FO…^FS`) **dentro** do bloco da DANFE que já existe — é o carimbo do
> produto → [[Identificação na impressão (carimbo)]]. Não existe um único
> comando de mídia (`^LL`/`^PQ`/`^MN`/`^LH`) em todo o repositório.

> [!success] Página vazia vinda do arquivo não chega a imprimir
> Se o Mercado Livre mandasse um bloco vazio, o app da Zebra o **descarta** antes
> de enviar à impressora (loga *"conteúdo vazio entre ^XA e ^XZ — ignorado"*).

## As três causas possíveis

| # | Causa | Como confirmar | O que fazer |
|---|---|---|---|
| a | **Auto-feed de início de sessão** do app da Zebra: ele imprime uma etiqueta em branco **de propósito** para posicionar o sensor | linha `Avançando etiqueta — posicionando sensor` no `~/zebra_usb_log.txt` | nada — é esperado. Só acontece na **primeira** impressão depois de clicar em *Iniciar* |
| b | **Configuração de mídia mudando no meio do lote** (`^MN`/`^LL` diferentes entre os blocos do ML) | `python tools/diag_zpl.py` acusa `^MN MUDA` / `^LL MUDA` | é do lado do ML — registre o caso antes de mexer em qualquer coisa |
| c | **Calibração da mídia** (sensor de gap perdido) | as duas checagens acima limpas | botão **Calibrar mídia** no app da Zebra |

## O diagnóstico

```bash
python tools/diag_zpl.py            # pega o lote mais recente sozinho
python tools/diag_zpl.py <arquivo.zip>
```

Ele lê o lote **que já foi impresso** — o app da Zebra guarda em
`~/zebra_usb_concluidos/AAAA-MM-DD/` → [[Ponte com a Zebra]] — e mostra, página
por página, o que o arquivo mandou para a impressora.

> [!warning] Ele mostra só a estrutura, e isso é de propósito
> A etiqueta carrega **nome, endereço e CEP do comprador**, e este repositório é
> público. O relatório traz nome de comando, contagem e tamanho — nunca o
> conteúdo de um campo → [[Redação de segredos]].

## Armadilha ao olhar a tira de papel

> [!danger] A ordem física é o inverso da ordem de impressão
> O Mercado Livre manda **envio → DANFE** (nessa ordem), e a impressora empurra o
> papel para fora — então **o que está mais perto da impressora foi impresso por
> último**. Ler a tira ao contrário troca *"a branca veio antes de tudo"*
> (causa **a**) por *"a branca veio no meio da venda"* (causas **b**/**c**), que
> pedem ações diferentes.

## Relacionado
- [[Ponte com a Zebra]] · [[Identificação na impressão (carimbo)]] · [[Validar o repositório]] · [[Sistemas externos]]
