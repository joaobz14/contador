"""
bot_telegram.py
Bot do Telegram para CONSULTAR e IMPRIMIR os pedidos de qualquer lugar.
Reaproveita o nucleo (separador_etiquetas_ml.py): a consulta e somente leitura;
a impressao reusa exatamente a mesma logica da tela/CLI (imprimir_pendentes).

IMPORTANTE (impressao): imprimir gera um .zip na pasta Downloads DA MAQUINA ONDE
O BOT RODA, que o app da Zebra (impressora_zebra_usb.py) vigia e manda para a
impressora. Logo, para imprimir pelo bot ele precisa estar rodando no PC do
escritorio (com a Zebra e o monitor da Zebra ligados). De longe voce dispara a
impressao; o papel sai la.

Seguranca:
  - o token NUNCA fica no codigo: vem da variavel TELEGRAM_BOT_TOKEN ou do
    arquivo bot_config.json (que NAO e versionado);
  - so responde aos chat ids autorizados (whitelist em bot_config.json);
  - imprimir sempre pede uma confirmacao (Confirmar/Cancelar) antes de gerar a
    etiqueta, para evitar toque acidental pelo celular.

Recursos:
  - comandos /hoje /amanha /dia /todos /detalhar /resumo /id /menu;
  - botoes (toque em vez de digitar) via /start ou /menu;
  - botao "Imprimir" por grupo nas listagens (Hoje/Amanha/Dia/Todos);
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

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import (
        ApplicationBuilder,
        CallbackQueryHandler,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
except ImportError as _erro_import:
    # Dependencia do bot ausente: avisa de forma legivel e MANTEM a janela
    # aberta (senao o cmd fecha rapido e ninguem ve o motivo).
    print("\nNao consegui carregar a biblioteca do Telegram.")
    print("Instale as dependencias do bot rodando no terminal, nesta pasta:\n")
    print("    pip install -r requirements-bot.txt\n")
    print(f"(detalhe tecnico: {_erro_import})")
    try:
        input("\nPressione Enter para fechar...")
    except EOFError:
        pass
    raise SystemExit(1)

import relatorio
import separador_etiquetas_ml as core
import shopee_api as shopee

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
    token = core.obter_token(cred)
    return core.coletar_grupos(token, cred["seller_id"], dia=dia, somente_hoje=somente_hoje)


def _imprimir_grupo(grupo):
    """Imprime os envios ainda pendentes do grupo (reusa o nucleo).

    Roda em thread (chamada de rede + I/O). Devolve a lista de shipment_ids
    impressos (vazia se o grupo ja estava todo impresso). Lanca SeparadorError
    em falha de download/ZPL invalido (nesse caso nada e marcado como impresso).
    """
    cred = core.carregar_credenciais()
    token = core.obter_token(cred)
    estado = core.carregar_estado()
    return core.imprimir_pendentes(token, grupo, estado)


def _prontos():
    cred = core.carregar_credenciais()
    token = core.obter_token(cred)
    pedidos = core.buscar_pedidos(token, cred["seller_id"])
    return core.filtrar_para_imprimir(token, pedidos)


# ---------------------------------------------------------------- contas
def _garantir_conta_ativa() -> str:
    """Garante que aponte para uma conta valida (mesma logica da tela).

    Se a conta salva no config sumiu/for invalida e existirem contas em
    contas/, escolhe a primeira e a torna ativa. Devolve o nome da conta ativa
    ('' quando nao ha nenhuma conta configurada). Sem isto, o bot cairia no
    credenciais.json da raiz (inexistente no setup multi-conta) e falharia.
    """
    contas = core.listar_contas()
    if not contas:
        return ""
    ativa = core.conta_ativa()
    if ativa not in contas:
        ativa = contas[0]
        _trocar_conta(ativa)
    return ativa


def _trocar_conta(nome: str) -> None:
    """Torna `nome` a conta ativa: aponta os arquivos e grava no config.json
    (compartilhado com a tela, para as duas ficarem na mesma conta)."""
    core.definir_conta(nome)
    cfg = core.carregar_config()
    cfg["conta_ativa"] = nome
    core.salvar_config(cfg)


def _data_valida(texto: str) -> bool:
    try:
        datetime.strptime(texto, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _exec_resumo():
    return relatorio.texto_resumo(_prontos(), core._hoje_br(), core._amanha_br())


# ---------------------------------------------------------------- loja (marketplace)
# A loja ativa e POR CHAT (cada conversa escolhe a sua). Mercado Livre e o padrao.
# Shopee no bot e SOMENTE CONSULTA (a impressao da Shopee fica no app).
LOJA_ML = "Mercado Livre"
LOJA_SHOPEE = "Shopee"


def _loja(context) -> str:
    return context.chat_data.get("loja", LOJA_ML)


def _eh_shopee(context) -> bool:
    return _loja(context) == LOJA_SHOPEE


def _coletar_grupos(context, dia: str | None, somente_hoje: bool) -> list:
    """Coleta os grupos da LOJA ativa do chat (somente leitura).
    ML: via nucleo (usa a conta ativa). Shopee: via shopee_api."""
    if _eh_shopee(context):
        grupos, *_ = shopee.coletar_grupos(shopee.carregar_credenciais(),
                                           dia=dia, somente_hoje=somente_hoje)
        return grupos
    return _coletar(dia, somente_hoje).grupos


# Parametros de cada listagem (dia, somente_hoje, titulo). A data de amanha e
# calculada na hora para nunca "envelhecer" se o bot ficar ligado virando o dia.
def _params_listagem(acao: str):
    amanha = core._amanha_br()
    return {
        "hoje": (None, True, "HOJE"),
        "amanha": (amanha, False, f"AMANHA ({amanha})"),
        "todos": (None, False, "TODOS OS DIAS"),
    }.get(acao)


# ---------------------------------------------------------------- autorizacao / envio
def _autorizado(update: Update, cfg: dict) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id in cfg["chat_ids"])


def _teclado(loja: str = LOJA_ML) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Hoje", callback_data="hoje"),
         InlineKeyboardButton("📅 Amanhã", callback_data="amanha")],
        [InlineKeyboardButton("📊 Resumo", callback_data="resumo"),
         InlineKeyboardButton("🗂 Todos", callback_data="todos")],
        [InlineKeyboardButton(f"🏪 Loja: {loja} (trocar)", callback_data="loja")],
    ])


def _teclado_lojas(loja_ativa: str) -> InlineKeyboardMarkup:
    """Escolha da loja (a ativa marcada com ✓)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(("✓ " if n == loja_ativa else "") + n, callback_data=f"loja:{n}")]
        for n in (LOJA_ML, LOJA_SHOPEE)
    ])


