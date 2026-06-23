"""Suporte a multiplas contas: subpastas, migracao e selecao."""
import pytest


def _patch_pastas(core, monkeypatch, tmp_path):
    pasta_script = tmp_path / "app"
    pasta_script.mkdir()
    pasta_contas = pasta_script / "contas"
    monkeypatch.setattr(core, "PASTA_SCRIPT", pasta_script)
    monkeypatch.setattr(core, "PASTA_CONTAS", pasta_contas)
    # Restaura caminhos de arquivo para a raiz fake
    monkeypatch.setattr(core, "ARQUIVO_CRED", pasta_script / "credenciais.json")
    monkeypatch.setattr(core, "ARQUIVO_ESTADO", pasta_script / "estado_grupos.json")
    monkeypatch.setattr(core, "ARQUIVO_CACHE", pasta_script / "itens_cache.json")
    monkeypatch.setattr(core, "ARQUIVO_ENVIOS_CACHE", pasta_script / "envios_cache.json")
    monkeypatch.setattr(core, "ARQUIVO_CONFIG", pasta_script / "config.json")
    return pasta_script, pasta_contas


def test_definir_conta_cria_pasta_e_atualiza_arquivos(core, monkeypatch, tmp_path):
    pasta_script, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    pasta = core.definir_conta("Gastromaq")
    assert pasta == pasta_contas / "Gastromaq"
    assert pasta.is_dir()
    assert core.ARQUIVO_CRED == pasta_contas / "Gastromaq" / "credenciais.json"
    assert core.ARQUIVO_ESTADO == pasta_contas / "Gastromaq" / "estado_grupos.json"


def test_listar_contas_sem_pasta_retorna_vazio(core, monkeypatch, tmp_path):
    _, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    assert core.listar_contas() == []


def test_listar_contas_com_duas_contas(core, monkeypatch, tmp_path):
    _, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    for nome in ("Cozilatti", "Gastromaq"):
        p = pasta_contas / nome
        p.mkdir(parents=True)
        (p / "credenciais.json").write_text("{}", encoding="utf-8")
    contas = core.listar_contas()
    assert sorted(contas) == ["Cozilatti", "Gastromaq"]


def test_listar_contas_ignora_pastas_sem_credenciais(core, monkeypatch, tmp_path):
    _, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    (pasta_contas / "SemCred").mkdir(parents=True)   # pasta sem credenciais.json
    assert core.listar_contas() == []


def test_migrar_conta_legado_move_arquivos(core, monkeypatch, tmp_path):
    pasta_script, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    # Cria arquivos na raiz (situacao pre-migracao)
    (pasta_script / "credenciais.json").write_text('{"seller_id":"1"}', encoding="utf-8")
    (pasta_script / "estado_grupos.json").write_text('{}', encoding="utf-8")

    core.migrar_conta_legado("Gastromaq")

    assert (pasta_contas / "Gastromaq" / "credenciais.json").exists()
    assert (pasta_contas / "Gastromaq" / "estado_grupos.json").exists()
    assert not (pasta_script / "credenciais.json").exists()


def test_migrar_conta_legado_idempotente(core, monkeypatch, tmp_path):
    pasta_script, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    # Conta ja migrada: credenciais.json dentro da pasta da conta
    dest = pasta_contas / "Gastromaq"
    dest.mkdir(parents=True)
    (dest / "credenciais.json").write_text('{"seller_id":"1"}', encoding="utf-8")
    # Arquivo na raiz NAO deve ser tocado (segunda migracao nao acontece)
    (pasta_script / "credenciais.json").write_text('{"seller_id":"2"}', encoding="utf-8")

    core.migrar_conta_legado("Gastromaq")

    # Arquivo da raiz permanece intacto (nao foi movido de novo)
    assert (pasta_script / "credenciais.json").exists()


def test_migrar_sem_arquivos_na_raiz_nao_quebra(core, monkeypatch, tmp_path):
    _patch_pastas(core, monkeypatch, tmp_path)
    core.migrar_conta_legado("Gastromaq")   # nao ha nada para migrar -> silencioso


def test_aplicar_config_define_conta(core, monkeypatch, tmp_path):
    pasta_script, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    # Cria credenciais ja na pasta da conta (ja migrado)
    dest = pasta_contas / "Gastromaq"
    dest.mkdir(parents=True)
    (dest / "credenciais.json").write_text('{}', encoding="utf-8")

    cfg_path = pasta_script / "config.json"
    cfg_path.write_text('{"conta_ativa": "Gastromaq"}', encoding="utf-8")
    monkeypatch.setattr(core, "ARQUIVO_CONFIG", cfg_path)

    core.aplicar_config()

    assert core.ARQUIVO_CRED == pasta_contas / "Gastromaq" / "credenciais.json"
