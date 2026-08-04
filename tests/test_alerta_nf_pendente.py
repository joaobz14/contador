"""Alerta de venda parada em "Informe a NF-e" (substatus `invoice_pending`).

Por que existe: quando falta estoque, o faturador do dono não sobe o XML da
NF-e e a venda **não chega** a `ready_to_print` — some do fluxo inteiro do app,
que só olha esse substatus. Ou seja, justamente a venda que mais precisa de
aviso (é a que exige reposição com o fornecedor) era a única invisível.

O que estes testes protegem, em ordem de gravidade:

1. **Etiqueta que não existe nunca entra no lote.** `filtrar_para_imprimir`
   continua devolvendo SÓ `ready_to_print` — o ML não libera a etiqueta de um
   envio com NF-e pendente, e contá-lo como pronto mentiria para a tela (a
   mesma família da invariante 1).
2. **Sem o parâmetro novo, nada muda.** O caminho da impressão não paga nem uma
   chamada a mais nem avalia substatus extra.
3. **Os dois avisos convivem.** Dedup em baldes separados: avisar "falta NF-e"
   não pode calar o "está pronta" de quando o XML subir — são recados
   diferentes, com ações diferentes.
"""
from __future__ import annotations

import pytest

import separador_etiquetas_ml as core
import relatorio

try:
    import bot_telegram as bot
except BaseException as e:  # noqa: BLE001
    bot = None
    _MOTIVO = str(e)


def _pedido(sid, sub, dia="2026-08-04"):
    return {"id": sid * 100, "shipping": {"id": sid}, "_sub": sub, "_dia": dia}


@pytest.fixture
def envios(monkeypatch, tmp_path):
    """Dubla a rede: cada pedido devolve o substatus/data que o teste pediu."""
    monkeypatch.setattr(core, "ARQUIVO_ENVIOS_CACHE", tmp_path / "envios.json")
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-08-04")
    consultas: list[int] = []

    def _buscar(token, sid):
        consultas.append(sid)
        ped = next(p for p in _buscar.pedidos if p["shipping"]["id"] == sid)
        return {"status": "ready_to_ship", "substatus": ped["_sub"],
                "sla": {"expected_date": f"{ped['_dia']}T12:00:00.000-03:00"}}

    _buscar.pedidos = []
    monkeypatch.setattr(core, "buscar_envio", _buscar)
    _buscar.consultas = consultas
    return _buscar


# ------------------------------------------------- o lote de impressão é sagrado
def test_pendente_de_nf_nunca_entra_no_lote_de_impressao(envios):
    """O ML não libera a etiqueta desse envio: constar como pronto seria uma
    etiqueta fantasma no lote."""
    envios.pedidos = [_pedido(1, "ready_to_print"), _pedido(2, "invoice_pending")]
    pendentes: list = []
    prontos = core.filtrar_para_imprimir("tok", envios.pedidos, progresso=lambda *a: None,
                                         pendentes_nf=pendentes)
    assert [p["shipping"]["id"] for p in prontos] == [1]
    assert [p["shipping"]["id"] for p in pendentes] == [2]


def test_sem_o_parametro_o_comportamento_e_o_de_sempre(envios):
    """Guardião do caminho da impressão: sem `pendentes_nf`, o invoice_pending
    é descartado como qualquer outro substatus — nada de novo é avaliado."""
    envios.pedidos = [_pedido(1, "ready_to_print"), _pedido(2, "invoice_pending")]
    prontos = core.filtrar_para_imprimir("tok", envios.pedidos, progresso=lambda *a: None)
    assert [p["shipping"]["id"] for p in prontos] == [1]


def test_outros_substatus_continuam_fora(envios):
    """Só o invoice_pending entra no balde novo — não é "tudo que não está
    pronto"."""
    envios.pedidos = [_pedido(1, "invoice_pending"), _pedido(2, "printed"),
                      _pedido(3, "picked_up"), _pedido(4, "")]
    pendentes: list = []
    core.filtrar_para_imprimir("tok", envios.pedidos, progresso=lambda *a: None,
                               pendentes_nf=pendentes)
    assert [p["shipping"]["id"] for p in pendentes] == [1]


