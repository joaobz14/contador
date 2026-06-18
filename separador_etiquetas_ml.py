"""
separador_etiquetas_ml.py
Le os pedidos do Mercado Livre, filtra os que estao em "Etiquetas para imprimir"
(status ready_to_ship + substatus ready_to_print) e agrupa por
(PRODUTO + quantidade do pedido).

Identidade do produto: SKU > GTIN+voltagem > item_id:variacao.

Antes de usar: rode o pegar_token.py uma vez (gera credenciais.json).
Requisitos: pip install requests

Comandos:
  python separador_etiquetas_ml.py            -> lista grupos prontos para imprimir
  python separador_etiquetas_ml.py envios     -> mostra datas de despacho (hoje vs futuro)
  python separador_etiquetas_ml.py detalhar "<nome>" <QTD>
  python separador_etiquetas_ml.py imprimir "<nome>" <QTD>
  python separador_etiquetas_ml.py proximo
"""

from __future__ import annotations

import io
import json
import sys
import time
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import requests

API = "https://api.mercadolibre.com"
TIMEOUT = 30
MAX_PEDIDOS = 3000
DIAS_JANELA = 30
TAM_NOME = 45
SUBSTATUS_IMPRIMIR = "ready_to_print"
# Pasta deste script: os arquivos de credenciais/estado/cache ficam sempre
# aqui, independente de onde o programa for aberto (atalho, agendador, etc.).
PASTA_SCRIPT = Path(__file__).resolve().parent
ARQUIVO_CRED = PASTA_SCRIPT / "credenciais.json"
ARQUIVO_ESTADO = PASTA_SCRIPT / "estado_grupos.json"
ARQUIVO_CACHE = PASTA_SCRIPT / "itens_cache.json"
# Pasta que o app da Zebra (impressora_zebra_usb.py) vigia. AJUSTE aqui se o seu
# app estiver monitorando outra pasta (veja "Monitorando: ..." na tela dele).
PASTA_DOWNLOADS = Path.home() / "Downloads"


# ---------------------------------------------------------------------------
# ERROS
# ---------------------------------------------------------------------------
class SeparadorError(RuntimeError):
    """Erro de negocio do separador (credenciais, token, etc.).

    O nucleo lanca esta excecao em vez de encerrar o processo, para que a
    camada que chama (CLI ou GUI) decida como mostrar a mensagem.
    """


# ---------------------------------------------------------------------------
# CREDENCIAIS
# ---------------------------------------------------------------------------
def carregar_credenciais() -> dict:
    if not ARQUIVO_CRED.exists():
        raise SeparadorError(
            "credenciais.json nao encontrado. Rode pegar_token.py primeiro."
        )
    return json.loads(ARQUIVO_CRED.read_text(encoding="utf-8"))


def salvar_credenciais(cred: dict) -> None:
    ARQUIVO_CRED.write_text(json.dumps(cred, ensure_ascii=False, indent=2), encoding="utf-8")


def renovar_token(cred: dict) -> str:
    resp = requests.post(
        f"{API}/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": cred["client_id"],
            "client_secret": cred["client_secret"],
            "refresh_token": cred["refresh_token"],
        },
        headers={"Accept": "application/json"},
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        raise SeparadorError(f"Falha ao renovar token: {resp.text}")
    dados = resp.json()
    novo = dados.get("refresh_token")
    if novo and novo != cred["refresh_token"]:
        cred["refresh_token"] = novo
        salvar_credenciais(cred)
    return dados["access_token"]


def _requisicao_get(
    url: str, headers: dict, params: dict | None = None
) -> requests.Response:
    """GET com retry/backoff exponencial em erros transitorios (429/500/502/503).

    Retorna a Response da ultima tentativa; quem chama decide o que fazer com
    o status. Usado tanto pelas chamadas que esperam JSON quanto pelo download
    binario das etiquetas.
    """
    resp = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    for tentativa in range(1, 3):
        if resp.status_code not in (429, 500, 502, 503):
            return resp
        time.sleep(2 ** tentativa)
        resp = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    return resp


