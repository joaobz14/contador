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


def test_requisicao_get_repete_e_retorna_apos_erros(core, monkeypatch):
    estado = _sequencia(monkeypatch, core, [FakeResp(503), FakeResp(503), FakeResp(200, json_data={"ok": True})])
    out = core._get("http://x", "tok")
    assert out == {"ok": True}
    assert estado["n"] == 3


def test_get_esgota_tentativas_e_levanta(core, monkeypatch):
    _sequencia(monkeypatch, core, [FakeResp(500), FakeResp(500), FakeResp(500)])
    with pytest.raises(requests.HTTPError):
        core._get("http://x", "tok")


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
