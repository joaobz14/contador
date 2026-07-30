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
  2) copie exemplos/bot_config.example.json para bot_config.json e preencha o token
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
import sys
from datetime import datetime, time
from types import SimpleNamespace

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
from registro import sem_segredos
import shopee_api as shopee

ARQUIVO_CONFIG = core.PASTA_DADOS / "bot_config.json"
ARQUIVO_LOG = core.PASTA_LOGS / "bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(ARQUIVO_LOG, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("bot")

# O TOKEN DO BOT NAO PODE IR PARA O LOG.
# A URL da API do Telegram carrega o token no PROPRIO CAMINHO
# (https://api.telegram.org/bot<TOKEN>/getUpdates), e a biblioteca HTTP registra
# cada requisicao em INFO — com o `basicConfig` acima em INFO, o token ia inteiro
# para o bot.log E para o console, a cada chamada, para sempre. Quem quisesse
# ajuda com um erro colava o log e entregava o token junto (aconteceu em
# 2026-07-30). Nao e o `sem_segredos` do registro.py que resolve: estes registros
# vem de dentro da biblioteca, sem passar pelo nosso codigo.
#
# WARNING mantem erro de rede visivel (que importa pra diagnostico) e corta o
# INFO de requisicao (que so repete o obvio e vaza o token). `httpcore` entra
# junto como defesa em profundidade: e a camada de baixo do httpx e loga a mesma
# URL se alguem subir o nivel global para DEBUG algum dia.
for _biblioteca in ("httpx", "httpcore"):
    logging.getLogger(_biblioteca).setLevel(logging.WARNING)


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


def _prontos(dias: int | None = None):
    cred = core.carregar_credenciais()
    token = core.obter_token(cred)
    pedidos = core.buscar_pedidos(token, cred["seller_id"], dias=dias)
    return core.filtrar_para_imprimir(token, pedidos)


# ---------------------------------------------------------- alerta pos-horario
ARQUIVO_ALERTAS = core.PASTA_DADOS / "alertas_pos_horario.json"
INTERVALO_ALERTA_SEGUNDOS = 5 * 60
# Janela de BUSCA do alerta (dias), bem menor que a DIAS_JANELA=30 do Atualizar:
# um envio novo ja ready_to_print com despacho HOJE e sempre recente — 5 dias
# cobrem fim de semana + feriado prolongado. Achado da auditoria de APIs: com a
# janela cheia, cada ciclo de 5 min re-consultava TODOS os envios nao-terminais
# de 30 dias (~300+ chamadas /shipments por ciclo, ~90-100 mil/dia); com a
# janela curta, so os pedidos recentes. Um caso raro que escape (pedido criado
# ha 6+ dias que so agora ficou pronto pra hoje) ainda aparece no aviso da
# manha e em qualquer Atualizar manual, que seguem com a janela cheia.
DIAS_JANELA_ALERTA = 5
# Janela de HORARIO (Brasilia) em que o alerta roda: o motivo do alerta e a
# venda que cai depois das 8:30 e precisa de reposicao no MESMO dia — de
# madrugada nao ha o que fazer com o aviso (a venda da noite aparece no aviso
# da manha), e cada ciclo fora de hora e so gasto de API. Fora da janela o job
# acorda e volta a dormir sem chamada nenhuma.
ALERTA_HORA_INICIO = 7    # inclusive (07:00)
ALERTA_HORA_FIM = 21      # exclusive (roda ate 20:59)


def _alerta_no_horario(agora=None) -> bool:
    """True se o relogio de Brasilia esta dentro da janela em que o alerta e
    util (ver ALERTA_HORA_INICIO/FIM)."""
    hora = (agora or datetime.now(core.TZ_BR)).hour
    return ALERTA_HORA_INICIO <= hora < ALERTA_HORA_FIM


