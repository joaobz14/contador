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

Comandos: /hoje  /amanha  /resumo  /id  /start
Onde rodar: numa maquina sempre ligada e com internet, que tenha o projeto e o
credenciais.json (ex.: o PC do escritorio).
"""

from __future__ import annotations

import asyncio
import os

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

import relatorio
import separador_etiquetas_ml as core

ARQUIVO_CONFIG = core.PASTA_SCRIPT / "bot_config.json"


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
def _grupos_do_dia(dia: str | None, somente_hoje: bool):
    cred = core.carregar_credenciais()
    token = core.renovar_token(cred)
    return core.coletar_grupos(token, cred["seller_id"], dia=dia, somente_hoje=somente_hoje)


def _prontos():
    cred = core.carregar_credenciais()
    token = core.renovar_token(cred)
    pedidos = core.buscar_pedidos(token, cred["seller_id"])
    return core.filtrar_para_imprimir(token, pedidos)


# ---------------------------------------------------------------- autorizacao
def _autorizado(update: Update, cfg: dict) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id in cfg["chat_ids"])


async def _responder_consulta(update, context, executor, titulo_ok):
    cfg = context.bot_data["cfg"]
    if not _autorizado(update, cfg):
        await update.message.reply_text("Nao autorizado. Use /id e peca para liberar seu chat.")
        return
    await update.message.reply_text("Consultando o Mercado Livre, um instante...")
    try:
        texto = await asyncio.to_thread(executor)
    except core.SeparadorError as e:
        await update.message.reply_text(f"Erro: {e}")
        return
    except Exception as e:  # noqa: BLE001 - mostrar qualquer falha ao usuario
        await update.message.reply_text(f"Falha inesperada: {e}")
        return
    await update.message.reply_text(texto)


# ---------------------------------------------------------------- comandos
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot de consulta de pedidos (somente leitura).\n"
        "Comandos: /hoje  /amanha  /resumo  /id"
    )


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Seu chat id e: {update.effective_chat.id}")


async def cmd_hoje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _responder_consulta(
        update, context,
        lambda: relatorio.texto_grupos(_grupos_do_dia(None, True).grupos, "HOJE"),
        "HOJE",
    )


async def cmd_amanha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dia = core._amanha_br()
    await _responder_consulta(
        update, context,
        lambda: relatorio.texto_grupos(_grupos_do_dia(dia, False).grupos, f"AMANHA ({dia})"),
        "AMANHA",
    )


async def cmd_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _responder_consulta(
        update, context,
        lambda: relatorio.texto_resumo(_prontos(), core._hoje_br(), core._amanha_br()),
        "RESUMO",
    )


# ---------------------------------------------------------------- inicializacao
def main() -> None:
    cfg = carregar_config()
    app = ApplicationBuilder().token(cfg["token"]).build()
    app.bot_data["cfg"] = cfg
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("hoje", cmd_hoje))
    app.add_handler(CommandHandler("amanha", cmd_amanha))
    app.add_handler(CommandHandler("resumo", cmd_resumo))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda u, c: u.message.reply_text("Use /hoje, /amanha, /resumo ou /id."),
    ))
    print("Bot rodando... Ctrl+C para parar.")
    app.run_polling()


if __name__ == "__main__":
    main()
