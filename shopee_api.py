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
"""

from __future__ import annotations

import hashlib
import hmac
import sys
import time
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


def _get_shop(cred: dict, token: str, path: str, params: dict) -> dict:
    """GET assinado em uma API de loja, com a resiliencia de rede do core."""
    ts = int(time.time())
    query = {
        "partner_id": cred["partner_id"],
        "timestamp": ts,
        "access_token": token,
        "shop_id": cred["shop_id"],
        "sign": _assinatura_shop(cred, path, ts, token),
        **params,
    }
    resp = core._requisicao_get(f"{HOST}{path}", headers={}, params=query)
    resp.raise_for_status()
    dados = resp.json()
    if dados.get("error"):
        raise core.SeparadorError(f"Shopee {path}: {dados.get('error')} - {dados.get('message')}")
    return dados


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
    qtd = sum(len(d.get("item_list", [])) for d in detalhes) if alvo_dia is None else \
        sum(1 for d in detalhes if _data_envio(d.get("ship_by_date")) == alvo_dia)
    return grupos, qtd


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    args = sys.argv[1:]
    comando = args[0] if args else "listar"
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
