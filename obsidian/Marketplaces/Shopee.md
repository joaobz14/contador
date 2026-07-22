---
tags: [marketplace, shopee, hub]
type: marketplace
status: current
aliases: [Shopee, Shopee Open Platform]
source_files: [shopee_api.py]
source_docs: [docs/ARQUITETURA.md]
verified_at_commit: bcab879
---

# 🟠 Shopee

> [!abstract]
> Marketplace secundário, **uma loja só**. A etiqueta **não existe** até organizar o
> envio (que emite o **AWB**); a etiqueta vem pronta **sem o nome do produto**. Integração
> em `shopee_api.py`.

## Especificidades
- **Loja única** (`credenciais_shopee.json`) — sem multi-conta.
- **Organizar → AWB → documento:** o caminho e as pegadinhas (GET vs POST, `tracking_number`
  obrigatório, drop-off) → [[Shopee — organizar envio e AWB]].
- **Conferência por AWB:** sem nome na etiqueta, a tela lista o AWB de cada etiqueta impressa
  → [[Conferência na Shopee (rastreio)]].
- **Desempenho:** organizar é **~14s fixos** (piso do AWB); o ganho é gerar documentos em
  paralelo por pedido → [[Desempenho]].
- **Segurança:** a URL é **assinada por HMAC** e leva `access_token`/`sign` na query — erros
  não podem vazar o token → [[Redação de segredos]].

## API (sistema externo)
Shopee Open Platform API v2. A etiqueta térmica vem como **ZIP com ZPL (`~DGR/Z64`) dentro**
— imprime direto, não reembrulhar. Ver [[Sistemas externos]].

## Restrição operacional
O bot do Telegram **não imprime** grupos da Shopee (só consulta) — invariante 10 → [[Telegram]].

## Relacionado
- [[shopee_api]] · [[Shopee — organizar envio e AWB]] · [[Conferência na Shopee (rastreio)]] · [[Redação de segredos]] · [[Mercado Livre]]
