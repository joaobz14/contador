"""
bot_telegram.py
Bot do Telegram para CONSULTAR os pedidos (somente leitura) de qualquer lugar.
Reaproveita o nucleo (separador_etiquetas_ml.py); nao imprime nem altera estado.

Seguranca:
  - o token NUNCA fica no codigo: vem da variavel TELEGRAM_BOT_TOKEN ou do
    arquivo bot_config.json (que NAO e versionado);
  - so responde aos chat ids autorizados (whitelist em bot_config.json).

Como usar:
  1) pip install -r requirements-bot.txt
  2) copie bot_config.example.json para bot_config.json e preencha o token
  3) python bot_telegram.py   (precisa do credenciais.json do ML na mesma pasta)
  4) no Telegram mande /id para descobrir seu chat id, coloque em bot_config.json
     na lista "chat_ids", e reinicie o bot.

Comandos: /hoje  /amanha  /dia AAAA-MM-DD  /todos  /detalhar SKU  /resumo  /id  /start
Onde rodar: numa maquina sempre ligada e com internet, que tenha o projeto e o
credenciais.json (ex.: o PC do escritorio).
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

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
    autorizados = {int(c) for c in cfg.get("chat_ids", [])}
    return {"token": token, "chat_ids": autorizados}


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


# ---------------------------------------------------------------- autorizacao / envio
def _autorizado(update: Update, cfg: dict) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id in cfg["chat_ids"])


async def _enviar(update: Update, texto: str) -> None:
    for bloco in relatorio.dividir_mensagem(texto):
        await update.message.reply_text(bloco)


async def _responder(update, context, nome: str, executor) -> None:
    """Roda uma consulta (em thread, para nao travar o bot), com autorizacao,
    log e tratamento de erro padronizados."""
    cfg = context.bot_data["cfg"]
    chat_id = update.effective_chat.id if update.effective_chat else "?"
    if not _autorizado(update, cfg):
        log.warning("Comando /%s negado para chat %s", nome, chat_id)
        await update.message.reply_text("Nao autorizado. Use /id e peca para liberar seu chat.")
        return
    log.info("Comando /%s de chat %s", nome, chat_id)
    await update.message.reply_text("Consultando o Mercado Livre, um instante...")
    try:
        texto = await asyncio.to_thread(executor)
    except core.SeparadorError as e:
        await update.message.reply_text(f"Erro: {e}")
        return
    except Exception as e:  # noqa: BLE001 - mostrar qualquer falha ao usuario
        log.exception("Falha no comando /%s", nome)
        await update.message.reply_text(f"Falha inesperada: {e}")
        return
    await _enviar(update, texto)


# ---------------------------------------------------------------- comandos
AJUDA = (
    "Bot de consulta de pedidos (somente leitura).\n\n"
    "/hoje — grupos prontos para HOJE\n"
    "/amanha — grupos de amanha\n"
    "/dia AAAA-MM-DD — grupos de um dia especifico\n"
    "/todos — grupos de todos os dias\n"
    "/detalhar SKU — composicao de um SKU (hoje)\n"
    "/resumo — quantos pacotes por dia\n"
    "/id — mostra seu chat id"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(AJUDA)


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Seu chat id e: {update.effective_chat.id}")


async def cmd_hoje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _responder(update, context, "hoje",
                     lambda: relatorio.texto_grupos(_coletar(None, True).grupos, "HOJE"))


async def cmd_amanha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dia = core._amanha_br()
    await _responder(update, context, "amanha",
                     lambda: relatorio.texto_grupos(_coletar(dia, False).grupos, f"AMANHA ({dia})"))


async def cmd_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _responder(update, context, "todos",
                     lambda: relatorio.texto_grupos(_coletar(None, False).grupos, "TODOS OS DIAS"))


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


async def cmd_desconhecido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Nao entendi. Mande /start para ver os comandos.")


# ---------------------------------------------------------------- inicializacao
def main() -> None:
    cfg = carregar_config()
    app = ApplicationBuilder().token(cfg["token"]).build()
    app.bot_data["cfg"] = cfg
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ajuda", cmd_start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("hoje", cmd_hoje))
    app.add_handler(CommandHandler("amanha", cmd_amanha))
    app.add_handler(CommandHandler("todos", cmd_todos))
    app.add_handler(CommandHandler("dia", cmd_dia))
    app.add_handler(CommandHandler("detalhar", cmd_detalhar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_desconhecido))
    log.info("Bot iniciado (%d chat(s) autorizado(s)).", len(cfg["chat_ids"]))
    print("Bot rodando... Ctrl+C para parar.")
    app.run_polling()


if __name__ == "__main__":
    main()
