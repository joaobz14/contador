#!/usr/bin/env python3
"""Coletor deterministico do Product Ads (Mercado Livre).

Grava, uma vez por dia, o snapshot das metricas de cada campanha (e, dentro
dela, de cada ad_group/item anunciado) das contas configuradas (Cozilatti,
Gastromaq...) num SQLite LOCAL — a base historica do futuro monitor. Motor de
recomendacao e dado de margem por SKU ficam para uma proxima etapa (a
atribuicao por ad_group/item ja fica gravada, pronta pra ser cruzada com
margem quando essa fonte existir).

- SO GET (leitura). Nunca pausa, edita ou muda orcamento de campanha.
- Reusa a autenticacao do nucleo (obter_token/definir_conta): mesma trava
  entre processos que a GUI/bot usam — nunca duplica logica de refresh nem
  arrisca rotacionar o refresh_token por fora.
- Um DIA por execucao (default ONTEM — o Mercado Livre atualiza os dados de
  Ads as 10:00 GMT-3, entao "hoje" viria incompleto/provisorio). Sem backfill
  automatico: para varios dias, rode com --dia repetidas vezes.
- Idempotente: rodar o mesmo dia de novo REGRAVA (INSERT OR REPLACE), nao
  duplica.
- Isola falha por conta: uma conta sem Product Ads ou com token vencido nao
  derruba a coleta das demais.

Endpoints usados (confirmados na doc oficial "Product Ads" e "Product Ads
para Catalogo e User Products" do Mercado Livre Developers):
  GET /advertising/advertisers?product_id=PADS
  GET /advertising/{site}/advertisers/{advertiser_id}/product_ads/campaigns/search
  GET /advertising/{site}/product_ads/campaigns/{campaign_id}
  GET /advertising/{site}/advertisers/{advertiser_id}/product_ads/ad_groups/search
  GET /advertising/{site}/product_ads/ad_groups/{ad_group_id}/ads

Os dois ultimos foram validados com chamada real (tools/diag_ads.py, passo 5,
PR #167/#168): resolvem a cadeia campanha -> ad_group -> item_id, o que
prepara terreno pra atribuicao por SKU. Ressalva confirmada com dado real: um
ad_group NAO e 1:1 com item (tipo FAMILY/CATALOG pode agrupar varios item_id,
sem quebra de metrica por item dentro do grupo -- a granularidade mais fina
que a API da e o ad_group).

Resolucao de SKU (_resolver_skus): prioriza o seller_sku REAL, buscado via
core.buscar_detalhes (GET /items/{id}, o MESMO cache itens_cache.json que a
impressao ja mantem — zero chamada de escrita, so estende um cache existente)
e cai pro mapa de adocao skus_por_anuncio.json (anuncios sem seller_sku
cadastrado) quando o item nao tiver seller_sku — mesma prioridade de
identidade() no nucleo. Achado real (validado 2026-07-23): antes desta
mudanca a cobertura era 0/468 itens porque skus_por_anuncio.json e um mapa
manual pequeno, nao um resolvedor geral — a maioria dos produtos tem
seller_sku cadastrado direto no anuncio, so nao havia cache local pra isso.

Uso:
    python ads-monitor/coletar.py                    # ontem, todas as contas
    python ads-monitor/coletar.py --dia 2026-07-20    # um dia especifico
    python ads-monitor/coletar.py --conta cozilatti   # so uma conta
"""
from __future__ import annotations

import argparse
import datetime
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import separador_etiquetas_ml as core  # noqa: E402

PASTA = Path(__file__).resolve().parent
ARQUIVO_DB = PASTA / "historico_ads.sqlite3"

