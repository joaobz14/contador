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
import os
import random
import re
import sys
import time
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

API = "https://api.mercadolibre.com"
TIMEOUT = 30
MAX_PEDIDOS = 3000
DIAS_JANELA = 30
TAM_NOME = 45
SUBSTATUS_IMPRIMIR = "ready_to_print"
DIAS_ESTADO = 7  # dias de historico de impressao mantidos no estado_grupos.json
# Horario de Brasilia. O Mercado Livre expressa o prazo de despacho em -03:00
# e o Brasil nao usa horario de verao desde 2019, entao um offset fixo basta
# (e evita depender da base de fusos do sistema, ausente em muitos Windows).
TZ_BR = timezone(timedelta(hours=-3))
# Pasta deste script: os arquivos de credenciais/estado/cache ficam sempre
# aqui, independente de onde o programa for aberto (atalho, agendador, etc.).
PASTA_SCRIPT = Path(__file__).resolve().parent
ARQUIVO_CRED = PASTA_SCRIPT / "credenciais.json"
ARQUIVO_ESTADO = PASTA_SCRIPT / "estado_grupos.json"
ARQUIVO_CACHE = PASTA_SCRIPT / "itens_cache.json"
# De-para opcional SKU -> nome amigavel, exibido junto do SKU na tela/CLI.
ARQUIVO_NOMES = PASTA_SCRIPT / "nomes_sku.json"
# Cache de envios ja finalizados (shipped/delivered/etc.): uma vez terminais,
# nunca mais voltam a ready_to_print, entao sao pulados nas proximas buscas.
ARQUIVO_ENVIOS_CACHE = PASTA_SCRIPT / "envios_cache.json"
# Preferencias do app (ex.: carimbar o SKU), editaveis pela tela.
ARQUIVO_CONFIG = PASTA_SCRIPT / "config.json"
PASTA_CONTAS = PASTA_SCRIPT / "contas"
STATUS_TERMINAIS = {"shipped", "delivered", "not_delivered", "cancelled"}
# Pasta que o app da Zebra (impressora_zebra_usb.py) vigia. AJUSTE aqui se o seu
# app estiver monitorando outra pasta (veja "Monitorando: ..." na tela dele).
PASTA_DOWNLOADS = Path.home() / "Downloads"

# Carimbo na DANFE (nota fiscal), na area LIVRE CENTRAL (sempre vazia),
# centralizado, para identificar o produto. A etiqueta de envio nao e carimbada.
# Dois conteudos possiveis: o SKU (modo 'carimbo') ou o NOME amigavel do produto,
# vindo da aba Nomes (modo 'carimbo_nome'). Posicao/tamanho em "dots" (203 dpi ~= 8/mm).
CARIMBAR_SKU = False   # legado: ligado quando o modo era o carimbo de SKU
MODO_IDENT = "nenhuma"  # modo de identificacao atual: carimbo | carimbo_nome | divisoria | nenhuma
CARIMBO_Y = 800        # dots a partir do topo (mais abaixo, no centro da area livre da DANFE)
CARIMBO_ALTURA = 70    # altura da fonte do SKU em dots (~8 mm)
CARIMBO_ALTURA_NOME = 45  # fonte menor para o nome (mais longo que o SKU, pode quebrar linha)
LARGURA_ETIQUETA = 812  # largura ~10 cm @203 dpi; usada para centralizar texto


# ---------------------------------------------------------------------------
# ERROS
# ---------------------------------------------------------------------------
class SeparadorError(RuntimeError):
    """Erro de negocio do separador (credenciais, token, etc.).

    O nucleo lanca esta excecao em vez de encerrar o processo, para que a
    camada que chama (CLI ou GUI) decida como mostrar a mensagem.
    """


# ---------------------------------------------------------------------------
# DATAS (sempre no horario de Brasilia, como o Mercado Livre define o prazo)
# ---------------------------------------------------------------------------
def _hoje_br() -> str:
    """Data de hoje (YYYY-MM-DD) no horario de Brasilia, independente do
    fuso/relogio da maquina (importante em servidores em UTC)."""
    return datetime.now(TZ_BR).date().isoformat()


def _amanha_br() -> str:
    """Data de amanha (YYYY-MM-DD) no horario de Brasilia."""
    return (datetime.now(TZ_BR).date() + timedelta(days=1)).isoformat()


def _data_despacho(expected_raw: str) -> str:
    """Converte o expected_date da API para o dia (YYYY-MM-DD) no horario de
    Brasilia. Interpreta o offset ISO 8601 que o ML envia; se nao der para
    parsear, cai no recorte simples dos 10 primeiros caracteres."""
    if not expected_raw:
        return ""
    try:
        dt = datetime.fromisoformat(expected_raw.replace("Z", "+00:00"))
    except ValueError:
        return expected_raw[:10]
    if dt.tzinfo is None:                 # sem offset: usa o que veio
        return expected_raw[:10]
    return dt.astimezone(TZ_BR).date().isoformat()


# ---------------------------------------------------------------------------
# IO DE ARQUIVOS JSON (gravacao atomica + leitura tolerante a falhas)
# ---------------------------------------------------------------------------
def _ler_json(caminho: Path) -> dict:
    """Le um JSON. Se nao existir ou estiver corrompido/ilegivel, retorna {}
    em vez de quebrar (importante com a sincronizacao do OneDrive, que pode
    deixar um arquivo lido pela metade)."""
    if not caminho.exists():
        return {}
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}


def _gravar_json(caminho: Path, dados) -> None:
    """Grava JSON de forma atomica e DURAVEL: escreve em .tmp, forca o disco a
    persistir (flush+fsync) e so entao renomeia. O fsync evita o classico
    'arquivo de 1 KB cheio de bytes nulos' quando cai a energia logo apos gravar
    (a renomeacao ja constava mas os dados ainda nao tinham ido pro disco)."""
    tmp = caminho.with_name(caminho.name + ".tmp")
    texto = json.dumps(dados, ensure_ascii=False, indent=2)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(texto)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass                      # alguns sistemas de arquivo nao suportam
    tmp.replace(caminho)


