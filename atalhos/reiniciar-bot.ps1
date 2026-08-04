# reiniciar-bot.ps1
# Reinicia o bot do Telegram de forma CONFIAVEL, deixando exatamente UM rodando.
#
# Por que existe (achado 2026-08-04): a receita antiga era
#   schtasks /end /tn "..."  +  schtasks /run /tn "..."
# e ela NAO funcionava. O `rodar-bot-oculto.ps1` subia o .bat com `Start-Process`
# sem `-Wait`: o PowerShell saia na hora, o Agendador dava a tarefa por
# terminada, e o `cmd.exe` do laco mais o `python.exe` do bot ficavam ORFAOS,
# fora da arvore da tarefa. O `/end` nao tinha o que matar e o `/run` subia um
# SEGUNDO bot por cima do primeiro. Os dois ficavam brigando pelo getUpdates
# (erro 409 do Telegram) e o antigo continuava respondendo -- o sintoma era
# "reiniciei e o /versao insiste na versao velha".
#
# O `-Wait` foi acrescentado la, mas este script NAO depende dele: ele mata os
# processos por identificacao propria, entao funciona mesmo com uma instancia
# antiga (orfa) ainda de pe. Rode:
#   powershell -NoProfile -ExecutionPolicy Bypass -File atalhos\reiniciar-bot.ps1
# ou de um duplo clique em 'Reiniciar Bot.bat'.

$ErrorActionPreference = 'Stop'
$NomeTarefa = 'Contador - Bot do Telegram (login)'

function Processos-Do-Bot {
    # So python/pythonw: filtrar pelo NOME evita que este proprio PowerShell
    # entre na conta (a linha de comando dele contem "bot_telegram" por causa
    # deste filtro -- um `-like '*bot_telegram*'` solto se mataria sozinho).
    Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
        Where-Object { $_.CommandLine -like '*bot_telegram*' }
}

function Lancadores {
    # O .bat e um LACO: matar so o python faz ele ressuscitar o bot antigo em
    # 15s. Para um reinicio limpo, o lancador cai junto e sobe uma vez so.
    Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" |
        Where-Object { $_.CommandLine -like '*Iniciar Bot (auto)*' }
}

$bots = @(Processos-Do-Bot)
$lanc = @(Lancadores)
Write-Host "Encontrado: $($bots.Count) bot(s) e $($lanc.Count) lancador(es)."
if ($bots.Count -gt 1) {
    Write-Host "  (mais de um bot rodando -- era isso que segurava a versao antiga)" -ForegroundColor Yellow
}

foreach ($p in @($lanc) + @($bots)) {          # lancador primeiro: nao ressuscita
    try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop }
    catch { Write-Host "  nao consegui parar o PID $($p.ProcessId): $_" -ForegroundColor Yellow }
}

# Espera a fila esvaziar de verdade antes de subir de novo: dois bots pollando
# o mesmo token brigam (409) e o sintoma volta.
for ($i = 0; $i -lt 20 -and (@(Processos-Do-Bot).Count -gt 0); $i++) { Start-Sleep -Milliseconds 500 }
if (@(Processos-Do-Bot).Count -gt 0) {
    Write-Host "AINDA ha bot de pe. Feche na mao (Gerenciador de Tarefas) e rode de novo." -ForegroundColor Red
    exit 1
}

# Sobe UMA vez. Pela tarefa quando ela existir (mesmo caminho do logon); senao,
# direto pelo .bat -- um setup sem a tarefa registrada continua utilizavel.
schtasks /query /tn "$NomeTarefa" *> $null
if ($LASTEXITCODE -eq 0) {
    schtasks /run /tn "$NomeTarefa" *> $null
    Write-Host "Bot reiniciado pela tarefa do Agendador." -ForegroundColor Green
} else {
    $bat = Join-Path $PSScriptRoot 'Iniciar Bot (auto).bat'
    Start-Process -FilePath $bat -WindowStyle Hidden
    Write-Host "Bot reiniciado pelo lancador (tarefa nao registrada)." -ForegroundColor Green
}
Write-Host "Mande /versao no Telegram em uns 15s para confirmar."
