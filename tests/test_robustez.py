"""Robustez: IO de JSON atomico/tolerante, retry de rede, credenciais invalidas."""
import json
import time

import pytest
import requests

from conftest import FakeResp


# --------------------------------------------------- IO JSON (atomico/tolerante)
def test_ler_json_inexistente_retorna_vazio(core, tmp_path, monkeypatch):
    assert core._ler_json(tmp_path / "nao_existe.json") == {}


def test_ler_json_corrompido_retorna_vazio(core, tmp_path):
    arq = tmp_path / "ruim.json"
    arq.write_text("{ nao e json ", encoding="utf-8")
    assert core._ler_json(arq) == {}


def test_gravar_json_atomico_e_relido(core, tmp_path):
    arq = tmp_path / "x.json"
    core._gravar_json(arq, {"a": 1})
    assert json.loads(arq.read_text(encoding="utf-8")) == {"a": 1}
    assert not (tmp_path / "x.json.tmp").exists()   # nao deixa lixo .tmp


def test_carregar_estado_nao_quebra_com_arquivo_corrompido(core, tmp_path, monkeypatch):
    arq = tmp_path / "estado.json"
    arq.write_text("{{{ corrompido", encoding="utf-8")
    monkeypatch.setattr(core, "ARQUIVO_ESTADO", arq)
    assert core.carregar_estado() == {}


# --------------------------------------------------- credenciais invalidas
def test_carregar_credenciais_invalida_da_erro_amigavel(core, tmp_path, monkeypatch):
    arq = tmp_path / "credenciais.json"
    arq.write_text("nao e json", encoding="utf-8")
    monkeypatch.setattr(core, "ARQUIVO_CRED", arq)
    with pytest.raises(core.SeparadorError):
        core.carregar_credenciais()


# ------------------------------------------ backup/auto-recuperacao de credenciais
def test_salvar_credenciais_cria_backup_espelho(core, tmp_path, monkeypatch):
    arq = tmp_path / "credenciais.json"
    monkeypatch.setattr(core, "ARQUIVO_CRED", arq)
    core.salvar_credenciais({"refresh_token": "abc"})
    bak = tmp_path / "credenciais.json.bak"
    assert json.loads(bak.read_text(encoding="utf-8")) == {"refresh_token": "abc"}


def test_carregar_credenciais_restaura_do_backup_quando_corrompe(core, tmp_path, monkeypatch):
    arq = tmp_path / "credenciais.json"
    monkeypatch.setattr(core, "ARQUIVO_CRED", arq)
    core.salvar_credenciais({"refresh_token": "bom"})     # gera o .bak
    arq.write_text("\x00\x00\x00", encoding="utf-8")      # simula queda de energia
    cred = core.carregar_credenciais()                    # deve recuperar do .bak
    assert cred == {"refresh_token": "bom"}
    # e reescreve o principal a partir do backup (proxima leitura ja le direto)
    assert json.loads(arq.read_text(encoding="utf-8")) == {"refresh_token": "bom"}


def test_carregar_credenciais_gera_backup_na_primeira_leitura(core, tmp_path, monkeypatch):
    # arquivo veio do pegar_token.py (sem .bak ainda) -> a 1a leitura cria o .bak
    arq = tmp_path / "credenciais.json"
    arq.write_text(json.dumps({"refresh_token": "x"}), encoding="utf-8")
    monkeypatch.setattr(core, "ARQUIVO_CRED", arq)
    assert core.carregar_credenciais() == {"refresh_token": "x"}
    assert (tmp_path / "credenciais.json.bak").exists()


def test_backup_acompanha_token_girado(core, tmp_path, monkeypatch):
    # apos o token girar, o .bak reflete o novo (restauracao devolve token valido)
    arq = tmp_path / "credenciais.json"
    monkeypatch.setattr(core, "ARQUIVO_CRED", arq)
    core.salvar_credenciais({"refresh_token": "v1"})
    core.salvar_credenciais({"refresh_token": "v2"})      # token girou
    bak = tmp_path / "credenciais.json.bak"
    assert json.loads(bak.read_text(encoding="utf-8")) == {"refresh_token": "v2"}


