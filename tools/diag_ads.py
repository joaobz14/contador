#!/usr/bin/env python3
"""Validacao SO-LEITURA do acesso ao Product Ads do Mercado Livre.

Confirma, na SUA conta, se o token do app acessa o Product Ads, descobre o
`advertiser_id` e traz uma janela curta de metricas — base para o futuro monitor
de campanhas.

- SO requisicoes GET; nao altera NADA (nao pausa/edita campanha, nao mexe em
  orcamento). Nenhuma chamada de escrita.
- NUNCA imprime token/secret/Authorization. Mascara `advertiser_id`/`user_id`.
  Nomes e metricas de campanha NAO sao mascarados (sao dados do proprio usuario).
- Endpoint de campanhas CONFIRMADO na doc oficial (via conector MercadoLibre,
  pagina "Product Ads" — product-ads-leitura):
      GET /advertising/{site_id}/advertisers/{advertiser_id}/product_ads/campaigns/search
  header `Api-Version: 2` (nomes de header sao case-insensitive por HTTP).
  Os endpoints legados testados como fallback (ex.:
  /advertising/advertisers/{id}/product_ads/campaigns) estao na lista OFICIAL de
  descontinuados em 26/02/2026 (ja passou) — 404 e o esperado, confirmado na doc.

Uso:
    python tools/diag_ads.py [conta]     # valida uma conta (default: conta ativa)
    python tools/diag_ads.py --todas     # valida todas as contas configuradas
"""
from __future__ import annotations

import datetime
import os
import sys
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import separador_etiquetas_ml as core  # noqa: E402


def _mask(v) -> str:
    s = str(v or "")
    if not s:
        return "(vazio)"
    return f"{s[:2]}...{s[-2:]} ({len(s)} chars)" if len(s) > 5 else "***"


def _get(path, token, headers=None):
    """GET cru. Devolve (status, json|None, erro). A URL do ML nao leva token na
    query (Bearer no header), entao o path e seguro de exibir."""
    import requests
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


def _categoria(status) -> str:
    return {
        400: "parametro invalido (data/metrics mal formatado?)",
        401: "token expirado/invalido",
        403: "sem permissao (app/conta nao habilitado p/ Ads?)",
        404: "endpoint/advertiser nao encontrado (path errado ou nao anunciante)",
        405: "endpoint existe mas GET nao e o metodo certo (talvez precise POST)",
        406: "versao de API incorreta (header Api-Version)",
        429: "rate limit",
    }.get(status, "")


