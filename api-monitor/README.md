# api-monitor — monitor semanal das APIs (Mercado Livre + Shopee)

Checa **uma vez por semana** se mudou algo na **documentação/políticas** das APIs
que o Separador usa — **sem consultar dados da conta**, só as páginas públicas.
Objetivo: pegar cedo depreciação de endpoint, nova política, prazo, taxa, etc.

## Fontes monitoradas

1. Mercado Livre — Devcenter Novidades: https://developers.mercadolivre.com.br/devcenter/news/
2. Mercado Livre — API Docs: https://developers.mercadolivre.com.br/pt_br/api-docs-pt-br
3. Shopee Open Platform — Announcements: https://open.shopee.com/announcements
4. Shopee Open Platform — Documents: https://open.shopee.com/documents

## Estrutura

```
api-monitor/
├─ prompt-semanal.md      # o prompt que a rotina roda toda semana
├─ run-semanal.ps1        # executa a checagem (pré-renderiza Shopee + chama `claude -p`)
├─ fetch-render.py        # renderiza as SPAs da Shopee via Playwright (Edge do sistema)
├─ registrar-tarefa.ps1   # registra a tarefa semanal no Agendador do Windows (rode 1x)
├─ snapshots/             # conteúdo da última coleta, 1 arquivo por fonte
├─ fetched/               # HTML pré-renderizado das SPAs (gitignorado, efêmero)
├─ relatorios/            # 1 relatório por execução (api-monitor/relatorios/<data>.md)
└─ logs/                  # saída bruta de cada run (gitignorado)
```

## Como funciona

`run-semanal.ps1` primeiro **pré-renderiza as fontes SPA da Shopee** com o
**Playwright dirigindo o Edge do sistema** (`fetch-render.py`), salvando o HTML
já hidratado em `fetched/`. Depois roda o **próprio Claude Code** (`claude -p`)
com o texto de `prompt-semanal.md`: o Claude lê a Shopee dos arquivos locais e
busca o ML direto, compara com o snapshot salvo, lista só o que mudou de fato,
sobrescreve o snapshot e grava `relatorios/<data>.md` (com "requer atenção"
quando a mudança afeta operação real).

### Cobertura real das 4 fontes

- **ML API Docs** (fonte 2): via WebFetch — **funciona**.
- **Shopee Announcements / Documents** (3, 4): SPAs — capturadas via **Playwright
  + Edge do sistema** (`fetch-render.py`). O Edge `--dump-dom` por linha de
  comando devolvia vazio no `--headless=new`, então usamos o Playwright, que
  espera a SPA hidratar. Se não renderizar, o log avisa e o relatório marca
  "bloqueada" (sem inventar).
- **ML Novidades** (fonte 1): a página `/devcenter/news/` exige **login** (área
  logada do console) — não há URL/RSS público equivalente, então não é
  automatizável por fetch. Fica marcada como bloqueada. As mudanças de **API**
  de verdade aparecem na fonte 2 (API Docs), que é monitorada.

## Instalação (uma vez, na máquina Windows)

No PowerShell, na pasta do projeto (ex.: `C:\contador`):

```powershell
# 0) (uma vez) instalar o Playwright para renderizar a Shopee. Usa o Edge que
#    você já tem (channel=msedge), então NÃO baixa navegador nenhum.
pip install playwright

# 1) (opcional) rodar uma vez à mão para criar o baseline e conferir que funciona
powershell -NoProfile -ExecutionPolicy Bypass -File api-monitor\run-semanal.ps1

# 2) registrar a tarefa semanal (segunda 09:00 por padrão — edite no script se quiser)
powershell -NoProfile -ExecutionPolicy Bypass -File api-monitor\registrar-tarefa.ps1
```

> **Nota:** o `pip install playwright` precisa ir para o **mesmo Python** que o
> `run-semanal.ps1` acha no PATH (`python`/`py`). Se a Shopee continuar vindo
> vazia depois disso, confirme com `python -c "import playwright"` que o pacote
> está no Python certo.

O `registrar-tarefa.ps1` usa `Register-ScheduledTask` (PowerShell nativo, **não**
Git Bash — evita a tradução de caminho Windows→shell que já deu problema antes).
Ele imprime a **próxima data de execução** ao final. A tarefa roda com o seu
usuário, **só quando você está logado** (não guarda senha).

Comandos úteis depois:
```powershell
Start-ScheduledTask   -TaskName 'Contador - Monitor APIs (semanal)'   # rodar agora
Get-ScheduledTaskInfo -TaskName 'Contador - Monitor APIs (semanal)'   # ver próxima execução / último resultado
Unregister-ScheduledTask -TaskName 'Contador - Monitor APIs (semanal)' -Confirm:$false  # remover
```

## Notas

- **Permissões:** `run-semanal.ps1` chama `claude -p --permission-mode
  bypassPermissions` para rodar sem pedir confirmação (é tarefa automática, sem
  ninguém para responder). Se preferir restringir, troque por
  `--allowedTools "WebFetch,Read,Write,Edit"` no script.
- **Baseline inicial vazio:** os snapshots começam vazios porque a configuração
  foi feita num ambiente de nuvem com **rede restrita** que não alcança essas
  fontes (ver `relatorios/2026-07-17.md`). O baseline é criado na **primeira
  execução local**. Não há nada inventado.
- **Churn de git:** cada execução sobrescreve `snapshots/` e cria um novo
  `relatorios/<data>.md`. Isso aparece como alteração no git — versione (fica um
  histórico bonito do que mudou nas APIs) ou ignore, como preferir. `logs/` já é
  gitignorado.
