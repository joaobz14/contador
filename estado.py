"""
estado.py
Camada comum do controle de "ja impresso" (estado de impressao), compartilhada
por Mercado Livre e Shopee. Antes essa logica vivia no nucleo (separador_etiquetas_ml)
e era parcialmente COPIADA no shopee_api; aqui ela e unica.

O estado e um dict {chave -> lista de ids impressos}, gravado num JSON por
marketplace + conta + dia de despacho:
  chave = "{dia_de_despacho}|{chave_do_grupo}"  (ex.: "2026-07-08|SKU123|q2")
  valor = lista de shipment_ids (ML) / order_sns (Shopee) ja impressos no dia.

Regras que este modulo protege (invariantes do projeto):
  - envio novo num grupo ja impresso REABRE o grupo como "parcial";
  - marcar_impresso RECARREGA do disco e MESCLA (uniao) antes de gravar
    (last-writer-merge: tela e bot na mesma conta nao se apagam);
  - leitura tolerante do formato legado ("impresso" como string);
  - poda por idade para o arquivo nao crescer sem fim.

Modulo-folha de proposito: NAO importa o nucleo. As funcoes de arquivo recebem
o CAMINHO explicito (o unico ponto em que ML e Shopee diferem) — o nucleo e o
shopee_api mantem wrappers finos que passam o seu ARQUIVO_ESTADO. O fuso de
Brasilia e espelhado aqui (UTC-3) para manter a folha independente; e a mesma
regra de sempre-Brasilia do nucleo.
"""
from __future__ import annotations

import contextlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Fuso de Brasilia (UTC-3), espelhado do nucleo para manter este modulo sem
# dependencia do god-file. A regra e a mesma: datas de despacho sempre em BR.
_TZ_BR = timezone(timedelta(hours=-3))


def _hoje_br() -> str:
    return datetime.now(_TZ_BR).date().isoformat()


# ---------------------------------------------------------------------------
# IO DE JSON (gravacao atomica+duravel / leitura tolerante a falhas)
# ---------------------------------------------------------------------------
def ler_json(caminho: Path) -> dict:
    """Le um JSON. Se nao existir ou estiver corrompido/ilegivel, retorna {}
    em vez de quebrar (importante com a sincronizacao do OneDrive, que pode
    deixar um arquivo lido pela metade)."""
    if not caminho.exists():
        return {}
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}


def gravar_json(caminho: Path, dados) -> None:
    """Grava JSON de forma atomica e DURAVEL: escreve em .tmp, forca o disco a
    persistir (flush+fsync) e so entao renomeia. O fsync evita o classico
    'arquivo de 1 KB cheio de bytes nulos' quando cai a energia logo apos gravar
    (a renomeacao ja constava mas os dados ainda nao tinham ido pro disco).

    O nome do .tmp inclui o PID: dois processos (tela + bot) gravando o mesmo
    arquivo nao disputam o mesmo temporario (um sobrescreveria/renomearia o tmp
    do outro no meio da escrita). Continua terminando em .tmp (gitignore)."""
    tmp = caminho.with_name(f"{caminho.name}.{os.getpid()}.tmp")
    texto = json.dumps(dados, ensure_ascii=False, indent=2)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(texto)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass                      # alguns sistemas de arquivo nao suportam
    tmp.replace(caminho)


# ---------------------------------------------------------------------------
# TRAVA ENTRE PROCESSOS (para o ciclo ler -> mesclar -> salvar do estado)
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def trava(caminho: Path):
    """Exclusao mutua ENTRE PROCESSOS para o arquivo `caminho` (via um .lock ao
    lado). O merge do marcar_impresso protege o caso sequencial, mas se a tela e
    o bot LEREM ao mesmo tempo (antes de qualquer um gravar), a ultima gravacao
    venceria e uma marcacao se perderia — esta trava serializa o ciclo inteiro.

    Windows usa msvcrt.locking (bloqueia ate ~10s, depois OSError); POSIX usa
    fcntl.flock (bloqueia). DEGRADACAO SUAVE: se a trava nao puder ser obtida
    (sistema de arquivos sem suporte, permissao, timeout), segue SEM ela — o
    comportamento volta a ser o merge de hoje, que ja cobre o caso sequencial;
    melhor isso que impedir a marcacao de uma etiqueta ja impressa. O .lock e
    local e gitignorado; fica no disco (esvaziado) apos o uso, sem problema."""
    lock_path = caminho.with_name(caminho.name + ".lock")
    try:
        f = open(lock_path, "a+")
    except OSError:
        yield                                   # sem .lock possivel: segue sem trava
        return
    travado = False
    try:
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            travado = True
        except OSError:
            pass                                # degrada: opera sem trava
        yield
    finally:
        if travado:
            try:
                if os.name == "nt":
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        f.close()


