"""
shopee_api.py
Integracao com a Shopee Open Platform API v2 — FASE 1 (somente leitura):
lista os pedidos prontos para enviar e os agrupa por SKU + quantidade,
reaproveitando a logica do separador_etiquetas_ml.py (agrupamento, nomes,
fuso de Brasilia, resiliencia de rede).

Antes de usar: rode pegar_token_shopee.py uma vez (gera credenciais_shopee.json).

ATENCAO: alguns detalhes da API (host da regiao Brasil, nomes de campos) devem
ser confirmados no painel https://open.shopee.com ao registrar o app. Os trechos
a confirmar estao marcados com "# CONFIRMAR".

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
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests

import separador_etiquetas_ml as core

# host global do Open Platform; sellers do Brasil usam a mesma plataforma.
# CONFIRMAR no painel se a sua conta usa outro host de regiao.
HOST = "https://partner.shopeemobile.com"
TIMEOUT = core.TIMEOUT
DIAS_JANELA = 15           # Shopee limita a janela de busca a 15 dias
TAMANHO_LOTE = 50          # get_order_detail aceita ate 50 order_sn por chamada
MARGEM_TOKEN = 300         # renova o token 5 min antes de expirar

ARQUIVO_CRED = core.PASTA_SCRIPT / "credenciais_shopee.json"


# ---------------------------------------------------------------------------
# CREDENCIAIS
# ---------------------------------------------------------------------------
def carregar_credenciais() -> dict:
    if not ARQUIVO_CRED.exists():
        raise core.SeparadorError(
            "credenciais_shopee.json nao encontrado. Rode pegar_token_shopee.py primeiro."
        )
    cred = core._ler_json(ARQUIVO_CRED)
    if not cred:
        raise core.SeparadorError(
            "credenciais_shopee.json invalido. Rode pegar_token_shopee.py de novo."
        )
    return cred


def salvar_credenciais(cred: dict) -> None:
    core._gravar_json(ARQUIVO_CRED, cred)


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


def _get_shop(cred: dict, token: str, path: str, params: dict) -> dict:
    """GET assinado em uma API de loja, com a resiliencia de rede do core."""
    query = {**_params_assinados(cred, token, path), **params}
    resp = core._requisicao_get(f"{HOST}{path}", headers={}, params=query)
    resp.raise_for_status()
    dados = resp.json()
    if dados.get("error"):
        raise core.SeparadorError(f"Shopee {path}: {dados.get('error')} - {dados.get('message')}")
    return dados


def _post_shop(cred: dict, token: str, path: str, body: dict) -> dict:
    """POST assinado em uma API de loja (sign na query, dados no corpo JSON)."""
    resp = requests.post(f"{HOST}{path}", params=_params_assinados(cred, token, path),
                         json=body, timeout=TIMEOUT)
    resp.raise_for_status()
    dados = resp.json()
    if dados.get("error"):
        raise core.SeparadorError(f"Shopee {path}: {dados.get('error')} - {dados.get('message')}")
    return dados


def _download_shop(cred: dict, token: str, path: str, body: dict) -> bytes:
    """POST assinado que devolve um ARQUIVO (etiqueta). Se vier JSON, e erro."""
    resp = requests.post(f"{HOST}{path}", params=_params_assinados(cred, token, path),
                         json=body, timeout=TIMEOUT)
    resp.raise_for_status()
    if "application/json" in resp.headers.get("Content-Type", ""):
        dados = resp.json()
        raise core.SeparadorError(
            f"Shopee {path}: {dados.get('error')} - {dados.get('message')}")
    return resp.content


# ---------------------------------------------------------------------------
# TOKEN (validade ~4h; refresh dura 30 dias)
# ---------------------------------------------------------------------------
def renovar_token(cred: dict) -> str:
    path = "/api/v2/auth/access_token/get"
    ts = int(time.time())
    resp = requests.post(
        f"{HOST}{path}",
        params={"partner_id": cred["partner_id"], "timestamp": ts,
                "sign": _assinatura_publica(cred, path, ts)},
        json={"refresh_token": cred["refresh_token"],
              "partner_id": int(cred["partner_id"]), "shop_id": int(cred["shop_id"])},
        timeout=TIMEOUT,
    )
    dados = resp.json()
    if resp.status_code != 200 or dados.get("error"):
        raise core.SeparadorError(f"Falha ao renovar token Shopee: {dados or resp.text}")
    cred["access_token"] = dados["access_token"]
    cred["access_token_exp"] = time.time() + float(dados.get("expire_in", 14400))
    novo_refresh = dados.get("refresh_token")
    if novo_refresh:
        cred["refresh_token"] = novo_refresh
    salvar_credenciais(cred)
    return cred["access_token"]


def obter_token(cred: dict) -> str:
    if cred.get("access_token") and time.time() < cred.get("access_token_exp", 0) - MARGEM_TOKEN:
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


def buscar_detalhes(cred: dict, token: str, order_sns: list[str]) -> list[dict]:
    """Detalhes dos pedidos (item_list, ship_by_date) em lotes de 50."""
    detalhes: list[dict] = []
    for i in range(0, len(order_sns), TAMANHO_LOTE):
        lote = order_sns[i:i + TAMANHO_LOTE]
        dados = _get_shop(cred, token, "/api/v2/order/get_order_detail", {
            "order_sn_list": ",".join(lote),
            "response_optional_fields": "item_list,ship_by_date",
        })
        detalhes.extend(dados.get("response", {}).get("order_list", []))
    return detalhes


def _data_envio(ship_by_date) -> str:
    """ship_by_date (epoch em segundos) -> dia YYYY-MM-DD no horario de Brasilia."""
    if not ship_by_date:
        return ""
    return datetime.fromtimestamp(int(ship_by_date), core.TZ_BR).date().isoformat()


def grupos_de_detalhes(detalhes: list[dict], nomes: dict, dia: str | None) -> list[core.Grupo]:
    """Converte os detalhes em ItemPedido, filtra pelo dia de envio e agrupa
    por SKU + quantidade (reaproveitando o nucleo). Funcao pura: testavel sem rede."""
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
    grupos = core.agrupar(itens)
    core.aplicar_nomes(grupos, nomes)
    return grupos


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
    qtd = sum(len(d.get("item_list", [])) for d in detalhes) if alvo_dia is None else \
        sum(1 for d in detalhes if _data_envio(d.get("ship_by_date")) == alvo_dia)
    return grupos, qtd


# ---------------------------------------------------------------------------
# ETIQUETA (FASE 2): create -> result(READY) -> download
# Fluxo confirmado pela documentacao/IA da Shopee. Nomes de campos marcados
# com "# CONFIRMAR" devem ser validados no primeiro teste real.
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


def _organizar_varios(cred: dict, token: str, order_sns: list, *,
                      branch_id=None, sender_real_name=None) -> tuple[dict, list]:
    """Organiza varios envios EM PARALELO (cada um espera o seu AWB). Devolve
    (ok, falhas): ok={order_sn: awb} dos que organizaram; falhas=[(sn, motivo)].
    NAO levanta — quem chama decide (grupo unico aborta; lote tolera)."""
    ok: dict = {}
    falhas: list = []

    def _um(sn):
        try:
            ok[sn] = organizar_envio(cred, token, str(sn),
                                     branch_id=branch_id, sender_real_name=sender_real_name)
        except Exception as e:                       # inclui erro de rede (HTTPError)
            falhas.append((sn, str(e)))

    if order_sns:
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(_um, order_sns))
    return ok, falhas


def ship_order(cred: dict, token: str, order_sn: str, *,
               pickup: dict | None = None, dropoff: dict | None = None) -> dict:
    """Finaliza o arranjo de envio (pickup OU dropoff) antes de gerar a etiqueta.
    ATENCAO: acao que COMPROMETE o envio. So chamar com os parametros corretos,
    obtidos de parametros_envio(). # CONFIRMAR campos no primeiro teste real."""
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
    token = token or obter_token(cred)
    if rastreios is None:
        rastreios = _rastreios_paralelo(cred, token, order_sns)
    sem_awb = [sn for sn, tn in rastreios.items() if not tn]
    if sem_awb:
        raise core.SeparadorError(
            "Sem numero de rastreio (AWB) para: " + ", ".join(sem_awb) + ". "
            "Organize o envio (botao 'Organizar Envio' na Shopee) antes de gerar a etiqueta."
        )
    criar_documento(cred, token, order_sns, tipo, rastreios=rastreios)
    for _ in range(tentativas):
        status = _status_documento(resultado_documento(cred, token, order_sns, tipo))
        # Avalia por pedido PEDIDO (nao so os que vieram no result_list): um pedido
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
    destino = core.PASTA_DOWNLOADS / f"etiqueta shopee - {base}.{ext}"
    destino.write_bytes(conteudo)
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


