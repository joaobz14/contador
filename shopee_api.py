"""
shopee_api.py
Integracao com a Shopee Open Platform API v2 — FASE 1 (somente leitura):
lista os pedidos prontos para enviar e os agrupa por SKU + quantidade,
reaproveitando a logica do separador_etiquetas_ml.py (agrupamento, nomes,
fuso de Brasilia, resiliencia de rede).

Antes de usar: rode pegar_token_shopee.py uma vez (gera credenciais_shopee.json).

O fluxo completo (listar, organizar envio, gerar/baixar etiqueta) foi VALIDADO
com a loja real (BR) — hosts, metodos HTTP e nomes de campos conferidos em
producao. Pegadinhas de dominio documentadas no CLAUDE.md.

Comandos:
  python shopee_api.py            -> grupos prontos para enviar HOJE
  python shopee_api.py amanha     -> grupos de amanha
  python shopee_api.py todos      -> todos os dias da janela
  python shopee_api.py dia <AAAA-MM-DD>
  python shopee_api.py etiqueta <order_sn>   -> gera/baixa a etiqueta e mostra o formato
  python shopee_api.py parametros <order_sn> -> tipos de documento disponiveis (diagnostico)
"""

from __future__ import annotations

import hashlib
import hmac
import io
import sys
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import requests

import estado as _estado
import historico
import separador_etiquetas_ml as core

# Host global do Open Platform — validado com a loja real (BR) em producao.
HOST = "https://partner.shopeemobile.com"
TIMEOUT = core.TIMEOUT
DIAS_JANELA = 15           # Shopee limita a janela de busca a 15 dias
TAMANHO_LOTE = 50          # get_order_detail aceita ate 50 order_sn por chamada
MARGEM_TOKEN = 300         # renova o token 5 min antes de expirar
_LOCK_TOKEN = threading.Lock()   # serializa o refresh entre threads (ver obter_token)

ARQUIVO_CRED = core.PASTA_DADOS / "credenciais_shopee.json"

# Cache de AWB (order_sn -> tracking_number). O AWB e IMUTAVEL depois de emitido,
# entao guardamos o que a impressao ja descobriu: a coleta seguinte le daqui em
# vez de re-buscar um a um na rede (menos chamadas) e — mais importante — os
# codigos que a tela mostra para conferencia passam a vir do momento da
# impressao, nao de um refetch que pode falhar (best-effort). Local, gitignorado.
ARQUIVO_AWB_CACHE = core.PASTA_DADOS / "awb_cache_shopee.json"

# Cronometragem da impressao (diagnostico): registra quanto cada fase leva, para
# saber ONDE o tempo vai (organizar x gerar x baixar) antes de otimizar. Arquivo
# local, gitignorado; nunca guarda dados sensiveis (so contagens e segundos).
ARQUIVO_TEMPOS = core.PASTA_LOGS / "shopee_tempos.log"


def _log_tempos(n: int, organizar: float, gerar: float, *, contexto: str = "lote") -> None:
    """Anexa uma linha com os tempos de cada fase da impressao Shopee. Nunca
    levanta (diagnostico nao pode atrapalhar a impressao)."""
    try:
        total = organizar + gerar
        linha = (f"{datetime.now():%Y-%m-%d %H:%M:%S} | {contexto} | {n} pedido(s) | "
                 f"organizar {organizar:5.1f}s | gerar+baixar {gerar:5.1f}s | "
                 f"total {total:5.1f}s\n")
        with open(ARQUIVO_TEMPOS, "a", encoding="utf-8") as f:
            f.write(linha)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# CREDENCIAIS
# ---------------------------------------------------------------------------
def carregar_credenciais() -> dict:
    # Com auto-recuperacao via .bak (queda de energia nao exige refazer o token).
    cred = core._carregar_credenciais_com_backup(ARQUIVO_CRED)
    if cred:
        return cred
    if not ARQUIVO_CRED.exists():
        raise core.SeparadorError(
            "credenciais_shopee.json nao encontrado. Rode pegar_token_shopee.py primeiro."
        )
    raise core.SeparadorError(
        "credenciais_shopee.json invalido. Rode pegar_token_shopee.py de novo."
    )


def salvar_credenciais(cred: dict) -> None:
    core._gravar_credenciais_com_backup(ARQUIVO_CRED, cred)


# ---------------------------------------------------------------------------
# ASSINATURA (HMAC-SHA256) E CHAMADAS
# ---------------------------------------------------------------------------
def _assinar(partner_key: str, base: str) -> str:
    return hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()


def _assinatura_shop(cred: dict, path: str, ts: int, access_token: str) -> str:
    """Assinatura para APIs de loja: partner_id + path + timestamp + token + shop_id."""
    base = f"{cred['partner_id']}{path}{ts}{access_token}{cred['shop_id']}"
    return _assinar(cred["partner_key"], base)


def _assinatura_publica(cred: dict, path: str, ts: int) -> str:
    """Assinatura para APIs publicas (token/auth): partner_id + path + timestamp."""
    base = f"{cred['partner_id']}{path}{ts}"
    return _assinar(cred["partner_key"], base)


def _params_assinados(cred: dict, token: str, path: str) -> dict:
    ts = int(time.time())
    return {
        "partner_id": cred["partner_id"],
        "timestamp": ts,
        "access_token": token,
        "shop_id": cred["shop_id"],
        "sign": _assinatura_shop(cred, path, ts, token),
    }


def _rede_limpa(fazer, path: str):
    """Executa a chamada HTTP convertendo falhas de TRANSPORTE (queda de conexao,
    timeout esgotado, proxy) em SeparadorError LIMPO.

    A excecao crua do requests carrega a URL preparada inteira ("Max retries
    exceeded with url: ...") — e a URL da Shopee leva access_token e sign na
    query. Sem esta conversao, o texto subiria ate a tela, o log e o chat do
    bot, vazando o token. O `from None` tambem corta o encadeamento: um
    traceback logado (ex.: log.exception do bot) nao arrasta a exceccao
    original com a URL assinada. Complementa o _levantar_se_erro, que cobre os
    erros HTTP COM resposta."""
    try:
        return fazer()
    except requests.RequestException as e:
        raise core.SeparadorError(
            f"Shopee {path}: falha de rede ({type(e).__name__}). "
            "Verifique a conexao e tente de novo.") from None


def _levantar_se_erro(resp, path: str) -> None:
    """Levanta um SeparadorError LIMPO se a resposta for >= 400.

    NAO usar resp.raise_for_status(): a mensagem do HTTPError inclui a URL
    inteira — e a URL da Shopee carrega access_token e sign na query. Esse texto
    subiria ate o log, a tela e (no bot) o chat do Telegram, vazando o token.
    Aqui so expomos o path (sem segredo), o status e o erro/mensagem do CORPO da
    resposta (descritores da Shopee, sem a URL)."""
    if resp.status_code < 400:
        return
    detalhe = ""
    try:
        d = resp.json()
        detalhe = f" - {d.get('error')} {d.get('message')}".rstrip()
    except Exception:                            # corpo nao-JSON: so o status
        pass
    raise core.SeparadorError(f"Shopee {path}: HTTP {resp.status_code}{detalhe}")


def _json_limpo(resp, path: str) -> dict:
    """resp.json() convertendo corpo nao-JSON em SeparadorError LIMPO. Um proxy
    ou rede corporativa interceptando pode devolver HTML com status 200 — sem
    esta guarda, o JSONDecodeError cru subia ate a tela/bot (feio, mas sem
    segredo: a mensagem dele nao carrega a URL). `from None` pela mesma razao
    de _rede_limpa: nao arrastar encadeamento pro log."""
    try:
        return resp.json()
    except ValueError:
        raise core.SeparadorError(
            f"Shopee {path}: resposta invalida da API (nao-JSON). "
            "Tente de novo.") from None


def _get_shop(cred: dict, token: str, path: str, params: dict) -> dict:
    """GET assinado em uma API de loja, com a resiliencia de rede do core."""
    query = {**_params_assinados(cred, token, path), **params}
    resp = _rede_limpa(lambda: core._requisicao_get(
        f"{HOST}{path}", headers={}, params=query), path)
    _levantar_se_erro(resp, path)
    dados = _json_limpo(resp, path)
    if dados.get("error"):
        raise core.SeparadorError(f"Shopee {path}: {dados.get('error')} - {dados.get('message')}")
    return dados


