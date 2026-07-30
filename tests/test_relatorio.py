"""Formatacao dos textos do bot (puro, sem Telegram nem rede)."""
from datetime import datetime

import relatorio
import separador_etiquetas_ml as core_mod
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


def test_texto_bom_dia(core):
    prontos = [
        {"_envio": {"expected_date": "2026-06-19"}},
        {"_envio": {"expected_date": "2026-06-19"}},
        {"_envio": {"expected_date": "2026-06-22"}},
    ]
    txt = relatorio.texto_bom_dia(prontos, "2026-06-19", "2026-06-20")
    assert "Bom dia! Hoje voce tem 2 pacote(s)" in txt
    assert "2026-06-22" in txt              # inclui o resumo por dia


def test_texto_bom_dia_sem_pedidos(core):
    txt = relatorio.texto_bom_dia([], "2026-06-19", "2026-06-20")
    assert "0 pacote(s)" in txt


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


def test_texto_alerta_pos_horario(core):
    itens = [
        core.ItemPedido(order_id=1, shipment_id=100, chave="A02", nome="A02", quantidade=2),
        core.ItemPedido(order_id=2, shipment_id=101, chave="A06F", nome="A06F", quantidade=1),
    ]
    txt = relatorio.texto_alerta_pos_horario("Cozilatti", itens)
    assert txt.split("\n")[0] == "🔔 Venda Cozilatti"
    assert "A02 - 2" in txt
    assert "A06F - 1" in txt
    assert "100" not in txt  # sem numero de envio


def test_texto_alerta_pos_horario_soma_mesmo_sku_entre_envios(core):
    # O mesmo SKU em 2 envios diferentes deve somar, numa linha so.
    itens = [
        core.ItemPedido(order_id=1, shipment_id=200, chave="A02", nome="A02", quantidade=1),
        core.ItemPedido(order_id=2, shipment_id=201, chave="A02", nome="A02", quantidade=2),
    ]
    txt = relatorio.texto_alerta_pos_horario("", itens)
    assert txt.count("A02") == 1
    assert "A02 - 3" in txt


def test_texto_alerta_pos_horario_sem_conta_usa_rotulo_generico(core):
    txt = relatorio.texto_alerta_pos_horario("", [])
    assert txt == "🔔 Venda nova"


# ------------------------------------------------------------ texto_resumo_vendas_apos
# O resumo e HTML do Telegram (parse_mode="HTML"). Regras que os testes guardam:
# so tags b/i/u/s/a/code/pre/blockquote/tg-spoiler; & < > escapados em TODO texto
# dinamico (senao a API devolve 400 e a mensagem nao chega); alinhamento de
# coluna SO dentro de <pre>; teto de 4096 caracteres.
AGORA = datetime(2026, 7, 30, 12, 33, tzinfo=core_mod.TZ_BR)


def _itens(d: dict) -> list:
    return [{"chave": k, "quantidade": v} for k, v in d.items()]


def _resumo(dados, **kw):
    return relatorio.texto_resumo_vendas_apos(dados, agora=AGORA, **kw)


def test_texto_resumo_vendas_apos_vazio(core):
    assert _resumo({}) == "Nenhuma venda avisada hoje ainda."
    assert _resumo({"Cozilatti": []}) == "Nenhuma venda avisada hoje ainda."


def test_cabecalho_traz_a_janela_e_o_horario(core):
    txt = _resumo({"Cozilatti": _itens({"A01": 1})})
    assert "<b>RESUMO DE VENDAS</b>" in txt
    assert "desde 08h30" in txt
    assert "30/07, 12:33" in txt


def test_ordena_por_quantidade_decrescente(core):
    """O que mais vendeu tem de aparecer primeiro — era o motivo do pedido."""
    txt = _resumo({"Cozilatti": _itens({"A01": 1, "A11": 10, "A05": 6})})
    assert [ln.split()[0] for ln in _linhas_pre(txt)] == ["A11", "A05", "A01"]


def test_empate_desempata_pelo_sku(core):
    """Ordem estavel: sem isso, dois SKUs de mesma quantidade trocariam de lugar
    entre dois envios do mesmo dia e o dono leria como "mudou alguma coisa"."""
    dados = {"Cozilatti": _itens({"B": 2, "A": 2, "C": 2})}
    assert _linhas_pre(_resumo(dados)) == _linhas_pre(_resumo(dados))
    assert [ln.split()[0] for ln in _linhas_pre(_resumo(dados))] == ["A", "B", "C"]


def test_quantidade_alinhada_a_direita(core):
    """Coluna so bate dentro de <pre> — e a largura vem do SKU mais longo do
    bloco, nao de um numero fixo."""
    linhas = _linhas_pre(_resumo({"Cozilatti": _itens({"A11": 10, "M120INX": 3})}))
    # Propriedade, nao string escrita a mao: toda linha com o mesmo comprimento e
    # a quantidade encostada na direita — e o que faz a coluna bater na tela.
    assert len({len(ln) for ln in linhas}) == 1, f"colunas desalinhadas: {linhas}"
    assert [ln.split()[-1] for ln in linhas] == ["10", "3"]
    assert all(ln.rstrip() == ln for ln in linhas), "sobrou espaco depois do numero"


