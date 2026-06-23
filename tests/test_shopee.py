"""Shopee (Fase 1): assinatura HMAC e mapeamento pedido -> grupo (sem rede)."""
import hashlib
import hmac

import shopee_api as sh


def test_assinatura_hmac_sha256_deterministica():
    # base = partner_id + path + timestamp + token + shop_id
    cred = {"partner_id": 111, "partner_key": "segredo", "shop_id": 222}
    sign = sh._assinatura_shop(cred, "/api/v2/order/get_order_list", 1700000000, "TOK")
    esperado = hmac.new(
        b"segredo", b"111/api/v2/order/get_order_list1700000000TOK222", hashlib.sha256
    ).hexdigest()
    assert sign == esperado


def test_detectar_formato_etiqueta():
    assert sh.detectar_formato(b"%PDF-1.7\n...") == "PDF"
    assert sh.detectar_formato(b"^XA^FO50,50^FDx^FS^XZ") == "ZPL"
    assert sh.detectar_formato(b"\x89PNG\r\n\x1a\n") == "PNG"
    assert sh.detectar_formato(b"PK\x03\x04") == "ZIP"
    assert sh.detectar_formato(b"qualquer coisa") == "DESCONHECIDO"


def test_status_documento_extrai_status_por_order():
    res = {"response": {"result_list": [
        {"order_sn": "A1", "status": "READY"},
        {"order_sn": "A2", "document_status": "PROCESSING"},
    ]}}
    assert sh._status_documento(res) == {"A1": "READY", "A2": "PROCESSING"}


def test_assinatura_publica():
    cred = {"partner_id": 111, "partner_key": "segredo"}
    sign = sh._assinatura_publica(cred, "/api/v2/auth/token/get", 1700000000)
    esperado = hmac.new(
        b"segredo", b"111/api/v2/auth/token/get1700000000", hashlib.sha256
    ).hexdigest()
    assert sign == esperado


def _detalhes_exemplo(dia_epoch):
    return [
        {"order_sn": "A1", "ship_by_date": dia_epoch,
         "item_list": [{"model_sku": "PRP", "model_quantity_purchased": 1}]},
        {"order_sn": "A2", "ship_by_date": dia_epoch,
         "item_list": [{"item_sku": "PRP", "model_quantity_purchased": 1}]},
        {"order_sn": "A3", "ship_by_date": dia_epoch + 86400,   # outro dia
         "item_list": [{"model_sku": "A02", "model_quantity_purchased": 2}]},
    ]


def test_grupos_filtra_por_dia_e_agrupa_por_sku_quantidade():
    from datetime import datetime
    hoje = sh.core._hoje_br()
    # epoch ao meio-dia de hoje em Brasilia (garante o mesmo dia)
    meio_dia = int(datetime.fromisoformat(hoje + "T12:00:00-03:00").timestamp())
    grupos = sh.grupos_de_detalhes(_detalhes_exemplo(meio_dia), {}, hoje)
    # so os de hoje: PRP q1 (A1 e A2) -> 1 grupo com 2 envios
    assert len(grupos) == 1
    g = grupos[0]
    assert g.chave == "PRP" and g.quantidade == 1
    assert len(g.shipment_ids) == 2


def test_grupos_aplica_nome_amigavel():
    from datetime import datetime
    hoje = sh.core._hoje_br()
    meio_dia = int(datetime.fromisoformat(hoje + "T12:00:00-03:00").timestamp())
    det = [{"order_sn": "A1", "ship_by_date": meio_dia,
            "item_list": [{"model_sku": "PRP", "model_quantity_purchased": 1}]}]
    grupos = sh.grupos_de_detalhes(det, {"PRP": "PICADOR PEQUENO"}, hoje)
    assert grupos[0].nome == "PRP — PICADOR PEQUENO"


def test_data_envio_converte_epoch_para_brasilia():
    from datetime import datetime
    epoch = int(datetime.fromisoformat("2026-06-19T12:00:00-03:00").timestamp())
    assert sh._data_envio(epoch) == "2026-06-19"
    assert sh._data_envio(0) == ""
