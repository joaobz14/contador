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


@pytest.fixture(autouse=True)
def _arquivo_alertas_isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "ARQUIVO_ALERTAS", tmp_path / "alertas.json")


def _envio(sid, dia, item_id=1):
    return {"id": item_id, "_envio": {"shipment_id": sid, "expected_date": dia}}


# ------------------------------------------------------- _carregar/_salvar_alertas
def test_carregar_alertas_comeca_vazio_sem_arquivo(monkeypatch):
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    dados = bot._carregar_alertas()
    assert dados == {"dia": "2026-07-24", "avisados": {}}


def test_carregar_alertas_preserva_mesmo_dia(monkeypatch):
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    bot._salvar_alertas({"dia": "2026-07-24", "avisados": {"cozilatti": [1, 2]}})
    dados = bot._carregar_alertas()
    assert dados["avisados"] == {"cozilatti": [1, 2]}


def test_carregar_alertas_reseta_quando_dia_muda(monkeypatch):
    bot._salvar_alertas({"dia": "2026-07-23", "avisados": {"cozilatti": [1, 2]}})
    monkeypatch.setattr(core, "_hoje_br", lambda: "2026-07-24")
    dados = bot._carregar_alertas()
    assert dados == {"dia": "2026-07-24", "avisados": {}}


# ------------------------------------------------------------ _dados_alerta_da_conta
def test_dados_alerta_filtra_por_hoje_e_dedup(monkeypatch):
    prontos = [_envio(1, "2026-07-24"), _envio(2, "2026-07-23"), _envio(3, "2026-07-24")]
    monkeypatch.setattr(core, "conta_ativa", lambda: "")
    monkeypatch.setattr(core, "definir_conta", lambda nome: None)
    monkeypatch.setattr(bot, "_prontos", lambda: prontos)
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
    monkeypatch.setattr(bot, "_prontos", lambda: [_envio(1, "2026-07-24")])
    chamou = []
    monkeypatch.setattr(core, "extrair_itens", lambda *a, **k: chamou.append(1))

    novos, itens = bot._dados_alerta_da_conta("cozilatti", avisados={1}, hoje="2026-07-24")

    assert novos == [] and itens == []
    assert chamou == []


def test_dados_alerta_troca_e_restaura_conta(monkeypatch):
    trocas = []
    monkeypatch.setattr(core, "conta_ativa", lambda: "gastromaq")
    monkeypatch.setattr(core, "definir_conta", lambda nome: trocas.append(nome))
    monkeypatch.setattr(bot, "_prontos", lambda: [])
    monkeypatch.setattr(core, "extrair_itens", lambda *a, **k: [])

    bot._dados_alerta_da_conta("cozilatti", avisados=set(), hoje="2026-07-24")

    # troca pra cozilatti (checagem) e volta pra gastromaq (conta original) no final.
    assert trocas == ["cozilatti", "gastromaq"]


def test_dados_alerta_nao_troca_se_ja_e_a_conta_ativa(monkeypatch):
    trocas = []
    monkeypatch.setattr(core, "conta_ativa", lambda: "cozilatti")
    monkeypatch.setattr(core, "definir_conta", lambda nome: trocas.append(nome))
    monkeypatch.setattr(bot, "_prontos", lambda: [])

    bot._dados_alerta_da_conta("cozilatti", avisados=set(), hoje="2026-07-24")

    assert trocas == []


# ------------------------------------------------------------------- job_alerta
def _ctx(chat_ids, send):
    class _Bot:
        async def send_message(self, chat_id, texto, **k):
            return send(chat_id, texto)

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


# ---------------------------------------------------------------- lock de PID
def test_escrever_e_limpar_lock_bot(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_LOCK_BOT", tmp_path / "bot.lock")
    bot._escrever_lock_bot()
    assert core.ARQUIVO_LOCK_BOT.read_text(encoding="utf-8").strip() == str(bot.os.getpid())
    bot._limpar_lock_bot()
    assert not core.ARQUIVO_LOCK_BOT.exists()


def test_limpar_lock_bot_nao_apaga_lock_de_outro_processo(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_LOCK_BOT", tmp_path / "bot.lock")
    core.ARQUIVO_LOCK_BOT.write_text("999999", encoding="utf-8")
    bot._limpar_lock_bot()
    assert core.ARQUIVO_LOCK_BOT.exists()  # PID nao bate com o deste processo -- nao mexe
