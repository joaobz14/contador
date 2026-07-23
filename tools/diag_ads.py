#!/usr/bin/env python3
"""Validacao SO-LEITURA do acesso ao Product Ads do Mercado Livre.

Confirma, na SUA conta, se o token do app acessa o Product Ads e descobre o
`advertiser_id` — base para o futuro monitor de campanhas.

- SO requisicoes GET; nao altera NADA (nao pausa/edita campanha, nao mexe em
  orcamento). Nenhuma chamada de escrita.
- NUNCA imprime token/secret/Authorization. Mascara `advertiser_id`, `user_id` e
  nomes. A saida e segura para colar aqui.
- Empirico: TESTA endpoints candidatos e reporta o status de cada um (nao presume
  que os antigos continuam validos). Os caminhos exatos serao confirmados na doc
  oficial; aqui o objetivo e ver o que a SUA conta realmente responde.

Uso:
    python tools/diag_ads.py [conta]     # valida uma conta (default: conta ativa)
    python tools/diag_ads.py --todas     # valida todas as contas configuradas
"""
from __future__ import annotations

import os
import sys

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

    # 3) campanhas (candidatos) — so LISTAGEM, sem detalhe.
    # IMPORTANTE (achado nesta rodada): os endpoints legados de Product Ads
    # (product_id=PADS na URL de campanhas) foram DESATIVADOS em 26/02/2026 —
    # ja passou. Os 404 anteriores eram esperados por esse motivo, nao erro de
    # codigo. O padrao novo (fontes: busca web, nao confirmado na doc oficial
    # ainda — conector MercadoLibre indisponivel) usa o site_id do advertiser
    # no path. Ha 2 variantes conflitantes nas fontes; testamos as duas.
    site_id = site_id or "MLB"  # fallback: unico site que este app opera
    print(f"  --- campanhas do advertiser {_mask(advertiser_id)} "
          f"(site_id={site_id}; candidatos) ---")
    cand_campanhas = [
        (f"/advertising/{site_id}/advertisers/{advertiser_id}/product_ads/campaigns/search",
         {"Api-Version": "2"}),
        (f"/marketplace/advertising/{site_id}/advertisers/{advertiser_id}/product_ads/campaigns",
         {"Api-Version": "2"}),
        # legado: esperado 404 (desativado 26/02/2026) — mantido so p/ confirmar
        (f"/advertising/advertisers/{advertiser_id}/product_ads/campaigns",
         {"Api-Version": "1"}),
    ]
    for path, hdr in cand_campanhas:
        st, data, err = _get(path, token, hdr)
        n = None
        if st == 200 and isinstance(data, dict):
            camps = data.get("campaigns") or data.get("results") or []
            n = len(camps) if isinstance(camps, list) else "?"
        # mascara o advertiser_id SE ele aparecer no path, mas preserva o resto
        # (inclusive a query string) — cortar a query fazia 2 candidatos
        # diferentes imprimirem o mesmo texto (parecia bug de copia-e-cola).
        safe = path.replace(advertiser_id, _mask(advertiser_id))
        print(f"    GET {safe} -> {st} "
              f"{('| '+str(n)+' campanha(s)') if n is not None else _categoria(st)} {err or ''}")

    print("  RESULTADO: advertiser encontrado; veja acima qual endpoint de campanha "
          "respondeu 200. O candidato legado (3o) DEVE dar 404 (endpoints antigos de "
          "Product Ads foram desativados em 26/02/2026) — isso e esperado, nao erro. "
          "Me mande esta saida (advertiser_id vem MASCARADO).")


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
