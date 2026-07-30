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


@pytest.fixture(autouse=True)
def _saida_isolada(monkeypatch, tmp_path):
    """A geracao consulta a pasta de saida (checagem do monitor da Zebra) —
    nenhum teste pode olhar a Downloads real da maquina."""
    monkeypatch.setattr(core, "PASTA_DOWNLOADS", tmp_path)
    monkeypatch.setattr(core, "ARQUIVO_LOG_MONITOR", tmp_path / "zebra_usb_log.txt")


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
        _confirmar_e_marcar=lambda impressos, falhas, sinal: capturado.update(
            impressos=impressos, falhas=falhas, sinal=sinal),
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


# ------------------------- sinal do monitor da Zebra --------------------------

def _prov_que_gera(pasta, nome="etiqueta de envio - LOTES x1 - 143012.zip"):
    class ProvFake:
        def carregar_estado(self):
            return {}

        def imprimir_lotes(self, grupos, estado, *, modo):
            (pasta / nome).write_bytes(b"PK\x03\x04")   # o ZIP que o monitor pegaria
            return [(grupos[0], ["S1"])], []

    return ProvFake()


def test_sinal_do_monitor_chega_na_confirmacao(tmp_path):
    """O arquivo continua na pasta e o log EXISTE sem avançar: o monitor não deu
    sinal — e a confirmação precisa dizer isso ao operador."""
    import os
    import time as _t

    core.ARQUIVO_LOG_MONITOR.write_text("[08:00:00] sessao anterior", encoding="utf-8")
    velho = _t.time() - 3600
    os.utime(core.ARQUIVO_LOG_MONITOR, (velho, velho))

    app, cap = _app_fake(_prov_que_gera(tmp_path), {})
    gui.SeparadorApp._gerar_sem_marcar_thread(app, [_g("A")])
    assert cap["sinal"] == "sem_sinal"


def test_sem_log_do_monitor_a_tela_fica_calada(tmp_path):
    """Espelha o incidente de 2026-07-30 no nível da tela: sem log para
    consultar, a confirmação não pode acusar o monitor de estar parado."""
    app, cap = _app_fake(_prov_que_gera(tmp_path), {})
    gui.SeparadorApp._gerar_sem_marcar_thread(app, [_g("A")])
    assert cap["sinal"] == "sem_saida"
    assert core.texto_sinal_monitor(cap["sinal"]) == "", "não pode aparecer aviso"


def test_monitor_rapido_demais_ainda_da_sinal_de_vida(tmp_path):
    """CORRIDA REAL: o monitor varre a cada 1s e pode consumir o ZIP ANTES de a
    tela tirar o segundo instantâneo — aí a diferença vem vazia, igualzinho a
    "nada foi gerado".

    O log avançando resolve: prova que ele está vivo. O veredito é "imprimindo",
    NÃO "impresso" — sem ter visto o nosso arquivo sumir, afirmar que ele saiu
    seria justamente o erro que esta tela não pode cometer.
    """
    prov = _prov_que_gera(tmp_path)
    original = prov.imprimir_lotes

    def _gerar_e_o_monitor_leva_na_hora(grupos, estado, *, modo):
        r = original(grupos, estado, modo=modo)
        for p in tmp_path.glob("*.zip"):
            p.unlink()
        core.ARQUIVO_LOG_MONITOR.write_text("[14:30:12] imprimindo", encoding="utf-8")
        return r

    prov.imprimir_lotes = _gerar_e_o_monitor_leva_na_hora
    app, cap = _app_fake(prov, {})
    gui.SeparadorApp._gerar_sem_marcar_thread(app, [_g("A")])
    assert cap["sinal"] == "imprimindo"


def test_zip_que_ja_estava_na_pasta_nao_e_contado(tmp_path, monkeypatch):
    """Só o que aparece DEPOIS de gerar é nosso.

    Cenário: um ZIP antigo está encalhado na Downloads (lote que o monitor nunca
    consumiu) e o nosso é impresso normalmente. Se o antigo entrasse na conta,
    ele nunca sumiria e o veredito seria "sem_sinal" — um alarme falso toda vez
    que sobrasse lixo na pasta.
    """
    encalhado = tmp_path / "etiqueta de envio - de ontem - 090000.zip"
    encalhado.write_bytes(b"PK\x03\x04")

    # O monitor consome o NOSSO durante a espera (depois do instantâneo).
    def _monitor_consome(_s):
        (tmp_path / "etiqueta de envio - LOTES x1 - 143012.zip").unlink(missing_ok=True)

    monkeypatch.setattr(core.time, "sleep", _monitor_consome)

    app, cap = _app_fake(_prov_que_gera(tmp_path), {})
    gui.SeparadorApp._gerar_sem_marcar_thread(app, [_g("A")])

    assert cap["sinal"] == "impresso", "o ZIP encalhado de ontem contaminou o veredito"
    assert encalhado.exists()


def test_falha_na_checagem_do_monitor_nao_impede_a_confirmacao(tmp_path, monkeypatch):
    """A checagem e um aviso a mais. Se ela quebrar, a impressao segue e o
    operador confirma como sempre — nunca o contrario."""
    monkeypatch.setattr(core, "aguardar_impressao",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("pasta sumiu")))
    app, cap = _app_fake(_prov_que_gera(tmp_path), {})
    gui.SeparadorApp._gerar_sem_marcar_thread(app, [_g("A")])
    assert cap["impressos"], "a confirmacao tem de acontecer mesmo assim"
    assert cap["sinal"] == "sem_saida"


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
