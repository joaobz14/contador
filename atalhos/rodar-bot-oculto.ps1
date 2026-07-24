# rodar-bot-oculto.ps1
# Sobe 'Iniciar Bot (auto).bat' (lancador com reinicio automatico ja existente)
# SEM janela visivel. Chamado pelo Agendador de Tarefas no login do Windows
# (ver registrar-tarefa-bot.ps1) -- nao precisa rodar isto na mao.

$ErrorActionPreference = 'Stop'
$Bat = Join-Path $PSScriptRoot 'Iniciar Bot (auto).bat'
Start-Process -FilePath $Bat -WindowStyle Hidden
