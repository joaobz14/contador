"""Confirmação de impressão: o retorno do app da Zebra.

A entrega é por arquivo (ZIP na Downloads) e até então a tela não tinha como
saber se o monitor chegou a rodar. Com "Excluir após imprimir" ligado, o arquivo
SOME quando imprime — e o log do monitor avança enquanto ele trabalha. São os
dois sinais que `aguardar_impressao` observa.

Nada aqui decide por ninguém: o resultado só informa a pergunta "as etiquetas
saíram corretamente?", que continua sendo do operador (invariante 1).
"""
from __future__ import annotations

import pytest


@pytest.fixture
def saida(core, monkeypatch, tmp_path):
    """Pasta de saída isolada + log do monitor apontado para o tmp."""
    monkeypatch.setattr(core, "PASTA_DOWNLOADS", tmp_path)
    monkeypatch.setattr(core, "ARQUIVO_LOG_MONITOR", tmp_path / "zebra_usb_log.txt")
    monkeypatch.setattr(core.time, "sleep", lambda _s: None)
    return tmp_path


def _zip(pasta, nome: str):
    alvo = pasta / nome
    alvo.write_bytes(b"PK\x03\x04")
    return alvo


def _log_parado(core, quando_atras: float = 3600.0):
    """Cria o log do monitor com mtime ANTIGO — o unico caso em que o ⚠️ pode
    aparecer: log encontrado E provadamente sem avanco."""
    import os
    import time as _t

    core.ARQUIVO_LOG_MONITOR.write_text("[08:00:00] sessao anterior", encoding="utf-8")
    velho = _t.time() - quando_atras
    os.utime(core.ARQUIVO_LOG_MONITOR, (velho, velho))


# ── Reconhecer as nossas saídas na pasta ─────────────────────────────────────

def test_reconhece_os_zips_de_etiqueta(core, saida):
    _zip(saida, "etiqueta de envio - LOTES x2 - 143012.zip")
    _zip(saida, "etiqueta shopee - lote 3 - 143012.zip")
    assert len(core.saidas_na_pasta()) == 2


def test_ignora_o_que_nao_e_nosso(core, saida):
    """Downloads de verdade tem de tudo — só os nossos podem entrar na conta."""
    _zip(saida, "fotos.zip")
    _zip(saida, "boleto.pdf")
    (saida / "tmp_etiqueta de envio - x.zip.part").write_bytes(b"parcial")
    assert core.saidas_na_pasta() == set()


def test_pasta_inexistente_nao_levanta(core, monkeypatch, tmp_path):
    monkeypatch.setattr(core, "PASTA_DOWNLOADS", tmp_path / "nao_existe")
    assert core.saidas_na_pasta() == set()


def test_diferenca_entre_instantaneos_isola_o_lote_novo(core, saida):
    """É assim que a tela descobre quais arquivos são dela, sem receber o
    caminho de volta pela cadeia provedor→núcleo."""
    _zip(saida, "etiqueta de envio - antigo - 100000.zip")
    antes = core.saidas_na_pasta()

    novo = _zip(saida, "etiqueta de envio - LOTES x2 - 143012.zip")

    assert core.saidas_na_pasta() - antes == {novo}


# ── Os três sinais ───────────────────────────────────────────────────────────

def test_arquivo_sumiu_e_impresso(core, saida):
    """O monitor apaga após imprimir: sumiu = imprimiu. É a confirmação forte."""
    nosso = _zip(saida, "etiqueta de envio - x.zip")
    nosso.unlink()
    assert core.aguardar_impressao({nosso}) == "impresso"


def test_arquivo_parado_e_log_PARADO_e_sem_sinal(core, saida):
    """O ⚠️ exige PROVA: log encontrado e provadamente sem avanço."""
    nosso = _zip(saida, "etiqueta de envio - x.zip")
    _log_parado(core)
    assert core.aguardar_impressao({nosso}, espera=0) == "sem_sinal"


def test_sem_log_para_consultar_fica_CALADO(core, saida):
    """INCIDENTE 2026-07-30: um lote de 12 avisou "o monitor NÃO deu sinal" com a
    impressora trabalhando normal. Dois fatos somados: em lote grande o arquivo
    não some dentro do teto (o monitor só o apaga na última etiqueta) E o log não
    pôde ser lido — a versão anterior tratava "não sei" como "monitor parado".

    Falso alarme é pior que aviso nenhum: ensina a ignorar o ⚠️, e aí ele perde a
    utilidade justamente no dia em que estiver certo.
    """
    nosso = _zip(saida, "etiqueta de envio - x.zip")
    assert not core.ARQUIVO_LOG_MONITOR.exists()
    assert core.aguardar_impressao({nosso}, espera=0) == "sem_saida"


