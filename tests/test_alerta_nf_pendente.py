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
    texto = relatorio.texto_alerta_pos_horario([
        relatorio.BlocoAlerta("cozilatti", itens, nf_pendente=True,
                              aviso="⚠️ O ML esta esperando a NF-e")])
    assert "A03 - 1" in texto
    assert "Ainda sem NF-e" in texto
    assert "esperando a NF-e" in texto


def test_venda_pronta_nao_leva_recado_de_nf():
    """Sem a secao de NF, o texto nao pode insinuar que falta alguma coisa —
    era o recado que fazia o dono conferir o painel a toa."""
    itens = [core.ItemPedido(order_id=1, shipment_id=1, chave="A03", nome="A03", quantidade=1)]
    texto = relatorio.texto_alerta_pos_horario([relatorio.BlocoAlerta("cozilatti", itens)])
    assert texto == "🔔 Vendas novas para hoje\n\ncozilatti\nA03 - 1"
    assert "NF-e" not in texto


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
def test_job_manda_um_texto_com_as_duas_secoes_e_baldes_separados(monkeypatch, tmp_path):
    """De ponta a ponta: uma venda pronta e uma parada na NF-e viram UMA
    mensagem com duas secoes — e continuam em baldes de dedup SEPARADOS.

    O agrupamento (05/08/2026) mudou so o ENVIO. A separacao dos baldes e o que
    nao pode mudar: se o shipment_id ja avisado como "falta NF-e" caisse no
    mesmo balde, ele calaria o aviso de quando a venda ficasse pronta de fato."""
    import asyncio

    import shopee_api as shopee

    hoje = "2026-08-04"
    monkeypatch.setattr(bot, "ARQUIVO_ALERTAS", tmp_path / "alertas.json")
    monkeypatch.setattr(shopee, "ARQUIVO_CRED", tmp_path / "sem_shopee.json")
    monkeypatch.setattr(bot, "_alerta_no_horario", lambda agora=None: True)
    monkeypatch.setattr(core, "listar_contas", lambda: ["cozilatti"])
    monkeypatch.setattr(core, "_hoje_br", lambda: hoje)

    # O `shipment_id` do item TEM de bater com o do envio, como em producao
    # (`extrair_itens` usa `_envio["shipment_id"]`): desde a carencia da NF-e o
    # alerta cruza os dois para separar quem ja passou do tempo de quem nao.
    def _item(chave, sid):
        return core.ItemPedido(order_id=sid, shipment_id=sid, chave=chave,
                               nome=chave, quantidade=1)

    monkeypatch.setattr(bot, "_dados_alerta_da_conta",
                        lambda conta, avisados, hoje, avisados_nf=None: (
                            [_envio_bot(1, hoje)], [_item("A02", 1)],
                            [_envio_bot(9, hoje)], [_item("A03", 9)]))

    enviadas = []

    class _Bot:
        async def send_message(self, chat_id, texto=None, **k):
            enviadas.append(texto if texto is not None else k.get("text", ""))

    class _Ctx:
        bot_data = {"cfg": {"chat_ids": [10]}}
        bot = _Bot()

    # 1o ciclo do dia e calado (so registra); o 2o e que fala.
    asyncio.run(bot.job_alerta_pos_horario(_Ctx()))
    assert enviadas == [], "o ciclo que abre a janela nao despeja o dia inteiro"
    core._gravar_json(tmp_path / "alertas.json",
                      {"dia": hoje, "avisados": {}, "itens": {}, "iniciado": True})

    asyncio.run(bot.job_alerta_pos_horario(_Ctx()))

    assert len(enviadas) == 1, "uma mensagem por ciclo, nao uma por balde"
    texto = enviadas[0]
    assert "A02 - 1" in texto and "A03 - 1" in texto
    assert texto.index("A02 - 1") < texto.index("Ainda sem NF-e"), \
        "o que da para imprimir vem antes do que ainda nao da"
    assert "esperando a NF-e" in texto

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


