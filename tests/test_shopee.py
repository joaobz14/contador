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


def test_salvar_etiqueta_atomico_sem_tmp_sobrando(monkeypatch, tmp_path):
    # Grava em .tmp e renomeia: o monitor da Zebra nunca ve o arquivo pela metade.
    monkeypatch.setattr(sh.core, "PASTA_DOWNLOADS", tmp_path)
    destino, fmt = sh.salvar_etiqueta(b"PK\x03\x04conteudo", "SN123")
    assert fmt == "ZIP" and destino.read_bytes() == b"PK\x03\x04conteudo"
    assert destino.name == "etiqueta shopee - SN123.zip"
    assert not list(tmp_path.glob("*.tmp"))            # nao deixa lixo .tmp


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


def test_gerar_etiqueta_espera_todos_os_pedidos_ready(monkeypatch):
    # so baixa quando A E B estao READY; um subconjunto nao basta
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "criar_documento", lambda *a, **k: {})
    monkeypatch.setattr(sh, "baixar_documento", lambda c, t, ids, tipo=sh.TIPO_ETIQUETA: b"PKzip")
    monkeypatch.setattr(sh.time, "sleep", lambda *_a, **_k: None)
    seq = iter([
        {"response": {"result_list": [{"order_sn": "A", "status": "READY"}]}},   # B ausente
        {"response": {"result_list": [{"order_sn": "A", "status": "READY"},
                                      {"order_sn": "B", "status": "READY"}]}},
    ])
    monkeypatch.setattr(sh, "resultado_documento", lambda *a, **k: next(seq))
    out = sh.gerar_etiqueta({"x": 1}, ["A", "B"], rastreios={"A": "x", "B": "y"})
    assert out == b"PKzip"


def test_gerar_etiqueta_fatia_em_blocos_de_50(monkeypatch):
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    chamadas = []
    monkeypatch.setattr(sh, "_gerar_bloco",
                        lambda cred, token, sns, tipo, r, t, e: chamadas.append(list(sns)) or b"PKz")
    monkeypatch.setattr(sh, "_combinar_etiquetas", lambda zips: b"COMBINED")
    sns = [f"S{i}" for i in range(120)]
    out = sh.gerar_etiqueta({"x": 1}, sns, rastreios={s: f"BR{s}" for s in sns})
    assert [len(c) for c in chamadas] == [50, 50, 20]     # fatiou em 50/50/20
    assert out == b"COMBINED"                             # varios blocos -> combinou


def test_gerar_etiqueta_um_bloco_nao_combina(monkeypatch):
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "_gerar_bloco", lambda *a: b"PKsingle")
    monkeypatch.setattr(sh, "_combinar_etiquetas",
                        lambda zips: (_ for _ in ()).throw(AssertionError("nao combinar")))
    out = sh.gerar_etiqueta({"x": 1}, ["A", "B"], rastreios={"A": "x", "B": "y"})
    assert out == b"PKsingle"                             # 1 bloco -> retorna direto


