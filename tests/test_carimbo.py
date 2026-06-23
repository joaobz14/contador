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