def _post_shop(cred: dict, token: str, path: str, body: dict) -> dict:
    """POST assinado em uma API de loja (sign na query, dados no corpo JSON).
    Passa pelo retry do nucleo (408/429/5xx e rede)."""
    resp = _rede_limpa(lambda: core._requisicao_post(
        f"{HOST}{path}", params=_params_assinados(cred, token, path), json=body), path)
    _levantar_se_erro(resp, path)
    dados = _json_limpo(resp, path)
    if dados.get("error"):
        raise core.SeparadorError(f"Shopee {path}: {dados.get('error')} - {dados.get('message')}")
    return dados


def _download_shop(cred: dict, token: str, path: str, body: dict) -> bytes:
    """POST assinado que devolve um ARQUIVO (etiqueta). Se vier JSON, e erro.
    Passa pelo retry do nucleo (408/429/5xx e rede)."""
    resp = _rede_limpa(lambda: core._requisicao_post(
        f"{HOST}{path}", params=_params_assinados(cred, token, path), json=body), path)
    _levantar_se_erro(resp, path)
    if "application/json" in resp.headers.get("Content-Type", ""):
        dados = _json_limpo(resp, path)
        raise core.SeparadorError(
            f"Shopee {path}: {dados.get('error')} - {dados.get('message')}")
    return resp.content


# ---------------------------------------------------------------------------
# TOKEN (validade ~4h; refresh dura 30 dias)
# ---------------------------------------------------------------------------
def renovar_token(cred: dict) -> str:
    path = "/api/v2/auth/access_token/get"
    ts = int(time.time())
    # SEM retry (tentativas=1): o refresh_token pode rotacionar; um retry apos o
    # servidor ja te-lo consumido mandaria um token invalido e travaria a loja.
    resp = _rede_limpa(lambda: core._requisicao_post(
        f"{HOST}{path}",
        params={"partner_id": cred["partner_id"], "timestamp": ts,
                "sign": _assinatura_publica(cred, path, ts)},
        json={"refresh_token": cred["refresh_token"],
              "partner_id": int(cred["partner_id"]), "shop_id": int(cred["shop_id"])},
        tentativas=1,
    ), path)
    try:
        dados = resp.json()
    except ValueError:                           # corpo nao-JSON (proxy/HTML)
        dados = {}
    if resp.status_code != 200 or not dados or dados.get("error"):
        raise core.SeparadorError(
            f"Falha ao renovar token Shopee: {dados or f'HTTP {resp.status_code}'}")
    cred["access_token"] = dados["access_token"]
    cred["access_token_exp"] = time.time() + float(dados.get("expire_in", 14400))
    novo_refresh = dados.get("refresh_token")
    if novo_refresh:
        cred["refresh_token"] = novo_refresh
    salvar_credenciais(cred)
    return cred["access_token"]


def _token_valido(cred: dict) -> bool:
    return bool(cred.get("access_token")) and \
        time.time() < cred.get("access_token_exp", 0) - MARGEM_TOKEN


def obter_token(cred: dict) -> str:
    """Token valido do cache, ou renova. Serializa o refresh com um lock e
    re-checa dentro dele (double-checked): se varias threads paralelas pegarem o
    token expirado ao mesmo tempo, apenas UMA renova — evitando a corrida que
    poderia invalidar o refresh_token (rotacao) e travar a loja."""
    if _token_valido(cred):
        return cred["access_token"]
    with _LOCK_TOKEN:
        if _token_valido(cred):                      # outra thread ja renovou?
            return cred["access_token"]
        # Trava de ARQUIVO entre processos (mesma protecao do nucleo): bot e
        # GUI na mesma loja nao renovam em paralelo — quem chega depois espera
        # e adota o token salvo pelo primeiro, sem gastar outro refresh.
        # Degrada suave: sem trava, rele o disco como antes. espera=2*TIMEOUT:
        # no Windows o LK_LOCK desiste em ~10s e o refresh dura ate TIMEOUT —
        # ver o obter_token do nucleo.
        with _estado.trava(ARQUIVO_CRED, espera=2 * TIMEOUT):
            disco = core._ler_json(ARQUIVO_CRED)
            if disco.get("access_token"):
                cred.update(disco)
                if _token_valido(cred):
                    return cred["access_token"]
            return renovar_token(cred)


# ---------------------------------------------------------------------------
# PEDIDOS
# ---------------------------------------------------------------------------
def listar_order_sns(cred: dict, token: str) -> list[str]:
    """Lista os order_sn em READY_TO_SHIP na janela de DIAS_JANELA dias."""
    agora = int(time.time())
    desde = agora - DIAS_JANELA * 86400
    sns: list[str] = []
    cursor = ""
    while True:
        dados = _get_shop(cred, token, "/api/v2/order/get_order_list", {
            "time_range_field": "create_time",
            "time_from": desde,
            "time_to": agora,
            "page_size": 100,
            "cursor": cursor,
            "order_status": "READY_TO_SHIP",
        })
        resp = dados.get("response", {})
        sns.extend(o["order_sn"] for o in resp.get("order_list", []))
        if not resp.get("more"):
            break
        cursor = resp.get("next_cursor", "")
        if not cursor:
            break
    return sns


def listar_pedidos_com_status(cred: dict, token: str) -> list[dict]:
    """TODOS os pedidos da janela, cada um com o seu `order_status`.

    Diferente do `listar_order_sns`, que pede so os READY_TO_SHIP — e por isso
    nao enxerga uma venda travada em outro estado (ex.: esperando a NF-e). Serve
    ao diagnostico `status` da CLI: descobrir, na conta real, QUAL estado a
    Shopee usa para cada situacao. O nome do estado e contrato deles, entao
    adivinhar aqui seria repetir o erro que o diagnostico existe para evitar.
    """
    agora = int(time.time())
    desde = agora - DIAS_JANELA * 86400
    saida: list[dict] = []
    cursor = ""
    while True:
        dados = _get_shop(cred, token, "/api/v2/order/get_order_list", {
            "time_range_field": "create_time",
            "time_from": desde,
            "time_to": agora,
            "page_size": 100,
            "cursor": cursor,
            "response_optional_fields": "order_status",
        })
        resp = dados.get("response", {})
        saida.extend(resp.get("order_list", []))
        if not resp.get("more"):
            break
        cursor = resp.get("next_cursor", "")
        if not cursor:
            break
    return saida


# Campos pedidos no detalhe do pedido. `invoice_data` e `pay_time` entraram
# junto com o aviso de NF-e pendente: sao campos OPCIONAIS (so vem quando
# pedidos pelo nome) e vao na MESMA chamada que ja era feita — custo zero.
CAMPOS_DETALHE = "item_list,ship_by_date,invoice_data,pay_time"


def buscar_detalhes(cred: dict, token: str, order_sns: list[str]) -> list[dict]:
    """Detalhes dos pedidos (ver CAMPOS_DETALHE) em lotes de 50."""
    detalhes: list[dict] = []
    for i in range(0, len(order_sns), TAMANHO_LOTE):
        lote = order_sns[i:i + TAMANHO_LOTE]
        dados = _get_shop(cred, token, "/api/v2/order/get_order_detail", {
            "order_sn_list": ",".join(lote),
            "response_optional_fields": CAMPOS_DETALHE,
        })
        detalhes.extend(dados.get("response", {}).get("order_list", []))
    return detalhes


def nota_nao_validada(ped: dict) -> bool:
    """True quando a Shopee ainda NAO validou a nota do pedido.

    O efeito e o que importa e esta verificado: nesse estado a Shopee **recusa o
    `ship_order`** (erro `error_pending_invoice`, confirmado com o suporte deles
    em 2026-08-04) — a venda nao pode ser despachada, ponto.

    **A CAUSA nao e unica, e por isso a funcao nao se chama `nf_pendente`.** O
    suporte disse que `pending` = "Enviar NF-e" no painel, mas o painel do dono
    desmentiu: as 20 `pending` da loja apareciam como **"Em processamento"** (a
    Shopee ainda processando; a etiqueta libera num horario que ela anuncia) e as
    3 `valid` como "Em aberto" — casamento exato, 20/20 e 3/3. Ou seja, `pending`
    cobre pelo menos dois casos: processamento em andamento E nota faltando.
    Afirmar "esperando a NF-e" mandaria o dono cobrar o faturador de uma venda
    que so precisa de tempo.

    Sozinho o campo tambem nao serve de alerta: `pending` e o estado inicial de
    toda venda paga. Quem separa o que exige acao HOJE e o dia (`dia_previsto`).
    """
    return ((ped.get("invoice_data") or {}).get("status") or "") != "valid"