def test_gerar_etiqueta_aborta_se_algum_falhou(monkeypatch):
    import pytest
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "criar_documento", lambda *a, **k: {})
    monkeypatch.setattr(sh, "baixar_documento",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("nao baixar")))
    monkeypatch.setattr(sh.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(sh, "resultado_documento", lambda *a, **k:
                        {"response": {"result_list": [{"order_sn": "A", "status": "READY"},
                                                      {"order_sn": "B", "status": "FAILED"}]}})
    with pytest.raises(sh.core.SeparadorError):
        sh.gerar_etiqueta({"x": 1}, ["A", "B"], rastreios={"A": "x", "B": "y"})


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


def test_contagem_por_dia_inclui_fim_de_semana_e_sem_data():
    from datetime import datetime
    sab = int(datetime.fromisoformat("2026-07-04T12:00:00-03:00").timestamp())  # sabado
    seg = int(datetime.fromisoformat("2026-07-06T12:00:00-03:00").timestamp())
    det = [
        {"order_sn": "A", "ship_by_date": sab},
        {"order_sn": "B", "ship_by_date": sab},
        {"order_sn": "C", "ship_by_date": seg},
        {"order_sn": "D"},                                  # sem ship_by_date
    ]
    # datas de fim de semana e "sem data" contam — o seletor da GUI as expoe
    assert sh.contagem_por_dia(det) == {"2026-07-04": 2, "2026-07-06": 1, "": 1}


def test_coletar_grupos_devolve_contagem_da_mesma_busca(monkeypatch):
    from datetime import datetime
    seg = int(datetime.fromisoformat("2026-07-06T12:00:00-03:00").timestamp())
    det = [{"order_sn": "A1", "ship_by_date": seg,
            "item_list": [{"model_sku": "PRP", "model_quantity_purchased": 1}]}]
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "listar_order_sns", lambda c, t: ["A1"])
    monkeypatch.setattr(sh, "buscar_detalhes", lambda c, t, sns: det)
    monkeypatch.setattr(sh.core, "carregar_nomes", lambda: {})
    grupos, qtd, contagem = sh.coletar_grupos({}, dia="2026-07-06", somente_hoje=False)
    assert [g.chave for g in grupos] == ["PRP"] and qtd == 1
    assert contagem == {"2026-07-06": 1}                    # sem rede extra


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


def _forca_individual(monkeypatch):
    """Leva _organizar_varios direto ao caminho individual (sem AWB previo e sem
    batch), preservando a semantica dos testes escritos antes do batch_ship_order."""
    monkeypatch.setattr(sh, "_rastreios_paralelo",
                        lambda c, t, sns: {str(s): "" for s in sns})
    monkeypatch.setattr(sh, "batch_ship_order",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sem batch")))


def test_marcar_impresso_namespaceia_por_dia(monkeypatch):
    monkeypatch.setattr(sh, "salvar_estado", lambda estado: None)
    estado = {}
    g = _grupo(dia="2026-06-25")
    sh.marcar_impresso(estado, g, ["SN1"])
    assert estado["2026-06-25|A01|q1"] == ["SN1"]


def test_imprimir_grupo_organiza_gera_marca(monkeypatch):
    chamadas = {"organizar": [], "salvou": []}
    _forca_individual(monkeypatch)
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
    assert sorted(chamadas["organizar"]) == ["SN1", "SN2"]  # organizou os dois (em paralelo)
    assert estado["2026-06-25|A01|q1"] == ["SN1", "SN2"]    # marcou impresso


def test_imprimir_grupo_pula_ja_impressos(monkeypatch):
    monkeypatch.setattr(sh, "gerar_etiqueta",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("nao gerar")))
    g = _grupo(dia="2026-06-25")
    estado = {"2026-06-25|A01|q1": ["SN1", "SN2"]}          # tudo ja impresso
    assert sh.imprimir_grupo({}, g, estado) == []


def test_preencher_rastreios_lista_todos_os_impressos(monkeypatch):
    def g(chave, ids):
        x = sh.core.Grupo(chave=chave, nome=chave, quantidade=1, shipment_ids=list(ids))
        x.dia = "2026-06-25"
        return x
    g1, g2, g3, g4 = (g("A", ["SN1"]), g("B", ["SN2", "SN3"]),
                      g("C", ["SN4"]), g("D", ["SN5", "SN6"]))
    estado = {"2026-06-25|A|q1": ["SN1"],            # unico + impresso
              "2026-06-25|B|q1": ["SN2", "SN3"],     # varios + todos impressos
              "2026-06-25|D|q1": ["SN5"]}            # parcial (so SN5 impresso)
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "numero_rastreio", lambda c, t, sn: f"BR-{sn}")
    sh.preencher_rastreios({}, [g1, g2, g3, g4], estado)
    assert g1.rastreios == ["BR-SN1"]                # 1 impresso
    assert g2.rastreios == ["BR-SN2", "BR-SN3"]      # varios impressos -> lista todos
    assert g3.rastreios == []                        # pendente (sem AWB) -> nada
    assert g4.rastreios == ["BR-SN5"]                # parcial -> so o ja impresso


