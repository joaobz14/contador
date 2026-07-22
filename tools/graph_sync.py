#!/usr/bin/env python3
"""Sincronizador seguro do grafo Graphify (`graphify-out/graph.json`).

Problema que resolve
--------------------
O `graph.json` mistura **duas camadas**:

* **AST** (derivada do codigo): nos de arquivos/classes/funcoes/metodos e as
  arestas estruturais (`contains`, `method`, `inherits`, `imports`,
  `imports_from`) + a topologia de `calls`.
* **Semantica** (mantida a mao): nos `rationale`/`concept`/`document`/`image`
  e as arestas de conhecimento (`rationale_for`, `conceptually_related_to`,
  `shares_data_with`), alem de arestas marcadas `MANUAL`.

O CLI `graphify` nao roda neste ambiente e um `graphify hook install`
reconstruiria SO a camada AST, apagando a camada semantica (ver `CLAUDE.md`).
Este utilitario faz o oposto: **re-deriva a camada estrutural do codigo atual e
reconcilia o resto preservando integralmente a camada semantica**, com IDs
estaveis para nao orfaozar as arestas manuais.

O que ele (re)faz
------------------
1. **Estrutural (regenerado do AST):** `contains`, `method`, `inherits`,
   `imports`, `imports_from` entre nos de codigo (exceto arestas `MANUAL`).
2. **`calls`/`references`/`indirect_call` (reconciliado, NAO reconstruido):**
   mantem as arestas cujos dois extremos sobrevivem, descarta as penduradas e
   adiciona apenas chamadas diretas `Nome()` do MESMO modulo para nos novos
   (baixissimo falso-positivo — chamadas por atributo/`.get()` sao ignoradas de
   proposito porque poluiriam o grafo; medido em `--measure`).
3. **Localizacoes (`source_location`)** de todo simbolo de codigo.
4. **Inventario de nos:** adiciona simbolos novos, remove nos AST obsoletos
   (simbolo/arquivo sumiu) e **preserva** aliases/re-exports e globais que o
   parser estrutural nao enxerga mas continuam existindo no arquivo.
5. **Camada semantica:** preservada verbatim. Arestas manuais penduradas
   (apontando para um simbolo removido) sao **reconectadas** ao no do modulo de
   origem (best-effort) e **reportadas** — nunca apagadas em silencio.

Uso
---
    python tools/graph_sync.py --check     # so detecta defasagem (exit!=0 se houver)
    python tools/graph_sync.py --update    # aplica e grava graph.json atomico
    python tools/graph_sync.py --validate  # so valida o graph.json atual
    python tools/graph_sync.py --measure    # calibra o extrator de calls vs o snapshot

Regras de seguranca
-------------------
* Nunca sobrescreve `graph.json` sem passar por `validate()`.
* Grava de forma atomica (`.tmp` + `os.replace`).
* Emite tambem `graphify-out/semantic.json`: um extrato duravel e revisavel da
  camada semantica (o "backup" que garante que um rebuild futuro do CLI possa
  re-mesclar o conhecimento manual). Corrige a causa-raiz: a camada manual deixa
  de viver so dentro de um monolito de ~900 KB.
* NAO instala hooks. NAO chama o CLI. NAO toca em credenciais/estado/caches.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH = os.path.join(REPO, "graphify-out", "graph.json")
SEMANTIC = os.path.join(REPO, "graphify-out", "semantic.json")
MANIFEST = os.path.join(REPO, "graphify-out", "manifest.json")
# Extensoes que o manifesto acompanha (mesmas categorias do build original).
MANIFEST_EXTS = (".py", ".sh", ".toml", ".json", ".txt", ".yml", ".yaml", ".md", ".png")

# Relacoes estruturais re-derivadas do AST (quando EXTRACTED, entre nos de codigo).
STRUCTURAL_RELS = {"contains", "method", "inherits", "imports", "imports_from"}
# Subconjunto que o extrator realmente reconstroi do zero. `imports_from`
# (from X import simbolo) fica de FORA: e preservado/reconciliado como as demais,
# porque o extrator so emite `imports` a nivel de modulo — regenerar apagaria os
# `imports_from` existentes sem repo-los.
REGEN_STRUCTURAL = {"contains", "method", "inherits", "imports"}
# Relacoes de chamada: reconciliadas (preserva + remenda), nunca reconstruidas do zero.
CALLISH_RELS = {"calls", "references", "indirect_call"}
# Relacoes puramente semanticas: preservadas verbatim.
SEMANTIC_RELS = {"rationale_for", "conceptually_related_to", "shares_data_with"}
VALID_RELS = STRUCTURAL_RELS | CALLISH_RELS | SEMANTIC_RELS

CODE_FILE_TYPES = {"code"}
SEMANTIC_FILE_TYPES = {"rationale", "concept", "document", "image"}


# --------------------------------------------------------------------------- #
# Utilidades                                                                    #
# --------------------------------------------------------------------------- #
def git_files(pattern: str) -> list[str]:
    out = subprocess.check_output(["git", "-C", REPO, "ls-files", pattern]).decode()
    return [f for f in out.splitlines() if f]


def versioned_set() -> set[str]:
    out = subprocess.check_output(["git", "-C", REPO, "ls-files"]).decode()
    return {f for f in out.splitlines() if f}


def module_id(source_file: str) -> str:
    p = source_file[1:] if source_file.startswith(".") else source_file
    p = re.sub(r"\.(py|sh|toml|json|md|yml|yaml)$", "", p)
    return re.sub(r"[^a-zA-Z0-9]+", "_", p).strip("_").lower()


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _loc_num(loc) -> int:
    m = re.match(r"L(\d+)", str(loc or ""))
    return int(m.group(1)) if m else 0


def canonical_links(links: list) -> list:
    """Ordena as arestas de forma deterministica (idempotencia + diffs limpos)."""
    return sorted(links, key=lambda l: (l.get("relation", ""), l["source"],
                                        l["target"], _loc_num(l.get("source_location"))))


def dump_atomic(path: str, data) -> None:
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Extracao AST                                                                  #
# --------------------------------------------------------------------------- #
@dataclass
class Symbol:
    id: str            # id canonico (pode ser trocado por um existente na fase de match)
    kind: str          # file | class | function | method
    name: str          # nome do simbolo (leaf)
    qual: str          # qualificado: "Classe.metodo" ou "funcao" ou nome do modulo
    source_file: str
    line: int
    module_id: str
    parent_id: str | None = None   # id do container (arquivo p/ func/classe; classe p/ metodo)
    bases: list[str] = field(default_factory=list)  # nomes de bases (p/ inherits)


@dataclass
class ParsedModule:
    source_file: str
    module_id: str
    symbols: list[Symbol]
    imports: list[str]            # nomes de modulos importados (top-level)
    calls: list[tuple[str, str, int, bool]]  # (caller_id, callee_name, line, is_attr)


def gen_symbol_id(mid: str, kind: str, name: str, class_name: str | None = None) -> str:
    if kind == "file":
        return mid
    if kind == "class":
        return f"{mid}_{name.lower().strip('_') or 'cls'}"
    if kind == "function":
        return f"{mid}_{name.strip('_') or 'fn'}"
    if kind == "method":
        cid = f"{mid}_{(class_name or '').lower().strip('_') or 'cls'}"
        return f"{cid}_{name.strip('_') or 'fn'}"
    raise ValueError(kind)


def parse_python(source_file: str) -> ParsedModule:
    src = open(os.path.join(REPO, source_file), encoding="utf-8").read()
    tree = ast.parse(src)
    mid = module_id(source_file)
    symbols: list[Symbol] = [
        Symbol(mid, "file", os.path.basename(source_file), mid, source_file, 1, mid)
    ]
    imports: list[str] = []
    calls: list[tuple[str, str, int, bool]] = []

    # nome -> ids de funcoes/metodos definidos no MODULO (p/ resolver calls same-module)
    local_defs: dict[str, list[str]] = defaultdict(list)

    def record_calls(fn_node, owner_id: str) -> None:
        for sub in ast.walk(fn_node):
            if isinstance(sub, ast.Call):
                f = sub.func
                if isinstance(f, ast.Name):
                    calls.append((owner_id, f.id, getattr(sub, "lineno", 0), False))
                elif isinstance(f, ast.Attribute):
                    calls.append((owner_id, f.attr, getattr(sub, "lineno", 0), True))

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.append(a.name.split(".")[0])
            else:
                if node.module and node.level == 0:
                    imports.append(node.module.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sid = gen_symbol_id(mid, "function", node.name)
            symbols.append(Symbol(sid, "function", node.name, node.name,
                                  source_file, node.lineno, mid, mid))
            local_defs[node.name].append(sid)
            record_calls(node, sid)
        elif isinstance(node, ast.ClassDef):
            cid = gen_symbol_id(mid, "class", node.name)
            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
            symbols.append(Symbol(cid, "class", node.name, node.name,
                                  source_file, node.lineno, mid, mid, bases=bases))
            for m in node.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    mmid = gen_symbol_id(mid, "method", m.name, node.name)
                    symbols.append(Symbol(mmid, "method", m.name,
                                          f"{node.name}.{m.name}", source_file,
                                          m.lineno, mid, cid))
                    local_defs[m.name].append(mmid)
                    record_calls(m, mmid)
    return ParsedModule(source_file, mid, symbols, imports, calls)


def parse_all() -> list[ParsedModule]:
    mods = []
    for f in git_files("*.py"):
        try:
            mods.append(parse_python(f))
        except SyntaxError as exc:  # pragma: no cover - codigo do repo deve parsear
            print(f"! erro de sintaxe em {f}: {exc}", file=sys.stderr)
    return mods


# --------------------------------------------------------------------------- #
# Reconciliacao                                                                 #
# --------------------------------------------------------------------------- #
def leaf_name(label: str) -> str:
    lbl = label.strip()
    if lbl.endswith("()"):
        lbl = lbl[:-2]
    if "." in lbl:
        lbl = lbl.rsplit(".", 1)[-1]
    return lbl


@dataclass
class SyncResult:
    nodes: list
    links: list
    hyperedges: list
    added_nodes: list
    removed_nodes: list
    relocated: list          # (id, old_loc, new_loc)
    dangling_reconnected: list
    dangling_reported: list
    dropped_edges: int


def reconcile(graph: dict, mods: list[ParsedModule]) -> SyncResult:
    existing = {n["id"]: n for n in graph["nodes"]}
    code_nodes = {i: n for i, n in existing.items() if n.get("file_type") in CODE_FILE_TYPES}
    semantic_nodes = {i: n for i, n in existing.items()
                      if n.get("file_type") in SEMANTIC_FILE_TYPES}

    # indice p/ label-fallback: (source_file) -> [(leaf, id, node)]
    by_file: dict[str, list[tuple[str, str, dict]]] = defaultdict(list)
    for i, n in code_nodes.items():
        by_file[n.get("source_file", "")].append((leaf_name(n.get("label", "")), i, n))

    parsed_ids: dict[str, Symbol] = {}   # id final -> symbol
    sym_to_id: dict[tuple[str, str], str] = {}  # (source_file, qual) -> id final
    matched_existing: set[str] = set()
    used_ids: set[str] = set(existing.keys())

    def match_symbol(sym: Symbol) -> str:
        # 1) id canonico bate um no existente do mesmo arquivo
        cand = existing.get(sym.id)
        if cand is not None and cand.get("source_file") == sym.source_file \
                and cand.get("file_type") in CODE_FILE_TYPES:
            return sym.id
        # 2) label-fallback (pega renomeacoes e IDs excecao, ex.: __com_retry)
        want_class = None
        if sym.kind == "method":
            want_class = f"{sym.module_id}_{sym.qual.split('.')[0].lower().lstrip('_')}_"
        options = [(leaf, i, n) for (leaf, i, n) in by_file.get(sym.source_file, [])
                   if leaf == sym.name and i not in matched_existing]
        if sym.kind == "method":
            options = [o for o in options if o[1].startswith(want_class)]
        if len(options) == 1:
            return options[0][1]
        # 3) novo id (dedup contra colisao)
        nid = sym.id
        n = 2
        while nid in used_ids and nid not in parsed_ids:
            nid = f"{sym.id}_{n}"
            n += 1
        return nid

    for mod in mods:
        for sym in mod.symbols:
            fid = match_symbol(sym)
            sym.id = fid
            used_ids.add(fid)
            parsed_ids[fid] = sym
            sym_to_id[(sym.source_file, sym.qual)] = fid
            if fid in existing:
                matched_existing.add(fid)

    versioned = versioned_set()

    # --- destino de cada no de codigo existente -------------------------------
    removed_ids: set[str] = set()
    preserved_ids: set[str] = set()
    for i, n in code_nodes.items():
        if i in matched_existing:
            continue
        sf = n.get("source_file", "")
        kind = (n.get("metadata") or {}).get("kind")
        if not sf:
            preserved_ids.add(i)          # simbolo externo/importado (sem arquivo): alvo de reference/call
            continue
        if kind in ("global", "bash_entrypoint"):
            preserved_ids.add(i)          # binding de modulo/entrypoint fora do parser estrutural
            continue
        if sf and sf not in versioned:
            removed_ids.add(i)
            continue
        if sf and not sf.endswith(".py"):
            preserved_ids.add(i)          # arquivos bash/toml: fora do parser Python
            continue
        # simbolo Python nao casado: alias/global/re-export? preserva se o nome
        # ainda aparece como binding textual no arquivo; senao, removido.
        leaf = leaf_name(n.get("label", ""))
        try:
            body = open(os.path.join(REPO, sf), encoding="utf-8").read() if sf else ""
        except OSError:
            body = ""
        if leaf and re.search(rf"(?m)^\s*{re.escape(leaf)}\s*=", body):
            preserved_ids.add(i)
        elif leaf and re.search(rf"(?m)^\s*(async\s+)?def\s+{re.escape(leaf)}\b", body):
            preserved_ids.add(i)          # def existe mas fugiu do match (raro)
        else:
            removed_ids.add(i)

    alive_code = set(matched_existing) | set(parsed_ids.keys()) | preserved_ids
    alive_code -= removed_ids
    alive_all = alive_code | set(semantic_nodes.keys())

    # --- montar nos -----------------------------------------------------------
    out_nodes: list = []
    added_nodes: list = []
    relocated: list = []
    module_community: dict[str, int] = {}
    next_comm = max((n.get("community", 0) for n in existing.values()), default=0) + 1
    for mod in mods:
        mnode = existing.get(mod.module_id)
        if mnode:
            module_community[mod.module_id] = mnode.get("community", 0)
        else:
            module_community[mod.module_id] = next_comm  # modulo novo: comunidade propria
            next_comm += 1

    for i, n in existing.items():
        if i in removed_ids:
            continue
        node = dict(n)
        sym = parsed_ids.get(i)
        if sym is not None:
            new_loc = f"L{sym.line}"
            if node.get("source_location") != new_loc:
                relocated.append((i, node.get("source_location"), new_loc))
                node["source_location"] = new_loc
            md = dict(node.get("metadata") or {})
            md.setdefault("language", "python")
            md.setdefault("kind", sym.kind)
            node["metadata"] = md
        out_nodes.append(node)

    for i, sym in parsed_ids.items():
        if i in existing:
            continue
        comm = module_community.get(sym.module_id, 0)
        label = (os.path.basename(sym.source_file) if sym.kind == "file"
                 else (sym.name if sym.kind == "class"
                       else (f".{sym.name}()" if sym.kind == "method" else f"{sym.name}()")))
        node = {
            "label": label,
            "file_type": "code",
            "source_file": sym.source_file,
            "source_location": f"L{sym.line}",
            "metadata": {"language": "python", "kind": sym.kind},
            "_origin": "ast",
            "id": i,
            "community": comm,
            "norm_label": label.lower(),
        }
        out_nodes.append(node)
        added_nodes.append(node)

    # --- arestas --------------------------------------------------------------
    # 1) estruturais frescas do AST
    fresh_struct: set[tuple[str, str, str]] = set()
    struct_meta: dict[tuple[str, str, str], dict] = {}

    def add_struct(src, tgt, rel, line, sf):
        key = (src, tgt, rel)
        if src in alive_all and tgt in alive_all and src != tgt:
            fresh_struct.add(key)
            struct_meta[key] = {"source_file": sf, "source_location": f"L{line}"}

    for mod in mods:
        for sym in mod.symbols:
            if sym.kind in ("function", "class") and sym.parent_id:
                add_struct(sym.parent_id, sym.id, "contains", sym.line, sym.source_file)
            elif sym.kind == "method" and sym.parent_id:
                add_struct(sym.parent_id, sym.id, "method", sym.line, sym.source_file)
            if sym.kind == "class":
                for b in sym.bases:
                    bid = sym_to_id.get((sym.source_file, b))
                    if bid:
                        add_struct(sym.id, bid, "inherits", sym.line, sym.source_file)
        # imports intra-repo
        for imp in set(mod.imports):
            if imp in {m.module_id for m in mods} or imp in existing:
                if imp in alive_all and mod.module_id in alive_all:
                    add_struct(mod.module_id, imp, "imports", 1, mod.source_file)

    # 2) preservar arestas nao-estruturais (calls/refs/semantic/MANUAL),
    #    mais estruturais MANUAL ou envolvendo nos preservados (aliases/bash).
    out_links: list = []
    seen_links: set[tuple[str, str, str]] = set()
    dangling_reconnected: list = []
    dangling_reported: list = []
    dropped = 0

    # mapa arquivo->id do no de modulo (p/ reconectar aresta manual pendurada)
    file_to_module = {m.source_file: m.module_id for m in mods}
    for i, n in code_nodes.items():
        if n.get("metadata", {}).get("kind") == "file":
            file_to_module.setdefault(n.get("source_file", ""), i)

    def endpoint_fix(node_id: str):
        """Reconecta um extremo removido ao no do seu modulo (best-effort)."""
        if node_id in alive_all:
            return node_id
        rf = existing.get(node_id, {}).get("source_file")
        mod = file_to_module.get(rf)
        if mod and mod in alive_all:
            return mod
        return None

    for link in graph["links"]:
        rel = link.get("relation")
        src, tgt = link["source"], link["target"]
        conf = link.get("confidence")
        is_struct_ast = (rel in REGEN_STRUCTURAL and conf != "MANUAL"
                         and existing.get(src, {}).get("file_type") in CODE_FILE_TYPES
                         and existing.get(tgt, {}).get("file_type") in CODE_FILE_TYPES)
        if is_struct_ast:
            # sera reconstruida — mas preserva se envolve no preservado (alias/bash)
            if src in preserved_ids or tgt in preserved_ids:
                if src in alive_all and tgt in alive_all:
                    key = (src, tgt, rel)
                    if key not in seen_links:
                        out_links.append(dict(link))
                        seen_links.add(key)
                continue
            continue  # descartada aqui; re-adicionada a partir de fresh_struct
        # nao-estrutural: preservar, remendando extremos pendurados
        nsrc, ntgt = src, tgt
        if src not in alive_all:
            fix = endpoint_fix(src)
            if fix is None:
                dropped += 1
                dangling_reported.append((rel, src, tgt, "source removido sem modulo"))
                continue
            nsrc = fix
            dangling_reconnected.append((rel, src, "->", fix, "(source)"))
        if tgt not in alive_all:
            fix = endpoint_fix(tgt)
            if fix is None:
                dropped += 1
                dangling_reported.append((rel, src, tgt, "target removido sem modulo"))
                continue
            ntgt = fix
            dangling_reconnected.append((rel, tgt, "->", fix, "(target)"))
        key = (nsrc, ntgt, rel)
        if key in seen_links or nsrc == ntgt:
            continue
        nl = dict(link)
        nl["source"], nl["target"] = nsrc, ntgt
        out_links.append(nl)
        seen_links.add(key)

    # 3) materializar estruturais frescas (sem duplicar as ja preservadas)
    for key in sorted(fresh_struct):
        if key in seen_links:
            continue
        src, tgt, rel = key
        meta = struct_meta[key]
        out_links.append({
            "relation": rel,
            "confidence": "EXTRACTED",
            "source_file": meta["source_file"],
            "source_location": meta["source_location"],
            "weight": 1.0,
            "source": src,
            "target": tgt,
            "confidence_score": 1.0,
        })
        seen_links.add(key)

    # 4) calls novas, so p/ nos novos, mesmo-modulo, chamada por Nome (baixo FP)
    new_ids = {n["id"] for n in added_nodes}
    same_mod_defs: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for mod in mods:
        for sym in mod.symbols:
            if sym.kind in ("function", "method"):
                same_mod_defs[mod.module_id][sym.name].append(sym.id)
    for mod in mods:
        for (caller, callee, line, is_attr) in mod.calls:
            if is_attr:
                continue
            tgts = same_mod_defs[mod.module_id].get(callee, [])
            if len(tgts) != 1:
                continue
            tgt = tgts[0]
            # so materializa se a aresta toca um no NOVO (nos existentes ja tem
            # sua topologia de calls preservada do snapshot)
            if caller not in new_ids and tgt not in new_ids:
                continue
            if caller == tgt or caller not in alive_all or tgt not in alive_all:
                continue
            key = (caller, tgt, "calls")
            if key in seen_links:
                continue
            out_links.append({
                "relation": "calls", "confidence": "EXTRACTED",
                "source_file": mod.source_file, "source_location": f"L{line}",
                "weight": 1.0, "source": caller, "target": tgt,
                "confidence_score": 1.0,
            })
            seen_links.add(key)

    # --- hyperedges -----------------------------------------------------------
    out_hyper = []
    for h in graph.get("hyperedges", []):
        members = [m for m in h.get("nodes", []) if m in alive_all]
        nh = dict(h)
        nh["nodes"] = members
        out_hyper.append(nh)

    removed_nodes = [existing[i] for i in sorted(removed_ids)]
    return SyncResult(out_nodes, out_links, out_hyper, added_nodes, removed_nodes,
                      relocated, dangling_reconnected, dangling_reported, dropped)


# --------------------------------------------------------------------------- #
# Validacao                                                                     #
# --------------------------------------------------------------------------- #
def validate(graph: dict) -> list[str]:
    errs: list[str] = []
    ids = [n["id"] for n in graph["nodes"]]
    idset = set(ids)
    if len(ids) != len(idset):
        dup = [i for i in idset if ids.count(i) > 1]
        errs.append(f"IDs duplicados: {dup[:10]}")
    versioned = versioned_set()
    for n in graph["nodes"]:
        sf = n.get("source_file")
        if sf and sf not in versioned and n.get("file_type") == "code":
            errs.append(f"no de codigo com source_file ausente: {n['id']} ({sf})")
    for l in graph["links"]:
        if l["source"] not in idset:
            errs.append(f"aresta orfa (source): {l['source']} -> {l['target']} [{l['relation']}]")
        if l["target"] not in idset:
            errs.append(f"aresta orfa (target): {l['source']} -> {l['target']} [{l['relation']}]")
        if l.get("relation") not in VALID_RELS:
            errs.append(f"relacao invalida: {l.get('relation')}")
    for h in graph.get("hyperedges", []):
        for m in h.get("nodes", []):
            if m not in idset:
                errs.append(f"hyperedge {h.get('id')} membro inexistente: {m}")
    # source_location coerente p/ nos de codigo com no de modulo do mesmo arquivo
    return errs


# --------------------------------------------------------------------------- #
# semantic.json (extrato duravel da camada manual)                              #
# --------------------------------------------------------------------------- #
def build_semantic_snapshot(graph: dict) -> dict:
    idmap = {n["id"]: n for n in graph["nodes"]}
    sem_nodes = [n for n in graph["nodes"]
                 if n.get("file_type") in SEMANTIC_FILE_TYPES]
    sem_ids = {n["id"] for n in sem_nodes}
    sem_edges = []
    for l in graph["links"]:
        rel, conf = l.get("relation"), l.get("confidence")
        s, t = l["source"], l["target"]
        keep = (rel in SEMANTIC_RELS or conf == "MANUAL"
                or s in sem_ids or t in sem_ids
                or (rel in CALLISH_RELS and (idmap.get(s, {}).get("file_type") in SEMANTIC_FILE_TYPES
                                             or idmap.get(t, {}).get("file_type") in SEMANTIC_FILE_TYPES)))
        if keep:
            sem_edges.append(l)
    return {
        "_comment": ("Extrato duravel da camada semantica (hand-curated) do grafo. "
                     "Gerado por tools/graph_sync.py. Serve de backup para re-mesclar "
                     "o conhecimento manual caso a camada AST seja reconstruida. "
                     "NAO editar a mao aqui — edite graph.json e rode --update."),
        "node_count": len(sem_nodes),
        "edge_count": len(sem_edges),
        "hyperedges": graph.get("hyperedges", []),
        "nodes": sem_nodes,
        "edges": canonical_links(sem_edges),
    }


# --------------------------------------------------------------------------- #
# Relatorio de drift                                                            #
# --------------------------------------------------------------------------- #
def write_manifest() -> int:
    """Regenera o manifesto com os arquivos versionados atuais.

    Os hashes sao um **sha1 do conteudo** (stand-in) — o `ast_hash`/`semantic_hash`
    proprios do CLI `graphify` so um rebuild completo re-deriva. Um hash de conteudo
    diferente apenas faz o CLI re-extrair o arquivo (conservador), nunca perde dados.
    """
    import hashlib
    manifest: dict[str, dict] = {}
    for f in sorted(versioned_set()):
        if f.startswith("graphify-out/") or not f.endswith(MANIFEST_EXTS):
            continue
        p = os.path.join(REPO, f)
        try:
            data = open(p, "rb").read()
            h = hashlib.sha1(data).hexdigest()
            manifest[f] = {"mtime": os.path.getmtime(p), "ast_hash": h,
                           "semantic_hash": h}
        except OSError:
            continue
    dump_atomic(MANIFEST, manifest)
    return len(manifest)


def report(res: SyncResult) -> None:
    print(f"  nos adicionados : {len(res.added_nodes)}")
    for n in res.added_nodes:
        print(f"      + {n['id']}  ({n['source_file']} {n['source_location']})")
    print(f"  nos removidos   : {len(res.removed_nodes)}")
    for n in res.removed_nodes:
        print(f"      - {n['id']}  ({n.get('source_file')})  label={n.get('label')!r}")
    print(f"  linhas corrigidas: {len(res.relocated)}")
    for i, old, new in res.relocated[:60]:
        print(f"      ~ {i}: {old} -> {new}")
    if len(res.relocated) > 60:
        print(f"      ... +{len(res.relocated) - 60} mais")
    print(f"  arestas manuais reconectadas: {len(res.dangling_reconnected)}")
    for rc in res.dangling_reconnected:
        print(f"      -> {rc}")
    print(f"  arestas penduradas reportadas (nao resolvidas): {len(res.dangling_reported)}")
    for rc in res.dangling_reported:
        print(f"      !! {rc}")
    print(f"  arestas descartadas (extremo removido): {res.dropped_edges}")


# --------------------------------------------------------------------------- #
# CLI                                                                           #
# --------------------------------------------------------------------------- #
def measure() -> None:
    """Calibra o extrator de calls contra o snapshot (diagnostico)."""
    graph = load_json(GRAPH)
    mods = parse_all()
    same_mod: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for mod in mods:
        for sym in mod.symbols:
            if sym.kind in ("function", "method"):
                same_mod[mod.module_id][sym.name].append(sym.id)
    mine = set()
    for mod in mods:
        for caller, callee, line, is_attr in mod.calls:
            tgts = same_mod[mod.module_id].get(callee, [])
            if len(tgts) == 1 and tgts[0] != caller:
                mine.add((caller, tgts[0]))
    existing = {(l["source"], l["target"]) for l in graph["links"]
                if l["relation"] == "calls" and l["confidence"] == "EXTRACTED"}
    print("same-module Name-calls extraidas:", len(mine))
    print("calls EXTRACTED no snapshot:", len(existing))
    print("intersecao:", len(mine & existing))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="so detecta defasagem (exit!=0)")
    g.add_argument("--update", action="store_true", help="aplica e grava graph.json")
    g.add_argument("--validate", action="store_true", help="so valida o graph.json atual")
    g.add_argument("--measure", action="store_true", help="calibra o extrator de calls")
    args = ap.parse_args()

    if args.measure:
        measure()
        return 0

    graph = load_json(GRAPH)

    if args.validate:
        errs = validate(graph)
        if errs:
            print("INVALIDO:")
            for e in errs:
                print("  -", e)
            return 1
        print(f"OK: {len(graph['nodes'])} nos, {len(graph['links'])} arestas, "
              f"{len(graph.get('hyperedges', []))} hyperedges — valido.")
        return 0

    mods = parse_all()
    res = reconcile(graph, mods)

    drift = bool(res.added_nodes or res.removed_nodes or res.relocated
                 or res.dangling_reported)

    if args.check:
        print("== graph_sync --check ==")
        report(res)
        old_n, old_e = len(graph["nodes"]), len(graph["links"])
        print(f"\n  antes : {old_n} nos, {old_e} arestas")
        print(f"  depois: {len(res.nodes)} nos, {len(res.links)} arestas")
        if drift:
            print("\nDEFASAGEM detectada. Rode: python tools/graph_sync.py --update")
            return 1
        print("\nSem defasagem estrutural.")
        return 0

    # --update
    new_graph = dict(graph)
    new_graph["nodes"] = res.nodes
    new_graph["links"] = canonical_links(res.links)
    new_graph["hyperedges"] = res.hyperedges
    if "graph" in new_graph and isinstance(new_graph["graph"], dict):
        new_graph["graph"] = {"hyperedges": res.hyperedges}
    try:
        head = subprocess.check_output(["git", "-C", REPO, "rev-parse", "HEAD"]).decode().strip()
        new_graph["built_at_commit"] = head
    except Exception:
        pass

    errs = validate(new_graph)
    if errs:
        print("ABORTADO: grafo resultante invalido:")
        for e in errs:
            print("  -", e)
        return 2

    report(res)
    dump_atomic(GRAPH, new_graph)
    dump_atomic(SEMANTIC, build_semantic_snapshot(new_graph))
    n_manifest = write_manifest()
    print(f"\ngraph.json atualizado: {len(res.nodes)} nos, {len(res.links)} arestas.")
    print("semantic.json emitido: extrato da camada manual.")
    print(f"manifest.json regenerado: {n_manifest} arquivos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
