# api-monitor — monitor semanal das APIs (Mercado Livre + Shopee)

> [!warning] **DESATIVADO em 05/08/2026** (pausa, não desistência)
>
> `run-semanal.ps1` e `registrar-tarefa.ps1` **não rodam mais** — os dois saem
> logo no começo com um aviso. O código foi preservado inteiro; para reativar,
> apague os blocos marcados `ARQUIVADO` no topo de cada um.
>
> **Por que:** nunca se conseguiu acesso confiável às fontes. A fonte 1 (ML
> Novidades) exige **login** do console e não tem equivalente público; as 3 e 4
> (Shopee) são SPAs que dependem do Playwright + Edge renderizar, e nem sempre
> renderizam. Uma rotina que marca "bloqueada" toda semana não monitora nada —
> e continuava **custando uma chamada paga de IA por semana**.
>
> **O que importava mais que o desperdício** (auditoria de 05/08/2026): a rotina
> rodava `claude -p --permission-mode bypassPermissions`, **sem ninguém olhando**,
> com o `cwd` na raiz do projeto — a mesma pasta de `dados/contas/*/credenciais.json`,
> `credenciais_shopee.json` e `bot_config.json` (token do Telegram e as URLs dos
> webhooks do n8n, que são credenciais). E a **entrada** dela era conteúdo baixado
> da web. Probabilidade baixa, raio de alcance igual às credenciais do negócio.
> A flag foi trocada por `--allowedTools "WebFetch,Read,Write,Edit"` (em modo `-p`,
> ferramenta fora da lista falha em vez de perguntar — funciona sem ninguém
> presente, **sem shell**), para que uma reativação futura não reinstale o risco
> por descuido.
>
> **O que destrava:** uma fonte pública e estável para as novidades do ML (RSS,
> changelog, ou a área logada via API) e uma captura da Shopee que não dependa de
> renderizar SPA. Sem isso, reativar só recria o relatório vazio.
>
> **Enquanto isso**, mudança de API aparece do jeito de sempre: quebrando algo, e
> aí os diagnósticos do projeto dizem o quê (`python separador_etiquetas_ml.py
> substatus`, `python shopee_api.py status`).

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
├─ snapshots/             # conteúdo da última coleta, 1 arquivo por fonte (gitignorado; só o README é versionado)
├─ fetched/               # HTML pré-renderizado das SPAs (gitignorado, efêmero)
├─ relatorios/            # 1 relatório por execução (gitignorado; local)
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

- **Permissões (corrigido em 05/08/2026, junto com a desativação):**
  `run-semanal.ps1` chamava `claude -p --permission-mode bypassPermissions` — sem
  restrição nenhuma, sem ninguém olhando, na pasta das credenciais e com conteúdo
  da web como entrada. Hoje usa `--allowedTools "WebFetch,Read,Write,Edit"`: em
  modo `-p`, ferramenta fora da lista **falha** em vez de perguntar, então
  continua rodando desassistido, mas **sem shell**. **Se reativar, mantenha a
  lista** — a flag antiga é o risco que motivou desligar tudo.
- **Baseline inicial vazio:** os snapshots começam vazios porque a configuração
  foi feita num ambiente de nuvem com **rede restrita** que não alcança essas
  fontes (ver `relatorios/2026-07-17.md`). O baseline é criado na **primeira
  execução local**. Não há nada inventado.
- **Saídas do monitor NÃO são versionadas:** `snapshots/` (baselines),
  `relatorios/`, `fetched/` e `logs/` são **gitignorados** — são dados locais,
  recriados a cada run. Só a **infra** (prompt, scripts, `README`, o
  `snapshots/README.md`) é versionada. Isso evita que cada execução deixasse a
  cópia de `C:\contador` "modificada" e travasse o `git pull` seguinte. O
  baseline vive na sua máquina; a primeira execução o cria.