def test_pendente_de_nf_vem_com_data_de_despacho(envios):
    """A data é o que permite filtrar "só o que preciso enviar HOJE" — sem ela
    o alerta avisaria de venda de qualquer dia."""
    envios.pedidos = [_pedido(1, "invoice_pending", dia="2026-08-04"),
                      _pedido(2, "invoice_pending", dia="2026-08-05")]
    pendentes: list = []
    core.filtrar_para_imprimir("tok", envios.pedidos, progresso=lambda *a: None,
                               pendentes_nf=pendentes)
    assert [p["_envio"]["expected_date"] for p in pendentes] == ["2026-08-04", "2026-08-05"]
    assert all(p["_envio"]["substatus"] == "invoice_pending" for p in pendentes)


def test_uma_consulta_por_envio_mesmo_coletando_os_dois(envios):
    """Os dois grupos saem da MESMA passada: o alerta roda a cada 5 min e a
    economia de chamadas custou uma auditoria inteira."""
    envios.pedidos = [_pedido(1, "ready_to_print"), _pedido(2, "invoice_pending")]
    core.filtrar_para_imprimir("tok", envios.pedidos, progresso=lambda *a: None,
                               pendentes_nf=[])
    assert sorted(envios.consultas) == [1, 2]


def test_envio_terminal_nao_e_cacheado_como_pendente(envios, tmp_path):
    """Regressão: o pendente de NF-e não é terminal e não pode entrar no cache
    de finalizados (senão sumiria das buscas seguintes, para sempre)."""
    envios.pedidos = [_pedido(1, "invoice_pending")]
    core.filtrar_para_imprimir("tok", envios.pedidos, progresso=lambda *a: None,
                               pendentes_nf=[])
    assert core._ler_json(core.ARQUIVO_ENVIOS_CACHE) == {}


# ------------------------------------------------------------------ o aviso
def test_texto_do_aviso_diz_que_ainda_nao_da_para_imprimir():
    itens = [core.ItemPedido(order_id=1, shipment_id=1, chave="A03", nome="A03", quantidade=1)]
    texto = relatorio.texto_alerta_pos_horario("cozilatti · falta NF-e", itens,
                                               aviso="⚠️ O ML esta esperando a NF-e")
    assert "A03 - 1" in texto
    assert "falta NF-e" in texto
    assert "esperando a NF-e" in texto


def test_aviso_vazio_mantem_o_texto_de_sempre():
    itens = [core.ItemPedido(order_id=1, shipment_id=1, chave="A03", nome="A03", quantidade=1)]
    assert relatorio.texto_alerta_pos_horario("cozilatti", itens) == "🔔 Venda cozilatti\nA03 - 1"


# ------------------------------------------------------------- integração bot
@pytest.mark.skipif(bot is None, reason="bot_telegram indisponivel")
def test_alerta_separa_prontos_de_pendentes_por_dia(monkeypatch):
    """Só o que precisa sair HOJE entra — nos dois grupos, mesma regra."""
    hoje = "2026-08-04"

    def _prontos_falso(dias=None, pendentes_nf=None):
        if pendentes_nf is not None:
            pendentes_nf += [_envio_bot(10, hoje), _envio_bot(11, "2026-08-05")]
        return [_envio_bot(1, hoje), _envio_bot(2, "2026-08-05")]

    monkeypatch.setattr(core, "conta_ativa", lambda: "")
    monkeypatch.setattr(core, "definir_conta", lambda n: None)
    monkeypatch.setattr(bot, "_prontos", _prontos_falso)
    monkeypatch.setattr(core, "carregar_credenciais", lambda: {})
    monkeypatch.setattr(core, "obter_token", lambda cred: "tok")
    monkeypatch.setattr(core, "extrair_itens", lambda token, peds: [
        core.ItemPedido(order_id=p["id"], shipment_id=p["_envio"]["shipment_id"],
                        chave=f"SKU{p['_envio']['shipment_id']}", nome="x", quantidade=1)
        for p in peds])

    novos, itens, novos_nf, itens_nf = bot._dados_alerta_da_conta(
        "conta", avisados=set(), hoje=hoje, avisados_nf=set())

    assert [p["_envio"]["shipment_id"] for p in novos] == [1]
    assert [p["_envio"]["shipment_id"] for p in novos_nf] == [10]
    assert [i.chave for i in itens] == ["SKU1"]
    assert [i.chave for i in itens_nf] == ["SKU10"]


