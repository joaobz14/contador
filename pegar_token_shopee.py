"""
pegar_token_shopee.py
Programa de UMA VEZ SO. Autoriza sua loja na Shopee Open Platform e salva tudo
em 'credenciais_shopee.json'.

Pre-requisitos (criar em https://open.shopee.com):
  - registrar um app e pegar o App ID (partner_id) e a Partner Key (partner_secret);
  - cadastrar uma URL de redirect (pode ser https://www.google.com para teste).

Como usar:
  1) pip install requests
  2) python pegar_token_shopee.py
  3) siga as instrucoes na tela (abrir o link, autorizar, colar a URL de retorno)
"""

import hashlib
import hmac
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

HOST = "https://partner.shopeemobile.com"   # CONFIRMAR host da sua regiao no painel
ARQUIVO = Path("credenciais_shopee.json")


def perguntar(rotulo: str) -> str:
    valor = ""
    while not valor.strip():
        valor = input(rotulo).strip()
    return valor


def assinar(partner_key: str, base: str) -> str:
    return hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()


def main() -> None:
    print("=" * 60)
    print(" AUTORIZACAO DA LOJA NA SHOPEE")
    print("=" * 60)

    partner_id = perguntar("\n1) App ID (partner_id):\n> ")
    partner_key = perguntar("\n2) Partner Key (partner_secret):\n> ")
    redirect = input(
        "\n3) URL de redirect cadastrada no app (Enter = https://www.google.com):\n> "
    ).strip() or "https://www.google.com"

    # Monta o link de autorizacao (assinatura publica: partner_id + path + timestamp).
    path = "/api/v2/shop/auth_partner"
    ts = int(time.time())
    sign = assinar(partner_key, f"{partner_id}{path}{ts}")
    link = (f"{HOST}{path}?partner_id={partner_id}&timestamp={ts}"
            f"&sign={sign}&redirect={redirect}")

    Path("link_autorizacao_shopee.txt").write_text(link, encoding="utf-8")
    print("\nAbra este link no navegador, faca login e AUTORIZE a loja:\n")
    print(link + "\n")
    print("Depois o navegador cai na URL de redirect com ?code=...&shop_id=...")
    colado = perguntar("Cole aqui a URL inteira de retorno:\n> ")

    query = parse_qs(urlparse(colado).query)
    code = (query.get("code") or [""])[0]
    shop_id = (query.get("shop_id") or [""])[0]
    if not code or not shop_id:
        print("\n[ERRO] Nao encontrei 'code' e 'shop_id' na URL colada.")
        return

    # Troca o code pelo access_token + refresh_token.
    path = "/api/v2/auth/token/get"
    ts = int(time.time())
    sign = assinar(partner_key, f"{partner_id}{path}{ts}")
    resp = requests.post(
        f"{HOST}{path}",
        params={"partner_id": partner_id, "timestamp": ts, "sign": sign},
        json={"code": code, "partner_id": int(partner_id), "shop_id": int(shop_id)},
        timeout=30,
    )
    dados = resp.json()
    if resp.status_code != 200 or dados.get("error"):
        print("\n[ERRO] A Shopee recusou a troca do code:")
        print(dados or resp.text)
        return

    credenciais = {
        "partner_id": int(partner_id),
        "partner_key": partner_key,
        "shop_id": int(shop_id),
        "refresh_token": dados["refresh_token"],
        "access_token": dados.get("access_token", ""),
        "access_token_exp": time.time() + float(dados.get("expire_in", 14400)),
        "redirect_uri": redirect,
    }
    ARQUIVO.write_text(json.dumps(credenciais, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print(" PRONTO! Salvo em 'credenciais_shopee.json'")
    print(f" shop_id: {shop_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
