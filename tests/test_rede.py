"""Camada HTTP: retry/backoff e download de etiquetas ZPL."""
import io
import zipfile

import pytest
import requests

from conftest import FakeResp


def _sequencia(monkeypatch, core, respostas):
    """Faz requests.get devolver as respostas em ordem; conta as chamadas."""
    estado = {"n": 0}

    def fake_get(url, headers=None, params=None, timeout=None):
        r = respostas[estado["n"]]
        estado["n"] += 1
        return r

    monkeypatch.setattr(core.requests, "get", fake_get)
    return estado


def test_espera_retry_respeita_header(core):
    r = FakeResp(429, headers={"Retry-After": "5"})
    espera = core._espera_retry(r, 1)
    assert 5 <= espera <= 5.5            # Retry-After + jitter pequeno


def test_espera_retry_sem_header_usa_backoff(core):
    r = FakeResp(503)                    # sem Retry-After
    e1 = core._espera_retry(r, 1)
    e2 = core._espera_retry(r, 2)
    assert 2 <= e1 <= 2.5                # 2^1 + jitter
    assert 4 <= e2 <= 4.5                # 2^2 + jitter


def test_espera_retry_header_invalido_cai_no_backoff(core):
    r = FakeResp(429, headers={"Retry-After": "xx"})
    assert 2 <= core._espera_retry(r, 1) <= 2.5


def test_requisicao_get_repete_e_retorna_apos_erros(core, monkeypatch):
    estado = _sequencia(monkeypatch, core, [FakeResp(503), FakeResp(503), FakeResp(200, json_data={"ok": True})])
    out = core._get("http://x", "tok")
    assert out == {"ok": True}
    assert estado["n"] == 3


def test_get_esgota_tentativas_e_levanta(core, monkeypatch):
    _sequencia(monkeypatch, core, [FakeResp(500), FakeResp(500), FakeResp(500)])
    with pytest.raises(requests.HTTPError):
        core._get("http://x", "tok")


def test_get_retenta_em_504(core, monkeypatch):
    estado = _sequencia(monkeypatch, core, [FakeResp(504), FakeResp(200, json_data={"ok": True})])
    assert core._get("http://x", "tok") == {"ok": True}
    assert estado["n"] == 2                # 504 agora e retentado


def test_requisicao_post_retry_em_erro_transitorio(core, monkeypatch):
    seq = iter([FakeResp(503), FakeResp(200, json_data={"ok": True})])
    monkeypatch.setattr(core.requests, "post", lambda *a, **k: next(seq))
    resp = core._requisicao_post("http://x", json={"a": 1})
    assert resp.status_code == 200         # POST agora tambem re-tenta


def test_zpl_de_zip_extrai_conteudo(core):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.txt", "^XA ZIP ^XZ")
    assert "^XA ZIP" in core._zpl_de_zip(buf.getvalue())


def test_baixar_zpl_sucesso_texto(core, monkeypatch):
    monkeypatch.setattr(core, "_requisicao_get",
                        lambda url, headers, params=None: FakeResp(200, content=b"^XA OK ^XZ"))
    assert "^XA" in core.baixar_zpl("tok", [1, 2, 3])


def test_baixar_zpl_aceita_zip(core, monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("x.txt", "^XA ZIP ^XZ")
    monkeypatch.setattr(core, "_requisicao_get",
                        lambda url, headers, params=None: FakeResp(200, content=buf.getvalue()))
    assert "^XA ZIP" in core.baixar_zpl("tok", [1])


def test_baixar_zpl_aborta_em_falha_parcial(core, monkeypatch):
    chamadas = {"n": 0}

    def resposta(url, headers, params=None):
        chamadas["n"] += 1
        return FakeResp(200, content=b"^XA ok ^XZ") if chamadas["n"] == 1 else FakeResp(500, text="boom")

    monkeypatch.setattr(core, "_requisicao_get", resposta)
    with pytest.raises(core.SeparadorError):
        core.baixar_zpl("tok", list(range(60)))  # 2 lotes -> o 2o falha