def _rotulo_grupo(grupo) -> str:
    """Texto do botao de impressao de um grupo (cabe no limite do Telegram)."""
    return f"🖨 {grupo.total_etiquetas}× {grupo.nome}"[:60]


def _teclado_grupos(grupos: list) -> InlineKeyboardMarkup | None:
    """Botoes 'Imprimir' por grupo, SEPARADOS por quantidade do pedido (igual a
    tela). Antes de cada bloco vai uma linha-cabecalho nao-clicavel
    ('— Quantidade por pedido = N —'), ja que o Telegram nao deixa por texto
    solto no meio dos botoes. So entram grupos com etiquetas; None se nao houver
    nada imprimivel.

    O callback de cada botao carrega so o indice do grupo na lista guardada no
    chat_data, entao o agrupamento visual nao altera qual grupo sera impresso.
    """
    por_qtd: dict[int, list] = {}
    for i, g in enumerate(grupos):
        if g.total_etiquetas:
            por_qtd.setdefault(g.quantidade, []).append((i, g))
    if not por_qtd:
        return None
    linhas: list = []
    for qtd in sorted(por_qtd):
        linhas.append([InlineKeyboardButton(
            f"— Quantidade por pedido = {qtd} —", callback_data="noop")])
        for i, g in por_qtd[qtd]:
            linhas.append([InlineKeyboardButton(_rotulo_grupo(g), callback_data=f"ver:{i}")])
    return InlineKeyboardMarkup(linhas)


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