# --------------------------------------------- token ML: cache + lock (double-check)
def test_renovar_token_cacheia_access_token_e_rotaciona(core, monkeypatch):
    monkeypatch.setattr(core, "_requisicao_post", lambda *a, **k: FakeResp(
        200, json_data={"access_token": "AT", "expires_in": 21600, "refresh_token": "R1"}))
    monkeypatch.setattr(core, "salvar_credenciais", lambda c: None)
    cred = {"client_id": "c", "client_secret": "s", "refresh_token": "R0"}
    assert core.renovar_token(cred) == "AT"
    assert cred["access_token"] == "AT"
    assert cred["access_token_exp"] > time.time()      # validade cacheada
    assert cred["refresh_token"] == "R1"               # rotacionou


def test_obter_token_reusa_cache_e_so_renova_quando_expira(core, tmp_path, monkeypatch):
    chamou = {"n": 0}

    def fake_renovar(cred):
        chamou["n"] += 1
        cred["access_token"] = "NOVO"
        cred["access_token_exp"] = time.time() + 9999
        return "NOVO"

    monkeypatch.setattr(core, "renovar_token", fake_renovar)
    # ARQUIVO_CRED sem token no disco: obter_token nao acha nada e cai no renovar.
    monkeypatch.setattr(core, "ARQUIVO_CRED", tmp_path / "sem_cred.json")
    valido = {"access_token": "OK", "access_token_exp": time.time() + 9999}
    assert core.obter_token(valido) == "OK" and chamou["n"] == 0   # cache: nao renova
    expirado = {"access_token": "VELHO", "access_token_exp": 0}
    assert core.obter_token(expirado) == "NOVO" and chamou["n"] == 1  # renova 1x


def test_obter_token_adota_token_do_disco_de_outro_processo(core, tmp_path, monkeypatch):
    """GUI+bot na MESMA conta: se outro processo ja renovou e salvou no disco,
    obter_token adota esse token em vez de renovar (evita gastar o refresh_token
    de uso unico e a corrida que travaria a conta)."""
    arq = tmp_path / "credenciais.json"
    monkeypatch.setattr(core, "ARQUIVO_CRED", arq)
    core._gravar_json(arq, {"access_token": "DO_DISCO", "access_token_exp": time.time() + 9999,
                            "refresh_token": "R_NOVO", "seller_id": 7})
    monkeypatch.setattr(core, "renovar_token",
                        lambda c: (_ for _ in ()).throw(AssertionError("nao deve renovar")))
    cred = {"access_token": "VELHO", "access_token_exp": 0, "refresh_token": "R_VELHO"}
    assert core.obter_token(cred) == "DO_DISCO"
    assert cred["refresh_token"] == "R_NOVO"          # adotou o refresh mais recente do disco


def test_obter_token_rele_o_disco_dentro_da_trava_de_processos(core, tmp_path, monkeypatch):
    """A releitura do disco acontece DEPOIS de adquirir a trava de ARQUIVO:
    simulamos outro processo que termina o refresh enquanto esperavamos a
    trava (o context manager injetado grava o token novo na entrada).
    obter_token deve ADOTAR esse token — nunca disparar um segundo refresh (o
    refresh_token e de uso unico; a corrida podia travar a conta). No codigo
    antigo (sem trava), o disco era lido ainda vazio e renovava junto."""
    import contextlib
    import time

    arq = tmp_path / "credenciais.json"
    monkeypatch.setattr(core, "ARQUIVO_CRED", arq)
    core._gravar_json(arq, {"access_token": "", "access_token_exp": 0,
                            "refresh_token": "R1"})     # vazio ANTES da trava
    renovacoes = []
    monkeypatch.setattr(core, "renovar_token",
                        lambda c: renovacoes.append(1) or "NAO_DEVIA")

    @contextlib.contextmanager
    def trava_simulada(caminho):
        assert caminho == arq                     # trava no arquivo certo
        # "outro processo" terminou o refresh enquanto esperavamos a trava:
        core._gravar_json(arq, {"access_token": "DO_OUTRO",
                                "access_token_exp": time.time() + 9999,
                                "refresh_token": "R2"})
        yield

    monkeypatch.setattr(core._estado, "trava", trava_simulada)
    cred = {"access_token": "VELHO", "access_token_exp": 0, "refresh_token": "R1"}
    assert core.obter_token(cred) == "DO_OUTRO"
    assert renovacoes == []                       # nenhum refresh gasto
    assert cred["refresh_token"] == "R2"          # adotou o refresh mais novo


