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


def test_envio_ja_arranjado():
    # info_needed vazio -> ja organizado
    assert sh.envio_ja_arranjado({"response": {"info_needed": {}}}) is True
    # metodo presente (mesmo com lista vazia de campos) -> ainda precisa organizar.
    # Comportamento observado na API real: pedido nao organizado devolve
    # info_needed = {"dropoff": []}.
    assert sh.envio_ja_arranjado(
        {"response": {"info_needed": {"dropoff": []}}}) is False
    assert sh.envio_ja_arranjado(
        {"response": {"info_needed": {"pickup": ["address_id"]}}}) is False


def test_detectar_formato_zpl_cru_shopee():
    # etiqueta termica Shopee crua comeca com ~DGR (download de grafico Z64)
    assert sh.detectar_formato(b"~DGR:DEMO.GRF,1234,12,:Z64:abc") == "ZPL"


def test_criar_documento_inclui_tracking_number(monkeypatch):
    capturado = {}

    def fake_post(cred, token, path, body):
        capturado["path"] = path
        capturado["body"] = body
        return {"error": "", "response": {"result_list": [{"order_sn": "A1"}]}}

    monkeypatch.setattr(sh, "_post_shop", fake_post)
    sh.criar_documento({"x": 1}, "TOK", ["A1"], rastreios={"A1": "BR123"})
    item = capturado["body"]["order_list"][0]
    assert capturado["path"].endswith("create_shipping_document")
    assert item["order_sn"] == "A1"
    assert item["tracking_number"] == "BR123"        # AWB no corpo (senao da 404/invalid)
    assert item["shipping_document_type"] == sh.TIPO_ETIQUETA


def test_criar_documento_sem_rastreio_omite_campo(monkeypatch):
    capturado = {}
    monkeypatch.setattr(sh, "_post_shop",
                        lambda cred, token, path, body: capturado.update(body=body) or {})
    sh.criar_documento({"x": 1}, "TOK", ["A1"])
    assert "tracking_number" not in capturado["body"]["order_list"][0]


def test_gerar_etiqueta_aborta_sem_awb(monkeypatch):
    # sem AWB (envio nao organizado) -> erro claro, sem chamar o create
    monkeypatch.setattr(sh, "obter_token", lambda cred: "TOK")
    monkeypatch.setattr(sh, "numero_rastreio", lambda cred, token, sn: "")

    def nao_deveria(*a, **k):
        raise AssertionError("create nao deveria ser chamado sem AWB")

    monkeypatch.setattr(sh, "criar_documento", nao_deveria)
    import pytest
    with pytest.raises(sh.core.SeparadorError, match="rastreio"):
        sh.gerar_etiqueta({"x": 1}, ["A1"])


def test_numero_rastreio_le_response(monkeypatch):
    monkeypatch.setattr(sh, "_get_shop",
                        lambda cred, token, path, params: {"response": {"tracking_number": "BR9 "}})
    assert sh.numero_rastreio({"x": 1}, "TOK", "A1") == "BR9"


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


# ----------------------------------------------------- organizar envio (drop-off)
def test_montar_dropoff_vazio_quando_nada_exigido():
    assert sh._montar_dropoff({"dropoff": []}) == {}
    assert sh._montar_dropoff({}) == {}


def test_montar_dropoff_inclui_campos_exigidos():
    d = sh._montar_dropoff({"dropoff": ["branch_id", "sender_real_name"]},
                           branch_id=7, sender_real_name="Gastromaq")
    assert d == {"branch_id": 7, "sender_real_name": "Gastromaq"}


def test_montar_dropoff_ignora_tracking_number():
    # tracking_number e gerado pela Shopee — nunca enviado
    assert sh._montar_dropoff({"dropoff": ["tracking_number"]}) == {}


def test_montar_dropoff_erro_se_campo_faltando():
    import pytest
    with pytest.raises(sh.core.SeparadorError, match="branch_id"):
        sh._montar_dropoff({"dropoff": ["branch_id"]})   # sem fornecer branch_id


def test_organizar_envio_pula_se_ja_tem_awb(monkeypatch):
    monkeypatch.setattr(sh, "numero_rastreio", lambda c, t, sn: "BR123")
    monkeypatch.setattr(sh, "ship_order",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("nao chamar")))
    assert sh.organizar_envio({}, "TOK", "A1") == "BR123"      # devolve o AWB existente