def organizar_envio(cred: dict, token: str, order_sn: str, *,
                    branch_id=None, sender_real_name=None,
                    tentativas: int = 40, espera: float = 1.0) -> str:
    """Organiza o envio como Postagem (drop-off) — equivale a 'vou postar no ponto
    de coleta' no painel — e ESPERA o rastreio (AWB) ser emitido (a Shopee leva
    alguns segundos apos o ship_order). Idempotente: se ja houver AWB, devolve na
    hora. Retorna o tracking_number; erro claro se o AWB nao sair a tempo.
    Polling de 1s (checa mais vezes -> encontra o AWB mais cedo)."""
    tn = numero_rastreio(cred, token, order_sn)
    if tn:
        return tn
    info = parametros_envio(cred, token, order_sn).get("response", {}).get("info_needed", {}) or {}
    if "dropoff" not in info:
        raise core.SeparadorError(
            f"O pedido {order_sn} nao oferece Postagem (drop-off) — info_needed={info}. "
            f"Organize manualmente no painel da Shopee."
        )
    dropoff = _montar_dropoff(info, branch_id=branch_id, sender_real_name=sender_real_name)
    ship_order(cred, token, order_sn, dropoff=dropoff)
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


def envios_a_organizar(cred: dict, order_sns: list[str]) -> list[str]:
    """Quais order_sns ainda nao tem AWB (precisam de Organizar Envio)."""
    token = obter_token(cred)
    return [sn for sn in order_sns if not numero_rastreio(cred, token, sn)]


