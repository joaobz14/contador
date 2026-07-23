#!/usr/bin/env python3
"""Coletor deterministico do Product Ads (Mercado Livre).

Grava, uma vez por dia, o snapshot das metricas de cada campanha das contas
configuradas (Cozilatti, Gastromaq...) num SQLite LOCAL — a base historica do
futuro monitor. Camada 1 (coleta); motor de recomendacao e dado de margem
ficam para uma proxima etapa.

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

Endpoints usados (confirmados na doc oficial "Product Ads" do Mercado Livre
Developers, via conector MercadoLibre):
  GET /advertising/advertisers?product_id=PADS
  GET /advertising/{site}/advertisers/{advertiser_id}/product_ads/campaigns/search
  GET /advertising/{site}/product_ads/campaigns/{campaign_id}

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
"""


def conectar_db(caminho=ARQUIVO_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(caminho)
    conn.execute(SCHEMA_SQL)
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


def coletar_conta(conn: sqlite3.Connection, conta: str, dia: datetime.date) -> dict:
    """Coleta 1 conta p/ 1 dia. Isola falha — nunca levanta (uma conta ruim
    nao pode derrubar a coleta das demais no mesmo run)."""
    resultado = {"conta": conta, "ok": False, "campanhas": 0, "erro": None}
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

    campanhas = buscar_campanhas_do_dia(token, site_id, advertiser_id, dia)
    for c in campanhas:
        cid = c.get("id") or c.get("campaign_id")
        detalhe = buscar_detalhe_campanha(token, site_id, cid, dia) if cid else {}
        salvar_campanha(conn, dia=dia, conta=conta, site_id=site_id,
                        advertiser_id=advertiser_id, campanha=c, detalhe=detalhe)
    conn.commit()
    resultado["ok"] = True
    resultado["campanhas"] = len(campanhas)
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
                print(f"  {conta}: {r['campanhas']} campanha(s) salvas para {dia}")
            else:
                falhas += 1
                print(f"  {conta}: FALHOU -- {r['erro']}")
        print(f"\nColeta de {dia} concluida. {len(contas) - falhas}/{len(contas)} conta(s) OK.")
        return 1 if falhas else 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