def _get(url: str, token: str, params: dict | None = None, extra: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if extra:
        headers.update(extra)
    resp = _requisicao_get(url, headers, params)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# MODELO
# ---------------------------------------------------------------------------
@dataclass
class ItemPedido:
    order_id: int
    shipment_id: int | None
    chave: str
    nome: str
    quantidade: int
    item_id: str = ""
    titulo: str = ""
    voltagem: str = ""


@dataclass
class Grupo:
    chave: str
    nome: str
    quantidade: int
    shipment_ids: list[int] = field(default_factory=list)

    @property
    def chave_grupo(self) -> str:
        return f"{self.chave}|q{self.quantidade}"

    @property
    def total_etiquetas(self) -> int:
        return len(self.shipment_ids)


# ---------------------------------------------------------------------------
# CACHE DE PRODUTOS (item_id -> {title, variations:{variation_id: gtin}})
# ---------------------------------------------------------------------------
def carregar_cache() -> dict:
    if ARQUIVO_CACHE.exists():
        return json.loads(ARQUIVO_CACHE.read_text(encoding="utf-8"))
    return {}


def salvar_cache(cache: dict) -> None:
    ARQUIVO_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def buscar_detalhes(token: str, item_ids: set[str], cache: dict) -> None:
    faltando = [i for i in item_ids if i not in cache]
    if not faltando:
        return
    print(f"Buscando detalhes de {len(faltando)} produtos novos...")
    for n, item_id in enumerate(faltando, 1):
        print(f"  {n}/{len(faltando)}", end="\r")
        try:
            det = _get(f"{API}/items/{item_id}", token, params={"include_attributes": "all"})
        except requests.HTTPError:
            cache[item_id] = {"title": "", "variations": {}}
            continue
        variacoes: dict[str, str] = {}
        for v in det.get("variations", []):
            gtin = ""
            for a in v.get("attributes", []):
                if a.get("id") == "GTIN":
                    gtin = a.get("value_name") or ""
            variacoes[str(v.get("id"))] = gtin
        cache[item_id] = {"title": det.get("title", ""), "variations": variacoes}
    print()
    salvar_cache(cache)


# ---------------------------------------------------------------------------
# IDENTIDADE DO PRODUTO
# ---------------------------------------------------------------------------
def _voltagem(item: dict) -> str:
    for attr in item.get("variation_attributes") or []:
        if attr.get("id") == "VOLTAGE":
            return attr.get("value_name") or ""
    return ""


def identidade(item: dict, cache: dict) -> tuple[str, str]:
    sku = item.get("seller_sku") or item.get("seller_custom_field")
    if sku:
        sku = str(sku).strip()
        return sku, sku

    item_id = item.get("id") or "?"
    var_id = str(item.get("variation_id") or "0")
    volt = _voltagem(item)
    info = cache.get(item_id, {})
    gtin = (info.get("variations") or {}).get(var_id, "")
    titulo = (item.get("title") or info.get("title") or "Produto").strip()[:TAM_NOME]
    nome = f"{titulo} ({volt})" if volt else titulo

    if gtin:
        sufixo = f"|{volt}" if volt else ""
        return f"GTIN:{gtin}{sufixo}", nome
    return f"{item_id}:{var_id}", nome


# ---------------------------------------------------------------------------
# BUSCA DE PEDIDOS E ENVIOS
# ---------------------------------------------------------------------------
def buscar_pedidos(token: str, seller_id: str) -> list[dict]:
    desde = (datetime.now() - timedelta(days=DIAS_JANELA)).strftime("%Y-%m-%dT00:00:00.000-03:00")
    pedidos: list[dict] = []
    offset = 0
    while offset < MAX_PEDIDOS:
        dados = _get(
            f"{API}/orders/search",
            token,
            params={
                "seller": seller_id,
                "order.status": "paid",
                "order.date_created.from": desde,
                "sort": "date_desc",
                "offset": offset,
                "limit": 50,
            },
        )
        resultados = dados.get("results", [])
        pedidos.extend(resultados)
        total = dados.get("paging", {}).get("total", 0)
        offset += 50
        if offset >= total or not resultados:
            break
    return pedidos


def buscar_pedidos_amplo(token: str, seller_id: str, limite: int = 1000) -> list[dict]:
    """Busca pedidos SEM filtro de status (para diagnostico)."""
    pedidos: list[dict] = []
    offset = 0
    while offset < limite:
        dados = _get(
            f"{API}/orders/search",
            token,
            params={"seller": seller_id, "sort": "date_desc", "offset": offset, "limit": 50},
        )
        resultados = dados.get("results", [])
        pedidos.extend(resultados)
        total = dados.get("paging", {}).get("total", 0)
        offset += 50
        if offset >= total or not resultados:
            break
    return pedidos


def rastrear_sku(token: str, seller_id: str, sku: str) -> None:
    """Mostra todos os pedidos de um SKU e por que cada um entra (ou nao) em 'hoje'."""
    alvo = sku.lower()
    hoje = datetime.now().date().isoformat()
    print(f"Buscando todos os pedidos do SKU {sku}...")
    pedidos = buscar_pedidos_amplo(token, seller_id)
    achados = []
    for ped in pedidos:
        for oi in ped.get("order_items", []):
            item = oi.get("item", {})
            s = item.get("seller_sku") or item.get("seller_custom_field") or ""
            if str(s).strip().lower() == alvo:
                achados.append((ped, int(oi.get("quantity", 1))))
    print(f"\nPedidos encontrados com SKU {sku}: {len(achados)}\n")
    for ped, qtd in achados:
        sid = (ped.get("shipping") or {}).get("id")
        status = ped.get("status")
        env = buscar_envio(token, sid) if sid else {}
        sub = env.get("substatus")
        sla = _sla(token, sid) if sid else {}
        exp = (sla.get("expected_date") or "")[:10]
        entra = status == "paid" and sub == SUBSTATUS_IMPRIMIR and exp == hoje
        marca = "ENTRA HOJE" if entra else "fora"
        print(f"  pedido {ped.get('id')} | qtd {qtd} | status {status} | "
              f"envio {sub} | despacho {exp} | -> {marca}")


def buscar_envio(token: str, shipment_id: int) -> dict:
    try:
        return _get(f"{API}/shipments/{shipment_id}", token, extra={"x-format-new": "true"})
    except requests.HTTPError:
        return {}


def _avaliar_pedido(token: str, ped: dict) -> dict | None:
    """Retorna o pedido com _envio se estiver ready_to_print; senao None."""
    sid = (ped.get("shipping") or {}).get("id")
    if not sid:
        return None
    env = buscar_envio(token, sid)
    if env.get("substatus") != SUBSTATUS_IMPRIMIR:
        return None
    sla = _sla(token, sid)
    expected = (sla.get("expected_date") or "")[:10]
    logt = env.get("logistic_type") or (env.get("logistic") or {}).get("type", "")
    ped["_envio"] = {"shipment_id": sid, "expected_date": expected, "logistica": logt}
    return ped


def filtrar_para_imprimir(token: str, pedidos: list[dict], progresso=None) -> list[dict]:
    """Mantem pedidos em ready_to_print. progresso(feitos, total) e chamado por pedido."""
    total = len(pedidos)
    prontos: list[dict] = []
    feitos = 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        for resultado in ex.map(lambda p: _avaliar_pedido(token, p), pedidos):
            feitos += 1
            if progresso:
                progresso(feitos, total)
            else:
                print(f"  Verificando envios: {feitos}/{total}", end="\r")
            if resultado is not None:
                prontos.append(resultado)
    if not progresso:
        print()
    return prontos


def extrair_itens(token: str, pedidos: list[dict]) -> list[ItemPedido]:
    precisa: set[str] = set()
    for ped in pedidos:
        for oi in ped.get("order_items", []):
            item = oi.get("item", {})
            if not (item.get("seller_sku") or item.get("seller_custom_field")) and item.get("id"):
                precisa.add(item["id"])
    cache = carregar_cache()
    buscar_detalhes(token, precisa, cache)

    itens: list[ItemPedido] = []
    for ped in pedidos:
        sid = (ped.get("_envio") or {}).get("shipment_id") or (ped.get("shipping") or {}).get("id")
        for oi in ped.get("order_items", []):
            item = oi.get("item", {})
            chave, nome = identidade(item, cache)
            itens.append(
                ItemPedido(
                    order_id=ped.get("id"),
                    shipment_id=sid,
                    chave=chave,
                    nome=nome,
                    quantidade=int(oi.get("quantity", 1)),
                    item_id=item.get("id") or "",
                    titulo=(item.get("title") or "").strip(),
                    voltagem=_voltagem(item),
                )
            )
    return itens


def agrupar(itens: list[ItemPedido]) -> list[Grupo]:
    """REGRA PRINCIPAL: agrupa por identidade do produto + quantidade do pedido."""
    grupos: dict[tuple[str, int], Grupo] = {}
    for it in itens:
        ch = (it.chave, it.quantidade)
        g = grupos.get(ch)
        if g is None:
            g = Grupo(chave=it.chave, nome=it.nome, quantidade=it.quantidade)
            grupos[ch] = g
        if it.shipment_id and it.shipment_id not in g.shipment_ids:
            g.shipment_ids.append(it.shipment_id)
    return sorted(grupos.values(), key=lambda g: (g.quantidade, g.nome.lower()))


# ---------------------------------------------------------------------------
# PIPELINE (reutilizado pela CLI e pela GUI)
# ---------------------------------------------------------------------------
@dataclass
class Coleta:
    """Resultado do pipeline completo de uma atualizacao."""
    prontos: list[dict]               # todos os envios ready_to_print
    alvo: list[dict]                  # subconjunto considerado (hoje ou todos)
    itens: list[ItemPedido]
    grupos: list[Grupo]


def coletar_grupos(
    token: str, seller_id: str, *, somente_hoje: bool = True, progresso=None
) -> Coleta:
    """Busca pedidos, filtra os prontos para imprimir, seleciona pelo dia,
    extrai os itens e agrupa. Centraliza o fluxo usado pela CLI e pela GUI
    para que as duas nao divirjam. progresso(feitos, total) e repassado ao
    filtro de envios.
    """
    pedidos = buscar_pedidos(token, seller_id)
    prontos = filtrar_para_imprimir(token, pedidos, progresso=progresso)
    if somente_hoje:
        hoje = datetime.now().date().isoformat()
        alvo = [p for p in prontos if p["_envio"]["expected_date"] == hoje]
    else:
        alvo = prontos
    itens = extrair_itens(token, alvo)
    grupos = agrupar(itens)
    return Coleta(prontos=prontos, alvo=alvo, itens=itens, grupos=grupos)


# ---------------------------------------------------------------------------
# DIAGNOSTICO DE DATAS (hoje vs proximos dias)
# ---------------------------------------------------------------------------
def _sla(token: str, shipment_id: int) -> dict:
    try:
        return _get(f"{API}/shipments/{shipment_id}/sla", token)
    except requests.HTTPError:
        return {}


def debug_envios(pedidos_prontos: list[dict], hoje: str) -> None:
    """Lista os envios prontos com a data de despacho, marcando os de hoje."""
    print(f"\n--- ENVIOS PRONTOS PARA IMPRIMIR (hoje = {hoje}) ---\n")
    cont_hoje = 0
    for ped in pedidos_prontos:
        e = ped["_envio"]
        eh_hoje = e["expected_date"] == hoje
        cont_hoje += 1 if eh_hoje else 0
        marca = " <== HOJE" if eh_hoje else ""
        print(f"  ship {e['shipment_id']} | {e['logistica']} | despacho {e['expected_date']}{marca}")
    print(f"\nTotal prontos: {len(pedidos_prontos)} | de hoje: {cont_hoje}")


# ---------------------------------------------------------------------------
# ETIQUETAS ZPL
# ---------------------------------------------------------------------------
def _zpl_de_zip(conteudo: bytes) -> str:
    """Extrai e concatena o ZPL de dentro de um ZIP retornado pela API."""
    partes: list[str] = []
    with zipfile.ZipFile(io.BytesIO(conteudo)) as zf:
        for nome in zf.namelist():
            partes.append(zf.read(nome).decode("utf-8", errors="ignore"))
    return "\n".join(partes)


def baixar_zpl(token: str, shipment_ids: list[int]) -> str:
    """Baixa as etiquetas ZPL via /shipment_labels (ate 50 envios por chamada).

    Se QUALQUER lote falhar (apos os retries de _requisicao_get), aborta com
    SeparadorError em vez de devolver um ZPL incompleto. Assim quem chama nao
    gera um ZIP parcial nem marca o grupo como impresso por engano.
    """
    headers = {"Authorization": f"Bearer {token}"}
    partes: list[str] = []
    for i in range(0, len(shipment_ids), 50):
        lote = shipment_ids[i:i + 50]
        ids = ",".join(str(s) for s in lote)
        resp = _requisicao_get(
            f"{API}/shipment_labels",
            headers,
            {"shipment_ids": ids, "response_type": "zpl2"},
        )
        if resp.status_code != 200:
            raise SeparadorError(
                f"Falha ao baixar etiquetas (HTTP {resp.status_code}) para os "
                f"envios {ids}. Nada foi impresso; o grupo segue pendente."
            )
        conteudo = resp.content
        if conteudo[:2] == b"PK":          # resposta e um ZIP
            partes.append(_zpl_de_zip(conteudo))
        else:                               # resposta e ZPL em texto
            partes.append(conteudo.decode("utf-8", errors="ignore"))
    return "\n".join(partes)


def gerar_zip_etiquetas(grupo: Grupo, zpl_texto: str) -> Path:
    """
    Monta um ZIP no formato que o impressora_zebra_usb.py reconhece:
      - nome do ZIP comeca com um prefixo aceito ("etiqueta de envio")
      - dentro, um TXT cujo nome contem "etiqueta de envio" (identifica ML)
    Grava de forma atomica (.tmp -> rename) para o monitor so ver o arquivo pronto.
    """
    PASTA_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    base = "".join(c if c.isalnum() else "_" for c in grupo.nome)[:30].strip("_")
    nome_zip = PASTA_DOWNLOADS / f"etiqueta de envio - {base} - q{grupo.quantidade}.zip"
    tmp = nome_zip.with_name(nome_zip.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"Etiqueta de envio - {base}.txt", zpl_texto)
    tmp.replace(nome_zip)
    return nome_zip


# ---------------------------------------------------------------------------
# ESTADO
# ---------------------------------------------------------------------------
def carregar_estado() -> dict:
    if ARQUIVO_ESTADO.exists():
        return json.loads(ARQUIVO_ESTADO.read_text(encoding="utf-8"))
    return {}


def salvar_estado(estado: dict) -> None:
    ARQUIVO_ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def _chave_estado(grupo: Grupo) -> str:
    return f"{datetime.now().date().isoformat()}|{grupo.chave_grupo}"


def status_grupo(estado: dict, grupo: Grupo) -> str:
    return estado.get(_chave_estado(grupo), "pendente")


def marcar_impresso(estado: dict, grupo: Grupo) -> None:
    estado[_chave_estado(grupo)] = "impresso"
    salvar_estado(estado)


# ---------------------------------------------------------------------------
# SAIDA
# ---------------------------------------------------------------------------
def listar(grupos: list[Grupo], estado: dict, qtd_prontos: int) -> None:
    print(f"\nPedidos prontos para imprimir: {qtd_prontos}")
    if not grupos:
        print("Nenhum grupo para imprimir.")
        return
    por_qtd: dict[int, list[Grupo]] = defaultdict(list)
    for g in grupos:
        por_qtd[g.quantidade].append(g)
    total = 0
    for qtd in sorted(por_qtd):
        print(f"\n=== Quantidade por pedido = {qtd} ===")
        for g in por_qtd[qtd]:
            st = status_grupo(estado, g).upper()
            total += g.total_etiquetas
            print(f"  {g.total_etiquetas:>3} et.  {g.nome:<{TAM_NOME}}  [{st}]")
    print(f"\nTotal de grupos: {len(grupos)} | Total de etiquetas: {total}")


def imprimir_grupo(token: str, grupo: Grupo, estado: dict) -> None:
    print(f"Baixando etiquetas de: {grupo.nome} (qtd {grupo.quantidade}) ...")
    try:
        zpl = baixar_zpl(token, grupo.shipment_ids)
    except SeparadorError as e:
        print(f"  ERRO: {e}")
        return
    if "^XA" not in zpl:
        print("  ATENCAO: a API nao retornou ZPL valido (sem ^XA). Nada foi gerado.")
        return
    caminho = gerar_zip_etiquetas(grupo, zpl)
    print(f"  {grupo.total_etiquetas} etiquetas -> ZIP em: {caminho}")
    print("  O app da Zebra vai detectar e imprimir automaticamente.")
    marcar_impresso(estado, grupo)
    print("  Status: IMPRESSO.")


def achar_grupo(grupos: list[Grupo], texto: str, qtd: int) -> Grupo | None:
    texto = texto.lower()
    for g in grupos:
        if g.quantidade == qtd and (g.chave.lower() == texto or g.nome.lower().startswith(texto)):
            return g
    return None


def detalhar(itens: list[ItemPedido], grupos: list[Grupo], texto: str, qtd: int) -> None:
    alvo = achar_grupo(grupos, texto, qtd)
    if not alvo:
        print("Grupo nao encontrado.")
        return
    print(f"\nComposicao de: {alvo.nome} (qtd {qtd}) -> {alvo.total_etiquetas} etiquetas\n")
    comp: dict[tuple[str, str, str], set] = defaultdict(set)
    for it in itens:
        if it.chave == alvo.chave and it.quantidade == qtd and it.shipment_id:
            comp[(it.item_id, it.titulo[:50], it.voltagem)].add(it.shipment_id)
    for (iid, tit, volt), ships in sorted(comp.items(), key=lambda x: -len(x[1])):
        v = f" [{volt}]" if volt else ""
        print(f"  {len(ships):>3} et.  {iid}  {tit}{v}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    args = sys.argv[1:]
    comando = args[0] if args else "listar"

    try:
        cred = carregar_credenciais()
        token = renovar_token(cred)
    except SeparadorError as e:
        sys.exit(f"ERRO: {e}")

    if comando == "rastrear" and len(args) >= 2:
        rastrear_sku(token, cred["seller_id"], args[1])
        return

    if comando == "envios":
        # Diagnostico leve: nao precisa extrair/agrupar itens.
        pedidos = buscar_pedidos(token, cred["seller_id"])
        prontos = filtrar_para_imprimir(token, pedidos)
        debug_envios(prontos, datetime.now().date().isoformat())
        return

    # Por padrao: so os de HOJE. Comando "todos" mostra tambem os de outros dias.
    coleta = coletar_grupos(token, cred["seller_id"], somente_hoje=(comando != "todos"))
    itens, grupos = coleta.itens, coleta.grupos
    estado = carregar_estado()

    if comando in ("listar", "todos"):
        listar(grupos, estado, len(coleta.alvo))
        rotulo = "todos os dias" if comando == "todos" else "somente HOJE"
        print(f"\n(Nada foi impresso. Mostrando {rotulo}.)")

    elif comando == "detalhar" and len(args) >= 3:
        detalhar(itens, grupos, args[1], int(args[2]))

    elif comando == "imprimir" and len(args) >= 3:
        alvo_g = achar_grupo(grupos, args[1], int(args[2]))
        if not alvo_g:
            print("Grupo nao encontrado.")
            return
        imprimir_grupo(token, alvo_g, estado)

    elif comando == "proximo":
        pendente = next((g for g in grupos if status_grupo(estado, g) == "pendente"), None)
        if not pendente:
            print("Nenhum grupo pendente.")
            return
        imprimir_grupo(token, pendente, estado)

    else:
        print('Uso: listar | todos | envios | detalhar "<nome>" <QTD> | imprimir "<nome>" <QTD> | proximo')


if __name__ == "__main__":
    main()
