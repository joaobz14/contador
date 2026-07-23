# registrar-tarefa.ps1
# Registra (ou atualiza) a tarefa diaria no Agendador de Tarefas do Windows que
# roda ads-monitor\run-diario.ps1. PowerShell nativo (Register-ScheduledTask),
# sem Git Bash.
#
# Rode UMA VEZ, na SUA maquina Windows, no PowerShell:
#   powershell -NoProfile -ExecutionPolicy Bypass -File ads-monitor\registrar-tarefa.ps1
#
# Ajuste o horario na variavel abaixo se quiser.

$ErrorActionPreference = 'Stop'

# ---- configuracao (edite se quiser) --------------------------------------
# 11:00 -- depois das 10:00 GMT-3 que a doc oficial do Product Ads cita como
# horario de fechamento/validacao das metricas do dia anterior (a margem de
# 1h evita coletar "ontem" ainda provisorio, sem exagerar na espera).
$Hora       = '11:00'       # HH:mm (24h)
$NomeTarefa = 'Contador - Monitor Ads (diario)'
# --------------------------------------------------------------------------

$ScriptDir = $PSScriptRoot                          # ...\contador\ads-monitor
$RunScript = Join-Path $ScriptDir 'run-diario.ps1'
if (-not (Test-Path $RunScript)) { throw "Nao achei run-diario.ps1 em $ScriptDir" }

$psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'

# Acao: chama o run-diario.ps1 sem perfil e com policy Bypass (so para este processo).
$acao = New-ScheduledTaskAction -Execute $psExe `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RunScript`"" `
    -WorkingDirectory (Split-Path $ScriptDir -Parent)

# Gatilho: diario, no horario escolhido.
$gatilho = New-ScheduledTaskTrigger -Daily -At $Hora

# Roda com o usuario atual, so quando ele estiver logado (nao precisa guardar senha).
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

# Se o PC estava desligado na hora, roda assim que puder; nao mata se demorar
# (coleta com muitas campanhas/ad_groups pode levar alguns minutos).
$config = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $NomeTarefa -Action $acao -Trigger $gatilho `
    -Principal $principal -Settings $config `
    -Description 'Coleta diaria de metricas do Product Ads (Mercado Ads) -- so leitura.' `
    -Force | Out-Null

Write-Host "OK: tarefa registrada -> '$NomeTarefa'" -ForegroundColor Green
$info = Get-ScheduledTaskInfo -TaskName $NomeTarefa
Write-Host ("Proxima execucao: {0}" -f $info.NextRunTime)
Write-Host "Rodar agora (teste):  Start-ScheduledTask -TaskName '$NomeTarefa'"
Write-Host "Ver estado:           Get-ScheduledTaskInfo -TaskName '$NomeTarefa'"
Write-Host "Remover:              Unregister-ScheduledTask -TaskName '$NomeTarefa' -Confirm:`$false"
