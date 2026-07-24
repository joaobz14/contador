"""Testes da camada de narrativa (ads-monitor/narrar.py).

Importa por caminho (a pasta tem hifen, nao e pacote Python) — mesmo padrao de
tests/test_ads_monitor_recomendar.py. narrar.py nao tem @dataclass proprio (so
importa recomendar.py, que tem) e faz um `import recomendar as rm` NORMAL no
seu proprio topo — o import normal do Python ja registra sys.modules antes de
executar o corpo do modulo, entao nao precisa do truque de sys.modules que
test_ads_monitor_recomendar.py usa pra importar recomendar.py DIRETO pela API
de baixo nivel do importlib.
"""
import datetime
import importlib.util
import json
from pathlib import Path
from unittest import mock

_RAIZ = Path(__file__).resolve().parent.parent / "ads-monitor"

_SPEC_COLETAR = importlib.util.spec_from_file_location(
    "ads_monitor_coletar", _RAIZ / "coletar.py")
cm = importlib.util.module_from_spec(_SPEC_COLETAR)
_SPEC_COLETAR.loader.exec_module(cm)

_SPEC_NARRAR = importlib.util.spec_from_file_location(
    "ads_monitor_narrar", _RAIZ / "narrar.py")
nr = importlib.util.module_from_spec(_SPEC_NARRAR)
_SPEC_NARRAR.loader.exec_module(nr)


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


# ------------------------------------------------------------- montar_dados
def test_montar_dados_inclui_recomendacao_e_monitorando(tmp_path):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    dias = _janela(7)
    _popular(conn, dias, "cozilatti", 1, "Orcamento Baixo", perdido_orcamento=0.40)
    _popular(conn, dias, "cozilatti", 2, "Saudavel", roas=15.0)
    dados = nr.montar_dados(conn, ["cozilatti"], dias[-1], 7)
    conn.close()

    conta = dados["contas"][0]
    assert conta["conta"] == "cozilatti"
    tipos = {r["tipo"] for r in conta["recomendacoes"]}
    assert tipos == {"orcamento_insuficiente"}
    nomes_monitorando = {m["campaign_name"] for m in conta["monitorando"]}
    assert nomes_monitorando == {"Saudavel"}


def test_montar_dados_campanha_fraca_vira_monitorando(tmp_path):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    dias = _janela(2)  # < MIN_DIAS
    _popular(conn, dias, "cozilatti", 1, "Nova", perdido_orcamento=0.40)
    dados = nr.montar_dados(conn, ["cozilatti"], dias[-1], 7)
    conn.close()

    conta = dados["contas"][0]
    assert conta["recomendacoes"] == []
    assert conta["monitorando"][0]["motivo"] == "dado insuficiente"


def test_montar_dados_preserva_condicionada_margem(tmp_path):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    dias = _janela(7)
    _popular(conn, dias, "cozilatti", 1, "Orcamento Baixo", perdido_orcamento=0.40)
    dados = nr.montar_dados(conn, ["cozilatti"], dias[-1], 7)
    conn.close()

    rec = dados["contas"][0]["recomendacoes"][0]
    assert rec["condicionada_margem"] is True


# ------------------------------------------------------------- montar_prompt
def test_montar_prompt_contem_regras_e_dados():
    dados = {"periodo": {"de": "2026-07-16", "ate": "2026-07-22", "dias": 7},
            "gerado_em": "2026-07-22T10:00:00-03:00",
            "contas": [{"conta": "cozilatti", "recomendacoes": [], "monitorando": []}]}
    prompt = nr.montar_prompt(dados)
    assert "REGRAS OBRIGATORIAS" in prompt
    assert "cozilatti" in prompt
    # o payload precisa estar em JSON valido dentro do prompt
    inicio_json = prompt.index("{")
    json.loads(prompt[inicio_json:])


# ------------------------------------------------------------- chamar_claude
def test_chamar_claude_sem_binario_devolve_vazio(monkeypatch):
    monkeypatch.setattr(nr.shutil, "which", lambda _: None)
    assert nr.chamar_claude("prompt qualquer") == ""