def dia_previsto(ped: dict) -> str:
    """Dia de despacho (YYYY-MM-DD), com fallback para quando o prazo ainda nao
    foi atribuido.

    A Shopee leva um tempo para preencher `ship_by_date` depois do pagamento —
    as vendas mais novas vem sem ele. Sem fallback, uma venda travada recem-paga
    ficaria fora de qualquer filtro por dia, e o aviso nasceria mudo.

    A derivacao foi conferida contra um pedido real: `ship_by_date` e o FIM DO
    DIA (23:59:59 de Brasilia) de `pay_time` + `days_to_ship`. Quando o campo
    existe ele manda — a conta e so para o intervalo em que ele falta.
    """
    dia = _data_envio(ped.get("ship_by_date"))
    if dia:
        return dia
    pago = ped.get("pay_time") or ped.get("create_time")
    if not pago:
        return ""
    base = datetime.fromtimestamp(int(pago), core.TZ_BR).date()
    return (base + timedelta(days=int(ped.get("days_to_ship") or 0))).isoformat()


def _data_envio(ship_by_date) -> str:
    """ship_by_date (epoch em segundos) -> dia YYYY-MM-DD no horario de Brasilia."""
    if not ship_by_date:
        return ""
    return datetime.fromtimestamp(int(ship_by_date), core.TZ_BR).date().isoformat()


def _itens_de_detalhes(detalhes: list[dict], dia: str | None) -> list[core.ItemPedido]:
    """Extrai ItemPedido de cada pedido, filtrando pelo dia de envio (None =
    sem filtro). Funcao pura, reaproveitada por grupos_de_detalhes (agrupado,
    pra tela/CLI) e pedidos_prontos_novos (flat, pro alerta pos-horario)."""
    itens: list[core.ItemPedido] = []
    for ped in detalhes:
        if dia is not None and _data_envio(ped.get("ship_by_date")) != dia:
            continue
        sn = ped.get("order_sn", "")
        for it in ped.get("item_list", []):
            sku = (it.get("model_sku") or it.get("item_sku") or "").strip()
            chave = sku or f"item:{it.get('item_id')}"
            nome = sku or (it.get("item_name") or "Produto")
            itens.append(core.ItemPedido(
                order_id=sn, shipment_id=sn, chave=chave, nome=nome,
                quantidade=int(it.get("model_quantity_purchased", 1)),
            ))
    return itens


def grupos_de_detalhes(detalhes: list[dict], nomes: dict, dia: str | None) -> list[core.Grupo]:
    """Converte os detalhes em ItemPedido, filtra pelo dia de envio e agrupa
    por SKU + quantidade (reaproveitando o nucleo). Funcao pura: testavel sem rede."""
    grupos = core.agrupar(_itens_de_detalhes(detalhes, dia))
    core.aplicar_nomes(grupos, nomes)
    return grupos


def pedidos_prontos_novos(cred: dict, token: str, avisados: set, hoje: str,
                          avisados_nf: set | None = None):
    """Filtro do alerta pos-horario da Shopee: pedidos READY_TO_SHIP
    (`listar_order_sns` ja filtra isso) com despacho HOJE, ainda nao avisados
    (dedup por order_sn, string — a Shopee nao tem shipment_id separado).

    Devolve QUATRO listas: (prontos, itens, pendentes_de_nf, itens_nf). A
    separacao e por `invoice_data.status`, e nao e cosmetica: com a nota
    pendente a Shopee RECUSA o `ship_order` (`error_pending_invoice`), entao a
    venda nao pode ser despachada. Mistura-la com as prontas mandaria o operador
    tentar imprimir o que a propria Shopee vai negar.

    Os dois grupos saem da MESMA busca — `invoice_data` viaja na chamada de
    detalhe que ja era feita (ver CAMPOS_DETALHE), sem chamada extra."""
    order_sns = listar_order_sns(cred, token)
    if not order_sns:
        return [], [], [], []
    detalhes = buscar_detalhes(cred, token, order_sns)
    do_dia = [d for d in detalhes if dia_previsto(d) == hoje]
    # A separacao e por NF-e, e ela decide o RECADO: uma venda com nota pendente
    # nao pode ser despachada (o ship_order e recusado com error_pending_invoice),
    # entao chama-la de "pronta" seria dizer ao operador que esta pronto o que nao
    # esta — a mesma familia do incidente de 2026-07-31 no ML.
    novos = [d for d in do_dia
             if not nota_nao_validada(d) and d.get("order_sn") not in avisados]
    novos_nf = [d for d in do_dia
                if nota_nao_validada(d) and d.get("order_sn") not in (avisados_nf or set())]
    return (novos, _itens_de_detalhes(novos, None),
            novos_nf, _itens_de_detalhes(novos_nf, None))


def contagem_por_dia(detalhes: list[dict]) -> dict[str, int]:
    """Conta os pedidos prontos por dia de envio (YYYY-MM-DD; "" = sem data).
    Funcao pura — alimenta o seletor de dias da GUI sem chamada extra de rede,
    inclusive datas fora de seg-sex (ship_by_date pode cair no fim de semana)."""
    por_dia: dict[str, int] = {}
    for ped in detalhes:
        d = _data_envio(ped.get("ship_by_date"))
        por_dia[d] = por_dia.get(d, 0) + 1
    return por_dia


def coletar_grupos(cred: dict, *, dia: str | None = None, somente_hoje: bool = True):
    token = obter_token(cred)
    order_sns = listar_order_sns(cred, token)
    detalhes = buscar_detalhes(cred, token, order_sns) if order_sns else []
    alvo_dia = (core._hoje_br() if somente_hoje else None) if dia is None else dia
    grupos = grupos_de_detalhes(detalhes, core.carregar_nomes(), alvo_dia)
    if alvo_dia is not None:
        # Namespaceia o estado de impressao por dia de despacho (igual ao ML).
        for g in grupos:
            g.dia = alvo_dia
    # qtd = numero de PEDIDOS (nao de itens), igual ao filtro por dia — o CLI
    # exibe "Pedidos prontos para imprimir: N" e as duas unidades divergiam.
    qtd = len(detalhes) if alvo_dia is None else \
        sum(1 for d in detalhes if _data_envio(d.get("ship_by_date")) == alvo_dia)
    return grupos, qtd, contagem_por_dia(detalhes)


# ---------------------------------------------------------------------------
# ETIQUETA (FASE 2): create -> result(READY) -> download
# Fluxo VALIDADO com a loja real: create exige o tracking_number (AWB), o
# resultado vira READY em segundos e o download e um ZIP com o ZPL dentro.
# ---------------------------------------------------------------------------
TIPO_ETIQUETA = "THERMAL_AIR_WAYBILL"   # etiqueta ja dimensionada p/ impressora termica


def parametros_documento(cred: dict, token: str, order_sn: str) -> dict:
    """Tipos de documento disponiveis para o pedido (para conferir o que da pra gerar)."""
    return _post_shop(cred, token, "/api/v2/logistics/get_shipping_document_parameter",
                      {"order_list": [{"order_sn": order_sn}]})


def parametros_envio(cred: dict, token: str, order_sn: str) -> dict:
    """get_shipping_parameter (LEITURA, GET): diz se o pedido precisa de pickup ou
    dropoff e quais opcoes existem. Use antes de ship_order para saber o que enviar.
    E um endpoint GET (order_sn na query) — POST devolve 404."""
    return _get_shop(cred, token, "/api/v2/logistics/get_shipping_parameter",
                     {"order_sn": order_sn})


def numero_rastreio(cred: dict, token: str, order_sn: str) -> str:
    """get_tracking_number (GET): numero de rastreio/AWB do pedido. So existe depois
    que o envio foi organizado (Organizar Envio / ship_order); vazio caso contrario.
    A Shopee exige esse AWB no create_shipping_document (senao da
    logistics.tracking_number_invalid)."""
    dados = _get_shop(cred, token, "/api/v2/logistics/get_tracking_number",
                      {"order_sn": order_sn})
    return ((dados.get("response") or {}).get("tracking_number") or "").strip()


def _rastreios_paralelo(cred: dict, token: str, order_sns: list) -> dict:
    """Busca o AWB de varios pedidos EM PARALELO. Devolve {order_sn: awb} ('' em
    falha). Muito mais rapido que buscar um a um quando ha varios pedidos."""
    out: dict = {}

    def _um(sn):
        try:
            out[sn] = numero_rastreio(cred, token, str(sn))
        except Exception:
            out[sn] = ""

    if order_sns:
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(_um, order_sns))
    return out


LOTE_SHIP = 50   # batch_ship_order aceita ate 50 pedidos por chamada


def batch_ship_order(cred: dict, token: str, order_sns: list, *,
                     dropoff: dict | None = None) -> dict:
    """Organiza VARIOS envios num request so (ate LOTE_SHIP), como Postagem
    (drop-off). Mesmo efeito do ship_order pedido a pedido, com 1 chamada em
    vez de N. A resposta pode listar falhas por pedido, mas NAO dependemos do
    formato dela: a prova confiavel de que organizou e o AWB sair
    (ver _organizar_varios)."""
    body: dict = {"order_list": [{"order_sn": str(sn)} for sn in order_sns]}
    if dropoff is not None:
        body["dropoff"] = dropoff
    return _post_shop(cred, token, "/api/v2/logistics/batch_ship_order", body)


