"""Agrupamento por envio: 1 envio = 1 etiqueta (inclui combos multi-SKU)."""


def _item(core, sid, chave, qtd=1):
    return core.ItemPedido(order_id=sid, shipment_id=sid, chave=chave, nome=chave, quantidade=qtd)


def test_envios_de_um_unico_sku_agrupam_por_sku_e_quantidade(core):
    itens = [
        _item(core, 10, "A", 1),
        _item(core, 11, "A", 1),
        _item(core, 12, "A", 2),   # 2 unidades do mesmo SKU = 1 etiqueta, grupo qtd 2
    ]
    grupos = core.agrupar(itens)
    assert len(grupos) == 2
    g1 = next(g for g in grupos if g.quantidade == 1)
    assert g1.chave == "A" and sorted(g1.shipment_ids) == [10, 11] and g1.total_etiquetas == 2
    g2 = next(g for g in grupos if g.quantidade == 2)
    assert g2.chave == "A" and g2.shipment_ids == [12]


def test_mesmo_sku_em_duas_linhas_soma_quantidade(core):
    # envio unico com o mesmo SKU em duas linhas -> soma (nao vira combo)
    grupos = core.agrupar([_item(core, 10, "A", 1), _item(core, 10, "A", 1)])
    assert len(grupos) == 1
    assert grupos[0].chave == "A" and grupos[0].quantidade == 2
    assert grupos[0].total_etiquetas == 1           # 1 envio = 1 etiqueta
    assert grupos[0].componentes == []


def test_envio_combo_vira_um_grupo_com_uma_etiqueta(core):
    # 1 envio com SKUs diferentes (A01 + A03) = 1 etiqueta, nao separa por SKU
    grupos = core.agrupar([_item(core, 99, "A01", 1), _item(core, 99, "A03", 1)])
    assert len(grupos) == 1
    g = grupos[0]
    assert g.total_etiquetas == 1                    # NAO conta 2
    assert g.quantidade == 1
    assert g.componentes == [("A01", 1), ("A03", 1)]
    assert g.chave == "COMBO:A01x1+A03x1"
    assert "Combo" in g.nome and "A01" in g.nome and "A03" in g.nome


def test_combos_iguais_agrupam_juntos(core):
    itens = [
        _item(core, 1, "A01", 1), _item(core, 1, "A03", 1),
        _item(core, 2, "A03", 1), _item(core, 2, "A01", 1),   # mesma combinacao (ordem diferente)
    ]
    grupos = core.agrupar(itens)
    assert len(grupos) == 1                          # combos iguais juntos
    assert grupos[0].total_etiquetas == 2            # 2 pacotes = 2 etiquetas
    assert sorted(grupos[0].shipment_ids) == [1, 2]


def test_aplicar_nomes_em_combo(core):
    grupos = core.agrupar([_item(core, 5, "A01", 1), _item(core, 5, "A03", 2)])
    core.aplicar_nomes(grupos, {"A01": "LIQUIDIFICADOR AR 2L 110 M1", "A03": "LIQUIDIFICADOR BR 2L 110 M1"})
    nome = grupos[0].nome
    assert "A01 — LIQUIDIFICADOR AR 2L 110 M1" in nome
    assert "A03 — LIQUIDIFICADOR BR 2L 110 M1 (x2)" in nome
