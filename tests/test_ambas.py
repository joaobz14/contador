"""Modo "Ambas": fusao das contas ML num grupo por produto (dia de motorista unico)."""
import provedores as pv
import separador_etiquetas_ml as core


def _g(chave, qtd, ids, dia="2026-07-07", nome=None):
    return core.Grupo(chave=chave, nome=nome or chave, quantidade=qtd,
                      shipment_ids=list(ids), dia=dia)


# ------------------------------------------------------------------ fusao
def test_fundir_grupos_junta_por_sku_e_quantidade():
    fund = pv.fundir_grupos({
        "Gastromaq": [_g("A05F", 1, [1, 2]), _g("PRP", 2, [3])],
        "Cozilatti": [_g("A05F", 1, [10]), _g("MDH", 1, [11])],
    })
    por_chave = {(f.chave, f.quantidade): f for f in fund}
    f = por_chave[("A05F", 1)]
    assert sorted(f.shipment_ids) == [1, 2, 10]          # etiquetas das 2 contas
    assert set(f.por_conta) == {"Gastromaq", "Cozilatti"}
    assert f.total_etiquetas == 3
    # grupos sem par na outra conta tambem entram (com 1 conta so)
    assert ("PRP", 2) in por_chave and ("MDH", 1) in por_chave
    assert list(por_chave[("PRP", 2)].por_conta) == ["Gastromaq"]


def test_fundir_nao_mistura_quantidades_diferentes():
    fund = pv.fundir_grupos({"G": [_g("A", 1, [1])], "C": [_g("A", 2, [2])]})
    assert len(fund) == 2                                # A q1 e A q2 separados


# ------------------------------------------------------- estado composto
def test_status_e_pendentes_compostos():
    prov = pv.ProvedorMLAmbas()
    fund = pv.fundir_grupos({"G": [_g("A", 1, [1, 2])], "C": [_g("A", 1, [3])]})
    g = fund[0]
    estado = {"G": {}, "C": {}}
    assert prov.status_grupo(estado, g) == "pendente"
    assert sorted(prov.envios_pendentes(estado, g)) == [1, 2, 3]
    # a conta G ja foi impressa separada de manha -> grupo fica "parcial"
    estado["G"] = {core._chave_estado(g.por_conta["G"]): [1, 2]}
    assert sorted(prov.envios_pendentes(estado, g)) == [3]
    assert prov.status_grupo(estado, g) == "parcial"
    estado["C"] = {core._chave_estado(g.por_conta["C"]): [3]}
    assert prov.status_grupo(estado, g) == "impresso"


def test_marcar_impresso_grava_no_estado_da_conta_certa(monkeypatch):
    chamadas = []
    monkeypatch.setattr(core, "definir_conta", lambda c: chamadas.append(("conta", c)))
    monkeypatch.setattr(core, "marcar_impresso",
                        lambda estado, sub, ids: chamadas.append(("marca", sorted(ids))))
    prov = pv.ProvedorMLAmbas()
    fund = pv.fundir_grupos({"G": [_g("A", 1, [1, 2])], "C": [_g("A", 1, [3])]})
    prov.marcar_impresso({}, fund[0], [1, 2, 3])
    # cada conta marca APENAS os seus ids, e a troca de conta vem antes da marca
    assert chamadas == [("conta", "G"), ("marca", [1, 2]),
                        ("conta", "C"), ("marca", [3])]


def test_marcar_impresso_pula_conta_sem_ids(monkeypatch):
    trocas = []
    monkeypatch.setattr(core, "definir_conta", lambda c: trocas.append(c))
    monkeypatch.setattr(core, "marcar_impresso", lambda estado, sub, ids: None)
    prov = pv.ProvedorMLAmbas()
    fund = pv.fundir_grupos({"G": [_g("A", 1, [1])], "C": [_g("A", 1, [3])]})
    prov.marcar_impresso({}, fund[0], [3])               # so o pedido da C
    assert trocas == ["C"]                               # G nem e tocada


