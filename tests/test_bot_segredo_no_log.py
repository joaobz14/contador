"""O token do bot NAO pode ir para o log.

A URL da API do Telegram carrega o token no proprio caminho
(`https://api.telegram.org/bot<TOKEN>/getUpdates`), e a biblioteca HTTP registra
cada requisicao em INFO. Com o log do bot em INFO, o token ia inteiro para o
`bot.log` e para o console a cada chamada — e quem colasse o log pedindo ajuda
entregava o token junto (aconteceu em 2026-07-30).

Nao adianta o `sem_segredos` do `registro.py`: estes registros nascem DENTRO da
biblioteca, sem passar pelo nosso codigo. A unica defesa e nao deixa-los sair.
"""
from __future__ import annotations

import logging

import pytest

try:
    import bot_telegram as bot
except BaseException as e:  # noqa: BLE001 - pyo3 PanicException herda de BaseException
    pytest.skip(f"bot_telegram indisponivel: {e}", allow_module_level=True)

TOKEN_FALSO = "8123456789:AAF-fakefakefakefakefakefakefakefakeQ"
URL_COM_TOKEN = f"HTTP Request: POST https://api.telegram.org/bot{TOKEN_FALSO}/getUpdates"


@pytest.mark.parametrize("biblioteca", ["httpx", "httpcore"])
def test_requisicao_http_nao_chega_ao_log(caplog, biblioteca):
    """O INFO de requisicao da biblioteca HTTP nao pode ser emitido."""
    with caplog.at_level(logging.DEBUG):          # captura o MAXIMO possivel
        logging.getLogger(biblioteca).info(URL_COM_TOKEN)

    assert TOKEN_FALSO not in caplog.text, f"{biblioteca} vazou o token no log"


def test_erro_de_rede_continua_visivel(caplog):
    """WARNING para cima segue passando: cortar o INFO nao pode cegar o
    diagnostico de rede — um bot que nao conecta precisa dizer por que."""
    with caplog.at_level(logging.WARNING):
        logging.getLogger("httpx").warning("Connection refused")

    assert "Connection refused" in caplog.text


def test_o_log_do_proprio_bot_nao_foi_silenciado(caplog):
    """A correcao e cirurgica: so as bibliotecas HTTP sobem para WARNING. O que
    o bot registra (INFO) tem de continuar aparecendo, senao a operacao perde o
    diagnostico que o `registro.py` existe para dar."""
    with caplog.at_level(logging.INFO):
        bot.log.info("Alerta pos-horario: 2 venda(s) nova(s)")

    assert "Alerta pos-horario" in caplog.text


@pytest.mark.parametrize("biblioteca", ["httpx", "httpcore"])
def test_nivel_configurado_no_import(biblioteca):
    """Guarda o ajuste em si: alguem que remova as linhas do `basicConfig` faz
    este teste falhar antes de o token voltar a vazar em producao."""
    assert logging.getLogger(biblioteca).level >= logging.WARNING
