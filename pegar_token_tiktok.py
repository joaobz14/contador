"""
pegar_token_tiktok.py
Programa de UMA VEZ SO. Autoriza sua loja no TikTok Shop e salva tudo em
'dados/credenciais_tiktok.json'.

Pre-requisitos (em https://partner.tiktokshop.com, aba "Manage apps"):

  ATENCAO AO PORTAL. NAO e o developers.tiktok.com (TikTok for Developers) --
  aquele e o portal das APIs de conteudo/login, e as credenciais de la NAO
  servem aqui. Como saber que voce esta no errado: la a credencial se chama
  "Client key"/"Client secret" (aqui e App key/App secret), os produtos sao
  Login Kit / Display API / Content Posting API, e nao existe "Service ID".
  Nao ha conversao: e outro cadastro, do zero. Ja custou tempo 3x -- ver
  "A armadilha dos portais parecidos" em docs/TIKTOK_SHOP_API.md.

  - App Key e App Secret do app;
  - SERVICE ID do app -- e ele, NAO o app_key, que vai no link de autorizacao.
    Fica na pagina do app, perto do App Key (as vezes rotulado "Service ID" ou
    dentro de "Basic information"). Sem ele nao ha como autorizar a loja: o
    TikTok Shop NAO tem botao "autorizar" na pagina do app, o link e montado
    por voce.

Como usar:
  1) pip install requests
  2) python pegar_token_tiktok.py
  3) siga as instrucoes: abra o link, autorize a loja, e cole a URL de retorno.

ATENCAO: o 'auth_code' expira em MINUTOS (igual ML/Shopee). Deixe este script
aberto ANTES de clicar em autorizar.
"""

import traceback
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

# Hosts confirmados no codigo dos SDKs oficiais-de-terceiros (ver
# docs/TIKTOK_SHOP_API.md, secao "Forca da evidencia"). O dominio ".us" so vale
# para os EUA; o Brasil usa o global.
HOST_AUTH = "https://auth.tiktok-shops.com"
HOST_API = "https://open-api.tiktokglobalshop.com"
PAGINA_AUTORIZAR = "https://services.tiktokshop.com/open/authorize"

PASTA_SCRIPT = Path(__file__).resolve().parent
ARQUIVO = PASTA_SCRIPT / "dados" / "credenciais_tiktok.json"


def perguntar(rotulo: str) -> str:
    valor = ""
    while not valor.strip():
        valor = input(rotulo).strip()
    return valor


def extrair_code(colado: str) -> str:
    """Aceita a URL inteira de retorno OU so o code.

    O TikTok devolve o parametro como `code`; algumas telas mostram `auth_code`.
    Aceita os dois para o operador nao ter que adivinhar qual copiar.
    """
    q = parse_qs(urlparse(colado).query)
    for chave in ("code", "auth_code"):
        valor = (q.get(chave) or [""])[0].strip()
        if valor:
            return valor
    return "" if "=" in colado else colado.strip()


