---
tags: [conceito, shopee, awb, gui]
aliases: [rastreio Shopee, AWB na tela, preencher_rastreios]
type: concept
---

# 🔎 Conferência na Shopee (rastreio)

> [!abstract]
> A etiqueta Shopee é imagem pronta **sem o nome do produto** (e sem faixa livre estável
> para carimbar — validado com 10 etiquetas). Então a **tela** lista o **AWB** de cada
> etiqueta impressa do grupo, para o operador cruzar código físico × produto.

## Como é preenchido
- `Grupo.rastreios`, à esquerda, embaixo do nome.
- `preencher_rastreios` (todos os impressos) e na hora da impressão (`_somar_rastreios` **UNE** aos já exibidos — substituir apagaria códigos de um grupo parcial).
- AWB é imutável → **cacheado na impressão** (`_cachear_awbs` → `awb_cache_shopee.json`, local). `preencher_rastreios` lê do cache primeiro (menos rede, códigos confiáveis) e só busca os ausentes.
- **Pendentes não têm AWB** (só existe após organizar) → não mostram código.

## Contraste com o ML
No ML a identificação é o **carimbo na DANFE** → [[Identificação na impressão (carimbo)]].

## Relacionado
- [[Shopee — organizar envio e AWB]] · [[shopee_api]] · [[Identificação na impressão (carimbo)]]
