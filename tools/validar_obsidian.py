#!/usr/bin/env python3
"""Validador do cofre Obsidian (`obsidian/`).

Checa os Markdown do cofre sem depender do Obsidian: links internos resolvem,
frontmatter mínimo válido, nenhum arquivo vazio, sem colisão de nome por caixa,
referências de `source_files`/`source_docs` existem e nenhum segredo real vazou.

- Só biblioteca padrão (roda em Python 3.11 e 3.12, Linux e Windows, UTF-8).
- Determinístico: a saída é ordenada.
- Sai com código != 0 quando encontra um problema REAL em arquivo rastreado.

Uso:
    python tools/validar_obsidian.py [--root obsidian] [--repo-root .]
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# Taxonomia aceita no frontmatter (ver obsidian/README.md e a seção de metadados).
# ---------------------------------------------------------------------------
TIPOS_VALIDOS = {
    "hub", "concept", "module", "feature", "decision", "incident", "runbook",
    "marketplace", "integration", "project-state", "reference", "glossary",
}
STATUS_VALIDOS = {
    "current", "historical", "planned", "research", "deprecated", "needs-verification",
}

# Pastas locais do Obsidian que NÃO são conteúdo (não versionadas de verdade).
DIRS_IGNORADOS = {".obsidian", ".trash", ".git"}


def _nfc(texto: str) -> str:
    return unicodedata.normalize("NFC", texto)


# ---------------------------------------------------------------------------
# Frontmatter (parser mínimo — sem dependência de YAML)
# ---------------------------------------------------------------------------
def separar_frontmatter(texto: str) -> tuple[dict, str]:
    """Devolve (frontmatter_dict, corpo). Suporta escalares, listas inline
    `[a, b]` e listas em bloco (`- item`). Chaves desconhecidas são mantidas."""
    if not texto.startswith("---"):
        return {}, texto
    linhas = texto.splitlines()
    fim = None
    for i in range(1, len(linhas)):
        if linhas[i].strip() == "---":
            fim = i
            break
    if fim is None:
        return {}, texto
    fm: dict = {}
    chave_lista = None
    for linha in linhas[1:fim]:
        if re.match(r"^\s*-\s+", linha) and chave_lista:
            fm[chave_lista].append(_desaspar(linha.split("-", 1)[1].strip()))
            continue
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", linha)
        if not m:
            continue
        chave, valor = m.group(1), m.group(2).strip()
        if valor == "":
            fm[chave] = []
            chave_lista = chave
        elif valor.startswith("[") and valor.endswith("]"):
            itens = [x.strip() for x in valor[1:-1].split(",") if x.strip()]
            fm[chave] = [_desaspar(x) for x in itens]
            chave_lista = None
        else:
            fm[chave] = _desaspar(valor)
            chave_lista = None
    corpo = "\n".join(linhas[fim + 1:])
    return fm, corpo


def _desaspar(v: str) -> str:
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


# ---------------------------------------------------------------------------
# Remoção de código (para não achar link/segredo dentro de exemplo de código)
# ---------------------------------------------------------------------------
_FENCE = re.compile(r"^\s*(```|~~~)")


def sem_codigo(corpo: str) -> str:
    """Remove blocos de código cercados e código inline (`...`)."""
    saida = []
    dentro = False
    for linha in corpo.splitlines():
        if _FENCE.match(linha):
            dentro = not dentro
            continue
        if dentro:
            continue
        saida.append(re.sub(r"`[^`]*`", "", linha))
    return "\n".join(saida)


# ---------------------------------------------------------------------------
# Links wiki
# ---------------------------------------------------------------------------
_WIKILINK = re.compile(r"!?\[\[([^\]]+)\]\]")


def alvos_de_link(corpo: str) -> list[str]:
    """Nomes-alvo de cada wikilink (sem alias, sem seção). `[[#Seção]]` (mesma
    nota) e embeds `![[...]]` incluídos."""
    alvos = []
    for bruto in _WIKILINK.findall(sem_codigo(corpo)):
        alvo = bruto.split("|", 1)[0]          # tira alias
        alvo = alvo.split("#", 1)[0]           # tira seção
        alvos.append(_nfc(alvo.strip()))
    return alvos


# ---------------------------------------------------------------------------
# Segredos
# ---------------------------------------------------------------------------
_CAMPOS_SENSIVEIS = (
    r"access_token|refresh_token|client_secret|partner_key|api[_-]?key|secret|"
    r"password|senha|authorization|bearer|sign|token|code|cookie"
)
_ATRIBUICAO = re.compile(
    r"(?i)\b(" + _CAMPOS_SENSIVEIS + r")\b\s*[:=]\s*[\"']?([^\s\"',}]+)")
_FORMAS_FORTES = [
    re.compile(r"APP_USR-[0-9A-Za-z]{6,}-[0-9A-Za-z]{4,}"),   # token ML
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),         # chave privada
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),  # JWT
    re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{30,}\b"),              # token de bot Telegram
]
_PLACEHOLDER = re.compile(
    r"(?i)^(seu_.*|.*_exemplo|.*_ficticio|.*_fake|.*_aqui|exemplo|fake|"
    r"placeholder|x{3,}|todo|change_?me|\.\.\.|<.+>|none|null|nan)$")


def _valor_e_segredo(valor: str) -> bool:
    v = valor.strip().strip("\"'")
    if len(v) < 16:
        return False
    if _PLACEHOLDER.match(v):
        return False
    # ALL_CAPS_COM_UNDERSCORE = nome de variável/ambiente ou placeholder, não valor.
    if re.fullmatch(r"[A-Z0-9_]+", v):
        return False
    # precisa parecer credencial: charset restrito e com mistura de classes.
    if not re.fullmatch(r"[A-Za-z0-9+/=_.\-]{16,}", v):
        return False
    classes = sum(bool(re.search(p, v)) for p in (r"[a-z]", r"[A-Z]", r"[0-9]"))
    return classes >= 2


def achar_segredos(corpo: str) -> list[str]:
    """Retorna descrições de possíveis segredos REAIS (valores), nunca a menção
    ao nome de um campo. Valor completo NÃO é ecoado (só um trecho mascarado)."""
    achados = []
    texto = sem_codigo(corpo)
    for rx in _FORMAS_FORTES:
        if rx.search(texto):
            achados.append(f"formato de credencial detectado ({rx.pattern[:24]}...)")
    for m in _ATRIBUICAO.finditer(texto):
        campo, valor = m.group(1), m.group(2)
        if _valor_e_segredo(valor):
            achados.append(f"'{campo}' com valor de alta entropia "
                           f"(mascarado: {valor[:4]}...{valor[-2:]})")
    return sorted(set(achados))


# ---------------------------------------------------------------------------
# Coleta do cofre
# ---------------------------------------------------------------------------
class Nota:
    def __init__(self, caminho: Path, raiz: Path) -> None:
        self.caminho = caminho
        self.rel = caminho.relative_to(raiz).as_posix()
        self.basename = _nfc(caminho.stem)
        self.texto = caminho.read_text(encoding="utf-8")
        self.fm, self.corpo = separar_frontmatter(self.texto)
        self.aliases = [_nfc(a) for a in _lista(self.fm.get("aliases"))]


def _lista(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def coletar_notas(raiz: Path) -> list[Nota]:
    notas = []
    for p in sorted(raiz.rglob("*.md")):
        if any(parte in DIRS_IGNORADOS for parte in p.relative_to(raiz).parts):
            continue
        notas.append(Nota(p, raiz))
    return notas


# ---------------------------------------------------------------------------
# Validações
# ---------------------------------------------------------------------------
def validar(raiz: Path, repo_root: Path) -> list[str]:
    notas = coletar_notas(raiz)
    erros: list[str] = []

    # índices para resolução de link (case-insensitive, NFC)
    por_base: dict[str, list[Nota]] = {}
    por_rel: dict[str, Nota] = {}
    por_alias: dict[str, list[Nota]] = {}
    por_casefold_rel: dict[str, list[str]] = {}
    por_casefold_base: dict[str, set[str]] = {}
    for n in notas:
        por_base.setdefault(n.basename.casefold(), []).append(n)
        por_rel[_nfc(n.rel[:-3]).casefold()] = n           # sem .md
        for a in n.aliases:
            por_alias.setdefault(a.casefold(), []).append(n)
        por_casefold_rel.setdefault(_nfc(n.rel).casefold(), []).append(n.rel)
        por_casefold_base.setdefault(n.basename.casefold(), set()).add(n.basename)

    # 1) colisão de caminho por caixa (perigo em FS sem diferenciação)
    for chave, rels in sorted(por_casefold_rel.items()):
        if len(rels) > 1:
            erros.append(f"[colisao-caixa] caminhos colidem ignorando caixa: {sorted(rels)}")
    # 2) basename ambíguo (torna [[nome]] ambíguo)
    for chave, bases in sorted(por_casefold_base.items()):
        arquivos = [n.rel for n in por_base[chave]]
        if len(arquivos) > 1:
            erros.append(f"[nome-ambiguo] '{chave}' aparece em vários arquivos: "
                         f"{sorted(arquivos)}")

    for n in notas:
        # 3) vazio (sem corpo além do frontmatter)
        if n.corpo.strip() == "":
            erros.append(f"[vazio] {n.rel}: sem conteúdo além do frontmatter")

        # 4) frontmatter mínimo
        tipo = n.fm.get("type")
        if not tipo:
            erros.append(f"[frontmatter] {n.rel}: falta 'type'")
        elif tipo not in TIPOS_VALIDOS:
            erros.append(f"[frontmatter] {n.rel}: type '{tipo}' inválido "
                         f"(use um de {sorted(TIPOS_VALIDOS)})")
        status = n.fm.get("status")
        if status is not None and status not in STATUS_VALIDOS:
            erros.append(f"[frontmatter] {n.rel}: status '{status}' inválido "
                         f"(use um de {sorted(STATUS_VALIDOS)})")
        vac = n.fm.get("verified_at_commit")
        if vac is not None and not re.fullmatch(r"[0-9a-f]{7,40}", str(vac)):
            erros.append(f"[frontmatter] {n.rel}: verified_at_commit '{vac}' "
                         f"não parece um hash git")

        # 5) referências declaradas existem no repositório
        for campo in ("source_files", "source_docs"):
            for ref in _lista(n.fm.get(campo)):
                if not (repo_root / ref).exists():
                    erros.append(f"[fonte] {n.rel}: {campo} aponta para "
                                 f"'{ref}' que não existe no repositório")

        # 6) links internos resolvem
        for alvo in alvos_de_link(n.corpo):
            if alvo == "":                       # [[#Secao]] = mesma nota
                continue
            chave = alvo.casefold()
            if "/" in alvo:
                if _nfc(alvo).casefold() in por_rel:
                    continue
            if chave in por_base or chave in por_alias:
                continue
            erros.append(f"[link] {n.rel}: link '[[{alvo}]]' não resolve")

        # 7) segredos
        for s in achar_segredos(n.corpo):
            erros.append(f"[segredo] {n.rel}: {s}")

    return sorted(set(erros))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Valida o cofre Obsidian.")
    ap.add_argument("--root", default="obsidian", help="pasta do cofre")
    ap.add_argument("--repo-root", default=None,
                    help="raiz do repositório (default: pai de --root)")
    args = ap.parse_args(argv)

    raiz = Path(args.root).resolve()
    if not raiz.is_dir():
        print(f"ERRO: pasta '{raiz}' não existe", file=sys.stderr)
        return 2
    repo_root = Path(args.repo_root).resolve() if args.repo_root else raiz.parent

    erros = validar(raiz, repo_root)
    if erros:
        print(f"Validação do cofre: {len(erros)} problema(s) em '{raiz.name}':")
        for e in erros:
            print(f"  {e}")
        return 1
    total = len(coletar_notas(raiz))
    print(f"Validação do cofre OK: {total} notas, 0 problema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