def preencher_rastreios(cred: dict, grupos: list, estado: dict) -> None:
    """Para grupos de UM unico pedido JA IMPRESSO, busca o AWB (get_tracking_number)
    em paralelo e seta g.rastreio — para conferencia na tela. Grupos com varios
    pedidos sao ignorados de proposito (o usuario nao precisa, e poupa chamadas)."""
    alvo = [g for g in grupos
            if len(g.shipment_ids) == 1 and core.status_grupo(estado, g) == "impresso"]
    if not alvo:
        return
    token = obter_token(cred)

    def _um(g):
        try:
            g.rastreio = numero_rastreio(cred, token, str(g.shipment_ids[0]))
        except Exception:                       # best-effort: rastreio e so conferencia
            pass

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(_um, alvo))


# ---------------------------------------------------------------------------
# ESTADO (controle de "ja impresso") — arquivo proprio da Shopee
# ---------------------------------------------------------------------------
ARQUIVO_ESTADO = core.PASTA_SCRIPT / "estado_shopee.json"


def carregar_estado() -> dict:
    return core._limpar_estado_antigo(core._ler_json(ARQUIVO_ESTADO))


def salvar_estado(estado: dict) -> None:
    core._gravar_json(ARQUIVO_ESTADO, estado)


def marcar_impresso(estado: dict, grupo: core.Grupo, order_sns: list | None = None) -> None:
    """Marca order_sns como impressos (ou todos do grupo). RECARREGA o estado do
    disco e mescla (uniao) antes de gravar, para nao apagar marcacoes de outro
    processo feitas nesse meio-tempo (mesma convencao do nucleo)."""
    ids = grupo.shipment_ids if order_sns is None else order_sns
    chave = core._chave_estado(grupo)
    disco = core._ler_json(ARQUIVO_ESTADO)
    impressos = core._impressos(estado, grupo)
    impressos.update(core._impressos(disco, grupo))
    impressos.update(ids)
    ordenados = sorted(impressos)
    disco[chave] = ordenados
    salvar_estado(disco)
    estado[chave] = ordenados


