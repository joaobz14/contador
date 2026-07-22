"""Historico de impressao: registro por dia-de-acao, resumo e formatacao."""
from datetime import datetime, timedelta, timezone

import historico
from conftest import make_grupo

TZ = timezone(timedelta(hours=-3))


def _agora(dia="2026-07-22", hora=15):
    return datetime.fromisoformat(f"{dia}T{hora:02d}:00:00").replace(tzinfo=TZ)


def test_registrar_e_resumo_agrega_por_secao_e_item(core, tmp_path):
    arq = tmp_path / "hist.json"
    g_frit = make_grupo(core, [1, 2, 3], chave="FRIT", nome="Fritadeira 220V", qtd=1)
    g_chapa = make_grupo(core, [9, 10], chave="CHAPA", nome="Chapa 80cm", qtd=2)
    g_liq = make_grupo(core, ["BR1"], chave="LIQ", nome="Liquidificador", qtd=1)
    historico.registrar(arq, marketplace="Mercado Livre", conta="cozilatti",
                        grupo=g_frit, ids=[1, 2, 3], agora=_agora())
    historico.registrar(arq, marketplace="Mercado Livre", conta="cozilatti",
                        grupo=g_chapa, ids=[9, 10], agora=_agora())
    historico.registrar(arq, marketplace="Shopee", conta="",
                        grupo=g_liq, ids=["BR1"], agora=_agora())

    r = historico.resumo_do_dia(arq, "2026-07-22")
    assert r["total_pedidos"] == 6           # 3 + 2 + 1 etiquetas
    assert r["total_unidades"] == 8          # 3*1 + 2*2 + 1*1
    secoes = {(s["marketplace"], s["conta"]): s for s in r["secoes"]}
    assert secoes[("Mercado Livre", "cozilatti")]["pedidos"] == 5
    assert secoes[("Shopee", "")]["pedidos"] == 1
    # itens ordenados por nome dentro da secao
    ml_itens = [i["nome"] for i in secoes[("Mercado Livre", "cozilatti")]["itens"]]
    assert ml_itens == ["Chapa 80cm", "Fritadeira 220V"]


def test_formatar_resumo_tem_titulo_secoes_e_total(core, tmp_path):
    arq = tmp_path / "hist.json"
    g = make_grupo(core, [1, 2], chave="K", nome="Chapa 80cm", qtd=2)
    historico.registrar(arq, marketplace="Mercado Livre", conta="cozilatti",
                        grupo=g, ids=[1, 2], agora=_agora())
    texto = historico.formatar_resumo(historico.resumo_do_dia(arq, "2026-07-22"))
    assert "Resumo de impressao - 22/07/2026" in texto
    assert "Mercado Livre (cozilatti)" in texto
    assert "Chapa 80cm (2x)" in texto        # qtd>1 mostra o multiplicador
    assert "Total: 2 etiquetas / 4 unidades" in texto


def test_consolidado_soma_sku_entre_marketplaces_e_ordena_por_nomes(core, tmp_path):
    arq = tmp_path / "hist.json"
    ga = make_grupo(core, [1, 2, 3], chave="A01", nome="2L 110", qtd=1)
    gs = make_grupo(core, ["S1", "S2"], chave="A01", nome="2L 110", qtd=1)
    gf = make_grupo(core, [4, 5], chave="A01F", nome="2L 220", qtd=2)
    gz = make_grupo(core, [9], chave="Z99", nome="Zebra", qtd=1)
    historico.registrar(arq, marketplace="Mercado Livre", conta="cozilatti",
                        grupo=ga, ids=[1, 2, 3], agora=_agora())
    historico.registrar(arq, marketplace="Shopee", conta="",
                        grupo=gs, ids=["S1", "S2"], agora=_agora())
    historico.registrar(arq, marketplace="Mercado Livre", conta="cozilatti",
                        grupo=gf, ids=[4, 5], agora=_agora())
    historico.registrar(arq, marketplace="Mercado Livre", conta="GASTROMAQ",
                        grupo=gz, ids=[9], agora=_agora())

    # ordem da aba Nomes: A01F antes de A01; Z99 nao esta -> vai pro fim
    r = historico.resumo_do_dia(arq, "2026-07-22", ordem=["A01F", "A01"])
    consol = {c["chave"]: c for c in r["consolidado"]}
    assert consol["A01"]["unidades"] == 5     # 3 (ML) + 2 (Shopee) somados
    assert consol["A01F"]["unidades"] == 4    # 2 etiquetas * qtd 2
    # ordem segue Nomes; SKU fora da lista por ultimo
    assert [c["chave"] for c in r["consolidado"]] == ["A01F", "A01", "Z99"]
    assert historico.linhas_consolidado(r)[0] == "A01F - 2L 220 - 4"