def main() -> None:
    print("=" * 62)
    print(" AUTORIZACAO DA LOJA NO TIKTOK SHOP")
    print("=" * 62)

    app_key = perguntar("\n1) App Key:\n> ")
    app_secret = perguntar("\n2) App Secret:\n> ")
    service_id = perguntar(
        "\n3) SERVICE ID do app (NAO e o App Key -- veja o cabecalho deste\n"
        "   arquivo se nao souber onde achar):\n> ")

    link = f"{PAGINA_AUTORIZAR}?service_id={service_id}"
    # Em dados/, nao na raiz (convencao "onde os arquivos ficam"). De quebra, o
    # .gitignore ignora dados/* inteiro -- o link nao escapa por esquecimento.
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    (ARQUIVO.parent / "link_autorizacao_tiktok.txt").write_text(link, encoding="utf-8")

    print("\n" + "=" * 62)
    print(" PASSO IMPORTANTE")
    print("=" * 62)
    print("\nAbra este link no navegador, LOGADO como vendedor, e autorize:\n")
    print(link + "\n")
    print("(o link tambem foi salvo em 'dados/link_autorizacao_tiktok.txt')")
    print("\nDepois de autorizar, o navegador vai para a URL de retorno que voce")
    print("cadastrou no app, com o code na barra de endereco. Copie a URL INTEIRA.")
    print("\nSe a pagina de retorno der erro de conexao, TUDO BEM -- o code esta")
    print("na barra de endereco do mesmo jeito; e so copiar de la.\n")

    colado = perguntar("Cole a URL de retorno (ou so o code) e Enter:\n> ")
    code = extrair_code(colado)
    if not code:
        print("\n[ERRO] Nao identifiquei o 'code' no que voce colou.")
        return

    # Troca o code por access_token + refresh_token.
    resp = requests.get(
        f"{HOST_AUTH}/api/v2/token/get",
        params={"app_key": app_key, "app_secret": app_secret,
                "auth_code": code, "grant_type": "authorized_code"},
        timeout=30,
    )
    dados = resp.json() if resp.content else {}
    if resp.status_code != 200 or dados.get("code") not in (0, None):
        print("\n[ERRO] O TikTok recusou a troca do code:")
        print(dados or resp.text)
        print("\nCausa comum: o code expira em minutos. Rode de novo e faca rapido.")
        return

    d = dados.get("data") or dados
    access_token = d.get("access_token", "")
    if not access_token:
        print("\n[ERRO] A resposta nao trouxe access_token:")
        print(dados)
        return

    # O shop_cipher NAO vem na troca do token: sai de uma chamada separada, ja
    # autenticada. Ele identifica a loja em quase toda chamada seguinte, entao
    # sem ele as credenciais ficam incompletas.
    cipher, shop_id, shop_nome = "", "", ""
    try:
        r2 = requests.get(
            f"{HOST_API}/authorization/202309/shops",
            params={"app_key": app_key},
            headers={"x-tts-access-token": access_token,
                     "content-type": "application/json"},
            timeout=30,
        )
        lojas = ((r2.json().get("data") or {}).get("shops") or [])
        if lojas:
            cipher = lojas[0].get("cipher", "")
            shop_id = str(lojas[0].get("id", ""))
            shop_nome = lojas[0].get("name", "")
        if len(lojas) > 1:
            print(f"\n[AVISO] O app tem {len(lojas)} lojas autorizadas; usei a 1a")
            print(f"        ({shop_nome}). Ajuste 'shop_cipher' na mao se errado.")
    except Exception as e:                      # noqa: BLE001 - best-effort
        print(f"\n[AVISO] Nao consegui buscar o shop_cipher agora ({type(e).__name__}).")
        print("        O token FOI salvo; rode de novo so se precisar do cipher.")

    credenciais = {
        "app_key": app_key,
        "app_secret": app_secret,
        "service_id": service_id,
        "shop_cipher": cipher,
        "shop_id": shop_id,
        "shop_nome": shop_nome,
        "access_token": access_token,
        "refresh_token": d.get("refresh_token", ""),
        # A resposta traz o instante ABSOLUTO de expiracao (epoch), nao a
        # duracao -- diferente da Shopee, que manda 'expire_in' relativo.
        "access_token_exp": float(d.get("access_token_expire_in", 0))
        or time.time() + 7 * 24 * 3600,
        "refresh_token_exp": float(d.get("refresh_token_expire_in", 0)),
    }

    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    # Grava pelo nucleo: atomico + fsync + espelho .bak (sobrevive a queda de
    # energia ja no primeiro salvamento), igual ML e Shopee.
    import separador_etiquetas_ml as core
    core._gravar_credenciais_com_backup(ARQUIVO, credenciais)

    print("\n" + "=" * 62)
    print(" PRONTO! Salvo em 'dados/credenciais_tiktok.json'")
    if shop_nome:
        print(f" Loja: {shop_nome} (id {shop_id})")
    print(f" shop_cipher: {'OK' if cipher else 'FALTANDO -- ver aviso acima'}")
    print("=" * 62)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\n[ERRO INESPERADO] Detalhes abaixo:")
        traceback.print_exc()
    input("\nPressione Enter para fechar...")