def carregar_config() -> dict:
    """Preferencias do app (config.json). Vazio/ausente -> {}."""
    return _ler_json(ARQUIVO_CONFIG)


def salvar_config(cfg: dict) -> None:
    _gravar_json(ARQUIVO_CONFIG, cfg)


def definir_conta(nome: str) -> Path:
    """Atualiza as globais de arquivo para apontar para contas/{nome}/."""
    global ARQUIVO_CRED, ARQUIVO_ESTADO, ARQUIVO_CACHE, ARQUIVO_ENVIOS_CACHE
    pasta = PASTA_CONTAS / nome
    pasta.mkdir(parents=True, exist_ok=True)
    ARQUIVO_CRED = pasta / "credenciais.json"
    ARQUIVO_ESTADO = pasta / "estado_grupos.json"
    ARQUIVO_CACHE = pasta / "itens_cache.json"
    ARQUIVO_ENVIOS_CACHE = pasta / "envios_cache.json"
    return pasta


def listar_contas() -> list[str]:
    """Retorna subpastas de PASTA_CONTAS que contenham credenciais.json."""
    if not PASTA_CONTAS.exists():
        return []
    return sorted(
        p.name for p in PASTA_CONTAS.iterdir()
        if p.is_dir() and (p / "credenciais.json").exists()
    )


def migrar_conta_legado(nome: str) -> None:
    """Move arquivos da raiz para contas/{nome}/ se necessario (uma unica vez)."""
    destino = PASTA_CONTAS / nome
    if (destino / "credenciais.json").exists():
        return  # ja migrado
    if not (PASTA_SCRIPT / "credenciais.json").exists():
        return  # nao ha nada para migrar
    destino.mkdir(parents=True, exist_ok=True)
    for nome_arq in ("credenciais.json", "estado_grupos.json", "envios_cache.json", "itens_cache.json"):
        origem = PASTA_SCRIPT / nome_arq
        if origem.exists():
            origem.replace(destino / nome_arq)


def conta_ativa() -> str:
    """Retorna o nome da conta ativa do config.json ('' se nao configurada)."""
    return carregar_config().get("conta_ativa", "")


def aplicar_config() -> dict:
    """Le o config.json e aplica as preferencias ao modulo (ex.: CARIMBAR_SKU).
    Devolve o config lido. Chamado na abertura da tela/CLI."""
    global CARIMBAR_SKU, MODO_IDENT
    cfg = carregar_config()
    # Modo de identificacao novo tem prioridade; cai no carimbar_sku legado.
    if "modo_identificacao" in cfg:
        MODO_IDENT = cfg["modo_identificacao"]
        CARIMBAR_SKU = MODO_IDENT == "carimbo"
    elif "carimbar_sku" in cfg:
        CARIMBAR_SKU = bool(cfg["carimbar_sku"])
        MODO_IDENT = "carimbo" if CARIMBAR_SKU else "nenhuma"
    if "conta_ativa" in cfg:
        migrar_conta_legado(cfg["conta_ativa"])  # so age se necessario
        definir_conta(cfg["conta_ativa"])
    return cfg


# ---------------------------------------------------------------------------
# CREDENCIAIS
# ---------------------------------------------------------------------------
def _caminho_backup(arquivo: Path) -> Path:
    return arquivo.with_name(arquivo.name + ".bak")


def _gravar_credenciais_com_backup(arquivo: Path, cred: dict) -> None:
    """Grava as credenciais e mantem um .bak espelho. O .bak acompanha SEMPRE a
    ultima versao (inclusive apos o token girar), para uma restauracao devolver
    um refresh_token ainda valido. Uma falha ao gravar o .bak nunca impede de
    salvar o arquivo principal."""
    _gravar_json(arquivo, cred)
    try:
        _gravar_json(_caminho_backup(arquivo), cred)
    except OSError:
        pass


def _carregar_credenciais_com_backup(arquivo: Path) -> dict | None:
    """Le credenciais tolerando corrupcao/energia, com auto-recuperacao.

    - Principal OK (JSON nao-vazio): garante o .bak em dia e devolve os dados.
    - Principal vazio/corrompido/ausente, mas ha um .bak valido: restaura o
      principal a partir do .bak e devolve os dados (recupera de queda de
      energia SEM refazer o token).
    - Nada valido: devolve None (o chamador decide a mensagem de erro)."""
    dados = _ler_json(arquivo) if arquivo.exists() else {}
    bak = _caminho_backup(arquivo)
    if dados:
        if _ler_json(bak) != dados:              # so grava o .bak quando muda
            try:
                _gravar_json(bak, dados)
            except OSError:
                pass
        return dados
    backup = _ler_json(bak) if bak.exists() else {}
    if backup:
        try:
            _gravar_json(arquivo, backup)         # restaura o principal
        except OSError:
            pass
        return backup
    return None


def carregar_credenciais() -> dict:
    dados = _carregar_credenciais_com_backup(ARQUIVO_CRED)
    if dados:
        return dados
    if not ARQUIVO_CRED.exists():
        raise SeparadorError(
            "credenciais.json nao encontrado. Rode pegar_token.py primeiro."
        )
    raise SeparadorError(
        "credenciais.json invalido ou ilegivel. Rode pegar_token.py de novo."
    )


def salvar_credenciais(cred: dict) -> None:
    _gravar_credenciais_com_backup(ARQUIVO_CRED, cred)


