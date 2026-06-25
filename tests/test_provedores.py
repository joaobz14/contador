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

    def fake_coletar(token, seller, *, dia, somente_hoje, progresso):
        capturado.update(token=token, seller=seller, dia=dia)
        return FakeColeta()

    monkeypatch.setattr(core, "coletar_grupos", fake_coletar)
    grupos = pv.ProvedorML().coletar(dia="2026-06-25", somente_hoje=False)
    assert grupos == ["g1", "g2"]
    assert capturado == {"token": "TOK", "seller": 9, "dia": "2026-06-25"}


def test_shopee_a_organizar_lista_pendentes_sem_awb(monkeypatch):
    g = sh.core.Grupo(chave="A01", nome="A01", quantidade=1, shipment_ids=["SN1", "SN2"])
    prov = pv.ProvedorShopee()
    prov.cred = {"x": 1}                                  # evita carregar credenciais
    # SN1 sem AWB, SN2 com AWB
    monkeypatch.setattr(sh, "obter_token", lambda c: "TOK")
    monkeypatch.setattr(sh, "numero_rastreio", lambda c, t, sn: "" if sn == "SN1" else "BR9")
    assert prov.a_organizar([g], {}) == ["SN1"]


def test_shopee_imprimir_grupo_delega(monkeypatch):
    prov = pv.ProvedorShopee()
    prov.cred = {"x": 1}
    capturado = {}
    monkeypatch.setattr(sh, "imprimir_grupo",
                        lambda cred, grupo, estado, **k: capturado.update(k=k) or ["SN1"])
    assert prov.imprimir_grupo("G", {}) == ["SN1"]
    # repassa o setup unico (ponto/remetente) para o shopee_api
    assert "branch_id" in capturado["k"] and "sender_real_name" in capturado["k"]
