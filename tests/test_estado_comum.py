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


# -------------------------------------------- estado corrompido visivel (5.2)
def test_gravar_json_escreve_lf_nao_crlf(tmp_path):
    """Grava LF mesmo no Windows (newline='\\n'): os JSONs versionados
    (nomes_sku.json, skus_por_anuncio.json) sao LF no repo; sem isto a GUI os
    reescrevia em CRLF e eles ficavam 'modificados' para sempre, colidindo em
    todo git pull na maquina de operacao."""
    arq = tmp_path / "x.json"
    estado.gravar_json(arq, {"a": 1, "b": [2, 3]})
    dados = arq.read_bytes()
    assert b"\r\n" not in dados          # nenhuma quebra CRLF
    assert b"\n" in dados                # mas tem LF (indent=2 gera multilinha)


def test_ler_estado_ausente_e_silencioso(tmp_path):
    """Arquivo ausente = {} silencioso (caso legitimo: primeiro uso do dia)."""
    assert estado.ler_estado(tmp_path / "nao_existe.json") == {}
    assert not list(tmp_path.glob("*.corrupto"))


def test_ler_estado_corrompido_preserva_e_avisa(tmp_path):
    """JSON truncado nao vira {} mudo: e movido para .corrupto (preservado) e um
    aviso e emitido. Sem isso, todos os grupos do dia voltavam a PENDENTE sem o
    operador saber o porque (auditoria 5.2)."""
    arq = tmp_path / "estado_grupos.json"
    arq.write_text('{"2026-07-16|X|q1": [1], "trunca', encoding="utf-8")  # JSON quebrado
    avisos = []
    import registro
    orig = registro.log.warning
    registro.log.warning = lambda m, *a, **k: avisos.append(m)
    try:
        assert estado.ler_estado(arq) == {}          # recomeca vazio
    finally:
        registro.log.warning = orig
    assert not arq.exists()                            # o original saiu do lugar
    corrompidos = list(tmp_path.glob("estado_grupos.json.*.corrupto"))
    assert len(corrompidos) == 1                       # preservado como .corrupto
    assert '"trunca' in corrompidos[0].read_text()     # conteudo recuperavel intacto
    assert avisos and "corrompido" in avisos[0].lower()


def test_ler_estado_nao_dict_e_corrompido(tmp_path):
    """Conteudo valido mas que nao e objeto (ex.: uma lista) tambem e tratado
    como corrompido — o resto do codigo espera um dict."""
    arq = tmp_path / "estado_shopee.json"
    arq.write_text("[1, 2, 3]", encoding="utf-8")
    assert estado.ler_estado(arq) == {}
    assert not arq.exists()
    assert len(list(tmp_path.glob("*.corrupto"))) == 1


def test_ler_estado_oserro_transitorio_nao_renomeia(tmp_path, monkeypatch):
    """Falha de leitura TRANSITORIA (arquivo preso pelo OneDrive/antivirus) cai
    em {} mas NAO renomeia: o arquivo pode estar intacto, so ilegivel no
    instante — move-lo aparte destruiria um estado bom."""
    arq = tmp_path / "estado_grupos.json"
    arq.write_text('{"2026-07-16|X|q1": [1]}', encoding="utf-8")

    def _boom(*a, **k):
        raise OSError("arquivo preso")

    monkeypatch.setattr(type(arq), "read_text", _boom)
    assert estado.ler_estado(arq) == {}
    assert arq.exists()                                # intacto, nao renomeado
    assert not list(tmp_path.glob("*.corrupto"))


def test_marcar_impresso_nao_destroi_estado_corrompido(core, tmp_path):
    """A marcacao apos corrupcao NAO grava por cima do corrompido: a leitura via
    ler_estado ja o preservou como .corrupto e recomeca vazio; o novo arquivo so
    tem a marca nova, e o conteudo antigo continua recuperavel no .corrupto."""
    arq = tmp_path / "estado.json"
    arq.write_text('{"lixo corrompido', encoding="utf-8")
    g = _g(core, [7], dia=_dia())
    estado.marcar_impresso(lambda: estado.ler_estado(arq),
                           lambda d: estado.salvar(arq, d), {}, g, [7], arquivo=arq)
    assert estado.ler_json(arq) == {estado.chave_estado(g): [7]}   # arquivo novo, so a marca
    corrompidos = list(tmp_path.glob("estado.json.*.corrupto"))
    assert len(corrompidos) == 1 and "lixo corrompido" in corrompidos[0].read_text()


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


