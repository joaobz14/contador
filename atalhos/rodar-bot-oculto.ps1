# rodar-bot-oculto.ps1
# Sobe 'Iniciar Bot (auto).bat' (lancador com reinicio automatico ja existente)
# SEM janela visivel. Chamado pelo Agendador de Tarefas no login do Windows
# (ver registrar-tarefa-bot.ps1) -- nao precisa rodar isto na mao.

$ErrorActionPreference = 'Stop'
$Bat = Join-Path $PSScriptRoot 'Iniciar Bot (auto).bat'
# `-Wait` NAO e detalhe: sem ele o PowerShell saia no primeiro segundo, o
# Agendador dava a tarefa por TERMINADA e o bot ficava orfao -- fora da arvore
# da tarefa. Ai `schtasks /end` nao tinha o que matar e `schtasks /run` subia um
# SEGUNDO bot por cima do primeiro (os dois brigando pelo getUpdates, erro 409,
# com o ANTIGO continuando a responder: "reiniciei e a versao nao mudou",
# achado em 2026-08-04). Com o -Wait a tarefa fica "Em execucao" enquanto o bot
# viver, que e a verdade. O ExecutionTimeLimit da tarefa ja e zero (sem limite),
# entao esperar o dia inteiro aqui e o esperado.
Start-Process -FilePath $Bat -WindowStyle Hidden -Wait
