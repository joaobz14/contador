"""Cache de envios finalizados: pula os terminais e nao deixa de ver os prontos."""
from datetime import datetime, timedelta, timezone


def _hoje():
    return datetime.now(timezone(timedelta(hours=-3))).date().isoformat()


def _envio(status, substatus):
    return {"status": status, "substatus": substatus,
            "shipping_option": {"estimated_handling_limit": {"date": _hoje() + "T00:00:00.000-03:00"}}}


def test_limpar_envios_cache_remove_antigos(core):
    hoje = _hoje()
    velho = (datetime.now(timezone(timedelta(hours=-3))).date() - timedelta(days=40)).isoformat()
    out = core._limpar_envios_cache({"1": hoje, "2": velho}, dias=30)
    assert set(out) == {"1"}


def test_filtrar_pula_cacheados_e_cacheia_terminais(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_ENVIOS_CACHE", tmp_path / "cache.json")
    # 10 ja shipped (terminal), 20 ready_to_print, 30 ja no cache (deve pular)
    env_por_sid = {
        10: _envio("shipped", "delivered_to_carrier"),
        20: _envio("ready_to_ship", core.SUBSTATUS_IMPRIMIR),
    }
    chamados = []

    def fake_buscar(token, sid):
        chamados.append(sid)
        return env_por_sid[sid]

    monkeypatch.setattr(core, "buscar_envio", fake_buscar)
    # cache inicial ja contem o 30
    core._salvar_envios_cache({"30": _hoje()})

    pedidos = [{"shipping": {"id": s}} for s in (10, 20, 30)]
    prontos = core.filtrar_para_imprimir("tok", pedidos)

    # 30 foi pulado (nao chamou a API); 10 e 20 sim
    assert 30 not in chamados
    assert set(chamados) == {10, 20}
    # so o 20 (ready_to_print) entra
    assert [p["_envio"]["shipment_id"] for p in prontos] == [20]
    # o 10 (shipped) foi cacheado; o 20 NAO (continua pendente)
    cache = core._carregar_envios_cache()
    assert "10" in cache and "30" in cache and "20" not in cache


def test_filtrar_preenche_stats_diagnostico(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_ENVIOS_CACHE", tmp_path / "cache.json")
    env_por_sid = {
        10: _envio("shipped", "delivered_to_carrier"),
        20: _envio("ready_to_ship", core.SUBSTATUS_IMPRIMIR),
    }
    monkeypatch.setattr(core, "buscar_envio", lambda token, sid: env_por_sid[sid])
    core._salvar_envios_cache({"30": _hoje()})   # 30 ja no cache

    stats: dict = {}
    core.filtrar_para_imprimir("tok", [{"shipping": {"id": s}} for s in (10, 20, 30)],
                               stats=stats)
    # 10 e 20 re-consultados; 30 pulado pelo cache; so o 20 fica pronto.
    assert stats == {"checados": 2, "cache_hits": 1, "prontos": 1,
                     "nao_verificados": 0, "data_incerta": 0}


def test_filtrar_nao_cacheia_ready_to_print(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_ENVIOS_CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(core, "buscar_envio",
                        lambda token, sid: _envio("ready_to_ship", core.SUBSTATUS_IMPRIMIR))
    core.filtrar_para_imprimir("tok", [{"shipping": {"id": 7}}])
    assert core._carregar_envios_cache() == {}   # nada terminal -> cache vazio


def test_envio_que_a_api_recusou_nao_e_cacheado_nem_silenciado(core, tmp_path, monkeypatch):
    """O envio que a API nao respondeu (1) nao entra nos prontos, (2) NAO e
    cacheado como terminal — senao ficaria escondido para sempre — e (3) e
    CONTADO, para a tela poder avisar antes de imprimir (incidente 2026-07-31).
    """
    monkeypatch.setattr(core, "ARQUIVO_ENVIOS_CACHE", tmp_path / "cache.json")
    env_por_sid = {10: None,                                    # API recusou
                   20: _envio("ready_to_ship", core.SUBSTATUS_IMPRIMIR)}
    monkeypatch.setattr(core, "buscar_envio", lambda token, sid: env_por_sid[sid])

    stats: dict = {}
    prontos = core.filtrar_para_imprimir(
        "tok", [{"shipping": {"id": s}} for s in (10, 20)], stats=stats)

    assert len(prontos) == 1, "o nao-verificado nao pode entrar no lote"
    assert stats["nao_verificados"] == 1
    assert "10" not in core._carregar_envios_cache(), \
        "cachear como terminal esconderia o envio nas proximas buscas"


def test_falha_de_item_nao_e_gravada_no_cache(core, tmp_path, monkeypatch):
    """ACHADO da varredura de 2026-08-03: uma falha TRANSITORIA do /items virava
    PERMANENTE. `_detalhe_item` devolvia entrada vazia, `buscar_detalhes` a
    gravava, e como so busca o que nao esta em cache, o item ficava sem GTIN e
    sem seller_sku para sempre — mudando a chave do grupo (`{item_id}:{var}` em
    vez de `GTIN:...`) e derrubando a adocao feita em `skus_por_anuncio.json`.
    So limpando o cache na mao para consertar.
    """
    import requests

    monkeypatch.setattr(core, "ARQUIVO_CACHE", tmp_path / "itens.json")
    monkeypatch.setattr(core, "_get", lambda *a, **k: (_ for _ in ()).throw(
        requests.HTTPError("500 do ML")))

    cache: dict = {}
    core.buscar_detalhes("tok", {"MLB1"}, cache)
    assert cache == {}, "falha nao pode virar entrada de cache"
    assert core.carregar_cache() == {}

    # A API voltou: a proxima busca TEM de tentar de novo.
    monkeypatch.setattr(core, "_get", lambda *a, **k: {
        "title": "Robust 2L", "seller_custom_field": "A16",
        "variations": [{"id": 9, "attributes": [{"id": "GTIN", "value_name": "789X"}]}]})

    cache = core.carregar_cache()
    core.buscar_detalhes("tok", {"MLB1"}, cache)

    assert cache["MLB1"]["seller_sku"] == "A16"
    assert cache["MLB1"]["variations"] == {"9": "789X"}
