"""Testes do alerta pos-horario (venda nova ja pronta pra despachar HOJE).

Mesmo padrao de tests/test_bot_impressao.py: pula se o telegram nao importar
no ambiente (dependencia nativa ausente).
"""
from __future__ import annotations

import asyncio

import pytest

try:
    import bot_telegram as bot
except BaseException as e:  # noqa: BLE001 - pyo3 PanicException herda de BaseException
    pytest.skip(f"bot_telegram indisponivel: {e}", allow_module_level=True)

import separador_etiquetas_ml as core  # noqa: E402
import shopee_api as shopee  # noqa: E402

# Referencia REAL do gate de horario, capturada antes de a fixture autouse
# substitui-la (os testes do proprio gate precisam da implementacao de verdade).
_ALERTA_NO_HORARIO_REAL = bot._alerta_no_horario


@pytest.fixture(autouse=True)
def _arquivo_alertas_isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "ARQUIVO_ALERTAS", tmp_path / "alertas.json")
    # Por padrao, sem credencial Shopee (isola do estado real do repo/maquina
    # e faz o job pular a checagem Shopee em silencio, como um setup so-ML).
    # Testes especificos da Shopee apontam pra um arquivo que EXISTE.
    monkeypatch.setattr(shopee, "ARQUIVO_CRED", tmp_path / "sem_credencial_shopee.json")
    # Testes rodam a qualquer hora (CI): fixa "dentro da janela de horario" pro
    # gate do job nao virar flakiness. O gate em si tem testes proprios.
    monkeypatch.setattr(bot, "_alerta_no_horario", lambda agora=None: True)


def _envio(sid, dia, item_id=1):
    return {"id": item_id, "_envio": {"shipment_id": sid, "expected_date": dia}}


# ------------------------------------------------------- _carregar/_salvar_alertas
def test_carregar_alertas_comeca_vazio_sem_arquivo(monkeypatch):
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    dados = bot._carregar_alertas()
    assert dados == {"dia": "2026-07-24", "avisados": {}, "itens": {}}


def test_carregar_alertas_preserva_mesmo_dia(monkeypatch):
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    bot._salvar_alertas({"dia": "2026-07-24", "avisados": {"cozilatti": [1, 2]},
                        "itens": {"cozilatti": [{"chave": "A02", "quantidade": 1}]}})
    dados = bot._carregar_alertas()
    assert dados["avisados"] == {"cozilatti": [1, 2]}
    assert dados["itens"] == {"cozilatti": [{"chave": "A02", "quantidade": 1}]}


def test_carregar_alertas_reseta_quando_dia_muda(monkeypatch):
    bot._salvar_alertas({"dia": "2026-07-23", "avisados": {"cozilatti": [1, 2]},
                        "itens": {"cozilatti": [{"chave": "A02", "quantidade": 1}]}})
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    dados = bot._carregar_alertas()
    assert dados == {"dia": "2026-07-24", "avisados": {}, "itens": {}}


# ------------------------------------------------------------ _dados_alerta_da_conta
def test_dados_alerta_filtra_por_hoje_e_dedup(monkeypatch):
    prontos = [_envio(1, "2026-07-24"), _envio(2, "2026-07-23"), _envio(3, "2026-07-24")]
    monkeypatch.setattr(core, "conta_ativa", lambda: "")
    monkeypatch.setattr(core, "definir_conta", lambda nome: None)
    monkeypatch.setattr(bot, "_prontos", lambda dias=None: prontos)
    monkeypatch.setattr(core, "carregar_credenciais", lambda: {})
    monkeypatch.setattr(core, "obter_token", lambda cred: "tok")
    monkeypatch.setattr(core, "extrair_itens", lambda token, pedidos: [f"item-{p['id']}" for p in pedidos])

    novos, itens = bot._dados_alerta_da_conta("cozilatti", avisados={3}, hoje="2026-07-24")

    # sid 1: hoje e nao avisado -> entra. sid 2: nao e hoje -> fora. sid 3: hoje mas ja avisado -> fora.
    assert [p["_envio"]["shipment_id"] for p in novos] == [1]
    assert itens == ["item-1"]


