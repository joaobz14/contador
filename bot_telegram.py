"""
bot_telegram.py
Bot do Telegram para CONSULTAR os pedidos (somente leitura) de qualquer lugar.
Reaproveita o nucleo (separador_etiquetas_ml.py); nao imprime nem altera estado.

Seguranca:
  - o token NUNCA fica no codigo: vem da variavel TELEGRAM_BOT_TOKEN ou do
    arquivo bot_config.json (que NAO e versionado);
  - so responde aos chat ids autorizados (whitelist em bot_config.json).

Recursos:
  - comandos /hoje /amanha /dia /todos /detalhar /resumo /id /menu;
  - botoes (toque em vez de digitar) via /start ou /menu;
  - aviso automatico de manha (se "aviso_horario" estiver no bot_config.json).

Como usar:
  1) pip install -r requirements-bot.txt
  2) copie bot_config.example.json para bot_config.json e preencha o token
  3) python bot_telegram.py   (precisa do credenciais.json do ML na mesma pasta)
  4) no Telegram mande /id, coloque o numero em "chat_ids", e reinicie o bot.

Onde rodar: numa maquina sempre ligada e com internet, que tenha o projeto e o
credenciais.json (ex.: o PC do escritorio). O aviso da manha so dispara com o
bot ligado no horario.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import relatorio
import separador_etiquetas_ml as core

ARQUIVO_CONFIG = core.PASTA_SCRIPT / "bot_config.json"
ARQUIVO_LOG = core.PASTA_SCRIPT / "bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(ARQUIVO_LOG, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("bot")


# ---------------------------------------------------------------- configuracao
def carregar_config() -> dict:
    cfg = core._ler_json(ARQUIVO_CONFIG)
    token = os.getenv("TELEGRAM_BOT_TOKEN") or cfg.get("token", "")
    if not token:
        raise core.SeparadorError(
            "Token do bot ausente. Defina TELEGRAM_BOT_TOKEN ou 'token' no bot_config.json."
        )
    return {
        "token": token,
        "chat_ids": {int(c) for c in cfg.get("chat_ids", [])},
        "aviso_horario": (cfg.get("aviso_horario") or "").strip(),
    }


# ---------------------------------------------------------------- coleta (rede)
def _coletar(dia: str | None, somente_hoje: bool):
    cred = core.carregar_credenciais()
    token = core.renovar_token(cred)
    return core.coletar_grupos(token, cred["seller_id"], dia=dia, somente_hoje=somente_hoje)


def _prontos():
    cred = core.carregar_credenciais()
    token = core.renovar_token(cred)
    pedidos = core.buscar_pedidos(token, cred["seller_id"])
    return core.filtrar_para_imprimir(token, pedidos)


def _data_valida(texto: str) -> bool:
    try:
        datetime.strptime(texto, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# executores nomeados reutilizados por comandos e botoes
def _exec_hoje():
    return relatorio.texto_grupos(_coletar(None, True).grupos, "HOJE")


def _exec_amanha():
    dia = core._amanha_br()
    return relatorio.texto_grupos(_coletar(dia, False).grupos, f"AMANHA ({dia})")


def _exec_todos():
    return relatorio.texto_grupos(_coletar(None, False).grupos, "TODOS OS DIAS")


def _exec_resumo():
    return relatorio.texto_resumo(_prontos(), core._hoje_br(), core._amanha_br())


EXECUTORES = {"hoje": _exec_hoje, "amanha": _exec_amanha,
              "todos": _exec_todos, "resumo": _exec_resumo}


# ---------------------------------------------------------------- autorizacao / envio
def _autorizado(update: Update, cfg: dict) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id in cfg["chat_ids"])


def _teclado() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Hoje", callback_data="hoje"),
         InlineKeyboardButton("📅 Amanhã", callback_data="amanha")],
        [InlineKeyboardButton("📊 Resumo", callback_data="resumo"),
         InlineKeyboardButton("🗂 Todos", callback_data="todos")],
    ])


async def _responder(update, context, nome: str, executor) -> None:
    """Roda uma consulta (em thread), com autorizacao, log e erro padronizados.
    Envia por chat_id, entao serve tanto para comandos quanto para botoes."""
    cfg = context.bot_data["cfg"]
    chat_id = update.effective_chat.id if update.effective_chat else None
    if not _autorizado(update, cfg):
        log.warning("Acao /%s negada para chat %s", nome, chat_id)
        if chat_id:
            await context.bot.send_message(chat_id, "Nao autorizado. Use /id e peca para liberar seu chat.")
        return
    log.info("Acao /%s de chat %s", nome, chat_id)
    await context.bot.send_message(chat_id, "Consultando o Mercado Livre, um instante...")
    try:
        texto = await asyncio.to_thread(executor)
    except core.SeparadorError as e:
        await context.bot.send_message(chat_id, f"Erro: {e}")
        return
    except Exception as e:  # noqa: BLE001 - mostrar qualquer falha ao usuario
        log.exception("Falha na acao /%s", nome)
        await context.bot.send_message(chat_id, f"Falha inesperada: {e}")
        return
    for bloco in relatorio.dividir_mensagem(texto):
        await context.bot.send_message(chat_id, bloco)


# ---------------------------------------------------------------- comandos
AJUDA = (
    "Bot de consulta de pedidos (somente leitura).\n\n"
    "Toque num botao abaixo ou use os comandos:\n"
    "/hoje  /amanha  /todos  /resumo\n"
    "/dia AAAA-MM-DD — um dia especifico\n"
    "/detalhar SKU — composicao de um SKU (hoje)\n"
    "/id — mostra seu chat id"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(AJUDA, reply_markup=_teclado())


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Seu chat id e: {update.effective_chat.id}")


async def cmd_hoje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _responder(update, context, "hoje", _exec_hoje)


async def cmd_amanha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _responder(update, context, "amanha", _exec_amanha)


async def cmd_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _responder(update, context, "todos", _exec_todos)


async def cmd_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _responder(update, context, "resumo", _exec_resumo)


async def cmd_dia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args or not _data_valida(args[0]):
        await update.message.reply_text("Use: /dia AAAA-MM-DD  (ex.: /dia 2026-06-22)")
        return
    dia = args[0]
    await _responder(update, context, "dia",
                     lambda: relatorio.texto_grupos(_coletar(dia, False).grupos, f"DIA {dia}"))


async def cmd_detalhar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await update.message.reply_text("Use: /detalhar SKU  (ex.: /detalhar PRP)")
        return
    sku = args[0]
    await _responder(update, context, "detalhar",
                     lambda: relatorio.texto_detalhe(_coletar(None, True).itens, sku))


async def cb_botao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tratador dos botoes (Hoje/Amanha/Resumo/Todos)."""
    query = update.callback_query
    await query.answer()
    executor = EXECUTORES.get(query.data)
    if executor:
        await _responder(update, context, query.data, executor)


