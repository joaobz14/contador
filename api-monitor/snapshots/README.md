# snapshots/

Aqui ficam os **snapshots** (conteúdo salvo da última coleta) de cada fonte, um
arquivo por fonte:

- `ml-news.md` — Mercado Livre / Devcenter Novidades
- `ml-api-docs.md` — Mercado Livre / API Docs
- `shopee-announcements.md` — Shopee Open Platform / Announcements
- `shopee-documents.md` — Shopee Open Platform / Documents

**Estão vazios de propósito na configuração inicial:** o baseline não pôde ser
capturado do ambiente de nuvem (rede restrita — ver `relatorios/2026-07-17.md`).
Eles serão **criados na primeira execução local** (`run-semanal.ps1`) na máquina
Windows, que tem rede aberta. A partir daí, cada execução compara com o snapshot
e o sobrescreve com o conteúdo atual.
