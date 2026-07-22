---
tags: [moc, invariante, seguranca]
aliases: [Invariantes, Regras de ouro, Invariantes críticas]
type: reference
---

# 🛡️ Invariantes críticas

> [!danger] Regras que **não** podem ser quebradas
> São as 12 invariantes de `docs/ARQUITETURA.md`. Quebrar qualquer uma leva a
> **imprimir errado, imprimir em dobro, ou travar uma conta**. Cada uma linka o
> conceito que a sustenta.

1. **A GUI nunca marca impresso antes da confirmação física** do usuário → [[Confirmação física antes de marcar]]
2. **Reimpressão nunca altera** o estado de impresso → [[Estado já impresso]]
3. Estado de impresso é **por marketplace + conta + dia de despacho** → [[Estado já impresso]] · [[Dia de despacho]]
4. **Envio novo em grupo já impresso reabre o grupo como parcial** → [[Estado já impresso]]
5. `marcar_impresso` **recarrega do disco e mescla** antes de gravar, sob **trava entre processos** → [[Trava entre processos]] · [[estado]]
6. Tokens obtidos **sempre via `obter_token`**, nunca `renovar_token` direto (o refresh **rotaciona**) → [[Token e rotação do refresh]]
7. Refresh de token **serializado por lock** (threads **e** processos) → [[Token e rotação do refresh]]
8. Na Shopee, a etiqueta **só existe após organizar o envio e obter o AWB** → [[Shopee — organizar envio e AWB]]
9. `create_shipping_document` **exige `tracking_number`** (AWB) no corpo → [[Shopee — organizar envio e AWB]]
10. O bot **não imprime grupos da Shopee** (só consulta) → [[bot_telegram]]
11. O bot **não imprime grupos antigos** se a conta/loja ativa mudou → [[bot_telegram]]
12. Credenciais, estado, cache e config **são locais e nunca versionados** → [[Arquivos — locais vs versionados]]

## Áreas de risco (o que quebra se mexer sem cuidado)
> [!warning]
> - **`marcar_impresso`**: perder o merge/trava → GUI e bot apagam a marcação um do outro. Ler por `ler_json` em vez de `ler_estado` → corrupção vira `{}` mudo e a próxima marcação grava por cima. Ver [[Estado já impresso]].
> - **`obter_token`/`renovar_token`**: chamar renovar direto → corrida rotaciona o refresh e **trava a conta**. Ver [[Token e rotação do refresh]].
> - **Shopee AWB**: gerar etiqueta sem AWB → `logistics.tracking_number_invalid`. Ver [[Shopee — organizar envio e AWB]].
> - **Modo Ambas**: token/estado da conta errada ao fundir → imprime/marca no lugar errado. Ver [[Modo Ambas (ML)]].
> - **Ordem "gera → confirma → marca"**: alterá-la fura a invariante 1. Ver [[Confirmação física antes de marcar]].
> - **Prefixo do ZIP na Downloads**: mudá-lo quebra a detecção do app Zebra. Ver [[Ponte com a Zebra]].

## Relacionado
- [[🏠 Home]] · [[Fluxos de operação]] · [[Testes como documentação]]
