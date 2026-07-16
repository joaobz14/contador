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


# ------------------------------------ releitura do estado antes de gerar (5.1)
import types  # noqa: E402


def _app_fake(prov, estado_memoria):
    """App minimo para exercitar _gerar_sem_marcar_thread sem Tk (liga o metodo
    nao-vinculado a um objeto com so o que ele toca)."""
    capturado = {}
    app = types.SimpleNamespace(
        estado=estado_memoria,
        prov=prov,
        modo_ident="nenhuma",
        _ctx_log=lambda: "ctx",
        # after chama o callback na hora (sem laco de eventos do Tk)
        root=types.SimpleNamespace(after=lambda _ms, fn: fn()),
        _confirmar_e_marcar=lambda impressos, falhas: capturado.update(
            impressos=impressos, falhas=falhas),
        _erro=lambda msg: capturado.update(erro=msg),
    )
    return app, capturado


def test_gerar_rele_estado_do_disco_antes_de_imprimir():
    """A geracao relê self.estado do provedor (disco) ANTES de calcular
    pendentes: uma marcacao gravada por fora (CLI/outra GUI) tem de valer, senao
    o pedido sai em dobro (auditoria 5.1)."""
    usado = {}

    class ProvFake:
        def carregar_estado(self):
            return {"do_disco": True}

        def imprimir_lotes(self, grupos, estado, *, modo):
            usado["estado"] = estado          # o estado usado para gerar/pendentes
            return [], []

    app, _cap = _app_fake(ProvFake(), {"em_memoria": True})
    gui.SeparadorApp._gerar_sem_marcar_thread(app, [_g("A")])
    assert app.estado == {"do_disco": True}   # substituiu o estado em memoria
    assert usado["estado"] == {"do_disco": True}   # gerou a partir do disco


def test_gerar_segue_com_estado_em_memoria_se_releitura_falha():
    """Falha ao reler o disco nao trava a impressao (degradacao suave): gera com
    o estado em memoria que a GUI ja tinha."""
    usado = {}

    class ProvFake:
        def carregar_estado(self):
            raise OSError("disco fora do ar")

        def imprimir_lotes(self, grupos, estado, *, modo):
            usado["estado"] = estado
            return [], []

    app, _cap = _app_fake(ProvFake(), {"em_memoria": True})
    gui.SeparadorApp._gerar_sem_marcar_thread(app, [_g("A")])
    assert usado["estado"] == {"em_memoria": True}   # caiu para o estado em memoria


# ---------------------------- trava de ponta a ponta na impressão (anti-duplicata)
class _FakeVar:
    def __init__(self, v):
        self._v = v

    def get(self):
        return self._v


def _app_lotes(monkeypatch, *, organizar=True, ocupado=False):
    """App mínimo para imprimir_lotes: threading.Thread é falso (só conta start)."""
    started = {"n": 0}

    class _FakeThread:
        def __init__(self, target=None, args=(), daemon=None):
            pass

        def start(self):
            started["n"] += 1

    monkeypatch.setattr(gui.threading, "Thread", _FakeThread)
    monkeypatch.setattr(gui.messagebox, "showinfo", lambda *a, **k: None)
    app = types.SimpleNamespace(
        ocupado=ocupado,
        _sel_vars=[(_g("A"), _FakeVar(True))],
        _confirmar_organizar=lambda sel: organizar,
        _gerar_sem_marcar_thread=lambda grupos: None,   # alvo da thread (fake não roda)
        prov=types.SimpleNamespace(suporta_identificacao=False),
        modo_ident="nenhuma")
    app._ocupar = lambda oc, msg="": setattr(app, "ocupado", oc)
    return app, started


def test_imprimir_lotes_trava_e_inicia(monkeypatch):
    """Fluxo normal: fica ocupado (trava) e inicia a thread de geração."""
    app, started = _app_lotes(monkeypatch, organizar=True)
    gui.SeparadorApp.imprimir_lotes(app)
    assert started["n"] == 1 and app.ocupado is True


def test_imprimir_lotes_recusa_reentrada_enquanto_ocupado(monkeypatch):
    """Um 2º clique enquanto ocupado (impressão/confirmação em curso) é recusado —
    é o que impedia o mesmo lote de sair em dobro."""
    app, started = _app_lotes(monkeypatch, organizar=True, ocupado=True)
    gui.SeparadorApp.imprimir_lotes(app)
    assert started["n"] == 0                          # não iniciou uma 2ª impressão


def test_imprimir_lotes_cancelar_organizar_libera_a_trava(monkeypatch):
    """Cancelar o 'Organizar envio' não pode deixar o app travado."""
    app, started = _app_lotes(monkeypatch, organizar=False)
    gui.SeparadorApp.imprimir_lotes(app)
    assert started["n"] == 0 and app.ocupado is False


def _app_confirmar(monkeypatch, *, resposta):
    for m in ("askyesno",):
        monkeypatch.setattr(gui.messagebox, m, lambda *a, **k: resposta)
    for m in ("showinfo", "showwarning", "showerror"):
        monkeypatch.setattr(gui.messagebox, m, lambda *a, **k: None)
    marcou = []
    app = types.SimpleNamespace(
        ocupado=True, estado={},
        prov=types.SimpleNamespace(
            marcar_impresso=lambda estado, g, pend: marcou.append(g.nome)),
        _ctx_log=lambda: "ctx")
    app._ocupar = lambda oc, msg="": setattr(app, "ocupado", oc)
    app._render = lambda: None
    app._confirmar_e_marcar_corpo = types.MethodType(
        gui.SeparadorApp._confirmar_e_marcar_corpo, app)
    return app, marcou


def test_confirmar_e_marcar_marca_e_libera(monkeypatch):
    app, marcou = _app_confirmar(monkeypatch, resposta=True)   # respondeu "Sim"
    gui.SeparadorApp._confirmar_e_marcar(app, [(_g("A"), ["S1"])], [])
    assert marcou == ["A"] and app.ocupado is False


def test_confirmar_e_marcar_nao_marca_mas_libera(monkeypatch):
    app, marcou = _app_confirmar(monkeypatch, resposta=False)  # respondeu "Não"
    gui.SeparadorApp._confirmar_e_marcar(app, [(_g("A"), ["S1"])], [])
    assert marcou == [] and app.ocupado is False               # a trava abre mesmo assim


def test_confirmar_e_marcar_libera_a_trava_mesmo_com_excecao(monkeypatch):
    """Se a confirmação estourar, o finally ainda libera — o app não pode ficar
    travado para sempre."""
    app, _marcou = _app_confirmar(monkeypatch, resposta=True)
    monkeypatch.setattr(gui.messagebox, "askyesno",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        gui.SeparadorApp._confirmar_e_marcar(app, [(_g("A"), ["S1"])], [])
    assert app.ocupado is False
