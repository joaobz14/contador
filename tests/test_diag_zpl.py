"""Guardioes do diagnostico de etiqueta em branco (tools/diag_zpl.py).

O valor da ferramenta e o VEREDITO: ela existe para dizer se a pagina em branco
saiu do arquivo ou nao. Um diagnostico que se cala diante do defeito e pior que
nenhum — mandaria procurar no lugar errado (calibrar a impressora quando o
problema esta no ZPL, ou vice-versa). Por isso os testes cobrem os dois lados:
acusa quando ha causa no arquivo, e fica quieto quando o arquivo esta limpo.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import diag_zpl  # noqa: E402

# Um lote saudavel do ML: ENVIO (grafico inline) + DANFE, mesma midia nos dois.
ENVIO = "^XA^PW812^LL1218^MNY^FO10,10^GFA,1,1,1,dados^FS^XZ"
# O bloco da nota carrega a palavra "DANFE" no proprio conteudo — e por ela que
# tanto o carimbo (carimbar_zpl) quanto este diagnostico o reconhecem.
DANFE = "^XA^PW812^LL1218^MNY^FO0,20^FDDANFE SIMPLIFICADA^FS^FO0,800^FDA01 - 2L 110^FS^XZ"
LOTE_OK = f"{ENVIO}\n{DANFE}"


def test_lote_saudavel_nao_acusa_nada():
    blocos, avisos = diag_zpl.analisar(LOTE_OK)
    assert len(blocos) == 2
    assert avisos == []


def test_reconhece_qual_bloco_e_a_danfe():
    blocos, _ = diag_zpl.analisar(LOTE_OK)
    assert [b["danfe"] for b in blocos] == [False, True]


def test_acusa_pagina_em_branco_dentro_do_arquivo():
    blocos, avisos = diag_zpl.analisar(f"{LOTE_OK}\n^XA^XZ")
    assert blocos[2]["vazio"]
    assert any("BLOCO EM BRANCO" in a for a in avisos)


def test_bloco_sem_nada_a_desenhar_conta_como_branco():
    """So comando de midia, nenhum campo: sai papel em branco do mesmo jeito."""
    _, avisos = diag_zpl.analisar(f"{LOTE_OK}\n^XA^PW812^LL1218^MNY^XZ")
    assert any("BLOCO EM BRANCO" in a for a in avisos)


def test_acusa_troca_de_modo_de_midia_no_meio_do_lote():
    """^MNN (midia continua) seguido de ^MNY faz a impressora procurar o gap —
    e esse avanco sai como etiqueta em branco. E a causa que so o arquivo revela."""
    lote = ENVIO.replace("^MNY", "^MNN") + "\n" + DANFE
    _, avisos = diag_zpl.analisar(lote)
    assert any("^MN MUDA" in a for a in avisos)


def test_acusa_comprimento_divergente_entre_blocos():
    lote = ENVIO.replace("^LL1218", "^LL800") + "\n" + DANFE
    _, avisos = diag_zpl.analisar(lote)
    assert any("^LL MUDA" in a for a in avisos)


def test_acusa_pedido_de_copia_extra():
    _, avisos = diag_zpl.analisar(LOTE_OK.replace("^MNY^FO0,20", "^MNY^PQ2,0,0,N^FO0,20"))
    assert any("^PQ" in a for a in avisos)


def test_uma_copia_so_nao_e_aviso():
    _, avisos = diag_zpl.analisar(LOTE_OK.replace("^MNY^FO0,20", "^MNY^PQ1,0,0,N^FO0,20"))
    assert avisos == []


def test_nunca_expoe_conteudo_de_campo():
    """A etiqueta leva nome, endereco e CEP do comprador e o repositorio e
    publico: o relatorio pode citar comando e numero, nunca o dado."""
    lote = ENVIO + "\n^XA^PW812^LL1218^MNY^FO0,800^FDRUA DAS FLORES 217 - JOAO^FS^XZ"
    blocos, avisos = diag_zpl.analisar(lote)
    texto = " ".join(avisos) + repr(blocos)
    assert "RUA DAS FLORES" not in texto
    assert "JOAO" not in texto
