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
import re
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


def _natural_key(texto: str) -> list:
    """Chave de ordenacao natural: 'A2' antes de 'A10' (nao alfabetica pura)."""
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", str(texto))]


def _ordenador(ordem: list | None):
    """Devolve uma funcao-chave que ordena itens pela ordem da aba Nomes (posicao
    do SKU em `ordem`); SKU fora da lista vai pro fim, em ordem natural pelo nome
    (mesma filosofia de `core.ordenar_grupos`)."""
    pos = {sku: i for i, sku in enumerate(ordem or [])}
    fim = len(ordem or [])
    return lambda item: (pos.get(item["chave"], fim), _natural_key(item["nome"]))


def resumo_do_dia(arquivo, data: str | None = None, ordem: list | None = None) -> dict:
    """Agrega os eventos de UMA data (default hoje, Brasilia).

    `ordem` (opcional): lista de SKUs na ordem da aba Nomes; quando passada, os
    itens (de cada secao E do consolidado) seguem essa ordem. Sem ela, ordem
    natural pelo nome.

    Retorna: {data, secoes: [{marketplace, conta, itens: [{chave, nome, qtd,
    pedidos, unidades}], pedidos, unidades}], consolidado: [{chave, nome,
    pedidos, unidades}], total_pedidos, total_unidades}. `pedidos` = numero de
    etiquetas (1 por pedido); `unidades` = pedidos * qtd por pedido."""
    data = data or _hoje_br()
    registros = [r for r in _ler(Path(arquivo))
                 if isinstance(r, dict) and r.get("data") == data]
    ordenar = _ordenador(ordem)

    # Agrupa por (marketplace, conta) e, dentro, por (chave, nome, qtd).
    secoes: dict = {}
    # Consolidado por SKU (chave), somando TUDO (todas as contas ML + Shopee) —
    # e a lista de "soma por produto" da impressao.
    consol: dict = {}
    for r in registros:
        chave_sec = (r.get("marketplace", ""), r.get("conta", "") or "")
        chave = r.get("chave", "")
        nome = r.get("nome", "") or chave
        qtd = int(r.get("qtd", 1) or 1)
        etiquetas = int(r.get("etiquetas", 0) or 0)
        sec = secoes.setdefault(chave_sec, {})
        acc = sec.setdefault((chave, nome, qtd), 0)
        sec[(chave, nome, qtd)] = acc + etiquetas
        c = consol.setdefault(chave, {"chave": chave, "nome": nome,
                                      "pedidos": 0, "unidades": 0})
        # prefere um nome amigavel (diferente do proprio SKU) se aparecer
        if c["nome"] == chave and nome != chave:
            c["nome"] = nome
        c["pedidos"] += etiquetas
        c["unidades"] += etiquetas * qtd

    saida_secoes = []
    total_pedidos = total_unidades = 0
    for (marketplace, conta), itens in secoes.items():
        lista = []
        sec_pedidos = sec_unidades = 0
        for (chave, nome, qtd), pedidos in itens.items():
            unidades = pedidos * qtd
            lista.append({"chave": chave, "nome": nome or chave, "qtd": qtd,
                          "pedidos": pedidos, "unidades": unidades})
            sec_pedidos += pedidos
            sec_unidades += unidades
        lista.sort(key=ordenar)
        saida_secoes.append({
            "marketplace": marketplace, "conta": conta, "itens": lista,
            "pedidos": sec_pedidos, "unidades": sec_unidades,
        })
        total_pedidos += sec_pedidos
        total_unidades += sec_unidades

    saida_secoes.sort(key=lambda s: (s["marketplace"], s["conta"]))
    consolidado = sorted(consol.values(), key=ordenar)
    return {"data": data, "secoes": saida_secoes, "consolidado": consolidado,
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


def _nome_sem_sku(chave: str, nome: str) -> str:
    """Remove o SKU do inicio do nome quando ele ja vem embutido — o rotulo do
    grupo no ML e `f"{sku} — {amigavel}"` (aplicar_nomes), entao sem isso o
    consolidado repetiria o SKU ('A01 - A01 — 2L 110'). Cobre os separadores
    usados (travessao, hifen, dois-pontos)."""
    for sep in (" — ", " – ", " - ", ": "):
        if nome.startswith(f"{chave}{sep}"):
            return nome[len(chave) + len(sep):].strip()
    return nome


def linhas_consolidado(resumo: dict) -> list:
    """Linhas da 'soma por produto' para a impressao: uma por SKU (todas as contas
    ML + Shopee somadas), no formato 'SKU - nome - unidades'. Ordem = a de `resumo`
    (aba Nomes quando `resumo_do_dia` recebeu `ordem`)."""
    linhas = []
    for item in resumo.get("consolidado", []):
        chave, nome, un = item["chave"], item["nome"], item["unidades"]
        amigavel = _nome_sem_sku(chave, nome) if nome else ""
        rotulo = f"{chave} - {amigavel}" if amigavel and amigavel != chave else str(chave)
        linhas.append(f"{rotulo} - {un}")
    return linhas


# ---------------------------------------------------------------------------
# PDF (Python puro, sem dependencia externa) — texto simples, fonte Helvetica.
# ---------------------------------------------------------------------------
def _pdf_escape(texto: str) -> str:
    return texto.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def gerar_pdf(caminho, titulo: str, linhas: list, *, tamanho: int = 11,
              titulo_tam: int = 15) -> None:
    """Gera um PDF A4 de texto (titulo + lista de linhas), paginando sozinho.

    Compacto de proposito (fonte pequena, sem margens gordas) — o alvo e a
    impressora comum e nao desperdicar folha. Sem biblioteca externa: emite o PDF
    na mao (Helvetica embutida, WinAnsiEncoding para acentos)."""
    larg, alt, margem = 595, 842, 40           # A4 em pontos
    leading = tamanho + 4
    util = alt - 2 * margem - (titulo_tam + 12)
    por_pag = max(1, int(util // leading))
    paginas = [linhas[i:i + por_pag] for i in range(0, len(linhas), por_pag)] or [[]]

    objetos: dict = {}
    objetos[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objetos[3] = (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                  b"/Encoding /WinAnsiEncoding >>")
    proximo = 4
    kids = []
    for idx, pag in enumerate(paginas):
        content_id, page_id = proximo, proximo + 1
        proximo += 2
        ct = ["BT"]
        if idx == 0:
            ct += [f"/F1 {titulo_tam} Tf",
                   f"1 0 0 1 {margem} {alt - margem - titulo_tam} Tm",
                   f"({_pdf_escape(titulo)}) Tj"]
            y0 = alt - margem - titulo_tam - 12 - tamanho
        else:
            y0 = alt - margem - tamanho
        ct += [f"/F1 {tamanho} Tf", f"{leading} TL", f"1 0 0 1 {margem} {y0} Tm"]
        for i, ln in enumerate(pag):
            ct.append(f"({_pdf_escape(ln)}) Tj" if i == 0
                      else f"T* ({_pdf_escape(ln)}) Tj")
        ct.append("ET")
        stream = "\n".join(ct).encode("cp1252", "replace")
        objetos[content_id] = (b"<< /Length " + str(len(stream)).encode()
                               + b" >>\nstream\n" + stream + b"\nendstream")
        objetos[page_id] = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] "
            "/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>"
            % (larg, alt, content_id)).encode()
        kids.append(page_id)
    objetos[2] = ("<< /Type /Pages /Count %d /Kids [%s] >>"
                  % (len(kids), " ".join(f"{k} 0 R" for k in kids))).encode()

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict = {}
    for num in sorted(objetos):
        offsets[num] = len(out)
        out += ("%d 0 obj\n" % num).encode() + objetos[num] + b"\nendobj\n"
    xref_pos = len(out)
    total = max(objetos) + 1
    out += ("xref\n0 %d\n" % total).encode() + b"0000000000 65535 f \n"
    for num in range(1, total):
        out += (("%010d 00000 n \n" % offsets[num]).encode() if num in offsets
                else b"0000000000 65535 f \n")
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (total, xref_pos)).encode()
    Path(caminho).write_bytes(bytes(out))
