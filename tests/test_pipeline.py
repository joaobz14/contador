"""Pipeline coletar_grupos: filtro do dia e repasse de progresso."""


def _prepara(core, monkeypatch, prontos):
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-06-18")
    monkeypatch.setattr(core, "buscar_pedidos", lambda token, seller: [{} for _ in prontos])
    chamou = {"progresso": False}

    def fake_filtrar(token, pedidos, progresso=None):
        if progresso:
            progresso(len(prontos), len(prontos))
            chamou["progresso"] = True
        return prontos

    monkeypatch.setattr(core, "filtrar_para_imprimir", fake_filtrar)
    monkeypatch.setattr(core, "extrair_itens", lambda token, alvo: [
        core.ItemPedido(order_id=i, shipment_id=p["_envio"]["shipment_id"],
                        chave="K", nome="N", quantidade=1)
        for i, p in enumerate(alvo)
    ])
    return chamou


def _prontos():
    return [
        {"_envio": {"shipment_id": 11, "expected_date": "2026-06-18"}},
        {"_envio": {"shipment_id": 22, "expected_date": "2000-01-01"}},
        {"_envio": {"shipment_id": 33, "expected_date": "2026-06-18"}},
    ]


def test_coletar_grupos_somente_hoje(core, monkeypatch):
    _prepara(core, monkeypatch, _prontos())
    col = core.coletar_grupos("tok", "seller", somente_hoje=True)
    assert len(col.prontos) == 3
    assert len(col.alvo) == 2
    assert {i.shipment_id for i in col.itens} == {11, 33}


def test_coletar_grupos_todos(core, monkeypatch):
    _prepara(core, monkeypatch, _prontos())
    col = core.coletar_grupos("tok", "seller", somente_hoje=False)
    assert len(col.alvo) == 3


def test_coletar_grupos_repassa_progresso(core, monkeypatch):
    chamou = _prepara(core, monkeypatch, _prontos())
    core.coletar_grupos("tok", "seller", progresso=lambda f, t: None)
    assert chamou["progresso"] is True