def _aguardar_awbs(cred: dict, token: str, order_sns: list, *,
                   tentativas: int = 25, espera: float = 1.0) -> dict:
    """Espera os AWBs de varios pedidos sairem (a Shopee leva alguns segundos
    apos o ship). Polling paralelo; para assim que todos sairem. Devolve
    {order_sn: awb} apenas dos que sairam no prazo.

    Backoff suave: 1s nas 10 primeiras tentativas (o AWB tipico sai em ~14s —
    checagem frequente encontra cedo), 2s dali em diante. Teto total ~40s como
    antes (10x1 + 15x2), com ~40% menos chamadas get_tracking_number por
    pedido que ainda nao saiu (achado da auditoria de APIs: 40 polls/pedido
    era agressivo sem ganho de latencia)."""
    pendentes = [str(sn) for sn in order_sns]
    ok: dict = {}
    for tentativa in range(tentativas):
        if not pendentes:
            break
        time.sleep(espera if tentativa < 10 else espera * 2)
        for sn, awb in _rastreios_paralelo(cred, token, pendentes).items():
            if awb:
                ok[sn] = awb
        pendentes = [sn for sn in pendentes if sn not in ok]
    return ok


def _filtrar_ja_arranjados(cred: dict, token: str, order_sns: list) -> list:
    """Dos `order_sns` (ja sem AWB), devolve os que a Shopee ja considera
    ARRANJADOS (info_needed sem pickup/dropoff/non_integrated — so falta o AWB
    sair). Consulta parametros_envio em paralelo; falha de rede num pedido nao
    o classifica como arranjado (fica de fora, segue o caminho normal — mesmo
    espirito conservador de _rede_limpa/envio_ja_arranjado: em duvida, nao
    assume que ja foi organizado)."""
    def _param(sn):
        try:
            return sn, parametros_envio(cred, token, sn)
        except Exception:
            return sn, None

    with ThreadPoolExecutor(max_workers=8) as executor:
        params = dict(executor.map(_param, order_sns))
    return [sn for sn in order_sns if params.get(sn) and envio_ja_arranjado(params[sn])]


def _organizar_varios(cred: dict, token: str, order_sns: list, *,
                      branch_id=None, sender_real_name=None) -> tuple[dict, list]:
    """Organiza varios envios, em camadas (da mais rapida para o fallback):

      1) quem JA tem AWB esta organizado (idempotente) — nada a fazer;
      1.5) dos que sobraram, quem a Shopee JA considera arranjado (so falta o
         AWB sair) vai direto pro fallback individual — chamar ship_order de
         novo num pedido ja arranjado a Shopee rejeita com 'already shipped'
         (achado no requisito de qualidade da Shopee pro v2.logistics.ship_order:
         success rate > 90% por 7 dias — reenviar um pedido ja arranjado e uma
         das causas documentadas de falha);
      2) o restante (genuinamente nao arranjado) vai TODO num batch_ship_order
         (1 request p/ ate 50) e os AWBs sao aguardados — o rastreio existir e
         a unica confirmacao em que confiamos (nao dependemos do formato da
         resposta do batch);
      3) quem ficar sem AWB apos o batch NAO cai no individual (ver motivo
         abaixo) — entra em `falhas` como pendente de confirmacao. Ja quem
         veio do 1.5 (ja arranjado antes desta chamada) OU cujo batch nunca
         chegou a ser tentado (endpoint indisponivel por inteiro) vai pro
         fallback individual (`organizar_envio`), que resolve casos especiais
         (info_needed com campos exigidos) e so reporta em `falhas` quando
         nem assim sai.

    Por que o passo 3 NAO reenvia quem passou pelo batch sem AWB: a Shopee
    confirmou que `fulfillment_status`/`is_shipment_arranged` podem levar
    ATE 15-20 MINUTOS pra propagar depois de um ship aceito — bem mais que os
    ~40s de polling deste modulo. Cair no individual logo em seguida
    consultaria `parametros_envio` ainda com o status ANTIGO (nao arranjado)
    e chamaria `ship_order` de novo no mesmo pedido — exatamente o cenario
    'already shipped' que conta contra a taxa de sucesso do endpoint. Melhor
    reportar como pendente e deixar o operador tentar de novo em alguns
    minutos: nessa hora o 1.5 (que usa a mesma consulta) ja teria o status
    atualizado e nao reenviaria.

    Devolve (ok={order_sn: awb}, falhas=[(sn, motivo)]). NAO levanta — quem
    chama decide (grupo unico aborta; lote tolera)."""
    order_sns = [str(sn) for sn in order_sns]
    ok: dict = {}
    falhas: list = []
    if not order_sns:
        return ok, falhas

    # 1) ja organizados (idempotencia): AWB existente = nada a fazer
    ok.update({sn: awb
               for sn, awb in _rastreios_paralelo(cred, token, order_sns).items() if awb})
    restantes = [sn for sn in order_sns if sn not in ok]

    # 1.5) filtra quem ja foi arranjado antes de deixar QUALQUER um chegar no
    # batch_ship_order (ver motivo no docstring).
    ja_arranjados = _filtrar_ja_arranjados(cred, token, restantes) if restantes else []
    restantes = [sn for sn in restantes if sn not in ja_arranjados]

    # 2) batch (1 request) SO para quem realmente ainda precisa ser arranjado.
    # Se NENHUM batch passou, nem espera — vai direto pro individual (evita
    # 40s de polling inutil).
    restantes_sem_batch: list = []   # o ship nunca chegou a ser tentado
    if restantes:
        dropoff: dict = {}
        if branch_id not in (None, ""):
            dropoff["branch_id"] = branch_id
        if sender_real_name not in (None, ""):
            dropoff["sender_real_name"] = sender_real_name
        algum_batch = False
        for i in range(0, len(restantes), LOTE_SHIP):
            try:
                batch_ship_order(cred, token, restantes[i:i + LOTE_SHIP], dropoff=dropoff)
                algum_batch = True
            except Exception:                        # fallback individual cobre
                pass
        if algum_batch:
            ok.update(_aguardar_awbs(cred, token, restantes))
            # estado ambiguo (ver docstring) -- NAO cai no individual.
            for sn in restantes:
                if sn not in ok:
                    falhas.append((sn, "Envio enviado, aguardando confirmacao (AWB) "
                                       "da Shopee. Tente novamente em alguns minutos."))
        else:
            restantes_sem_batch = restantes

    # 3) fallback individual (paralelo) — SO quem ja estava arranjado no 1.5
    # (organizar_envio checa de novo e so espera o AWB, sem reenviar) e quem
    # o batch nunca chegou a tentar (endpoint indisponivel por inteiro).
    def _um(sn):
        try:
            ok[sn] = organizar_envio(cred, token, sn,
                                     branch_id=branch_id, sender_real_name=sender_real_name)
        except Exception as e:                       # inclui erro de rede (HTTPError)
            falhas.append((sn, str(e)))

    restantes_final = ja_arranjados + restantes_sem_batch
    if restantes_final:
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(_um, restantes_final))
    return ok, falhas


def ship_order(cred: dict, token: str, order_sn: str, *,
               pickup: dict | None = None, dropoff: dict | None = None) -> dict:
    """Finaliza o arranjo de envio (pickup OU dropoff) antes de gerar a etiqueta.
    ATENCAO: acao que COMPROMETE o envio. So chamar com os parametros corretos,
    obtidos de parametros_envio(). Campos validados com a loja real (drop-off:
    info_needed geralmente vazio; as vezes branch_id/sender_real_name)."""
    body: dict = {"order_sn": order_sn}
    if pickup is not None:
        body["pickup"] = pickup
    if dropoff is not None:
        body["dropoff"] = dropoff
    return _post_shop(cred, token, "/api/v2/logistics/ship_order", body)


def envio_ja_arranjado(param: dict) -> bool:
    """True se o envio ja foi organizado. info_needed traz as chaves dos metodos
    (pickup/dropoff/non_integrated) que ainda PRECISAM ser arranjados; se qualquer
    uma estiver presente, o envio ainda nao foi organizado."""
    info = param.get("response", {}).get("info_needed", {}) or {}
    return not any(k in info for k in ("pickup", "dropoff", "non_integrated"))


