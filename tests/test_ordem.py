"""Ordem de exibicao/impressao (ordenar_grupos): mantem os blocos por
quantidade; no bloco 'Quantidade por pedido = 1' segue a ordem da aba Nomes (SKU
nao cadastrado vai pro fim, em ordem natural); blocos de 2+ ficam por nome."""
from conftest import make_grupo


def _g(core, chave, qtd, nome=None):
    return make_grupo(core, [1], chave=chave, nome=nome or chave, qtd=qtd)


def _nomes(core, tmp_path, monkeypatch, ordem: dict):
    arq = tmp_path / "nomes.json"
    monkeypatch.setattr(core, "ARQUIVO_NOMES", arq)
    core.salvar_nomes(ordem)


def test_qtd1_segue_a_ordem_da_aba_nomes(core, tmp_path, monkeypatch):
    _nomes(core, tmp_path, monkeypatch, {"A01": "x", "A01F": "y", "A02": "z"})
    grupos = [_g(core, "A02", 1), _g(core, "A01F", 1), _g(core, "A01", 1)]
    assert [g.chave for g in core.ordenar_grupos(grupos)] == ["A01", "A01F", "A02"]


def test_qtd1_nao_cadastrado_vai_pro_fim_em_ordem_natural(core, tmp_path, monkeypatch):
    _nomes(core, tmp_path, monkeypatch, {"A01": "x"})           # so A01 cadastrado
    grupos = [_g(core, "A10", 1), _g(core, "A2", 1), _g(core, "A01", 1)]
    # cadastrado primeiro; nao cadastrados depois em ordem natural (A2 antes de A10)
    assert [g.chave for g in core.ordenar_grupos(grupos)] == ["A01", "A2", "A10"]


def test_blocos_por_quantidade_sao_mantidos(core, tmp_path, monkeypatch):
    _nomes(core, tmp_path, monkeypatch, {"Z9": "z"})            # Z9 no topo do qtd1
    grupos = [_g(core, "A01", 2, "aaa"), _g(core, "Z9", 1, "zzz"), _g(core, "A00", 1, "bbb")]
    ordenados = core.ordenar_grupos(grupos)
    qtds = [g.quantidade for g in ordenados]
    assert qtds == sorted(qtds)                                # qtd 1 antes de qtd 2
    q1 = [g.chave for g in ordenados if g.quantidade == 1]
    assert q1 == ["Z9", "A00"]        # cadastrado (Z9) antes do nao cadastrado (A00)


def test_qtd_maior_que_1_ordena_por_nome_ignora_aba_nomes(core, tmp_path, monkeypatch):
    _nomes(core, tmp_path, monkeypatch, {"B": "0", "A": "1"})   # nao afeta o bloco qtd 2
    grupos = [_g(core, "A", 2, "zzz"), _g(core, "B", 2, "aaa")]
    # por nome (aaa < zzz), nao pela ordem da aba Nomes
    assert [g.chave for g in core.ordenar_grupos(grupos)] == ["B", "A"]


def test_sem_aba_nomes_qtd1_cai_em_ordem_natural(core, tmp_path, monkeypatch):
    _nomes(core, tmp_path, monkeypatch, {})                     # nada cadastrado
    grupos = [_g(core, "A10", 1), _g(core, "A2", 1), _g(core, "A1", 1)]
    assert [g.chave for g in core.ordenar_grupos(grupos)] == ["A1", "A2", "A10"]