def test_dia_previsto_nao_INVENTA_data_quando_falta_o_prazo():
    """Havia aqui um fallback `pay_time + days_to_ship`, dito "conferido contra
    um pedido real". Um segundo pedido real o contradiz (`260805JCWTKH9K`: pago
    05/08, days_to_ship 2, ship_by_date REAL de 06/08 — a conta daria 07/08),
    entao nao existe formula confirmada e adivinhar e pior que admitir.

    "" significa DATA INCERTA, e quem consome inclui (teste abaixo). O que
    condenou o fallback nao foi so estar errado: empurrando a venda para a
    frente, ele produzia exatamente o silencio que existia para evitar."""
    ped = _ped_shopee("SEM_PRAZO", nf="pending", pay=_epoch("2026-08-03", "14:36:50"),
                      dias=2)
    assert sh.dia_previsto(ped) == ""


def test_dia_previsto_vazio_quando_nao_da_para_saber():
    assert sh.dia_previsto({"order_sn": "X"}) == ""


def test_nota_nao_validada_e_tudo_que_nao_e_valid():
    """`!= "valid"` e nao `== "pending"`: o suporte disse que a lista de
    valores nao e exaustiva, e um valor novo que NAO seja "valid" tambem
    significa etiqueta bloqueada. Errar para o lado de nao imprimir."""
    assert sh.nota_nao_validada(_ped_shopee("A", nf="pending"))
    assert sh.nota_nao_validada(_ped_shopee("A", nf="qualquer_coisa_nova"))
    assert sh.nota_nao_validada({"order_sn": "A"})     # sem invoice_data: nao sabemos
    assert not sh.nota_nao_validada(_ped_shopee("A", nf="valid"))


def test_invoice_data_vem_na_mesma_chamada(monkeypatch):
    """Custo zero: o campo viaja na chamada de detalhe que ja era feita."""
    vistos = []
    monkeypatch.setattr(sh, "_get_shop", lambda c, t, p, params:
                        (vistos.append(params), {"response": {"order_list": []}})[1])
    sh.buscar_detalhes({}, "tok", ["A"])
    assert len(vistos) == 1, "nao pode fazer chamada extra"
    assert "invoice_data" in vistos[0]["response_optional_fields"]


# ============================================ carencia do aviso (05/08/2026)
# O aviso NAO existe para dizer "esta sem NF-e" — toda venda nova esta, por
# alguns minutos, enquanto o ERP do dono (UpSeller) puxa o pedido e sobe o XML.
# Ele existe para dizer "esta sem NF-e ha tempo demais para ser processamento
# normal", que no fluxo dele significa uma coisa so: o ERP olhou, NAO achou
# estoque e por isso nao faturou. Sem a carencia o alerta disparava dentro da
# janela normal e se desmentia minutos depois com o ✅.
from datetime import datetime, timedelta  # noqa: E402


def _agora():
    return datetime(2026, 8, 5, 14, 0, tzinfo=core.TZ_BR)


@pytest.mark.skipif(bot is None, reason="bot_telegram indisponivel")
def test_pago_em_le_as_duas_formas():
    """Shopee manda epoch (`pay_time`); ML manda ISO (`date_closed`)."""
    epoch = int(datetime(2026, 8, 5, 13, 30, tzinfo=core.TZ_BR).timestamp())
    assert bot._pago_em({"pay_time": epoch}).hour == 13

    iso = bot._pago_em({"date_closed": "2026-08-05T13:30:00.000-03:00"})
    assert iso is not None and iso.hour == 13

    # `date_created` e a reserva quando o pagamento nao veio
    assert bot._pago_em({"date_created": "2026-08-05T13:30:00.000-03:00"}) is not None
    # e "nao sei" continua sendo None, nao uma data inventada
    assert bot._pago_em({}) is None
    assert bot._pago_em({"date_closed": "isto nao e data"}) is None


@pytest.mark.skipif(bot is None, reason="bot_telegram indisponivel")
def test_venda_recem_paga_ainda_nao_vira_aviso():
    """O caso do relato: venda cai, o ERP ainda nem puxou, e o bot avisava."""
    recem = {"pay_time": int((_agora() - timedelta(minutes=5)).timestamp())}
    passaram, espera = bot._fora_da_carencia([recem], 30, agora=_agora())
    assert passaram == [] and espera == 0


