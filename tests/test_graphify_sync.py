"""Guarda automatica do grafo Graphify (`graphify-out/graph.json`).

Estes testes protegem contra **defasagem** e contra **corrupcao da camada
semantica** (o conhecimento mantido a mao). Rodam no CI junto com o resto.

Se um destes falhar por "inventario de simbolos mudou", o conserto e:

    python tools/graph_sync.py --update

Ver `tools/graph_sync.py` (o reconciliador) e `CLAUDE.md` / `GRAPH_REPORT.md`.
"""
import importlib.util
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH = os.path.join(REPO, "graphify-out", "graph.json")


def _load_gs():
    path = os.path.join(REPO, "tools", "graph_sync.py")
    spec = importlib.util.spec_from_file_location("graph_sync", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["graph_sync"] = mod
    spec.loader.exec_module(mod)
    return mod


gs = _load_gs()


@pytest.fixture(scope="module")
def graph():
    return gs.load_json(GRAPH)


def test_graph_is_valid(graph):
    """JSON valido, IDs unicos, sem arestas orfas, hyperedges coerentes,
    arquivos de origem existentes, relacoes com nomes validos."""
    errs = gs.validate(graph)
    assert not errs, "graph.json invalido:\n  " + "\n  ".join(errs)


def test_ids_unicos(graph):
    ids = [n["id"] for n in graph["nodes"]]
    assert len(ids) == len(set(ids)), "ha IDs de no duplicados"


def test_sem_defasagem_de_inventario(graph):
    """O inventario de simbolos do codigo casa com os nos de codigo do grafo.

    Toleramos deriva de numero de linha (refrescada por `--update`), mas NAO
    simbolos novos sem no nem nos AST apontando para simbolos removidos.
    """
    mods = gs.parse_all()
    res = gs.reconcile(graph, mods)
    problemas = []
    if res.added_nodes:
        problemas.append(f"{len(res.added_nodes)} simbolo(s) do codigo sem no: "
                         + ", ".join(n["id"] for n in res.added_nodes[:8]))
    if res.removed_nodes:
        problemas.append(f"{len(res.removed_nodes)} no(s) AST de simbolo removido: "
                         + ", ".join(n["id"] for n in res.removed_nodes[:8]))
    if res.dangling_reported:
        problemas.append(f"{len(res.dangling_reported)} aresta(s) manual(is) penduradas")
    assert not problemas, ("grafo defasado — rode `python tools/graph_sync.py --update`:\n  "
                           + "\n  ".join(problemas))


def test_camada_semantica_preservada(graph):
    """Nos de conhecimento mantidos a mao continuam presentes e ancorados."""
    ids = {n["id"] for n in graph["nodes"]}
    # amostra de invariantes/decisoes/barreiras que NAO podem sumir
    chave = [
        "inv_confirma_antes_marcar", "inv_marcar_merge", "inv_token_via_obter",
        "inv_shopee_awb", "estado_corrompido_visivel", "trava_espera_windows",
        "provedor_sem_imprimir_grupo", "zebra_contrato_v1257",
        "historico_dia_de_acao", "resumo_soma_por_produto", "config_por_chave",
        "amazon_fbm_vs_fba",
    ]
    faltando = [k for k in chave if k not in ids]
    assert not faltando, f"nos semanticos sumiram do grafo: {faltando}"

    # toda aresta rationale_for/conceptually_related_to resolve nos dois extremos
    for rel in ("rationale_for", "conceptually_related_to", "shares_data_with"):
        for l in graph["links"]:
            if l["relation"] == rel:
                assert l["source"] in ids and l["target"] in ids, \
                    f"aresta {rel} orfa: {l['source']} -> {l['target']}"


def test_contagens_batem_com_o_relatorio(graph):
    """As contagens de nos/arestas no GRAPH_REPORT.md refletem o graph.json."""
    report = os.path.join(REPO, "graphify-out", "GRAPH_REPORT.md")
    with open(report, encoding="utf-8") as fh:
        txt = fh.read()
    n_nodes, n_edges = len(graph["nodes"]), len(graph["links"])
    assert f"{n_nodes} nodes" in txt or f"{n_nodes} nós" in txt, \
        f"GRAPH_REPORT.md nao cita {n_nodes} nós (contagem defasada)"
    assert f"{n_edges} edges" in txt or f"{n_edges} arestas" in txt, \
        f"GRAPH_REPORT.md nao cita {n_edges} arestas (contagem defasada)"
