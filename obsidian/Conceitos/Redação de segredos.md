---
tags: [conceito, seguranca, log, shopee]
aliases: [sem_segredos, redação de segredos, vazamento de token]
type: conceito
---

# 🔐 Redação de segredos

> [!abstract]
> Nenhum texto de erro pode vazar segredo. `registro.sem_segredos()` redige **antes**
> de qualquer coisa ir para `separador.log`, tela ou bot.

## Por que é crítico
A **URL assinada da Shopee** leva `access_token`/`sign` na query. Um `HTTPError`
carrega essa URL. Sem redação, o segredo vaza para o log.

## Defesa em profundidade (HTTP **e** transporte)
- `_levantar_se_erro` (nunca `raise_for_status`, cuja mensagem inclui a URL) → [[shopee_api]].
- `_rede_limpa`: falhas de **transporte** (a exceção crua do requests carrega "Max retries exceeded with url: …") viram `SeparadorError` limpo com `from None` (corta o encadeamento).
- A GUI redige o que mostra (`_erro`); o bot redige o que manda ao chat.

## Cobertura de `sem_segredos`
Forma **query** (`chave=valor`) **e** forma **JSON/dict** (`"chave": "valor"`); chaves
incluem `token`/`sign`/`code` **+** `client_secret`/`partner_key`.

## Relacionado
- [[registro]] · [[shopee_api]] · [[bot_telegram]] · [[Invariantes críticas]]