def criar_documento(cred: dict, token: str, order_sns: list[str], tipo: str = TIPO_ETIQUETA,
                    rastreios: dict | None = None) -> dict:
    """Cria o documento da etiqueta. A Shopee exige o tracking_number (AWB) de cada
    pedido no corpo — `rastreios` mapeia order_sn -> AWB (ver numero_rastreio)."""
    rastreios = rastreios or {}
    order_list = []
    for sn in order_sns:
        item = {"order_sn": sn, "shipping_document_type": tipo}
        if rastreios.get(sn):
            item["tracking_number"] = rastreios[sn]
        order_list.append(item)
    return _post_shop(cred, token, "/api/v2/logistics/create_shipping_document",
                      {"order_list": order_list})


def resultado_documento(cred: dict, token: str, order_sns: list[str], tipo: str = TIPO_ETIQUETA) -> dict:
    body = {"order_list": [{"order_sn": sn, "shipping_document_type": tipo} for sn in order_sns]}
    return _post_shop(cred, token, "/api/v2/logistics/get_shipping_document_result", body)


def baixar_documento(cred: dict, token: str, order_sns: list[str], tipo: str = TIPO_ETIQUETA) -> bytes:
    body = {"shipping_document_type": tipo,
            "order_list": [{"order_sn": sn} for sn in order_sns]}
    return _download_shop(cred, token, "/api/v2/logistics/download_shipping_document", body)


def _status_documento(res: dict) -> dict:
    """Extrai {order_sn: status} do retorno do get_shipping_document_result."""
    lista = res.get("response", {}).get("result_list", [])
    return {it.get("order_sn"): (it.get("status") or it.get("document_status") or "").upper()
            for it in lista}


def gerar_etiqueta(cred: dict, order_sns: list[str], *, tipo: str = TIPO_ETIQUETA,
                   rastreios: dict | None = None, token: str | None = None,
                   tentativas: int = 30, espera: float = 1.0) -> bytes:
    """Gera (assincrono) e baixa as etiquetas dos pedidos. So baixa quando TODOS
    os pedidos pedidos estiverem READY (nao retorna num subconjunto), e aborta se
    a Shopee marcar algum FAILED.

    O tracking_number (AWB) de cada pedido e exigido no create; passe-o em
    `rastreios` ({sn: awb}) para nao buscar de novo (quem organiza ja tem). Se
    None, busca em paralelo. Sem AWB, aborta com mensagem clara em vez de deixar
    a Shopee devolver 'tracking_number_invalid'. `token` evita re-buscar o token
    em chamadas paralelas. Polling de 1s."""
    if not order_sns:
        raise core.SeparadorError("Nenhum pedido informado para gerar a etiqueta.")
    token = token or obter_token(cred)
    if rastreios is None:
        # Cache de AWB primeiro (o AWB e imutavel; ver ARQUIVO_AWB_CACHE): a
        # REIMPRESSAO de um grupo ja impresso nao pode falhar so porque um
        # refetch de rede do rastreio falhou — o codigo ja e conhecido desde a
        # impressao original. So os ausentes vao a rede; os buscados entram no
        # cache (best-effort), como na impressao.
        cache = _carregar_awb_cache()
        rastreios = {str(sn): cache.get(str(sn), "") for sn in order_sns}
        faltantes = [sn for sn in order_sns if not rastreios.get(str(sn))]
        if faltantes:
            buscados = _rastreios_paralelo(cred, token, faltantes)
            rastreios.update({str(sn): awb for sn, awb in buscados.items()})
            _cachear_awbs(buscados)
    # Valida TODOS os order_sns, nao so as chaves presentes em `rastreios`: um
    # pedido AUSENTE do mapa (mapa parcial) passava batido e seguia sem AWB ate a
    # Shopee devolver 'tracking_number_invalid' (auditoria 5.9). Compara por str
    # para tolerar chaves int/str no mapa.
    _mapa = {str(sn): tn for sn, tn in rastreios.items()}
    sem_awb = [str(sn) for sn in order_sns if not _mapa.get(str(sn))]
    if sem_awb:
        raise core.SeparadorError(
            "Sem numero de rastreio (AWB) para: " + ", ".join(sem_awb) + ". "
            "Organize o envio (botao 'Organizar Envio' na Shopee) antes de gerar a etiqueta."
        )
    # Os endpoints de documento tem limite de pedidos por chamada (TAMANHO_LOTE).
    # Fatia em blocos e combina num unico ZIP no fim (a Zebra imprime tudo junto).
    zips = [_gerar_bloco(cred, token, order_sns[i:i + TAMANHO_LOTE], tipo, rastreios,
                         tentativas, espera)
            for i in range(0, len(order_sns), TAMANHO_LOTE)]
    return zips[0] if len(zips) == 1 else _combinar_etiquetas(zips)


def _gerar_bloco(cred: dict, token: str, order_sns: list, tipo: str, rastreios: dict,
                 tentativas: int, espera: float) -> bytes:
    """Cria/espera(READY)/baixa UM bloco de pedidos (<= TAMANHO_LOTE). So baixa com
    TODOS os pedidos do bloco READY; aborta se algum FAILED."""
    criar_documento(cred, token, order_sns, tipo, rastreios=rastreios)
    for _ in range(tentativas):
        status = _status_documento(resultado_documento(cred, token, order_sns, tipo))
        # Avalia por pedido pedido (nao so os que vieram no result_list): um pedido
        # ausente conta como ainda-nao-pronto, evitando baixar antes da hora.
        if any(status.get(sn) == "FAILED" for sn in order_sns):
            raise core.SeparadorError(f"Geracao da etiqueta falhou: {status}")
        if all(status.get(sn) == "READY" for sn in order_sns):
            return baixar_documento(cred, token, order_sns, tipo)
        time.sleep(espera)
    raise core.SeparadorError("A etiqueta nao ficou pronta (READY) a tempo. Tente de novo.")


def detectar_formato(conteudo: bytes) -> str:
    """Identifica o formato do arquivo baixado pelos primeiros bytes.

    A etiqueta termica da Shopee vem como ZIP (assinatura 'PK') contendo um TXT
    com ZPL (~DGR/Z64). O app da Zebra reconhece esse ZIP pelo nome
    'etiqueta shopee - ...zip' e imprime direto."""
    if conteudo[:4] == b"%PDF":
        return "PDF"
    if conteudo[:3] == b"~DG" or b"^XA" in conteudo[:64]:
        return "ZPL"
    if conteudo[:4] == b"\x89PNG":
        return "PNG"
    if conteudo[:2] == b"PK":
        return "ZIP"
    return "DESCONHECIDO"


def salvar_etiqueta(conteudo: bytes, rotulo: str):
    """Grava a etiqueta na pasta Downloads e devolve (caminho, formato detectado).
    O nome comeca com 'etiqueta shopee - ' (prefixo que o app da Zebra reconhece);
    `rotulo` (order_sn ou rotulo do grupo) e saneado para virar nome de arquivo."""
    fmt = detectar_formato(conteudo)
    ext = {"PDF": "pdf", "ZPL": "zpl", "PNG": "png", "ZIP": "zip"}.get(fmt, "bin")
    base = "".join(c if (c.isalnum() or c in " -_") else "_" for c in str(rotulo))[:50].strip()
    core.PASTA_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    # nome_saida_unico: carimbo unico para nao sobrescrever uma etiqueta que o
    # monitor da Zebra ainda nao consumiu (mesmo padrao do ML — ver auditoria 5.1).
    destino = core.nome_saida_unico(core.PASTA_DOWNLOADS, "etiqueta shopee - ", base, ext)
    # Grava em temporario e renomeia (mesmo padrao do ML): o monitor da Zebra
    # vigia a pasta e nao pode enxergar o arquivo pela metade (imprimiria
    # corrompido). tmp_saida: nome que nao casa os prefixos/extensoes do monitor.
    tmp = core.tmp_saida(destino)
    tmp.write_bytes(conteudo)
    tmp.replace(destino)
    return destino, fmt


# ---------------------------------------------------------------------------
# ORGANIZAR ENVIO (ship_order como Postagem / drop-off)
# ---------------------------------------------------------------------------
def _montar_dropoff(info_needed: dict, *, branch_id=None, sender_real_name=None) -> dict:
    """Monta o corpo `dropoff` do ship_order a partir dos campos exigidos em
    info_needed.dropoff. Campos nao exigidos sao omitidos; `tracking_number` e
    gerado pela Shopee, nunca enviado. Levanta SeparadorError se um campo exigido
    nao foi fornecido (a GUI configura o ponto/remetente uma vez)."""
    exigidos = (info_needed or {}).get("dropoff") or []
    valores = {"branch_id": branch_id, "sender_real_name": sender_real_name}
    dropoff: dict = {}
    for campo in exigidos:
        if campo == "tracking_number":
            continue
        valor = valores.get(campo)
        if valor in (None, ""):
            raise core.SeparadorError(
                f"O envio exige '{campo}' para postar (drop-off). Configure o ponto "
                f"de coleta / nome do remetente da Shopee uma vez nas preferencias."
            )
        dropoff[campo] = valor
    return dropoff