# Campos aceitos pelo endpoint de listagem (campaigns/search) — ver doc.
METRICAS_CAMPANHA = [
    "clicks", "prints", "ctr", "cost", "cpc", "acos", "cvr", "roas", "sov",
    "units_quantity", "total_amount", "direct_amount", "indirect_amount",
    "direct_units_quantity", "indirect_units_quantity",
    "organic_units_quantity", "organic_units_amount", "organic_items_quantity",
    "direct_items_quantity", "indirect_items_quantity", "advertising_items_quantity",
]
# So existem no endpoint de DETALHE por campanha (nao na listagem) — o sinal
# oficial de causa da perda de impressao (orcamento vs. ranking).
METRICAS_DETALHE = [
    "impression_share", "top_impression_share",
    "lost_impression_share_by_budget", "lost_impression_share_by_ad_rank",
    "acos_benchmark",
]
# Campos aceitos pelo endpoint de ad_groups (search/detalhe) — subconjunto do
# de campanha (sem acos/roas/cvr/sov, que so existem a nivel de campanha).
METRICAS_AD_GROUP = [
    "clicks", "prints", "cost", "cpc", "ctr",
    "direct_amount", "indirect_amount", "total_amount",
    "direct_units_quantity", "indirect_units_quantity", "units_quantity",
]
# Limite padrao de paginacao da API (documentado) — buscar_ad_groups_da_campanha
# pagina com offset ate cobrir o "total" da resposta.
LIMITE_PAGINA_AD_GROUPS = 50