def _envio_bot(sid, dia):
    return {"id": sid * 100, "_envio": {"shipment_id": sid, "expected_date": dia}}


@pytest.mark.skipif(bot is None, reason="bot_telegram indisponivel")
def test_dedup_dos_dois_avisos_e_separado(monkeypatch):
    """O MESMO envio pode gerar os dois avisos: primeiro "falta NF-e" e, quando
    o XML sobe, "está pronta". Balde único calaria o segundo."""
    hoje = "2026-08-04"

    def _prontos_falso(dias=None, pendentes_nf=None):
        if pendentes_nf is not None:
            pendentes_nf.append(_envio_bot(7, hoje))
        return []

    monkeypatch.setattr(core, "conta_ativa", lambda: "")
    monkeypatch.setattr(core, "definir_conta", lambda n: None)
    monkeypatch.setattr(bot, "_prontos", _prontos_falso)
    monkeypatch.setattr(core, "carregar_credenciais", lambda: {})
    monkeypatch.setattr(core, "obter_token", lambda cred: "tok")
    monkeypatch.setattr(core, "extrair_itens", lambda token, peds: [
        core.ItemPedido(order_id=1, shipment_id=7, chave="A03", nome="x", quantidade=1)])

    # o envio 7 JA foi avisado como pronto — mesmo assim o aviso de NF-e sai
    _, _, novos_nf, _ = bot._dados_alerta_da_conta(
        "conta", avisados={7}, hoje=hoje, avisados_nf=set())
    assert [p["_envio"]["shipment_id"] for p in novos_nf] == [7]

    # e, uma vez avisado no balde de NF-e, não repete
    _, _, de_novo, _ = bot._dados_alerta_da_conta(
        "conta", avisados=set(), hoje=hoje, avisados_nf={7})
    assert de_novo == []


@pytest.mark.skipif(bot is None, reason="bot_telegram indisponivel")
def test_chave_do_balde_de_nf_nao_colide_com_a_da_conta():
    assert bot.SUFIXO_ALERTA_NF
    assert bot.SUFIXO_ALERTA_NF not in ("", " ")
    assert "cozilatti" + bot.SUFIXO_ALERTA_NF != "cozilatti"


@pytest.mark.skipif(bot is None, reason="bot_telegram indisponivel")
def test_job_manda_dois_avisos_separados(monkeypatch, tmp_path):
    """De ponta a ponta: uma venda pronta e uma parada na NF-e viram DUAS
    mensagens, cada uma com o seu recado, e cada uma no seu balde de dedup."""
    import asyncio

    import shopee_api as shopee

    hoje = "2026-08-04"
    monkeypatch.setattr(bot, "ARQUIVO_ALERTAS", tmp_path / "alertas.json")
    monkeypatch.setattr(shopee, "ARQUIVO_CRED", tmp_path / "sem_shopee.json")
    monkeypatch.setattr(bot, "_alerta_no_horario", lambda agora=None: True)
    monkeypatch.setattr(core, "listar_contas", lambda: ["cozilatti"])
    monkeypatch.setattr(core, "_hoje_br", lambda: hoje)

    def _item(chave):
        return core.ItemPedido(order_id=1, shipment_id=1, chave=chave, nome=chave, quantidade=1)

    monkeypatch.setattr(bot, "_dados_alerta_da_conta",
                        lambda conta, avisados, hoje, avisados_nf=None: (
                            [_envio_bot(1, hoje)], [_item("A02")],
                            [_envio_bot(9, hoje)], [_item("A03")]))

    enviadas = []

    class _Bot:
        async def send_message(self, chat_id, texto=None, **k):
            enviadas.append(texto if texto is not None else k.get("text", ""))

    class _Ctx:
        bot_data = {"cfg": {"chat_ids": [10]}}
        bot = _Bot()

    asyncio.run(bot.job_alerta_pos_horario(_Ctx()))

    assert len(enviadas) == 2
    pronto = next(t for t in enviadas if "A02" in t)
    pendente = next(t for t in enviadas if "A03" in t)
    assert "falta NF-e" not in pronto and "NF-e" not in pronto
    assert "falta NF-e" in pendente and "esperando a NF-e" in pendente

    # baldes de dedup separados, cada um com o seu envio
    dados = core._ler_json(tmp_path / "alertas.json")
    assert dados["avisados"]["cozilatti"] == [1]
    assert dados["avisados"]["cozilatti" + bot.SUFIXO_ALERTA_NF] == [9]


