"""Testes do validador do cofre Obsidian (tools/validar_obsidian.py).

Usam vaults mínimos e TEMPORÁRIOS — não dependem do conteúdo atual de obsidian/.
"""
import importlib.util
import unicodedata
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "validar_obsidian",
    Path(__file__).resolve().parent.parent / "tools" / "validar_obsidian.py")
vo = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(vo)


def _nota(corpo: str, *, type="concept", **fm) -> str:
    linhas = ["---", f"type: {type}"]
    for k, v in fm.items():
        if isinstance(v, list):
            linhas.append(f"{k}: [{', '.join(v)}]")
        else:
            linhas.append(f"{k}: {v}")
    linhas.append("---")
    linhas.append("")
    linhas.append(corpo)
    return "\n".join(linhas)


def _vault(tmp_path, arquivos: dict) -> Path:
    raiz = tmp_path / "vault"
    for rel, conteudo in arquivos.items():
        p = raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(conteudo, encoding="utf-8")
    return raiz


def _erros(raiz, repo_root=None):
    return vo.validar(raiz, repo_root or raiz.parent)


def _tem(erros, prefixo, trecho=""):
    return any(e.startswith(prefixo) and trecho in e for e in erros)


def test_vault_valido_sem_erros(tmp_path):
    raiz = _vault(tmp_path, {
        "A.md": _nota("Veja [[B]].", status="current"),
        "B.md": _nota("Conteúdo real.", status="current"),
    })
    assert _erros(raiz) == []


def test_link_valido_e_quebrado(tmp_path):
    raiz = _vault(tmp_path, {
        "A.md": _nota("Bom [[B]], ruim [[Inexistente]]."),
        "B.md": _nota("ok"),
    })
    erros = _erros(raiz)
    assert _tem(erros, "[link]", "Inexistente")
    assert not _tem(erros, "[link]", "[[B]]")


def test_link_por_alias(tmp_path):
    raiz = _vault(tmp_path, {
        "A.md": _nota("Veja [[apelido]]."),
        "B.md": _nota("ok", aliases=["apelido", "outro"]),
    })
    assert not _tem(_erros(raiz), "[link]")


def test_link_com_secao_e_alias(tmp_path):
    raiz = _vault(tmp_path, {
        "A.md": _nota("Veja [[B#Uma seção|texto exibido]] e [[B#Fim]]."),
        "B.md": _nota("## Uma seção\nx\n## Fim\ny"),
    })
    assert not _tem(_erros(raiz), "[link]")


def test_embed(tmp_path):
    raiz = _vault(tmp_path, {
        "A.md": _nota("Embute ![[B]]."),
        "B.md": _nota("ok"),
    })
    assert not _tem(_erros(raiz), "[link]")


def test_arquivo_vazio(tmp_path):
    raiz = _vault(tmp_path, {
        "Vazia.md": "---\ntype: concept\n---\n\n   \n",
        "B.md": _nota("ok"),
    })
    assert _tem(_erros(raiz), "[vazio]", "Vazia.md")


def test_colisao_por_caixa(tmp_path):
    raiz = _vault(tmp_path, {
        "Dup.md": _nota("um"),
        "dup.md": _nota("dois"),
    })
    erros = _erros(raiz)
    assert _tem(erros, "[colisao-caixa]") or _tem(erros, "[nome-ambiguo]")


def test_unicode_normalizacao_no_link(tmp_path):
    # nota em NFC; link escrito em NFD deve resolver após normalização
    nfd = unicodedata.normalize("NFD", "Café")
    raiz = _vault(tmp_path, {
        "Café.md": _nota("ok"),                      # NFC no nome do arquivo
        "A.md": _nota(f"Veja [[{nfd}]]."),
    })
    assert not _tem(_erros(raiz), "[link]")


def test_referencias_de_fonte(tmp_path):
    repo = tmp_path / "repo"
    (repo / "obsidian").mkdir(parents=True)
    (repo / "existe.py").write_text("x = 1\n", encoding="utf-8")
    raiz = repo / "obsidian"
    (raiz / "A.md").write_text(
        _nota("ok", source_files=["existe.py", "sumiu.py"]), encoding="utf-8")
    erros = _erros(raiz, repo_root=repo)
    assert _tem(erros, "[fonte]", "sumiu.py")
    assert not _tem(erros, "[fonte]", "existe.py")


def test_segredo_valor_real_e_flagrado(tmp_path):
    raiz = _vault(tmp_path, {
        "A.md": _nota("token: APP_USR-12345678-abcdEF90-mno1234567pqrs"),
        "B.md": _nota("ok"),
    })
    assert _tem(_erros(raiz), "[segredo]")


def test_segredo_jwt_flagrado(tmp_path):
    jwt = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
           "eyJzdWIiOiIxMjM0NTY3ODkwIn0.dOzNabc123DEF456ghiJKLmno789")
    raiz = _vault(tmp_path, {"A.md": _nota(f"Exemplo ruim: {jwt}")})
    assert _tem(_erros(raiz), "[segredo]")


def test_nome_de_campo_sensivel_sem_valor_nao_e_segredo(tmp_path):
    corpo = ("A URL leva `access_token` e `sign` na query. O token vem de "
             "`TELEGRAM_BOT_TOKEN` ou de `bot_config.json`. Use `SEU_TOKEN_AQUI` "
             "e `CLIENT_ID_EXEMPLO` nos exemplos.")
    raiz = _vault(tmp_path, {"A.md": _nota(corpo)})
    assert not _tem(_erros(raiz), "[segredo]")


def test_segredo_em_bloco_de_codigo_com_placeholder_ok(tmp_path):
    corpo = "```\nexport TELEGRAM_BOT_TOKEN=SEU_TOKEN_AQUI\n```\ntexto."
    raiz = _vault(tmp_path, {"A.md": _nota(corpo)})
    assert not _tem(_erros(raiz), "[segredo]")


def test_frontmatter_type_invalido(tmp_path):
    raiz = _vault(tmp_path, {
        "A.md": _nota("ok", type="xpto"),
        "B.md": _nota("ok"),
    })
    assert _tem(_erros(raiz), "[frontmatter]", "type 'xpto'")


def test_frontmatter_faltando_type(tmp_path):
    raiz = _vault(tmp_path, {"A.md": "---\nstatus: current\n---\n\nsem type\n"})
    assert _tem(_erros(raiz), "[frontmatter]", "falta 'type'")


def test_status_invalido(tmp_path):
    raiz = _vault(tmp_path, {"A.md": _nota("ok", status="inventado")})
    assert _tem(_erros(raiz), "[frontmatter]", "status 'inventado'")


def test_link_para_mesma_nota_secao_ok(tmp_path):
    raiz = _vault(tmp_path, {"A.md": _nota("Veja [[#Topo]].\n\n## Topo\nx")})
    assert not _tem(_erros(raiz), "[link]")