def test_imprimir_lotes_nao_marca_estado(monkeypatch):
    # lotes geram/imprimem mas NAO marcam — a GUI marca apos a confirmacao
    _forca_individual(monkeypatch)
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "organizar_envio", lambda c, t, sn, **k: True)
    monkeypatch.setattr(sh, "gerar_etiqueta", lambda c, ids, **k: b"PK\x03\x04")
    monkeypatch.setattr(sh, "salvar_etiqueta", lambda conteudo, rotulo: ("p", "ZIP"))
    monkeypatch.setattr(sh, "salvar_estado",
                        lambda estado: (_ for _ in ()).throw(AssertionError("nao marcar")))
    estado = {}
    g = _grupo(dia="2026-06-25")
    impressos, falhas = sh.imprimir_lotes({}, [g], estado)
    assert impressos == [(g, ["SN1", "SN2"])]
    assert falhas == []
    assert estado == {}                                    # nada marcado


def test_imprimir_lotes_gera_um_unico_zip(monkeypatch):
    # Um documento POR PEDIDO (em paralelo), combinados num UNICO zip (Zebra sem gap).
    chamadas = {"gerou": [], "salvou": 0}
    _forca_individual(monkeypatch)
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "organizar_envio", lambda c, t, sn, **k: f"BR-{sn}")

    def fake_gerar(c, ids, **k):
        chamadas["gerou"].append(list(ids))
        return b"PK-" + str(ids[0]).encode()

    monkeypatch.setattr(sh, "gerar_etiqueta", fake_gerar)
    monkeypatch.setattr(sh, "_combinar_etiquetas", lambda zips: b"COMBINADO")
    monkeypatch.setattr(sh, "salvar_etiqueta",
                        lambda conteudo, rotulo: chamadas.update(salvou=chamadas["salvou"] + 1) or ("p", "ZIP"))
    g1 = _grupo("A", ids=["SN1"], dia="2026-06-25")
    g2 = _grupo("B", ids=["SN2", "SN3"], dia="2026-06-25")
    impressos, falhas = sh.imprimir_lotes({}, [g1, g2], {})
    assert chamadas["salvou"] == 1                          # UM zip so (combinado)
    assert sorted(c[0] for c in chamadas["gerou"]) == ["SN1", "SN2", "SN3"]  # 1 doc por pedido
    assert impressos == [(g1, ["SN1"]), (g2, ["SN2", "SN3"])]
    assert falhas == []
    # Todos os grupos levam os AWBs recem-impressos (para a tela conferir),
    # inclusive os de varios pedidos.
    assert g1.rastreios == ["BR-SN1"]
    assert g2.rastreios == ["BR-SN2", "BR-SN3"]


def test_combinar_etiquetas_junta_zpl_num_unico_zip():
    import io
    import zipfile

    def _zip(texto):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("thermal_zpl_shipping_label.txt", texto)
        return buf.getvalue()

    out = sh._combinar_etiquetas([_zip("~DGR:A ^XA a ^XZ"), _zip("~DGR:B ^XA b ^XZ")])
    with zipfile.ZipFile(io.BytesIO(out)) as z:
        nomes = z.namelist()
        conteudo = z.read(nomes[0]).decode()
    assert len(nomes) == 1                                  # um TXT so
    assert "~DGR:A" in conteudo and "~DGR:B" in conteudo    # as duas etiquetas
    assert "thermal_zpl_shipping_label" in nomes[0]         # nome que a Zebra reconhece


