"""Testes do coletor deterministico do Product Ads (ads-monitor/coletar.py).

Importa por caminho (a pasta tem hifen, nao e pacote Python) — mesmo padrao
de tests/test_validar_obsidian.py.
"""
import datetime
import importlib.util
from pathlib import Path

from conftest import FakeResp

_SPEC = importlib.util.spec_from_file_location(
    "ads_monitor_coletar",
    Path(__file__).resolve().parent.parent / "ads-monitor" / "coletar.py")
cm = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cm)

DIA = datetime.date(2026, 7, 22)


def _sequencia(monkeypatch, respostas):
    estado = {"n": 0}

    def fake_get(url, headers=None, timeout=None):
        r = respostas[estado["n"]]
        estado["n"] += 1
        return r

    monkeypatch.setattr(cm.requests, "get", fake_get)
    return estado


# --------------------------------------------------------------- advertiser
def test_buscar_advertiser_ok(monkeypatch):
    _sequencia(monkeypatch, [FakeResp(200, json_data={
        "advertisers": [{"advertiser_id": 999, "site_id": "MLB"}]})])
    assert cm.buscar_advertiser("tok") == ("999", "MLB")


def test_buscar_advertiser_404_devolve_none(monkeypatch):
    _sequencia(monkeypatch, [FakeResp(404, json_data={"error": "not_found"})])
    assert cm.buscar_advertiser("tok") is None


def test_buscar_advertiser_lista_vazia_devolve_none(monkeypatch):
    _sequencia(monkeypatch, [FakeResp(200, json_data={"advertisers": []})])
    assert cm.buscar_advertiser("tok") is None


# --------------------------------------------------------------- campanhas
def test_buscar_campanhas_do_dia_ok(monkeypatch):
    payload = {"results": [{"id": 1, "name": "A", "status": "active",
                            "metrics": {"clicks": 10}}]}
    _sequencia(monkeypatch, [FakeResp(200, json_data=payload)])
    camps = cm.buscar_campanhas_do_dia("tok", "MLB", "999", DIA)
    assert len(camps) == 1 and camps[0]["id"] == 1


def test_buscar_campanhas_do_dia_falha_devolve_lista_vazia(monkeypatch):
    _sequencia(monkeypatch, [FakeResp(500)])
    assert cm.buscar_campanhas_do_dia("tok", "MLB", "999", DIA) == []


# ---------------------------------------------------------------- detalhe
def test_buscar_detalhe_campanha_ok(monkeypatch):
    payload = {"metrics": {"lost_impression_share_by_budget": 0.42}}
    _sequencia(monkeypatch, [FakeResp(200, json_data=payload)])
    m = cm.buscar_detalhe_campanha("tok", "MLB", "1", DIA)
    assert m["lost_impression_share_by_budget"] == 0.42


def test_buscar_detalhe_campanha_falha_devolve_vazio(monkeypatch):
    _sequencia(monkeypatch, [FakeResp(404)])
    assert cm.buscar_detalhe_campanha("tok", "MLB", "1", DIA) == {}


# --------------------------------------------------------------- storage
def test_salvar_campanha_e_idempotente(tmp_path):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    campanha = {"id": 1, "name": "A", "status": "active", "budget": 200.0,
               "metrics": {"clicks": 10, "roas": 5.0}}
    cm.salvar_campanha(conn, dia=DIA, conta="cozilatti", site_id="MLB",
                       advertiser_id="999", campanha=campanha, detalhe={})
    conn.commit()
    linhas = conn.execute("SELECT clicks, roas FROM campanhas_diarias").fetchall()
    assert linhas == [(10, 5.0)]

    # regravar o MESMO dia/conta/campanha -> substitui, nao duplica
    campanha2 = dict(campanha, metrics={"clicks": 20, "roas": 6.0})
    cm.salvar_campanha(conn, dia=DIA, conta="cozilatti", site_id="MLB",
                       advertiser_id="999", campanha=campanha2, detalhe={})
    conn.commit()
    linhas = conn.execute("SELECT clicks, roas FROM campanhas_diarias").fetchall()
    assert linhas == [(20, 6.0)]
    conn.close()


