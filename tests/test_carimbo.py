"""Carimbo do SKU na etiqueta ZPL (sem rede)."""


def _grupo(core, chave="A03", componentes=None):
    return core.Grupo(chave=chave, nome=chave, quantidade=1, shipment_ids=[1],
                      componentes=componentes or [])


def test_carimbo_insere_sku_antes_do_fim_da_etiqueta(core):
    zpl = "^XA^FO50,50^FDfulano^FS^XZ"
    out = core.carimbar_zpl(zpl, "A03")
    assert out.count("^XZ") == 1
    assert "^FDA03^FS" in out
    assert "fulano" in out                     # nada do original e perdido
    assert out.index("A03") < out.index("^XZ") # carimbo vem antes do fim


def test_carimbo_em_todas_as_etiquetas(core):
    zpl = "^XA...^XZ\n^XA...^XZ"
    out = core.carimbar_zpl(zpl, "A05")
    assert out.count("^FDA05^FS") == 2         # uma por etiqueta


def test_carimbo_pula_a_danfe(core):
    # pacote do ML: DANFE (nota) + etiqueta de envio. So a etiqueta leva carimbo.
    zpl = "^XA DANFE SIMPLIFICADO ^XZ\n^XA etiqueta de envio ^XZ"
    out = core.carimbar_zpl(zpl, "A03")
    assert out.count("^FDA03^FS") == 1         # so na etiqueta de envio
    assert "DANFE" in out                      # bloco da nota preservado


def test_carimbo_texto_vazio_nao_altera(core):
    zpl = "^XA^XZ"
    assert core.carimbar_zpl(zpl, "") == zpl


def test_carimbo_zpl_invalido_nao_altera(core):
    assert core.carimbar_zpl("texto qualquer", "A03") == "texto qualquer"


def test_carimbo_neutraliza_caracteres_de_controle(core):
    out = core.carimbar_zpl("^XA^XZ", "A^03~X")
    assert "^03" not in out.split("^FD")[1]    # ^ e ~ nao escapam para comando


def test_texto_carimbo_grupo_normal(core):
    assert core._texto_carimbo(_grupo(core, "A03")) == "A03"


def test_texto_carimbo_combo_usa_skus(core):
    g = _grupo(core, "COMBO:A01x1+A03x1", componentes=[("A01", 1), ("A03", 1)])
    assert core._texto_carimbo(g) == "A01+A03"
