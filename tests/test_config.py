"""Preferencias do app (config.json) e aplicacao no modulo — incluindo o
saneamento: valor de tipo/valor invalido cai no default em vez de derrubar a
GUI/bot na abertura (KeyError/AttributeError/TypeError provados na auditoria)."""
import pytest


def test_salvar_e_carregar_config(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_CONFIG", tmp_path / "config.json")
    core.salvar_config({"carimbar_sku": True})
    assert core.carregar_config() == {"carimbar_sku": True}


def test_carregar_config_ausente_vazio(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_CONFIG", tmp_path / "nao_existe.json")
    assert core.carregar_config() == {}


def test_aplicar_config_liga_carimbo(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(core, "CARIMBAR_SKU", False)
    core.salvar_config({"carimbar_sku": True})
    cfg = core.aplicar_config()
    assert core.CARIMBAR_SKU is True
    assert cfg["carimbar_sku"] is True


def test_aplicar_config_sem_chave_nao_mexe(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(core, "CARIMBAR_SKU", True)
    core.salvar_config({"outra_coisa": 1})
    core.aplicar_config()
    assert core.CARIMBAR_SKU is True          # preservado


# ------------------------------------------------- saneamento (auditoria)
@pytest.mark.parametrize("ruim", [
    {"modo_identificacao": 123},              # dava KeyError na GUI
    {"modo_identificacao": "foo"},            # idem (valor desconhecido)
    {"marketplace": 123},                     # dava AttributeError (.strip)
    {"marketplace": "Loja Desconhecida"},     # radio orfao na GUI
    {"conta_ativa": 123},                     # dava TypeError (Path / int)
    {"conta_ativa": "   "},                   # so espacos = nao configurada
    {"geometria": 123},                       # nao-string
])
def test_aplicar_config_descarta_valor_invalido(core, tmp_path, monkeypatch, ruim):
    monkeypatch.setattr(core, "ARQUIVO_CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(core, "MODO_IDENT", "nenhuma")
    monkeypatch.setattr(core, "CARIMBAR_SKU", False)
    core.salvar_config(ruim)
    cfg = core.aplicar_config()               # nao pode levantar
    assert next(iter(ruim)) not in cfg        # chave invalida descartada
    assert core.MODO_IDENT in core.MODOS_IDENT


def test_aplicar_config_valores_validos_passam_intactos(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(core, "MODO_IDENT", "nenhuma")
    trocas = []
    monkeypatch.setattr(core, "migrar_conta_legado", lambda n: None)
    monkeypatch.setattr(core, "definir_conta", lambda n: trocas.append(n))
    core.salvar_config({"modo_identificacao": "carimbo_nome",
                        "marketplace": "Shopee", "conta_ativa": "Gastromaq",
                        "geometria": "700x800+10+10", "outra_chave": 42})
    cfg = core.aplicar_config()
    assert core.MODO_IDENT == "carimbo_nome"
    assert cfg["marketplace"] == "Shopee"
    assert cfg["geometria"] == "700x800+10+10"
    assert cfg["outra_chave"] == 42           # chave desconhecida preservada
    assert trocas == ["Gastromaq"]


def test_conta_ativa_tolera_tipo_errado(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ARQUIVO_CONFIG", tmp_path / "config.json")
    core.salvar_config({"conta_ativa": 123})
    assert core.conta_ativa() == ""           # nao propaga o int pra Path/


def test_sanear_config_nao_dict_vira_vazio(core):
    assert core._sanear_config(["lista"]) == {}
    assert core._sanear_config(None) == {}
