Verifique se houve mudanças nas 4 fontes abaixo desde o último snapshot em
api-monitor/snapshots/.
Fontes:
1. https://developers.mercadolivre.com.br/devcenter/news/
2. https://developers.mercadolivre.com.br/pt_br/api-docs-pt-br
3. https://open.shopee.com/announcements
4. https://open.shopee.com/documents

Para cada uma: busque o conteúdo atual, compare com o snapshot salvo, liste
só o que é novo ou mudou de fato (nova política, endpoint, prazo,
depreciação, taxa) e ignore mudanças cosméticas. Se alguma fonte estiver
bloqueada, registre isso em vez de falhar. Sobrescreva o snapshot com o
conteúdo atual. Gere o relatório em api-monitor/relatorios/<data>.md com o
resultado por fonte e um aviso de "requer atenção" quando a mudança parecer
afetar operação real. Se nada mudou, diga isso claramente.