def test_organizar_envio_posta_e_espera_o_awb(monkeypatch):
    capturado = {}
    chamadas = {"n": 0}

    def fake_rastreio(c, t, sn):       # vazio na 1a checagem; AWB so apos o ship_order
        chamadas["n"] += 1
        return "" if chamadas["n"] == 1 else "BR9"

    monkeypatch.setattr(sh, "numero_rastreio", fake_rastreio)
    monkeypatch.setattr(sh, "parametros_envio",
                        lambda c, t, sn: {"response": {"info_needed": {"dropoff": []}}})
    monkeypatch.setattr(sh, "ship_order",
                        lambda c, t, sn, **k: capturado.update(sn=sn, kw=k) or {})
    monkeypatch.setattr(sh.time, "sleep", lambda *_a, **_k: None)
    assert sh.organizar_envio({}, "TOK", "A1") == "BR9"        # esperou o AWB sair
    assert capturado["sn"] == "A1" and capturado["kw"]["dropoff"] == {}


def test_organizar_envio_erro_se_awb_nao_sai(monkeypatch):
    import pytest
    monkeypatch.setattr(sh, "numero_rastreio", lambda c, t, sn: "")        # AWB nunca sai
    monkeypatch.setattr(sh, "parametros_envio",
                        lambda c, t, sn: {"response": {"info_needed": {"dropoff": []}}})
    monkeypatch.setattr(sh, "ship_order", lambda c, t, sn, **k: {})
    monkeypatch.setattr(sh.time, "sleep", lambda *_a, **_k: None)
    with pytest.raises(sh.core.SeparadorError, match="AWB"):
        sh.organizar_envio({}, "TOK", "A1", tentativas=2)


def test_organizar_envio_erro_se_so_pickup(monkeypatch):
    import pytest
    monkeypatch.setattr(sh, "numero_rastreio", lambda c, t, sn: "")
    monkeypatch.setattr(sh, "parametros_envio",
                        lambda c, t, sn: {"response": {"info_needed": {"pickup": []}}})
    with pytest.raises(sh.core.SeparadorError, match="drop-off"):
        sh.organizar_envio({}, "TOK", "A1")


# ----------------------------------------------------- imprimir grupo / estado
def _grupo(chave="A01", ids=("SN1", "SN2"), dia=""):
    g = sh.core.Grupo(chave=chave, nome=chave, quantidade=1, shipment_ids=list(ids))
    g.dia = dia
    return g


def test_marcar_impresso_namespaceia_por_dia(monkeypatch):
    monkeypatch.setattr(sh, "salvar_estado", lambda estado: None)
    estado = {}
    g = _grupo(dia="2026-06-25")
    sh.marcar_impresso(estado, g, ["SN1"])
    assert estado["2026-06-25|A01|q1"] == ["SN1"]


def test_imprimir_grupo_organiza_gera_marca(monkeypatch):
    chamadas = {"organizar": [], "salvou": []}
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "organizar_envio",
                        lambda c, t, sn, **k: chamadas["organizar"].append(sn))
    monkeypatch.setattr(sh, "gerar_etiqueta", lambda c, ids, **k: b"PK\x03\x04")
    monkeypatch.setattr(sh, "salvar_etiqueta",
                        lambda conteudo, rotulo: chamadas["salvou"].append(rotulo) or ("p", "ZIP"))
    monkeypatch.setattr(sh, "salvar_estado", lambda estado: None)
    estado = {}
    g = _grupo(dia="2026-06-25")
    impressos = sh.imprimir_grupo({}, g, estado)
    assert impressos == ["SN1", "SN2"]
    assert chamadas["organizar"] == ["SN1", "SN2"]          # organizou os dois
    assert estado["2026-06-25|A01|q1"] == ["SN1", "SN2"]    # marcou impresso


def test_imprimir_grupo_pula_ja_impressos(monkeypatch):
    monkeypatch.setattr(sh, "gerar_etiqueta",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("nao gerar")))
    g = _grupo(dia="2026-06-25")
    estado = {"2026-06-25|A01|q1": ["SN1", "SN2"]}          # tudo ja impresso
    assert sh.imprimir_grupo({}, g, estado) == []


def test_imprimir_lotes_nao_marca_estado(monkeypatch):
    # lotes geram/imprimem mas NAO marcam — a GUI marca apos a confirmacao
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "organizar_envio", lambda c, t, sn, **k: True)
    monkeypatch.setattr(sh, "gerar_etiqueta", lambda c, ids, **k: b"PK\x03\x04")
    monkeypatch.setattr(sh, "salvar_etiqueta", lambda conteudo, rotulo: ("p", "ZIP"))
    monkeypatch.setattr(sh, "salvar_estado",
                        lambda estado: (_ for _ in ()).throw(AssertionError("nao marcar")))
    estado = {}
    g = _grupo(dia="2026-06-25")
    impressos = sh.imprimir_lotes({}, [g], estado)
    assert impressos == [(g, ["SN1", "SN2"])]
    assert estado == {}                                    # nada marcado
