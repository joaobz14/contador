"""Camada comum de estado de impressao (estado.py): API publica, merge
concorrente, poda por idade e o seam de gravacao injetavel. As regras ja sao
exercitadas via nucleo/shopee; aqui elas ficam ancoradas no proprio modulo."""
import json
from datetime import datetime, timedelta, timezone

import estado
from conftest import make_grupo

TZ = timezone(timedelta(hours=-3))


def _dia(delta=0):
    return (datetime.now(TZ).date() - timedelta(days=delta)).isoformat()


def _g(core, ids, chave="K", qtd=1, dia=""):
    g = make_grupo(core, ids, chave=chave, qtd=qtd)
    g.dia = dia
    return g


# ------------------------------------------------------------------ puras
def test_chave_usa_dia_do_grupo(core):
    g = _g(core, [1], chave="SKU", qtd=2, dia="2026-06-25")
    assert estado.chave_estado(g) == "2026-06-25|SKU|q2"


def test_status_pendente_parcial_impresso(core):
    g = _g(core, [10, 20, 30], dia=_dia())
    assert estado.status_grupo({}, g) == "pendente"
    parcial = {estado.chave_estado(g): [20]}
    assert estado.status_grupo(parcial, g) == "parcial"
    assert estado.envios_pendentes(parcial, g) == [10, 30]
    cheio = {estado.chave_estado(g): [10, 20, 30]}
    assert estado.status_grupo(cheio, g) == "impresso"


def test_formato_legado_string_impresso(core):
    g = _g(core, [1, 2], dia=_dia())
    legado = {estado.chave_estado(g): "impresso"}
    assert estado.status_grupo(legado, g) == "impresso"
    assert estado.impressos(legado, g) == {1, 2}


def test_envio_novo_reabre_como_parcial(core):
    g = _g(core, [1, 2], dia=_dia())
    est = {estado.chave_estado(g): [1, 2]}
    g.shipment_ids.append(9)                      # chegou envio novo
    assert estado.status_grupo(est, g) == "parcial"


def test_limpar_antigo_descarta_fora_da_janela_e_legado():
    misto = {
        f"{_dia(1)}|A|q1": [1],
        f"{_dia(999)}|B|q1": [2],                 # muito antigo
        "sem-data": [3],                          # chave sem data valida
    }
    assert estado.limpar_antigo(misto, 7) == {f"{_dia(1)}|A|q1": [1]}


# -------------------------------------------------------- arquivo / merge
def test_carregar_persistir_poda_regrava(core, tmp_path):
    arq = tmp_path / "e.json"
    estado.gravar_json(arq, {f"{_dia(999)}|X|q1": [1], f"{_dia(0)}|Y|q1": [2]})
    out = estado.carregar(arq, 7, persistir_poda=True)
    assert out == {f"{_dia(0)}|Y|q1": [2]}
    assert json.loads(arq.read_text()) == out    # regravou o arquivo podado


def test_carregar_sem_persistir_nao_regrava(core, tmp_path):
    arq = tmp_path / "e.json"
    original = {f"{_dia(999)}|X|q1": [1], f"{_dia(0)}|Y|q1": [2]}
    estado.gravar_json(arq, original)
    out = estado.carregar(arq, 7, persistir_poda=False)
    assert out == {f"{_dia(0)}|Y|q1": [2]}        # poda em memoria
    assert json.loads(arq.read_text()) == original  # arquivo intacto


def test_marcar_impresso_merge_last_writer(core):
    """Tela marca [5], bot (com memoria velha) marca [6]: nenhum some (inv. 5)."""
    g = _g(core, [5, 6], dia=_dia())
    disco = {}                                    # "arquivo" em memoria
    ler = lambda: dict(disco)
    salvar = lambda d: disco.update(d)
    et_tela, et_bot = {}, {}
    estado.marcar_impresso(ler, salvar, et_tela, g, [5])
    estado.marcar_impresso(ler, salvar, et_bot, g, [6])
    assert disco[estado.chave_estado(g)] == [5, 6]
    assert et_bot[estado.chave_estado(g)] == [5, 6]


def test_marcar_impresso_grava_pelo_seam_injetado(core):
    """O salvar_fn injetado e o unico caminho de escrita (nada vaza pro disco real)."""
    g = _g(core, [1], dia=_dia())
    gravou = {}
    estado.marcar_impresso(lambda: {}, lambda d: gravou.update(d), {}, g, [1])
    assert gravou == {estado.chave_estado(g): [1]}
