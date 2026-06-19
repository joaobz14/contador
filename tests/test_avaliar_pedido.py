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

    ped, sid, status = core._avaliar_pedido("tok", {"shipping": {"id": 99}})
    assert ped["_envio"]["expected_date"] == "2026-06-18"
    assert ped["_envio"]["logistica"] == "fulfillment"
    assert (sid, status) == (99, "ready_to_ship")
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
    ped, sid, status = core._avaliar_pedido("tok", {"shipping": {"id": 99}})
    assert ped["_envio"]["expected_date"] == "2026-06-18"
    assert ped["_envio"]["logistica"] == "self_service"
    assert chamou_sla["v"] is True


def test_avaliar_pedido_nao_ready_devolve_status(core, monkeypatch):
    monkeypatch.setattr(core, "buscar_envio", lambda token, sid: {"status": "shipped", "substatus": "x"})
    ped, sid, status = core._avaliar_pedido("tok", {"shipping": {"id": 5}})
    assert ped is None and sid == 5 and status == "shipped"


def test_avaliar_pedido_sem_shipment(core):
    assert core._avaliar_pedido("tok", {}) == (None, None, "")
