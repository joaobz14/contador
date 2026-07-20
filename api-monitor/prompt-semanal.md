NOTA DE COLETA (leia antes de tudo):
- Snapshots ficam em api-monitor/snapshots/<slug>.md — slugs: ml-news,
  ml-api-docs, shopee-announcements, shopee-documents.
- Fontes 3 e 4 (Shopee) são SPAs: NÃO use fetch direto da URL (vem casca
  vazia). Leia os arquivos LOCAIS já pré-renderizados pelo Edge headless:
  api-monitor/fetched/shopee-announcements.html e
  api-monitor/fetched/shopee-documents.html. Extraia deles o conteúdo de
  anúncios/documentos. Se o arquivo não existir, vier vazio, ou parecer página
  de login, marque a fonte como BLOQUEADA (registre o motivo, não invente).
- Fonte 1 (ML Novidades): se o fetch redirecionar para login, marque BLOQUEADA
  (é gate de autenticação real do console, não dá para automatizar).

Verifique se houve mudanças nas 4 fontes abaixo desde o último snapshot em
api-monitor/snapshots/.
Fontes:
1. https://developers.mercadolivre.com.br/devcenter/news/
2. https://developers.mercadolivre.com.br/pt_br/api-docs-pt-br
3. https://open.shopee.com/announcements
4. https://open.shopee.com/documents

Para cada uma: obtenha o conteúdo atual (fontes 1 e 2 via fetch da URL; fontes
3 e 4 pelos arquivos locais em api-monitor/fetched/ — ver NOTA acima), compare
com o snapshot salvo, liste só o que é novo ou mudou de fato (nova política,
endpoint, prazo, depreciação, taxa) e ignore mudanças cosméticas (espaçamento,
ordem de itens de menu, ruído de markup). Se alguma fonte estiver bloqueada,
registre isso em vez de falhar. Sobrescreva o snapshot com o conteúdo atual
(extraído/limpo, não o HTML cru). Gere o relatório em
api-monitor/relatorios/<data>.md com o resultado por fonte e um aviso de
"requer atenção" quando a mudança parecer afetar operação real. Se nada mudou,
diga isso claramente.
