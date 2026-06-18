"""Agrupamento por (produto + quantidade do pedido)."""


def test_agrupa_por_produto_e_quantidade_e_deduplica_envios(core):
    itens = [
        core.ItemPedido(order_id=1, shipment_id=10, chave="A", nome="A", quantidade=1),
        core.ItemPedido(order_id=2, shipment_id=11, chave="A", nome="A", quantidade=1),
        core.ItemPedido(order_id=3, shipment_id=12, chave="A", nome="A", quantidade=2),
        core.ItemPedido(order_id=4, shipment_id=10, chave="A", nome="A", quantidade=1),  # ship repetido
    ]
    grupos = core.agrupar(itens)

    assert len(grupos) == 2  # (A,1) e (A,2)
    g1 = next(g for g in grupos if g.quantidade == 1)
    assert g1.shipment_ids == [10, 11]   # 10 nao duplica
    assert g1.total_etiquetas == 2
    g2 = next(g for g in grupos if g.quantidade == 2)
    assert g2.shipment_ids == [12]


def test_ordena_por_quantidade_e_nome(core):
    itens = [
        core.ItemPedido(order_id=1, shipment_id=1, chave="B", nome="Bola", quantidade=2),
        core.ItemPedido(order_id=2, shipment_id=2, chave="A", nome="Arco", quantidade=1),
    ]
    grupos = core.agrupar(itens)
    assert [g.quantidade for g in grupos] == [1, 2]