def test_dados_alerta_sem_novidade_nao_chama_extrair_itens(monkeypatch):
    monkeypatch.setattr(core, "conta_ativa", lambda: "")
    monkeypatch.setattr(core, "definir_conta", lambda nome: None)
    monkeypatch.setattr(bot, "_prontos", lambda dias=None: [_envio(1, "2026-07-24")])
    chamou = []
    monkeypatch.setattr(core, "extrair_itens", lambda *a, **k: chamou.append(1))

    novos, itens = bot._dados_alerta_da_conta("cozilatti", avisados={1}, hoje="2026-07-24")

    assert novos == [] and itens == []
    assert chamou == []


def test_dados_alerta_troca_e_restaura_conta(monkeypatch):
    trocas = []
    monkeypatch.setattr(core, "conta_ativa", lambda: "gastromaq")
    monkeypatch.setattr(core, "definir_conta", lambda nome: trocas.append(nome))
    monkeypatch.setattr(bot, "_prontos", lambda dias=None: [])
    monkeypatch.setattr(core, "extrair_itens", lambda *a, **k: [])

    bot._dados_alerta_da_conta("cozilatti", avisados=set(), hoje="2026-07-24")

    # troca pra cozilatti (checagem) e volta pra gastromaq (conta original) no final.
    assert trocas == ["cozilatti", "gastromaq"]


def test_dados_alerta_nao_troca_se_ja_e_a_conta_ativa(monkeypatch):
    trocas = []
    monkeypatch.setattr(core, "conta_ativa", lambda: "cozilatti")
    monkeypatch.setattr(core, "definir_conta", lambda nome: trocas.append(nome))
    monkeypatch.setattr(bot, "_prontos", lambda dias=None: [])

    bot._dados_alerta_da_conta("cozilatti", avisados=set(), hoje="2026-07-24")

    assert trocas == []


# ---------------------------------------------------------------- _dados_alerta_shopee
def test_dados_alerta_shopee_delega_pro_shopee_api(monkeypatch):
    chamadas = []
    monkeypatch.setattr(shopee, "carregar_credenciais", lambda: {"cred": 1})
    monkeypatch.setattr(shopee, "obter_token", lambda cred: "TOK")
    monkeypatch.setattr(shopee, "pedidos_prontos_novos",
                        lambda cred, token, avisados, hoje: chamadas.append(
                            (cred, token, avisados, hoje)) or (["novo"], ["item"]))

    novos, itens = bot._dados_alerta_shopee(avisados={"SN0"}, hoje="2026-07-24")

    assert novos == ["novo"] and itens == ["item"]
    assert chamadas == [({"cred": 1}, "TOK", {"SN0"}, "2026-07-24")]


# ----------------------------------------------------- janela de horario/busca
def test_alerta_no_horario_janela():
    from datetime import datetime
    tz = core.TZ_BR

    def as_(h, m=0):
        return datetime(2026, 7, 29, h, m, tzinfo=tz)

    assert _ALERTA_NO_HORARIO_REAL(as_(6, 59)) is False   # madrugada: dorme
    assert _ALERTA_NO_HORARIO_REAL(as_(7, 0)) is True     # inicio inclusivo
    assert _ALERTA_NO_HORARIO_REAL(as_(12, 30)) is True
    assert _ALERTA_NO_HORARIO_REAL(as_(20, 59)) is True   # ultimo ciclo util
    assert _ALERTA_NO_HORARIO_REAL(as_(21, 0)) is False   # fim exclusivo


def test_dados_alerta_usa_janela_curta_de_busca(monkeypatch):
    """O alerta busca com DIAS_JANELA_ALERTA (5 dias), nao a janela cheia de 30
    — e o corte de ~90% das chamadas achado na auditoria de APIs."""
    capturado = {}

    def _fake_prontos(dias=None):
        capturado["dias"] = dias
        return []

    monkeypatch.setattr(core, "conta_ativa", lambda: "")
    monkeypatch.setattr(core, "definir_conta", lambda nome: None)
    monkeypatch.setattr(bot, "_prontos", _fake_prontos)

    bot._dados_alerta_da_conta("cozilatti", avisados=set(), hoje="2026-07-29")

    assert capturado["dias"] == bot.DIAS_JANELA_ALERTA


