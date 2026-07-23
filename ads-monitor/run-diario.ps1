# run-diario.ps1
# Executa a coleta diaria do Product Ads (ads-monitor\coletar.py) -- default:
# ontem, todas as contas configuradas. Idempotente (regrava, nao duplica), entao
# rodar de novo no mesmo dia (ex.: apos falha de rede) e seguro.
#
# Roda na maquina Windows do dono. PowerShell nativo (sem Git Bash), mesmo
# padrao do api-monitor\run-semanal.ps1.
#
# Uso manual:  powershell -NoProfile -ExecutionPolicy Bypass -File ads-monitor\run-diario.ps1
# (o Agendador de Tarefas chama exatamente esta linha -- ver registrar-tarefa.ps1)

$ErrorActionPreference = 'Stop'

# Diretorio do projeto = pasta-mae de ads-monitor/ (derivado, sem hardcode).
$ScriptDir  = $PSScriptRoot                       # ...\contador\ads-monitor
$ProjetoDir = Split-Path $ScriptDir -Parent       # ...\contador
$Coletor    = Join-Path $ScriptDir 'coletar.py'
$LogDir     = Join-Path $ScriptDir 'logs'

if (-not (Test-Path $Coletor)) { throw "Nao achei coletar.py em $ScriptDir" }
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$stamp   = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$LogFile = Join-Path $LogDir "run-$stamp.log"

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw "Comando 'python' (ou 'py') nao encontrado no PATH." }

# Trabalha na raiz do projeto (coletar.py importa separador_etiquetas_ml pelo
# caminho do proprio arquivo, entao o cwd nao afeta o import -- mas mantem o
# padrao dos outros scripts do repo).
Push-Location $ProjetoDir
try {
    "[$([DateTime]::Now)] Iniciando coleta diaria (cwd=$ProjetoDir)" | Tee-Object -FilePath $LogFile

    & $py $Coletor *>&1 | Tee-Object -FilePath $LogFile -Append

    $code = $LASTEXITCODE
    "[$([DateTime]::Now)] Fim. coletar.py exit=$code. Log: $LogFile" | Tee-Object -FilePath $LogFile -Append
    exit $code
}
finally {
    Pop-Location
}
