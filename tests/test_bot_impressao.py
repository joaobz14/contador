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


# --------------------------------------------------------------------- contas
def _patch_contas(monkeypatch, tmp_path):
    pasta = tmp_path / "app"
    pasta.mkdir()
    monkeypatch.setattr(core, "PASTA_SCRIPT", pasta)
    monkeypatch.setattr(core, "PASTA_CONTAS", pasta / "contas")
    monkeypatch.setattr(core, "ARQUIVO_CONFIG", pasta / "config.json")
    monkeypatch.setattr(core, "ARQUIVO_CRED", pasta / "credenciais.json")
    return pasta


def _criar_conta(pasta, nome):
    p = pasta / "contas" / nome
    p.mkdir(parents=True)
    (p / "credenciais.json").write_text("{}", encoding="utf-8")


def test_garantir_conta_ativa_escolhe_primeira_quando_invalida(monkeypatch, tmp_path):
    pasta = _patch_contas(monkeypatch, tmp_path)
    _criar_conta(pasta, "Cozilatti")
    _criar_conta(pasta, "Gastromaq")
    # nenhuma conta_ativa salva -> deve escolher a 1a (ordem alfabetica) e gravar
    ativa = bot._garantir_conta_ativa()
    assert ativa == "Cozilatti"
    assert core.conta_ativa() == "Cozilatti"
    assert core.ARQUIVO_CRED == pasta / "contas" / "Cozilatti" / "credenciais.json"


def test_garantir_conta_ativa_respeita_a_salva(monkeypatch, tmp_path):
    pasta = _patch_contas(monkeypatch, tmp_path)
    _criar_conta(pasta, "Cozilatti")
    _criar_conta(pasta, "Gastromaq")
    bot._trocar_conta("Gastromaq")
    assert bot._garantir_conta_ativa() == "Gastromaq"


def test_garantir_conta_ativa_sem_contas(monkeypatch, tmp_path):
    _patch_contas(monkeypatch, tmp_path)
    assert bot._garantir_conta_ativa() == ""


def test_trocar_conta_aponta_arquivos_e_grava(monkeypatch, tmp_path):
    pasta = _patch_contas(monkeypatch, tmp_path)
    _criar_conta(pasta, "Gastromaq")
    bot._trocar_conta("Gastromaq")
    assert core.conta_ativa() == "Gastromaq"
    assert core.ARQUIVO_ESTADO == pasta / "contas" / "Gastromaq" / "estado_grupos.json"


def test_teclado_contas_marca_a_ativa(monkeypatch, tmp_path):
    teclado = bot._teclado_contas(["Cozilatti", "Gastromaq"], "Gastromaq")
    linhas = teclado.inline_keyboard
    assert [linha[0].callback_data for linha in linhas] == ["conta:0", "conta:1"]
    assert linhas[1][0].text.startswith("✓")      # a ativa leva o ✓
    assert not linhas[0][0].text.startswith("✓")


def test_conta_mudou(monkeypatch, tmp_path):
    pasta = _patch_contas(monkeypatch, tmp_path)
    _criar_conta(pasta, "Gastromaq")
    bot._trocar_conta("Gastromaq")

    class Ctx:
        chat_data = {"conta": "Gastromaq"}

    assert bot._conta_mudou(Ctx()) is False
    Ctx.chat_data = {"conta": "Cozilatti"}
    assert bot._conta_mudou(Ctx()) is True
