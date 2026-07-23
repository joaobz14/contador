"""Testes do motor de recomendacao (ads-monitor/recomendar.py).

Importa por caminho (a pasta tem hifen, nao e pacote Python) — mesmo padrao
de tests/test_ads_monitor_coletar.py.
"""
import datetime
import importlib.util
import sys
from pathlib import Path

_SPEC_COLETAR = importlib.util.spec_from_file_location(
    "ads_monitor_coletar",
    Path(__file__).resolve().parent.parent / "ads-monitor" / "coletar.py")
cm = importlib.util.module_from_spec(_SPEC_COLETAR)
_SPEC_COLETAR.loader.exec_module(cm)

# registrado em sys.modules ANTES do exec: o modulo usa @dataclass, que
# resolve cls.__module__ via sys.modules -- sem isso, dataclasses.dataclass
# quebra com "NoneType has no attribute __dict__".
_SPEC_REC = importlib.util.spec_from_file_location(
    "ads_monitor_recomendar",
    Path(__file__).resolve().parent.parent / "ads-monitor" / "recomendar.py")
rm = importlib.util.module_from_spec(_SPEC_REC)
sys.modules["ads_monitor_recomendar"] = rm
_SPEC_REC.loader.exec_module(rm)


def _campanha(dia, conta, cid, nome, *, clicks=20, cost=100.0, roas=10.0,
             roas_target=10.0, total_amount=1000.0, perdido_orcamento=0.02,
             perdido_ranking=0.02, status="active"):
    return dict(
        dia=dia, conta=conta, site_id="MLB", advertiser_id="1",
        campanha={"id": cid, "name": nome, "status": status, "budget": 100,
                 "roas_target": roas_target,
                 "metrics": {"clicks": clicks, "cost": cost, "roas": roas,
                            "total_amount": total_amount}},
        detalhe={"lost_impression_share_by_budget": perdido_orcamento,
                "lost_impression_share_by_ad_rank": perdido_ranking},
    )


def _popular(conn, dias, conta, cid, nome, **kw):
    for d in dias:
        cm.salvar_campanha(conn, **_campanha(d, conta, cid, nome, **kw))
    conn.commit()


def _janela(n=7, fim=datetime.date(2026, 7, 22)):
    return [fim - datetime.timedelta(days=i) for i in range(n)][::-1]


# ------------------------------------------------------------ avaliar_campanha (puro)
def test_avaliar_campanha_sem_dado_suficiente_nao_recomenda():
    ag = {"campaign_id": 1, "campaign_name": "X", "dias": 1, "clicks_total": 5,
         "media_perdido_orcamento": 0.9, "media_perdido_ranking": 0.9,
         "media_roas": 1.0, "media_roas_target": 10.0}
    assert rm.avaliar_campanha("cozilatti", ag) == []


def test_avaliar_campanha_saudavel_nao_recomenda():
    ag = {"campaign_id": 1, "campaign_name": "X", "dias": 7, "clicks_total": 200,
         "media_perdido_orcamento": 0.02, "media_perdido_ranking": 0.02,
         "media_roas": 15.0, "media_roas_target": 10.0}
    assert rm.avaliar_campanha("cozilatti", ag) == []


def test_avaliar_campanha_orcamento_insuficiente():
    ag = {"campaign_id": 1, "campaign_name": "X", "dias": 7, "clicks_total": 200,
         "media_perdido_orcamento": 0.40, "media_perdido_ranking": 0.02,
         "media_roas": 15.0, "media_roas_target": 10.0}
    recs = rm.avaliar_campanha("cozilatti", ag)
    assert len(recs) == 1
    r = recs[0]
    assert r.tipo == "orcamento_insuficiente"
    assert r.condicionada_margem is True
    assert r.urgencia == "alta"  # 0.40 >= LIMIAR_URGENCIA_ALTA (0.30)


def test_avaliar_campanha_ranking_baixo():
    ag = {"campaign_id": 1, "campaign_name": "X", "dias": 7, "clicks_total": 200,
         "media_perdido_orcamento": 0.02, "media_perdido_ranking": 0.20,
         "media_roas": 15.0, "media_roas_target": 10.0}
    recs = rm.avaliar_campanha("cozilatti", ag)
    assert len(recs) == 1
    assert recs[0].tipo == "ranking_baixo"
    assert recs[0].condicionada_margem is True
    assert recs[0].urgencia == "media"  # 0.20 < LIMIAR_URGENCIA_ALTA