@pytest.mark.skipif(bot is None, reason="bot_telegram indisponivel")
def test_venda_parada_ha_tempo_demais_vira_aviso():
    """Passou da carencia e continua sem nota: agora sim e falta de estoque."""
    velha = {"pay_time": int((_agora() - timedelta(minutes=45)).timestamp())}
    passaram, espera = bot._fora_da_carencia([velha], 30, agora=_agora())
    assert passaram == [velha]
    assert espera == 45, "o tempo vai para a mensagem: e ele que sugere a causa"


@pytest.mark.skipif(bot is None, reason="bot_telegram indisponivel")
def test_carencia_conta_da_VENDA_e_nao_de_quando_o_bot_olhou():
    """Bot fora do ar a noite toda: a venda travada desde as 23h ja nasce com
    9 horas de idade e e avisada na hora, sem esperar mais 30 min a toa."""
    ontem = datetime(2026, 8, 4, 23, 0, tzinfo=core.TZ_BR)
    de_ontem = {"pay_time": int(ontem.timestamp())}
    manha = datetime(2026, 8, 5, 8, 30, tzinfo=core.TZ_BR)
    passaram, espera = bot._fora_da_carencia([de_ontem], 30, agora=manha)
    assert passaram == [de_ontem] and espera == 9 * 60 + 30


@pytest.mark.skipif(bot is None, reason="bot_telegram indisponivel")
def test_sem_carimbo_de_tempo_AVISA_em_vez_de_calar():
    """"Nao sei" para o lado de falar: calar por falta de informacao esconderia
    justamente a venda sem estoque que este aviso existe para pegar. Se a API
    parar de mandar o campo, o sintoma sera ruido visivel, nao silencio."""
    passaram, espera = bot._fora_da_carencia([{"order_sn": "SN1"}], 30, agora=_agora())
    assert passaram and espera == 0


@pytest.mark.skipif(bot is None, reason="bot_telegram indisponivel")
def test_carencia_do_config_manda_no_padrao():
    assert bot._carencia({}) == bot.CARENCIA_NF_MIN, "config sem a chave nao quebra"
    assert bot._carencia({"carencia_nf_min": 90}) == 90
    assert bot._carencia({"carencia_nf_min": "lixo"}) == bot.CARENCIA_NF_MIN


@pytest.mark.skipif(bot is None, reason="bot_telegram indisponivel")
def test_job_nao_avisa_venda_dentro_da_carencia_e_avisa_depois(monkeypatch, tmp_path):
    """De ponta a ponta: a MESMA venda fica calada no 1o ciclo (recem-paga) e
    vira aviso quando envelhece — sem nunca ter sido registrada no meio, senao
    o dedup a calaria para sempre."""
    import asyncio

    import shopee_api as shopee

    hoje = "2026-08-05"
    monkeypatch.setattr(bot, "ARQUIVO_ALERTAS", tmp_path / "alertas.json")
    monkeypatch.setattr(shopee, "ARQUIVO_CRED", tmp_path / "sem_shopee.json")
    monkeypatch.setattr(bot, "_alerta_no_horario", lambda agora=None: True)
    monkeypatch.setattr(core, "listar_contas", lambda: ["cozilatti"])
    monkeypatch.setattr(core, "_hoje_br", lambda: hoje)
    bot._salvar_alertas({"dia": hoje, "avisados": {}, "itens": {}, "iniciado": True})

    idade = {"min": 5}

    def _dados(conta, avisados, hoje_, avisados_nf=None):
        if 9 in (avisados_nf or set()):
            return [], [], [], []
        pago = datetime.now(core.TZ_BR) - timedelta(minutes=idade["min"])
        ped = dict(_envio_bot(9, hoje_))
        ped["date_closed"] = pago.isoformat()
        item = core.ItemPedido(order_id=9, shipment_id=9, chave="AR1",
                               nome="AR1", quantidade=1)
        return [], [], [ped], [item]

    monkeypatch.setattr(bot, "_dados_alerta_da_conta", _dados)

    enviadas = []

    class _Bot:
        async def send_message(self, chat_id, texto=None, **k):
            enviadas.append(texto if texto is not None else k.get("text", ""))

    class _Ctx:
        bot_data = {"cfg": {"chat_ids": [10]}}
        bot = _Bot()

    asyncio.run(bot.job_alerta_pos_horario(_Ctx()))
    assert enviadas == [], "recem-paga: o ERP ainda nem puxou"
    estado = core._ler_json(tmp_path / "alertas.json")
    assert not estado["avisados"].get("cozilatti" + bot.SUFIXO_ALERTA_NF), \
        "quem esta na carencia NAO pode ser registrado, senao nunca seria avisado"

    idade["min"] = 45                       # a mesma venda, mais tarde
    asyncio.run(bot.job_alerta_pos_horario(_Ctx()))
    assert len(enviadas) == 1
    assert "AR1 - 1" in enviadas[0] and "parada há 45 min" in enviadas[0]
    estado = core._ler_json(tmp_path / "alertas.json")
    assert estado["avisados"]["cozilatti" + bot.SUFIXO_ALERTA_NF] == [9]