def test_log_avancando_com_arquivo_parado_e_imprimindo(core, saida):
    """Lote grande: o arquivo só some na última etiqueta, mas o log prova vida.

    Sem este sinal, um lote demorado apareceria como 'monitor fechado' e o
    operador iria procurar problema onde não há.
    """
    import time as _t

    inicio = _t.time() - 1          # o instante em que a tela mandou gerar
    nosso = _zip(saida, "etiqueta de envio - x.zip")
    core.ARQUIVO_LOG_MONITOR.write_text("[12:00:00] imprimindo...", encoding="utf-8")

    assert core.aguardar_impressao({nosso}, espera=0, desde=inicio) == "imprimindo"


def test_log_velho_nao_conta_como_vida(core, saida):
    """Log de uma sessão ANTERIOR não pode ser lido como monitor ativo agora."""
    import os
    import time as _t

    nosso = _zip(saida, "etiqueta de envio - x.zip")
    core.ARQUIVO_LOG_MONITOR.write_text("[08:00:00] sessao de ontem", encoding="utf-8")
    antigo = _t.time() - 3600
    os.utime(core.ARQUIVO_LOG_MONITOR, (antigo, antigo))

    assert core.aguardar_impressao({nosso}, espera=0) == "sem_sinal"


def test_sem_arquivo_nenhum_nao_ha_o_que_observar(core, saida):
    assert core.aguardar_impressao(set()) == "sem_saida"


def test_parte_do_lote_consumida_ainda_nao_e_impresso(core, saida):
    """Só vale 'impresso' quando TODOS sumiram — um ZIP preso é um lote parado."""
    a = _zip(saida, "etiqueta de envio - a.zip")
    b = _zip(saida, "etiqueta de envio - b.zip")
    a.unlink()
    _log_parado(core)
    assert core.aguardar_impressao({a, b}, espera=0) == "sem_sinal"


def test_sai_assim_que_o_arquivo_some(core, saida, monkeypatch):
    """Lote pequeno não pode fazer o operador esperar o teto inteiro."""
    nosso = _zip(saida, "etiqueta de envio - x.zip")
    voltas = []

    def _some(_s):
        voltas.append(1)
        nosso.unlink()                    # o monitor consumiu entre as checagens

    monkeypatch.setattr(core.time, "sleep", _some)
    assert core.aguardar_impressao({nosso}, espera=60) == "impresso"
    assert len(voltas) == 1, "esperou mais do que precisava"


def test_arquivo_preso_nao_e_confundido_com_impresso(core, saida, monkeypatch):
    """Best-effort e CONSERVADOR: se não dá para ler a pasta (antivírus, OneDrive
    segurando o arquivo), não se pode afirmar que sumiu — afirmar "foi impresso"
    sem ter visto o arquivo sair seria a pior mentira possível nesta tela."""
    nosso = _zip(saida, "etiqueta de envio - x.zip")

    def _explode(*_a, **_k):
        raise OSError("arquivo preso")

    monkeypatch.setattr(core.Path, "stat", _explode)
    # nem "impresso" (nao vimos sumir) nem ⚠️ (nao lemos o log): fica calado
    assert core.aguardar_impressao({nosso}, espera=0) == "sem_saida"


# ── Texto mostrado na confirmação ────────────────────────────────────────────

@pytest.mark.parametrize("sinal", ["impresso", "imprimindo", "sem_sinal"])
def test_cada_sinal_tem_texto(core, sinal):
    assert core.texto_sinal_monitor(sinal)


def test_sem_saida_nao_polui_a_pergunta(core):
    """Sem nada a dizer, a confirmação fica exatamente como era antes."""
    assert core.texto_sinal_monitor("sem_saida") == ""
    assert core.texto_sinal_monitor("qualquer_coisa") == ""


def test_aviso_de_monitor_parado_diz_o_que_fazer(core):
    texto = core.texto_sinal_monitor("sem_sinal")
    assert "Downloads" in texto and "aberto" in texto


def test_confirmacao_nunca_afirma_que_a_etiqueta_saiu_certa(core):
    """O monitor confirma que MANDOU imprimir — não que o papel saiu legível.

    Se um texto destes prometer mais do que o sinal prova, o operador para de
    conferir o papel e a invariante 1 (nada marcado sem etiqueta física) perde
    a sua única defesa real.
    """
    assert "saíram corretamente" not in core.texto_sinal_monitor("impresso")