def _carregar_alertas() -> dict:
    """Estado de dedup do alerta pos-horario: shipment_ids ja avisados HOJE,
    por conta ({"dia": "...", "avisados": {conta: [sid, ...]}}), MAIS os
    itens (chave+quantidade) de cada aviso ja disparado hoje ({"itens":
    {conta: [{chave, quantidade}, ...]}}) — usados pelo /vendasapos pra
    juntar tudo sem refazer nenhuma chamada de API. Reseta sozinho quando o
    dia muda (mesma filosofia do estado de impressao — nao precisa "limpar"
    nada na mao; um dia novo comeca com "hoje" vazio)."""
    dados = core._ler_json(ARQUIVO_ALERTAS)
    hoje = core._hoje_br()
    if dados.get("dia") != hoje:
        return {"dia": hoje, "avisados": {}, "itens": {}}
    dados.setdefault("avisados", {})
    dados.setdefault("itens", {})
    return dados


def _salvar_alertas(dados: dict) -> None:
    core._gravar_json(ARQUIVO_ALERTAS, dados)


def _dados_alerta_da_conta(conta: str, avisados: set, hoje: str):
    """Todo o trabalho de rede de UMA conta (prontos + detalhe dos itens
    novos) num unico bloco de troca de conta. Junto numa funcao so: a troca de
    conta mexe em globais do nucleo compartilhadas com o resto do bot — fazer
    prontos() e extrair_itens() em dois blocos separados arriscaria a 2a
    chamada rodar ja com a conta ORIGINAL restaurada pelo primeiro bloco
    (bug sutil de conta errada). Roda em thread (rede) — ver job_alerta_pos_horario.
    """
    original = core.conta_ativa()
    try:
        if conta and conta != original:
            core.definir_conta(conta)
        prontos = _prontos(dias=DIAS_JANELA_ALERTA)
        novos_pedidos = [
            p for p in prontos
            if (p.get("_envio") or {}).get("expected_date") == hoje
            and p["_envio"]["shipment_id"] not in avisados
        ]
        if not novos_pedidos:
            return [], []
        cred = core.carregar_credenciais()
        token = core.obter_token(cred)
        itens = core.extrair_itens(token, novos_pedidos)
        return novos_pedidos, itens
    finally:
        if conta and conta != original and original:
            core.definir_conta(original)


CHAVE_ALERTA_SHOPEE = "Shopee"


def _dados_alerta_shopee(avisados: set, hoje: str):
    """Equivalente Shopee de _dados_alerta_da_conta: loja UNICA (sem troca de
    conta — a Shopee so tem uma), delega o filtro pra
    shopee_api.pedidos_prontos_novos (READY_TO_SHIP + despacho hoje, dedup
    por order_sn). Roda em thread (rede) — ver job_alerta_pos_horario."""
    cred = shopee.carregar_credenciais()
    token = shopee.obter_token(cred)
    return shopee.pedidos_prontos_novos(cred, token, avisados, hoje)


async def _disparar_alerta(context, cfg: dict, dados: dict,
                           chave_estado: str, itens: list, ids_novos: list) -> None:
    """Monta o texto, manda pra todos os chats autorizados e atualiza `dados`
    (dedup + itens) IN-PLACE. `chave_estado` e a chave usada em
    dados['avisados']/['itens'] — nome da conta ML, ou CHAVE_ALERTA_SHOPEE.
    `ids_novos` sao os identificadores pra dedup (shipment_id numerico no
    ML, order_sn string na Shopee) — o chamador decide o tipo, esta funcao
    so acumula. Compartilhada entre ML e Shopee pra nao duplicar o envio +
    a persistencia em dois lugares."""
    texto = relatorio.texto_alerta_pos_horario(chave_estado, itens)
    for chat_id in cfg["chat_ids"]:
        try:
            for bloco in relatorio.dividir_mensagem(texto):
                await context.bot.send_message(chat_id, bloco)
        except Exception:
            log.exception("Falha ao enviar alerta pos-horario para o chat %s", chat_id)

    dados["avisados"].setdefault(chave_estado, [])
    dados["avisados"][chave_estado].extend(ids_novos)
    dados["itens"].setdefault(chave_estado, [])
    dados["itens"][chave_estado].extend(
        {"chave": it.chave, "quantidade": it.quantidade} for it in itens)


