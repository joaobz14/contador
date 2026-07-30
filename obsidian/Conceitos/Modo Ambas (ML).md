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

## Avisar o motorista do dia — ENCERRADO ("não fazer", 2026-07-30)
A ideia era o app perceber sozinho se o motorista do dia é o mesmo nas duas
contas e **avisar** (sem selecionar nada), em vez do dono lembrar na mão.

A premissa estava **certa** — no mesmo dia, os painéis das duas contas mostraram
o mesmo motorista e a mesma placa. O que não existe é o **canal**: nenhuma das
duas fontes plausíveis da API pública entrega o dado (ver abaixo). Ferramenta de
diagnóstico usada: `tools/diag_coleta.py` (`--comparar`, `--cru`, `--envio`,
`--chaves`) — só leitura, com dado pessoal mascarado.

> [!failure] A API pública do ML não expõe o motorista da coleta do dia
> Testado com dado real em 2026-07-30, nas duas fontes plausíveis:
> - `schedule/{logistic_type}` → **gabarito semanal**; `driver`/`carrier`/`vehicle`
>   existem na estrutura mas vêm vazios em todos os 7 dias;
> - `GET /shipments/{id}` (que o núcleo já chama) → **não tem nem a chave**.
>
> O painel do vendedor mostra motorista e placa, então o dado existe — mas por
> endpoint **interno**. A premissa estava certa; o que falta é o canal.
> **Nada muda:** o Ambas segue sendo escolha manual. Veredito completo e o que
> reabriria o item no item 12 do `PRIORIDADES_TECNICAS.md`.

> [!danger] Ausência de dado ≠ "motoristas diferentes"
> O terceiro estado (sem coleta programada, logística diferente, token sem
> permissão, API fora) tem que ser **silêncio**. Chamá-lo de "diferentes" seria
> um palpite disfarçado de informação — e o dono passaria a confiar num aviso que
> às vezes chuta.

O desenho que teria sido usado (avisar sem selecionar, em duas fases, com
critério de "nenhum falso *iguais*") fica registrado no item 12 — serve de molde
se o ML publicar o dado um dia.

## Relacionado
- [[provedores]] · [[Multi-conta (ML)]] · [[Agrupamento e identidade do produto]] · [[Adoção de anúncios sem SKU]]
