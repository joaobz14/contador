"""Datas no horario de Brasilia (filtro de despacho)."""
from datetime import datetime, timedelta, timezone

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
