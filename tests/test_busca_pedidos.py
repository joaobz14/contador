"""Busca de pedidos: paginacao paralela cobre todas as paginas."""


def _fake_get_paginado(total):
    """Simula orders/search: 50 por pagina, ids sequenciais, paging.total fixo."""
    def fake(url, token, params=None, extra=None):
        off = params["offset"]
        ids = list(range(off, min(off + 50, total)))
        return {"results": [{"id": i} for i in ids], "paging": {"total": total}}
    return fake


def test_busca_todas_as_paginas(core, monkeypatch):
    monkeypatch.setattr(core, "_get", _fake_get_paginado(173))   # 4 paginas (50*3 + 23)
    pedidos = core.buscar_pedidos("tok", "seller")
    ids = sorted(p["id"] for p in pedidos)
    assert ids == list(range(173))                                # todos, sem buracos/duplicatas


def test_uma_pagina_so(core, monkeypatch):
    monkeypatch.setattr(core, "_get", _fake_get_paginado(30))
    assert len(core.buscar_pedidos("tok", "seller")) == 30


def test_respeita_max_pedidos(core, monkeypatch):
    monkeypatch.setattr(core, "MAX_PEDIDOS", 100)
    monkeypatch.setattr(core, "_get", _fake_get_paginado(500))
    assert len(core.buscar_pedidos("tok", "seller")) == 100


def test_dedup_de_paginacao(core, monkeypatch):
    """Pedido novo chegando no meio da paginacao (sort=date_desc) desloca os
    offsets e o mesmo id pode vir em 2 paginas — dedup por id evita o pedido
    (e o envio dele) contado em dobro."""
    def fake(url, token, params=None, extra=None):
        off = params["offset"]
        if off == 0:
            return {"results": [{"id": i} for i in range(50)], "paging": {"total": 60}}
        # pagina 2 repete os ids 45-49 (deslocados) + traz os 10 restantes
        return {"results": [{"id": i} for i in range(45, 60)], "paging": {"total": 60}}

    monkeypatch.setattr(core, "_get", fake)
    pedidos = core.buscar_pedidos("tok", "seller")
    ids = [p["id"] for p in pedidos]
    assert sorted(ids) == list(range(60))
    assert len(ids) == len(set(ids))                       # sem duplicatas


def test_janela_de_dias_customizada(core, monkeypatch):
    """dias= reduz a janela do date_created.from (o alerta do bot usa 5 dias em
    vez dos 30 do Atualizar). Sem dias=, mantem a DIAS_JANELA padrao."""
    from datetime import datetime, timedelta
    capturado = {}

    def fake(url, token, params=None, extra=None):
        capturado["desde"] = params["order.date_created.from"]
        return {"results": [], "paging": {"total": 0}}

    monkeypatch.setattr(core, "_get", fake)

    core.buscar_pedidos("tok", "seller", dias=5)
    esperado_5 = (datetime.now(core.TZ_BR) - timedelta(days=5)).strftime("%Y-%m-%d")
    assert capturado["desde"].startswith(esperado_5)

    core.buscar_pedidos("tok", "seller")
    esperado_30 = (datetime.now(core.TZ_BR) - timedelta(days=core.DIAS_JANELA)).strftime("%Y-%m-%d")
    assert capturado["desde"].startswith(esperado_30)
