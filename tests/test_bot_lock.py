"""Testes do lock de PID do bot (core.bot_ja_rodando/iniciar_bot_em_segundo_plano) —
a tela usa isso para subir o bot junto, sem duplicar. subprocess/tasklist real
so existe no Windows, entao aqui so testamos a LOGICA (com subprocess.run
substituido por um fake) — nunca o comando de verdade.
"""
from __future__ import annotations

import subprocess

import pytest

import separador_etiquetas_ml as core


@pytest.fixture(autouse=True)
def _lock_isolado(tmp_path, monkeypatch):
    """Cada teste usa seu proprio ARQUIVO_LOCK_BOT (nunca o do projeto real)."""
    monkeypatch.setattr(core, "ARQUIVO_LOCK_BOT", tmp_path / "bot.lock")


# ------------------------------------------------------------------ _pid_vivo
def test_pid_vivo_quando_tasklist_lista_o_pid(monkeypatch):
    def _fake_run(cmd, **kw):
        assert cmd[0] == "tasklist"
        return subprocess.CompletedProcess(cmd, 0, stdout="python.exe  1234 Console  1  10.000 K\n")

    monkeypatch.setattr(core.subprocess, "run", _fake_run)
    assert core._pid_vivo(1234) is True


def test_pid_nao_vivo_quando_tasklist_nao_lista(monkeypatch):
    def _fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout="INFO: No tasks running.\n")

    monkeypatch.setattr(core.subprocess, "run", _fake_run)
    assert core._pid_vivo(9999) is False


def test_pid_vivo_assume_vivo_quando_comando_falha(monkeypatch):
    def _fake_run(cmd, **kw):
        raise OSError("tasklist ausente")

    monkeypatch.setattr(core.subprocess, "run", _fake_run)
    # Em duvida, assume vivo -- nao arrisca subir um 2o bot por falso-negativo.
    assert core._pid_vivo(1) is True


# -------------------------------------------------------------- bot_ja_rodando
def test_bot_ja_rodando_falso_sem_lock():
    assert core.bot_ja_rodando() is False


def test_bot_ja_rodando_true_com_pid_vivo(monkeypatch):
    core.ARQUIVO_LOCK_BOT.write_text("4242", encoding="utf-8")
    monkeypatch.setattr(core, "_pid_vivo", lambda pid: pid == 4242)
    assert core.bot_ja_rodando() is True


def test_bot_ja_rodando_false_com_lock_travado_pid_morto(monkeypatch):
    """Lock travado (processo morreu sem limpar -- queda de energia, kill
    forcado): PID morto -> trata como "nao esta rodando", nao trava a tela
    pra sempre."""
    core.ARQUIVO_LOCK_BOT.write_text("4242", encoding="utf-8")
    monkeypatch.setattr(core, "_pid_vivo", lambda pid: False)
    assert core.bot_ja_rodando() is False


def test_bot_ja_rodando_false_com_lock_corrompido():
    core.ARQUIVO_LOCK_BOT.write_text("nao-e-um-pid", encoding="utf-8")
    assert core.bot_ja_rodando() is False


# ------------------------------------------------------ iniciar_bot_em_segundo_plano
def test_iniciar_bot_nao_faz_nada_fora_do_windows(monkeypatch):
    monkeypatch.setattr(core.os, "name", "posix")
    chamado = []
    monkeypatch.setattr(core.subprocess, "Popen", lambda *a, **kw: chamado.append(1))
    assert core.iniciar_bot_em_segundo_plano() == "nao_windows"
    assert chamado == []


def test_iniciar_bot_nao_duplica_se_ja_rodando(monkeypatch):
    monkeypatch.setattr(core.os, "name", "nt")
    monkeypatch.setattr(core, "bot_ja_rodando", lambda: True)
    chamado = []
    monkeypatch.setattr(core.subprocess, "Popen", lambda *a, **kw: chamado.append(1))
    assert core.iniciar_bot_em_segundo_plano() == "ja_rodando"
    assert chamado == []


def test_iniciar_bot_nao_sobe_se_bat_nao_existe(monkeypatch, tmp_path):
    monkeypatch.setattr(core.os, "name", "nt")
    monkeypatch.setattr(core, "bot_ja_rodando", lambda: False)
    monkeypatch.setattr(core, "PASTA_SCRIPT", tmp_path)  # sem atalhos/ aqui
    chamado = []
    monkeypatch.setattr(core.subprocess, "Popen", lambda *a, **kw: chamado.append(1))
    assert core.iniciar_bot_em_segundo_plano() == "bat_ausente"
    assert chamado == []


def test_iniciar_bot_sobe_o_bat_sem_janela(monkeypatch, tmp_path):
    monkeypatch.setattr(core.os, "name", "nt")
    monkeypatch.setattr(core, "bot_ja_rodando", lambda: False)
    monkeypatch.setattr(core, "PASTA_SCRIPT", tmp_path)
    (tmp_path / "atalhos").mkdir()
    bat = tmp_path / "atalhos" / "Iniciar Bot (auto).bat"
    bat.write_text("@echo off\n", encoding="utf-8")

    chamadas = []
    monkeypatch.setattr(core.subprocess, "Popen",
                        lambda cmd, **kw: chamadas.append((cmd, kw)))
    # CREATE_NO_WINDOW so existe no Windows de verdade; simulamos aqui.
    monkeypatch.setattr(core.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

    assert core.iniciar_bot_em_segundo_plano() == "subiu"

    assert len(chamadas) == 1
    cmd, kw = chamadas[0]
    assert cmd[0] == "cmd"
    assert str(bat) in cmd
    assert kw["creationflags"] == 0x08000000
    assert kw["cwd"] == str(tmp_path)
