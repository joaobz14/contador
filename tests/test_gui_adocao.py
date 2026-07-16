"""Adoção de anúncio sem SKU pela GUI (_aplicar_adocao/_aplicar_mapa_anuncios_local):
o botão inline aplica em memória no ML normal, mas RE-COLETA no modo Ambas —
os sub-grupos .por_conta não são reescritos em memória (fundir sem mesclar o
.por_conta esconderia envios do lote e a marcação cairia na chave antiga)."""
from __future__ import annotations

import pytest

# So roda onde o tkinter importa (o modulo da GUI importa tk no topo). Nao
# precisa de display: os metodos testados operam em dados, com Tk injetado fora.
try:
    import separador_gui as gui
except Exception as _e:  # noqa: BLE001 - ambiente sem tkinter
    pytest.skip(f"separador_gui nao importavel aqui: {_e}", allow_module_level=True)

import provedores as pv
import separador_etiquetas_ml as core


def _app(prov, grupos):
    """SeparadorApp sem Tk: so os atributos que os metodos de adocao usam."""
    app = gui.SeparadorApp.__new__(gui.SeparadorApp)
    app.prov = prov
    app.grupos = grupos
    app._render = lambda: None
    return app


def _g(chave, ids, qtd=1):
    return core.Grupo(chave=chave, nome=chave, quantidade=qtd,
                      shipment_ids=list(ids))


# ------------------------------------------------------------ roteamento
def test_adocao_ml_normal_aplica_em_memoria(monkeypatch):
    app = _app(pv.ProvedorML(), [])
    chamou = []
    monkeypatch.setattr(gui.SeparadorApp, "_aplicar_mapa_anuncios_local",
                        lambda self: chamou.append("local"))
    monkeypatch.setattr(gui.SeparadorApp, "atualizar",
                        lambda self: chamou.append("recoleta"))
    app._aplicar_adocao()
    assert chamou == ["local"]


def test_adocao_ambas_recoleta_em_vez_de_aplicar_local(monkeypatch):
    """Ambas NAO pode aplicar em memoria: os sub-grupos .por_conta manteriam a
    chave antiga (envios invisiveis no lote + estado gravado na chave errada)."""
    app = _app(pv.ProvedorMLAmbas(), [])
    chamou = []
    monkeypatch.setattr(gui.SeparadorApp, "_aplicar_mapa_anuncios_local",
                        lambda self: chamou.append("local"))
    monkeypatch.setattr(gui.SeparadorApp, "atualizar",
                        lambda self: chamou.append("recoleta"))
    app._aplicar_adocao()
    assert chamou == ["recoleta"]


# ------------------------------------- aplicacao em memoria (ML normal)
def test_aplicar_mapa_local_reescreve_e_funde(monkeypatch):
    """Anuncio adotado vira o SKU e FUNDE com o grupo existente de mesmo
    SKU+quantidade (ids unidos); a chave de estado passa a ser a do SKU."""
    ga = _g("MLB1:0", [1, 2])
    gb = _g("F1AP", [3])
    app = _app(pv.ProvedorML(), [gb, ga])
    monkeypatch.setattr(core, "carregar_skus_anuncio",
                        lambda: {"MLB1:0": "F1AP"})
    monkeypatch.setattr(core, "carregar_nomes", lambda: {})
    app._aplicar_mapa_anuncios_local()
    assert len(app.grupos) == 1
    g = app.grupos[0]
    assert g.chave == "F1AP" and sorted(g.shipment_ids) == [1, 2, 3]
    assert core._chave_estado(g).endswith("|F1AP|q1")   # estado na chave NOVA


def test_aplicar_mapa_local_nao_funde_quantidades_diferentes(monkeypatch):
    ga = _g("MLB1:0", [1], qtd=2)
    gb = _g("F1AP", [3], qtd=1)
    app = _app(pv.ProvedorML(), [gb, ga])
    monkeypatch.setattr(core, "carregar_skus_anuncio",
                        lambda: {"MLB1:0": "F1AP"})
    monkeypatch.setattr(core, "carregar_nomes", lambda: {})
    app._aplicar_mapa_anuncios_local()
    assert len(app.grupos) == 2                          # q1 e q2 separados


def test_aplicar_mapa_local_sem_mapa_nao_muda_nada(monkeypatch):
    ga = _g("MLB1:0", [1])
    app = _app(pv.ProvedorML(), [ga])
    monkeypatch.setattr(core, "carregar_skus_anuncio", lambda: {})
    monkeypatch.setattr(core, "carregar_nomes", lambda: {})
    app._aplicar_mapa_anuncios_local()
    assert app.grupos == [ga] and ga.chave == "MLB1:0"
