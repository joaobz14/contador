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
    catch {
        # Processo que JA saiu nao e falha -- e o caso tipico aqui: o python do
        # bot cai junto com o cmd.exe do lancador, entao quando chega a vez dele
        # na lista ele nao existe mais. Avisar nesse caso seria um alarme falso
        # num caminho de SUCESSO, e alarme falso ensina a ignorar o alarme.
        if (Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue) {
            Write-Host "  nao consegui parar o PID $($p.ProcessId): $_" -ForegroundColor Yellow
        }
    }
}

# Espera a fila esvaziar de verdade antes de subir de novo: dois bots pollando
# o mesmo token brigam (409) e o sintoma volta.
for ($i = 0; $i -lt 20 -and (@(Processos-Do-Bot).Count -gt 0); $i++) { Start-Sleep -Milliseconds 500 }
if (@(Processos-Do-Bot).Count -gt 0) {
    Write-Host "AINDA ha bot de pe. Feche na mao (Gerenciador de Tarefas) e rode de novo." -ForegroundColor Red
    exit 1
}

# Espera o LANCADOR sair tambem. Nao e detalhe (achado 2026-08-05: "tenho que
# abrir o Reiniciar Bot.bat 2x"): enquanto o cmd.exe do laco existir, o
# `Start-Process -Wait` do rodar-bot-oculto.ps1 ainda nao voltou e a TAREFA
# continua "Em execucao" -- e o Agendador RECUSA `schtasks /run` numa tarefa que
# ja esta rodando (regra padrao: nao iniciar nova instancia). O laco anterior so
# olhava o python, que ja tinha morrido, entao saia na hora e o /run vinha cedo
# demais. Na 1a execucao nada subia; na 2a a tarefa ja tinha liberado.
for ($i = 0; $i -lt 20 -and (@(Lancadores).Count -gt 0); $i++) { Start-Sleep -Milliseconds 500 }

function Tarefa-Rodando {
    try { (Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction Stop).State -eq 'Running' }
    catch { $false }   # tarefa inexistente nao esta rodando
}
for ($i = 0; $i -lt 20 -and (Tarefa-Rodando); $i++) { Start-Sleep -Milliseconds 500 }

# Sobe UMA vez. Pela tarefa quando ela existir (mesmo caminho do logon); senao,
# direto pelo .bat -- um setup sem a tarefa registrada continua utilizavel.
$subiu_por = ""
schtasks /query /tn "$NomeTarefa" *> $null
if ($LASTEXITCODE -eq 0) {
    schtasks /run /tn "$NomeTarefa" *> $null
    if ($LASTEXITCODE -eq 0) { $subiu_por = "tarefa do Agendador" }
    else { Write-Host "  o Agendador recusou iniciar a tarefa (codigo $LASTEXITCODE)." -ForegroundColor Yellow }
}

# CONFERE que um bot apareceu de verdade, em vez de anunciar sucesso e sair.
# Era exatamente isso que escondia a falha: o codigo de saida do `schtasks /run`
# era descartado e a mensagem verde saia de qualquer jeito, entao o unico
# sintoma visivel era "nao reiniciou, abre de novo".
for ($i = 0; $i -lt 30 -and (@(Processos-Do-Bot).Count -eq 0); $i++) { Start-Sleep -Milliseconds 500 }

if (@(Processos-Do-Bot).Count -eq 0) {
    # Ultimo recurso: sobe pelo .bat direto. Este script ja nao depende da
    # arvore da tarefa (mata por identificacao propria), entao um bot fora dela
    # e plenamente gerenciavel -- e bot de pe vale mais que bot na arvore certa.
    $bat = Join-Path $PSScriptRoot 'Iniciar Bot (auto).bat'
    Start-Process -FilePath $bat -WindowStyle Hidden
    $subiu_por = "lancador direto"
    for ($i = 0; $i -lt 30 -and (@(Processos-Do-Bot).Count -eq 0); $i++) { Start-Sleep -Milliseconds 500 }
}

if (@(Processos-Do-Bot).Count -eq 0) {
    Write-Host "NAO consegui subir o bot. Veja o fim de logs\bot.log -- se falar em " -ForegroundColor Red -NoNewline
    Write-Host "bot_config.json, o arquivo esta invalido." -ForegroundColor Red
    exit 1
}
Write-Host "Bot reiniciado ($subiu_por). Mande /versao no Telegram para confirmar." -ForegroundColor Green
