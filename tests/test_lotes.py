"""Impressao em lote + divisoria + carimbo centralizado (sem rede)."""
import pytest


def _grupo(core, chave="A05F", nome="A05F EXAUSTOR", qtd=1, ships=(1,), comp=None):
    return core.Grupo(chave=chave, nome=nome, quantidade=qtd,
                      shipment_ids=list(ships), componentes=comp or [])


def test_carimbo_centralizado_usa_field_block(core):
    out = core.carimbar_zpl("^XA ^PW812 DANFE ^XZ", "A05F")
    assert "^FB" in out and ",C," in out          # centralizado via field block
    assert "^FDA05F^FS" in out


def test_carimbo_usa_largura_do_pw(core):
    # a largura do ^FB deve refletir o ^PW do bloco
    out = core.carimbar_zpl("^XA ^PW600 DANFE ^XZ", "A05F")
    assert "^FB600," in out


def test_largura_zpl_padrao_quando_sem_pw(core):
    assert core._largura_zpl("^XA DANFE ^XZ") == core.LARGURA_ETIQUETA


def test_zpl_divisoria_tem_sku_nome_e_quantidade(core):
    g = _grupo(core, chave="A05F", nome="A05F EXAUSTOR 220", qtd=2, ships=(1, 2, 3))
    z = core.zpl_divisoria(g)
    assert z.startswith("^XA") and z.endswith("^XZ")
    assert "A05F" in z and "EXAUSTOR 220" in z
    assert "q2" in z and "3 etiqueta(s)" in z


def test_zpl_divisoria_combo_usa_skus(core):
    g = _grupo(core, chave="COMBO:A01x1+A03x1", comp=[("A01", 1), ("A03", 1)])
    assert "A01+A03" in core.zpl_divisoria(g)


# --------------------------------------------------------------- lotes
def _mocka_download(core, monkeypatch, tmp_path):
    monkeypatch.setattr(core, "_gerar_zip", lambda rotulo, zpl: tmp_path / "z.zip")
    monkeypatch.setattr(core, "baixar_zpl",
                        lambda token, ids: "^XA DANFE ^XZ\n^XA etiqueta ^XZ")


def test_preparar_lotes_divisoria_insere_separador(core, monkeypatch, tmp_path):
    _mocka_download(core, monkeypatch, tmp_path)
    g = _grupo(core, "A01", "A01 LIQ", ships=(10,))
    zpl, pend = core.preparar_lotes("tok", [g], {}, modo="divisoria")
    assert pend == [(g, [10])]
    # a divisoria (com o SKU em ^FB centralizado) vem ANTES da etiqueta do lote
    assert zpl.index("A01") < zpl.index("DANFE")


def test_preparar_lotes_carimbo_carimba_danfe(core, monkeypatch, tmp_path):
    _mocka_download(core, monkeypatch, tmp_path)
    g = _grupo(core, "A01", "A01 LIQ", ships=(10,))
    zpl, _ = core.preparar_lotes("tok", [g], {}, modo="carimbo")
    assert "^FDA01^FS" in zpl                      # carimbou o SKU na DANFE


def test_preparar_lotes_carimbo_nome_carimba_o_nome(core, monkeypatch, tmp_path):
    _mocka_download(core, monkeypatch, tmp_path)
    monkeypatch.setattr(core, "carregar_nomes", lambda: {"A01": "Liquidificador AR 2L"})
    g = _grupo(core, "A01", "A01 LIQ", ships=(10,))
    zpl, _ = core.preparar_lotes("tok", [g], {}, modo="carimbo_nome")
    assert "^FDLiquidificador AR 2L^FS" in zpl     # carimbou o NOME, nao o SKU
    assert "^FDA01^FS" not in zpl


def test_preparar_lotes_pula_ja_impressos(core, monkeypatch, tmp_path):
    _mocka_download(core, monkeypatch, tmp_path)
    g = _grupo(core, "A01", "A01 LIQ", ships=(10,))
    estado = {core._chave_estado(g): [10]}         # ja impresso
    zpl, pend = core.preparar_lotes("tok", [g], estado, modo="nenhuma")
    assert pend == [] and zpl == ""


def test_gerar_zip_lotes_nao_marca_estado(core, monkeypatch, tmp_path):
    _mocka_download(core, monkeypatch, tmp_path)
    g = _grupo(core, "A01", "A01 LIQ", ships=(10,))
    estado = {}
    pend = core.gerar_zip_lotes("tok", [g], estado, modo="nenhuma")
    assert pend == [(g, [10])]
    assert estado == {}                            # NAO marcou (marca apos confirmacao)


def test_gerar_zip_lotes_aborta_em_zpl_invalido(core, monkeypatch, tmp_path):
    monkeypatch.setattr(core, "_gerar_zip", lambda rotulo, zpl: tmp_path / "z.zip")
    monkeypatch.setattr(core, "baixar_zpl", lambda token, ids: "sem zpl valido")
    with pytest.raises(core.SeparadorError):
        core.gerar_zip_lotes("tok", [_grupo(core, ships=(1,))], {}, modo="nenhuma")
