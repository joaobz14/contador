"""Testes do /perguntas — o comando que ACIONA o n8n e nao responde nada.

Tres coisas que este teste protege (as tres ja quase deram errado no projeto):

1. **Quem pode.** O comando fala de uma conta especifica do dono, entao e
   restrito a UM chat (`chat_perguntas`), nao a whitelist inteira. Qualquer
   outro chat e ignorado em silencio — nem confirma que o comando existe.
2. **A URL nunca aparece.** O webhook nao pede autenticacao: quem tem o link
   dispara o fluxo. Nenhuma mensagem de erro pode carregar a URL (o repositorio
   e publico e o dono cola log/print quando pede ajuda).
3. **Falha de rede nao derruba o bot.** O disparo e best-effort: n8n fora do ar
   vira um aviso no chat, nunca uma excecao subindo pelo handler.

Mesmo padrao dos outros testes do bot: pula se o telegram nao importar.
"""
from __future__ import annotations

import asyncio

import pytest

try:
    import bot_telegram as bot
except BaseException as e:  # noqa: BLE001 - pyo3 PanicException herda de BaseException
    pytest.skip(f"bot_telegram indisponivel: {e}", allow_module_level=True)

import registro  # noqa: E402
import separador_etiquetas_ml as core  # noqa: E402

CHAT_DONO = 725104161
OUTRO_CHAT = 999000111
URL = "https://exemplo.app.n8n.cloud/webhook/perguntas-conta3-9f4c2a7be13d"


def _cfg(**extra):
    base = {
        "token": "x",
        "chat_ids": {CHAT_DONO, OUTRO_CHAT},
        "aviso_horario": "",
        "webhook_perguntas": URL,
        "chat_perguntas": CHAT_DONO,
    }
    base.update(extra)
    return base


class _Bot:
    """Dublê do bot: guarda o que foi enviado, por chat."""

    def __init__(self):
        self.enviadas: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text=None, **k):
        self.enviadas.append((chat_id, text if text is not None else k.get("text", "")))


class _Update:
    def __init__(self, chat_id):
        self.effective_chat = type("C", (), {"id": chat_id})()


class _Ctx:
    def __init__(self, cfg, bot_duble):
        self.bot_data = {"cfg": cfg}
        self.bot = bot_duble


def _rodar(chat_id, cfg, disparo):
    """Roda cmd_perguntas com o disparo dublado. Devolve (mensagens, chamadas)."""
    duble = _Bot()
    chamadas: list[str] = []

    def _falso(url, chat_id):
        chamadas.append(url)
        return disparo(url) if disparo else None

    original = bot._disparar_perguntas
    bot._disparar_perguntas = _falso
    try:
        asyncio.run(bot.cmd_perguntas(_Update(chat_id), _Ctx(cfg, duble)))
    finally:
        bot._disparar_perguntas = original
    return duble.enviadas, chamadas


# ------------------------------------------------------------------ quem pode
def test_chat_do_dono_dispara_o_webhook():
    enviadas, chamadas = _rodar(CHAT_DONO, _cfg(), None)
    assert chamadas == [URL]
    assert len(enviadas) == 1, "so o aviso imediato — a RESPOSTA vem do n8n"
    assert "Consultando" in enviadas[0][1]
    assert enviadas[0][0] == CHAT_DONO


def test_outro_chat_autorizado_e_ignorado_em_silencio():
    """Esta na whitelist do bot, mas nao e o chat_perguntas: nada acontece."""
    enviadas, chamadas = _rodar(OUTRO_CHAT, _cfg(), None)
    assert chamadas == []
    assert enviadas == [], "responder ja confirmaria que o comando existe"


def test_estranho_e_ignorado_em_silencio():
    enviadas, chamadas = _rodar(123456, _cfg(), None)
    assert chamadas == []
    assert enviadas == []


def test_sem_configuracao_explica_ao_dono_em_vez_de_silenciar():
    """Sem `chat_perguntas`, o comando fica desligado — mas quem esta autorizado
    precisa saber POR QUE (senao o sintoma e um comando que nao faz nada)."""
    enviadas, chamadas = _rodar(CHAT_DONO, _cfg(chat_perguntas=0), None)
    assert chamadas == []
    assert len(enviadas) == 1
    assert "webhook_perguntas" in enviadas[0][1]


def test_configurado_mas_sem_url_tambem_explica():
    enviadas, chamadas = _rodar(CHAT_DONO, _cfg(webhook_perguntas=""), None)
    assert chamadas == []
    assert "bot_config.json" in enviadas[0][1]