# ---------------------------------------------------------------------------
# LOGICA DE ESTADO (puras — nao tocam disco)
# ---------------------------------------------------------------------------
def chave_estado(grupo) -> str:
    # Usa o dia de despacho do grupo (quando definido) para namespacar o
    # estado por dia; senao, cai no dia de hoje.
    return f"{grupo.dia or _hoje_br()}|{grupo.chave_grupo}"


def impressos(estado: dict, grupo) -> set:
    """Conjunto de ids ja impressos para o grupo (no dia).

    Aceita o formato novo (lista de ids) e o antigo (string "impresso"),
    para nao quebrar arquivos de estado ja existentes.
    """
    valor = estado.get(chave_estado(grupo))
    if valor == "impresso":               # formato antigo: tudo impresso
        return set(grupo.shipment_ids)
    if isinstance(valor, list):
        return set(valor)
    return set()


def status_grupo(estado: dict, grupo) -> str:
    """pendente | parcial | impresso, comparando os envios ATUAIS do grupo
    com os que ja foram impressos. Um envio novo reabre o grupo."""
    atuais = set(grupo.shipment_ids)
    if not atuais:
        return "pendente"
    imp = impressos(estado, grupo)
    if atuais <= imp:
        return "impresso"
    if atuais & imp:
        return "parcial"
    return "pendente"


def envios_pendentes(estado: dict, grupo) -> list:
    """Envios do grupo que ainda nao foram impressos (preserva a ordem)."""
    imp = impressos(estado, grupo)
    return [s for s in grupo.shipment_ids if s not in imp]


def limpar_antigo(estado: dict, dias: int) -> dict:
    """Mantem so as entradas dos ultimos `dias` dias.

    As chaves tem o formato 'YYYY-MM-DD|...'. Entradas mais antigas que a
    janela (e chaves sem data valida, como formatos legados) sao descartadas,
    evitando que o arquivo de estado cresca indefinidamente.
    """
    limite = (datetime.now(_TZ_BR).date() - timedelta(days=dias)).isoformat()
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


# ---------------------------------------------------------------------------
# ESTADO EM ARQUIVO (path explicito)
# ---------------------------------------------------------------------------
def carregar(arquivo: Path, dias: int, *, persistir_poda: bool) -> dict:
    """Le o estado do arquivo e poda as entradas antigas. Se persistir_poda e a
    poda mudou algo, regrava o arquivo ja podado (comportamento do ML; a Shopee
    poda em memoria mas nao regrava)."""
    estado = ler_json(arquivo)
    limpo = limpar_antigo(estado, dias)
    if persistir_poda and len(limpo) != len(estado):
        gravar_json(arquivo, limpo)
    return limpo


def salvar(arquivo: Path, estado: dict) -> None:
    gravar_json(arquivo, estado)


def marcar_impresso(ler, salvar_fn, estado: dict, grupo, ids=None, *,
                    arquivo: Path | None = None) -> None:
    """Marca como impressos os ids informados (ou todos do grupo), acumulando
    com os ja registrados no dia.

    Antes de gravar, RECARREGA o estado do disco e mescla (uniao). Assim, se a
    tela e o bot estiverem rodando ao mesmo tempo na mesma conta, a marcacao de
    um nao apaga a do outro feita nesse meio-tempo (last-writer-merge em vez de
    last-writer-wins). O dict em memoria do chamador tambem e atualizado para o
    render seguinte refletir o que foi gravado.

    `arquivo` (quando informado) liga a TRAVA ENTRE PROCESSOS em volta do ciclo
    inteiro ler -> mesclar -> salvar (ver trava()): sem ela, duas leituras
    simultaneas calculam merges diferentes da mesma versao antiga e a ultima
    gravacao vence (o merge sozinho so cobre o caso sequencial). O nucleo e o
    shopee_api passam o seu ARQUIVO_ESTADO.

    `ler`/`salvar_fn` sao injetados pelo chamador (o nucleo e o shopee_api passam a
    leitura crua e o seu proprio salvar_estado). Isso mantem a gravacao passando
    pela funcao de modulo de cada marketplace — que os testes interceptam — em vez
    de escrever direto no arquivo."""
    ids = grupo.shipment_ids if ids is None else ids
    chave = chave_estado(grupo)

    def _ciclo() -> None:
        disco = ler()
        imp = impressos(estado, grupo)          # o que ja sabiamos em memoria
        imp.update(impressos(disco, grupo))     # + o que outro processo gravou
        imp.update(ids)                         # + os recem-impressos
        ordenados = sorted(imp)
        disco[chave] = ordenados                # grava por cima do disco atual
        salvar_fn(disco)
        estado[chave] = ordenados               # reflete na memoria do chamador

    if arquivo is not None:
        with trava(Path(arquivo)):
            _ciclo()
    else:
        _ciclo()
