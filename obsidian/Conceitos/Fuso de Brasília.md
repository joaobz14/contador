---
tags: [conceito, data, fuso]
aliases: [Brasília, TZ_BR, fuso horário]
type: conceito
---

# 🕰️ Fuso de Brasília

> [!abstract]
> **Sempre** Brasília: `TZ_BR`, `_hoje_br()`, `_amanha_br()`. Toda data (dia de despacho,
> carimbo de tempo do histórico, aviso da manhã do bot) usa esse fuso.

## Por quê
A operação é no Brasil; misturar UTC/local causaria pedido no dia errado e histórico
com carimbo torto. Centralizar o fuso evita isso.

## Relacionado
- [[Dia de despacho]] · [[Histórico e resumo do dia]] · [[bot_telegram]]
