"""Estado de impressao por shipment_ids e limpeza por idade."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from conftest import make_grupo


def _d(delta):
    hoje = datetime.now(timezone(timedelta(hours=-3))).date()
    return (hoje - timedelta(days=delta)).isoformat()


# --------------------------------------------------------------- ciclo de vida
def test_grupo_novo_fica_pendente(core):
    g = make_grupo(core, [10, 20])
    assert core.status_grupo({}, g) == "pendente"
    assert core.envios_pendentes({}, g) == [10, 20]


def test_marcar_impresso_acumula_e_deduplica(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_ESTADO", tmp_path / "estado.json")
    g = make_grupo(core, [5, 6])
    estado = {}
    core.marcar_impresso(estado, g, [5])
    core.marcar_impresso(estado, g, [5, 6])
    assert estado[core._chave_estado(g)] == [5, 6]
    assert core.status_grupo(estado, g) == "impresso"


def test_envio_novo_reabre_como_parcial(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_ESTADO", tmp_path / "estado.json")
    estado = {}
    core.marcar_impresso(estado, make_grupo(core, [10, 20]))
    g2 = make_grupo(core, [10, 20, 30])  # chegou o envio 30
    assert core.status_grupo(estado, g2) == "parcial"
    assert core.envios_pendentes(estado, g2) == [30]


def test_compatibilidade_formato_antigo_string(core):
    g = make_grupo(core, [1, 2])
    estado = {core._chave_estado(g): "impresso"}
    assert core.status_grupo(estado, g) == "impresso"
    assert core.envios_pendentes(estado, g) == []


def test_status_usa_o_dia_de_despacho_do_grupo(core):
    # Datas fixas no passado para nunca colidirem com "hoje".
    g = make_grupo(core, [10, 20])
    g.dia = "2000-01-02"
    # chave do mesmo dia marca como impresso
    assert core.status_grupo({"2000-01-02|K|q1": [10, 20]}, g) == "impresso"
    # estado de OUTRO dia nao deve influenciar a visao do dia do grupo
    assert core.status_grupo({"2000-01-01|K|q1": [10, 20]}, g) == "pendente"


# ------------------------------------------------------------ imprimir_pendentes
def test_imprimir_pendentes_baixa_somente_os_novos(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_ESTADO", tmp_path / "estado.json")
    monkeypatch.setattr(core, "gerar_zip_etiquetas", lambda g, zpl: tmp_path / "fake.zip")
    baixados = {}
    monkeypatch.setattr(core, "baixar_zpl",
                        lambda token, ids: baixados.update(ids=list(ids)) or "^XA ^XZ")

    estado = {}
    core.imprimir_pendentes("tok", make_grupo(core, [10, 20]), estado)
    assert baixados["ids"] == [10, 20]

    baixados.clear()
    impressos = core.imprimir_pendentes("tok", make_grupo(core, [10, 20, 30]), estado)
    assert impressos == [30]
    assert baixados["ids"] == [30]  # nao reimprime 10 e 20


def test_imprimir_pendentes_sem_nada_nao_baixa(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_ESTADO", tmp_path / "estado.json")
    chamou = {"v": False}
    monkeypatch.setattr(core, "baixar_zpl", lambda *a: chamou.update(v=True) or "^XA")
    g = make_grupo(core, [1])
    estado = {core._chave_estado(g): [1]}  # ja impresso
    assert core.imprimir_pendentes("tok", g, estado) == []
    assert chamou["v"] is False


def test_imprimir_pendentes_falha_mantem_pendente(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_ESTADO", tmp_path / "estado.json")

    def baixar_falha(token, ids):
        raise core.SeparadorError("falha")

    monkeypatch.setattr(core, "baixar_zpl", baixar_falha)
    estado = {}
    g = make_grupo(core, [99])
    with pytest.raises(core.SeparadorError):
        core.imprimir_pendentes("tok", g, estado)
    assert core.status_grupo(estado, g) == "pendente"


# --------------------------------------------------------------- limpeza por idade
def test_limpar_estado_antigo(core):
    estado = {
        f"{_d(0)}|A|q1": [1],
        f"{_d(7)}|B|q1": [2],     # no limite -> mantem
        f"{_d(8)}|C|q1": [3],     # antigo -> remove
        "A11|q1": "impresso",     # legado sem data -> remove
    }
    limpo = core._limpar_estado_antigo(estado, dias=7)
    assert set(limpo) == {f"{_d(0)}|A|q1", f"{_d(7)}|B|q1"}


def test_carregar_estado_poda_e_persiste(core, tmp_path, monkeypatch):
    arq = tmp_path / "estado.json"
    monkeypatch.setattr(core, "ARQUIVO_ESTADO", arq)
    arq.write_text(json.dumps({f"{_d(0)}|A|q1": [1], f"{_d(30)}|B|q1": [2]}), encoding="utf-8")

    out = core.carregar_estado()
    assert set(out) == {f"{_d(0)}|A|q1"}
    # regravou sem a entrada antiga
    assert set(json.loads(arq.read_text(encoding="utf-8"))) == {f"{_d(0)}|A|q1"}
