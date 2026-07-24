# registrar-tarefa-bot.ps1
# Registra (ou atualiza) uma tarefa no Agendador de Tarefas do Windows que
# sobe o bot do Telegram sozinho, sem janela visivel, toda vez que voce faz
# login no Windows -- sem precisar lembrar de abrir o .bat na mao, e sem
# depender da tela (separador_gui.py) estar aberta.
#
# Rode UMA VEZ, na SUA maquina Windows, no PowerShell:
#   powershell -NoProfile -ExecutionPolicy Bypass -File atalhos\registrar-tarefa-bot.ps1
#
# O bot sobe via 'Iniciar Bot (auto).bat' (reinicio automatico se cair) --
# reusa o lancador ja existente em vez de reimplementar retry aqui.

$ErrorActionPreference = 'Stop'

$NomeTarefa = 'Contador - Bot do Telegram (login)'

$ScriptDir  = $PSScriptRoot                                    # ...\contador\atalhos
$RunScript  = Join-Path $ScriptDir 'rodar-bot-oculto.ps1'
if (-not (Test-Path $RunScript)) { throw "Nao achei rodar-bot-oculto.ps1 em $ScriptDir" }

$psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'

# Acao: chama o wrapper oculto, que sobe o .bat sem janela visivel.
$acao = New-ScheduledTaskAction -Execute $psExe `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RunScript`"" `
    -WorkingDirectory $ScriptDir

# Gatilho: no login do usuario atual (nao no boot do PC -- nao precisa de
# senha guardada nem rodar antes de alguem logar).
$gatilho = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"

# Roda com o usuario atual, so quando ele estiver logado (mesmo padrao do
# registrar-tarefa.ps1 do ads-monitor).
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

# Sem limite de tempo de execucao -- o bot fica de pe o dia todo (o
# ExecutionTimeLimit padrao do Agendador mataria o processo depois de
# algumas horas, o que derrubaria o bot sem motivo).
$config = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $NomeTarefa -Action $acao -Trigger $gatilho `
    -Principal $principal -Settings $config `
    -Description 'Sobe o bot do Telegram (alerta de venda pronta pra hoje + consulta remota) no login, sem janela visivel.' `
    -Force | Out-Null

Write-Host "OK: tarefa registrada -> '$NomeTarefa'" -ForegroundColor Green
Write-Host "Vai subir sozinho no proximo login. Pra testar agora:"
Write-Host "  Start-ScheduledTask -TaskName '$NomeTarefa'"
Write-Host "Ver estado:  Get-ScheduledTaskInfo -TaskName '$NomeTarefa'"
Write-Host "Remover:     Unregister-ScheduledTask -TaskName '$NomeTarefa' -Confirm:`$false"
