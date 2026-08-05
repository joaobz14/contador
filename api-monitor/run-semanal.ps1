# run-semanal.ps1
# Executa a checagem semanal das APIs (ML + Shopee) rodando o proprio Claude Code
# (claude -p) com o prompt de api-monitor/prompt-semanal.md.
#
# Roda na maquina Windows do dono (rede aberta). Nao usa Git Bash - PowerShell
# nativo, para evitar traducao de caminho Windows->shell.
#
# Uso manual:  powershell -NoProfile -ExecutionPolicy Bypass -File api-monitor\run-semanal.ps1
# (o Agendador de Tarefas chama exatamente esta linha - ver registrar-tarefa.ps1)
#
# ############################################################################
# ARQUIVADO EM 05/08/2026 - ESTE SCRIPT NAO RODA MAIS (ver api-monitor/README.md)
#
# POR QUE: nunca se conseguiu acesso confiavel as fontes. A fonte 1 (ML
# Novidades) exige login do console e nao tem equivalente publico; as fontes 3 e
# 4 (Shopee) sao SPAs que dependem do Playwright+Edge renderizar. Uma rotina que
# marca "bloqueada" toda semana nao monitora nada -- e continuava CUSTANDO uma
# chamada paga de IA por semana.
#
# E POR QUE ISSO IMPORTAVA MAIS QUE O DESPERDICIO (auditoria de 05/08/2026): ela
# rodava `claude -p --permission-mode bypassPermissions`, sem ninguem olhando, com
# o cwd na raiz do projeto -- a mesma pasta onde ficam dados/contas/*/
# credenciais.json, credenciais_shopee.json e bot_config.json (token do Telegram
# e as URLs dos webhooks do n8n, que sao credenciais). E a entrada dela era
# CONTEUDO BAIXADO DA WEB. Probabilidade baixa, raio de alcance = as credenciais
# do negocio. Desativar era a decisao mais barata; a alternativa seria restringir
# as ferramentas (ver a linha do --allowedTools la embaixo, ja corrigida).
#
# PARA REATIVAR: resolva o acesso as fontes PRIMEIRO (sem isso o relatorio nasce
# vazio), apague o bloco abaixo e rode o registrar-tarefa.ps1 -- que tambem esta
# desativado. NAO volte com `bypassPermissions`.
# ############################################################################
Write-Host "api-monitor DESATIVADO em 05/08/2026 (fontes inacessiveis)." -ForegroundColor Yellow
Write-Host "Motivo e como reativar: api-monitor\README.md e o cabecalho deste arquivo."
exit 0

$ErrorActionPreference = 'Stop'

# Diretorio do projeto = pasta-mae de api-monitor/ (derivado, sem hardcode).
$ScriptDir  = $PSScriptRoot                       # ...\contador\api-monitor
$ProjetoDir = Split-Path $ScriptDir -Parent       # ...\contador
$PromptFile = Join-Path $ScriptDir 'prompt-semanal.md'
$LogDir     = Join-Path $ScriptDir 'logs'

if (-not (Test-Path $PromptFile)) { throw "Prompt nao encontrado: $PromptFile" }
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$stamp   = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$LogFile = Join-Path $LogDir "run-$stamp.log"

# claude precisa estar no PATH (instalacao normal do Claude Code). Se voce usa um
# caminho especifico, troque 'claude' por ele aqui.
$Claude = 'claude'
if (-not (Get-Command $Claude -ErrorAction SilentlyContinue)) {
    throw "Comando 'claude' nao encontrado no PATH. Ajuste a variavel `$Claude neste script."
}

# -Encoding UTF8: o prompt-semanal.md tem acentos; sem forcar UTF-8 o PS 5.1 le
# como ANSI e o prompt chega mojibake no claude.
$prompt = Get-Content -Path $PromptFile -Raw -Encoding UTF8

# Trabalha na raiz do projeto (o prompt referencia caminhos relativos: api-monitor/...).
Push-Location $ProjetoDir
try {
    "[$([DateTime]::Now)] Iniciando checagem semanal (cwd=$ProjetoDir)" | Tee-Object -FilePath $LogFile

    # Pre-renderiza as fontes SPA (Shopee) via Playwright dirigindo o Edge do
    # sistema (fetch-render.py) -> api-monitor/fetched/. O claude compara esses
    # arquivos locais em vez de tentar o WebFetch (que numa SPA pega casca vazia).
    # Best-effort: se python/playwright faltar, avisa e o claude marca "bloqueada".
    $fetchPy = Join-Path $ScriptDir 'fetch-render.py'
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
    if ($py -and (Test-Path $fetchPy)) {
        "[$([DateTime]::Now)] Pre-renderizando fontes SPA (Playwright/Edge)..." | Tee-Object -FilePath $LogFile -Append
        try { & $py $fetchPy *>&1 | Tee-Object -FilePath $LogFile -Append }
        catch { "  aviso: pre-render falhou: $($_.Exception.Message)" | Tee-Object -FilePath $LogFile -Append }
    }
    else {
        "  aviso: python nao encontrado no PATH - Shopee nao sera pre-renderizada" | Tee-Object -FilePath $LogFile -Append
    }

    # -p (--print): modo nao-interativo, imprime o resultado e sai.
    # --allowedTools (e NAO `--permission-mode bypassPermissions`, que era o que
    #   estava aqui): em modo -p, ferramenta fora da lista simplesmente falha em
    #   vez de perguntar, entao continua funcionando sem ninguem presente -- mas
    #   SEM shell. A entrada desta rotina e conteudo baixado da web, e ela roda
    #   com o cwd na pasta que guarda todas as credenciais do negocio; dar
    #   ferramenta irrestrita a um agente nessa posicao e o risco que motivou a
    #   desativacao (ver cabecalho). Se um dia reativar, mantenha a lista.
    # O prompt vai por stdin (multilinha, sem problema de aspas).
    $prompt | & $Claude -p --allowedTools "WebFetch,Read,Write,Edit" *>&1 |
        Tee-Object -FilePath $LogFile -Append

    $code = $LASTEXITCODE
    "[$([DateTime]::Now)] Fim. claude exit=$code. Log: $LogFile" | Tee-Object -FilePath $LogFile -Append
    exit $code
}
finally {
    Pop-Location
}