# =================================================== Shopee (invoice_data)
# A Shopee e o CONTRARIO do ML aqui: a venda travada NAO some — ela continua em
# READY_TO_SHIP, ja aparece na tela e o alerta ja avisava dela como "pronta".
# So que a Shopee RECUSA o ship_order enquanto a nota estiver pendente
# (error_pending_invoice, confirmado com o suporte deles em 2026-08-04), entao
# chama-la de pronta e dizer ao operador que esta pronto o que nao esta.
import shopee_api as sh  # noqa: E402


def _ped_shopee(sn, dia_epoch=None, nf="valid", pay=None, dias=None):
    ped = {"order_sn": sn, "invoice_data": {"status": nf},
           "item_list": [{"model_sku": sn, "model_quantity_purchased": 1}]}
    if dia_epoch is not None:
        ped["ship_by_date"] = dia_epoch
    if pay is not None:
        ped["pay_time"] = pay
    if dias is not None:
        ped["days_to_ship"] = dias
    return ped


def _epoch(dia_iso, hora="12:00:00"):
    from datetime import datetime
    return int(datetime.fromisoformat(f"{dia_iso}T{hora}-03:00").timestamp())


def test_shopee_separa_pronta_de_travada_na_nf(monkeypatch):
    hoje = core._hoje_br()
    det = [_ped_shopee("OK", _epoch(hoje), nf="valid"),
           _ped_shopee("TRAVADA", _epoch(hoje), nf="pending")]
    monkeypatch.setattr(sh, "listar_order_sns", lambda c, t: ["OK", "TRAVADA"])
    monkeypatch.setattr(sh, "buscar_detalhes", lambda c, t, sns: det)

    novos, itens, nf, itens_nf = sh.pedidos_prontos_novos(
        {}, "tok", avisados=set(), hoje=hoje, avisados_nf=set())

    assert [d["order_sn"] for d in novos] == ["OK"]
    assert [d["order_sn"] for d in nf] == ["TRAVADA"]
    assert [i.chave for i in itens] == ["OK"]
    assert [i.chave for i in itens_nf] == ["TRAVADA"]


def test_shopee_travada_nao_e_mais_chamada_de_pronta(monkeypatch):
    """Regressao: antes a venda com NF-e pendente entrava no aviso de "pronta"
    — e a Shopee recusa o ship_order dela. Era dizer que esta pronto o que a
    propria Shopee nega."""
    hoje = core._hoje_br()
    det = [_ped_shopee("TRAVADA", _epoch(hoje), nf="pending")]
    monkeypatch.setattr(sh, "listar_order_sns", lambda c, t: ["TRAVADA"])
    monkeypatch.setattr(sh, "buscar_detalhes", lambda c, t, sns: det)

    novos, _, nf, _ = sh.pedidos_prontos_novos({}, "tok", avisados=set(), hoje=hoje,
                                               avisados_nf=set())
    assert novos == []
    assert [d["order_sn"] for d in nf] == ["TRAVADA"]