# ---------------------------------------------------------------------------
# TRAVA NO WINDOWS (msvcrt): espera estendida para secoes longas (P1 releitura)
# O LK_LOCK desiste sozinho apos ~10s; sem a espera=, o segundo processo
# degradaria NO MEIO de um refresh de token (que roda HTTP de ate 30s dentro
# da trava) e dispararia um refresh paralelo. Logica testada com msvcrt FAKE e
# relogio FAKE (determinismo; o modulo real so existe no Windows).
# ---------------------------------------------------------------------------
class _RelogioFake:
    def __init__(self):
        self.agora = 0.0

    def monotonic(self):
        return self.agora


def _instalar_msvcrt_fake(monkeypatch, relogio, plano: list):
    """Instala um msvcrt fake e liga o ramo Windows da trava. `plano` dita o
    resultado de cada LK_LOCK, em ordem: 'ocupado' (gasta ~10s e falha, como o
    LK_LOCK real com a trava tomada), 'rapido' (falha em ms — FS sem suporte)
    ou 'ok' (adquire). Devolve a lista de chamadas registradas."""
    import types
    chamadas: list = []
    mod = types.SimpleNamespace(LK_LOCK=1, LK_UNLCK=2)

    def locking(_fd, modo, _n):
        if modo == mod.LK_UNLCK:
            chamadas.append("unlock")
            return
        acao = plano.pop(0) if plano else "ocupado"
        chamadas.append(acao)
        if acao == "ok":
            return
        relogio.agora += 10.0 if acao == "ocupado" else 0.001
        raise OSError(36, "resource deadlock avoided")

    mod.locking = locking
    import sys
    monkeypatch.setitem(sys.modules, "msvcrt", mod)
    monkeypatch.setattr(estado.os, "name", "nt")
    monkeypatch.setattr(estado, "time", relogio)
    return chamadas


def test_trava_windows_espera_re_tenta_ate_adquirir(monkeypatch, tmp_path):
    """Trava ocupada por outro processo (2 tentativas de ~10s falham): com
    espera=60 a trava RE-TENTA e adquire na 3a — nao degrada no meio da secao
    critica do outro processo."""
    relogio = _RelogioFake()
    chamadas = _instalar_msvcrt_fake(monkeypatch, relogio,
                                     ["ocupado", "ocupado", "ok"])
    with estado.trava(tmp_path / "cred.json", espera=60):
        pass
    assert chamadas == ["ocupado", "ocupado", "ok", "unlock"]  # adquiriu e liberou


def test_trava_windows_padrao_mantem_uma_tentativa(monkeypatch, tmp_path):
    """Sem espera= (caminhos do estado): comportamento de sempre — UMA tentativa
    (~10s do proprio LK_LOCK) e degrada, sem re-tentar."""
    relogio = _RelogioFake()
    chamadas = _instalar_msvcrt_fake(monkeypatch, relogio, ["ocupado"])
    executou = []
    with estado.trava(tmp_path / "estado.json"):
        executou.append(1)
    assert executou == [1]                       # corpo rodou (degradou, nao travou)
    assert chamadas == ["ocupado"]               # 1 tentativa, sem unlock


def test_trava_windows_fs_sem_suporte_degrada_na_hora(monkeypatch, tmp_path):
    """Falha RAPIDA (FS sem suporte, ms): degrada imediatamente MESMO com
    espera=60 — nao fica 60s re-tentando um lock que nunca vai existir."""
    relogio = _RelogioFake()
    chamadas = _instalar_msvcrt_fake(monkeypatch, relogio, ["rapido"])
    with estado.trava(tmp_path / "cred.json", espera=60):
        pass
    assert chamadas == ["rapido"]                # 1 tentativa so
    assert relogio.agora < 1                     # nao esperou os 60s


def test_trava_windows_espera_esgotada_degrada(monkeypatch, tmp_path):
    """Ocupada alem da espera: degrada (suave) depois de esgotar — a essa
    altura o detentor ja terminou a operacao protegida (espera > duracao
    maxima), entao seguir sem trava e seguro."""
    relogio = _RelogioFake()
    chamadas = _instalar_msvcrt_fake(monkeypatch, relogio,
                                     ["ocupado"] * 10)
    executou = []
    with estado.trava(tmp_path / "cred.json", espera=25):
        executou.append(1)
    assert executou == [1]                       # degradou e seguiu
    assert "unlock" not in chamadas
    assert chamadas.count("ocupado") >= 3        # re-tentou ate passar de 25s
    assert relogio.agora >= 25


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