# ------------------------------------------------------------------- job_alerta
def _ctx(chat_ids, send, extras=None):
    """`extras` (opcional) coleta os kwargs de cada envio — e assim que os testes
    do resumo conferem parse_mode/disable_web_page_preview, que sao tao
    obrigatorios quanto o texto: sem parse_mode="HTML" as tags aparecem cruas."""
    class _Bot:
        async def send_message(self, chat_id, texto=None, **k):
            if extras is not None:
                extras.append(k)
            return send(chat_id, texto if texto is not None else k.get("text", ""))

    class _Ctx:
        bot_data = {"cfg": {"chat_ids": chat_ids}}
        bot = _Bot()

    return _Ctx()


def test_job_alerta_avisa_e_marca_dedup(monkeypatch):
    enviados = []
    monkeypatch.setattr(core, "listar_contas", lambda: ["cozilatti"])
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    monkeypatch.setattr(bot, "_dados_alerta_da_conta",
                        lambda conta, avisados, hoje: (
                            [_envio(1, hoje)],
                            [core.ItemPedido(order_id=1, shipment_id=1, chave="A02",
                                            nome="A02", quantidade=1)],
                        ))
    ctx = _ctx([10], lambda cid, txt: enviados.append((cid, txt)))

    asyncio.run(bot.job_alerta_pos_horario(ctx))

    assert len(enviados) == 1
    assert "A02" in enviados[0][1]
    dados = bot._carregar_alertas()
    assert dados["avisados"]["cozilatti"] == [1]
    assert dados["itens"]["cozilatti"] == [{"chave": "A02", "quantidade": 1}]


def test_job_alerta_fora_do_horario_e_noop_sem_api(monkeypatch):
    """Fora da janela (madrugada), o job acorda e volta a dormir: nenhuma
    chamada de API, nenhuma leitura de estado, nenhuma mensagem."""
    monkeypatch.setattr(bot, "_alerta_no_horario", lambda agora=None: False)
    monkeypatch.setattr(core, "listar_contas",
                        lambda: (_ for _ in ()).throw(AssertionError("nao devia consultar nada")))
    monkeypatch.setattr(bot, "_carregar_alertas",
                        lambda: (_ for _ in ()).throw(AssertionError("nao devia ler estado")))
    enviados = []
    ctx = _ctx([10], lambda cid, txt: enviados.append((cid, txt)))

    asyncio.run(bot.job_alerta_pos_horario(ctx))

    assert enviados == []


def test_job_alerta_sem_novidade_nao_envia_nada(monkeypatch):
    enviados = []
    monkeypatch.setattr(core, "listar_contas", lambda: ["cozilatti"])
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    monkeypatch.setattr(bot, "_dados_alerta_da_conta", lambda conta, avisados, hoje: ([], []))
    ctx = _ctx([10], lambda cid, txt: enviados.append((cid, txt)))

    asyncio.run(bot.job_alerta_pos_horario(ctx))

    assert enviados == []


def test_job_alerta_nao_repete_o_mesmo_envio_em_ciclos_seguintes(monkeypatch):
    """2 ciclos seguidos: o mesmo shipment_id so pode gerar 1 alerta."""
    enviados = []
    monkeypatch.setattr(core, "listar_contas", lambda: ["cozilatti"])
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")

    def _dados(conta, avisados, hoje):
        if 1 in avisados:
            return [], []
        return ([_envio(1, hoje)],
                [core.ItemPedido(order_id=1, shipment_id=1, chave="A02", nome="A02", quantidade=1)])

    monkeypatch.setattr(bot, "_dados_alerta_da_conta", _dados)
    ctx = _ctx([10], lambda cid, txt: enviados.append((cid, txt)))

    asyncio.run(bot.job_alerta_pos_horario(ctx))
    asyncio.run(bot.job_alerta_pos_horario(ctx))

    assert len(enviados) == 1


def test_job_alerta_isola_falha_por_conta(monkeypatch):
    """Uma conta que estoura excecao nao impede o aviso das demais."""
    enviados = []
    monkeypatch.setattr(core, "listar_contas", lambda: ["com_erro", "ok"])
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")

    def _dados(conta, avisados, hoje):
        if conta == "com_erro":
            raise RuntimeError("falha de rede")
        return ([_envio(1, hoje)],
                [core.ItemPedido(order_id=1, shipment_id=1, chave="A02", nome="A02", quantidade=1)])

    monkeypatch.setattr(bot, "_dados_alerta_da_conta", _dados)
    ctx = _ctx([10], lambda cid, txt: enviados.append((cid, txt)))

    asyncio.run(bot.job_alerta_pos_horario(ctx))

    assert len(enviados) == 1  # a conta "ok" ainda avisou