# ------------------------------------------------------------- impressao
def test_imprimir_lotes_um_zip_com_o_token_de_cada_conta(monkeypatch):
    prov = pv.ProvedorMLAmbas()
    monkeypatch.setattr(pv.ProvedorMLAmbas, "_token",
                        lambda self, conta: f"TOK-{conta}")
    baixadas = []

    def fake_baixar(token, ids):
        baixadas.append((token, sorted(ids)))
        return f"^XA {token} ^XZ"

    monkeypatch.setattr(core, "baixar_zpl", fake_baixar)
    zips = {}
    monkeypatch.setattr(core, "_gerar_zip",
                        lambda rotulo, zpl: zips.update(rotulo=rotulo, zpl=zpl))
    fund = pv.fundir_grupos({"G": [_g("A", 1, [1, 2])], "C": [_g("A", 1, [3])]})
    impressos, falhas = prov.imprimir_lotes(fund, {"G": {}, "C": {}})
    assert falhas == []
    assert impressos[0][0] is fund[0]
    assert sorted(impressos[0][1]) == [1, 2, 3]
    # cada conta baixada com o SEU token, tudo num ZIP unico
    assert ("TOK-G", [1, 2]) in baixadas and ("TOK-C", [3]) in baixadas
    assert "TOK-G" in zips["zpl"] and "TOK-C" in zips["zpl"]


def test_imprimir_lotes_so_baixa_o_que_falta(monkeypatch):
    prov = pv.ProvedorMLAmbas()
    monkeypatch.setattr(pv.ProvedorMLAmbas, "_token", lambda self, conta: "TOK")
    baixadas = []
    monkeypatch.setattr(core, "baixar_zpl",
                        lambda token, ids: baixadas.append(sorted(ids)) or "^XA ok ^XZ")
    monkeypatch.setattr(core, "_gerar_zip", lambda rotulo, zpl: None)
    fund = pv.fundir_grupos({"G": [_g("A", 1, [1, 2])], "C": [_g("A", 1, [3])]})
    g = fund[0]
    estado = {"G": {core._chave_estado(g.por_conta["G"]): [1, 2]}, "C": {}}
    impressos, _ = prov.imprimir_lotes([g], estado)
    assert baixadas == [[3]]                             # G ja impressa: nao baixa
    assert impressos == [(g, [3])]


def test_imprimir_lotes_nada_pendente_nao_gera_zip(monkeypatch):
    prov = pv.ProvedorMLAmbas()
    monkeypatch.setattr(pv.ProvedorMLAmbas, "_token", lambda self, conta: "TOK")
    monkeypatch.setattr(core, "_gerar_zip",
                        lambda *a: (_ for _ in ()).throw(AssertionError("nao devia gerar")))
    fund = pv.fundir_grupos({"G": [_g("A", 1, [1])]})
    g = fund[0]
    estado = {"G": {core._chave_estado(g.por_conta["G"]): [1]}}
    assert prov.imprimir_lotes([g], estado) == ([], [])


# --------------------------------------------------------------- coleta
def test_coletar_funde_e_soma_contagem(monkeypatch):
    prov = pv.ProvedorMLAmbas()
    prov._tokens_cred = {"G": {"seller_id": 1}, "C": {"seller_id": 2}}
    monkeypatch.setattr(pv.ProvedorMLAmbas, "_token", lambda self, conta: "TOK")
    monkeypatch.setattr(core, "listar_contas", lambda: ["G", "C"])

    class Coleta:
        def __init__(self, grupos, prontos):
            self.grupos, self.prontos = grupos, prontos

    coletas = {
        1: Coleta([_g("A", 1, [1])],
                  [{"_envio": {"expected_date": "2026-07-07"}}] * 2),
        2: Coleta([_g("A", 1, [9])],
                  [{"_envio": {"expected_date": "2026-07-07"}},
                   {"_envio": {"expected_date": ""}}]),
    }
    monkeypatch.setattr(
        core, "coletar_grupos",
        lambda token, seller, *, dia, somente_hoje, progresso: coletas[seller])
    grupos = prov.coletar(dia="2026-07-07", somente_hoje=False)
    assert len(grupos) == 1 and sorted(grupos[0].shipment_ids) == [1, 9]
    # contagem SOMADA das duas contas ("(sem data)" normalizado para "")
    assert prov.contagem_dias == {"2026-07-07": 3, "": 1}


def test_capacidades_do_provedor_ambas():
    prov = pv.ProvedorMLAmbas()
    assert prov.suporta_contas and prov.suporta_identificacao
    assert not prov.organiza_envio