async def job_alerta_pos_horario(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Roda a cada INTERVALO_ALERTA_SEGUNDOS, independente do botao Atualizar
    da tela e de qualquer comando manual: percorre TODAS as contas ML
    configuradas (ou a unica, em setup legado sem contas/) MAIS a Shopee (loja
    unica), e avisa — uma vez so, por envio/pedido — quando surge algo novo ja
    pronto pra despachar HOJE (ready_to_print no ML, READY_TO_SHIP na Shopee).
    Isola falha por conta/loja: uma com erro nao impede o aviso das demais
    (mesma filosofia do ads-monitor/coletar.py). Fora da janela de horario
    (ver _alerta_no_horario) e um no-op sem chamada de API nenhuma."""
    if not _alerta_no_horario():
        return
    cfg = context.bot_data["cfg"]
    contas = core.listar_contas() or [""]
    hoje = core._hoje_br()
    dados = await asyncio.to_thread(_carregar_alertas)
    mudou = False

    for conta in contas:
        avisados = set(dados["avisados"].get(conta, []))
        try:
            novos_pedidos, itens = await asyncio.to_thread(
                _dados_alerta_da_conta, conta, avisados, hoje)
        except Exception:
            log.exception("Falha ao checar alerta pos-horario da conta %r", conta)
            continue
        if not novos_pedidos:
            continue
        await _disparar_alerta(context, cfg, dados, conta, itens,
                               [p["_envio"]["shipment_id"] for p in novos_pedidos])
        mudou = True

    # Shopee e independente das contas ML (loja unica); pula em silencio se
    # nao houver credencial configurada (setup so-ML e valido e nao deve
    # logar erro a cada 5 min pra sempre).
    if shopee.ARQUIVO_CRED.exists():
        avisados_shopee = set(dados["avisados"].get(CHAVE_ALERTA_SHOPEE, []))
        try:
            novos_shopee, itens_shopee = await asyncio.to_thread(
                _dados_alerta_shopee, avisados_shopee, hoje)
        except Exception:
            log.exception("Falha ao checar alerta pos-horario da Shopee")
            novos_shopee, itens_shopee = [], []
        if novos_shopee:
            await _disparar_alerta(context, cfg, dados, CHAVE_ALERTA_SHOPEE, itens_shopee,
                                   [d["order_sn"] for d in novos_shopee])
            mudou = True

    if mudou:
        await asyncio.to_thread(_salvar_alertas, dados)


def _agendar_alerta_pos_horario(app, cfg: dict) -> None:
    if app.job_queue is None:
        log.warning("Alerta de venda pronta pra hoje NAO agendado: JobQueue "
                    "indisponivel. Rode: pip install -r requirements-bot.txt")
        return
    app.job_queue.run_repeating(job_alerta_pos_horario,
                                interval=INTERVALO_ALERTA_SEGUNDOS, first=10)
    log.info("Alerta de venda pronta pra hoje agendado a cada %d min.",
             INTERVALO_ALERTA_SEGUNDOS // 60)


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


def _exec_resumo(context):
    """Resumo por dia DA LOJA ATIVA do chat (era sempre ML — achado P2 da
    revisão: com Shopee selecionada, o botão Resumo trazia dados do ML).
    Shopee: a contagem por dia vem da MESMA busca (contagem_por_dia), sem rede
    extra; ML: caminho original (_prontos)."""
    hoje, amanha = core._hoje_br(), core._amanha_br()
    if _eh_shopee(context):
        _grupos, _qtd, contagem = shopee.coletar_grupos(
            shopee.carregar_credenciais(), somente_hoje=False)
        return relatorio.texto_resumo_contagem(contagem, hoje, amanha, loja=LOJA_SHOPEE)
    return relatorio.texto_resumo(_prontos(), hoje, amanha)


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
        [InlineKeyboardButton("🔔 Vendas após", callback_data="vendas_apos")],
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


# O Telegram recusa um teclado inline com mais de 100 botoes ("reply markup
# too long"). Fatiamos em teclados de ate este tamanho (margem sob 100) para um
# dia com MUITOS grupos nao deixar o teclado sem ser enviado (era enviado inteiro
# e o send_message falhava em silencio).
MAX_BOTOES_TECLADO = 90


def _teclado_grupos(grupos: list) -> list[InlineKeyboardMarkup]:
    """Botoes 'Imprimir' por grupo, SEPARADOS por quantidade do pedido (igual a
    tela). Antes de cada bloco vai uma linha-cabecalho nao-clicavel
    ('— Quantidade por pedido = N —'), ja que o Telegram nao deixa por texto
    solto no meio dos botoes. So entram grupos com etiquetas.

    Devolve uma LISTA de teclados (fatiados por MAX_BOTOES_TECLADO); vazia se
    nao houver nada imprimivel. O callback de cada botao carrega so o indice do
    grupo na lista guardada no chat_data, entao o agrupamento/fatiamento visual
    nao altera qual grupo sera impresso.
    """
    por_qtd: dict[int, list] = {}
    for i, g in enumerate(grupos):
        if g.total_etiquetas:
            por_qtd.setdefault(g.quantidade, []).append((i, g))
    if not por_qtd:
        return []
    linhas: list = []
    for qtd in sorted(por_qtd):
        linhas.append([InlineKeyboardButton(
            f"— Quantidade por pedido = {qtd} —", callback_data="noop")])
        for i, g in por_qtd[qtd]:
            linhas.append([InlineKeyboardButton(_rotulo_grupo(g), callback_data=f"ver:{i}")])

    # Fatia em teclados de ate MAX_BOTOES_TECLADO botoes (1 botao por linha aqui).
    teclados: list = []
    atual: list = []
    for linha in linhas:
        if len(atual) >= MAX_BOTOES_TECLADO:
            # nao deixa um cabecalho orfao no fim de um teclado (o grupo dele
            # foi para o proximo): empurra o cabecalho para o teclado seguinte.
            carry = [atual.pop()] if atual[-1][0].callback_data == "noop" else []
            teclados.append(InlineKeyboardMarkup(atual))
            atual = carry
        atual.append(linha)
    if atual:
        teclados.append(InlineKeyboardMarkup(atual))
    return teclados


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
    await context.bot.send_message(chat_id, f"Consultando a {_loja(context)}, um instante...")
    try:
        texto = await asyncio.to_thread(executor)
    except core.SeparadorError as e:
        await context.bot.send_message(chat_id, f"Erro: {sem_segredos(e)}")
        return
    except Exception as e:  # noqa: BLE001 - mostrar qualquer falha ao usuario
        log.exception("Falha na acao /%s", nome)
        await context.bot.send_message(
            chat_id, f"Falha inesperada: {sem_segredos(e)}")  # nunca vazar URL assinada no chat
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
        await context.bot.send_message(chat_id, f"Erro: {sem_segredos(e)}")
        return
    except Exception as e:  # noqa: BLE001 - mostrar qualquer falha ao usuario
        log.exception("Falha na acao /%s", nome)
        await context.bot.send_message(
            chat_id, f"Falha inesperada: {sem_segredos(e)}")  # nunca vazar URL assinada no chat
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
    teclados = _teclado_grupos(grupos)
    for n, teclado in enumerate(teclados):
        texto = "🖨 Toque num grupo para imprimir:" if n == 0 else "🖨 (continuação)"
        await context.bot.send_message(chat_id, texto, reply_markup=teclado)


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
        await context.bot.send_message(chat_id, f"Erro ao imprimir: {sem_segredos(e)}")
        return
    except Exception as e:  # noqa: BLE001
        log.exception("Falha ao imprimir '%s'", grupo.nome)
        await context.bot.send_message(
            chat_id, f"Falha inesperada: {sem_segredos(e)}")  # nunca vazar URL assinada no chat
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
    await _responder(update, context, "resumo", lambda: _exec_resumo(context))


async def cmd_vendas_apos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Junta TUDO que o alerta pos-horario ja avisou hoje (todas as contas)
    numa mensagem so, com o TOTAL por SKU no final — pedido do dono: varias
    vendas caindo depois das 8:30 no mesmo dia poluem o chat com um alerta
    por venda. So le o estado ja persistido (nao refaz nenhuma chamada de
    API), entao nao usa `_responder` (que mostra "Consultando a loja..." —
    irrelevante aqui, isto nao depende de ML/Shopee)."""
    cfg = context.bot_data["cfg"]
    chat_id = update.effective_chat.id if update.effective_chat else None
    if not _autorizado(update, cfg):
        log.warning("Acao /vendasapos negada para chat %s", chat_id)
        if chat_id:
            await context.bot.send_message(chat_id, "Nao autorizado. Use /id e peca para liberar seu chat.")
        return
    log.info("Acao /vendasapos de chat %s", chat_id)
    dados = await asyncio.to_thread(_carregar_alertas)
    await context.bot.send_message(chat_id, **_resumo_para_envio(dados["itens"]))


def _contas_do_resumo() -> list[str]:
    """Contas que DEVEM aparecer no resumo, mesmo sem venda — ausencia tambem e
    informacao ("nenhuma venda" e diferente de o bloco sumir)."""
    try:
        return [*core.listar_contas(), CHAVE_ALERTA_SHOPEE]
    except OSError:                              # diagnostico nao pode derrubar o envio
        return []


def _resumo_para_envio(itens_por_conta: dict) -> dict:
    """Argumentos do `send_message` para o resumo de vendas.

    MENSAGEM UNICA de proposito: o texto usa `<pre>` para alinhar as colunas
    (unica forma no Telegram), e `dividir_mensagem` partiria o bloco no meio —
    HTML quebrado faz a API devolver 400 e a mensagem nao chega. Por isso o
    proprio `texto_resumo_vendas_apos` corta pelos maiores ate caber.
    """
    return {
        "text": relatorio.texto_resumo_vendas_apos(
            itens_por_conta, contas=_contas_do_resumo(), ordem=_ordem_de_separacao()),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }


def _ordem_de_separacao() -> list[str]:
    """SKUs na ordem da aba Nomes — a ordem em que o dono anda pelo estoque.

    O bloco TOTAL POR SKU e uma lista de SEPARACAO, entao segue a mesma ordem
    da tela e do PDF do resumo do dia (`historico.resumo_do_dia(ordem=...)`).
    Falha de leitura nao pode derrubar o resumo: sem a ordem, o bloco cai em
    quantidade decrescente, que e util do mesmo jeito."""
    try:
        return list(core.carregar_nomes())
    except OSError:
        return []


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
        await _responder(update, context, "resumo", lambda: _exec_resumo(context))
        return
    if data == "vendas_apos":
        await cmd_vendas_apos(update, context)
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
        # sem_segredos: convencao de TODO texto de excecao que sai pro chat —
        # hoje o aviso e so-ML, mas se um dia incluir Shopee a excecao crua
        # carregaria a URL assinada (access_token/sign).
        texto = f"Nao consegui montar o aviso da manha: {sem_segredos(e)}"
    for chat_id in cfg["chat_ids"]:
        # Falha num chat (ex.: bot bloqueado) nao pode calar o aviso dos outros.
        try:
            for bloco in relatorio.dividir_mensagem(texto):
                await context.bot.send_message(chat_id, bloco)
        except Exception:  # noqa: BLE001
            log.exception("Falha ao enviar o aviso da manha para o chat %s", chat_id)


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
    app.add_handler(CommandHandler("vendasapos", cmd_vendas_apos))
    app.add_handler(CommandHandler("dia", cmd_dia))
    app.add_handler(CommandHandler("detalhar", cmd_detalhar))
    app.add_handler(CallbackQueryHandler(cb_botao))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_desconhecido))

    _agendar_aviso(app, cfg)
    _agendar_alerta_pos_horario(app, cfg)
    log.info("Bot iniciado (%d chat(s) autorizado(s)).", len(cfg["chat_ids"]))
    print("Bot rodando... Ctrl+C para parar.")
    app.run_polling()


