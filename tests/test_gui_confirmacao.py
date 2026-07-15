"""Persistência pós-confirmação da GUI: etiqueta impressa nunca perde a
marcação em silêncio (_marcar_lote_tolerante) — achado P2 da revisão."""
from __future__ import annotations

import pytest

# So roda onde o tkinter importa (o modulo da GUI importa tk no topo). Nao
# precisa de display: _marcar_lote_tolerante e pura (callables injetados).
try:
    import separador_gui as gui
except Exception as _e:  # noqa: BLE001 - ambiente sem tkinter
    pytest.skip(f"separador_gui nao importavel aqui: {_e}", allow_module_level=True)

import separador_etiquetas_ml as core


def _g(nome):
    return core.Grupo(chave=nome, nome=nome, quantidade=1, shipment_ids=["S1"])


def test_todos_marcados_sem_falha():
    marcados = []
    falhas = gui._marcar_lote_tolerante(
        lambda g, pend: marcados.append(g.nome),
        [(_g("A"), ["S1"]), (_g("B"), ["S1"])],
        perguntar_retry=lambda nome, erro: (_ for _ in ()).throw(
            AssertionError("nao deveria perguntar")),
    )
    assert marcados == ["A", "B"] and falhas == []


def test_falha_num_grupo_nao_derruba_o_resto():
    """B falha (retry recusado): A e C sao marcados; B volta como falha."""
    marcados = []

    def marcar(g, pend):
        if g.nome == "B":
            raise OSError("disco cheio")
        marcados.append(g.nome)

    falhas = gui._marcar_lote_tolerante(
        marcar, [(_g("A"), ["S1"]), (_g("B"), ["S1"]), (_g("C"), ["S1"])],
        perguntar_retry=lambda nome, erro: False)
    assert marcados == ["A", "C"]
    assert len(falhas) == 1 and falhas[0][0] == "B" and "disco cheio" in falhas[0][1]


def test_retry_resolve_falha_transitoria():
    """1a gravacao falha (arquivo preso), retry aceito, 2a passa: sem falhas."""
    tentativas = {"n": 0}

    def marcar(g, pend):
        tentativas["n"] += 1
        if tentativas["n"] == 1:
            raise OSError("arquivo em uso")

    falhas = gui._marcar_lote_tolerante(
        marcar, [(_g("A"), ["S1"])], perguntar_retry=lambda nome, erro: True)
    assert falhas == [] and tentativas["n"] == 2


def test_erro_com_segredo_sai_redigido():
    def marcar(g, pend):
        raise RuntimeError("url?access_token=SEGREDO123&sign=ASS456 falhou")

    falhas = gui._marcar_lote_tolerante(
        marcar, [(_g("A"), ["S1"])], perguntar_retry=lambda nome, erro: False)
    (nome, erro), = falhas
    assert "SEGREDO123" not in erro and "ASS456" not in erro
    assert "access_token=***" in erro
