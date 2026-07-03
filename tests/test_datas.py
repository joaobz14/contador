"""Datas no horario de Brasilia (filtro de despacho)."""
from datetime import date, datetime, timedelta, timezone

import pytest


def test_hoje_br_usa_offset_menos_3(core):
    esperado = datetime.now(timezone(timedelta(hours=-3))).date().isoformat()
    assert core._hoje_br() == esperado


@pytest.mark.parametrize("raw,esperado", [
    ("2026-06-18T00:00:00.000-03:00", "2026-06-18"),  # formato do ML (meia-noite BR)
    ("2026-06-18T00:00:00.000-04:00", "2026-06-18"),  # outro offset, mesmo dia
    ("2026-06-18T03:00:00.000Z", "2026-06-18"),       # 03h UTC == 00h BR
    ("2026-06-18T00:00:00.000Z", "2026-06-17"),       # 00h UTC == 21h do dia anterior BR
    ("2026-06-18", "2026-06-18"),                     # sem hora/offset -> recorte
    ("", ""),
    ("data-invalida", "data-inval"),                  # fallback [:10]
])
def test_data_despacho_converte_para_brasilia(core, raw, esperado):
    assert core._data_despacho(raw) == esperado


# --------------------------------------------------- seletor de dias uteis (seg-sex)
def test_proximos_dias_uteis_numa_sexta_pula_o_fim_de_semana(core):
    sexta = date(2026, 7, 3)                    # 2026-07-03 e uma sexta
    dias = core.proximos_dias_uteis(5, base=sexta)
    # sexta(hoje) e ja a proxima semana: seg, ter, qua, qui (sab/dom fora)
    assert dias == ["2026-07-03", "2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09"]


def test_proximos_dias_uteis_comeca_no_proximo_util_no_sabado(core):
    sabado = date(2026, 7, 4)
    dias = core.proximos_dias_uteis(5, base=sabado)
    assert dias[0] == "2026-07-06"              # pula sab/dom -> comeca na segunda
    assert all(date.fromisoformat(d).weekday() < 5 for d in dias)


def test_proximos_dias_uteis_dia_comum(core):
    terca = date(2026, 6, 30)
    dias = core.proximos_dias_uteis(5, base=terca)
    assert dias == ["2026-06-30", "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"]


def test_rotulo_dia_formata_curto(core):
    assert core.rotulo_dia("2026-07-06") == "Seg 06/07"
    assert core.rotulo_dia("2026-07-03") == "Sex 03/07"
