"""De-para SKU -> nome amigavel (apenas exibicao)."""
import json

from conftest import make_grupo


def test_aplicar_nomes_enriquece_rotulo(core):
    g_prp = make_grupo(core, [1], chave="PRP", nome="PRP", qtd=2)
    g_sem = make_grupo(core, [2], chave="A02", nome="A02", qtd=1)
    core.aplicar_nomes([g_prp, g_sem], {"PRP": "Picador Pequeno"})
    assert g_prp.nome == "PRP — Picador Pequeno"
    assert g_sem.nome == "A02"            # sem mapa -> inalterado
    assert g_prp.chave == "PRP"           # chave/agrupamento nao muda


def test_aplicar_nomes_mapa_vazio_nao_altera(core):
    g = make_grupo(core, [1], chave="PRP", nome="PRP")
    core.aplicar_nomes([g], {})
    assert g.nome == "PRP"


def test_carregar_nomes_le_arquivo(core, tmp_path, monkeypatch):
    arq = tmp_path / "nomes.json"
    arq.write_text(json.dumps({"PRP": "Picador Pequeno"}), encoding="utf-8")
    monkeypatch.setattr(core, "ARQUIVO_NOMES", arq)
    assert core.carregar_nomes() == {"PRP": "Picador Pequeno"}


def test_carregar_nomes_sem_arquivo_retorna_vazio(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_NOMES", tmp_path / "naoexiste.json")
    assert core.carregar_nomes() == {}


def test_carregar_nomes_json_invalido_retorna_vazio(core, tmp_path, monkeypatch):
    arq = tmp_path / "ruim.json"
    arq.write_text("{ isso nao e json", encoding="utf-8")
    monkeypatch.setattr(core, "ARQUIVO_NOMES", arq)
    assert core.carregar_nomes() == {}


def test_salvar_nomes_grava_ordenado_e_relê(core, tmp_path, monkeypatch):
    arq = tmp_path / "nomes.json"
    monkeypatch.setattr(core, "ARQUIVO_NOMES", arq)
    core.salvar_nomes({"B02": "Beta", "A01": "Alfa"})
    # chaves ordenadas no arquivo (diff do git limpo) e o roundtrip bate
    assert list(json.loads(arq.read_text(encoding="utf-8"))) == ["A01", "B02"]
    assert core.carregar_nomes() == {"A01": "Alfa", "B02": "Beta"}


def test_salvar_nomes_descarta_vazios_e_apara(core, tmp_path, monkeypatch):
    arq = tmp_path / "nomes.json"
    monkeypatch.setattr(core, "ARQUIVO_NOMES", arq)
    core.salvar_nomes({" PRP ": " Picador ", "": "sem sku", "X01": "  "})
    assert core.carregar_nomes() == {"PRP": "Picador"}   # apara e ignora vazios
