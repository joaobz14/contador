#!/usr/bin/env python3
"""Diagnostico SO-LEITURA do cronograma de coleta do Mercado Livre.

Confirma, na SUA conta, se a API entrega o MOTORISTA da coleta e permite
comparar duas contas — para avaliar a ideia de ligar o modo "Ambas" automatico
quando o mesmo motorista atende as duas contas.

Endpoint (doc "Envios Coletas e Places"):
    GET /users/{USER_ID}/shipping/schedule/{LOGISTIC_TYPE}
Retorna, por dia da semana, `detail[]` com: from/to/cutoff (janela),
carrier{id,name}, vehicle{license_plate,...}, driver{id,name}, sla, logistic_type.

- SO requisicoes GET; nao altera NADA.
- MASCARA o nome do motorista e a placa (dados pessoais). Imprime driver.id,
  carrier e a janela — que e o que interessa para casar as contas — entao a
  saida e SEGURA para colar aqui.

Uso:
    python tools/diag_coleta.py [conta]                    # cronograma de 1 conta (hoje)
    python tools/diag_coleta.py --comparar contaA contaB   # mesmo motorista hoje?
"""
from __future__ import annotations

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import separador_etiquetas_ml as core  # noqa: E402

DIAS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
# tipos logisticos que tem coleta com motorista (drop_off/correio nao tem)
LOGISTICAS = ["cross_docking", "xd_drop_off", "xd_same_day"]


def _hoje() -> str:
    return DIAS[datetime.datetime.now(core.TZ_BR).weekday()]


def _mask(v) -> str:
    """Mascara um dado pessoal (nome/placa) — mostra so o tamanho."""
    s = str(v or "")
    return f"***({len(s)} chars)" if s else "(vazio)"


def _token_seller(conta: str):
    if conta:
        core.definir_conta(conta)
    cred = core.carregar_credenciais()
    return core.obter_token(cred), cred["seller_id"]


def _logistica_do_envio(token, seller) -> str | None:
    """Le o logistic_type de um envio real (dica de qual logistica consultar)."""
    try:
        pedidos = core.buscar_pedidos(token, seller)
    except Exception:
        return None
    for p in pedidos:
        sid = (p.get("shipping") or {}).get("id")
        if not sid:
            continue
        env = core.buscar_envio(token, sid)
        lt = env.get("logistic_type") or (env.get("logistic") or {}).get("type")
        if lt:
            return lt
    return None


def _schedule(token, seller, logistica):
    """GET do cronograma. Devolve (status, json|None). Nao levanta; a URL do ML
    nao carrega token na query, entao o path e seguro."""
    import requests
    url = f"{core.API}/users/{seller}/shipping/schedule/{logistica}"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"},
                         timeout=core.TIMEOUT)
    except requests.RequestException as e:
        return "ERRO", type(e).__name__
    if r.status_code != 200:
        return r.status_code, None
    try:
        return 200, r.json()
    except ValueError:
        return 200, None


def _detalhes_hoje(sched: dict) -> list:
    dia = (sched.get("schedule") or {}).get(_hoje()) or {}
    return dia.get("detail") or []


def _driver_id_hoje(sched: dict):
    for d in _detalhes_hoje(sched):
        did = (d.get("driver") or {}).get("id")
        if did:
            return str(did)
    return None