def test_gerar_pdf_valido_e_pagina(core, tmp_path):
    pdf = tmp_path / "s.pdf"
    historico.gerar_pdf(pdf, "Titulo", [f"SKU{i} - nome - {i}" for i in range(200)])
    dados = pdf.read_bytes()
    assert dados.startswith(b"%PDF-") and dados.rstrip().endswith(b"%%EOF")
    assert dados.count(b"/MediaBox") >= 2      # 200 linhas -> paginou

    # acentos nao quebram (cp1252 / WinAnsiEncoding)
    historico.gerar_pdf(pdf, "Resumo", ["Fritadeira Eletrica 220V - 3"])
    assert pdf.read_bytes().startswith(b"%PDF-")


def test_resumo_dia_vazio(core, tmp_path):
    arq = tmp_path / "hist.json"
    r = historico.resumo_do_dia(arq, "2026-07-22")
    assert r["secoes"] == [] and r["total_pedidos"] == 0
    assert "Nada impresso" in historico.formatar_resumo(r)


def test_poda_descarta_eventos_antigos(core, tmp_path, monkeypatch):
    arq = tmp_path / "hist.json"
    monkeypatch.setattr(historico, "DIAS_HISTORICO", 30)
    g = make_grupo(core, [1], chave="K", nome="X")
    velho = _agora(dia="2026-05-01")         # bem alem de 30 dias
    hoje = _agora(dia="2026-07-22")
    historico.registrar(arq, marketplace="Mercado Livre", conta="c", grupo=g,
                        ids=[1], agora=velho)
    historico.registrar(arq, marketplace="Mercado Livre", conta="c", grupo=g,
                        ids=[2], agora=hoje)
    # o evento velho foi podado na 2a gravacao (hoje - 30 dias como limite)
    assert historico.resumo_do_dia(arq, "2026-05-01")["secoes"] == []
    assert historico.resumo_do_dia(arq, "2026-07-22")["total_pedidos"] == 1


def test_registrar_e_best_effort_nunca_levanta(core, tmp_path, monkeypatch):
    # gravar_json quebrando nao pode propagar (historico e secundario)
    monkeypatch.setattr(historico._estado, "gravar_json",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("disco cheio")))
    g = make_grupo(core, [1], chave="K", nome="X")
    historico.registrar(tmp_path / "h.json", marketplace="Mercado Livre",
                        conta="c", grupo=g, ids=[1])   # nao deve levantar


def test_core_marcar_impresso_registra_no_historico(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_ESTADO", tmp_path / "estado.json")
    monkeypatch.setattr(core, "ARQUIVO_HISTORICO", tmp_path / "hist.json")
    monkeypatch.setattr(core, "conta_ativa", lambda: "cozilatti")
    g = make_grupo(core, [11, 12], chave="SKU9", nome="Forno", qtd=1)
    g.dia = "2026-07-23"
    estado: dict = {}
    core.marcar_impresso(estado, g, [11, 12])
    r = historico.resumo_do_dia(core.ARQUIVO_HISTORICO,
                                datetime.now(TZ).date().isoformat())
    secoes = {(s["marketplace"], s["conta"]): s for s in r["secoes"]}
    assert secoes[("Mercado Livre", "cozilatti")]["pedidos"] == 2


def test_core_marcar_impresso_nao_conta_reimpressao(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_ESTADO", tmp_path / "estado.json")
    monkeypatch.setattr(core, "ARQUIVO_HISTORICO", tmp_path / "hist.json")
    monkeypatch.setattr(core, "conta_ativa", lambda: "c")
    g = make_grupo(core, [1, 2, 3], chave="K", nome="X")
    estado: dict = {}
    core.marcar_impresso(estado, g, [1, 2])          # marca 1,2
    core.marcar_impresso(estado, g, [1, 2, 3])       # so o 3 e novo
    core.marcar_impresso(estado, g, [1, 2, 3])       # nada novo -> sem evento
    hoje = datetime.now(TZ).date().isoformat()
    r = historico.resumo_do_dia(core.ARQUIVO_HISTORICO, hoje)
    # 2 + 1 = 3 etiquetas ao todo (a reimpressao nao somou)
    assert r["total_pedidos"] == 3
