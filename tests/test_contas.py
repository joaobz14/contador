"""Suporte a multiplas contas: subpastas, migracao e selecao."""


def _patch_pastas(core, monkeypatch, tmp_path):
    """Estrutura fake: app/ (raiz) com dados/ dentro. Os arquivos "soltos" do
    setup de conta unica ficam em dados/ (a reorganizacao em pastas ja os tirou
    da raiz antes) — e contas/{nome}/ e subpasta de dados/."""
    pasta_script = tmp_path / "app"
    pasta_dados = pasta_script / "dados"
    pasta_dados.mkdir(parents=True)
    pasta_contas = pasta_dados / "contas"
    monkeypatch.setattr(core, "PASTA_SCRIPT", pasta_script)
    monkeypatch.setattr(core, "PASTA_DADOS", pasta_dados)
    monkeypatch.setattr(core, "PASTA_CONTAS", pasta_contas)
    # Restaura caminhos de arquivo para a pasta de dados fake
    monkeypatch.setattr(core, "ARQUIVO_CRED", pasta_dados / "credenciais.json")
    monkeypatch.setattr(core, "ARQUIVO_ESTADO", pasta_dados / "estado_grupos.json")
    monkeypatch.setattr(core, "ARQUIVO_CACHE", pasta_dados / "itens_cache.json")
    monkeypatch.setattr(core, "ARQUIVO_ENVIOS_CACHE", pasta_dados / "envios_cache.json")
    monkeypatch.setattr(core, "ARQUIVO_CONFIG", pasta_dados / "config.json")
    return pasta_dados, pasta_contas


def test_definir_conta_cria_pasta_e_atualiza_arquivos(core, monkeypatch, tmp_path):
    dados, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
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
    dados, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    # Cria arquivos na raiz (situacao pre-migracao)
    (dados / "credenciais.json").write_text('{"seller_id":"1"}', encoding="utf-8")
    (dados / "estado_grupos.json").write_text('{}', encoding="utf-8")

    core.migrar_conta_legado("Gastromaq")

    assert (pasta_contas / "Gastromaq" / "credenciais.json").exists()
    assert (pasta_contas / "Gastromaq" / "estado_grupos.json").exists()
    assert not (dados / "credenciais.json").exists()


def test_migrar_conta_legado_idempotente(core, monkeypatch, tmp_path):
    dados, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    # Conta ja migrada: credenciais.json dentro da pasta da conta
    dest = pasta_contas / "Gastromaq"
    dest.mkdir(parents=True)
    (dest / "credenciais.json").write_text('{"seller_id":"1"}', encoding="utf-8")
    # Arquivo na raiz NAO deve ser tocado (segunda migracao nao acontece)
    (dados / "credenciais.json").write_text('{"seller_id":"2"}', encoding="utf-8")

    core.migrar_conta_legado("Gastromaq")

    # Arquivo da raiz permanece intacto (nao foi movido de novo)
    assert (dados / "credenciais.json").exists()


def test_migrar_sem_arquivos_na_raiz_nao_quebra(core, monkeypatch, tmp_path):
    _patch_pastas(core, monkeypatch, tmp_path)
    core.migrar_conta_legado("Gastromaq")   # nao ha nada para migrar -> silencioso


def test_migrar_leva_o_bak_junto(core, monkeypatch, tmp_path):
    """O .bak vai junto na migracao: um .bak desgarrado na raiz guarda um
    refresh_token ja rotacionado (morto) — a auto-recuperacao poderia um dia
    'restaurar' um credenciais.json zumbi na raiz (achado da auditoria)."""
    dados, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    (dados / "credenciais.json").write_text('{"refresh_token":"r"}', encoding="utf-8")
    (dados / "credenciais.json.bak").write_text('{"refresh_token":"r"}', encoding="utf-8")

    core.migrar_conta_legado("Gastromaq")

    assert (pasta_contas / "Gastromaq" / "credenciais.json.bak").exists()
    assert not (dados / "credenciais.json.bak").exists()   # raiz limpa


def test_migrar_ja_migrado_remove_bak_orfao_da_raiz(core, monkeypatch, tmp_path):
    """Conta ja migrada (por uma versao antiga, que NAO levava o .bak): o .bak
    orfao da raiz e removido — sem principal ao lado, ele so alimenta a cadeia
    do zumbi (auto-restauracao de credencial morta + prompt de migracao em loop)."""
    dados, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    dest = pasta_contas / "Gastromaq"
    dest.mkdir(parents=True)
    (dest / "credenciais.json").write_text('{"refresh_token":"novo"}', encoding="utf-8")
    (dados / "credenciais.json.bak").write_text('{"refresh_token":"MORTO"}', encoding="utf-8")

    core.migrar_conta_legado("Gastromaq")

    assert not (dados / "credenciais.json.bak").exists()
    # a conta migrada fica intacta
    assert (dest / "credenciais.json").read_text(encoding="utf-8") == '{"refresh_token":"novo"}'


def test_migrar_ja_migrado_nao_remove_bak_com_principal_na_raiz(core, monkeypatch, tmp_path):
    """Se a raiz tem credenciais.json E .bak (par completo, ex.: conta nova que
    o dono colocou ali), o .bak NAO e apagado — so o orfao (sem principal) e
    lixo garantido."""
    dados, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    dest = pasta_contas / "Gastromaq"
    dest.mkdir(parents=True)
    (dest / "credenciais.json").write_text("{}", encoding="utf-8")
    (dados / "credenciais.json").write_text('{"refresh_token":"par"}', encoding="utf-8")
    (dados / "credenciais.json.bak").write_text('{"refresh_token":"par"}', encoding="utf-8")

    core.migrar_conta_legado("Gastromaq")   # ja migrado -> retorna cedo

    assert (dados / "credenciais.json.bak").exists()      # par preservado


