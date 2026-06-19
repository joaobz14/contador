"""Formatacao dos textos do bot (puro, sem Telegram nem rede)."""
import relatorio
from conftest import make_grupo


def test_texto_grupos_vazio(core):
    txt = relatorio.texto_grupos([], "HOJE")
    assert "nenhum grupo" in txt.lower()


def test_texto_grupos_lista_por_quantidade(core):
    g1 = make_grupo(core, [1, 2, 3], chave="A02", nome="A02 — LIQUIDIFICADOR", qtd=1)
    g2 = make_grupo(core, [9], chave="A06F", nome="A06F — EXAUSTOR", qtd=2)
    txt = relatorio.texto_grupos([g1, g2], "HOJE")
    assert "HOJE — 2 grupo(s), 4 etiqueta(s)" in txt
    assert "Quantidade por pedido = 1" in txt
    assert "Quantidade por pedido = 2" in txt
    assert "A02 — LIQUIDIFICADOR" in txt
    assert "A06F — EXAUSTOR" in txt


def test_texto_resumo(core):
    prontos = [
        {"_envio": {"expected_date": "2026-06-19"}},
        {"_envio": {"expected_date": "2026-06-19"}},
        {"_envio": {"expected_date": "2026-06-20"}},
    ]
    txt = relatorio.texto_resumo(prontos, "2026-06-19", "2026-06-20")
    assert "2026-06-19     2 pacote(s)  <= HOJE" in txt
    assert "2026-06-20     1 pacote(s)  <= amanha" in txt
    assert "Total: 3 pacote(s) em 2 dia(s)." in txt


def test_texto_resumo_vazio(core):
    assert "Nenhum envio" in relatorio.texto_resumo([], "2026-06-19", "2026-06-20")
