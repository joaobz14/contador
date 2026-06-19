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


def test_texto_detalhe(core):
    itens = [
        core.ItemPedido(order_id=1, shipment_id=10, chave="PRP", nome="PRP",
                        quantidade=1, item_id="MLB1", titulo="Picador", voltagem="110V"),
        core.ItemPedido(order_id=2, shipment_id=11, chave="PRP", nome="PRP",
                        quantidade=1, item_id="MLB1", titulo="Picador", voltagem="110V"),
        core.ItemPedido(order_id=3, shipment_id=12, chave="A02", nome="A02", quantidade=1),
    ]
    txt = relatorio.texto_detalhe(itens, "prp")          # casa sem diferenciar caixa
    assert "Composicao de prp" in txt
    assert "MLB1" in txt and "Picador" in txt and "110V" in txt
    assert "2  MLB1" in txt                               # 2 envios do mesmo item


def test_texto_detalhe_sem_resultado(core):
    assert "Nada encontrado" in relatorio.texto_detalhe([], "XYZ")


def test_dividir_mensagem_curta_nao_divide(core):
    assert relatorio.dividir_mensagem("linha1\nlinha2") == ["linha1\nlinha2"]


def test_dividir_mensagem_respeita_limite(core):
    texto = "\n".join(f"linha {i}" for i in range(100))
    blocos = relatorio.dividir_mensagem(texto, limite=50)
    assert all(len(b) <= 50 for b in blocos)
    assert "\n".join(blocos).count("linha") == 100        # nada se perde


def test_dividir_mensagem_linha_gigante(core):
    blocos = relatorio.dividir_mensagem("x" * 25, limite=10)
    assert blocos == ["x" * 10, "x" * 10, "x" * 5]