async def _listar_grupos(update, context, nome: str, dia: str | None,
                         somente_hoje: bool, titulo: str) -> None:
    """Lista os grupos de um dia da LOJA ativa. No Mercado Livre, oferece um botao
    'Imprimir' por grupo; na Shopee e somente consulta (a impressao fica no app).

    Guarda os grupos no chat_data para que o toque no botao (que so carrega o
    indice) saiba qual grupo imprimir, sem refazer a busca.
    """
    cfg = context.bot_data["cfg"]
    chat_id = update.effective_chat.id if update.effective_chat else None
    if not _autorizado(update, cfg):
        log.warning("Acao /%s negada para chat %s", nome, chat_id)
        if chat_id:
            await context.bot.send_message(chat_id, "Nao autorizado. Use /id e peca para liberar seu chat.")
        return
    loja = _loja(context)
    log.info("Acao /%s (loja %s) de chat %s", nome, loja, chat_id)
    await context.bot.send_message(chat_id, f"Consultando a {loja}, um instante...")
    try:
        grupos = await asyncio.to_thread(_coletar_grupos, context, dia, somente_hoje)
    except core.SeparadorError as e:
        await context.bot.send_message(chat_id, f"Erro: {e}")
        return
    except Exception as e:  # noqa: BLE001 - mostrar qualquer falha ao usuario
        log.exception("Falha na acao /%s", nome)
        await context.bot.send_message(chat_id, f"Falha inesperada: {e}")
        return
    context.chat_data["grupos"] = grupos
    # Guarda de qual conta E de qual loja sao esses grupos: se a conta/loja mudar
    # antes do toque, os shipment_ids seriam de outra origem e nao devem imprimir.
    context.chat_data["conta"] = core.conta_ativa()
    context.chat_data["loja_grupos"] = loja
    texto = relatorio.texto_grupos(grupos, f"[{loja}] {titulo}")
    for bloco in relatorio.dividir_mensagem(texto):
        await context.bot.send_message(chat_id, bloco)
    if _eh_shopee(context):
        return  # Shopee no bot e somente consulta
    teclado = _teclado_grupos(grupos)
    if teclado:
        await context.bot.send_message(chat_id, "🖨 Toque num grupo para imprimir:", reply_markup=teclado)


def _grupo_do_indice(context, idx: int):
    """Recupera o grupo guardado no chat_data; None se a lista expirou/saiu de faixa."""
    grupos = context.chat_data.get("grupos") or []
    return grupos[idx] if 0 <= idx < len(grupos) else None


def _conta_mudou(context) -> bool:
    """True se a conta ativa nao for mais a que gerou os grupos guardados."""
    return context.chat_data.get("conta") != core.conta_ativa()


def _lista_imprimivel(context) -> bool:
    """Imprimir e SO do Mercado Livre. Os grupos guardados precisam ter sido
    listados na loja ML — protege contra tocar num botao 'Imprimir' antigo do ML
    depois de ter listado a Shopee (cujos shipment_ids sao order_sn de outra API)."""
    return context.chat_data.get("loja_grupos") == LOJA_ML


async def _confirmar_impressao(update, context, idx: int) -> None:
    """Mostra 'Imprimir N etiquetas de <grupo>?' com Confirmar/Cancelar."""
    chat_id = update.effective_chat.id if update.effective_chat else None
    grupo = _grupo_do_indice(context, idx)
    if grupo is None:
        await context.bot.send_message(chat_id, "Essa lista expirou. Refaca a consulta (/hoje, /amanha...).")
        return
    if not _lista_imprimivel(context):
        await context.bot.send_message(chat_id, "Impressao e so do Mercado Livre. Na Shopee, imprima pelo app.")
        return
    if _conta_mudou(context):
        await context.bot.send_message(chat_id, "A conta ativa mudou. Refaca a consulta (/hoje, /amanha...).")
        return
    teclado = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirmar", callback_data=f"imp:{idx}"),
        InlineKeyboardButton("✖️ Cancelar", callback_data="cancelar"),
    ]])
    await context.bot.send_message(
        chat_id,
        f"Imprimir {grupo.total_etiquetas} etiqueta(s) de:\n{grupo.nome} (qtd {grupo.quantidade})?",
        reply_markup=teclado,
    )