# Trechos EXATOS das mensagens de erro documentadas no FAQ de compliance da
# Shopee pro v2.logistics.ship_order (confirmados com o suporte deles,
# 2026-07) — usados pra reconhecer os dois casos abaixo sem reimplementar
# um parser de erro novo (a excecao ja carrega error+message, ver
# _levantar_se_erro). Comparacao em minusculas.
_MSG_JA_ENVIADO = "already been shipped"
_MSG_ALOCANDO = "please wait until the allocate is completed"


def organizar_envio(cred: dict, token: str, order_sn: str, *,
                    branch_id=None, sender_real_name=None,
                    tentativas: int = 40, espera: float = 1.0,
                    tentativas_alocando: int = 3, espera_alocando: float = 3.0) -> str:
    """Organiza o envio como Postagem (drop-off) — equivale a 'vou postar no ponto
    de coleta' no painel — e ESPERA o rastreio (AWB) ser emitido (a Shopee leva
    alguns segundos apos o ship_order). Idempotente: se ja houver AWB, devolve na
    hora. Retorna o tracking_number; erro claro se o AWB nao sair a tempo.
    Polling de 1s (checa mais vezes -> encontra o AWB mais cedo).

    Defesa em profundidade contra os 2 casos de erro de status de pedido do
    ship_order documentados pela Shopee (alem do filtro de quem chama, ver
    _organizar_varios): 'already been shipped' (a Shopee ja considera
    arranjado apesar do info_needed que acabamos de ler — normalmente uma
    corrida com outra chamada; nao e erro de verdade, so falta o AWB) e
    'please wait until the allocate is completed' (transiente segundo a
    propria mensagem da Shopee — tenta de novo com um pequeno intervalo)."""
    tn = numero_rastreio(cred, token, order_sn)
    if tn:
        return tn
    param = parametros_envio(cred, token, order_sn)
    info = param.get("response", {}).get("info_needed", {}) or {}
    if envio_ja_arranjado(param):
        # JA organizado (info_needed sem pickup/dropoff/non_integrated) mas o AWB
        # ainda nao saiu — organizado manualmente no painel, ou o batch organizou
        # e a resposta foi ambigua. NAO re-organizar (nem tratar info_needed={}
        # como "nao oferece drop-off", que era o falso erro do achado 5.3): so
        # aguardar o rastreio ja em processamento, no polling abaixo.
        pass
    elif "dropoff" not in info:
        raise core.SeparadorError(
            f"O pedido {order_sn} nao oferece Postagem (drop-off) — info_needed={info}. "
            f"Organize manualmente no painel da Shopee."
        )
    else:
        dropoff = _montar_dropoff(info, branch_id=branch_id, sender_real_name=sender_real_name)
        for tentativa in range(tentativas_alocando):
            try:
                ship_order(cred, token, order_sn, dropoff=dropoff)
                break
            except core.SeparadorError as e:
                msg = str(e).lower()
                if _MSG_JA_ENVIADO in msg:
                    break                      # ja arranjado -- so falta o AWB
                if _MSG_ALOCANDO in msg and tentativa < tentativas_alocando - 1:
                    time.sleep(espera_alocando)
                    continue
                raise
    # O AWB nao sai na hora: a Shopee leva alguns segundos para emiti-lo.
    for _ in range(tentativas):
        time.sleep(espera)
        tn = numero_rastreio(cred, token, order_sn)
        if tn:
            return tn
    raise core.SeparadorError(
        f"Envio organizado, mas o rastreio (AWB) do pedido {order_sn} ainda nao saiu. "
        f"Aguarde alguns segundos e clique em Imprimir novamente."
    )


def preencher_rastreios(cred: dict, grupos: list, estado: dict) -> None:
    """Para cada grupo, preenche g.rastreios com o AWB de CADA etiqueta JA
    IMPRESSA — a etiqueta Shopee nao tem o nome do produto, entao a tela lista
    os codigos para conferir qual etiqueta e qual produto. Envios PENDENTES sao
    ignorados: o AWB so existe apos organizar o envio.

    Le do CACHE de AWB primeiro (preenchido na impressao; o AWB e imutavel):
    codigos que vieram da impressao nao dependem de rede e nao 'somem' se uma
    busca falhar. So os que faltam no cache vao a rede (em paralelo); os novos
    entram no cache, que e podado junto com o estado (por idade)."""
    cache = _carregar_awb_cache()
    tarefas = []                                # (grupo, indice, order_sn) — misses
    for g in grupos:
        pend = set(core.envios_pendentes(estado, g))
        ids = [i for i in g.shipment_ids if i not in pend]   # ja impressos
        if not ids:
            continue
        g.rastreios = [""] * len(ids)           # posicao por etiqueta (thread-safe)
        for idx, sn in enumerate(ids):
            awb = cache.get(str(sn))
            if awb:
                g.rastreios[idx] = awb          # cache hit: confiavel, sem rede
            else:
                tarefas.append((g, idx, sn))

    novos: dict = {}
    if tarefas:
        token = obter_token(cred)
        trava = threading.Lock()

        def _um(tarefa):
            g, idx, sn = tarefa
            try:
                awb = numero_rastreio(cred, token, str(sn))
            except Exception:                   # best-effort: rastreio e so conferencia
                return
            if awb:
                g.rastreios[idx] = awb
                with trava:
                    novos[str(sn)] = awb

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(_um, tarefas))

    for g in grupos:                            # descarta falhas, preserva a ordem
        if g.rastreios:
            g.rastreios = [c for c in g.rastreios if c]

    # Persiste novos + poda SEMPRE que algo mudar — a poda nao pode depender de
    # haver `novos` (P2 da releitura): no regime normal pos-cache tudo e cache
    # hit, `novos` fica vazio e o arquivo cresceria para sempre. So regrava
    # quando o conteudo muda (best-effort preservado: cache correto = sem IO).
    try:
        cache.update(novos)
        manter = _order_sns_do_estado(estado) | {
            str(sn) for g in grupos for sn in g.shipment_ids}
        podado = {sn: awb for sn, awb in cache.items() if sn in manter}
        if podado != _carregar_awb_cache():
            _estado.gravar_json(ARQUIVO_AWB_CACHE, podado)
    except Exception:                           # noqa: BLE001 - cache best-effort
        pass


# ---------------------------------------------------------------------------
# ESTADO (controle de "ja impresso") — arquivo proprio da Shopee
# ---------------------------------------------------------------------------
ARQUIVO_ESTADO = core.PASTA_DADOS / "estado_shopee.json"


# Estado de "ja impresso" da Shopee: mesma camada comum do ML (estado.py), so
# muda o arquivo. persistir_poda=True (igual ao ML): sem isso a poda so valia em
# memoria e cada marcar_impresso regravava o disco com as entradas antigas
# intactas — o arquivo crescia sem limite (auditoria 5.7). A regravacao da poda
# roda sob a MESMA trava do marcar_impresso e RELENDO o disco (ver carregar), entao
# nao apaga uma marcacao concorrente.
def carregar_estado() -> dict:
    return _estado.carregar(ARQUIVO_ESTADO, core.DIAS_ESTADO, persistir_poda=True)


def salvar_estado(estado: dict) -> None:
    _estado.salvar(ARQUIVO_ESTADO, estado)


def marcar_impresso(estado: dict, grupo: core.Grupo, order_sns: list | None = None) -> None:
    """Marca order_sns como impressos (ou todos do grupo). RECARREGA o estado do
    disco e mescla (uniao) antes de gravar, para nao apagar marcacoes de outro
    processo feitas nesse meio-tempo (mesma convencao do nucleo). arquivo= liga
    a trava entre processos no ciclo ler->mesclar->salvar."""
    # ler_estado (nao ler_json): estado corrompido e preservado, nao sobrescrito
    # em silencio destruindo o recuperavel (auditoria 5.2).
    _estado.marcar_impresso(
        lambda: _estado.ler_estado(ARQUIVO_ESTADO), salvar_estado, estado, grupo, order_sns,
        arquivo=ARQUIVO_ESTADO,
        # Historico do dia: so os order_sns recem-marcados (delta). Shopee e loja
        # unica, entao conta="" (o resumo mostra a secao "Shopee").
        registrar=lambda novos: historico.registrar(
            core.ARQUIVO_HISTORICO, marketplace="Shopee", conta="",
            grupo=grupo, ids=novos))