def test_imprimir_lotes_tolera_falha_parcial(monkeypatch):
    # SN2 nao organiza -> entra em falhas; SN1 e SN3 imprimem num zip so.
    _forca_individual(monkeypatch)
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")

    def fake_org(c, t, sn, **k):
        if sn == "SN2":
            raise sh.core.SeparadorError("rastreio (AWB) nao saiu")
        return f"BR-{sn}"

    gerou = []
    monkeypatch.setattr(sh, "organizar_envio", fake_org)
    monkeypatch.setattr(sh, "gerar_etiqueta",
                        lambda c, ids, **k: gerou.append(ids[0]) or (b"PK-" + ids[0].encode()))
    monkeypatch.setattr(sh, "_combinar_etiquetas", lambda zips: b"COMBINADO")
    monkeypatch.setattr(sh, "salvar_etiqueta", lambda conteudo, rotulo: ("p", "ZIP"))
    g1 = _grupo("A", ids=["SN1"], dia="2026-06-25")
    g2 = _grupo("B", ids=["SN2"], dia="2026-06-25")
    g3 = _grupo("C", ids=["SN3"], dia="2026-06-25")
    impressos, falhas = sh.imprimir_lotes({}, [g1, g2, g3], {})
    assert sorted(gerou) == ["SN1", "SN3"]                 # gerou so os que deram (1 por pedido)
    assert impressos == [(g1, ["SN1"]), (g3, ["SN3"])]     # g2 ficou de fora
    assert [sn for sn, _ in falhas] == ["SN2"]             # e foi reportado


# ------------------------------------------- organizar em lote (batch_ship_order)
def test_batch_ship_order_monta_o_corpo(monkeypatch):
    capt = {}
    monkeypatch.setattr(sh, "_post_shop",
                        lambda c, t, path, body: capt.update(path=path, body=body) or {})
    sh.batch_ship_order({}, "TOK", ["S1", "S2"], dropoff={})
    assert capt["path"].endswith("/batch_ship_order")
    assert capt["body"] == {"order_list": [{"order_sn": "S1"}, {"order_sn": "S2"}],
                            "dropoff": {}}


def test_organizar_varios_via_batch_sem_individual(monkeypatch):
    # rodada 1 (idempotencia): ninguem tem AWB; rodada 2 (apos o batch): todos tem
    seq = iter([{"S1": "", "S2": ""}, {"S1": "BR1", "S2": "BR2"}])
    monkeypatch.setattr(sh, "_rastreios_paralelo",
                        lambda c, t, sns: {k: v for k, v in next(seq).items() if k in sns})
    batches = []
    monkeypatch.setattr(sh, "batch_ship_order",
                        lambda c, t, sns, dropoff=None: batches.append(list(sns)) or {})
    monkeypatch.setattr(sh.time, "sleep", lambda *_: None)
    monkeypatch.setattr(sh, "organizar_envio",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("individual nao devia rodar")))
    ok, falhas = sh._organizar_varios({}, "TOK", ["S1", "S2"])
    assert ok == {"S1": "BR1", "S2": "BR2"} and falhas == []
    assert batches == [["S1", "S2"]]              # UM request para os dois


def test_organizar_varios_idempotente_nem_chama_batch(monkeypatch):
    monkeypatch.setattr(sh, "_rastreios_paralelo", lambda c, t, sns: {"S1": "BR1"})
    monkeypatch.setattr(sh, "batch_ship_order",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("nada a organizar")))
    ok, falhas = sh._organizar_varios({}, "TOK", ["S1"])
    assert ok == {"S1": "BR1"} and falhas == []


