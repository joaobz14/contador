"""Autorizacao do bot: TODO handler registrado tem de checar quem esta falando.

Varredura de seguranca de 2026-08-03. O bot e a unica superficie do projeto que
qualquer pessoa na internet alcanca — basta descobrir o @usuario dele. A
autorizacao e por `chat_id` numa lista do `bot_config.json` (`_autorizado`).

O risco NAO e o codigo de hoje: e o handler de amanha. A checagem vive em dois
pontos de estrangulamento (`_responder` e `_listar_grupos`) e a maioria dos
comandos delega para eles — mas um comando novo que nao delegue nasce ABERTO, e
nada acusaria. Dai este teste.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

try:
    import bot_telegram as bot  # noqa: F401
except Exception as e:  # noqa: BLE001
    pytest.skip(f"bot_telegram indisponivel: {e}", allow_module_level=True)

FONTE = Path(__file__).resolve().parent.parent / "bot_telegram.py"

# Handlers ABERTOS de proposito, com o motivo. Mexer aqui e uma decisao de
# seguranca consciente — nunca a saida facil para um teste vermelho.
ABERTOS = {
    # Porta de entrada legitima: devolve SO o chat id de quem perguntou, que e
    # justamente o numero que o dono precisa para autorizar alguem.
    "cmd_id",
    # Resposta generica a texto solto ("Nao entendi, mande /menu"). Nao revela
    # nada do negocio; so confirma que o bot existe, o que o proprio Telegram ja
    # faz ao listar o @usuario.
    "cmd_desconhecido",
}


def _handlers_registrados() -> set[str]:
    """Nomes das funcoes passadas a add_handler(...) no `main`."""
    src = FONTE.read_text(encoding="utf-8")
    nomes: set[str] = set()
    for ch in re.findall(r"add_handler\(\s*(\w+Handler)\((.*?)\)\s*\)", src, re.S):
        args = ch[1]
        # o handler e sempre o ULTIMO identificador solto do construtor
        cands = re.findall(r"(?:^|,)\s*(\w+)\s*(?:,|$)", args)
        nomes.update(c for c in cands if c.startswith(("cmd_", "cb_")))
    return nomes


def _checa_autorizacao(nome: str, src: str, arvore, vistos: set) -> bool:
    """True se a funcao chama `_autorizado` — direta ou via quem ela chama."""
    if nome in vistos:
        return False
    vistos.add(nome)
    for no in ast.walk(arvore):
        if isinstance(no, (ast.AsyncFunctionDef, ast.FunctionDef)) and no.name == nome:
            corpo = ast.get_source_segment(src, no) or ""
            if "_autorizado" in corpo:
                return True
            for chamada in re.findall(r"await\s+(_?\w+)\(", corpo):
                if _checa_autorizacao(chamada, src, arvore, vistos):
                    return True
    return False


def test_todo_handler_registrado_checa_autorizacao():
    src = FONTE.read_text(encoding="utf-8")
    arvore = ast.parse(src)
    registrados = _handlers_registrados()

    assert len(registrados) >= 12, f"o scanner achou so {registrados} — regex quebrada?"

    desprotegidos = [
        h for h in sorted(registrados)
        if h not in ABERTOS and not _checa_autorizacao(h, src, arvore, set())
    ]
    assert not desprotegidos, (
        "handler(s) do Telegram SEM checagem de autorizacao: "
        + ", ".join(desprotegidos)
        + ". Delegue para _responder/_listar_grupos, chame _autorizado direto, "
          "ou justifique em ABERTOS (decisao de seguranca, nao atalho).")


def test_menu_nao_responde_a_estranho():
    """Regressao: /start, /menu e /ajuda respondiam a qualquer um, revelando a
    lista de comandos e a LOJA ATIVA."""
    src = FONTE.read_text(encoding="utf-8")
    corpo = src[src.index("async def cmd_start"):src.index("async def cmd_id")]
    assert "_autorizado" in corpo


def test_id_continua_aberto_de_proposito():
    """`/id` e a porta de entrada: sem ele o dono nao descobre o proprio chat id
    para se autorizar. Devolve SO o id de quem perguntou."""
    src = FONTE.read_text(encoding="utf-8")
    corpo = src[src.index("async def cmd_id"):]
    corpo = corpo[:corpo.index("\n\n\n")]
    assert "_autorizado" not in corpo
    assert "effective_chat.id" in corpo, "so pode revelar o id de QUEM PERGUNTOU"