# ---------------------------------------------------------------------------
# IMPRESSAO DE GRUPO / LOTES (organiza -> gera -> salva -> marca)
# ---------------------------------------------------------------------------
def _rotulo_lote(grupo: core.Grupo, ids: list) -> str:
    return ids[0] if len(ids) == 1 else f"{grupo.chave} x{len(ids)}"


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
    if organizar:
        awbs, falhas = _organizar_varios(cred, token, pendentes,
                                         branch_id=branch_id, sender_real_name=sender_real_name)
        if falhas:
            raise core.SeparadorError(falhas[0][1])
    else:
        awbs = _rastreios_paralelo(cred, token, pendentes)
    conteudo = gerar_etiqueta(cred, pendentes, token=token,
                              rastreios={sn: awbs.get(sn, "") for sn in pendentes})
    salvar_etiqueta(conteudo, _rotulo_lote(grupo, pendentes))
    if len(grupo.shipment_ids) == 1:
        grupo.rastreio = awbs.get(pendentes[0], "")
    if marcar:
        marcar_impresso(estado, grupo, pendentes)
    return pendentes


def _gerar_lote(cred: dict, token: str, alvo: list, awbs: dict) -> tuple:
    """Gera as etiquetas dos pedidos `alvo` num so ZIP, tolerando falha parcial.
    Tenta tudo de uma vez (rapido); se a Shopee recusar algum, cai para geracao
    individual em paralelo, combinando os que derem. Devolve (conteudo|None,
    sns_ok, falhas)."""
    if not alvo:
        return None, [], []
    try:
        conteudo = gerar_etiqueta(cred, alvo, rastreios={sn: awbs[sn] for sn in alvo}, token=token)
        return conteudo, list(alvo), []
    except Exception:
        pass  # alguma etiqueta falhou no lote -> tenta uma a uma (isola a falha)

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
    conteudo = _combinar_etiquetas([resultados[sn] for sn in sns_ok]) if sns_ok else None
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
    if organizar:
        awbs, falhas = _organizar_varios(cred, token, todos,
                                         branch_id=branch_id, sender_real_name=sender_real_name)
    else:
        awbs = _rastreios_paralelo(cred, token, todos)
        falhas = [(sn, "sem numero de rastreio (AWB) — organize o envio")
                  for sn in todos if not awbs.get(sn)]
    alvo = [sn for sn in todos if awbs.get(sn)]
    conteudo, sns_ok, falhas_gen = _gerar_lote(cred, token, alvo, awbs)
    falhas += falhas_gen
    if conteudo:
        salvar_etiqueta(conteudo, f"lote {sns_ok[0]} x{len(sns_ok)}")
    ok = set(sns_ok)
    impressos = []
    for g, pend in pend_por_grupo:
        ids_ok = [sn for sn in pend if sn in ok]
        if ids_ok:
            if len(g.shipment_ids) == 1:
                g.rastreio = awbs.get(ids_ok[0], "")
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
        grupos, qtd = coletar_grupos(cred, dia=dia, somente_hoje=somente_hoje)
    except core.SeparadorError as e:
        sys.exit(f"ERRO: {e}")

    rotulo = {"amanha": f"AMANHA ({dia})", "todos": "todos os dias"}.get(comando, "HOJE")
    print(f"\n[Shopee] Mostrando {rotulo}")
    core.listar(grupos, {}, qtd)


if __name__ == "__main__":
    main()