def _testar_alerta_pos_horario_agora() -> None:
    """Forca uma rodada do alerta pos-horario AGORA, sem esperar os 5 min do
    JobQueue. Usa a config/contas/token REAIS e manda mensagem de verdade
    pro Telegram se achar algum envio ready_to_print de hoje ainda nao
    avisado -- reusa 100% job_alerta_pos_horario (nao reimplementa nada),
    so chama ela uma vez fora do agendamento. Util pra confirmar que o
    envio funciona sem precisar esperar uma venda nova cair ou o proximo
    ciclo de 5 min. Rode: python bot_telegram.py testar-alerta"""
    core.aplicar_config()
    _garantir_conta_ativa()
    cfg = carregar_config()

    async def _rodar() -> None:
        app = ApplicationBuilder().token(cfg["token"]).build()
        app.bot_data["cfg"] = cfg
        await app.initialize()
        try:
            ctx = SimpleNamespace(bot=app.bot, bot_data=app.bot_data)
            await job_alerta_pos_horario(ctx)
        finally:
            await app.shutdown()

    print("Checando alerta pos-horario agora (sem esperar os 5 min)...")
    asyncio.run(_rodar())
    print("Pronto. Se havia algum envio novo ready_to_print para hoje ainda "
          "nao avisado, a mensagem foi enviada agora no Telegram. Se nao "
          "avisou nada, e porque nao ha nenhum envio novo hoje (ou ja foi "
          "avisado antes). Detalhes em bot.log.")


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