# ---------------------------------------------------------------------------
# IMPRESSAO DE GRUPO / LOTES (organiza -> gera -> salva -> marca)
# ---------------------------------------------------------------------------
def _rotulo_lote(grupo: core.Grupo, ids: list) -> str:
    return ids[0] if len(ids) == 1 else f"{grupo.chave} x{len(ids)}"


def _carregar_awb_cache() -> dict:
    return _estado.ler_json(ARQUIVO_AWB_CACHE)


def _cachear_awbs(awbs: dict) -> None:
    """Guarda os AWB (order_sn -> tracking) obtidos numa impressao. Best-effort:
    uma falha de IO nunca atrapalha a impressao (como _log_tempos)."""
    validos = {str(sn): awb for sn, awb in (awbs or {}).items() if awb}
    if not validos:
        return
    try:
        cache = _carregar_awb_cache()
        cache.update(validos)
        _estado.gravar_json(ARQUIVO_AWB_CACHE, cache)
    except Exception:                            # noqa: BLE001 - diagnostico/cache
        pass


def _order_sns_do_estado(estado: dict) -> set:
    """Todos os order_sns que aparecem no estado de impressao (para podar o cache
    de AWB junto com o estado, que ja e podado por idade)."""
    out: set = set()
    for valor in estado.values():
        if isinstance(valor, list):
            out.update(str(x) for x in valor)
    return out


def _somar_rastreios(grupo, novos: list) -> None:
    """UNE os AWBs recem-impressos aos ja exibidos, sem duplicar e preservando a
    ordem. Num grupo PARCIAL, g.rastreios ja tem os codigos das etiquetas antigas
    (preenchidos na coleta); substituir a lista apagaria da tela a referencia que
    o operador usa para casar etiqueta fisica x produto (a etiqueta Shopee nao
    tem o nome) ate a proxima coleta."""
    atuais = list(getattr(grupo, "rastreios", []) or [])
    grupo.rastreios = atuais + [a for a in novos if a and a not in atuais]


def _zpl_do_zip(conteudo: bytes) -> bytes:
    """Extrai o ZPL (em BYTES, sem reencodar — evita corromper o ~DG/Z64) de dentro
    de um .zip de etiqueta Shopee, ou devolve o proprio conteudo se ja for ZPL cru."""
    try:
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            return b"\n".join(z.read(n) for n in z.namelist())
    except zipfile.BadZipFile:
        return conteudo


def _combinar_etiquetas(zips: list) -> bytes:
    """Junta o ZPL de varias etiquetas Shopee num UNICO .zip (um TXT) — para a
    Zebra imprimir tudo de uma vez, sem intervalo entre arquivos. Trabalha em
    bytes para preservar o conteudo exato das etiquetas."""
    texto = b"\n".join(_zpl_do_zip(b) for b in zips)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("thermal_zpl_shipping_label.txt", texto)
    return buf.getvalue()


def imprimir_grupo(cred: dict, grupo: core.Grupo, estado: dict, *, organizar: bool = True,
                   marcar: bool = True, branch_id=None, sender_real_name=None) -> list:
    """Organiza (se preciso e organizar=True, em paralelo), gera/baixa a etiqueta
    dos envios PENDENTES do grupo, salva na Downloads (a Zebra imprime) e, se
    marcar=True, marca o estado. Retorna os order_sns impressos. Grupo unico:
    aborta com erro se algum pedido falhar (o lote e que tolera parcial)."""
    pendentes = core.envios_pendentes(estado, grupo)
    if not pendentes:
        return []
    token = obter_token(cred)
    _t0 = time.time()
    if organizar:
        awbs, falhas = _organizar_varios(cred, token, pendentes,
                                         branch_id=branch_id, sender_real_name=sender_real_name)
        if falhas:
            raise core.SeparadorError(falhas[0][1])
    else:
        awbs = _rastreios_paralelo(cred, token, pendentes)
    _t1 = time.time()
    conteudo = gerar_etiqueta(cred, pendentes, token=token,
                              rastreios={sn: awbs.get(sn, "") for sn in pendentes})
    salvar_etiqueta(conteudo, _rotulo_lote(grupo, pendentes))
    _log_tempos(len(pendentes), _t1 - _t0, time.time() - _t1, contexto="grupo")
    _cachear_awbs(awbs)                          # AWB imutavel: a coleta seguinte le do cache
    # UNE os AWBs recem-impressos aos ja exibidos (parcial nao perde os antigos).
    _somar_rastreios(grupo, [awbs.get(sn, "") for sn in pendentes])
    if marcar:
        marcar_impresso(estado, grupo, pendentes)
    return pendentes


def _gerar_lote(cred: dict, token: str, alvo: list, awbs: dict) -> tuple:
    """Gera as etiquetas dos pedidos `alvo` num so ZIP, tolerando falha parcial.

    Gera UM DOCUMENTO POR PEDIDO, EM PARALELO (8 de cada vez): medimos que a
    geracao do documento na Shopee escala ~por pedido (~5s cada) quando pedida
    num lote unico — entao paralelizar encurta o tempo total se a Shopee
    processar em paralelo. Combina os que derem num ZIP unico; cada pedido que
    falhar entra em `falhas` sem derrubar os outros. Devolve (conteudo|None,
    sns_ok, falhas)."""
    if not alvo:
        return None, [], []
    resultados: dict = {}
    falhas: list = []

    def _um(sn):
        try:
            resultados[sn] = gerar_etiqueta(cred, [sn], rastreios={sn: awbs[sn]}, token=token)
        except Exception as e:
            falhas.append((sn, str(e)))

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(_um, alvo))
    sns_ok = [sn for sn in alvo if sn in resultados]
    if not sns_ok:
        return None, [], falhas
    # 1 pedido nao precisa combinar (o proprio ZIP ja serve).
    conteudo = (resultados[sns_ok[0]] if len(sns_ok) == 1
                else _combinar_etiquetas([resultados[sn] for sn in sns_ok]))
    return conteudo, sns_ok, falhas


def imprimir_lotes(cred: dict, grupos: list, estado: dict, *,
                   organizar: bool = True, branch_id=None, sender_real_name=None) -> tuple:
    """Organiza+imprime varios grupos SEM marcar o estado (quem chama marca apos a
    confirmacao, igual ao ML). Gera UM UNICO .zip com todas as etiquetas que derem
    certo (a Zebra imprime de enfiada, sem intervalo). TOLERA FALHA PARCIAL.

    Devolve (impressos, falhas): impressos=[(grupo, ids_ok), ...] (so o que gerou),
    falhas=[(order_sn, motivo), ...] (sem AWB, ou recusado pela Shopee)."""
    pend_por_grupo = [(g, core.envios_pendentes(estado, g)) for g in grupos]
    pend_por_grupo = [(g, p) for g, p in pend_por_grupo if p]
    if not pend_por_grupo:
        return [], []
    token = obter_token(cred)
    todos = [sn for _, pend in pend_por_grupo for sn in pend]
    _t0 = time.time()
    if organizar:
        awbs, falhas = _organizar_varios(cred, token, todos,
                                         branch_id=branch_id, sender_real_name=sender_real_name)
    else:
        awbs = _rastreios_paralelo(cred, token, todos)
        falhas = [(sn, "sem numero de rastreio (AWB) — organize o envio")
                  for sn in todos if not awbs.get(sn)]
    _t1 = time.time()
    _cachear_awbs(awbs)                          # AWB imutavel: a coleta seguinte le do cache
    alvo = [sn for sn in todos if awbs.get(sn)]
    conteudo, sns_ok, falhas_gen = _gerar_lote(cred, token, alvo, awbs)
    falhas += falhas_gen
    if conteudo:
        salvar_etiqueta(conteudo, f"lote {sns_ok[0]} x{len(sns_ok)}")
    _log_tempos(len(todos), _t1 - _t0, time.time() - _t1)
    ok = set(sns_ok)
    impressos = []
    for g, pend in pend_por_grupo:
        ids_ok = [sn for sn in pend if sn in ok]
        if ids_ok:
            # UNE aos ja exibidos (parcial nao perde os antigos).
            _somar_rastreios(g, [awbs.get(sn, "") for sn in ids_ok])
            impressos.append((g, ids_ok))
    return impressos, falhas