def test_avaliar_campanha_roas_abaixo_do_alvo_nao_e_condicionada_margem():
    ag = {"campaign_id": 1, "campaign_name": "X", "dias": 7, "clicks_total": 200,
         "media_perdido_orcamento": 0.02, "media_perdido_ranking": 0.02,
         "media_roas": 3.0, "media_roas_target": 10.0}
    recs = rm.avaliar_campanha("cozilatti", ag)
    assert len(recs) == 1
    assert recs[0].tipo == "roas_abaixo_do_alvo"
    assert recs[0].condicionada_margem is False


def test_avaliar_campanha_varios_sinais_juntos():
    ag = {"campaign_id": 1, "campaign_name": "X", "dias": 7, "clicks_total": 200,
         "media_perdido_orcamento": 0.40, "media_perdido_ranking": 0.20,
         "media_roas": 3.0, "media_roas_target": 10.0}
    recs = rm.avaliar_campanha("cozilatti", ag)
    tipos = {r.tipo for r in recs}
    assert tipos == {"orcamento_insuficiente", "ranking_baixo", "roas_abaixo_do_alvo"}


def test_avaliar_campanha_sem_roas_target_nao_quebra():
    ag = {"campaign_id": 1, "campaign_name": "X", "dias": 7, "clicks_total": 200,
         "media_perdido_orcamento": 0.02, "media_perdido_ranking": 0.02,
         "media_roas": 3.0, "media_roas_target": None}
    assert rm.avaliar_campanha("cozilatti", ag) == []


# --------------------------------------------------------------- fim-a-fim (sqlite)
def test_gerar_recomendacoes_fim_a_fim(tmp_path):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    dias = _janela(7)
    _popular(conn, dias, "cozilatti", 1, "Orcamento Baixo", perdido_orcamento=0.40)
    _popular(conn, dias, "cozilatti", 2, "ROAS Ruim", roas=3.0, roas_target=10.0)
    _popular(conn, dias, "cozilatti", 3, "Saudavel", roas=15.0)
    recs = rm.gerar_recomendacoes(conn, "cozilatti", dias[-1], janela_dias=7)
    tipos_por_campanha = {r.campaign_id: r.tipo for r in recs}
    assert tipos_por_campanha == {"1": "orcamento_insuficiente", "2": "roas_abaixo_do_alvo"}
    conn.close()


def test_gerar_recomendacoes_campanha_pausada_e_ignorada(tmp_path):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    dias = _janela(7)
    _popular(conn, dias, "cozilatti", 1, "Pausada", status="paused",
            perdido_orcamento=0.40)
    recs = rm.gerar_recomendacoes(conn, "cozilatti", dias[-1], janela_dias=7)
    assert recs == []
    conn.close()


def test_gerar_recomendacoes_poucos_dias_ainda_nao_recomenda(tmp_path):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    dias = _janela(2)  # < MIN_DIAS
    _popular(conn, dias, "cozilatti", 1, "Nova", perdido_orcamento=0.40)
    recs = rm.gerar_recomendacoes(conn, "cozilatti", dias[-1], janela_dias=7)
    assert recs == []
    conn.close()


def test_formatar_relatorio_vazio_explica_o_motivo():
    texto = rm.formatar_relatorio([])
    assert "insuficientes" in texto or "Nenhuma" in texto


def test_formatar_relatorio_marca_condicionada_margem(tmp_path):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    dias = _janela(7)
    _popular(conn, dias, "cozilatti", 1, "Orcamento Baixo", perdido_orcamento=0.40)
    recs = rm.gerar_recomendacoes(conn, "cozilatti", dias[-1], janela_dias=7)
    texto = rm.formatar_relatorio(recs)
    assert "condicionada a validacao da margem" in texto
    conn.close()


# ------------------------------------------------------------------------- CLI
def test_main_sem_historico(tmp_path, capsys):
    conn = cm.conectar_db(tmp_path / "vazio.sqlite3")
    conn.close()
    rc = rm.main(["--db", str(tmp_path / "vazio.sqlite3")])
    assert rc == 1
    assert "Nenhum historico" in capsys.readouterr().out


def test_main_roda_para_todas_as_contas(tmp_path, capsys):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    dias = _janela(7)
    _popular(conn, dias, "cozilatti", 1, "Orcamento Baixo", perdido_orcamento=0.40)
    _popular(conn, dias, "gastromaq", 2, "Saudavel", roas=15.0)
    conn.close()
    rc = rm.main(["--db", str(tmp_path / "t.sqlite3")])
    saida = capsys.readouterr().out
    assert rc == 0
    assert "cozilatti" in saida and "gastromaq" in saida
