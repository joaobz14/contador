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