# NOTA: sem paginacao — o limite padrao da API e 50 campanhas por advertiser
# (documentado), acima do volume atual das duas contas (3 cada). Revisar se
# alguma conta passar de ~50 campanhas ativas.
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS campanhas_diarias (
    data TEXT NOT NULL,
    conta TEXT NOT NULL,
    site_id TEXT NOT NULL,
    advertiser_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    campaign_name TEXT,
    status TEXT,
    budget REAL,
    strategy TEXT,
    roas_target REAL,
    clicks INTEGER, prints INTEGER, ctr REAL, cost REAL, cpc REAL,
    acos REAL, cvr REAL, roas REAL, sov REAL,
    units_quantity INTEGER, total_amount REAL,
    direct_amount REAL, indirect_amount REAL,
    direct_units_quantity INTEGER, indirect_units_quantity INTEGER,
    organic_units_quantity INTEGER, organic_units_amount REAL,
    organic_items_quantity INTEGER, direct_items_quantity INTEGER,
    indirect_items_quantity INTEGER, advertising_items_quantity INTEGER,
    impression_share REAL, top_impression_share REAL,
    lost_impression_share_by_budget REAL, lost_impression_share_by_ad_rank REAL,
    acos_benchmark REAL,
    coletado_em TEXT NOT NULL,
    PRIMARY KEY (data, conta, campaign_id)
);
CREATE TABLE IF NOT EXISTS ad_groups_diarios (
    data TEXT NOT NULL,
    conta TEXT NOT NULL,
    site_id TEXT NOT NULL,
    advertiser_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    ad_group_id TEXT NOT NULL,
    ad_group_title TEXT,
    ad_group_type TEXT,
    clicks INTEGER, prints INTEGER, cost REAL, cpc REAL, ctr REAL,
    direct_amount REAL, indirect_amount REAL, total_amount REAL,
    direct_units_quantity INTEGER, indirect_units_quantity INTEGER,
    units_quantity INTEGER,
    coletado_em TEXT NOT NULL,
    PRIMARY KEY (data, conta, ad_group_id)
);
CREATE TABLE IF NOT EXISTS ad_group_itens_diarios (
    data TEXT NOT NULL,
    conta TEXT NOT NULL,
    ad_group_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    sku TEXT,
    titulo TEXT,
    preco REAL,
    coletado_em TEXT NOT NULL,
    PRIMARY KEY (data, conta, ad_group_id, item_id)
);
"""


def conectar_db(caminho=ARQUIVO_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(caminho)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def _get(path: str, token: str, headers: dict | None = None):
    """GET cru contra a API do ML. Devolve (status, json|None, erro|None).
    NUNCA levanta — quem chama decide o que fazer com o status (mesmo
    espirito do _com_retry do nucleo, mas sem retry: coleta diaria pode
    tentar de novo no proximo dia sem prejuizo)."""
    h = {"Authorization": f"Bearer {token}"}
    if headers:
        h.update(headers)
    try:
        r = requests.get(core.API + path, headers=h, timeout=core.TIMEOUT)
    except requests.RequestException as e:
        return "ERRO", None, type(e).__name__
    try:
        data = r.json()
    except ValueError:
        data = None
    return r.status_code, data, None


def buscar_advertiser(token: str) -> tuple[str, str] | None:
    """Descobre (advertiser_id, site_id) do Product Ads (product_id=PADS).
    None se a conta nao tiver Product Ads habilitado ou a chamada falhar."""
    st, data, _ = _get("/advertising/advertisers?product_id=PADS", token,
                       {"Api-Version": "1"})
    if st != 200 or not isinstance(data, dict):
        return None
    advs = data.get("advertisers") or []
    if not advs or not isinstance(advs, list):
        return None
    a = advs[0]
    aid = a.get("advertiser_id") or a.get("id")
    site = a.get("site_id")
    if not aid or not site:
        return None
    return str(aid), str(site)


def buscar_campanhas_do_dia(token: str, site_id: str, advertiser_id: str,
                            dia: datetime.date) -> list[dict]:
    """Campanhas do advertiser com metricas de UM dia (date_from==date_to).
    [] se a chamada falhar ou nao houver campanha — nunca levanta."""
    qs = urlencode({
        "date_from": dia.isoformat(),
        "date_to": dia.isoformat(),
        "metrics": ",".join(METRICAS_CAMPANHA),
    })
    path = (f"/advertising/{site_id}/advertisers/{advertiser_id}"
            f"/product_ads/campaigns/search?{qs}")
    st, data, _ = _get(path, token, {"Api-Version": "2"})
    if st != 200 or not isinstance(data, dict):
        return []
    camps = data.get("results") or data.get("campaigns") or []
    return camps if isinstance(camps, list) else []


def buscar_detalhe_campanha(token: str, site_id: str, campaign_id: str,
                            dia: datetime.date) -> dict:
    """Metricas de limitacao (orcamento/ranking) de UMA campanha no dia.
    {} se falhar — best-effort: o snapshot principal ja foi obtido, este
    detalhe extra nao pode impedir a gravacao do resto."""
    qs = urlencode({
        "date_from": dia.isoformat(),
        "date_to": dia.isoformat(),
        "metrics": ",".join(METRICAS_DETALHE),
    })
    path = f"/advertising/{site_id}/product_ads/campaigns/{campaign_id}?{qs}"
    st, data, _ = _get(path, token, {"Api-Version": "2"})
    if st != 200 or not isinstance(data, dict):
        return {}
    m = data.get("metrics")
    return m if isinstance(m, dict) else {}


def buscar_ad_groups_da_campanha(token: str, site_id: str, advertiser_id: str,
                                 campaign_id: str, dia: datetime.date) -> list[dict]:
    """Todos os ad_groups (item/familia/catalogo anunciado) de UMA campanha no
    dia -- pagina com offset ate cobrir o total (a resposta vem limitada a
    LIMITE_PAGINA_AD_GROUPS por chamada). [] se falhar -- nunca levanta."""
    resultados: list[dict] = []
    offset = 0
    while True:
        qs = urlencode({
            "date_from": dia.isoformat(), "date_to": dia.isoformat(),
            "metrics": ",".join(METRICAS_AD_GROUP),
            "filters[campaign_id]": campaign_id, "offset": offset,
        })
        path = (f"/advertising/{site_id}/advertisers/{advertiser_id}"
               f"/product_ads/ad_groups/search?{qs}")
        st, data, _ = _get(path, token, {"Api-Version": "2"})
        if st != 200 or not isinstance(data, dict):
            break
        pagina = data.get("results")
        if not isinstance(pagina, list) or not pagina:
            break
        resultados.extend(pagina)
        paging = data.get("paging") or {}
        total = paging.get("total")
        limite = paging.get("limit") or len(pagina)
        offset += limite
        if not isinstance(total, int) or offset >= total:
            break
    return resultados


def buscar_itens_do_ad_group(token: str, site_id: str, ad_group_id: str,
                             dia: datetime.date) -> list[dict]:
    """Item_id(s) que compoe UM ad_group no dia (pode ser mais de 1 -- tipos
    FAMILY/CATALOG agrupam variacoes/concorrentes). [] se falhar."""
    qs = urlencode({"date_from": dia.isoformat(), "date_to": dia.isoformat()})
    path = f"/advertising/{site_id}/product_ads/ad_groups/{ad_group_id}/ads?{qs}"
    st, data, _ = _get(path, token, {"Api-Version": "2"})
    if st != 200 or not isinstance(data, dict):
        return []
    itens = data.get("results")
    return itens if isinstance(itens, list) else []


def salvar_campanha(conn: sqlite3.Connection, *, dia: datetime.date, conta: str,
                    site_id: str, advertiser_id: str, campanha: dict,
                    detalhe: dict) -> None:
    """Grava (ou regrava) UMA linha — chave (data, conta, campaign_id), para
    re-rodar o mesmo dia ser idempotente em vez de duplicar."""
    m = campanha.get("metrics") or {}
    cid = campanha.get("id") or campanha.get("campaign_id")
    linha = {
        "data": dia.isoformat(), "conta": conta, "site_id": site_id,
        "advertiser_id": advertiser_id, "campaign_id": str(cid),
        "campaign_name": campanha.get("name") or campanha.get("campaign_name"),
        "status": campanha.get("status"), "budget": campanha.get("budget"),
        "strategy": campanha.get("strategy"),
        "roas_target": campanha.get("roas_target"),
        "clicks": m.get("clicks"), "prints": m.get("prints"), "ctr": m.get("ctr"),
        "cost": m.get("cost"), "cpc": m.get("cpc"), "acos": m.get("acos"),
        "cvr": m.get("cvr"), "roas": m.get("roas"), "sov": m.get("sov"),
        "units_quantity": m.get("units_quantity"),
        "total_amount": m.get("total_amount"),
        "direct_amount": m.get("direct_amount"),
        "indirect_amount": m.get("indirect_amount"),
        "direct_units_quantity": m.get("direct_units_quantity"),
        "indirect_units_quantity": m.get("indirect_units_quantity"),
        "organic_units_quantity": m.get("organic_units_quantity"),
        "organic_units_amount": m.get("organic_units_amount"),
        "organic_items_quantity": m.get("organic_items_quantity"),
        "direct_items_quantity": m.get("direct_items_quantity"),
        "indirect_items_quantity": m.get("indirect_items_quantity"),
        "advertising_items_quantity": m.get("advertising_items_quantity"),
        "impression_share": detalhe.get("impression_share"),
        "top_impression_share": detalhe.get("top_impression_share"),
        "lost_impression_share_by_budget": detalhe.get("lost_impression_share_by_budget"),
        "lost_impression_share_by_ad_rank": detalhe.get("lost_impression_share_by_ad_rank"),
        "acos_benchmark": detalhe.get("acos_benchmark"),
        "coletado_em": datetime.datetime.now(core.TZ_BR).isoformat(timespec="seconds"),
    }
    campos = ", ".join(linha.keys())
    marcas = ", ".join("?" for _ in linha)
    conn.execute(f"INSERT OR REPLACE INTO campanhas_diarias ({campos}) "
                f"VALUES ({marcas})", list(linha.values()))


def salvar_ad_group(conn: sqlite3.Connection, *, dia: datetime.date, conta: str,
                    site_id: str, advertiser_id: str, campaign_id: str,
                    ad_group: dict) -> None:
    """Grava (ou regrava) UMA linha de ad_group -- chave (data, conta,
    ad_group_id), mesmo padrao idempotente de salvar_campanha."""
    m = ad_group.get("metrics") or {}
    agid = ad_group.get("id") or ad_group.get("ad_group_id")
    linha = {
        "data": dia.isoformat(), "conta": conta, "site_id": site_id,
        "advertiser_id": advertiser_id, "campaign_id": str(campaign_id),
        "ad_group_id": str(agid),
        "ad_group_title": ad_group.get("title"),
        "ad_group_type": ad_group.get("ad_group_type"),
        "clicks": m.get("clicks"), "prints": m.get("prints"), "cost": m.get("cost"),
        "cpc": m.get("cpc"), "ctr": m.get("ctr"),
        "direct_amount": m.get("direct_amount"),
        "indirect_amount": m.get("indirect_amount"),
        "total_amount": m.get("total_amount"),
        "direct_units_quantity": m.get("direct_units_quantity"),
        "indirect_units_quantity": m.get("indirect_units_quantity"),
        "units_quantity": m.get("units_quantity"),
        "coletado_em": datetime.datetime.now(core.TZ_BR).isoformat(timespec="seconds"),
    }
    campos = ", ".join(linha.keys())
    marcas = ", ".join("?" for _ in linha)
    conn.execute(f"INSERT OR REPLACE INTO ad_groups_diarios ({campos}) "
                f"VALUES ({marcas})", list(linha.values()))


def _resolver_sku_adocao(item_id: str, skus_anuncio: dict) -> str | None:
    """Fallback: SKU a partir do de-para local skus_por_anuncio.json (mesma
    chave que identidade() usa p/ anuncio sem variacao, '{item_id}:0'). So usado
    quando o item NAO tem seller_sku cadastrado (ver _resolver_skus) -- mesma
    prioridade de identidade() no nucleo."""
    return skus_anuncio.get(f"{item_id}:0")


def _resolver_skus(token: str, cache: dict, item_ids, skus_anuncio: dict) -> dict[str, str | None]:
    """Resolve SKU de varios item_id de uma vez. Prioriza o seller_sku REAL
    (GET /items/{id}, cacheado em itens_cache.json via core.buscar_detalhes --
    mesmo cache que a impressao ja usa e mantem, sem chamada de escrita) e cai
    pro mapa de adocao local quando o item nao tem seller_sku cadastrado.
    Entradas do cache anteriores a esta funcionalidade nao tem a chave
    'seller_sku' -- forca o refetch delas em vez de assumir 'sem SKU' por
    engano (cache staleness)."""
    ids = {str(i) for i in item_ids if i}
    if not ids:
        return {}
    incompletos = [i for i in ids if i in cache and "seller_sku" not in cache[i]]
    for i in incompletos:
        del cache[i]
    core.buscar_detalhes(token, ids, cache)
    resultado: dict[str, str | None] = {}
    for item_id in ids:
        entrada = cache.get(item_id) or {}
        resultado[item_id] = entrada.get("seller_sku") or _resolver_sku_adocao(item_id, skus_anuncio)
    return resultado


def salvar_item_ad_group(conn: sqlite3.Connection, *, dia: datetime.date, conta: str,
                         ad_group_id: str, item: dict, sku: str | None) -> None:
    """Grava (ou regrava) UM item dentro de um ad_group -- chave (data, conta,
    ad_group_id, item_id)."""
    item_id = item.get("item_id")
    linha = {
        "data": dia.isoformat(), "conta": conta, "ad_group_id": str(ad_group_id),
        "item_id": str(item_id), "sku": sku, "titulo": item.get("title"),
        "preco": item.get("price"),
        "coletado_em": datetime.datetime.now(core.TZ_BR).isoformat(timespec="seconds"),
    }
    campos = ", ".join(linha.keys())
    marcas = ", ".join("?" for _ in linha)
    conn.execute(f"INSERT OR REPLACE INTO ad_group_itens_diarios ({campos}) "
                f"VALUES ({marcas})", list(linha.values()))


def _teve_atividade(metrics: dict) -> bool:
    """Um ad_group so vale a pena resolver pro item_id (chamada extra) se
    teve gasto/clique/venda no dia -- a maioria fica zerada (validado com
    dado real: numa campanha de 3, so 1 tinha atividade no dia)."""
    return any((metrics.get(k) or 0) for k in ("clicks", "cost", "units_quantity"))


def _coletar_ad_groups_da_campanha(conn: sqlite3.Connection, token: str, site_id: str,
                                   advertiser_id: str, conta: str, campaign_id: str,
                                   dia: datetime.date, cache: dict, skus_anuncio: dict) -> int:
    """Ad_groups de UMA campanha + resolucao de item_id/SKU dos que tiveram
    atividade no dia. Devolve quantos ad_groups foram gravados. A resolucao de
    SKU e feita numa unica leva (todos os itens da campanha), nao item a item
    -- menos overhead de cache/thread-pool no core.buscar_detalhes."""
    ad_groups = buscar_ad_groups_da_campanha(token, site_id, advertiser_id,
                                             campaign_id, dia)
    itens_por_ad_group: dict[str, list[dict]] = {}
    for ag in ad_groups:
        salvar_ad_group(conn, dia=dia, conta=conta, site_id=site_id,
                        advertiser_id=advertiser_id, campaign_id=campaign_id,
                        ad_group=ag)
        agid = ag.get("id") or ag.get("ad_group_id")
        if not agid or not _teve_atividade(ag.get("metrics") or {}):
            continue
        itens = [it for it in buscar_itens_do_ad_group(token, site_id, agid, dia)
                if it.get("item_id")]
        if itens:
            itens_por_ad_group[agid] = itens

    todos_item_ids = {it["item_id"] for itens in itens_por_ad_group.values() for it in itens}
    skus = _resolver_skus(token, cache, todos_item_ids, skus_anuncio)
    for agid, itens in itens_por_ad_group.items():
        for item in itens:
            salvar_item_ad_group(conn, dia=dia, conta=conta, ad_group_id=agid,
                                item=item, sku=skus.get(str(item["item_id"])))
    return len(ad_groups)


def coletar_conta(conn: sqlite3.Connection, conta: str, dia: datetime.date) -> dict:
    """Coleta 1 conta p/ 1 dia. Isola falha — nunca levanta (uma conta ruim
    nao pode derrubar a coleta das demais no mesmo run)."""
    resultado = {"conta": conta, "ok": False, "campanhas": 0, "ad_groups": 0,
                "erro": None}
    try:
        if conta:
            core.definir_conta(conta)
        cred = core.carregar_credenciais()
        token = core.obter_token(cred)
    except Exception as e:
        resultado["erro"] = f"falha de autenticacao: {type(e).__name__}"
        return resultado

    adv = buscar_advertiser(token)
    if not adv:
        resultado["erro"] = "advertiser nao encontrado (conta sem Product Ads?)"
        return resultado
    advertiser_id, site_id = adv
    skus_anuncio = core.carregar_skus_anuncio()
    cache = core.carregar_cache()

    campanhas = buscar_campanhas_do_dia(token, site_id, advertiser_id, dia)
    total_ad_groups = 0
    for c in campanhas:
        cid = c.get("id") or c.get("campaign_id")
        detalhe = buscar_detalhe_campanha(token, site_id, cid, dia) if cid else {}
        salvar_campanha(conn, dia=dia, conta=conta, site_id=site_id,
                        advertiser_id=advertiser_id, campanha=c, detalhe=detalhe)
        if cid:
            total_ad_groups += _coletar_ad_groups_da_campanha(
                conn, token, site_id, advertiser_id, conta, cid, dia, cache, skus_anuncio)
    conn.commit()
    resultado["ok"] = True
    resultado["campanhas"] = len(campanhas)
    resultado["ad_groups"] = total_ad_groups
    return resultado


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Coleta snapshot diario do Product Ads.")
    ap.add_argument("--dia", default=None, help="AAAA-MM-DD (default: ontem, Brasilia)")
    ap.add_argument("--conta", default=None,
                    help="uma conta especifica (default: todas configuradas)")
    ap.add_argument("--db", default=str(ARQUIVO_DB), help="caminho do SQLite")
    args = ap.parse_args(argv)

    dia = (datetime.date.fromisoformat(args.dia) if args.dia
          else datetime.datetime.now(core.TZ_BR).date() - datetime.timedelta(days=1))
    contas = [args.conta] if args.conta else core.listar_contas()
    if not contas:
        print("Nenhuma conta configurada em contas/.")
        return 1

    conn = conectar_db(args.db)
    try:
        falhas = 0
        for conta in contas:
            r = coletar_conta(conn, conta, dia)
            if r["ok"]:
                print(f"  {conta}: {r['campanhas']} campanha(s), "
                     f"{r['ad_groups']} ad group(s) salvos para {dia}")
            else:
                falhas += 1
                print(f"  {conta}: FALHOU -- {r['erro']}")
        print(f"\nColeta de {dia} concluida. {len(contas) - falhas}/{len(contas)} conta(s) OK.")
        return 1 if falhas else 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
