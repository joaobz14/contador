# run-semanal.ps1
# Executa a checagem semanal das APIs (ML + Shopee) rodando o proprio Claude Code
# (claude -p) com o prompt de api-monitor/prompt-semanal.md.
#
# Roda na maquina Windows do dono (rede aberta). Nao usa Git Bash — PowerShell
# nativo, para evitar traducao de caminho Windows->shell.
#
# Uso manual:  powershell -NoProfile -ExecutionPolicy Bypass -File api-monitor\run-semanal.ps1
# (o Agendador de Tarefas chama exatamente esta linha — ver registrar-tarefa.ps1)

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

$prompt = Get-Content -Path $PromptFile -Raw

# Trabalha na raiz do projeto (o prompt referencia caminhos relativos: api-monitor/...).
Push-Location $ProjetoDir
try {
    "[$([DateTime]::Now)] Iniciando checagem semanal (cwd=$ProjetoDir)" | Tee-Object -FilePath $LogFile

    # Pre-renderiza as fontes SPA (Shopee) via Edge headless -> api-monitor/fetched/.
    # O claude compara esses arquivos locais em vez de tentar o WebFetch (que numa
    # SPA pega casca vazia). Best-effort: se falhar, o claude marca "bloqueada".
    $fetchScript = Join-Path $ScriptDir 'fetch-render.ps1'
    if (Test-Path $fetchScript) {
        "[$([DateTime]::Now)] Pre-renderizando fontes SPA (Edge headless)..." | Tee-Object -FilePath $LogFile -Append
        try { & $fetchScript *>&1 | Tee-Object -FilePath $LogFile -Append }
        catch { "  aviso: pre-render falhou: $($_.Exception.Message)" | Tee-Object -FilePath $LogFile -Append }
    }

    # -p (--print): modo nao-interativo, imprime o resultado e sai.
    # --permission-mode bypassPermissions: roda sem pedir confirmacao (tarefa
    #   automatica, sem ninguem para responder prompts). Se preferir restringir,
    #   troque por:  --allowedTools "WebFetch,Read,Write,Edit"
    # O prompt vai por stdin (multilinha, sem problema de aspas).
    $prompt | & $Claude -p --permission-mode bypassPermissions *>&1 |
        Tee-Object -FilePath $LogFile -Append

    $code = $LASTEXITCODE
    "[$([DateTime]::Now)] Fim. claude exit=$code. Log: $LogFile" | Tee-Object -FilePath $LogFile -Append
    exit $code
}
finally {
    Pop-Location
}
