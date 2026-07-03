"""Carimbo do SKU na DANFE (area livre central), sem rede."""


def _grupo(core, chave="A03", componentes=None):
    return core.Grupo(chave=chave, nome=chave, quantidade=1, shipment_ids=[1],
                      componentes=componentes or [])


# Pacote tipico do ML: DANFE (nota) + etiqueta de envio, dois blocos ^XA..^XZ.
ZPL = "^XA DANFE SIMPLIFICADO conteudo da nota ^XZ\n^XA etiqueta de envio SBA6 ^XZ"


def test_carimbo_so_na_danfe(core):
    out = core.carimbar_zpl(ZPL, "A03")
    assert out.count("^FDA03^FS") == 1                 # uma vez so
    danfe, envio = out.split("^XA etiqueta")           # separa os dois blocos
    assert "^FDA03^FS" in danfe                         # carimbo ficou na DANFE
    assert "A03" not in envio                           # etiqueta de envio intacta


def test_carimbo_nao_toca_a_etiqueta_de_envio(core):
    out = core.carimbar_zpl(ZPL, "A03")
    assert "etiqueta de envio SBA6 ^XZ" in out          # bloco de envio preservado


def test_carimbo_sem_danfe_nao_altera(core):
    zpl = "^XA so etiqueta de envio ^XZ"
    assert core.carimbar_zpl(zpl, "A03") == zpl


def test_carimbo_texto_vazio_nao_altera(core):
    assert core.carimbar_zpl(ZPL, "") == ZPL


def test_carimbo_zpl_invalido_nao_altera(core):
    assert core.carimbar_zpl("texto qualquer", "A03") == "texto qualquer"


def test_carimbo_neutraliza_caracteres_de_controle(core):
    out = core.carimbar_zpl("^XA DANFE ^XZ", "A^03~X")
    assert "^03" not in out.split("^FD")[1]            # ^ e ~ nao viram comando


def test_texto_carimbo_grupo_normal(core):
    assert core._texto_carimbo(_grupo(core, "A03")) == "A03"


def test_texto_carimbo_combo_usa_skus(core):
    g = _grupo(core, "COMBO:A01x1+A03x1", componentes=[("A01", 1), ("A03", 1)])
    assert core._texto_carimbo(g) == "A01+A03"


# ------------------------------------------------------ carimbo por NOME do produto
def test_texto_carimbo_nome_usa_o_mapa(core):
    nomes = {"A03": "Picador Pequeno"}
    assert core._texto_carimbo_nome(_grupo(core, "A03"), nomes) == "Picador Pequeno"


def test_texto_carimbo_nome_cai_no_sku_sem_cadastro(core):
    # SKU sem nome na aba Nomes -> usa o proprio SKU (nunca fica sem identificacao)
    assert core._texto_carimbo_nome(_grupo(core, "A03"), {}) == "A03"


def test_texto_carimbo_nome_combo_junta_nomes(core):
    g = _grupo(core, "COMBO", componentes=[("A01", 1), ("A03", 1)])
    nomes = {"A01": "Liquidificador", "A03": "Picador"}
    assert core._texto_carimbo_nome(g, nomes) == "Liquidificador + Picador"


def test_carimbar_grupo_modo_nome_usa_nome_e_fonte_menor(core):
    g = _grupo(core, "A03")
    out = core._carimbar_grupo(ZPL, g, "carimbo_nome", {"A03": "Picador Pequeno"})
    assert "^FDPicador Pequeno^FS" in out
    assert f"^A0N,{core.CARIMBO_ALTURA_NOME}," in out    # nome longo (15) -> fonte-base
    assert "^FB812,3," in out                            # ate 3 linhas


def test_fonte_nome_curto_maior_longo_menor(core):
    assert core._fonte_nome("1B") == (75, 1)             # bem curto -> fonte grande
    assert core._fonte_nome("Picador") == (60, 1)        # 7 chars
    assert core._fonte_nome("Cutter 12 L") == (50, 2)    # 11 chars
    assert core._fonte_nome("CUTTER 6L 110") == (core.CARIMBO_ALTURA_NOME, 3)  # 13 -> como antes


def test_carimbar_grupo_nome_curto_usa_fonte_maior(core):
    # nome curto (fallback ou cadastrado) deve sair com fonte maior que a base
    out = core._carimbar_grupo(ZPL, _grupo(core, "1B"), "carimbo_nome", {})
    assert "^FD1B^FS" in out
    assert "^A0N,75," in out                             # fonte maior para curto
    assert "^FB812,1," in out                            # 1 linha


def test_carimbar_grupo_modo_sku_inalterado(core):
    out = core._carimbar_grupo(ZPL, _grupo(core, "A03"), "carimbo")
    assert "^FDA03^FS" in out
    assert f"^A0N,{core.CARIMBO_ALTURA}," in out         # fonte cheia do SKU
    assert "^FB812,1," in out                            # 1 linha


def test_carimbar_grupo_modo_nenhuma_nao_altera(core):
    assert core._carimbar_grupo(ZPL, _grupo(core, "A03"), "nenhuma") == ZPL


def test_modo_ident_efetivo_respeita_legado(core, monkeypatch):
    monkeypatch.setattr(core, "MODO_IDENT", "nenhuma")
    monkeypatch.setattr(core, "CARIMBAR_SKU", True)
    assert core._modo_ident_efetivo() == "carimbo"       # CARIMBAR_SKU legado
    monkeypatch.setattr(core, "MODO_IDENT", "carimbo_nome")
    assert core._modo_ident_efetivo() == "carimbo_nome"  # modo novo tem prioridade
