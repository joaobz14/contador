@echo off
REM ============================================================
REM  Forca uma checagem do alerta pos-horario AGORA, sem esperar
REM  os 5 minutos do agendamento nem uma venda nova cair.
REM
REM  Usa a config/contas/token DE VERDADE: se houver algum envio
REM  ja pronto pra hoje (ready_to_print) que ainda nao foi
REM  avisado, manda a mensagem de verdade no Telegram agora.
REM  Se nao houver nada novo, so avisa que nao achou nada (nao
REM  manda mensagem a toa).
REM
REM  A janela fica aberta ate o fim (mesmo com erro) para ler.
REM ============================================================

cd /d "%~dp0.."

python bot_telegram.py testar-alerta
