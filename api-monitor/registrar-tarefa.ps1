# registrar-tarefa.ps1
# Registra (ou atualiza) a tarefa semanal no Agendador de Tarefas do Windows que
# roda api-monitor\run-semanal.ps1. PowerShell nativo (Register-ScheduledTask),
# sem Git Bash.
#
# Rode UMA VEZ, na SUA maquina Windows, no PowerShell:
#   powershell -NoProfile -ExecutionPolicy Bypass -File api-monitor\registrar-tarefa.ps1
#
# Ajuste o dia/horario nas variaveis abaixo se quiser.

$ErrorActionPreference = 'Stop'

# ---- configuracao (edite se quiser) --------------------------------------
$DiaSemana = 'Monday'      # Monday..Sunday
$Hora      = '09:00'       # HH:mm (24h)
$NomeTarefa = 'Contador - Monitor APIs (semanal)'
# --------------------------------------------------------------------------

$ScriptDir = $PSScriptRoot                          # ...\contador\api-monitor
$RunScript = Join-Path $ScriptDir 'run-semanal.ps1'
if (-not (Test-Path $RunScript)) { throw "Nao achei run-semanal.ps1 em $ScriptDir" }

$psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'

# Acao: chama o run-semanal.ps1 sem perfil e com policy Bypass (so para este processo).
$acao = New-ScheduledTaskAction -Execute $psExe `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RunScript`"" `
    -WorkingDirectory (Split-Path $ScriptDir -Parent)

# Gatilho: semanal, no dia/hora escolhidos.
$gatilho = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DiaSemana -At $Hora

# Roda com o usuario atual, so quando ele estiver logado (nao precisa guardar senha).
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

# Se o PC estava desligado na hora, roda assim que puder; nao mata se demorar.
$config = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $NomeTarefa -Action $acao -Trigger $gatilho `
    -Principal $principal -Settings $config `
    -Description 'Checa semanalmente mudancas nas APIs do Mercado Livre e Shopee (rodando claude -p).' `
    -Force | Out-Null

Write-Host "OK: tarefa registrada -> '$NomeTarefa'" -ForegroundColor Green
$info = Get-ScheduledTaskInfo -TaskName $NomeTarefa
Write-Host ("Proxima execucao: {0}" -f $info.NextRunTime)
Write-Host "Rodar agora (teste):  Start-ScheduledTask -TaskName '$NomeTarefa'"
Write-Host "Ver estado:           Get-ScheduledTaskInfo -TaskName '$NomeTarefa'"
Write-Host "Remover:              Unregister-ScheduledTask -TaskName '$NomeTarefa' -Confirm:`$false"