def test_organizar_varios_batch_indisponivel_cai_no_individual(monkeypatch):
    # endpoint falhou por inteiro -> NAO fica esperando AWB; vai direto pro individual
    monkeypatch.setattr(sh, "_rastreios_paralelo", lambda c, t, sns: {s: "" for s in sns})
    monkeypatch.setattr(sh, "batch_ship_order",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("endpoint fora")))
    esperas = []
    monkeypatch.setattr(sh.time, "sleep", lambda s: esperas.append(s))
    monkeypatch.setattr(sh, "organizar_envio", lambda c, t, sn, **k: f"BR-{sn}")
    ok, falhas = sh._organizar_varios({}, "TOK", ["S1", "S2"])
    assert ok == {"S1": "BR-S1", "S2": "BR-S2"} and falhas == []
    assert esperas == []                          # sem polling inutil


def test_organizar_varios_awb_que_nao_sai_cai_no_individual(monkeypatch):
    # batch "passa", mas o AWB de S2 nunca sai -> SO S2 vai pro individual
    monkeypatch.setattr(sh, "_rastreios_paralelo",
                        lambda c, t, sns: {s: ("BR1" if s == "S1" else "") for s in sns})
    monkeypatch.setattr(sh, "batch_ship_order", lambda c, t, sns, dropoff=None: {})
    monkeypatch.setattr(sh.time, "sleep", lambda *_: None)
    chamados = []
    monkeypatch.setattr(sh, "organizar_envio",
                        lambda c, t, sn, **k: chamados.append(sn) or f"BRX-{sn}")
    ok, falhas = sh._organizar_varios({}, "TOK", ["S1", "S2"])
    assert ok == {"S1": "BR1", "S2": "BRX-S2"} and falhas == []
    assert chamados == ["S2"]                     # S1 (idempotente) nem e tocado


def test_organizar_varios_dropoff_leva_branch_e_remetente(monkeypatch):
    capt = {}
    monkeypatch.setattr(sh, "_rastreios_paralelo", lambda c, t, sns: {s: "" for s in sns})
    monkeypatch.setattr(sh, "batch_ship_order",
                        lambda c, t, sns, dropoff=None: capt.update(dropoff=dropoff) or {})
    monkeypatch.setattr(sh.time, "sleep", lambda *_: None)
    monkeypatch.setattr(sh, "organizar_envio", lambda c, t, sn, **k: "BR")
    sh._organizar_varios({}, "TOK", ["S1"], branch_id=77, sender_real_name="Joao")
    assert capt["dropoff"] == {"branch_id": 77, "sender_real_name": "Joao"}


# --------------------------------------------------- cronometragem (diagnostico)
def test_log_tempos_registra_as_fases(monkeypatch, tmp_path):
    arq = tmp_path / "tempos.log"
    monkeypatch.setattr(sh, "ARQUIVO_TEMPOS", arq)
    sh._log_tempos(25, 8.2, 4.1, contexto="lote")
    linha = arq.read_text(encoding="utf-8")
    assert "25 pedido(s)" in linha
    assert "organizar   8.2s" in linha and "gerar+baixar   4.1s" in linha
    assert "total  12.3s" in linha


def test_log_tempos_nunca_levanta(monkeypatch):
    # diagnostico nao pode atrapalhar a impressao: falha de IO e engolida
    monkeypatch.setattr(sh, "ARQUIVO_TEMPOS", sh.core.Path("/caminho/inexistente/x.log"))
    sh._log_tempos(1, 1.0, 1.0)          # nao deve levantar


def test_imprimir_lotes_cronometra(monkeypatch, tmp_path):
    _forca_individual(monkeypatch)
    arq = tmp_path / "tempos.log"
    monkeypatch.setattr(sh, "ARQUIVO_TEMPOS", arq)
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "organizar_envio", lambda c, t, sn, **k: f"BR-{sn}")
    monkeypatch.setattr(sh, "gerar_etiqueta", lambda c, ids, **k: b"PK\x03\x04")
    monkeypatch.setattr(sh, "salvar_etiqueta", lambda conteudo, rotulo: ("p", "ZIP"))
    g = _grupo("A", ids=["SN1"], dia="2026-06-25")
    sh.imprimir_lotes({}, [g], {})
    assert "1 pedido(s)" in arq.read_text(encoding="utf-8")   # registrou o tempo


