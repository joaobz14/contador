"""
pegar_token_shopee.py
Programa de UMA VEZ SO. Autoriza sua loja na Shopee Open Platform e salva tudo
em 'credenciais_shopee.json'.

Pre-requisitos (em https://open.shopee.com, app ja "Live"):
  - App ID (partner_id) e Partner Key (partner_secret) de PRODUCAO;
  - Redirect URL cadastrada no app. Use a pagina deste projeto no GitHub Pages:
    https://joaobz14.github.io/contador/

Como usar:
  1) pip install requests
  2) python pegar_token_shopee.py   (ou duplo-clique no Pegar Token Shopee.bat)
  3) siga as instrucoes: abra o link, autorize, e cole o code e o shop_id que a
     pagina de retorno mostra.
"""

import hashlib
import hmac
import time
import traceback
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

HOST = "https://partner.shopeemobile.com"   # host global; validado com a loja real (BR)
PASTA_SCRIPT = Path(__file__).resolve().parent
ARQUIVO = PASTA_SCRIPT / "credenciais_shopee.json"
REDIRECT_PADRAO = "https://joaobz14.github.io/contador/"


def perguntar(rotulo: str) -> str:
    valor = ""
    while not valor.strip():
        valor = input(rotulo).strip()
    return valor


def assinar(partner_key: str, base: str) -> str:
    return hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()


def extrair(colado: str) -> tuple[str, str]:
    """Aceita a URL inteira de retorno OU so o code. Devolve (code, shop_id)."""
    q = parse_qs(urlparse(colado).query)
    code = (q.get("code") or [""])[0].strip()
    shop_id = (q.get("shop_id") or [""])[0].strip()
    if not code and "code=" not in colado:
        code = colado.strip()          # usuario colou so o code
    return code, shop_id


def main() -> None:
    print("=" * 60)
    print(" AUTORIZACAO DA LOJA NA SHOPEE")
    print("=" * 60)

    partner_id = perguntar("\n1) App ID (partner_id) de PRODUCAO:\n> ")
    partner_key = perguntar("\n2) Partner Key (partner_secret) de PRODUCAO:\n> ")
    redirect = input(
        f"\n3) Redirect URL cadastrada no app (Enter = {REDIRECT_PADRAO}):\n> "
    ).strip() or REDIRECT_PADRAO

    # Monta o link de autorizacao (assinatura publica: partner_id + path + timestamp).
    path = "/api/v2/shop/auth_partner"
    ts = int(time.time())
    sign = assinar(partner_key, f"{partner_id}{path}{ts}")
    link = (f"{HOST}{path}?partner_id={partner_id}&timestamp={ts}"
            f"&sign={sign}&redirect={redirect}")

    (PASTA_SCRIPT / "link_autorizacao_shopee.txt").write_text(link, encoding="utf-8")
    print("\n" + "=" * 60)
    print(" PASSO IMPORTANTE")
    print("=" * 60)
    print("\nAbra este link no navegador, faca login e AUTORIZE a loja:\n")
    print(link + "\n")
    print("(o link tambem foi salvo em 'link_autorizacao_shopee.txt')")
    print(f"\nDepois o navegador cai na pagina de retorno ({redirect}),")
    print("que mostra o 'code' e o 'shop_id'. Copie os dois.\n")

    colado = perguntar("Cole a URL de retorno (ou so o code) e Enter:\n> ")
    code, shop_id = extrair(colado)
    if not shop_id:
        shop_id = perguntar("shop_id (numero da loja, mostrado na pagina):\n> ")
    if not code:
        print("\n[ERRO] Nao identifiquei o 'code'. Rode de novo e cole o code certo.")
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
        print("\nCausa comum: o code expira em minutos. Rode de novo e faca rapido.")
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
    # Grava pelo nucleo: atomico + fsync + espelho .bak (sobrevive a queda de
    # energia ja no primeiro salvamento).
    import separador_etiquetas_ml as core
    core._gravar_credenciais_com_backup(ARQUIVO, credenciais)

    print("\n" + "=" * 60)
    print(" PRONTO! Salvo em 'credenciais_shopee.json'")
    print(f" shop_id: {shop_id}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\n[ERRO INESPERADO] Detalhes abaixo:")
        traceback.print_exc()
    input("\nPressione Enter para fechar...")