def test_obter_token_concorrente_so_um_refresh(tmp_path, monkeypatch):
    """Concorrencia real (trava de arquivo de verdade): dois 'processos' sem
    token valido chegam juntos — apenas UM renova; o outro espera a trava e
    adota o token salvo. Sem a fixture `core` (ela neutraliza o time.sleep,
    que aqui precisa ser real para segurar a trava)."""
    import threading
    import time as _t

    import separador_etiquetas_ml as core_mod

    arq = tmp_path / "credenciais.json"
    monkeypatch.setattr(core_mod, "ARQUIVO_CRED", arq)
    core_mod._gravar_json(arq, {"access_token": "", "access_token_exp": 0,
                                "refresh_token": "R1"})
    renovacoes = []

    def renovar_lento(cred):
        _t.sleep(0.1)                             # janela para o 2o chegar
        renovacoes.append(1)
        cred["access_token"] = "RENOVADO"
        cred["access_token_exp"] = _t.time() + 9999
        cred["refresh_token"] = "R2"
        core_mod._gravar_json(arq, dict(cred))
        return "RENOVADO"

    monkeypatch.setattr(core_mod, "renovar_token", renovar_lento)
    # _LOCK_TOKEN e por processo; para simular DOIS processos, cada worker usa
    # um lock proprio (senao o lock de thread ja serializa e o teste nao
    # exercita a trava de arquivo).
    tokens = []

    def processo():
        monkeypatch.setattr(core_mod, "_LOCK_TOKEN", threading.Lock())
        cred = {"access_token": "", "access_token_exp": 0, "refresh_token": "R1"}
        tokens.append(core_mod.obter_token(cred))

    t1 = threading.Thread(target=processo)
    t2 = threading.Thread(target=processo)
    t1.start(); _t.sleep(0.02); t2.start()
    t1.join(); t2.join()
    assert tokens == ["RENOVADO", "RENOVADO"]
    assert renovacoes == [1]                      # UM refresh so (o 2o adotou)


def test_renovar_token_nao_retenta_o_refresh_grant(core, monkeypatch):
    """O refresh grant NAO pode ser re-tentado: um retry apos o servidor ja ter
    rotacionado o refresh_token (uso unico) gastaria um token invalido."""
    capt = {}

    def fake_post(url, **k):
        capt["tentativas"] = k.get("tentativas")
        return FakeResp(200, json_data={"access_token": "AT", "expires_in": 100})

    monkeypatch.setattr(core, "_requisicao_post", fake_post)
    monkeypatch.setattr(core, "salvar_credenciais", lambda c: None)
    core.renovar_token({"client_id": "c", "client_secret": "s", "refresh_token": "R"})
    assert capt["tentativas"] == 1


# --------------------------------------------------- retry em falha de rede
def test_requisicao_get_retenta_apos_falha_de_rede(core, monkeypatch):
    estado = {"n": 0}

    def fake_get(url, headers=None, params=None, timeout=None):
        estado["n"] += 1
        if estado["n"] < 3:
            raise requests.ConnectionError("rede caiu")
        return FakeResp(200, json_data={"ok": True})

    monkeypatch.setattr(core.requests, "get", fake_get)
    resp = core._requisicao_get("http://x", {})
    assert resp.status_code == 200 and estado["n"] == 3


def test_requisicao_get_desiste_apos_rede_persistente(core, monkeypatch):
    def sempre_falha(url, headers=None, params=None, timeout=None):
        raise requests.Timeout("estourou")

    monkeypatch.setattr(core.requests, "get", sempre_falha)
    with pytest.raises(requests.Timeout):
        core._requisicao_get("http://x", {})
