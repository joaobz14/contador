"""A tela nao pode falhar em silencio ao abrir.

O atalho sobe a GUI por `pythonw` — sem console. Ate 2026-08-05 o `main()`
eram quatro linhas sem `try/except` e sem log: se a montagem estourasse, o
duplo-clique nao produzia NADA (sem janela, sem mensagem, sem uma linha no
separador.log) e a investigacao comecava do zero.

E o mesmo defeito do incidente do bot_config.json, na tela que se abre todo
dia de manha: uma falha que so aparece onde ninguem olha e uma falha
silenciosa — e sob janela oculta, "imprimir o erro" nao conta como reportar.
"""
from __future__ import annotations

import pytest

try:
    import separador_gui as gui
except Exception as _e:  # noqa: BLE001 - ambiente sem tkinter
    pytest.skip(f"separador_gui nao importavel aqui: {_e}", allow_module_level=True)


class _RootFalso:
    def __init__(self):
        self.report_callback_exception = None
        self.rodou = False

    def mainloop(self):
        self.rodou = True


@pytest.fixture
def espiao(monkeypatch):
    """Troca log e messagebox por espioes — nenhum teste toca display ou disco."""
    registros: dict = {"excecao": [], "erro": [], "caixa": []}
    monkeypatch.setattr(gui.log, "exception",
                        lambda *a, **k: registros["excecao"].append(a))
    monkeypatch.setattr(gui.log, "error",
                        lambda *a, **k: registros["erro"].append(a))
    monkeypatch.setattr(gui.messagebox, "showerror",
                        lambda titulo, msg: registros["caixa"].append(msg))
    return registros


def test_falha_ao_montar_a_tela_deixa_rastro_no_log_e_avisa(monkeypatch, espiao):
    """O caso realista: a janela cria, mas a montagem do app estoura."""
    monkeypatch.setattr(gui.tk, "Tk", _RootFalso)

    def _explode(root):
        raise RuntimeError("faltou um widget")
    monkeypatch.setattr(gui, "SeparadorApp", _explode)

    with pytest.raises(SystemExit) as e:
        gui.main()

    assert e.value.code == 1, "sair com 0 faria o lancador achar que abriu"
    assert espiao["excecao"], "a falha TEM de ir para o separador.log"
    assert espiao["caixa"], "e o operador precisa ver alguma coisa na tela"
    assert "separador.log" in espiao["caixa"][0], \
        "a caixa precisa dizer ONDE esta o erro completo"


def test_falha_ao_criar_a_janela_tambem_e_reportada(monkeypatch, espiao):
    """Se nem o tk.Tk() sobe (display ausente, Tk quebrado), idem."""
    def _sem_tk():
        raise RuntimeError("no display name and no $DISPLAY")
    monkeypatch.setattr(gui.tk, "Tk", _sem_tk)

    with pytest.raises(SystemExit):
        gui.main()
    assert espiao["excecao"]


def test_caixa_de_dialogo_falhando_nao_engole_o_log(monkeypatch, espiao):
    """Sem display, o proprio messagebox estoura. O log ja foi gravado antes —
    e a saida continua sendo codigo 1, nao um traceback novo por cima."""
    monkeypatch.setattr(gui.tk, "Tk", _RootFalso)
    monkeypatch.setattr(gui, "SeparadorApp",
                        lambda root: (_ for _ in ()).throw(RuntimeError("x")))

    def _sem_caixa(titulo, msg):
        raise RuntimeError("sem display para a caixa")
    monkeypatch.setattr(gui.messagebox, "showerror", _sem_caixa)

    with pytest.raises(SystemExit) as e:
        gui.main()
    assert e.value.code == 1
    assert espiao["excecao"], "o log e a garantia; a caixa e o extra"


def test_abertura_normal_instala_o_registrador_de_erro_de_callback(monkeypatch, espiao):
    """O Tk engole excecao de callback e segue. Sob pythonw o traceback vai
    para um stderr que nao existe — entao a tela precisa registra-lo."""
    root = _RootFalso()
    monkeypatch.setattr(gui.tk, "Tk", lambda: root)
    monkeypatch.setattr(gui, "SeparadorApp", lambda r: None)

    gui.main()

    assert root.rodou, "abertura normal segue para o mainloop"
    assert root.report_callback_exception is gui._erro_de_callback


def test_erro_de_callback_vai_para_o_log_e_nunca_levanta(espiao):
    """Registrar e best-effort: chamado de dentro do Tk, levantar aqui
    quebraria a tela em vez de so anotar o problema."""
    try:
        raise ValueError("estourou no after()")
    except ValueError as e:
        gui._erro_de_callback(type(e), e, e.__traceback__)

    assert espiao["erro"], "o erro engolido pelo Tk tem de aparecer no log"
    assert "estourou no after()" in str(espiao["erro"][0])
