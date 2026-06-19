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


def test_filtrar_nao_cacheia_ready_to_print(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_ENVIOS_CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(core, "buscar_envio",
                        lambda token, sid: _envio("ready_to_ship", core.SUBSTATUS_IMPRIMIR))
    core.filtrar_para_imprimir("tok", [{"shipping": {"id": 7}}])
    assert core._carregar_envios_cache() == {}   # nada terminal -> cache vazio
