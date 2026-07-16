"""Editores (Nomes/SKUs): instância única e indisponíveis durante operação
(auditoria 5.5). Sem abrir janelas Tk de verdade — os métodos não-vinculados são
ligados a fakes (mesma técnica de test_gui_confirmacao)."""
from __future__ import annotations

import types

import pytest

try:
    import separador_gui as gui
except Exception as _e:  # noqa: BLE001 - ambiente sem tkinter
    pytest.skip(f"separador_gui nao importavel aqui: {_e}", allow_module_level=True)


def _app(**kw):
    base = dict(ocupado=False, _editor_nomes=None, _editor_skus=None)
    base.update(kw)
    app = types.SimpleNamespace(**base)
    # liga o método real de foco (usado por abrir_editor_*) ao fake
    app._focar_editor_aberto = types.MethodType(gui.SeparadorApp._focar_editor_aberto, app)
    return app


def _win_viva():
    return types.SimpleNamespace(winfo_exists=lambda: True,
                                 lift=lambda: None, focus_set=lambda: None)


def test_focar_editor_aberto_traz_para_frente():
    chamou = {"lift": 0, "focus": 0}
    win = types.SimpleNamespace(
        winfo_exists=lambda: True,
        lift=lambda: chamou.__setitem__("lift", chamou["lift"] + 1),
        focus_set=lambda: chamou.__setitem__("focus", chamou["focus"] + 1))
    app = _app()
    assert gui.SeparadorApp._focar_editor_aberto(app, types.SimpleNamespace(win=win)) is True
    assert chamou == {"lift": 1, "focus": 1}
    assert gui.SeparadorApp._focar_editor_aberto(app, None) is False   # sem editor


def test_abrir_editor_nomes_instancia_unica(monkeypatch):
    criados = []
    monkeypatch.setattr(gui, "EditorNomes", lambda app: criados.append(app) or "ED")
    app = _app()
    gui.SeparadorApp.abrir_editor_nomes(app)          # 1a abertura cria
    assert app._editor_nomes == "ED" and len(criados) == 1
    app._editor_nomes = types.SimpleNamespace(win=_win_viva())   # janela ainda aberta
    gui.SeparadorApp.abrir_editor_nomes(app)          # 2a chamada só foca
    assert len(criados) == 1                          # não criou um 2º editor


def test_editores_nao_abrem_durante_operacao(monkeypatch):
    criados = []
    monkeypatch.setattr(gui, "EditorNomes", lambda app: criados.append("n"))
    monkeypatch.setattr(gui, "EditorSkusAnuncio", lambda app: criados.append("s"))
    app = _app(ocupado=True)
    gui.SeparadorApp.abrir_editor_nomes(app)
    gui.SeparadorApp.abrir_editor_skus(app)
    assert criados == []                              # nada abre durante coleta/impressão


def test_atribuir_sku_nao_muta_grupos_durante_operacao(monkeypatch):
    """_atribuir_sku volta cedo se ocupado — não abre o diálogo nem mexe nos
    grupos enquanto a thread de impressão os itera (5.5)."""
    chamou = {"dialogo": 0}
    monkeypatch.setattr(gui.simpledialog, "askstring",
                        lambda *a, **k: chamou.__setitem__("dialogo", 1) or "F1")
    app = _app(ocupado=True)
    gui.SeparadorApp._atribuir_sku(app, types.SimpleNamespace(nome="x", chave="c:"))
    assert chamou["dialogo"] == 0                     # nem abriu o diálogo