def test_subtotal_por_conta_e_total_geral(core):
    txt = _resumo({"Cozilatti": _itens({"A01": 1, "A05": 3}),
                   "Gastromaq": _itens({"A02": 5})})
    assert "<b>COZILATTI · 4 unidades · 2 SKUs</b>" in txt
    assert "<b>GASTROMAQ · 5 unidades · 1 SKU</b>" in txt
    assert "<b>TOTAL: 9 unidades</b>" in txt


def test_singular_e_plural(core):
    txt = _resumo({"Cozilatti": _itens({"A01": 1})})
    assert "1 unidade ·" in txt and "1 SKU<" in txt
    assert "unidades" not in txt.split("TOTAL:")[0].split("·")[1]


def test_conta_sem_venda_aparece_como_nenhuma_venda(core):
    """Ausencia tambem e informacao: o bloco nao pode sumir."""
    txt = _resumo({"Cozilatti": _itens({"A01": 1}), "Gastromaq": []})
    assert "<b>GASTROMAQ</b>" in txt
    assert "nenhuma venda" in txt


def test_conta_conhecida_sem_registro_tambem_aparece(core):
    """Conta que nem chave tem no estado (nenhuma venda o dia todo)."""
    txt = _resumo({"Cozilatti": _itens({"A01": 1})}, contas=["Cozilatti", "Shopee"])
    assert "<b>SHOPEE</b>" in txt and "nenhuma venda" in txt


# ---- total por SKU (a lista de reposicao) ----

def test_total_por_sku_soma_as_contas(core):
    """O numero que responde "quanto preciso repor": sem ele, o dono somaria de
    cabeca o mesmo SKU que aparece em duas contas."""
    txt = _resumo({"Cozilatti": _itens({"M120INX": 3, "A11": 10}),
                   "Gastromaq": _itens({"M120INX": 2, "A03": 1})})
    consolidado = txt.split("TOTAL POR SKU")[1]
    assert "<b>TOTAL POR SKU · 16 unidades · 3 SKUs</b>" in txt
    assert "M120INX   5" in consolidado          # 3 + 2
    assert "A11      10" in consolidado


def test_total_por_sku_tambem_ordena_por_quantidade(core):
    txt = _resumo({"Cozilatti": _itens({"A01": 1, "B": 2}),
                   "Gastromaq": _itens({"A01": 9})})
    bloco = txt.split("TOTAL POR SKU")[1]
    linhas = bloco.split("<pre>")[1].split("</pre>")[0].split("\n")
    assert [ln.split()[0] for ln in linhas] == ["A01", "B"]


def test_total_por_sku_nao_aparece_com_uma_conta_so(core):
    """Com uma conta, o bloco repetiria a lista dela — viraria ruido."""
    txt = _resumo({"Cozilatti": _itens({"A01": 1, "A05": 3})})
    assert "TOTAL POR SKU" not in txt
    assert "<b>TOTAL: 4 unidades</b>" in txt


def test_total_por_sku_ignora_conta_sem_venda(core):
    """Conta vazia nao pode fazer o consolidado aparecer sozinho."""
    txt = _resumo({"Cozilatti": _itens({"A01": 1})}, contas=["Cozilatti", "Shopee"])
    assert "TOTAL POR SKU" not in txt


# ---- ordem de separacao (aba Nomes) no consolidado ----

ORDEM = ["A01", "A02F", "A05", "A08", "A11", "M120INX"]   # a prateleira


def _consolidado(txt: str) -> list[str]:
    bloco = txt.split("TOTAL POR SKU")[1]
    return [ln.split()[0] for ln in
            bloco.split("<pre>")[1].split("</pre>")[0].split("\n")]


def test_consolidado_segue_a_ordem_da_aba_nomes(core):
    """O TOTAL POR SKU e lista de SEPARACAO: segue a ordem em que o dono anda
    pelo estoque, a mesma da tela e do PDF do resumo do dia."""
    txt = _resumo({"Cozilatti": _itens({"A11": 10, "A01": 1}),
                   "Gastromaq": _itens({"A05": 2, "A02F": 3})}, ordem=ORDEM)
    assert _consolidado(txt) == ["A01", "A02F", "A05", "A11"]


def test_sku_fora_da_aba_nomes_vai_pro_fim(core):
    """Mesma regra de core.ordenar_grupos e historico.resumo_do_dia: quem nao
    esta cadastrado vai pro fim, em ordem natural."""
    txt = _resumo({"Cozilatti": _itens({"A11": 1, "Z9": 1, "Z10": 1}),
                   "Gastromaq": _itens({"A01": 1})}, ordem=ORDEM)
    assert _consolidado(txt) == ["A01", "A11", "Z9", "Z10"]   # Z9 antes de Z10


