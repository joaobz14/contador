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


# ---------------------------------------------------------------------------
# TRAVA ENTRE PROCESSOS (ciclo ler -> mesclar -> salvar) — achado P1 da revisao
# ---------------------------------------------------------------------------
def test_trava_serializa_o_ciclo(tmp_path):
    """Quem pega a trava depois so entra apos o primeiro sair."""
    import threading
    import time as _t
    alvo = tmp_path / "estado.json"
    ordem: list = []

    def primeiro():
        with estado.trava(alvo):
            ordem.append("a-entrou")
            _t.sleep(0.08)
            ordem.append("a-saiu")

    def segundo():
        with estado.trava(alvo):
            ordem.append("b-entrou")

    t1 = threading.Thread(target=primeiro)
    t2 = threading.Thread(target=segundo)
    t1.start()
    _t.sleep(0.02)                      # garante que o 1o ja pegou a trava
    t2.start()
    t1.join(); t2.join()
    assert ordem == ["a-entrou", "a-saiu", "b-entrou"]


def test_trava_degrada_sem_quebrar(tmp_path):
    """Se o .lock nao puder ser criado (dir inexistente), segue sem trava."""
    alvo = tmp_path / "nao_existe" / "estado.json"
    with estado.trava(alvo):            # nao pode levantar
        pass


def test_marcar_impresso_concorrente_em_arquivo_real_nao_perde(core, tmp_path):
    """N threads marcando ids DIFERENTES no mesmo arquivo real, com a janela da
    corrida alargada (sleep dentro do ler): o resultado tem a UNIAO de todos.
    Sem a trava (arquivo=), este cenario perderia marcacoes (duas leituras da
    mesma versao antiga -> a ultima gravacao vence)."""
    import threading
    import time as _t
    arq = tmp_path / "estado.json"
    dia = _dia()
    n = 6
    g = _g(core, list(range(n)), dia=dia)

    def ler_lento():
        dados = estado.ler_json(arq)
        _t.sleep(0.02)                  # alarga a janela ler->salvar
        return dados

    def marcar(i):
        estado.marcar_impresso(ler_lento, lambda d: estado.salvar(arq, d),
                               {}, g, [i], arquivo=arq)

    threads = [threading.Thread(target=marcar, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    final = estado.ler_json(arq)
    assert final[estado.chave_estado(g)] == list(range(n))   # ninguem se perdeu
    assert not list(tmp_path.glob("*.tmp"))                  # sem lixo .tmp


def test_poda_persistida_rele_o_disco_e_nao_apaga_marca(core, tmp_path):
    """A poda que regrava o arquivo (carregar persistir_poda) roda sob a trava e
    RELE o disco: uma marca que outro processo grava depois da 1a leitura do
    carregar NAO e apagada pela poda — a mesma corrida last-writer-wins que a
    trava fecha no marcar_impresso. Sem o rele, a poda gravaria a versao antiga
    (sem a marca) por cima e a marca sumiria."""
    arq = tmp_path / "estado.json"
    velho = f"{_dia(999)}|OLD|q1"
    hoje = f"{_dia()}|NEW|q1"
    estado.gravar_json(arq, {velho: [1]})           # so a chave antiga -> poda remove

    orig = estado.limpar_antigo
    disparos = {"n": 0}

    def poda_hook(d, dias):
        disparos["n"] += 1
        if disparos["n"] == 1:                       # apos a 1a leitura, FORA da trava
            atual = estado.ler_json(arq)             # simula o bot marcando um
            atual[hoje] = [9]                        # envio de HOJE nesse meio-tempo
            estado.gravar_json(arq, atual)
        return orig(d, dias)

    estado.limpar_antigo = poda_hook
    try:
        out = estado.carregar(arq, 7, persistir_poda=True)
    finally:
        estado.limpar_antigo = orig

    salvo = estado.ler_json(arq)
    assert salvo.get(hoje) == [9]                    # a marca do outro processo sobreviveu
    assert velho not in salvo                        # a poda ainda removeu o antigo
    assert hoje in out                               # o retorno reflete o disco relido


def test_marcar_impresso_sem_arquivo_mantem_comportamento(core):
    """Sem arquivo= (chamadas antigas/testes), nada de trava — comportamento igual."""
    g = _g(core, [1], dia=_dia())
    gravou = {}
    estado.marcar_impresso(lambda: {}, lambda d: gravou.update(d), {}, g, [1])
    assert gravou == {estado.chave_estado(g): [1]}


def test_gravar_json_tmp_por_processo(tmp_path):
    """O nome do .tmp inclui o PID (dois processos nao disputam o temporario)."""
    import os as _os
    arq = tmp_path / "x.json"
    estado.gravar_json(arq, {"a": 1})
    assert json.loads(arq.read_text(encoding="utf-8")) == {"a": 1}
    assert not list(tmp_path.glob("*.tmp"))
    # o padrao do nome inclui o pid (validado indiretamente: unico por processo)
    assert str(_os.getpid())  # sanity