def test_gerar_lote_paraleliza_por_pedido_e_isola_falha(monkeypatch):
    # gera 1 doc por pedido; um que falha nao derruba os outros; combina o resto.
    def fake_gerar(c, ids, **k):
        if ids[0] == "B":
            raise sh.core.SeparadorError("documento falhou")
        return b"PK-" + ids[0].encode()
    monkeypatch.setattr(sh, "gerar_etiqueta", fake_gerar)
    monkeypatch.setattr(sh, "_combinar_etiquetas",
                        lambda zips: b"COMBINADO(" + b"+".join(zips) + b")")
    conteudo, sns_ok, falhas = sh._gerar_lote({}, "TOK", ["A", "B", "C"],
                                              {"A": "x", "B": "y", "C": "z"})
    assert sns_ok == ["A", "C"]                        # B fora, ordem preservada
    assert [sn for sn, _ in falhas] == ["B"]
    assert conteudo == b"COMBINADO(PK-A+PK-C)"         # combinou os que deram


def test_gerar_lote_um_pedido_nao_combina(monkeypatch):
    monkeypatch.setattr(sh, "gerar_etiqueta", lambda c, ids, **k: b"PKsozinho")
    monkeypatch.setattr(sh, "_combinar_etiquetas",
                        lambda zips: (_ for _ in ()).throw(AssertionError("nao combinar 1 so")))
    conteudo, sns_ok, falhas = sh._gerar_lote({}, "TOK", ["A"], {"A": "x"})
    assert conteudo == b"PKsozinho" and sns_ok == ["A"] and falhas == []


# ------------------------------------------ erro HTTP nao vaza o token (seguranca)
class _RespErro:
    """Resposta HTTP >= 400 com corpo JSON de erro (simula a Shopee)."""
    def __init__(self, status=403, corpo=None):
        self.status_code = status
        self._corpo = corpo if corpo is not None else {"error": "error_auth",
                                                        "message": "Invalid access_token."}
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        return self._corpo

    def raise_for_status(self):
        raise AssertionError("nao deve chamar raise_for_status (vaza a URL com o token)")


def test_get_shop_erro_http_nao_vaza_access_token(monkeypatch):
    cred = {"partner_id": 1, "partner_key": "k", "shop_id": 2}
    # o core devolve uma resposta 403 (o token/sign estariam na URL, nao aqui)
    monkeypatch.setattr(sh.core, "_requisicao_get", lambda *a, **k: _RespErro())
    try:
        sh._get_shop(cred, "TOKEN_SUPER_SECRETO", "/api/v2/order/get", {"order_sn": "A1"})
        assert False, "deveria ter levantado"
    except sh.core.SeparadorError as e:
        msg = str(e)
        assert "TOKEN_SUPER_SECRETO" not in msg      # o token NUNCA aparece
        assert "access_token" not in msg or "access_token=" not in msg
        assert "HTTP 403" in msg                      # mas o diagnostico util fica
        assert "/api/v2/order/get" in msg


def test_post_shop_erro_http_vira_separadorerror_limpo(monkeypatch):
    monkeypatch.setattr(sh.core, "_requisicao_post", lambda *a, **k: _RespErro(status=500, corpo={}))
    try:
        sh._post_shop({"partner_id": 1, "partner_key": "k", "shop_id": 2},
                      "TOKEN_X", "/api/v2/logistics/ship_order", {"order_sn": "A1"})
        assert False
    except sh.core.SeparadorError as e:
        assert "TOKEN_X" not in str(e) and "HTTP 500" in str(e)


