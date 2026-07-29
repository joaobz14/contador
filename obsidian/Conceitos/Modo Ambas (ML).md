---
tags: [conceito, ml, provedor, multiconta]
aliases: [Ambas, ProvedorMLAmbas, fundir_grupos]
type: concept
---

# 🌐 Modo "Ambas" (ML)

> [!abstract]
> Radio extra no seletor de conta para um **dia de motorista único**: junta as contas
> do ML, **fundindo** grupos de mesmo SKU+qtd numa pilha só, num ZIP único.

## Como funciona
- `ProvedorMLAmbas` coleta as contas **em sequência** e usa `fundir_grupos` (subgrupos em `.por_conta`).
- Imprime cada etiqueta com o **token da conta dela** → [[Token e rotação do refresh]].
- Estado segue **por conta**: `marcar_impresso` roteia com `definir_conta` antes de cada gravação → [[Estado já impresso]].
- Não é persistido no config (escolha pontual).

## Cuidado com anúncio sem SKU
> [!warning]
> No modo Ambas, o botão inline de adoção **RE-COLETA** (`_aplicar_adocao`), **não**
> aplica em memória: os sub-grupos `.por_conta` manteriam a chave antiga do anúncio,
> escondendo envios do lote e marcando estado na chave errada → [[Adoção de anúncios sem SKU]].

## Ideia em avaliação: avisar o motorista do dia (BLOQUEADA)
Hoje o dono lembra na mão se "o motorista é o mesmo nas duas contas" e clica (ou
não) no radio. A API do ML entrega o motorista da coleta
(`GET /users/{id}/shipping/schedule/{logistic_type}` → `driver.id`, ID estável),
e `tools/diag_coleta.py --comparar contaA contaB` já responde se é o mesmo hoje.

**Os dois lados interessam:** avisar "mesmo motorista" *e* "motoristas
diferentes". O aviso negativo não é redundante — hoje ele é implícito (silêncio +
memória do dono); explícito, vira informação confirmada. Em nenhum caso o app
seleciona nada: só informa.

> [!warning] Bloqueio: falta rodar o `--comparar` num dia com coleta e anotar o resultado
> Sem saber se o `driver.id` vem preenchido nas duas contas reais, não há o que
> automatizar. Detalhes, fases e desenho no item 12 do `PRIORIDADES_TECNICAS.md`.

> [!danger] Ausência de dado ≠ "motoristas diferentes"
> O terceiro estado (sem coleta programada, logística diferente, token sem
> permissão, API fora) tem que ser **silêncio**. Chamá-lo de "diferentes" seria
> um palpite disfarçado de informação — e o dono passaria a confiar num aviso que
> às vezes chuta.

**Fases:** (1) só avisar, registrando o veredito no `separador.log` para gerar
evidência; (2) considerar automatizar **só depois de provado** — o critério é
nenhum falso "iguais" em semanas de operação real, porque esse é o erro caro
(misturaria lotes de contas diferentes). Falso "diferentes" só faz o dono
conferir na mão, como já faz hoje.

## Relacionado
- [[provedores]] · [[Multi-conta (ML)]] · [[Agrupamento e identidade do produto]] · [[Adoção de anúncios sem SKU]]
