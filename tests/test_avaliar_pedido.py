"""Avaliacao do envio: prazo do detalhe evita /sla; retorno (ped, sid, status)."""
import pytest


@pytest.mark.parametrize("env,esperado", [
    ({"shipping_option": {"estimated_handling_limit": {"date": "2026-06-18T00:00:00.000-03:00"}}},
     "2026-06-18T00:00:00.000-03:00"),
    ({"estimated_handling_limit": {"date": "2026-06-18T00:00:00.000-03:00"}},
     "2026-06-18T00:00:00.000-03:00"),
    ({"lead_time": {"estimated_handling_limit": {"date": "2026-06-18T00:00:00.000-03:00"}}},
     "2026-06-18T00:00:00.000-03:00"),
    ({"sla": {"expected_date": "2026-06-18T00:00:00.000-03:00"}},
     "2026-06-18T00:00:00.000-03:00"),
    ({}, ""),
    ({"shipping_option": {}}, ""),
])
def test_prazo_do_envio_varios_formatos(core, esperado, env):
    assert core._prazo_do_envio(env) == esperado


def test_avaliar_pedido_nao_chama_sla_quando_detalhe_tem_prazo(core, monkeypatch):
    env = {
        "status": "ready_to_ship", "substatus": core.SUBSTATUS_IMPRIMIR,
        "logistic_type": "fulfillment",
        "shipping_option": {"estimated_handling_limit": {"date": "2026-06-18T00:00:00.000-03:00"}},
    }
    monkeypatch.setattr(core, "buscar_envio", lambda token, sid: env)
    chamou_sla = {"v": False}
    monkeypatch.setattr(core, "_sla", lambda token, sid: chamou_sla.update(v=True) or {})

    ped, sid, status, verificado = core._avaliar_pedido("tok", {"shipping": {"id": 99}})
    assert ped["_envio"]["expected_date"] == "2026-06-18"
    assert ped["_envio"]["logistica"] == "fulfillment"
    assert (sid, status, verificado) == (99, "ready_to_ship", True)
    assert chamou_sla["v"] is False


def test_avaliar_pedido_cai_no_sla_quando_detalhe_nao_tem(core, monkeypatch):
    env = {"status": "ready_to_ship", "substatus": core.SUBSTATUS_IMPRIMIR,
           "logistic": {"type": "self_service"}}
    monkeypatch.setattr(core, "buscar_envio", lambda token, sid: env)
    chamou_sla = {"v": False}

    def fake_sla(token, sid):
        chamou_sla["v"] = True
        return {"expected_date": "2026-06-18T00:00:00.000-03:00"}

    monkeypatch.setattr(core, "_sla", fake_sla)
    ped, sid, status, _ = core._avaliar_pedido("tok", {"shipping": {"id": 99}})
    assert ped["_envio"]["expected_date"] == "2026-06-18"
    assert ped["_envio"]["logistica"] == "self_service"
    assert chamou_sla["v"] is True


def test_avaliar_pedido_nao_ready_devolve_status(core, monkeypatch):
    monkeypatch.setattr(core, "buscar_envio", lambda token, sid: {"status": "shipped", "substatus": "x"})
    ped, sid, status, verificado = core._avaliar_pedido("tok", {"shipping": {"id": 5}})
    assert ped is None and sid == 5 and status == "shipped"
    assert verificado is True, "sabemos que nao esta pronto — isso NAO e falha de API"


def test_avaliar_pedido_sem_shipment(core):
    assert core._avaliar_pedido("tok", {}) == (None, None, "", True)


def test_avaliar_pedido_api_falhou_nao_e_nao_pronto(core, monkeypatch):
    """INCIDENTE 2026-07-31: `buscar_envio` devolvia {} quando a API do ML
    recusava, e o {} percorria o fluxo igual a um envio que nao esta pronto —
    o pedido sumia do lote EM SILENCIO. O operador despachou 5 de 7 vendas do
    mesmo SKU e so descobriu conferindo o painel.

    Agora None e "nao sei": `verificado` vem False, e quem chama tem de avisar.
    """
    monkeypatch.setattr(core, "buscar_envio", lambda token, sid: None)

    ped, sid, status, verificado = core._avaliar_pedido("tok", {"shipping": {"id": 7}})

    assert ped is None, "sem resposta da API o pedido nao pode entrar no lote"
    assert sid == 7
    assert verificado is False, "'a API nao respondeu' nao pode virar 'nao esta pronto'"