def test_job_alerta_falha_num_chat_nao_cala_os_outros(monkeypatch):
    enviados = []
    monkeypatch.setattr(core, "listar_contas", lambda: ["cozilatti"])
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    monkeypatch.setattr(bot, "_dados_alerta_da_conta",
                        lambda conta, avisados, hoje: (
                            [_envio(1, hoje)],
                            [core.ItemPedido(order_id=1, shipment_id=1, chave="A02",
                                            nome="A02", quantidade=1)],
                        ))

    def send(chat_id, texto):
        if chat_id == 1:
            raise RuntimeError("Forbidden: bot was blocked by the user")
        enviados.append(chat_id)

    ctx = _ctx([1, 2], send)
    asyncio.run(bot.job_alerta_pos_horario(ctx))
    assert enviados == [2]


def test_job_alerta_sem_contas_nao_quebra(monkeypatch):
    monkeypatch.setattr(core, "listar_contas", lambda: [])
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    monkeypatch.setattr(bot, "_dados_alerta_da_conta", lambda conta, avisados, hoje: ([], []))
    ctx = _ctx([10], lambda cid, txt: None)
    asyncio.run(bot.job_alerta_pos_horario(ctx))  # nao deve levantar


# --------------------------------------------------------------- Shopee no alerta
def _pedido_shopee(order_sn):
    return {"order_sn": order_sn}


def test_job_alerta_pula_shopee_sem_credencial(monkeypatch):
    """Setup so-ML (sem credenciais_shopee.json): nao chama a Shopee, nao
    loga erro a cada ciclo."""
    monkeypatch.setattr(core, "listar_contas", lambda: [])
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    monkeypatch.setattr(bot, "_dados_alerta_da_conta", lambda conta, avisados, hoje: ([], []))
    chamou = []
    monkeypatch.setattr(bot, "_dados_alerta_shopee", lambda *a, **k: chamou.append(1))
    ctx = _ctx([10], lambda cid, txt: None)

    asyncio.run(bot.job_alerta_pos_horario(ctx))

    assert chamou == []


def test_job_alerta_avisa_shopee_quando_configurada(monkeypatch, tmp_path):
    monkeypatch.setattr(shopee, "ARQUIVO_CRED", tmp_path / "credenciais_shopee.json")
    shopee.ARQUIVO_CRED.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(core, "listar_contas", lambda: [])
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    monkeypatch.setattr(bot, "_dados_alerta_da_conta", lambda conta, avisados, hoje: ([], []))
    monkeypatch.setattr(bot, "_dados_alerta_shopee",
                        lambda avisados, hoje: (
                            [_pedido_shopee("SN1")],
                            [core.ItemPedido(order_id="SN1", shipment_id="SN1", chave="A02",
                                            nome="A02", quantidade=2)],
                        ))
    enviados = []
    ctx = _ctx([10], lambda cid, txt: enviados.append((cid, txt)))

    asyncio.run(bot.job_alerta_pos_horario(ctx))

    assert len(enviados) == 1
    assert "🔔 Venda Shopee" in enviados[0][1]
    assert "A02 - 2" in enviados[0][1]
    dados = bot._carregar_alertas()
    assert dados["avisados"]["Shopee"] == ["SN1"]
    assert dados["itens"]["Shopee"] == [{"chave": "A02", "quantidade": 2}]


def test_job_alerta_shopee_isola_falha_sem_impedir_ml(monkeypatch, tmp_path):
    monkeypatch.setattr(shopee, "ARQUIVO_CRED", tmp_path / "credenciais_shopee.json")
    shopee.ARQUIVO_CRED.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(core, "listar_contas", lambda: ["cozilatti"])
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    monkeypatch.setattr(bot, "_dados_alerta_da_conta",
                        lambda conta, avisados, hoje: (
                            [_envio(1, hoje)],
                            [core.ItemPedido(order_id=1, shipment_id=1, chave="A02",
                                            nome="A02", quantidade=1)],
                        ))

    def _shopee_com_erro(avisados, hoje):
        raise RuntimeError("falha de rede shopee")

    monkeypatch.setattr(bot, "_dados_alerta_shopee", _shopee_com_erro)
    enviados = []
    ctx = _ctx([10], lambda cid, txt: enviados.append((cid, txt)))

    asyncio.run(bot.job_alerta_pos_horario(ctx))

    assert len(enviados) == 1  # ML ainda avisou, mesmo com a Shopee falhando