# ------------------------------------------ token: adota o do disco (GUI+bot mesma loja)
def test_obter_token_shopee_rele_o_disco_dentro_da_trava(monkeypatch, tmp_path):
    """Mesma protecao do nucleo: a releitura do disco acontece DENTRO da trava
    de arquivo — se outro processo terminou o refresh enquanto esperavamos
    (simulado pelo context manager injetado), adota o token dele em vez de
    gastar outro refresh."""
    import contextlib
    import time as _t

    arq = tmp_path / "credenciais_shopee.json"
    monkeypatch.setattr(sh, "ARQUIVO_CRED", arq)
    sh.core._gravar_json(arq, {"access_token": "", "access_token_exp": 0,
                               "refresh_token": "R1"})
    monkeypatch.setattr(sh, "renovar_token",
                        lambda c: (_ for _ in ()).throw(AssertionError("nao renovar")))

    @contextlib.contextmanager
    def trava_simulada(caminho):
        assert caminho == arq
        sh.core._gravar_json(arq, {"access_token": "DO_OUTRO",
                                   "access_token_exp": _t.time() + 9999,
                                   "refresh_token": "R2"})
        yield

    monkeypatch.setattr(sh._estado, "trava", trava_simulada)
    cred = {"access_token": "VELHO", "access_token_exp": 0, "refresh_token": "R1"}
    assert sh.obter_token(cred) == "DO_OUTRO"
    assert cred["refresh_token"] == "R2"


def test_obter_token_shopee_adota_token_do_disco(monkeypatch, tmp_path):
    """Se outro processo (bot vs app) ja renovou o token da loja e salvou,
    obter_token adota o do disco em vez de renovar (evita corrida no refresh)."""
    import time as _t
    arq = tmp_path / "credenciais_shopee.json"
    monkeypatch.setattr(sh, "ARQUIVO_CRED", arq)
    sh.core._gravar_json(arq, {"access_token": "DISCO", "access_token_exp": _t.time() + 9999,
                               "refresh_token": "RN", "partner_id": 1, "shop_id": 2})
    monkeypatch.setattr(sh, "renovar_token",
                        lambda c: (_ for _ in ()).throw(AssertionError("nao deve renovar")))
    cred = {"access_token": "VELHO", "access_token_exp": 0, "refresh_token": "RV"}
    assert sh.obter_token(cred) == "DISCO"
    assert cred["refresh_token"] == "RN"


# ---------------------------------------------------------------------------
# FALHA DE TRANSPORTE NAO PODE VAZAR O TOKEN (complementa o erro HTTP seguro)
# ---------------------------------------------------------------------------
import pytest  # noqa: E402

URL_ASSINADA = ("Max retries exceeded with url: /api/v2/x?partner_id=1"
                "&access_token=SEGREDO123&shop_id=2&sign=ASSINATURA456")


def _levanta_conexao(*a, **k):
    import requests
    raise requests.ConnectionError(URL_ASSINADA)


@pytest.mark.parametrize("chamar", [
    lambda: sh._get_shop({"partner_id": "1", "partner_key": "k", "shop_id": "2"},
                         "TOK", "/api/v2/x", {}),
    lambda: sh._post_shop({"partner_id": "1", "partner_key": "k", "shop_id": "2"},
                          "TOK", "/api/v2/x", {}),
    lambda: sh._download_shop({"partner_id": "1", "partner_key": "k", "shop_id": "2"},
                              "TOK", "/api/v2/x", {}),
])
def test_falha_de_transporte_vira_erro_limpo(monkeypatch, chamar):
    monkeypatch.setattr(sh.core, "_requisicao_get", _levanta_conexao)
    monkeypatch.setattr(sh.core, "_requisicao_post", _levanta_conexao)
    with pytest.raises(sh.core.SeparadorError) as exc:
        chamar()
    msg = str(exc.value)
    assert "SEGREDO123" not in msg and "ASSINATURA456" not in msg
    assert "/api/v2/x" in msg and "rede" in msg
    # O encadeamento e cortado (from None): um traceback logado (ex.:
    # log.exception do bot) nao arrasta a excecao original com a URL.
    assert exc.value.__suppress_context__ is True


