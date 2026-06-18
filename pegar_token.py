"""
pegar_token.py
Programa de UMA VEZ SO. Pega a autorizacao do Mercado Livre e salva tudo
no arquivo 'credenciais.json'. Depois disso voce nao precisa mais dele.

Como usar:
  1) pip install requests   (se ainda nao tiver)
  2) python pegar_token.py
  3) siga as instrucoes na tela
"""

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
ARQUIVO = Path("credenciais.json")


def perguntar(rotulo: str) -> str:
    valor = ""
    while not valor.strip():
        valor = input(rotulo).strip()
    return valor


def extrair_code(texto: str) -> str:
    """Aceita a URL inteira colada OU so o codigo."""
    if "code=" in texto:
        query = urlparse(texto).query
        codigos = parse_qs(query).get("code")
        if codigos:
            return codigos[0]
    return texto.strip()


def main() -> None:
    print("=" * 60)
    print(" CONFIGURACAO DAS CREDENCIAIS DO MERCADO LIVRE")
    print("=" * 60)

    client_id = perguntar("\n1) Cole aqui o App ID (Client ID) e Enter:\n> ")
    client_secret = perguntar("\n2) Cole aqui o Client Secret e Enter:\n> ")

    redirect = input(
        "\n3) Qual 'URI de redirect' voce cadastrou no app?\n"
        "   (Enter para usar https://www.google.com)\n> "
    ).strip() or "https://www.google.com"

    # Monta a pagina de autorizacao
    link = (
        f"{AUTH_URL}?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect}"
        f"&scope=offline_access+read+write"
    )

    print("\n" + "=" * 60)
    print(" PASSO IMPORTANTE - faca RAPIDO (o codigo expira em minutos)")
    print("=" * 60)
    Path("link_autorizacao.txt").write_text(link, encoding="utf-8")
    print("\nO link foi salvo no arquivo 'link_autorizacao.txt' (mesma pasta).")
    print("Abra com o Bloco de Notas, copie tudo e cole no Brave.")
    print("Ou, se preferir, copie o link abaixo direto:\n")
    print(link + "\n")
    print("Na pagina do Mercado Livre, clique em AUTORIZAR.")
    print("Depois o navegador vai cair numa pagina (ex: google.com).")
    print("COPIE a barra de enderecos INTEIRA dessa pagina.\n")

    colado = perguntar(
        "Cole aqui a barra de enderecos (ou so o codigo) e Enter:\n> "
    )
    code = extrair_code(colado)

    print("\nTrocando o codigo pela autorizacao definitiva...")
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect,
        },
        headers={"Accept": "application/json"},
        timeout=30,
    )

    if resp.status_code != 200:
        print("\n[ERRO] O Mercado Livre recusou. Resposta:")
        print(resp.text)
        print(
            "\nCausa mais comum: o codigo expirou ou ja foi usado.\n"
            "Solucao: rode o programa de novo e faca o passo do navegador rapido."
        )
        return

    dados = resp.json()
    if not dados.get("refresh_token"):
        print("\n[ERRO] O Mercado Livre nao devolveu a 'chave permanente'.")
        print("Causa: o app esta sem a permissao 'offline_access'.")
        print("\nResolva assim:")
        print("  1) DevCenter > sua aplicacao > Editar")
        print("  2) Marque o escopo 'offline_access' (e read e write)")
        print("  3) Salve e rode este programa de novo")
        return
    credenciais = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": dados["refresh_token"],
        "seller_id": str(dados["user_id"]),
        "redirect_uri": redirect,
    }
    ARQUIVO.write_text(
        json.dumps(credenciais, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print(" PRONTO! Tudo salvo em 'credenciais.json'")
    print("=" * 60)
    print(f" Seu numero de vendedor (seller_id): {credenciais['seller_id']}")
    print(" Pode fechar. Nao precisa mais rodar este programa.")


if __name__ == "__main__":
    main()