def test_job_alerta_shopee_sem_novidade_nao_envia(monkeypatch, tmp_path):
    monkeypatch.setattr(shopee, "ARQUIVO_CRED", tmp_path / "credenciais_shopee.json")
    shopee.ARQUIVO_CRED.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(core, "listar_contas", lambda: [])
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    monkeypatch.setattr(bot, "_dados_alerta_da_conta", lambda conta, avisados, hoje: ([], []))
    monkeypatch.setattr(bot, "_dados_alerta_shopee", lambda avisados, hoje: ([], []))
    enviados = []
    ctx = _ctx([10], lambda cid, txt: enviados.append((cid, txt)))

    asyncio.run(bot.job_alerta_pos_horario(ctx))

    assert enviados == []


# ------------------------------------------------ _testar_alerta_pos_horario_agora
def test_testar_alerta_cli_chama_job_uma_vez_com_contexto_real(monkeypatch):
    """CLI 'python bot_telegram.py testar-alerta': monta um Application de
    verdade (aqui, fake) e chama job_alerta_pos_horario uma unica vez, fora
    do agendamento -- sem reimplementar a logica do alerta."""
    chamadas = []

    async def _job_fake(ctx):
        chamadas.append(ctx)

    class _FakeBot:
        pass

    class _FakeApp:
        def __init__(self):
            self.bot = _FakeBot()
            self.bot_data = {}

        async def initialize(self):
            pass

        async def shutdown(self):
            pass

    class _FakeBuilder:
        def token(self, tok):
            return self

        def build(self):
            return _FakeApp()

    monkeypatch.setattr(bot, "ApplicationBuilder", lambda: _FakeBuilder())
    monkeypatch.setattr(bot, "job_alerta_pos_horario", _job_fake)
    monkeypatch.setattr(core, "aplicar_config", lambda: {})
    monkeypatch.setattr(bot, "_garantir_conta_ativa", lambda: "")
    monkeypatch.setattr(bot, "carregar_config",
                        lambda: {"token": "123:ABC", "chat_ids": [1]})

    bot._testar_alerta_pos_horario_agora()

    assert len(chamadas) == 1
    assert chamadas[0].bot_data["cfg"]["chat_ids"] == [1]


# ------------------------------------------------------------------ cmd_vendas_apos
def _update(chat_id):
    class _Chat:
        id = chat_id

    class _Update:
        effective_chat = _Chat()

    return _Update()


def test_cmd_vendas_apos_junta_tudo_que_ja_foi_avisado(monkeypatch):
    monkeypatch.setattr(core, "listar_contas", lambda: ["Cozilatti"])
    monkeypatch.setattr(bot, "_carregar_alertas", lambda: {
        "dia": "2026-07-24",
        "avisados": {"Cozilatti": [1]},
        "itens": {"Cozilatti": [{"chave": "A01", "quantidade": 1}]},
    })
    enviados, extras = [], []
    ctx = _ctx([1], lambda cid, txt: enviados.append((cid, txt)), extras)

    asyncio.run(bot.cmd_vendas_apos(_update(1), ctx))

    assert len(enviados) == 1, "o resumo vai em UMA mensagem (dividir partiria o <pre>)"
    assert "<b>RESUMO DE VENDAS</b>" in enviados[0][1]
    assert "A01" in enviados[0][1]


def test_cmd_vendas_apos_envia_como_html(monkeypatch):
    """Sem parse_mode="HTML" as tags aparecem cruas na tela; sem
    disable_web_page_preview o Telegram pode pendurar um cartao de link."""
    monkeypatch.setattr(core, "listar_contas", lambda: ["Cozilatti"])
    monkeypatch.setattr(bot, "_carregar_alertas", lambda: {
        "dia": "2026-07-24", "avisados": {},
        "itens": {"Cozilatti": [{"chave": "A01", "quantidade": 1}]},
    })
    extras = []
    ctx = _ctx([1], lambda cid, txt: None, extras)

    asyncio.run(bot.cmd_vendas_apos(_update(1), ctx))

    assert extras[0]["parse_mode"] == "HTML"
    assert extras[0]["disable_web_page_preview"] is True