def reimprimir_grupo(cred: dict, grupo: core.Grupo) -> list:
    """Regera a etiqueta de TODOS os envios do grupo, sem mexer no estado (util
    quando uma etiqueta atola). Assume o envio ja organizado."""
    ids = list(grupo.shipment_ids)
    if not ids:
        return []
    salvar_etiqueta(gerar_etiqueta(cred, ids), _rotulo_lote(grupo, ids))
    return ids


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    args = sys.argv[1:]
    comando = args[0] if args else "listar"

    # Etiqueta de um pedido: gera, baixa e salva na Downloads (o app da Zebra imprime).
    if comando == "etiqueta" and len(args) >= 2:
        order_sn = args[1]
        try:
            cred = carregar_credenciais()
            print(f"Gerando etiqueta ({TIPO_ETIQUETA}) do pedido {order_sn} ...")
            conteudo = gerar_etiqueta(cred, [order_sn])
            caminho, fmt = salvar_etiqueta(conteudo, order_sn)
        except core.SeparadorError as e:
            sys.exit(f"ERRO: {e}")
        print(f"\nEtiqueta salva em: {caminho}")
        print(f"Formato: {fmt}  ({len(conteudo)} bytes)")
        print("O app da Zebra (impressora_zebra_usb.py) detecta esse arquivo e imprime sozinho.")
        return

    # Diagnostico: QUAIS estados existem na loja agora, com contagem — e o que a
    # API devolve sobre os pedidos que NAO estao em READY_TO_SHIP.
    #
    # Existe pelo mesmo motivo do `substatus` do ML: o app so pede READY_TO_SHIP,
    # entao uma venda travada em outro estado (esperando a NF-e, por exemplo) e
    # invisivel para ele — e o nome desse estado e contrato da Shopee, que so a
    # conta real confirma. Rode com uma venda travada para descobrir o sinal.
    if comando == "status":
        try:
            cred = carregar_credenciais()
            token = obter_token(cred)
            pedidos = listar_pedidos_com_status(cred, token)
        except core.SeparadorError as e:
            sys.exit(f"ERRO: {e}")

        contagem: dict[str, int] = {}
        for p in pedidos:
            contagem[p.get("order_status") or "(sem status)"] = \
                contagem.get(p.get("order_status") or "(sem status)", 0) + 1
        print(f"\n{len(pedidos)} pedido(s) na janela de {DIAS_JANELA} dias\n")
        print("order_status encontrados:")
        for rotulo, n in sorted(contagem.items(), key=lambda x: -x[1]):
            marca = "   <- o app so enxerga estes" if rotulo == "READY_TO_SHIP" else ""
            print(f"  {n:>4}  {rotulo}{marca}")

        outros = [p.get("order_sn") for p in pedidos
                  if p.get("order_status") != "READY_TO_SHIP"][:5]
        if not outros:
            print("\nNenhum pedido fora de READY_TO_SHIP agora — nada a investigar.")
            return
        print(f"\nDetalhe de ate 5 pedidos FORA de READY_TO_SHIP ({len(outros)}):")
        try:
            dados = _get_shop(cred, token, "/api/v2/order/get_order_detail", {
                "order_sn_list": ",".join(outros),
                "response_optional_fields": "item_list,ship_by_date,order_status",
            })
            for d in dados.get("response", {}).get("order_list", []):
                print(f"\n  {d.get('order_sn')}  status={d.get('order_status')}"
                      f"  despacho={_data_envio(d.get('ship_by_date')) or '(sem data)'}")
                # As CHAVES sao o que interessa: e nelas que aparece o campo que
                # sinaliza "esperando a NF-e", qualquer que seja o nome dele.
                print(f"    campos: {', '.join(sorted(d.keys()))}")
        except core.SeparadorError as e:
            print(f"  nao consegui o detalhe: {e}")
        # A pergunta decisiva: `invoice_data.status` DISTINGUE as vendas travadas
        # das normais, ou e "pending" em toda venda nova? Se nao distinguir, usar
        # esse campo como sinal marcaria o lote inteiro como travado — e um aviso
        # que dispara sempre nao e aviso, e ruido.
        prontos = [p.get("order_sn") for p in pedidos
                   if p.get("order_status") == "READY_TO_SHIP"]
        if prontos:
            print(f"\ninvoice_data.status dos {len(prontos)} READY_TO_SHIP "
                  f"(o que decide se o campo serve de sinal):")
            por_nf: dict[str, list[str]] = {}
            hoje = core._hoje_br()
            for i in range(0, len(prontos), TAMANHO_LOTE):
                try:
                    dados = _get_shop(cred, token, "/api/v2/order/get_order_detail", {
                        "order_sn_list": ",".join(prontos[i:i + TAMANHO_LOTE]),
                        "response_optional_fields": "ship_by_date,invoice_data",
                    })
                except core.SeparadorError as e:
                    print(f"  nao consegui o detalhe: {e}")
                    break
                for d in dados.get("response", {}).get("order_list", []):
                    nf = (d.get("invoice_data") or {}).get("status") or "(sem invoice_data)"
                    dia = _data_envio(d.get("ship_by_date"))
                    marca = " [HOJE]" if dia == hoje else ""
                    por_nf.setdefault(nf, []).append(f"{d.get('order_sn')} {dia}{marca}")
            for nf, lista in sorted(por_nf.items(), key=lambda x: -len(x[1])):
                print(f"\n  status={nf}  ({len(lista)} pedido(s))")
                for linha in lista[:8]:
                    print(f"    {linha}")
                if len(lista) > 8:
                    print(f"    ... e mais {len(lista) - 8}")
            if len(por_nf) == 1:
                print("\n  >> TODOS iguais: este campo NAO distingue venda travada "
                      "de venda normal. Preciso de outro sinal.")
            else:
                print("\n  >> Valores DIFERENTES: o campo serve. Confira no painel "
                      "quais estao como 'Enviar NF-e' e veja se batem.")
        print("\nMande esta saida no chat: e ela que diz qual estado usar no alerta.")
        return

    # Diagnostico: TUDO que a API sabe sobre UM pedido, inclusive os campos
    # OPCIONAIS (que so vem quando pedidos pelo nome — por isso o `status` acima
    # nao os mostra: a ausencia la nao prova nada).
    #
    # Serve para apontar num pedido que o PAINEL mostra como "aguardando NF-e" e
    # descobrir onde esse estado aparece na API. Se a chamada larga for recusada,
    # cai numa segunda com o conjunto minimo e diz quais campos a Shopee nao
    # aceitou — a recusa tambem e informacao.
    if comando == "detalhe" and len(args) >= 2:
        order_sn = args[1]
        largo = ("item_list,ship_by_date,order_status,invoice_data,package_list,"
                 "note,fulfillment_flag,payment_method,total_amount,pay_time")
        try:
            cred = carregar_credenciais()
            token = obter_token(cred)
        except core.SeparadorError as e:
            sys.exit(f"ERRO: {e}")

        def _detalhe(campos: str):
            return _get_shop(cred, token, "/api/v2/order/get_order_detail", {
                "order_sn_list": order_sn, "response_optional_fields": campos,
            })

        try:
            dados = _detalhe(largo)
            print(f"\n(pedi os campos opcionais: {largo})")
        except core.SeparadorError as e:
            print(f"\nA Shopee recusou o conjunto largo: {e}")
            print("Tentando so os basicos...")
            try:
                dados = _detalhe("item_list,ship_by_date,order_status")
            except core.SeparadorError as e2:
                sys.exit(f"ERRO: {e2}")

        lista = dados.get("response", {}).get("order_list", [])
        if not lista:
            sys.exit(f"Pedido {order_sn} nao encontrado (confira o numero).")
        import json as _json
        print(f"\n--- {order_sn} ---")
        print(_json.dumps(lista[0], ensure_ascii=False, indent=2)[:4000])
        print("\nMande isto no chat. Procuramos onde aparece 'aguardando NF-e'.")
        return

    # Tipos de documento disponiveis para um pedido (diagnostico).
    if comando == "parametros" and len(args) >= 2:
        try:
            cred = carregar_credenciais()
            token = obter_token(cred)
            print(parametros_documento(cred, token, args[1]))
        except core.SeparadorError as e:
            sys.exit(f"ERRO: {e}")
        return

    try:
        cred = carregar_credenciais()
        dia = None
        somente_hoje = True
        if comando == "amanha":
            dia = core._amanha_br()
        elif comando == "dia" and len(args) >= 2:
            dia = args[1]
        elif comando == "todos":
            somente_hoje = False
        grupos, qtd, _ = coletar_grupos(cred, dia=dia, somente_hoje=somente_hoje)
    except core.SeparadorError as e:
        sys.exit(f"ERRO: {e}")

    rotulo = {"amanha": f"AMANHA ({dia})", "todos": "todos os dias"}.get(comando, "HOJE")
    print(f"\n[Shopee] Mostrando {rotulo}")
    # Estado REAL, nao {}: sem ele a coluna de status mentia [PENDENTE] para
    # grupos ja impressos pela tela/bot.
    core.listar(grupos, carregar_estado(), qtd)


if __name__ == "__main__":
    main()