def test_chamar_claude_timeout_devolve_vazio(monkeypatch):
    monkeypatch.setattr(nr.shutil, "which", lambda _: "/usr/bin/claude")

    def _levanta(*a, **kw):
        raise nr.subprocess.TimeoutExpired(cmd="claude", timeout=1)

    monkeypatch.setattr(nr.subprocess, "run", _levanta)
    assert nr.chamar_claude("prompt qualquer", timeout=1) == ""


def test_chamar_claude_retorno_no_zero_devolve_vazio(monkeypatch):
    monkeypatch.setattr(nr.shutil, "which", lambda _: "/usr/bin/claude")
    resultado = mock.Mock(returncode=1, stdout="")
    monkeypatch.setattr(nr.subprocess, "run", lambda *a, **kw: resultado)
    assert nr.chamar_claude("prompt qualquer") == ""


def test_chamar_claude_sucesso_devolve_stdout(monkeypatch):
    monkeypatch.setattr(nr.shutil, "which", lambda _: "/usr/bin/claude")
    resultado = mock.Mock(returncode=0, stdout="  texto narrado  \n")
    monkeypatch.setattr(nr.subprocess, "run", lambda *a, **kw: resultado)
    assert nr.chamar_claude("prompt qualquer") == "texto narrado"


# --------------------------------------------------------- salvar_relatorio
def test_salvar_relatorio_grava_arquivo(tmp_path):
    caminho = nr.salvar_relatorio("conteudo do relatorio",
                                  datetime.date(2026, 7, 22), pasta=tmp_path)
    assert caminho.exists()
    assert caminho.read_text(encoding="utf-8") == "conteudo do relatorio"
    assert "2026-07-22" in caminho.name


# ------------------------------------------------------------------------- CLI
def test_main_sem_historico(tmp_path, capsys):
    conn = cm.conectar_db(tmp_path / "vazio.sqlite3")
    conn.close()
    rc = nr.main(["--db", str(tmp_path / "vazio.sqlite3")])
    assert rc == 1
    assert "Nenhum historico" in capsys.readouterr().out


def test_main_dry_run_nao_chama_ia(tmp_path, capsys, monkeypatch):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    dias = _janela(7)
    _popular(conn, dias, "cozilatti", 1, "Orcamento Baixo", perdido_orcamento=0.40)
    conn.close()

    chamado = []
    monkeypatch.setattr(nr, "chamar_claude",
                        lambda *a, **kw: chamado.append(1) or "nunca")
    rc = nr.main(["--db", str(tmp_path / "t.sqlite3"), "--dry-run"])
    saida = capsys.readouterr().out
    assert rc == 0
    assert chamado == []
    assert "REGRAS OBRIGATORIAS" in saida


def test_main_ia_indisponivel_nao_quebra(tmp_path, capsys, monkeypatch):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    dias = _janela(7)
    _popular(conn, dias, "cozilatti", 1, "Orcamento Baixo", perdido_orcamento=0.40)
    conn.close()

    monkeypatch.setattr(nr, "chamar_claude", lambda *a, **kw: "")
    rc = nr.main(["--db", str(tmp_path / "t.sqlite3")])
    saida = capsys.readouterr().out
    assert rc == 1
    assert "IA nao respondeu" in saida


def test_main_sucesso_salva_e_imprime(tmp_path, capsys, monkeypatch):
    conn = cm.conectar_db(tmp_path / "t.sqlite3")
    dias = _janela(7)
    _popular(conn, dias, "cozilatti", 1, "Orcamento Baixo", perdido_orcamento=0.40)
    conn.close()

    pasta_saida = tmp_path / "saida"
    monkeypatch.setattr(nr, "PASTA_RELATORIOS", pasta_saida)
    monkeypatch.setattr(nr, "chamar_claude", lambda *a, **kw: "narrativa gerada")
    rc = nr.main(["--db", str(tmp_path / "t.sqlite3")])
    saida = capsys.readouterr().out
    assert rc == 0
    assert "narrativa gerada" in saida
    assert list(pasta_saida.glob("narrativa_*.md"))
