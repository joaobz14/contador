---
tags: [modulo, log, seguranca]
aliases: [registro.py, log operacional]
type: module
arquivo: registro.py
---

# 📝 registro.py — log operacional + redação de segredos

> [!abstract] Papel
> O log de diagnóstico (`separador.log`) e a função `sem_segredos` que **redige
> segredos** antes de qualquer texto ir para log/tela/bot.

## Duas regras de ouro
1. **Log nunca atrapalha a operação** — defensivo, `try/except`, `delay=True`.
2. **Nunca logar segredos** — todo texto de exceção passa por `sem_segredos` antes → [[Redação de segredos]].

## Por que importa
Um `HTTPError` da Shopee carrega a **URL assinada** com `access_token`/`sign`. Sem
redação, o segredo vazaria para o `separador.log`. Ver [[Redação de segredos]] para a
cobertura (formas query e JSON/dict; chaves `token`/`sign`/`code`/`client_secret`/`partner_key`).

## Relacionado
- [[Redação de segredos]] · [[shopee_api]] · [[bot_telegram]] · [[separador_gui]]