def test_aplicar_config_define_conta(core, monkeypatch, tmp_path):
    dados, pasta_contas = _patch_pastas(core, monkeypatch, tmp_path)
    # Cria credenciais ja na pasta da conta (ja migrado)
    dest = pasta_contas / "Gastromaq"
    dest.mkdir(parents=True)
    (dest / "credenciais.json").write_text('{}', encoding="utf-8")

    cfg_path = dados / "config.json"
    cfg_path.write_text('{"conta_ativa": "Gastromaq"}', encoding="utf-8")
    monkeypatch.setattr(core, "ARQUIVO_CONFIG", cfg_path)

    core.aplicar_config()

    assert core.ARQUIVO_CRED == pasta_contas / "Gastromaq" / "credenciais.json"


# ------------------------------------- reorganizacao em pastas (dados/ + logs/)
def _patch_reorg(core, monkeypatch, tmp_path):
    """Raiz fake com dados/ e logs/ ainda vazios (situacao pre-reorganizacao:
    tudo solto na raiz)."""
    raiz = tmp_path / "app"
    raiz.mkdir()
    monkeypatch.setattr(core, "PASTA_SCRIPT", raiz)
    monkeypatch.setattr(core, "PASTA_DADOS", raiz / "dados")
    monkeypatch.setattr(core, "PASTA_LOGS", raiz / "logs")
    monkeypatch.setattr(core, "PASTA_CONTAS", raiz / "dados" / "contas")
    return raiz


def test_migrar_para_pastas_move_dados_e_logs(core, monkeypatch, tmp_path):
    raiz = _patch_reorg(core, monkeypatch, tmp_path)
    (raiz / "config.json").write_text('{"a":1}', encoding="utf-8")
    (raiz / "estado_shopee.json").write_text('{"b":2}', encoding="utf-8")
    (raiz / "bot.log").write_text("linha", encoding="utf-8")

    core.migrar_para_pastas()

    assert (raiz / "dados" / "config.json").read_text(encoding="utf-8") == '{"a":1}'
    assert (raiz / "dados" / "estado_shopee.json").exists()
    assert (raiz / "logs" / "bot.log").read_text(encoding="utf-8") == "linha"
    assert not (raiz / "config.json").exists()          # raiz limpa


def test_migrar_para_pastas_leva_o_bak_das_credenciais(core, monkeypatch, tmp_path):
    """O .bak do token vai JUNTO: um .bak desgarrado do principal guarda um
    refresh ja rotacionado (morto) — mesma regra do migrar_conta_legado."""
    raiz = _patch_reorg(core, monkeypatch, tmp_path)
    (raiz / "credenciais_shopee.json").write_text('{"refresh_token":"r"}', encoding="utf-8")
    (raiz / "credenciais_shopee.json.bak").write_text('{"refresh_token":"r"}', encoding="utf-8")

    core.migrar_para_pastas()

    assert (raiz / "dados" / "credenciais_shopee.json").exists()
    assert (raiz / "dados" / "credenciais_shopee.json.bak").exists()
    assert not (raiz / "credenciais_shopee.json.bak").exists()


def test_migrar_para_pastas_move_a_pasta_contas_inteira(core, monkeypatch, tmp_path):
    raiz = _patch_reorg(core, monkeypatch, tmp_path)
    conta = raiz / "contas" / "Cozilatti"
    conta.mkdir(parents=True)
    (conta / "credenciais.json").write_text('{"seller_id":"9"}', encoding="utf-8")

    core.migrar_para_pastas()

    destino = raiz / "dados" / "contas" / "Cozilatti" / "credenciais.json"
    assert destino.read_text(encoding="utf-8") == '{"seller_id":"9"}'
    assert not (raiz / "contas").exists()


def test_migrar_para_pastas_nao_sobrescreve_destino(core, monkeypatch, tmp_path):
    """Se o destino JA existe (app ja migrado e rodando), o arquivo solto na
    raiz e resto de copia antiga — nao pode sobrescrever o dado EM USO."""
    raiz = _patch_reorg(core, monkeypatch, tmp_path)
    (raiz / "dados").mkdir()
    (raiz / "dados" / "config.json").write_text('{"em":"uso"}', encoding="utf-8")
    (raiz / "config.json").write_text('{"velho":true}', encoding="utf-8")

    core.migrar_para_pastas()

    assert (raiz / "dados" / "config.json").read_text(encoding="utf-8") == '{"em":"uso"}'


def test_migrar_para_pastas_e_idempotente_e_cria_pastas(core, monkeypatch, tmp_path):
    raiz = _patch_reorg(core, monkeypatch, tmp_path)
    core.migrar_para_pastas()          # instalacao nova: nada a mover
    core.migrar_para_pastas()          # 2a vez nao quebra
    assert (raiz / "dados").is_dir() and (raiz / "logs").is_dir()


def test_migrar_para_pastas_remove_bot_lock_orfao(core, monkeypatch, tmp_path):
    """bot.lock e sobra do auto-start pela tela (removido em 2026-07): sem
    codigo que o leia, so poluia a pasta."""
    raiz = _patch_reorg(core, monkeypatch, tmp_path)
    (raiz / "bot.lock").write_text("1234", encoding="utf-8")
    core.migrar_para_pastas()
    assert not (raiz / "bot.lock").exists()


def test_migrar_para_pastas_nunca_levanta(core, monkeypatch, tmp_path):
    """Best-effort: uma falha de IO na migracao nao pode impedir o app de abrir."""
    _patch_reorg(core, monkeypatch, tmp_path)

    def _explode(*a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(core.Path, "mkdir", _explode)
    core.migrar_para_pastas()          # silencioso
