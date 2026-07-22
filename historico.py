"""Historico de impressao (registro por dia-de-acao) + resumo diario.

Um LOG separado do estado de "ja impresso" (`estado.py`). Enquanto o estado
namespaceia por **dia de despacho** e NAO guarda quando a etiqueta saiu, este
modulo grava, no momento da marcacao confirmada, O QUE foi impresso e QUANDO
(carimbo de tempo de Brasilia) — para responder "o que eu imprimi hoje" e manter
um pequeno historico.

Invariantes:
- **Nunca interfere no estado nem na impressao.** A gravacao e best-effort: uma
  falha aqui JAMAIS levanta (mesma filosofia do `_log_tempos`); a marcacao ja foi
  feita quando chegamos aqui.
- **Arquivo local, unico por maquina** (ML de todas as contas + Shopee no mesmo
  arquivo), gitignorado — recriado na operacao, nao versionado.
- Poda por idade (`DIAS_HISTORICO`) para nao crescer sem limite.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import estado as _estado

_TZ_BR = timezone(timedelta(hours=-3))
# Quantos dias de historico manter no arquivo (o resumo do dia so olha hoje, mas
# guardar ~2 meses permite consultar dias anteriores sem deixar o arquivo crescer).
DIAS_HISTORICO = 60


def _hoje_br() -> str:
    return datetime.now(_TZ_BR).date().isoformat()


def _ler(arquivo: Path) -> list:
    """Le a lista de eventos. Ausente/ilegivel -> []. Aqui silenciar corrupcao
    como [] e aceitavel (o historico e secundario; perder eventos antigos nao
    destroi nada recuperavel, ao contrario do estado — por isso nao usa o
    `ler_estado`/.corrupto)."""
    if not arquivo.exists():
        return []
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return []
    return dados if isinstance(dados, list) else []


def _podar(registros: list, dias: int, hoje: str | None = None) -> list:
    """Mantem so eventos dos ultimos `dias` (pela data de acao)."""
    hoje_d = datetime.fromisoformat(hoje).date() if hoje else datetime.now(_TZ_BR).date()
    limite = (hoje_d - timedelta(days=dias)).isoformat()
    return [r for r in registros
            if isinstance(r, dict) and str(r.get("data", "")) >= limite]


def registrar(arquivo, *, marketplace: str, conta: str, grupo, ids,
              agora: datetime | None = None) -> None:
    """Anexa UM evento de impressao (os `ids` recem-marcados do grupo).

    Best-effort: NUNCA levanta. Ciclo ler->anexar->podar->gravar sob a trava
    entre processos (`estado.trava`), como o estado, para GUI e bot na mesma
    maquina nao perderem eventos concorrentes."""
    try:
        ids = [str(i) for i in (ids or [])]
        if not ids:
            return
        agora = agora or datetime.now(_TZ_BR)
        entrada = {
            "ts": agora.isoformat(timespec="seconds"),
            "data": agora.date().isoformat(),
            "marketplace": marketplace,
            "conta": conta or "",
            "dia_despacho": (getattr(grupo, "dia", "") or ""),
            "chave": getattr(grupo, "chave", ""),
            "nome": (getattr(grupo, "nome", "") or getattr(grupo, "chave", "")),
            "qtd": int(getattr(grupo, "quantidade", 1) or 1),
            "etiquetas": len(ids),
            "ids": ids,
        }
        caminho = Path(arquivo)
        with _estado.trava(caminho):
            registros = _ler(caminho)
            registros.append(entrada)
            _estado.gravar_json(caminho, _podar(registros, DIAS_HISTORICO,
                                                entrada["data"]))
    except Exception:
        # Historico e secundario; jamais atrapalha a impressao/marcacao.
        pass


def resumo_do_dia(arquivo, data: str | None = None) -> dict:
    """Agrega os eventos de UMA data (default hoje, Brasilia).

    Retorna: {data, secoes: [{marketplace, conta, itens: [{nome, qtd, pedidos,
    unidades}], pedidos, unidades}], total_pedidos, total_unidades}. `pedidos` =
    numero de etiquetas (1 por pedido); `unidades` = pedidos * qtd por pedido."""
    data = data or _hoje_br()
    registros = [r for r in _ler(Path(arquivo))
                 if isinstance(r, dict) and r.get("data") == data]

    # Agrupa por (marketplace, conta) e, dentro, por (chave, nome, qtd).
    secoes: dict = {}
    for r in registros:
        chave_sec = (r.get("marketplace", ""), r.get("conta", "") or "")
        item_key = (r.get("chave", ""), r.get("nome", ""), int(r.get("qtd", 1) or 1))
        sec = secoes.setdefault(chave_sec, {})
        acc = sec.setdefault(item_key, 0)
        sec[item_key] = acc + int(r.get("etiquetas", 0) or 0)

    saida_secoes = []
    total_pedidos = total_unidades = 0
    for (marketplace, conta), itens in secoes.items():
        lista = []
        sec_pedidos = sec_unidades = 0
        for (chave, nome, qtd), pedidos in itens.items():
            unidades = pedidos * qtd
            lista.append({"nome": nome or chave, "qtd": qtd,
                          "pedidos": pedidos, "unidades": unidades})
            sec_pedidos += pedidos
            sec_unidades += unidades
        lista.sort(key=lambda i: i["nome"].lower())
        saida_secoes.append({
            "marketplace": marketplace, "conta": conta, "itens": lista,
            "pedidos": sec_pedidos, "unidades": sec_unidades,
        })
        total_pedidos += sec_pedidos
        total_unidades += sec_unidades

    saida_secoes.sort(key=lambda s: (s["marketplace"], s["conta"]))
    return {"data": data, "secoes": saida_secoes,
            "total_pedidos": total_pedidos, "total_unidades": total_unidades}


def _br(data_iso: str) -> str:
    """AAAA-MM-DD -> DD/MM/AAAA (best-effort)."""
    try:
        return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y")
    except ValueError:
        return data_iso


def formatar_resumo(resumo: dict, *, largura: int = 40) -> str:
    """Monta o texto do resumo (para a tela e para o .txt). Puro/testavel."""
    linhas = [f"Resumo de impressao - {_br(resumo.get('data', ''))}", ""]
    if not resumo.get("secoes"):
        linhas.append("Nada impresso neste dia.")
        return "\n".join(linhas)

    for sec in resumo["secoes"]:
        titulo = sec["marketplace"]
        if sec["conta"]:
            titulo += f" ({sec['conta']})"
        linhas.append(titulo)
        for item in sec["itens"]:
            nome = item["nome"]
            if item["qtd"] > 1:
                nome += f" ({item['qtd']}x)"
            num = str(item["pedidos"])
            pontos = max(3, largura - len(nome) - len(num))
            linhas.append(f"  {nome} {'.' * pontos} {num}")
        linhas.append("")

    linhas.append(f"Total: {resumo['total_pedidos']} etiquetas "
                  f"/ {resumo['total_unidades']} unidades")
    return "\n".join(linhas)