def _porque_sem_driver(sched: dict | None) -> str:
    """Distingue as causas de `driver.id` ausente — cada uma pede acao diferente.

    Achado de 2026-07-30: o painel do ML mostrava o motorista (o MESMO nas duas
    contas, em dia com coleta programada), mas este endpoint devolveu 200 sem
    driver.id. Sem separar os casos abaixo nao da pra saber se o endpoint esta
    errado ou se o campo mudou de nome/lugar.
    """
    if sched is None:
        return "o endpoint nao respondeu 200 em nenhuma logistica"
    dia = (sched.get("schedule") or {}).get(_hoje())
    if dia is None:
        return f"o cronograma nao tem entrada para {_hoje()}"
    if dia.get("work") is False:
        return f"o cronograma marca {_hoje()} como dia SEM trabalho (work=false)"
    detalhes = dia.get("detail") or []
    if not detalhes:
        return (f"{_hoje()} existe no cronograma mas com detail[] VAZIO "
                "-> o cronograma semanal nao reflete a coleta real do dia "
                "(endpoint provavelmente errado para esta pergunta)")
    sem_chave = [i for i, d in enumerate(detalhes, 1) if "driver" not in d]
    if len(sem_chave) == len(detalhes):
        chaves = sorted({k for d in detalhes for k in d})
        return (f"detail[] tem {len(detalhes)} janela(s), mas NENHUMA traz a chave "
                f"'driver' -> o campo mudou de nome/lugar. Chaves presentes: "
                f"{', '.join(chaves)}")
    return (f"detail[] tem {len(detalhes)} janela(s) com a chave 'driver', mas "
            "sem 'id' dentro dela (driver vazio ou so com nome)")


def _coletar_conta(conta: str):
    """Devolve (seller, logistica_usada, status, sched) para o 1o logistic_type
    que responde 200 (tentando a do envio real primeiro)."""
    token, seller = _token_seller(conta)
    ordem = []
    lt_env = _logistica_do_envio(token, seller)
    if lt_env:
        ordem.append(lt_env)
    ordem += [x for x in LOGISTICAS if x not in ordem]
    ultimo = (ordem[0], None)
    for logistica in ordem:
        status, sched = _schedule(token, seller, logistica)
        if status == 200 and sched:
            return seller, logistica, status, sched
        ultimo = (logistica, status)
    return seller, ultimo[0], ultimo[1], None


def _mostrar_um(conta: str) -> int:
    # rotulo ANTES de trocar de conta: definir_conta() so troca os arquivos
    # (ARQUIVO_CRED etc.), nao o config.json — conta_ativa() apos o switch
    # continuaria devolvendo a conta antiga da GUI (rotulo errado, nao mistura
    # de dado: os arquivos usados abaixo sao os certos).
    rotulo = conta or core.conta_ativa() or "(padrao)"
    print(f"conta: {rotulo}  |  hoje = {_hoje()}\n")
    seller, logistica, status, sched = _coletar_conta(conta)
    print(f"seller_id: {seller}")
    print(f"logistic_type consultado: {logistica}  ->  HTTP {status}")
    if not sched:
        print("\nNao veio cronograma (status != 200 ou vazio). Possiveis causas: a "
              "conta nao e de coleta nessa logistica, ou o token nao tem permissao "
              "pra esse recurso. Tente outra logistica ou confira as permissoes.")
        return 1
    detalhes = _detalhes_hoje(sched)
    if not detalhes:
        print(f"\nHoje ({_hoje()}) sem coleta programada no cronograma "
              "(work=false ou detail vazio). Rode num dia com coleta.")
        return 0
    print(f"\n=== coleta de hoje ({_hoje()}) — {len(detalhes)} janela(s) ===")
    for i, d in enumerate(detalhes, 1):
        carrier = d.get("carrier") or {}
        vehicle = d.get("vehicle") or {}
        driver = d.get("driver") or {}
        print(f"  [{i}] janela {d.get('from')}-{d.get('to')} (corte {d.get('cutoff')})"
              f"  sla={d.get('sla')}  logistic_type={d.get('logistic_type')}")
        print(f"      carrier: id={carrier.get('id')} name={carrier.get('name')}")
        print(f"      driver : id={driver.get('id')}  name={_mask(driver.get('name'))}")
        print(f"      veiculo: placa={_mask(vehicle.get('license_plate'))} "
              f"tipo={vehicle.get('vehicle_type')} "
              f"so_hoje={vehicle.get('only_for_today')} "
              f"novo_motorista={vehicle.get('new_driver')}")
    print("\nO que importa pra casar as contas: driver.id e carrier.id (imprimidos "
          "acima). Nome e placa estao mascarados — a saida e segura pra colar aqui.")
    return 0


