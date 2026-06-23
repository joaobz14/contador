"""Preferencias do app (config.json) e aplicacao no modulo."""


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