def test_resumo_inclui_conta_sem_venda_do_dia(monkeypatch):
    """A conta que nao vendeu nada hoje nem chave tem no estado — quem a coloca
    na mensagem e `_contas_do_resumo`, lendo as contas cadastradas."""
    monkeypatch.setattr(core, "listar_contas", lambda: ["Cozilatti", "Gastromaq"])
    envio = bot._resumo_para_envio({"Cozilatti": [{"chave": "A01", "quantidade": 1}]})
    assert "GASTROMAQ" in envio["text"] and "nenhuma venda" in envio["text"]


def test_falha_ao_listar_contas_nao_derruba_o_resumo(monkeypatch):
    """O bloco "nenhuma venda" e enfeite util; o resumo em si nao pode depender
    de conseguir ler a pasta de contas."""
    def _explode():
        raise OSError("disco fora do ar")

    monkeypatch.setattr(core, "listar_contas", _explode)
    envio = bot._resumo_para_envio({"Cozilatti": [{"chave": "A01", "quantidade": 1}]})
    assert "COZILATTI" in envio["text"]


def test_cmd_vendas_apos_sem_nada_avisado(monkeypatch):
    monkeypatch.setattr(bot, "_carregar_alertas",
                        lambda: {"dia": "2026-07-24", "avisados": {}, "itens": {}})
    monkeypatch.setattr(core, "listar_contas", lambda: [])
    enviados = []
    ctx = _ctx([1], lambda cid, txt: enviados.append((cid, txt)))

    asyncio.run(bot.cmd_vendas_apos(_update(1), ctx))

    assert enviados == [(1, "Nenhuma venda avisada hoje ainda.")]


def test_cmd_vendas_apos_nao_autorizado(monkeypatch):
    monkeypatch.setattr(bot, "_carregar_alertas",
                        lambda: {"dia": "2026-07-24", "avisados": {}, "itens": {}})
    enviados = []
    ctx = _ctx([999], lambda cid, txt: enviados.append((cid, txt)))  # 1 nao esta liberado

    asyncio.run(bot.cmd_vendas_apos(_update(1), ctx))

    assert len(enviados) == 1
    assert "Nao autorizado" in enviados[0][1]


def test_botao_vendas_apos_entrega_o_MESMO_formato_do_comando(monkeypatch):
    """O menu tem o botao "🔔 Vendas apos" (callback_data="vendas_apos") e o
    chat tem o /vendasapos. Sao dois caminhos ATE a mesma funcao — este teste
    fixa isso: se alguem um dia responder o botao por outro caminho, o formato
    divergiria em silencio e so o dono descobriria, no celular.
    """
    monkeypatch.setattr(core, "listar_contas", lambda: ["Cozilatti", "Gastromaq"])
    monkeypatch.setattr(bot, "_carregar_alertas", lambda: {
        "dia": "2026-07-30", "avisados": {},
        "itens": {"Cozilatti": [{"chave": "A11", "quantidade": 10}],
                  "Gastromaq": [{"chave": "A11", "quantidade": 1}]},
    })

    def _rodar(update):
        enviados, extras = [], []
        ctx = _ctx([1], lambda cid, txt: enviados.append(txt), extras)
        asyncio.run(bot.cmd_vendas_apos(update, ctx))
        return enviados, extras

    por_comando, extras_cmd = _rodar(_update(1))
    por_botao, extras_bt = _rodar(_botao(1))

    assert por_comando == por_botao, "botao e comando divergiram no texto"
    assert extras_cmd == extras_bt, "botao e comando divergiram no parse_mode"
    assert "<b>RESUMO DE VENDAS</b>" in por_botao[0]
    assert "TOTAL POR SKU" in por_botao[0]          # consolidado tambem vem
    # a soma, sem depender do espacamento (que varia com o SKU mais longo)
    consolidado = por_botao[0].split("TOTAL POR SKU")[1]
    assert consolidado.split("<pre>")[1].split("</pre>")[0].split() == ["A11", "11"]


def _botao(chat_id):
    """Update de clique em botao: nao tem `message`, so `effective_chat` — por
    isso `cmd_vendas_apos` envia por chat_id em vez de `reply_text`."""
    class _Chat:
        id = chat_id

    class _Update:
        effective_chat = _Chat()
        message = None
        callback_query = object()

    return _Update()