# ------------------------------- data incerta nunca exclui (06/08/2026)
def test_venda_que_a_shopee_ainda_NAO_LIBEROU_fica_de_fora(monkeypatch):
    """Sem `ship_by_date` a venda NAO e de hoje — e isso e informacao, nao
    ignorancia (medido em 06/08/2026). O painel da Shopee, na venda sem prazo,
    diz: "A emissao de etiqueta estara disponivel a partir de 07/08 13:07. O
    prazo de envio comecara a contar APENAS APOS essa data". Campo ausente
    significa "ainda nao liberei esta venda", o oposto de "pode ser hoje".

    Incluir (como se tentou por 2 horas naquele dia) produzia alarme diario
    garantido: toda venda da tarde cai aqui, a carencia de 30 min nao alcanca
    (o "Em processamento" dura ~24h) e o aviso dizia "falta NF-e" de uma venda
    que o ERP nem tinha como faturar ainda."""
    hoje = core._hoje_br()
    det = [_ped_shopee("SEM_PRAZO", nf="valid"),
           _ped_shopee("SEM_PRAZO_NF", nf="pending")]
    monkeypatch.setattr(sh, "listar_order_sns", lambda c, t: ["SEM_PRAZO", "SEM_PRAZO_NF"])
    monkeypatch.setattr(sh, "buscar_detalhes", lambda c, t, sns: det)

    novos, _, nf, _ = sh.pedidos_prontos_novos(
        {}, "tok", avisados=set(), hoje=hoje, avisados_nf=set())

    assert novos == [] and nf == []


def test_venda_com_prazo_de_OUTRO_dia_continua_de_fora(monkeypatch):
    """A inclusao vale so para a data INCERTA. Prazo conhecido e diferente de
    hoje continua fora — senao o alerta viraria "todas as vendas abertas"."""
    monkeypatch.setattr(sh, "listar_order_sns", lambda c, t: ["OUTRO_DIA"])
    monkeypatch.setattr(sh, "buscar_detalhes", lambda c, t, sns: [
        _ped_shopee("OUTRO_DIA", _epoch("2026-08-20"), nf="valid")])

    novos, _, nf, _ = sh.pedidos_prontos_novos(
        {}, "tok", avisados=set(), hoje="2026-08-06", avisados_nf=set())

    assert novos == [] and nf == []


def test_o_pedido_real_que_expos_a_formula_errada():
    """`260805JCWTKH9K`, medido em 06/08/2026: pago 05/08 09:40 com
    days_to_ship 2 e ship_by_date REAL de 06/08. A formula antiga daria 07/08 —
    um dia depois — e a venda sumiria do filtro no dia em que vencia."""
    real = _ped_shopee("260805JCWTKH9K", _epoch("2026-08-06", "23:59:59"),
                       nf="pending", pay=_epoch("2026-08-05", "09:40:51"), dias=2)
    assert sh.dia_previsto(real) == "2026-08-06"
    sem = {k: v for k, v in real.items() if k != "ship_by_date"}
    assert sh.dia_previsto(sem) == "", "sem o campo, incerto — nao 2026-08-07"