# --------------------------------------------------------------- falha de rede
def _estourar(exc):
    def _f(url):
        raise exc
    return _f



def test_falha_do_n8n_vira_aviso_e_nao_derruba_o_bot():
    enviadas, _ = _rodar(CHAT_DONO, _cfg(),
                         _estourar(core.SeparadorError("nao consegui falar com o n8n")))
    assert len(enviadas) == 2                      # "Consultando" + o aviso
    assert "Nao consegui acionar" in enviadas[1][1]


def test_falha_inesperada_tambem_e_contida():
    enviadas, _ = _rodar(CHAT_DONO, _cfg(), _estourar(RuntimeError("boom")))
    assert len(enviadas) == 2
    assert "Falha inesperada" in enviadas[1][1]


def test_nenhuma_mensagem_de_erro_carrega_a_url():
    """A URL e a senha do webhook. Nenhum caminho de erro pode coloca-la no chat."""
    for erro in (core.SeparadorError(f"falhou em {URL}"), RuntimeError(f"POST {URL}")):
        enviadas, _ = _rodar(CHAT_DONO, _cfg(), _estourar(erro))
        texto = " ".join(t for _, t in enviadas)
        assert "9f4c2a7be13d" not in texto, "sufixo do webhook vazou para o chat"


# --------------------------------------------------- _disparar_perguntas (rede)
def test_disparar_manda_o_corpo_combinado_com_o_n8n(monkeypatch):
    visto = {}

    def _post(url, json=None, timeout=None):
        visto.update(url=url, json=json, timeout=timeout)
        return type("R", (), {"status_code": 200})()

    monkeypatch.setattr(bot.requests, "post", _post)
    bot._disparar_perguntas(URL, CHAT_DONO)
    assert visto["json"] == {"origem": "telegram", "comando": "/perguntas",
                             "chat_id": CHAT_DONO}
    assert visto["timeout"] == bot.TIMEOUT_PERGUNTAS
    assert visto["url"] == URL


def test_chat_id_enviado_e_o_de_quem_disparou(monkeypatch):
    """O fluxo do n8n responde a QUEM PERGUNTOU. Se o chat_id nao for o do
    disparo, a resposta vai para o chat errado — e o dono so descobre quando
    outra pessoa recebe o dado dele."""
    visto = {}
    monkeypatch.setattr(bot, "_disparar_perguntas",
                        lambda url, chat_id: visto.update(url=url, chat_id=chat_id))
    duble = _Bot()
    asyncio.run(bot.cmd_perguntas(_Update(CHAT_DONO), _Ctx(_cfg(), duble)))
    assert visto == {"url": URL, "chat_id": CHAT_DONO}


def test_disparar_converte_erro_http_sem_vazar_a_url(monkeypatch):
    monkeypatch.setattr(bot.requests, "post",
                        lambda *a, **k: type("R", (), {"status_code": 404})())
    with pytest.raises(core.SeparadorError) as e:
        bot._disparar_perguntas(URL, CHAT_DONO)
    assert "404" in str(e.value)
    assert "9f4c2a7be13d" not in str(e.value)


def test_disparar_converte_falha_de_transporte_sem_vazar_a_url(monkeypatch):
    """A excecao crua do requests traz "Max retries exceeded with url: ..." —
    exatamente a URL que nao pode aparecer. Mesmo motivo do _rede_limpa da
    Shopee, incluindo o `from None` (traceback nao arrasta a original)."""
    import requests

    def _explodir(*a, **k):
        raise requests.ConnectionError(f"Max retries exceeded with url: {URL}")

    monkeypatch.setattr(bot.requests, "post", _explodir)
    with pytest.raises(core.SeparadorError) as e:
        bot._disparar_perguntas(URL, CHAT_DONO)
    assert "9f4c2a7be13d" not in str(e.value)
    # `from None`: e o __suppress_context__ que faz um traceback logado NAO
    # imprimir a original (o __context__ continua no objeto, so nao e exibido).
    assert e.value.__cause__ is None
    assert e.value.__suppress_context__, "sem isso o log.exception mostraria a URL"


def test_sem_segredos_redige_o_caminho_do_webhook():
    """Ultima camada: se a URL escapar por algum caminho novo, o redator pega."""
    assert "9f4c2a7be13d" not in registro.sem_segredos(f"falhou: {URL}")
    assert "/webhook/***" in registro.sem_segredos(URL)