def test_renovar_token_falha_de_transporte_limpa(monkeypatch):
    monkeypatch.setattr(sh.core, "_requisicao_post", _levanta_conexao)
    cred = {"partner_id": "1", "partner_key": "k", "shop_id": "2",
            "refresh_token": "R", "access_token": "", "access_token_exp": 0}
    with pytest.raises(sh.core.SeparadorError) as exc:
        sh.renovar_token(cred)
    msg = str(exc.value)
    assert "SEGREDO123" not in msg and "ASSINATURA456" not in msg


def test_falha_de_transporte_no_traceback_nao_tem_url(monkeypatch):
    """O texto completo do traceback (o que um log.exception gravaria) nao pode
    conter a URL assinada — e o que protege o bot.log."""
    import traceback
    monkeypatch.setattr(sh.core, "_requisicao_get", _levanta_conexao)
    try:
        sh._get_shop({"partner_id": "1", "partner_key": "k", "shop_id": "2"},
                     "TOK", "/api/v2/x", {})
    except sh.core.SeparadorError as e:
        texto = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        assert "SEGREDO123" not in texto and "ASSINATURA456" not in texto
    else:
        raise AssertionError("nao levantou")
# AWB NA IMPRESSAO PARCIAL: une aos ja exibidos (nao substitui) — revisao P2
# ---------------------------------------------------------------------------
def test_somar_rastreios_une_sem_duplicar_preservando_ordem():
    g = _grupo("A", ids=["SN1", "SN2", "SN3"], dia="2026-07-15")
    g.rastreios = ["BR-A"]
    sh._somar_rastreios(g, ["BR-B", "", "BR-A", "BR-C"])   # vazio e duplicado fora
    assert g.rastreios == ["BR-A", "BR-B", "BR-C"]


def test_imprimir_lotes_parcial_preserva_awbs_antigos(monkeypatch):
    """Grupo parcial: SN1 ja impresso (AWB antigo na tela) + SN2 pendente.
    Imprimir o pendente NAO pode apagar o codigo antigo da lista."""
    _forca_individual(monkeypatch)
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "organizar_envio", lambda c, t, sn, **k: f"BR-{sn}")
    monkeypatch.setattr(sh, "gerar_etiqueta", lambda c, ids, **k: b"PK")
    monkeypatch.setattr(sh, "salvar_etiqueta", lambda conteudo, rotulo: ("p", "ZIP"))
    g = _grupo("A", ids=["SN1", "SN2"], dia="2026-07-15")
    g.rastreios = ["BR-SN1"]                       # da coleta (SN1 ja impresso)
    estado = {"2026-07-15|A|q1": ["SN1"]}          # parcial: falta SN2
    impressos, falhas = sh.imprimir_lotes({}, [g], estado)
    assert impressos == [(g, ["SN2"])] and falhas == []
    assert g.rastreios == ["BR-SN1", "BR-SN2"]     # antigo + novo (uniao)


def test_imprimir_grupo_parcial_preserva_awbs_antigos(monkeypatch):
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "_organizar_varios",
                        lambda c, t, sns, **k: ({sn: f"BR-{sn}" for sn in sns}, []))
    monkeypatch.setattr(sh, "gerar_etiqueta", lambda c, ids, **k: b"PK")
    monkeypatch.setattr(sh, "salvar_etiqueta", lambda conteudo, rotulo: ("p", "ZIP"))
    monkeypatch.setattr(sh, "marcar_impresso", lambda e, g, ids: None)
    g = _grupo("B", ids=["SN1", "SN2"], dia="2026-07-15")
    g.rastreios = ["BR-SN1"]
    estado = {"2026-07-15|B|q1": ["SN1"]}
    out = sh.imprimir_grupo({}, g, estado)
    assert out == ["SN2"]
    assert g.rastreios == ["BR-SN1", "BR-SN2"]