async def _executar_impressao(update, context, idx: int) -> None:
    """Imprime de fato o grupo escolhido (apos a confirmacao)."""
    chat_id = update.effective_chat.id if update.effective_chat else None
    query = update.callback_query
    grupo = _grupo_do_indice(context, idx)
    if grupo is None:
        await query.edit_message_text("Essa lista expirou. Refaca a consulta (/hoje, /amanha...).")
        return
    if not _lista_imprimivel(context):
        await query.edit_message_text("Impressao e so do Mercado Livre. Na Shopee, imprima pelo app.")
        return
    if _conta_mudou(context):
        await query.edit_message_text("A conta ativa mudou. Refaca a consulta (/hoje, /amanha...).")
        return
    log.info("Impressao de '%s' (qtd %s) por chat %s", grupo.nome, grupo.quantidade, chat_id)
    await query.edit_message_text(f"Imprimindo {grupo.nome} (qtd {grupo.quantidade})...")
    try:
        impressos = await asyncio.to_thread(_imprimir_grupo, grupo)
    except core.SeparadorError as e:
        await context.bot.send_message(chat_id, f"Erro ao imprimir: {e}")
        return
    except Exception as e:  # noqa: BLE001
        log.exception("Falha ao imprimir '%s'", grupo.nome)
        await context.bot.send_message(chat_id, f"Falha inesperada: {e}")
        return
    if impressos:
        await context.bot.send_message(
            chat_id,
            f"✅ {len(impressos)} etiqueta(s) enviada(s) para a fila da Zebra.\n"
            f"Status do grupo: IMPRESSO.",
        )
    else:
        await context.bot.send_message(chat_id, "Nada pendente — esse grupo ja estava impresso.")


# ---------------------------------------------------------------- comandos
AJUDA = (
    "Bot de pedidos (Mercado Livre e Shopee).\n\n"
    "Toque num botao abaixo ou use os comandos:\n"
    "/hoje  /amanha  /todos  /resumo\n"
    "/dia AAAA-MM-DD — um dia especifico\n"
    "/detalhar SKU — composicao de um SKU (hoje, ML)\n"
    "/loja — trocar entre Mercado Livre e Shopee\n"
    "/conta — ver/trocar a conta ML (com 2+ contas)\n"
    "/id — mostra seu chat id\n\n"
    "ML: toque em 🖨 num grupo para imprimir (pede confirmacao).\n"
    "Shopee: somente consulta (a impressao fica no app)."
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"{AJUDA}\n\nLoja ativa: {_loja(context)}", reply_markup=_teclado(_loja(context)))


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Seu chat id e: {update.effective_chat.id}")


def _teclado_contas(contas: list, ativa: str) -> InlineKeyboardMarkup:
    """Um botao por conta (a ativa marcada com ✓). Callback carrega o indice."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(("✓ " if n == ativa else "") + n, callback_data=f"conta:{i}")]
        for i, n in enumerate(contas)
    ])


async def cmd_conta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a conta ativa e, com 2+ contas, botoes para trocar."""
    cfg = context.bot_data["cfg"]
    if not _autorizado(update, cfg):
        await update.message.reply_text("Nao autorizado. Use /id e peca para liberar seu chat.")
        return
    contas = core.listar_contas()
    if not contas:
        await update.message.reply_text("Nenhuma conta configurada. Rode pegar_token.py no PC.")
        return
    ativa = core.conta_ativa()
    if len(contas) == 1:
        await update.message.reply_text(f"Conta ativa: {contas[0]} (unica configurada).")
        return
    await update.message.reply_text(
        f"Conta ativa: {ativa}\nEscolha a conta:",
        reply_markup=_teclado_contas(contas, ativa),
    )


async def _listar_acao(update, context, acao: str) -> None:
    dia, somente_hoje, titulo = _params_listagem(acao)
    await _listar_grupos(update, context, acao, dia, somente_hoje, titulo)


async def cmd_hoje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _listar_acao(update, context, "hoje")


async def cmd_amanha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _listar_acao(update, context, "amanha")


async def cmd_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _listar_acao(update, context, "todos")


async def cmd_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _responder(update, context, "resumo", _exec_resumo)