def test_sem_ordem_o_consolidado_cai_em_quantidade(core):
    """Falha ao ler a aba Nomes nao pode derrubar o resumo — so muda a ordem."""
    txt = _resumo({"Cozilatti": _itens({"A01": 1}), "Gastromaq": _itens({"A11": 9})})
    assert _consolidado(txt) == ["A11", "A01"]


def test_blocos_por_conta_seguem_por_quantidade_mesmo_com_ordem(core):
    """Sao perguntas diferentes: a conta responde "o que mais vendeu", o
    consolidado responde "por onde eu passo pra separar"."""
    txt = _resumo({"Cozilatti": _itens({"A01": 1, "A11": 10}),
                   "Gastromaq": _itens({"A05": 1})}, ordem=ORDEM)
    assert [ln.split()[0] for ln in _linhas_pre(txt)] == ["A11", "A01"]


def test_corte_escolhe_pelos_MAIORES_e_exibe_na_ordem_da_prateleira(core):
    """Quem aparece e escolhido pela quantidade; a ordem de exibicao continua a
    da prateleira. Cortar por POSICAO jogaria fora o fim da caminhada — e o
    maior de todos pode estar na ultima prateleira."""
    ordem = [f"P{i:03d}" for i in range(300)]
    # o maior volume esta no FIM da prateleira
    vendas = {f"P{i:03d}": (1 if i < 299 else 999) for i in range(300)}
    txt = _resumo({"Cozilatti": _itens(vendas), "Gastromaq": _itens({"P000": 1})},
                  ordem=ordem)
    mostrados = _consolidado(txt)
    assert "P299" in mostrados, "o maior sumiu por estar na ultima prateleira"
    sem_aviso = [s for s in mostrados if s != "…"]
    assert sem_aviso == sorted(sem_aviso, key=ordem.index), "saiu da ordem da prateleira"


# ---- HTML: escapar errado nao quebra local, so devolve 400 no envio ----

def test_escapa_texto_dinamico(core):
    txt = _resumo({"Loja & Cia <x>": _itens({"A&B": 5, "X<Y": 2})})
    assert "A&amp;B" in txt and "X&lt;Y" in txt
    assert "LOJA &amp; CIA &lt;X&gt;" in txt


def test_nao_gera_entidade_quebrada_ao_maiusculizar(core):
    """Bug real: escapar ANTES do .upper() produzia "&AMP;" — entidade invalida,
    400 na API. Maiuscula vem primeiro."""
    txt = _resumo({"a & b": _itens({"A01": 1})})
    assert "&AMP;" not in txt and "&amp;" in txt


def test_alinhamento_medido_no_texto_CRU(core):
    """O Telegram renderiza "&amp;" como 1 caractere. Se a largura fosse medida
    no texto ja escapado, a coluna sairia torta na tela apesar de "parecer"
    certa no codigo."""
    import html as _html
    linhas = [_html.unescape(ln) for ln in _linhas_pre(_resumo(
        {"C": _itens({"A&B": 1, "LONGO": 2})}))]
    assert len({len(ln) for ln in linhas}) == 1


# ---- teto do Telegram ----

def test_corta_pelos_maiores_e_avisa_o_corte(core):
    muitos = {f"SKU-BEM-LONGO-DE-VERDADE-{i:04d}": 900 - i for i in range(300)}
    txt = _resumo({"Cozilatti": _itens(muitos), "Gastromaq": _itens(muitos)})
    assert len(txt) <= 4096, "estourou o limite do Telegram"
    assert "… e mais" in txt
    assert "SKU-BEM-LONGO-DE-VERDADE-0000" in txt, "o maior tem de sobreviver ao corte"


def test_pre_nunca_fica_aberto(core):
    """Mensagem UNICA de proposito: dividir o texto partiria um <pre> no meio e
    a API devolveria 400. O corte acontece antes, por SKU."""
    muitos = {f"SKU-BEM-LONGO-DE-VERDADE-{i:04d}": 900 - i for i in range(300)}
    txt = _resumo({"Cozilatti": _itens(muitos), "Gastromaq": _itens(muitos)})
    # Balanceamento, nao a contagem: o numero de blocos muda conforme as contas
    # e o consolidado; o que nao pode mudar e ficar uma tag aberta.
    assert txt.count("<pre>") == txt.count("</pre>") > 0
    assert not txt.rstrip().endswith("<pre>")


def _linhas_pre(txt: str) -> list[str]:
    """Linhas do primeiro bloco <pre> (onde as colunas vivem)."""
    return txt.split("<pre>")[1].split("</pre>")[0].split("\n")


# ------------------------------------------------------------ dividir_mensagem
# Continua em uso pelos OUTROS comandos do bot (texto puro, sem HTML). O resumo
# de vendas nao usa: la o texto tem <pre>, e dividir partiria a tag no meio.

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