def _comparar(contaA: str, contaB: str) -> int:
    print(f"comparando coleta de HOJE ({_hoje()}) entre '{contaA}' e '{contaB}'\n")
    res = {}
    for conta in (contaA, contaB):
        seller, logistica, status, sched = _coletar_conta(conta)
        did = _driver_id_hoje(sched) if sched else None
        cid = None
        if sched:
            for d in _detalhes_hoje(sched):
                cid = (d.get("carrier") or {}).get("id") or cid
        res[conta] = {"seller": seller, "logistica": logistica, "status": status,
                      "driver_id": did, "carrier_id": cid, "sched": sched}
        print(f"  {conta}: seller={seller} logistica={logistica} HTTP={status} "
              f"driver.id={did} carrier.id={cid}")
        if not did:
            print(f"      por que: {_porque_sem_driver(sched)}")
    a, b = res[contaA], res[contaB]
    print()
    if not a["driver_id"] or not b["driver_id"]:
        print("Nao deu pra comparar: uma das contas nao trouxe driver.id hoje.")
        print("Veja o 'por que' de cada conta acima — a causa define o passo "
              "seguinte. Para o despejo cru (mascarado), rode:")
        print(f"    python tools/diag_coleta.py --cru {contaA}")
        return 1
    if a["driver_id"] == b["driver_id"]:
        print(f"MESMO MOTORISTA hoje (driver.id {a['driver_id']}) -> o modo 'Ambas' "
              "faria sentido automaticamente.")
    else:
        print(f"MOTORISTAS DIFERENTES ({a['driver_id']} != {b['driver_id']}) -> nao "
              "sugerir 'Ambas' hoje.")
    return 0


_CHAVES_PESSOAIS = ("name", "license_plate", "plate", "phone", "email",
                    "document", "address", "nickname")


def _mascarar_fundo(valor):
    """Mascara RECURSIVAMENTE qualquer dado pessoal no JSON, preservando a
    ESTRUTURA (que e o que interessa no diagnostico). Chave desconhecida entra
    como esta: sao dados de logistica, nao de pessoa — e se aparecer uma chave
    nova que carregue nome, ela vai entrar aqui na proxima rodada."""
    if isinstance(valor, dict):
        return {k: (_mask(v) if k in _CHAVES_PESSOAIS else _mascarar_fundo(v))
                for k, v in valor.items()}
    if isinstance(valor, list):
        return [_mascarar_fundo(v) for v in valor]
    return valor


def _despejo_cru(conta: str) -> int:
    """Imprime o cronograma CRU (mascarado) para ver a estrutura de verdade.

    Existe por causa do achado de 2026-07-30: o painel do ML mostrava o
    motorista e este endpoint devolveu 200 sem `driver.id`. Sem ver a resposta
    crua nao da pra saber se o campo mudou de nome, se mudou de lugar, ou se o
    cronograma semanal simplesmente nao e a fonte dessa informacao.
    """
    import json

    rotulo = conta or core.conta_ativa() or "(padrao)"
    seller, logistica, status, sched = _coletar_conta(conta)
    print(f"conta: {rotulo}  |  seller: {seller}  |  hoje = {_hoje()}")
    print(f"logistic_type: {logistica}  ->  HTTP {status}\n")
    if not sched:
        print("Sem cronograma para despejar.")
        return 1
    print(f"dias presentes em schedule: "
          f"{', '.join(sorted((sched.get('schedule') or {}).keys())) or '(nenhum)'}")
    print(f"veredito: {_porque_sem_driver(sched)}\n")
    print("=== resposta crua (nome/placa/telefone mascarados) ===")
    print(json.dumps(_mascarar_fundo(sched), indent=2, ensure_ascii=False)[:6000])
    print("\nA saida acima e SEGURA para colar: dado pessoal saiu como ***(n chars).")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--comparar":
        if len(args) < 3:
            print("uso: python tools/diag_coleta.py --comparar contaA contaB")
            return 2
        return _comparar(args[1], args[2])
    if args and args[0] == "--cru":
        return _despejo_cru(args[1] if len(args) > 1 else "")
    return _mostrar_um(args[0] if args else "")


if __name__ == "__main__":
    raise SystemExit(main())
