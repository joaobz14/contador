"""Resumo por dia de despacho (contagem de pacotes por dia)."""


def _pronto(expected_date):
    return {"_envio": {"shipment_id": 1, "expected_date": expected_date, "logistica": "x"}}


def test_resumo_conta_e_ordena_por_dia(core):
    prontos = [
        _pronto("2026-06-19"), _pronto("2026-06-19"), _pronto("2026-06-19"),
        _pronto("2026-06-22"),
        _pronto("2026-06-20"), _pronto("2026-06-20"),
    ]
    assert core.resumo_por_dia(prontos) == [
        ("2026-06-19", 3),
        ("2026-06-20", 2),
        ("2026-06-22", 1),
    ]


def test_resumo_vazio(core):
    assert core.resumo_por_dia([]) == []


def test_resumo_sem_data(core):
    prontos = [{"_envio": {"shipment_id": 1, "expected_date": ""}}, {"_envio": {}}]
    # data vazia/ausente cai em "(sem data)"
    assert core.resumo_por_dia(prontos) == [("(sem data)", 2)]
