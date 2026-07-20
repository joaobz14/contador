# fetch-render.ps1
# Pre-renderiza as fontes que sao SPA (JavaScript no cliente) usando o Edge
# headless — que JA vem no Windows, sem instalar nada — e salva o DOM ja
# hidratado em api-monitor/fetched/<slug>.html. O run-semanal.ps1 chama isto
# ANTES do claude, para o claude comparar arquivos LOCAIS em vez de depender do
# WebFetch (que numa SPA pega so a casca vazia).
#
# Hoje cobre so as 2 fontes Shopee. O ML nao entra aqui: a doc /pt_br/ ja e
# capturada pelo caminho normal, e o /devcenter/news/ e login (nem Edge resolve).
#
# Se o Edge nao renderizar (saida vazia/suspeita), o log avisa e o claude cai
# no comportamento de "fonte bloqueada" — nada quebra.

$ErrorActionPreference = 'Stop'
$ScriptDir = $PSScriptRoot
$OutDir = Join-Path $ScriptDir 'fetched'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'

$fontes = @(
    @{ slug = 'shopee-announcements'; url = 'https://open.shopee.com/announcements' }
    @{ slug = 'shopee-documents';     url = 'https://open.shopee.com/documents' }
)

# Localiza o msedge.exe (64 ou 32 bits).
$edge = @("$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
          "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe") |
        Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $edge) {
    Write-Warning "Edge nao encontrado — Shopee nao sera pre-renderizada (o claude marcara como bloqueada)."
    return
}
Write-Host "Edge: $edge"

foreach ($f in $fontes) {
    $out = Join-Path $OutDir "$($f.slug).html"
    $tmp = "$out.part"
    $errf = "$out.err"
    Write-Host "Renderizando $($f.slug) ($($f.url)) ..."
    try {
        # --dump-dom: serializa o DOM apos a SPA hidratar.
        # --virtual-time-budget: da tempo do JS rodar e faz o headless sair sozinho.
        # --user-data-dir em TEMP: nao mexe no seu perfil real do Edge.
        $argList = @(
            '--headless=new', '--disable-gpu', '--no-first-run',
            '--no-default-browser-check', '--disable-extensions',
            "--user-data-dir=$env:TEMP\edge-apimonitor",
            "--user-agent=$UA", '--virtual-time-budget=15000',
            '--dump-dom', $f.url
        )
        Start-Process -FilePath $edge -ArgumentList $argList -NoNewWindow -Wait `
            -RedirectStandardOutput $tmp -RedirectStandardError $errf | Out-Null

        $len = if (Test-Path $tmp) { (Get-Item $tmp).Length } else { 0 }
        if ($len -gt 0) {
            Move-Item -Force $tmp $out
            # heuristica so para o LOG (o claude decide de verdade): SPA que nao
            # renderizou costuma vir bem curta.
            $flag = if ($len -lt 2000) { 'SUSPEITO (curto — pode ser casca vazia/login)' } else { 'ok' }
            Write-Host ("  -> {0} bytes [{1}] -> {2}" -f $len, $flag, $out)
        }
        else {
            Write-Warning "  -> saida vazia para $($f.slug) (Edge nao dumpou o DOM)"
            if (Test-Path $tmp) { Remove-Item $tmp -Force }
        }
    }
    catch {
        Write-Warning "  -> falhou: $($_.Exception.Message)"
    }
    finally {
        if (Test-Path $errf) { Remove-Item $errf -Force -ErrorAction SilentlyContinue }
    }
}
