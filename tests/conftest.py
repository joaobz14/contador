"""Configuracao comum dos testes."""
import sys
from pathlib import Path

import pytest

# Garante que o modulo do projeto seja importavel a partir da raiz.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import separador_etiquetas_ml as _core  # noqa: E402


@pytest.fixture
def core(monkeypatch):
    """Modulo do nucleo com time.sleep neutralizado (testes de retry rapidos)."""
    monkeypatch.setattr(_core.time, "sleep", lambda *_a, **_k: None)
    return _core


class FakeResp:
    """Resposta HTTP falsa para simular requests.get sem rede."""

    def __init__(self, status=200, content=b"", json_data=None, text="", headers=None):
        self.status_code = status
        self.content = content
        self._json = json_data
        self.text = text
        self.headers = headers or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")


def make_grupo(core, ids, chave="K", nome="Produto X", qtd=1):
    g = core.Grupo(chave=chave, nome=nome, quantidade=qtd)
    g.shipment_ids = list(ids)
    return g
