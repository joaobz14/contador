#!/usr/bin/env python3
"""Diagnostico SO-LEITURA: descobre se a API do Mercado Livre expoe dados de
COLETA / MOTORISTA (para avaliar a ideia de ligar o modo "Ambas" automatico
quando o mesmo motorista atende as duas contas).

- Nao altera NADA (so requisicoes GET).
- Imprime apenas a ESTRUTURA (nomes de chave + tipos), NUNCA os valores — assim
  nao vaza endereco, nome de motorista, placa nem qualquer dado pessoal/segredo.
- Usa o token da conta pela mesma via do app (obter_token).

Uso:
    python tools/diag_coleta.py [conta] [shipment_id]

    conta         nome da conta ML (default: a conta ativa). Ex.: cozilatti
    shipment_id   inspeciona um envio especifico (default: pega um da busca).
                  Dica: rode com um envio que tenha COLETA PROGRAMADA hoje.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import separador_etiquetas_ml as core  # noqa: E402

# chaves cujo NOME sugere coleta/motorista/rota (busca so no nome, nao no valor)
PALAVRAS = (
    "driver", "motorista", "pickup", "coleta", "route", "rota", "carrier",
    "plate", "placa", "authorization", "autoriza", "sender_real", "hub",
    "agency", "agencia", "chofer", "conductor",
)


def esqueleto(obj, prof=0, maxprof=6):
    """Estrutura recursiva com TIPOS no lugar dos valores (sem dado real)."""
    if isinstance(obj, dict):
        if prof >= maxprof:
            return "{...}"
        return {k: esqueleto(v, prof + 1, maxprof) for k, v in obj.items()}
    if isinstance(obj, list):
        return [esqueleto(obj[0], prof + 1, maxprof)] if obj else []
    return type(obj).__name__


def achar_chaves(obj, caminho=""):
    achados = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            cam = f"{caminho}.{k}" if caminho else k
            if any(p in str(k).lower() for p in PALAVRAS):
                achados.append(cam)
            achados += achar_chaves(v, cam)
    elif isinstance(obj, list) and obj:
        achados += achar_chaves(obj[0], caminho + "[]")
    return achados


def _get_seguro(path, token):
    """GET cru que devolve (status, keys_de_topo). Nao levanta; nao ecoa valor.
    As URLs do ML nao carregam token na query (Bearer no header), entao o path
    e seguro de imprimir."""
    import requests
    try:
        r = requests.get(core.API + path,
                         headers={"Authorization": f"Bearer {token}",
                                  "x-format-new": "true"},
                         timeout=core.TIMEOUT)
    except requests.RequestException as e:
        return "ERRO", type(e).__name__
    if r.status_code == 200:
        try:
            d = r.json()
        except ValueError:
            return 200, "(resposta nao-JSON)"
        return 200, (list(d.keys())[:15] if isinstance(d, dict)
                     else f"[lista de {len(d)}]")
    return r.status_code, ""


def main() -> int:
    conta = sys.argv[1] if len(sys.argv) > 1 else ""
    sid_arg = sys.argv[2] if len(sys.argv) > 2 else ""
    if conta:
        core.definir_conta(conta)
    print(f"conta ativa: {core.conta_ativa() or '(padrao)'}")

    cred = core.carregar_credenciais()
    token = core.obter_token(cred)
    seller = cred["seller_id"]

    if sid_arg:
        sid = int(sid_arg)
    else:
        pedidos = core.buscar_pedidos(token, seller)
        print(f"pedidos retornados: {len(pedidos)}")
        sid = next((s for p in pedidos
                    if (s := (p.get("shipping") or {}).get("id"))), None)
        if not sid:
            print("Nenhum envio para inspecionar. Passe um shipment_id manual.")
            return 1
    print(f"inspecionando shipment: {sid}\n")

    env = core.buscar_envio(token, sid)
    if not env:
        print("Nao consegui obter o shipment (vazio). Tente outro id.")
        return 1

    print("=== chaves candidatas em /shipments/{id} (coleta/motorista/rota) ===")
    cands = achar_chaves(env)
    print("  " + "\n  ".join(cands) if cands
          else "  (NENHUMA — o motorista/coleta provavelmente NAO esta no shipment)")

    print("\n=== estrutura de /shipments/{id} (so tipos, sem valores) ===")
    import json
    print(json.dumps(esqueleto(env), ensure_ascii=True, indent=2)[:6000])

    print("\n=== probe de endpoints candidatos de coleta (status + chaves) ===")
    print("  (404 = nao existe nesse caminho; nomes sao PALPITES a confirmar na doc)")
    candidatos = [
        f"/shipments/{sid}/carrier",
        f"/shipments/{sid}/history",
        f"/shipments/{sid}/lead_time",
        f"/shipments/{sid}/sla",
        f"/users/{seller}/shipments/pickup",
        f"/shipments/pickup/{sid}",
    ]
    for path in candidatos:
        status, keys = _get_seguro(path, token)
        print(f"  {status:>5} {path} -> {keys}")

    print("\nResumo: se aparecerem chaves candidatas acima OU algum endpoint 200 "
          "com chaves de coleta/motorista, da para ler o dado. Me mande ESTA saida "
          "(sao so nomes de chave/tipos — sem dado pessoal) que eu avalio o proximo passo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