# ----------------------------------------------------------- menu e teclado
def test_menu_do_dono_tem_perguntas_e_o_dos_outros_nao():
    cfg = _cfg()
    do_dono = bot._comandos_do_chat(CHAT_DONO, cfg)
    do_outro = bot._comandos_do_chat(OUTRO_CHAT, cfg)
    assert bot.COMANDO_PERGUNTAS in do_dono
    assert bot.COMANDO_PERGUNTAS not in do_outro


def test_menu_mantem_os_comandos_que_ja_existiam():
    """O setMyCommands SUBSTITUI a lista inteira: esquecer um comando aqui o
    apaga do menu do app. Guardiao dos que ja existiam antes do /perguntas."""
    nomes = {c for c, _ in bot._comandos_do_chat(CHAT_DONO, _cfg())}
    assert {"hoje", "amanha", "todos", "resumo", "vendasapos", "dia", "detalhar",
            "loja", "conta", "versao", "menu", "id", "perguntas"} <= nomes


def test_todo_comando_registrado_esta_no_menu():
    """Comando novo tem de entrar no COMANDOS_MENU — senao existe mas nao
    aparece no "/" do app (e ninguem descobre que ele existe)."""
    import re
    from pathlib import Path

    fonte = Path(bot.__file__).read_text(encoding="utf-8")
    registrados: set[str] = set()
    for bloco in re.findall(r'CommandHandler\(\s*(\[[^\]]*\]|"[^"]*")', fonte):
        registrados.update(re.findall(r'"([^"]+)"', bloco))
    no_menu = {c for c, _ in bot._comandos_do_chat(CHAT_DONO, _cfg())}
    faltando = registrados - no_menu - {"start", "ajuda"}   # apelidos do /menu
    assert not faltando, f"comando(s) fora do COMANDOS_MENU: {sorted(faltando)}"


def test_botao_perguntas_so_aparece_para_quem_pode():
    com = bot._teclado("Mercado Livre", perguntas=True).inline_keyboard
    sem = bot._teclado("Mercado Livre", perguntas=False).inline_keyboard
    callbacks_com = [b.callback_data for linha in com for b in linha]
    callbacks_sem = [b.callback_data for linha in sem for b in linha]
    assert "perguntas" in callbacks_com
    assert "perguntas" not in callbacks_sem
    # os botoes de sempre continuam la, e a loja segue por ultimo
    assert {"hoje", "amanha", "resumo", "todos", "vendas_apos", "loja"} <= set(callbacks_sem)
    assert callbacks_com[-1] == "loja"


def test_pode_perguntas_exige_configuracao_explicita():
    assert bot._pode_perguntas(CHAT_DONO, _cfg())
    assert not bot._pode_perguntas(CHAT_DONO, _cfg(chat_perguntas=0))
    assert not bot._pode_perguntas(OUTRO_CHAT, _cfg())


# ------------------------------------------------------------------- config
def test_config_le_webhook_e_chat(tmp_path, monkeypatch):
    arq = tmp_path / "bot_config.json"
    core._gravar_json(arq, {"token": "t", "chat_ids": [CHAT_DONO],
                            "webhook_perguntas": URL, "chat_perguntas": CHAT_DONO})
    monkeypatch.setattr(bot, "ARQUIVO_CONFIG", arq)
    monkeypatch.delenv("N8N_WEBHOOK_PERGUNTAS", raising=False)
    cfg = bot.carregar_config()
    assert cfg["webhook_perguntas"] == URL
    assert cfg["chat_perguntas"] == CHAT_DONO


def test_config_invalida_desliga_o_comando_sem_derrubar_o_bot(tmp_path, monkeypatch):
    """bot_config.json editado a mao nao pode impedir o bot de subir."""
    arq = tmp_path / "bot_config.json"
    core._gravar_json(arq, {"token": "t", "chat_ids": [CHAT_DONO],
                            "chat_perguntas": "nao-e-numero"})
    monkeypatch.setattr(bot, "ARQUIVO_CONFIG", arq)
    monkeypatch.delenv("N8N_WEBHOOK_PERGUNTAS", raising=False)
    cfg = bot.carregar_config()
    assert cfg["chat_perguntas"] == 0
    assert not bot._pode_perguntas(CHAT_DONO, cfg)


def test_variavel_de_ambiente_vence_o_arquivo(tmp_path, monkeypatch):
    arq = tmp_path / "bot_config.json"
    core._gravar_json(arq, {"token": "t", "chat_ids": [], "webhook_perguntas": "do-arquivo"})
    monkeypatch.setattr(bot, "ARQUIVO_CONFIG", arq)
    monkeypatch.setenv("N8N_WEBHOOK_PERGUNTAS", "do-ambiente")
    assert bot.carregar_config()["webhook_perguntas"] == "do-ambiente"
