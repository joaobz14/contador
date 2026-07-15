"""Identidade do produto: SKU > GTIN+voltagem > item_id:variacao."""


def test_voltagem(core):
    item = {"variation_attributes": [{"id": "VOLTAGE", "value_name": "110V"}]}
    assert core._voltagem(item) == "110V"
    assert core._voltagem({}) == ""


def test_identidade_por_sku_tem_prioridade(core):
    item = {"seller_sku": "  A12  ", "id": "MLB1"}
    assert core.identidade(item, {}) == ("A12", "A12")


def test_identidade_usa_seller_custom_field(core):
    item = {"seller_custom_field": "XYZ"}
    assert core.identidade(item, {}) == ("XYZ", "XYZ")


def test_identidade_por_gtin_com_voltagem(core):
    item = {
        "id": "MLB1", "variation_id": 7, "title": "Furadeira",
        "variation_attributes": [{"id": "VOLTAGE", "value_name": "220V"}],
    }
    cache = {"MLB1": {"title": "Furadeira", "variations": {"7": "789123"}}}
    chave, nome = core.identidade(item, cache)
    assert chave == "GTIN:789123|220V"
    assert nome == "Furadeira (220V)"


def test_identidade_fallback_item_variacao(core):
    item = {"id": "MLB2", "variation_id": 0, "title": "Cabo"}
    assert core.identidade(item, {}) == ("MLB2:0", "Cabo")


def test_identidade_adota_anuncio_sem_sku_via_mapa(core):
    # Anuncio sem SKU cujo codigo esta no de-para -> tratado como aquele SKU.
    item = {"id": "MLB3982067005", "variation_id": 0, "title": "Fogao 1 Boca"}
    mapa = {"MLB3982067005:0": "F1AP"}
    assert core.identidade(item, {}, mapa) == ("F1AP", "F1AP")


def test_identidade_mapa_ignora_quem_ja_tem_sku(core):
    item = {"seller_sku": "A12", "id": "MLB1"}
    assert core.identidade(item, {}, {"MLB1:0": "X"}) == ("A12", "A12")


def test_identidade_adota_anuncio_por_gtin(core):
    # A chave do mapa e a mesma que identidade geraria (aqui, GTIN).
    item = {"id": "MLB1", "variation_id": 7, "title": "Furadeira"}
    cache = {"MLB1": {"title": "Furadeira", "variations": {"7": "789123"}}}
    assert core.identidade(item, cache, {"GTIN:789123": "FUR1"}) == ("FUR1", "FUR1")


def test_identidade_sem_mapa_mantem_comportamento(core):
    item = {"id": "MLB2", "variation_id": 0, "title": "Cabo"}
    assert core.identidade(item, {}) == ("MLB2:0", "Cabo")
    assert core.identidade(item, {}, {}) == ("MLB2:0", "Cabo")


def test_skus_anuncio_round_trip_apara_e_descarta_vazios(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_SKUS_ANUNCIO", tmp_path / "skus.json")
    core.salvar_skus_anuncio({"  MLB1:0 ": "  F1AP  ", "semvalor": "", "": "X"})
    assert core.carregar_skus_anuncio() == {"MLB1:0": "F1AP"}
