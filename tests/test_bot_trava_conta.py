"""Trava da conta ativa no bot (achado da varredura por blocos, 2026-08-03).

`core.definir_conta()` troca GLOBAIS do nucleo. O bot roda coisas em paralelo
(`asyncio.to_thread`): o job do alerta percorre TODAS as contas enquanto o dono
pode mandar /imprimir de outra. Sem trava, o comando le a credencial e o estado
da conta que o JOB apontou naquele instante — imprime com o token errado e grava
no estado_grupos.json da OUTRA conta.
"""
from __future__ import annotations

import threading

import bot_telegram as bot
import separador_etiquetas_ml as core


def test_trava_existe_e_e_reentrante():
    """RLock, nao Lock: `_dados_alerta_da_conta` roda dentro dela e chama
    funcoes que tambem a pegam — reentrancia na mesma thread nao pode travar."""
    with bot.TRAVA_CONTA:
        with bot.TRAVA_CONTA:               # travaria com um Lock simples
            pass


def test_comando_nao_le_a_conta_que_o_job_apontou(tmp_path, monkeypatch):
    """A prova: com a trava, o comando do dono so le os globais quando o job
    NAO esta no meio da troca."""
    monkeypatch.setattr(core, "PASTA_CONTAS", tmp_path / "contas")
    for c in ("Cozilatti", "Gastromaq"):
        core.definir_conta(c)

    visto: list[str] = []
    parar = threading.Event()

    def job_do_alerta():
        # Igual ao _dados_alerta_da_conta_travado: troca, trabalha, restaura.
        while not parar.is_set():
            with bot.TRAVA_CONTA:
                core.definir_conta("Gastromaq")
                for _ in range(50):         # a "rede" do alerta
                    pass
                core.definir_conta("Cozilatti")

    def comando_do_dono():
        for _ in range(200):
            with bot.TRAVA_CONTA:
                core.definir_conta("Cozilatti")      # a conta que o dono escolheu
                for _ in range(50):
                    pass
                visto.append(core.ARQUIVO_ESTADO.parent.name)

    t = threading.Thread(target=job_do_alerta, daemon=True)
    t.start()
    comando_do_dono()
    parar.set()
    t.join(timeout=5)

    assert visto, "o comando precisa ter rodado"
    assert set(visto) == {"Cozilatti"}, (
        f"o comando leu a conta errada em {sum(1 for v in visto if v != 'Cozilatti')} "
        "de {len(visto)} leituras")


def test_caminhos_que_dependem_da_conta_estao_travados():
    """Guarda de regressao: quem le/grava por conta TEM de passar pela trava.
    Um caminho novo esquecido aqui reintroduz a corrida em silencio."""
    import inspect

    for nome in ("_coletar", "_imprimir_grupo", "_prontos", "_trocar_conta",
                 "_dados_alerta_da_conta"):
        fonte = inspect.getsource(getattr(bot, nome))
        assert "TRAVA_CONTA" in fonte, f"{nome} nao esta sob a trava da conta"