async def cmd_desconhecido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Nao entendi. Mande /menu para ver as opcoes.")


# ---------------------------------------------------------------- aviso da manha
async def job_bom_dia(context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = context.bot_data["cfg"]
    log.info("Disparando aviso da manha para %d chat(s).", len(cfg["chat_ids"]))
    try:
        prontos = await asyncio.to_thread(_prontos)
        texto = relatorio.texto_bom_dia(prontos, core._hoje_br(), core._amanha_br())
    except Exception as e:  # noqa: BLE001
        log.exception("Falha ao montar o aviso da manha")
        texto = f"Nao consegui montar o aviso da manha: {e}"
    for chat_id in cfg["chat_ids"]:
        for bloco in relatorio.dividir_mensagem(texto):
            await context.bot.send_message(chat_id, bloco)


def _agendar_aviso(app, cfg: dict) -> None:
    horario = cfg["aviso_horario"]
    if not horario:
        return
    if app.job_queue is None:
        log.warning("aviso_horario definido, mas JobQueue indisponivel. "
                    "Rode: pip install -r requirements-bot.txt")
        return
    try:
        h, m = (int(x) for x in horario.split(":"))
        app.job_queue.run_daily(job_bom_dia, time=time(hour=h, minute=m, tzinfo=core.TZ_BR))
        log.info("Aviso diario agendado para %s (horario de Brasilia).", horario)
    except (ValueError, TypeError):
        log.warning("aviso_horario invalido: %r (use HH:MM, ex.: 08:00).", horario)


# ---------------------------------------------------------------- inicializacao
def main() -> None:
    cfg = carregar_config()
    app = ApplicationBuilder().token(cfg["token"]).build()
    app.bot_data["cfg"] = cfg

    app.add_handler(CommandHandler(["start", "menu", "ajuda"], cmd_start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("hoje", cmd_hoje))
    app.add_handler(CommandHandler("amanha", cmd_amanha))
    app.add_handler(CommandHandler("todos", cmd_todos))
    app.add_handler(CommandHandler("resumo", cmd_resumo))
    app.add_handler(CommandHandler("dia", cmd_dia))
    app.add_handler(CommandHandler("detalhar", cmd_detalhar))
    app.add_handler(CallbackQueryHandler(cb_botao))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_desconhecido))

    _agendar_aviso(app, cfg)
    log.info("Bot iniciado (%d chat(s) autorizado(s)).", len(cfg["chat_ids"]))
    print("Bot rodando... Ctrl+C para parar.")
    app.run_polling()


if __name__ == "__main__":
    main()