def _testar_resumo_vendas_agora() -> None:
    """Manda o resumo de vendas para os chats autorizados, AGORA.

    Existe porque o layout do resumo so pode ser conferido de verdade no
    celular: `<pre>`, alinhamento de coluna e escape de HTML sao coisas que o
    texto cru nao mostra — e um escape errado nao quebra nada localmente, so
    devolve 400 na hora do envio. Le o estado ja persistido; nao faz chamada de
    API de marketplace nenhuma. Rode: python bot_telegram.py testar-resumo"""
    core.aplicar_config()
    _garantir_conta_ativa()
    cfg = carregar_config()
    envio = _resumo_para_envio(_carregar_alertas()["itens"])

    print("--- texto que sera enviado (com as tags) ---")
    print(envio["text"])
    print(f"--- {len(envio['text'])} caracteres (limite do Telegram: 4096) ---\n")

    async def _rodar() -> None:
        app = ApplicationBuilder().token(cfg["token"]).build()
        await app.initialize()
        try:
            for chat_id in cfg["chat_ids"]:
                await app.bot.send_message(chat_id, **envio)
                print(f"enviado para o chat {chat_id}")
        finally:
            await app.shutdown()

    asyncio.run(_rodar())
    print("\nPronto — confira no celular. Se a API devolver 400, o motivo quase "
          "sempre e escape de HTML num SKU ou nome de conta.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "testar-resumo":
        try:
            _testar_resumo_vendas_agora()
        except core.SeparadorError as e:
            print(f"\nNAO CONSEGUI ENVIAR O RESUMO:\n  {e}")
            _pausar()
            raise SystemExit(1)
        _pausar()
        raise SystemExit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "testar-alerta":
        try:
            _testar_alerta_pos_horario_agora()
        except core.SeparadorError as e:
            print(f"\nNAO CONSEGUI TESTAR O ALERTA:\n  {e}")
            _pausar()
            raise SystemExit(1)
        _pausar()
        raise SystemExit(0)
    try:
        main()
    except KeyboardInterrupt:
        pass  # Ctrl+C: encerrar e silencioso
    except core.SeparadorError as e:
        # Erro esperado e explicado (ex.: token ausente, credenciais faltando).
        print(f"\nNAO FOI POSSIVEL INICIAR O BOT:\n  {e}")
        if "Token" in str(e):
            print("\nDica: copie exemplos/bot_config.example.json para bot_config.json e "
                  "preencha o token do @BotFather.")
        _pausar()
        raise SystemExit(1)
    except Exception:  # noqa: BLE001 - qualquer outra falha precisa ser vista
        import traceback
        print("\nO bot parou por um erro inesperado:\n")
        traceback.print_exc()
        _pausar()
        raise SystemExit(1)