async def cmd_loja(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a loja ativa e botoes para trocar (Mercado Livre / Shopee)."""
    cfg = context.bot_data["cfg"]
    if not _autorizado(update, cfg):
        await update.message.reply_text("Nao autorizado. Use /id e peca para liberar seu chat.")
        return
    await update.message.reply_text(
        f"Loja ativa: {_loja(context)}\nEscolha a loja:",
        reply_markup=_teclado_lojas(_loja(context)),
    )


async def cmd_dia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args or not _data_valida(args[0]):
        await update.message.reply_text("Use: /dia AAAA-MM-DD  (ex.: /dia 2026-06-22)")
        return
    dia = args[0]
    await _listar_grupos(update, context, "dia", dia, False, f"DIA {dia}")


async def cmd_detalhar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await update.message.reply_text("Use: /detalhar SKU  (ex.: /detalhar PRP)")
        return
    sku = args[0]
    await _responder(update, context, "detalhar",
                     lambda: relatorio.texto_detalhe(_coletar(None, True).itens, sku))


async def cb_botao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tratador dos botoes: menu (Hoje/Amanha/Resumo/Todos), escolha de grupo
    para imprimir (ver:N), confirmacao (imp:N) e cancelamento."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    cfg = context.bot_data["cfg"]
    if not _autorizado(update, cfg):
        chat_id = update.effective_chat.id if update.effective_chat else None
        log.warning("Botao '%s' negado para chat %s", data, chat_id)
        if chat_id:
            await context.bot.send_message(chat_id, "Nao autorizado. Use /id e peca para liberar seu chat.")
        return

    if data == "noop":
        return  # linha-cabecalho de quantidade: nao faz nada (so divisoria visual)
    if data == "cancelar":
        await query.edit_message_text("Impressao cancelada.")
        return
    if data.startswith("conta:"):
        contas = core.listar_contas()
        idx = int(data[6:])
        if 0 <= idx < len(contas):
            _trocar_conta(contas[idx])
            context.chat_data.pop("grupos", None)   # grupos eram da conta anterior
            await query.edit_message_text(
                f"Conta ativa agora: {contas[idx]}.\nUse /hoje para listar os pedidos.")
        return
    if data.startswith("ver:"):
        await _confirmar_impressao(update, context, int(data[4:]))
        return
    if data.startswith("imp:"):
        await _executar_impressao(update, context, int(data[4:]))
        return
    if data == "loja":
        await query.edit_message_text(
            f"Loja ativa: {_loja(context)}\nEscolha a loja:",
            reply_markup=_teclado_lojas(_loja(context)))
        return
    if data.startswith("loja:"):
        nova = data[5:]
        if nova in (LOJA_ML, LOJA_SHOPEE):
            context.chat_data["loja"] = nova
            context.chat_data.pop("grupos", None)   # grupos eram da loja anterior
            extra = " (somente consulta no bot)" if nova == LOJA_SHOPEE else ""
            await query.edit_message_text(
                f"Loja ativa agora: {nova}{extra}.\nUse /hoje para listar os pedidos.")
        return
    if data == "resumo":
        await _responder(update, context, "resumo", _exec_resumo)
        return
    if _params_listagem(data):
        await _listar_acao(update, context, data)


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
    # Aplica as preferencias do nucleo (conta ativa e carimbar_sku do config.json)
    # para o bot usar a mesma conta/ajustes da tela ao consultar e imprimir.
    core.aplicar_config()
    # Fallback: se a conta salva sumiu/for invalida mas ha contas, usa a 1a
    # (a tela faz o mesmo). Evita o bot cair no credenciais.json da raiz.
    conta = _garantir_conta_ativa()
    if conta:
        log.info("Conta ativa: %s (de %d configurada(s)).", conta, len(core.listar_contas()))
    cfg = carregar_config()
    app = ApplicationBuilder().token(cfg["token"]).build()
    app.bot_data["cfg"] = cfg

    app.add_handler(CommandHandler(["start", "menu", "ajuda"], cmd_start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("loja", cmd_loja))
    app.add_handler(CommandHandler("conta", cmd_conta))
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


def _pausar() -> None:
    """Segura a janela aberta para a mensagem ser lida (cmd fecha rapido senao).

    No modo de reinicio automatico (BOT_SEM_PAUSA=1, setado pelo
    'Iniciar Bot (auto).bat') NAO pausa: quem reinicia e o .bat, entao o
    processo precisa terminar para o loop subir o bot de novo."""
    if os.getenv("BOT_SEM_PAUSA"):
        return
    try:
        input("\nPressione Enter para fechar...")
    except EOFError:
        pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass  # Ctrl+C: encerrar e silencioso
    except core.SeparadorError as e:
        # Erro esperado e explicado (ex.: token ausente, credenciais faltando).
        print(f"\nNAO FOI POSSIVEL INICIAR O BOT:\n  {e}")
        if "Token" in str(e):
            print("\nDica: copie bot_config.example.json para bot_config.json e "
                  "preencha o token do @BotFather.")
        _pausar()
        raise SystemExit(1)
    except Exception:  # noqa: BLE001 - qualquer outra falha precisa ser vista
        import traceback
        print("\nO bot parou por um erro inesperado:\n")
        traceback.print_exc()
        _pausar()
        raise SystemExit(1)