def renovar_token(cred: dict) -> str:
    # Refresh com retry (408/429/5xx e rede): um soluco transitorio nao derruba
    # a atualizacao inteira logo na 1a chamada.
    resp = _requisicao_post(
        f"{API}/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": cred["client_id"],
            "client_secret": cred["client_secret"],
            "refresh_token": cred["refresh_token"],
        },
    )
    if resp.status_code != 200:
        raise SeparadorError(f"Falha ao renovar token: {resp.text}")
    dados = resp.json()
    novo = dados.get("refresh_token")
    if novo and novo != cred["refresh_token"]:
        cred["refresh_token"] = novo
        salvar_credenciais(cred)
    return dados["access_token"]


def _espera_retry(resp: requests.Response, tentativa: int) -> float:
    """Tempo de espera antes de re-tentar. Respeita o cabecalho Retry-After do
    ML quando presente; senao usa backoff exponencial. Soma um jitter aleatorio
    para os varios workers nao re-tentarem todos no mesmo instante."""
    retry_after = getattr(resp, "headers", {}).get("Retry-After")
    if retry_after:
        try:
            return float(retry_after) + random.uniform(0, 0.5)
        except (TypeError, ValueError):
            pass
    return (2 ** tentativa) + random.uniform(0, 0.5)


def _requisicao_get(
    url: str, headers: dict, params: dict | None = None, tentativas: int = 3
) -> requests.Response:
    """GET com retry em erros transitorios e em falhas de rede.

    Re-tenta em respostas 408/429/500/502/503/504 (em 429 respeita o Retry-After
    do ML e aplica jitter) e tambem em quedas/timeout de conexao, para um soluco
    de rede nao derrubar a atualizacao inteira. Retorna a Response da ultima
    tentativa; quem chama decide o que fazer com o status.
    """
    resp = None
    for tentativa in range(tentativas):
        ultima = tentativa == tentativas - 1
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
        except (requests.ConnectionError, requests.Timeout):
            if ultima:
                raise
            time.sleep((2 ** (tentativa + 1)) + random.uniform(0, 0.5))
            continue
        if resp.status_code not in (408, 429, 500, 502, 503, 504) or ultima:
            return resp
        time.sleep(_espera_retry(resp, tentativa + 1))
    return resp


def _requisicao_post(url: str, *, params: dict | None = None, json: dict | None = None,
                     data: dict | None = None, timeout: int = TIMEOUT,
                     tentativas: int = 3) -> requests.Response:
    """POST com retry em erros transitorios (408/429/5xx) e falhas de rede — mesma
    politica do _requisicao_get. Usado pelo refresh de token e pela Shopee (cujos
    POSTs, sem isto, nao re-tentavam num soluco de rede/429)."""
    resp = None
    for tentativa in range(tentativas):
        ultima = tentativa == tentativas - 1
        try:
            resp = requests.post(url, params=params, json=json, data=data, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout):
            if ultima:
                raise
            time.sleep((2 ** (tentativa + 1)) + random.uniform(0, 0.5))
            continue
        if resp.status_code not in (408, 429, 500, 502, 503, 504) or ultima:
            return resp
        time.sleep(_espera_retry(resp, tentativa + 1))
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
    # Dia de despacho (YYYY-MM-DD) ao qual este grupo pertence. Usado como
    # referencia no estado de impressao; vazio = usa o dia de hoje.
    dia: str = ""
    # Para envios "combo" (varios SKUs no mesmo pacote): lista de (sku, qtd).
    # Vazio em grupos normais de um unico SKU.
    componentes: list = field(default_factory=list)
    # Codigo de rastreio (AWB) — preenchido so para grupos Shopee de 1 pedido ja
    # impresso, para conferencia (app x etiqueta x site). Vazio nos demais.
    rastreio: str = ""

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
    return _ler_json(ARQUIVO_CACHE)


def salvar_cache(cache: dict) -> None:
    _gravar_json(ARQUIVO_CACHE, cache)


def _detalhe_item(token: str, item_id: str) -> tuple[str, dict]:
    """Busca 1 item e extrai (titulo, {variacao: GTIN}). Falha vira entrada vazia."""
    try:
        det = _get(f"{API}/items/{item_id}", token, params={"include_attributes": "all"})
    except requests.HTTPError:
        return item_id, {"title": "", "variations": {}}
    variacoes: dict[str, str] = {}
    for v in det.get("variations", []):
        gtin = ""
        for a in v.get("attributes", []):
            if a.get("id") == "GTIN":
                gtin = a.get("value_name") or ""
        variacoes[str(v.get("id"))] = gtin
    return item_id, {"title": det.get("title", ""), "variations": variacoes}