def test_salvar_campanha_chaves_diferentes_nao_colidem(tmp_path):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    for conta in ("cozilatti", "gastromaq"):
        cm.salvar_campanha(conn, dia=DIA, conta=conta, site_id="MLB",
                           advertiser_id="999", campanha={"id": 1, "metrics": {}},
                           detalhe={})
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM campanhas_diarias").fetchone()[0]
    assert n == 2  # mesma campaign_id, conta diferente -> nao colide
    conn.close()


def test_conectar_db_cria_schema(tmp_path):
    caminho = tmp_path / "novo.sqlite3"
    assert not caminho.exists()
    conn = cm.conectar_db(caminho)
    assert caminho.exists()
    # tabela existe e aceita select vazio sem erro
    assert conn.execute("SELECT COUNT(*) FROM campanhas_diarias").fetchone()[0] == 0
    conn.close()


# ----------------------------------------------------------- orquestracao
def test_coletar_conta_fim_a_fim(monkeypatch, tmp_path):
    monkeypatch.setattr(cm.core, "definir_conta", lambda nome: None)
    monkeypatch.setattr(cm.core, "carregar_credenciais", lambda: {"seller_id": "1"})
    monkeypatch.setattr(cm.core, "obter_token", lambda cred: "tok")

    respostas = [
        FakeResp(200, json_data={"advertisers": [{"advertiser_id": 999, "site_id": "MLB"}]}),
        FakeResp(200, json_data={"results": [
            {"id": 1, "name": "A", "status": "active", "metrics": {"clicks": 5}},
            {"id": 2, "name": "B", "status": "paused", "metrics": {"clicks": 1}},
        ]}),
        FakeResp(200, json_data={"metrics": {"lost_impression_share_by_budget": 0.1}}),
        FakeResp(200, json_data={"metrics": {"lost_impression_share_by_budget": 0.2}}),
    ]
    _sequencia(monkeypatch, respostas)

    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    r = cm.coletar_conta(conn, "cozilatti", DIA)
    assert r == {"conta": "cozilatti", "ok": True, "campanhas": 2, "erro": None}
    linhas = conn.execute(
        "SELECT campaign_id, lost_impression_share_by_budget FROM campanhas_diarias "
        "ORDER BY campaign_id").fetchall()
    assert linhas == [("1", 0.1), ("2", 0.2)]
    conn.close()


def test_coletar_conta_sem_advertiser_isola_falha(monkeypatch, tmp_path):
    monkeypatch.setattr(cm.core, "definir_conta", lambda nome: None)
    monkeypatch.setattr(cm.core, "carregar_credenciais", lambda: {"seller_id": "1"})
    monkeypatch.setattr(cm.core, "obter_token", lambda cred: "tok")
    _sequencia(monkeypatch, [FakeResp(404, json_data={"error": "not_found"})])

    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    r = cm.coletar_conta(conn, "sem-ads", DIA)
    assert r["ok"] is False
    assert "advertiser" in r["erro"]
    conn.close()


def test_coletar_conta_falha_de_auth_nao_levanta(monkeypatch, tmp_path):
    def _explode(nome):
        raise RuntimeError("token vencido")
    monkeypatch.setattr(cm.core, "definir_conta", _explode)

    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    r = cm.coletar_conta(conn, "cozilatti", DIA)  # nao deve levantar
    assert r["ok"] is False
    assert "autenticacao" in r["erro"]
    conn.close()


# ------------------------------------------------------------------- CLI
def test_main_sem_contas_configuradas(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cm.core, "listar_contas", lambda: [])
    rc = cm.main(["--db", str(tmp_path / "t.sqlite3")])
    assert rc == 1
    assert "Nenhuma conta" in capsys.readouterr().out


def test_main_dia_default_e_ontem(monkeypatch, tmp_path):
    capturado = {}

    def fake_coletar_conta(conn, conta, dia):
        capturado["dia"] = dia
        return {"conta": conta, "ok": True, "campanhas": 0, "erro": None}

    monkeypatch.setattr(cm.core, "listar_contas", lambda: ["cozilatti"])
    monkeypatch.setattr(cm, "coletar_conta", fake_coletar_conta)
    rc = cm.main(["--db", str(tmp_path / "t.sqlite3")])
    assert rc == 0
    esperado = datetime.datetime.now(cm.core.TZ_BR).date() - datetime.timedelta(days=1)
    assert capturado["dia"] == esperado
