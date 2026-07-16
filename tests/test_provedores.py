"""Camada de provedor (marketplace) — sem rede."""
import provedores as pv
import shopee_api as sh


def test_criar_provedor_por_nome():
    assert isinstance(pv.criar_provedor("shopee"), pv.ProvedorShopee)
    assert isinstance(pv.criar_provedor("Shopee"), pv.ProvedorShopee)
    assert isinstance(pv.criar_provedor("Mercado Livre"), pv.ProvedorML)
    assert isinstance(pv.criar_provedor(""), pv.ProvedorML)


def test_capacidades_por_provedor():
    ml = pv.ProvedorML()
    sho = pv.ProvedorShopee()
    # ML tem contas e identificacao; nao organiza envio.
    assert ml.suporta_contas and ml.suporta_identificacao and not ml.organiza_envio
    # Shopee organiza envio; nao tem sub-contas nem identificacao.
    assert sho.organiza_envio and not sho.suporta_contas and not sho.suporta_identificacao
    assert sho.contas() == []


def test_ml_coletar_delega_ao_nucleo(monkeypatch):
    import separador_etiquetas_ml as core
    monkeypatch.setattr(core, "carregar_credenciais", lambda: {"seller_id": 9})
    monkeypatch.setattr(core, "renovar_token", lambda cred: "TOK")
    capturado = {}

    class FakeColeta:
        grupos = ["g1", "g2"]
        # 2 pedidos na quarta, 1 num sabado e 1 sem data de despacho
        prontos = [
            {"_envio": {"expected_date": "2026-06-24"}},
            {"_envio": {"expected_date": "2026-06-24"}},
            {"_envio": {"expected_date": "2026-06-27"}},
            {"_envio": {"expected_date": ""}},
        ]

    def fake_coletar(token, seller, *, dia, somente_hoje, progresso):
        capturado.update(token=token, seller=seller, dia=dia)
        return FakeColeta()

    monkeypatch.setattr(core, "coletar_grupos", fake_coletar)
    prov = pv.ProvedorML()
    grupos = prov.coletar(dia="2026-06-25", somente_hoje=False)
    assert grupos == ["g1", "g2"]
    assert capturado == {"token": "TOK", "seller": 9, "dia": "2026-06-25"}
    # contagem por dia vem da MESMA coleta; "(sem data)" normalizado para ""
    assert prov.contagem_dias == {"2026-06-24": 2, "2026-06-27": 1, "": 1}


def test_shopee_coletar_guarda_contagem(monkeypatch):
    prov = pv.ProvedorShopee()
    prov.cred = {"x": 1}
    monkeypatch.setattr(sh, "coletar_grupos",
                        lambda cred, *, dia, somente_hoje: (["g"], 1, {"2026-07-04": 3}))
    monkeypatch.setattr(sh, "carregar_estado", lambda: {})
    monkeypatch.setattr(sh, "preencher_rastreios", lambda cred, grupos, estado: None)
    assert prov.coletar(dia="2026-07-04", somente_hoje=False) == ["g"]
    assert prov.contagem_dias == {"2026-07-04": 3}


def test_shopee_imprimir_grupo_delega(monkeypatch):
    prov = pv.ProvedorShopee()
    prov.cred = {"x": 1}
    capturado = {}
    monkeypatch.setattr(sh, "imprimir_grupo",
                        lambda cred, grupo, estado, **k: capturado.update(k=k) or ["SN1"])
    assert prov.imprimir_grupo("G", {}) == ["SN1"]
    # repassa o setup unico (ponto/remetente) para o shopee_api
    assert "branch_id" in capturado["k"] and "sender_real_name" in capturado["k"]


def test_ml_imprimir_revalida_o_token_da_coleta(monkeypatch):
    """self.token vem da ultima coleta e pode ter EXPIRADO (GUI aberta por
    horas): imprimir/reimprimir revalidam via obter_token em vez de reusar o
    token cru — senao o 401 se repetiria ate um novo Atualizar."""
    import separador_etiquetas_ml as core
    prov = pv.ProvedorML()
    prov.cred = {"access_token": "VELHO", "access_token_exp": 0}
    prov.token = "VELHO"                        # cache da coleta, ja vencido
    monkeypatch.setattr(core, "obter_token", lambda cred: "FRESCO")
    usado = {}
    monkeypatch.setattr(core, "gerar_zip_lotes",
                        lambda token, grupos, estado, **k: usado.update(lotes=token) or [])
    monkeypatch.setattr(core, "reimprimir",
                        lambda token, g: usado.update(reimp=token) or [])
    monkeypatch.setattr(core, "imprimir_pendentes",
                        lambda token, g, e: usado.update(grupo=token) or [])
    prov.imprimir_lotes([], {})
    prov.reimprimir("g")
    prov.imprimir_grupo("g", {})
    assert usado == {"lotes": "FRESCO", "reimp": "FRESCO", "grupo": "FRESCO"}
    assert prov.token == "FRESCO"               # cache atualizado de quebra


def test_ml_imprimir_sem_coleta_previa_carrega_credenciais(monkeypatch):
    """Imprimir sem nunca ter coletado (cred None) carrega as credenciais."""
    import separador_etiquetas_ml as core
    prov = pv.ProvedorML()
    monkeypatch.setattr(core, "carregar_credenciais", lambda: {"seller_id": 1})
    monkeypatch.setattr(core, "obter_token", lambda cred: "TOK")
    monkeypatch.setattr(core, "reimprimir", lambda token, g: [token])
    assert prov.reimprimir("g") == ["TOK"]
    assert prov.cred == {"seller_id": 1}


def test_marcar_impresso_vai_para_o_estado_certo(monkeypatch):
    # ML -> core.marcar_impresso ; Shopee -> shopee.marcar_impresso
    import separador_etiquetas_ml as core
    destino = {}
    monkeypatch.setattr(core, "marcar_impresso",
                        lambda estado, grupo, ids: destino.update(ml=ids))
    monkeypatch.setattr(sh, "marcar_impresso",
                        lambda estado, grupo, ids: destino.update(shopee=ids))
    pv.ProvedorML().marcar_impresso({}, "g", ["A"])
    pv.ProvedorShopee().marcar_impresso({}, "g", ["B"])
    assert destino == {"ml": ["A"], "shopee": ["B"]}