def buscar_detalhes(token: str, item_ids: set[str], cache: dict) -> None:
    faltando = [i for i in item_ids if i not in cache]
    if not faltando:
        return
    print(f"Buscando detalhes de {len(faltando)} produtos novos...")
    # Em paralelo (antes era serial): so ocorre quando aparece produto novo.
    with ThreadPoolExecutor(max_workers=8) as ex:
        for item_id, entry in ex.map(lambda i: _detalhe_item(token, i), faltando):
            cache[item_id] = entry
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
    desde = (datetime.now(TZ_BR) - timedelta(days=DIAS_JANELA)).strftime("%Y-%m-%dT00:00:00.000-03:00")

    def pagina(offset: int) -> dict:
        return _get(
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

    # 1a pagina (offset 0) para descobrir o total; as demais vao em paralelo.
    primeira = pagina(0)
    pedidos: list[dict] = list(primeira.get("results", []))
    total = min(primeira.get("paging", {}).get("total", 0), MAX_PEDIDOS)
    offsets = list(range(50, total, 50))
    if offsets:
        with ThreadPoolExecutor(max_workers=8) as ex:
            for dados in ex.map(pagina, offsets):
                pedidos.extend(dados.get("results", []))
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
    hoje = _hoje_br()
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
        exp = _data_despacho(sla.get("expected_date") or "")
        entra = status == "paid" and sub == SUBSTATUS_IMPRIMIR and exp == hoje
        marca = "ENTRA HOJE" if entra else "fora"
        print(f"  pedido {ped.get('id')} | qtd {qtd} | status {status} | "
              f"envio {sub} | despacho {exp} | -> {marca}")


def buscar_envio(token: str, shipment_id: int) -> dict:
    try:
        return _get(f"{API}/shipments/{shipment_id}", token, extra={"x-format-new": "true"})
    except requests.HTTPError:
        return {}


def _prazo_do_envio(env: dict) -> str:
    """Tenta achar o prazo de despacho (handling limit) ja dentro do detalhe
    do envio, evitando uma chamada extra ao /sla. Cobre os formatos conhecidos
    do ML; retorna "" se nao encontrar (ai o chamador cai no /sla)."""
    candidatos = [
        ((env.get("shipping_option") or {}).get("estimated_handling_limit") or {}).get("date"),
        (env.get("estimated_handling_limit") or {}).get("date"),
        ((env.get("lead_time") or {}).get("estimated_handling_limit") or {}).get("date"),
        (env.get("sla") or {}).get("expected_date"),
    ]
    for valor in candidatos:
        if valor:
            return valor
    return ""


def _carregar_envios_cache() -> dict:
    return _ler_json(ARQUIVO_ENVIOS_CACHE)


def _salvar_envios_cache(cache: dict) -> None:
    _gravar_json(ARQUIVO_ENVIOS_CACHE, cache)


def _limpar_envios_cache(cache: dict, dias: int = DIAS_JANELA) -> dict:
    """Descarta entradas mais antigas que a janela de busca de pedidos
    (alem dela o pedido nem aparece mais em orders/search)."""
    limite = (datetime.now(TZ_BR).date() - timedelta(days=dias)).isoformat()
    return {sid: d for sid, d in cache.items() if isinstance(d, str) and d >= limite}


def _avaliar_pedido(token: str, ped: dict) -> tuple[dict | None, int | None, str]:
    """Avalia o envio do pedido. Retorna (pedido, shipment_id, status):
    o pedido vem com _envio preenchido quando esta em ready_to_print; senao
    vem None (mas com o status, para o cache de finalizados)."""
    sid = (ped.get("shipping") or {}).get("id")
    if not sid:
        return None, None, ""
    env = buscar_envio(token, sid)
    status = env.get("status") or ""
    if env.get("substatus") != SUBSTATUS_IMPRIMIR:
        return None, sid, status
    # O prazo de despacho costuma vir no proprio detalhe do envio; so chama o
    # /sla (uma requisicao a mais) quando nao encontramos no detalhe.
    expected_raw = _prazo_do_envio(env)
    if not expected_raw:
        expected_raw = _sla(token, sid).get("expected_date") or ""
    expected = _data_despacho(expected_raw)
    logt = env.get("logistic_type") or (env.get("logistic") or {}).get("type", "")
    ped["_envio"] = {"shipment_id": sid, "expected_date": expected, "logistica": logt}
    return ped, sid, status


def filtrar_para_imprimir(token: str, pedidos: list[dict], progresso=None) -> list[dict]:
    """Mantem pedidos em ready_to_print. progresso(feitos, total) e chamado por pedido.

    Pula os envios ja conhecidos como finalizados (cache de status terminais),
    reduzindo bastante as chamadas a API em atualizacoes repetidas.
    """
    cache = _carregar_envios_cache()
    hoje = _hoje_br()
    a_checar = [
        p for p in pedidos
        if str((p.get("shipping") or {}).get("id")) not in cache
    ]
    total = len(a_checar)
    prontos: list[dict] = []
    novos_terminais: dict = {}
    feitos = 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        for ped, sid, status in ex.map(lambda p: _avaliar_pedido(token, p), a_checar):
            feitos += 1
            if progresso:
                progresso(feitos, total)
            else:
                print(f"  Verificando envios: {feitos}/{total}", end="\r")
            if ped is not None:
                prontos.append(ped)
            elif sid and status in STATUS_TERMINAIS:
                novos_terminais[str(sid)] = hoje
    if not progresso:
        print()
    cache.update(novos_terminais)
    _salvar_envios_cache(_limpar_envios_cache(cache))
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
    """Agrupa por ENVIO (1 envio = 1 etiqueta):

    - envio com 1 SKU (mesmo que varias unidades) -> grupo por SKU + quantidade;
    - envio com SKUs diferentes (combo/kit) -> um grupo "combo" proprio, contando
      1 etiqueta por pacote (nunca separa o combo por SKU).
    """
    # 1) junta os itens por envio
    por_envio: dict[int, list[ItemPedido]] = defaultdict(list)
    for it in itens:
        if it.shipment_id:
            por_envio[it.shipment_id].append(it)

    # 2) para cada envio, decide se e SKU unico ou combo
    grupos: dict[tuple[str, int], Grupo] = {}
    for sid, do_envio in por_envio.items():
        qtd_por_chave: dict[str, int] = defaultdict(int)
        nome_por_chave: dict[str, str] = {}
        for it in do_envio:
            qtd_por_chave[it.chave] += it.quantidade
            nome_por_chave.setdefault(it.chave, it.nome)

        if len(qtd_por_chave) == 1:                     # envio de um unico SKU
            chave, qtd = next(iter(qtd_por_chave.items()))
            nome = nome_por_chave[chave]
            componentes: list = []
        else:                                            # envio combo (varios SKUs)
            comp = sorted(qtd_por_chave.items())
            chave = "COMBO:" + "+".join(f"{c}x{q}" for c, q in comp)
            qtd = 1
            nome = "Combo: " + " + ".join(f"{c} x{q}" for c, q in comp)
            componentes = comp

        g = grupos.get((chave, qtd))
        if g is None:
            g = Grupo(chave=chave, nome=nome, quantidade=qtd, componentes=componentes)
            grupos[(chave, qtd)] = g
        if sid not in g.shipment_ids:
            g.shipment_ids.append(sid)
    return sorted(grupos.values(), key=lambda g: (g.quantidade, g.nome.lower()))


# ---------------------------------------------------------------------------
# NOMES AMIGAVEIS (de-para SKU -> nome)
# ---------------------------------------------------------------------------
def carregar_nomes() -> dict:
    """Le o de-para SKU -> nome do nomes_sku.json (vazio se nao existir)."""
    return _ler_json(ARQUIVO_NOMES)


def salvar_nomes(nomes: dict) -> None:
    """Grava o de-para SKU -> nome de forma atomica (.tmp -> rename), com as
    chaves ordenadas para o diff do git ficar limpo. Descarta SKUs/nomes
    vazios."""
    limpo = {str(sku).strip(): str(nome).strip()
             for sku, nome in nomes.items() if str(sku).strip() and str(nome).strip()}
    _gravar_json(ARQUIVO_NOMES, dict(sorted(limpo.items())))


def _rotulo_sku(sku: str, nomes: dict) -> str:
    amigavel = nomes.get(sku)
    return f"{sku} — {amigavel}" if amigavel else sku


def aplicar_nomes(grupos: list[Grupo], nomes: dict) -> None:
    """Acrescenta o nome amigavel ao rotulo dos grupos cujo SKU esta no mapa.
    Ex.: 'PRP' -> 'PRP — Picador Pequeno'. Em combos, enriquece cada SKU do
    pacote. So mexe na exibicao (Grupo.nome); agrupamento e estado seguem
    pela chave."""
    if not nomes:
        return
    for g in grupos:
        if g.componentes:                                # combo: enriquece os itens
            partes = [
                f"{_rotulo_sku(sku, nomes)} (x{q})" if q > 1 else _rotulo_sku(sku, nomes)
                for sku, q in g.componentes
            ]
            g.nome = "Combo: " + " + ".join(partes)
        else:
            amigavel = nomes.get(g.chave)
            if amigavel:
                g.nome = f"{g.chave} — {amigavel}"


@dataclass
class Coleta:
    """Resultado do pipeline completo de uma atualizacao."""
    prontos: list[dict]               # todos os envios ready_to_print
    alvo: list[dict]                  # subconjunto considerado (hoje ou todos)
    itens: list[ItemPedido]
    grupos: list[Grupo]


def coletar_grupos(
    token: str, seller_id: str, *, dia: str | None = None,
    somente_hoje: bool = True, progresso=None,
) -> Coleta:
    """Busca pedidos, filtra os prontos para imprimir, seleciona pelo dia,
    extrai os itens e agrupa. Centraliza o fluxo usado pela CLI e pela GUI
    para que as duas nao divirjam. progresso(feitos, total) e repassado ao
    filtro de envios.

    Selecao do alvo: se `dia` (YYYY-MM-DD) for informado, usa esse dia de
    despacho; senao, `somente_hoje` decide entre hoje e todos os dias.
    """
    pedidos = buscar_pedidos(token, seller_id)
    prontos = filtrar_para_imprimir(token, pedidos, progresso=progresso)
    if dia is not None:
        alvo = [p for p in prontos if p["_envio"]["expected_date"] == dia]
    elif somente_hoje:
        hoje = _hoje_br()
        alvo = [p for p in prontos if p["_envio"]["expected_date"] == hoje]
    else:
        alvo = prontos
    itens = extrair_itens(token, alvo)
    grupos = agrupar(itens)
    aplicar_nomes(grupos, carregar_nomes())
    if dia is not None:
        # Grupos de um dia especifico carregam esse dia para o estado de
        # impressao ser avaliado/gravado por dia de despacho.
        for g in grupos:
            g.dia = dia
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


def resumo_por_dia(pedidos_prontos: list[dict]) -> list[tuple[str, int]]:
    """Conta quantos envios prontos ha em cada dia de despacho, ordenado por
    data. Funcao pura (testavel sem rede)."""
    por_dia: dict[str, int] = defaultdict(int)
    for ped in pedidos_prontos:
        data = (ped.get("_envio") or {}).get("expected_date") or "(sem data)"
        por_dia[data] += 1
    return sorted(por_dia.items())


def imprimir_resumo(pedidos_prontos: list[dict], hoje: str, amanha: str) -> None:
    """Mostra um panorama de quantos pacotes ha por dia de despacho."""
    linhas = resumo_por_dia(pedidos_prontos)
    print(f"\n--- RESUMO POR DIA DE DESPACHO (hoje = {hoje}) ---\n")
    if not linhas:
        print("  Nenhum envio pronto para imprimir.")
        return
    for data, qtd in linhas:
        if data == hoje:
            marca = " <== HOJE"
        elif data == amanha:
            marca = " <== amanha"
        else:
            marca = ""
        print(f"  {data}   {qtd:>3} pacote(s){marca}")
    print(f"\n  Total: {len(pedidos_prontos)} pacote(s) em {len(linhas)} dia(s).")


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


def _texto_carimbo(grupo: Grupo) -> str:
    """Codigo curto do produto para carimbar na etiqueta.

    Grupo normal: o proprio SKU/chave. Combo: os SKUs unidos por '+'.
    """
    if grupo.componentes:
        return "+".join(str(sku) for sku, _ in grupo.componentes)
    return grupo.chave


def _texto_carimbo_nome(grupo: Grupo, nomes: dict | None = None) -> str:
    """Nome amigavel do produto para carimbar (modo 'carimbo_nome'), vindo da
    aba Nomes (nomes_sku.json). Combo: os nomes unidos por ' + '. Se um SKU nao
    tem nome cadastrado, cai no proprio SKU, para o produto nunca ficar sem
    identificacao."""
    if nomes is None:
        nomes = carregar_nomes()
    if grupo.componentes:
        return " + ".join(nomes.get(str(sku), str(sku)) for sku, _ in grupo.componentes)
    return nomes.get(grupo.chave, grupo.chave)


def _modo_ident_efetivo() -> str:
    """Modo de identificacao em vigor para a impressao de UM grupo (caminhos que
    usam o estado global, nao o parametro `modo`). Respeita o CARIMBAR_SKU legado."""
    if MODO_IDENT in ("carimbo", "carimbo_nome"):
        return MODO_IDENT
    return "carimbo" if CARIMBAR_SKU else "nenhuma"


def _carimbar_grupo(zpl: str, grupo: Grupo, modo: str, nomes: dict | None = None) -> str:
    """Aplica na DANFE o carimbo do modo pedido, devolvendo o ZPL (intacto se o
    modo nao carimba):
      - 'carimbo':      o SKU, 1 linha, fonte cheia;
      - 'carimbo_nome': o nome amigavel, fonte menor e ate 3 linhas (nomes sao
                        mais longos que o SKU e podem quebrar linha)."""
    if modo == "carimbo_nome":
        return carimbar_zpl(zpl, _texto_carimbo_nome(grupo, nomes),
                            altura=CARIMBO_ALTURA_NOME, linhas=3)
    if modo == "carimbo":
        return carimbar_zpl(zpl, _texto_carimbo(grupo))
    return zpl


def _largura_zpl(bloco: str) -> int:
    """Largura de impressao (^PWxxxx) do bloco; cai no padrao se nao houver."""
    m = re.search(r"\^PW(\d+)", bloco)
    return int(m.group(1)) if m else LARGURA_ETIQUETA


def carimbar_zpl(zpl: str, texto: str, *, altura: int = CARIMBO_ALTURA,
                 linhas: int = 1) -> str:
    """Carimba `texto` (o SKU ou o nome do produto) na DANFE (nota fiscal),
    CENTRALIZADO na area livre central.

    O "pacote" do ML traz duas paginas: a DANFE (nota fiscal) e a etiqueta de
    envio. Carimbamos SO a DANFE (bloco que contem "DANFE"); a etiqueta de envio
    fica intacta. O texto e centralizado na largura da etiqueta (^FB ... C).
    `altura` = tamanho da fonte em dots; `linhas` = maximo de linhas do bloco
    (o nome, mais longo, usa fonte menor e ate 3 linhas). Texto vazio, ZPL sem
    `^XZ` ou sem DANFE -> devolve intacto."""
    if not texto or "^XZ" not in zpl:
        return zpl
    seguro = texto.replace("^", " ").replace("~", " ")

    def _aplica(m: "re.Match") -> str:
        bloco = m.group(0)
        if "DANFE" not in bloco.upper():       # so a nota fiscal leva o carimbo
            return bloco
        pw = _largura_zpl(bloco)
        campo = (f"^FO0,{CARIMBO_Y}^A0N,{altura},{altura}"
                 f"^FB{pw},{linhas},0,C,0^FD{seguro}^FS")
        return bloco.replace("^XZ", f"\n{campo}\n^XZ", 1)

    novo, _ = re.subn(r"\^XA.*?\^XZ", _aplica, zpl, flags=re.DOTALL)
    return novo


def zpl_divisoria(grupo: Grupo) -> str:
    """Etiqueta separadora (1 pagina ZPL) com SKU, nome e quantidade do lote,
    centralizada. Impressa ANTES das etiquetas do lote no modo 'divisoria'."""
    sku = _texto_carimbo(grupo).replace("^", " ").replace("~", " ")
    nome = grupo.nome.replace("^", " ").replace("~", " ")
    info = f"q{grupo.quantidade}  -  {grupo.total_etiquetas} etiqueta(s)"
    w = LARGURA_ETIQUETA - 40
    return (
        "^XA^CI28"
        f"^FO20,260^A0N,120,120^FB{w},1,0,C,0^FD{sku}^FS"
        f"^FO20,410^A0N,45,45^FB{w},3,6,C,0^FD{nome}^FS"
        f"^FO20,640^A0N,55,55^FB{w},1,0,C,0^FD{info}^FS"
        "^XZ"
    )


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


def _gerar_zip(rotulo: str, zpl_texto: str) -> Path:
    """
    Monta um ZIP no formato que o impressora_zebra_usb.py reconhece:
      - nome do ZIP comeca com um prefixo aceito ("etiqueta de envio")
      - dentro, um TXT cujo nome contem "etiqueta de envio" (identifica ML)
    Grava de forma atomica (.tmp -> rename) para o monitor so ver o arquivo pronto.
    """
    PASTA_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    base = "".join(c if c.isalnum() else "_" for c in rotulo)[:40].strip("_")
    nome_zip = PASTA_DOWNLOADS / f"etiqueta de envio - {base}.zip"
    tmp = nome_zip.with_name(nome_zip.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"Etiqueta de envio - {base}.txt", zpl_texto)
    tmp.replace(nome_zip)
    return nome_zip


def gerar_zip_etiquetas(grupo: Grupo, zpl_texto: str) -> Path:
    return _gerar_zip(f"{grupo.nome} - q{grupo.quantidade}", zpl_texto)


# ---------------------------------------------------------------------------
# ESTADO
# ---------------------------------------------------------------------------
def _limpar_estado_antigo(estado: dict, dias: int = DIAS_ESTADO) -> dict:
    """Mantem so as entradas dos ultimos `dias` dias.

    As chaves tem o formato 'YYYY-MM-DD|...'. Entradas mais antigas que a
    janela (e chaves sem data valida, como formatos legados) sao descartadas,
    evitando que o estado_grupos.json cresca indefinidamente.
    """
    limite = (datetime.now(TZ_BR).date() - timedelta(days=dias)).isoformat()
    limpo: dict = {}
    for chave, valor in estado.items():
        data = chave.split("|", 1)[0]
        try:
            datetime.strptime(data, "%Y-%m-%d")
        except ValueError:
            continue  # chave sem data valida (legado): descarta
        if data >= limite:
            limpo[chave] = valor
    return limpo


def carregar_estado() -> dict:
    estado = _ler_json(ARQUIVO_ESTADO)
    limpo = _limpar_estado_antigo(estado)
    if len(limpo) != len(estado):   # poda entradas antigas e persiste
        salvar_estado(limpo)
    return limpo


def salvar_estado(estado: dict) -> None:
    _gravar_json(ARQUIVO_ESTADO, estado)


def _chave_estado(grupo: Grupo) -> str:
    # Usa o dia de despacho do grupo (quando definido) para namespacar o
    # estado por dia; senao, cai no dia de hoje.
    return f"{grupo.dia or _hoje_br()}|{grupo.chave_grupo}"


def _impressos(estado: dict, grupo: Grupo) -> set[int]:
    """Conjunto de shipment_ids ja impressos para o grupo (no dia).

    Aceita o formato novo (lista de ids) e o antigo (string "impresso"),
    para nao quebrar arquivos de estado ja existentes.
    """
    valor = estado.get(_chave_estado(grupo))
    if valor == "impresso":               # formato antigo: tudo impresso
        return set(grupo.shipment_ids)
    if isinstance(valor, list):
        return set(valor)
    return set()


def status_grupo(estado: dict, grupo: Grupo) -> str:
    """pendente | parcial | impresso, comparando os envios ATUAIS do grupo
    com os que ja foram impressos. Um envio novo reabre o grupo."""
    atuais = set(grupo.shipment_ids)
    if not atuais:
        return "pendente"
    impressos = _impressos(estado, grupo)
    if atuais <= impressos:
        return "impresso"
    if atuais & impressos:
        return "parcial"
    return "pendente"


def envios_pendentes(estado: dict, grupo: Grupo) -> list[int]:
    """Envios do grupo que ainda nao foram impressos (preserva a ordem)."""
    impressos = _impressos(estado, grupo)
    return [s for s in grupo.shipment_ids if s not in impressos]


def marcar_impresso(estado: dict, grupo: Grupo, shipment_ids: list[int] | None = None) -> None:
    """Marca como impressos os shipment_ids informados (ou todos do grupo),
    acumulando com os ja registrados no dia.

    Antes de gravar, RECARREGA o estado do disco e mescla (uniao). Assim, se a
    tela e o bot estiverem rodando ao mesmo tempo na mesma conta, a marcacao de
    um nao apaga a do outro feita nesse meio-tempo (last-writer-merge em vez de
    last-writer-wins). O dict em memoria do chamador tambem e atualizado para o
    render seguinte refletir o que foi gravado."""
    ids = grupo.shipment_ids if shipment_ids is None else shipment_ids
    chave = _chave_estado(grupo)
    disco = _ler_json(ARQUIVO_ESTADO)
    impressos = _impressos(estado, grupo)       # o que ja sabiamos em memoria
    impressos.update(_impressos(disco, grupo))  # + o que outro processo gravou
    impressos.update(ids)                       # + os recem-impressos
    ordenados = sorted(impressos)
    disco[chave] = ordenados                    # grava por cima do disco atual
    salvar_estado(disco)
    estado[chave] = ordenados                   # reflete na memoria do chamador


def imprimir_pendentes(token: str, grupo: Grupo, estado: dict) -> list[int]:
    """Baixa e gera o ZIP APENAS dos envios ainda nao impressos do grupo,
    marca-os e retorna a lista impressa (vazia se nada estava pendente).

    Logica compartilhada por CLI e GUI. Lanca SeparadorError em falha de
    download ou ZPL invalido; nesse caso nada e marcado como impresso.
    """
    pendentes = envios_pendentes(estado, grupo)
    if not pendentes:
        return []
    zpl = baixar_zpl(token, pendentes)
    if "^XA" not in zpl:
        raise SeparadorError("A API nao retornou ZPL valido (sem ^XA).")
    zpl = _carimbar_grupo(zpl, grupo, _modo_ident_efetivo())
    gerar_zip_etiquetas(grupo, zpl)
    marcar_impresso(estado, grupo, pendentes)
    return pendentes


def reimprimir(token: str, grupo: Grupo) -> list[int]:
    """Reimprime TODAS as etiquetas do grupo, independente do estado.

    Util quando uma etiqueta atolou/estragou. NAO altera o estado (o grupo
    continua como estava). Lanca SeparadorError em falha de download ou ZPL
    invalido. So funciona enquanto o ML ainda devolver a etiqueta dos envios.
    """
    ids = list(grupo.shipment_ids)
    if not ids:
        return []
    zpl = baixar_zpl(token, ids)
    if "^XA" not in zpl:
        raise SeparadorError("A API nao retornou ZPL valido (sem ^XA).")
    zpl = _carimbar_grupo(zpl, grupo, _modo_ident_efetivo())
    gerar_zip_etiquetas(grupo, zpl)
    return ids


def preparar_lotes(token: str, grupos: list[Grupo], estado: dict,
                   *, modo: str = "nenhuma") -> tuple[str, list[tuple[Grupo, list[int]]]]:
    """Baixa as etiquetas dos lotes (apenas os envios pendentes de cada um) e monta
    UM ZPL combinado, na ordem dos grupos. Por lote:
      - modo='divisoria':    insere uma etiqueta separadora ANTES das etiquetas;
      - modo='carimbo':      carimba o SKU em cada DANFE;
      - modo='carimbo_nome': carimba o NOME do produto (aba Nomes) em cada DANFE;
      - modo='nenhuma':      nem divisoria nem carimbo.

    NAO marca nada como impresso (quem chama marca depois da confirmacao). Aborta
    com SeparadorError se algum download falhar (nada e gerado). Devolve
    (zpl_combinado, [(grupo, pendentes), ...])."""
    partes: list[str] = []
    pendentes: list[tuple[Grupo, list[int]]] = []
    nomes = carregar_nomes() if modo == "carimbo_nome" else None   # 1 leitura so
    for g in grupos:
        pend = envios_pendentes(estado, g)
        if not pend:
            continue
        zpl = baixar_zpl(token, pend)
        if "^XA" not in zpl:
            raise SeparadorError("A API nao retornou ZPL valido (sem ^XA).")
        zpl = _carimbar_grupo(zpl, g, modo, nomes)
        if modo == "divisoria":
            partes.append(zpl_divisoria(g))
        partes.append(zpl)
        pendentes.append((g, pend))
    return "\n".join(partes), pendentes


def gerar_zip_lotes(token: str, grupos: list[Grupo], estado: dict,
                    *, modo: str = "nenhuma") -> list[tuple[Grupo, list[int]]]:
    """Gera UM ZIP com todos os lotes selecionados (com divisoria/carimbo conforme
    o modo) e devolve [(grupo, pendentes), ...] para marcar depois. Nada e marcado aqui."""
    zpl, pendentes = preparar_lotes(token, grupos, estado, modo=modo)
    if not pendentes:
        return []
    _gerar_zip(f"LOTES x{len(pendentes)}", zpl)
    return pendentes


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
    pendentes = envios_pendentes(estado, grupo)
    if not pendentes:
        print(f"Grupo '{grupo.nome}' (qtd {grupo.quantidade}): nada pendente, ja impresso.")
        return
    print(f"Baixando {len(pendentes)} etiqueta(s) de: {grupo.nome} (qtd {grupo.quantidade}) ...")
    try:
        impressos = imprimir_pendentes(token, grupo, estado)
    except SeparadorError as e:
        print(f"  ERRO: {e}")
        return
    print(f"  {len(impressos)} etiqueta(s) -> ZIP gerado em: {PASTA_DOWNLOADS}")
    print("  O app da Zebra vai detectar e imprimir automaticamente.")
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
    aplicar_config()           # respeita a preferencia de carimbo salva na tela

    try:
        cred = carregar_credenciais()
        token = renovar_token(cred)
    except SeparadorError as e:
        sys.exit(f"ERRO: {e}")

    if comando == "rastrear" and len(args) >= 2:
        rastrear_sku(token, cred["seller_id"], args[1])
        return

    if comando in ("envios", "resumo"):
        # Diagnostico leve: nao precisa extrair/agrupar itens.
        pedidos = buscar_pedidos(token, cred["seller_id"])
        prontos = filtrar_para_imprimir(token, pedidos)
        if comando == "resumo":
            imprimir_resumo(prontos, _hoje_br(), _amanha_br())
        else:
            debug_envios(prontos, _hoje_br())
        return

    # Selecao do dia: hoje (padrao), amanha, uma data especifica ou todos.
    dia = None
    rotulo = "somente HOJE"
    if comando == "amanha":
        dia = _amanha_br()
        rotulo = f"despacho de AMANHA ({dia})"
    elif comando == "dia" and len(args) >= 2:
        dia = args[1]
        rotulo = f"despacho de {dia}"
    elif comando == "todos":
        rotulo = "todos os dias"

    coleta = coletar_grupos(
        token, cred["seller_id"], dia=dia, somente_hoje=(comando not in ("todos",)),
    )
    itens, grupos = coleta.itens, coleta.grupos
    estado = carregar_estado()

    if comando in ("listar", "todos", "amanha", "dia"):
        listar(grupos, estado, len(coleta.alvo))
        print(f"\n(Nada foi impresso. Mostrando {rotulo}.)")

    elif comando == "detalhar" and len(args) >= 3:
        detalhar(itens, grupos, args[1], int(args[2]))

    elif comando == "imprimir" and len(args) >= 3:
        alvo_g = achar_grupo(grupos, args[1], int(args[2]))
        if not alvo_g:
            print("Grupo nao encontrado.")
            return
        imprimir_grupo(token, alvo_g, estado)

    elif comando == "reimprimir" and len(args) >= 3:
        alvo_g = achar_grupo(grupos, args[1], int(args[2]))
        if not alvo_g:
            print("Grupo nao encontrado.")
            return
        print(f"Reimprimindo {alvo_g.total_etiquetas} etiqueta(s) de: "
              f"{alvo_g.nome} (qtd {alvo_g.quantidade}) ...")
        try:
            reimpressos = reimprimir(token, alvo_g)
        except SeparadorError as e:
            print(f"  ERRO: {e}")
            return
        print(f"  {len(reimpressos)} etiqueta(s) -> ZIP gerado em: {PASTA_DOWNLOADS}")
        print("  (O estado de impresso nao foi alterado.)")

    elif comando == "proximo":
        pendente = next((g for g in grupos if status_grupo(estado, g) == "pendente"), None)
        if not pendente:
            print("Nenhum grupo pendente.")
            return
        imprimir_grupo(token, pendente, estado)

    else:
        print('Uso: listar | amanha | dia <AAAA-MM-DD> | todos | envios | resumo | '
              'detalhar "<nome>" <QTD> | imprimir "<nome>" <QTD> | '
              'reimprimir "<nome>" <QTD> | proximo')


if __name__ == "__main__":
    main()
