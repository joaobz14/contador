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
