"""
Testes das funcoes de impressao pelo bot do Telegram.

So a UI (botoes) e testada aqui; a impressao em si reusa imprimir_pendentes do
nucleo, ja coberto em test_estado/test_pipeline. O bot depende de
python-telegram-bot (requirements-bot.txt); onde ele nao estiver instalavel, os
testes sao pulados.
"""

from __future__ import annotations

import pytest

# So roda com as deps do bot (python-telegram-bot) realmente importaveis. Em
# ambientes onde o telegram nao importa (ex.: cryptography/cffi nativo ausente),
# o import pode estourar ate uma excecao nao-ImportError, entao capturamos tudo.
try:
    import bot_telegram as bot
except BaseException as e:  # noqa: BLE001 - pyo3 PanicException herda de BaseException
    pytest.skip(f"bot_telegram indisponivel: {e}", allow_module_level=True)

import separador_etiquetas_ml as core  # noqa: E402


def _grupo(chave="PRP", qtd=1, ships=(1, 2)):
    return core.Grupo(chave=chave, nome=f"{chave} — Produto", quantidade=qtd,
                      shipment_ids=list(ships))


def test_rotulo_grupo_cabe_no_limite():
    g = _grupo(chave="X" * 80, ships=(1, 2, 3))
    rotulo = bot._rotulo_grupo(g)
    assert rotulo.startswith("🖨 3×")
    assert len(rotulo) <= 60  # limite seguro do botao do Telegram


def test_teclado_grupos_um_botao_por_grupo_com_etiquetas():
    grupos = [_grupo("A", ships=(1, 2)), _grupo("B", ships=(3,))]
    teclado = bot._teclado_grupos(grupos)
    linhas = teclado.inline_keyboard
    assert len(linhas) == 2
    # o callback carrega o indice do grupo
    assert [linha[0].callback_data for linha in linhas] == ["ver:0", "ver:1"]


def test_teclado_grupos_ignora_grupos_sem_etiqueta():
    grupos = [_grupo("A", ships=(1,)), _grupo("B", ships=())]
    teclado = bot._teclado_grupos(grupos)
    assert len(teclado.inline_keyboard) == 1
    assert teclado.inline_keyboard[0][0].callback_data == "ver:0"


def test_teclado_grupos_vazio_retorna_none():
    assert bot._teclado_grupos([]) is None
    assert bot._teclado_grupos([_grupo("A", ships=())]) is None


def test_grupo_do_indice_fora_de_faixa():
    class Ctx:
        chat_data = {"grupos": [_grupo("A")]}

    ctx = Ctx()
    assert bot._grupo_do_indice(ctx, 0).chave == "A"
    assert bot._grupo_do_indice(ctx, 1) is None
    assert bot._grupo_do_indice(ctx, -1) is None


def test_grupo_do_indice_sem_lista():
    class Ctx:
        chat_data: dict = {}

    assert bot._grupo_do_indice(Ctx(), 0) is None