def test_shopee_so_avisa_do_dia(monkeypatch):
    """Mesma regra do ML: so o que precisa sair HOJE."""
    hoje = core._hoje_br()
    from datetime import date, timedelta
    amanha = (date.fromisoformat(hoje) + timedelta(days=1)).isoformat()
    det = [_ped_shopee("HOJE", _epoch(hoje), nf="pending"),
           _ped_shopee("AMANHA", _epoch(amanha), nf="pending")]
    monkeypatch.setattr(sh, "listar_order_sns", lambda c, t: ["HOJE", "AMANHA"])
    monkeypatch.setattr(sh, "buscar_detalhes", lambda c, t, sns: det)

    _, _, nf, _ = sh.pedidos_prontos_novos({}, "tok", avisados=set(), hoje=hoje,
                                           avisados_nf=set())
    assert [d["order_sn"] for d in nf] == ["HOJE"]


def test_shopee_dedup_separado_dos_prontos(monkeypatch):
    """O mesmo order_sn pode gerar os dois recados: primeiro "falta NF-e" e,
    quando o XML sobe, "esta pronta". Balde unico calaria o segundo."""
    hoje = core._hoje_br()
    monkeypatch.setattr(sh, "listar_order_sns", lambda c, t: ["X"])
    monkeypatch.setattr(sh, "buscar_detalhes", lambda c, t, sns:
                        [_ped_shopee("X", _epoch(hoje), nf="pending")])
    # ja avisado como PRONTO nao cala o aviso de NF-e
    _, _, nf, _ = sh.pedidos_prontos_novos({}, "tok", avisados={"X"}, hoje=hoje,
                                           avisados_nf=set())
    assert [d["order_sn"] for d in nf] == ["X"]
    # ja avisado no balde de NF-e nao repete
    _, _, de_novo, _ = sh.pedidos_prontos_novos({}, "tok", avisados=set(), hoje=hoje,
                                                avisados_nf={"X"})
    assert de_novo == []


# ------------------------------------------------- dia quando falta o prazo
def test_dia_previsto_usa_ship_by_date_quando_existe():
    hoje = core._hoje_br()
    assert sh.dia_previsto(_ped_shopee("A", _epoch(hoje))) == hoje


def test_dia_previsto_deriva_de_pay_time_mais_days_to_ship():
    """A Shopee leva um tempo para atribuir o `ship_by_date` — venda recem-paga
    vem sem ele. Sem este fallback, uma venda travada recem-criada ficaria fora
    de qualquer filtro por dia e o aviso nasceria mudo.

    A conta foi conferida contra um pedido real: ship_by_date e o FIM DO DIA de
    pay_time + days_to_ship (pago 03/08, days_to_ship 2 -> 05/08 23:59:59)."""
    ped = _ped_shopee("SEM_PRAZO", nf="pending", pay=_epoch("2026-08-03", "14:36:50"),
                      dias=2)
    assert sh.dia_previsto(ped) == "2026-08-05"


def test_dia_previsto_vazio_quando_nao_da_para_saber():
    assert sh.dia_previsto({"order_sn": "X"}) == ""


def test_nf_pendente_so_para_pending():
    assert sh.nf_pendente(_ped_shopee("A", nf="pending"))
    assert not sh.nf_pendente(_ped_shopee("A", nf="valid"))
    assert not sh.nf_pendente({"order_sn": "A"})          # sem invoice_data


def test_invoice_data_vem_na_mesma_chamada(monkeypatch):
    """Custo zero: o campo viaja na chamada de detalhe que ja era feita."""
    vistos = []
    monkeypatch.setattr(sh, "_get_shop", lambda c, t, p, params:
                        (vistos.append(params), {"response": {"order_list": []}})[1])
    sh.buscar_detalhes({}, "tok", ["A"])
    assert len(vistos) == 1, "nao pode fazer chamada extra"
    assert "invoice_data" in vistos[0]["response_optional_fields"]