def _validar_conta(conta: str) -> None:
    # rotulo ANTES de trocar de conta: definir_conta() so troca os arquivos
    # (ARQUIVO_CRED etc.), nao o config.json — conta_ativa() apos o switch
    # continuaria devolvendo a conta antiga da GUI (rotulo errado no --todas;
    # os arquivos/token usados abaixo ja eram os certos, so o texto enganava).
    rotulo = conta or core.conta_ativa() or "(padrao)"
    if conta:
        core.definir_conta(conta)
    print("=" * 60)
    print(f"CONTA: {rotulo}")
    cred = core.carregar_credenciais()
    token = core.obter_token(cred)
    seller_cred = str(cred.get("seller_id", ""))

    # 1) identidade — o token aponta para a conta certa?
    st, me, err = _get("/users/me", token)
    if st == 200 and me:
        uid = str(me.get("id", ""))
        bate = "OK (bate com a credencial)" if uid == seller_cred else "DIVERGE!"
        print(f"  identidade /users/me -> {st} | user_id {_mask(uid)} | "
              f"seller_id credencial {_mask(seller_cred)} | {bate}")
    else:
        print(f"  identidade /users/me -> {st} {_categoria(st)} {err or ''}")
        print("  (sem identidade valida, o resto nao vai funcionar — verifique o token)")
        return

    # 2) descoberta de advertiser (Product Ads = product_id PADS)
    print("  --- descoberta de advertiser (candidatos; reporta o que responder) ---")
    tentativas = [
        ("/advertising/advertisers?product_id=PADS", {"Api-Version": "1"}),
        ("/advertising/advertisers?product_id=PADS", {"Api-Version": "2"}),
        ("/advertising/advertisers?product_id=PADS", None),
    ]
    advertiser_id = None
    site_id = None
    for path, hdr in tentativas:
        st, data, err = _get(path, token, hdr)
        vsn = (hdr or {}).get("Api-Version", "-")
        n = None
        if st == 200 and isinstance(data, dict):
            advs = data.get("advertisers") or data.get("results") or []
            n = len(advs) if isinstance(advs, list) else "?"
            for a in (advs if isinstance(advs, list) else []):
                aid = a.get("advertiser_id") or a.get("id")
                site = a.get("site_id")
                if aid and not advertiser_id:
                    advertiser_id = str(aid)
                    site_id = site
                print(f"      advertiser: id {_mask(aid)} site={site}")
        print(f"    GET advertisers (Api-Version {vsn}) -> {st} "
              f"{('| '+str(n)+' advertiser(s)') if n is not None else _categoria(st)} {err or ''}")
        if advertiser_id:
            break

    if not advertiser_id:
        print("  RESULTADO: nao encontrei advertiser_id de Product Ads nesta conta.")
        print("  Causas possiveis: conta nao habilitada como anunciante, app sem o "
              "produto Advertising, ou o endpoint mudou (confirmar na doc). Ver o "
              "status/categoria acima para diferenciar.")
        return

    # 3) campanhas + janela curta de metricas (7 dias, ate ONTEM — a doc oficial
    # diz que os dados sao atualizados as 10:00 GMT-3, entao "hoje" viria
    # incompleto; evita recomendacao em cima de dado provisorio).
    # Endpoint CONFIRMADO na doc oficial "Product Ads" (product-ads-leitura, via
    # conector MercadoLibre): o MESMO endpoint da listagem aceita
    # date_from/date_to/metrics/metrics_summary — sem chamada extra p/ metricas.
    #   GET /advertising/{site_id}/advertisers/{advertiser_id}/product_ads/campaigns/search
    site_id = site_id or "MLB"  # fallback: unico site que este app opera
    hoje = datetime.datetime.now(core.TZ_BR).date()
    date_to = hoje - datetime.timedelta(days=1)
    date_from = date_to - datetime.timedelta(days=6)
    metricas = ["clicks", "prints", "ctr", "cost", "cpc", "acos", "cvr", "roas",
                "units_quantity", "total_amount", "organic_units_quantity"]
    qs = urlencode({
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "metrics": ",".join(metricas),
        "metrics_summary": "true",
    })
    print(f"  --- campanhas do advertiser {_mask(advertiser_id)} (site_id={site_id}) "
          f"| janela {date_from.isoformat()} a {date_to.isoformat()} ---")
    cand_campanhas = [
        (f"/advertising/{site_id}/advertisers/{advertiser_id}"
         f"/product_ads/campaigns/search?{qs}", {"Api-Version": "2"}),
        # legado, CONFIRMADO na doc oficial como descontinuado em 26/02/2026 —
        # so fallback final; 404 e o esperado (sem sentido pedir metricas aqui).
        (f"/advertising/advertisers/{advertiser_id}/product_ads/campaigns",
         {"Api-Version": "1"}),
    ]
    campanhas = None       # None = nenhum endpoint OK ainda; [] = OK mas 0 campanhas
    resumo_janela = None
    endpoint_ok = False
    for path, hdr in cand_campanhas:
        st, data, err = _get(path, token, hdr)
        n = None
        if st == 200 and isinstance(data, dict):
            camps = data.get("campaigns") or data.get("results") or []
            if isinstance(camps, list):
                n = len(camps)
                campanhas = camps
                resumo_janela = data.get("metrics_summary")
                endpoint_ok = True
        # mascara o advertiser_id SE ele aparecer no path; a query de data/metrica
        # nao carrega segredo (so datas e nomes de campo), fica visivel.
        safe = path.replace(advertiser_id, _mask(advertiser_id))
        print(f"    GET {safe} -> {st} "
              f"{('| '+str(n)+' campanha(s)') if n is not None else _categoria(st)} {err or ''}")
        if endpoint_ok:
            break  # achou o endpoint certo; nao precisa testar o fallback

    if not endpoint_ok:
        print("  RESULTADO: nenhum endpoint de campanha respondeu 200 nesta conta. "
              "Me mande esta saida (advertiser_id MASCARADO) para eu revisar os candidatos.")
        return
    if not campanhas:
        print("  RESULTADO: endpoint OK, mas 0 campanhas retornadas (conta sem "
              "campanha de Product Ads criada, ou todas fora do filtro default).")
        return

    print(f"\n  --- {len(campanhas)} campanha(s) (dado do PROPRIO usuario, nao e segredo) ---")
    for c in campanhas:
        cid = c.get("id") or c.get("campaign_id")
        nome = c.get("name") or c.get("campaign_name") or "(sem nome)"
        status = c.get("status")
        orcamento = c.get("budget")
        m = c.get("metrics") or {}
        print(f"      [{_mask(cid)}] '{nome}' status={status} "
              f"orcamento={orcamento if orcamento is not None else '?'} "
              f"strategy={c.get('strategy')} roas_target={c.get('roas_target')}")
        if m:
            print(f"          janela 7d: clicks={m.get('clicks')} prints={m.get('prints')} "
                  f"cost={m.get('cost')} cpc={m.get('cpc')} ctr={m.get('ctr')} "
                  f"acos={m.get('acos')} roas={m.get('roas')} cvr={m.get('cvr')} "
                  f"vendas={m.get('units_quantity')} receita={m.get('total_amount')}")

    ativas = [c for c in campanhas if str(c.get("status", "")).lower() in
              ("active", "activo", "ativa", "ativo")]
    print(f"\n  RESUMO: {len(campanhas)} campanha(s) no total, "
          f"{len(ativas)} com status 'active/ativa'.")
    if resumo_janela:
        print(f"  metrics_summary da janela (soma de todas as campanhas): {resumo_janela}")

    # 4) detalhe por campanha: sinal OFICIAL de limitacao por orcamento
    # (lost_impression_share_by_budget) — endpoint DIFERENTE do de listagem,
    # confirmado na doc oficial (NAO fica sob /advertisers/{id}/):
    #   GET /advertising/{site_id}/product_ads/campaigns/{campaign_id}
    # Uma chamada por campanha ja conhecida (poucas — sem paginar nem varrer
    # anuncios). O campo 'budget' e media diaria de um ciclo MENSAL com
    # rollover (a doc explica); por isso o sinal certo de "limitado por
    # orcamento" e este campo oficial, NAO um calculo caseiro custo/orcamento.
    print("\n  --- detalhe por campanha: limitacao por orcamento/ranking "
          "(mesma janela) ---")
    metricas_detalhe = ["impression_share", "top_impression_share",
                        "lost_impression_share_by_budget",
                        "lost_impression_share_by_ad_rank", "acos_benchmark",
                        "roas", "acos"]
    qs_detalhe = urlencode({
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "metrics": ",".join(metricas_detalhe),
    })
    for c in campanhas:
        cid = c.get("id") or c.get("campaign_id")
        nome = c.get("name") or c.get("campaign_name") or "(sem nome)"
        if not cid:
            continue
        path = f"/advertising/{site_id}/product_ads/campaigns/{cid}?{qs_detalhe}"
        st, data, err = _get(path, token, {"Api-Version": "2"})
        safe_path = path.replace(str(cid), _mask(cid))
        if st == 200 and isinstance(data, dict):
            m = data.get("metrics") or {}
            print(f"      GET {safe_path} -> {st}")
            print(f"          '{nome}': impression_share={m.get('impression_share')} "
                  f"perdido_por_orcamento={m.get('lost_impression_share_by_budget')} "
                  f"perdido_por_ranking={m.get('lost_impression_share_by_ad_rank')} "
                  f"acos_benchmark={m.get('acos_benchmark')}")
        else:
            print(f"      GET {safe_path} -> {st} {_categoria(st)} {err or ''}")

    print("\n  Me mande esta saida (ids MASCARADOS; nomes/metricas sao dados seus mesmo).")


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--todas":
        contas = core.listar_contas()
        if not contas:
            print("Nenhuma conta configurada em contas/.")
            return 1
        for c in contas:
            _validar_conta(c)
            print()
        return 0
    _validar_conta(args[0] if args else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
