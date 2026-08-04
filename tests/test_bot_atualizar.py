"""Testes do /atualizar — `git pull` + reinicio pelo Telegram.

Existe porque o dono quase sempre está no celular quando sai versão nova, e
atualizar exigia estar NA MÁQUINA. O que este teste protege:

1. **Alteração local nunca é destruída.** `nomes_sku.json` e
   `skus_por_anuncio.json` são versionados E editados pela tela: com a árvore
   suja o comando **não puxa nada** e diz quais arquivos travaram — nada de
   descarte automático do trabalho do dono.
2. **Não atropela uma operação.** O pull (e o reinício logo depois) não pode
   cair no meio de um /imprimir — daí a `TRAVA_CONTA`.
3. **Só sai do ar se alguém for reiniciá-lo.** Sair sem o lançador com laço
   deixaria o bot morto; um bot mudo é pior que um bot desatualizado.
4. **Nenhum erro do git leva credencial para o chat** (um remoto https pode ter
   `usuario:token@` embutido).

Mesmo padrão dos outros testes do bot: pula se o telegram não importar.
"""
from __future__ import annotations

import asyncio
import subprocess

import pytest

try:
    import bot_telegram as bot
except BaseException as e:  # noqa: BLE001 - pyo3 PanicException herda de BaseException
    pytest.skip(f"bot_telegram indisponivel: {e}", allow_module_level=True)

import registro  # noqa: E402
import separador_etiquetas_ml as core  # noqa: E402

CHAT = 725104161


class _Bot:
    def __init__(self):
        self.enviadas: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text=None, **k):
        self.enviadas.append((chat_id, text if text is not None else k.get("text", "")))


class _Update:
    def __init__(self, chat_id=CHAT):
        self.effective_chat = type("C", (), {"id": chat_id})()


class _Ctx:
    def __init__(self, duble):
        self.bot = duble
        self.bot_data = {"cfg": {"chat_ids": {CHAT}, "chat_perguntas": 0,
                                 "webhook_perguntas": ""}}


def _resposta(saida="", erro="", codigo=0):
    return subprocess.CompletedProcess(args=["git"], returncode=codigo,
                                       stdout=saida, stderr=erro)


def _git_falso(monkeypatch, respostas: dict):
    """Dubla `_git` devolvendo a resposta conforme o 1o argumento (status/pull)."""
    chamadas: list[tuple] = []

    def _f(*args):
        chamadas.append(args)
        return respostas[args[0]]

    monkeypatch.setattr(bot, "_git", _f)
    return chamadas


# ------------------------------------------------------------ arvore suja
def test_alteracao_local_impede_o_pull_e_nao_destroi_nada(monkeypatch):
    chamadas = _git_falso(monkeypatch, {
        "status": _resposta(saida=" M nomes_sku.json\n M skus_por_anuncio.json\n"),
    })
    mudou, texto = bot._puxar_atualizacao()
    assert mudou is False
    assert "nomes_sku.json" in texto and "skus_por_anuncio.json" in texto
    assert [c[0] for c in chamadas] == ["status"], "nao pode nem tentar o pull"
    assert "checkout" not in texto and "reset" not in texto


def test_arvore_suja_lista_no_maximo_alguns_arquivos(monkeypatch):
    _git_falso(monkeypatch, {
        "status": _resposta(saida="".join(f" M arq{i}.py\n" for i in range(20))),
    })
    _, texto = bot._puxar_atualizacao()
    assert "e mais 14" in texto
    assert len(texto) < 700, "a mensagem tem de caber no chat"


def test_arquivo_nao_rastreado_nao_bloqueia(monkeypatch):
    """`--untracked-files=no`: um out.png solto na pasta nao atrapalha o pull."""
    _git_falso(monkeypatch, {"status": _resposta(saida="")})
    args = []
    monkeypatch.setattr(bot, "_git", lambda *a: (args.append(a), _resposta(saida=""))[1])
    bot._puxar_atualizacao()
    assert "--untracked-files=no" in args[0]


# ---------------------------------------------------------------- pull
def test_ja_estava_atualizado(monkeypatch):
    _git_falso(monkeypatch, {"status": _resposta(), "pull": _resposta("Already up to date.")})
    monkeypatch.setattr(bot, "_commit_do_disco", lambda: "abc1234")
    mudou, texto = bot._puxar_atualizacao()
    assert mudou is False
    assert "Ja estava na versao mais nova" in texto and "abc1234" in texto


def test_atualizou_mostra_de_para(monkeypatch):
    commits = iter(["abc1234", "def5678"])
    _git_falso(monkeypatch, {"status": _resposta(), "pull": _resposta("Updating...")})
    monkeypatch.setattr(bot, "_commit_do_disco", lambda: next(commits))
    mudou, texto = bot._puxar_atualizacao()
    assert mudou is True
    assert "abc1234" in texto and "def5678" in texto


def test_pull_e_sempre_ff_only(monkeypatch):
    """Numa pasta de operacao o historico so anda para a frente. Um merge
    automatico aqui criaria commit local que ninguem vai revisar."""
    chamadas = _git_falso(monkeypatch, {"status": _resposta(), "pull": _resposta()})
    monkeypatch.setattr(bot, "_commit_do_disco", lambda: "x")
    bot._puxar_atualizacao()
    assert ("pull", "--ff-only") in chamadas


def test_pull_que_falha_explica_sem_derrubar(monkeypatch):
    _git_falso(monkeypatch, {
        "status": _resposta(),
        "pull": _resposta(erro="fatal: Not possible to fast-forward, aborting.", codigo=1),
    })
    monkeypatch.setattr(bot, "_commit_do_disco", lambda: "x")
    mudou, texto = bot._puxar_atualizacao()
    assert mudou is False
    assert "fast-forward" in texto


def test_pasta_sem_git_explica(monkeypatch):
    _git_falso(monkeypatch, {"status": _resposta(erro="fatal: not a git repository", codigo=128)})
    mudou, texto = bot._puxar_atualizacao()
    assert mudou is False
    assert "git clone" in texto


def test_git_ausente_ou_travado_nao_levanta(monkeypatch):
    for erro in (FileNotFoundError("git"), subprocess.TimeoutExpired("git", 120)):
        monkeypatch.setattr(bot, "_git", lambda *a, _e=erro: (_ for _ in ()).throw(_e))
        mudou, texto = bot._puxar_atualizacao()
        assert mudou is False and texto


def test_erro_do_git_nao_leva_credencial_para_o_chat(monkeypatch):
    """Um remoto https clonado com token carrega `usuario:token@` na URL, e o
    git repete a URL na mensagem de erro."""
    _git_falso(monkeypatch, {
        "status": _resposta(),
        "pull": _resposta(erro="fatal: unable to access "
                               "'https://joao:ghp_SEGREDO123@github.com/x/y.git/'", codigo=1),
    })
    monkeypatch.setattr(bot, "_commit_do_disco", lambda: "x")
    _, texto = bot._puxar_atualizacao()
    assert "ghp_SEGREDO123" not in texto
    assert "joao" not in texto


def test_sem_segredos_redige_credencial_embutida_na_url():
    limpo = registro.sem_segredos("https://joao:ghp_SEGREDO@github.com/x/y.git")
    assert "ghp_SEGREDO" not in limpo and "://***@github.com" in limpo
    # URL sem credencial continua legivel (diagnostico)
    assert registro.sem_segredos("https://github.com/x/y.git").endswith("y.git")


# --------------------------------------------------------------- trava
def test_nao_atualiza_no_meio_de_uma_operacao():
    """A trava esta na mao de outra thread (um /imprimir): responde na hora."""
    liberar = __import__("threading").Event()
    pegou = __import__("threading").Event()

    def _segurar():
        with bot.TRAVA_CONTA:
            pegou.set()
            liberar.wait(5)

    t = __import__("threading").Thread(target=_segurar)
    t.start()
    pegou.wait(5)
    try:
        assert bot._atualizar_sem_atropelar() is None
    finally:
        liberar.set()
        t.join()


def test_trava_e_devolvida_depois_da_atualizacao(monkeypatch):
    monkeypatch.setattr(bot, "_puxar_atualizacao", lambda: (False, "nada"))
    assert bot._atualizar_sem_atropelar() == (False, "nada")
    assert bot.TRAVA_CONTA.acquire(blocking=False), "a trava ficou presa"
    bot.TRAVA_CONTA.release()


# -------------------------------------------------------------- handler
def _rodar(monkeypatch, resultado, *, chat=CHAT, sem_pausa="1", saiu=None):
    saiu = [] if saiu is None else saiu     # `saiu or []` erraria: lista vazia e falsy
    duble = _Bot()
    monkeypatch.setattr(bot, "_atualizar_sem_atropelar", lambda: resultado)
    if sem_pausa is None:
        monkeypatch.delenv("BOT_SEM_PAUSA", raising=False)
    else:
        monkeypatch.setenv("BOT_SEM_PAUSA", sem_pausa)
    monkeypatch.setattr(bot.os, "_exit", saiu.append)
    monkeypatch.setattr(bot.logging, "shutdown", lambda *a: None)
    asyncio.run(bot.cmd_atualizar(_Update(chat), _Ctx(duble)))
    return duble.enviadas


def test_chat_nao_autorizado_nao_atualiza(monkeypatch):
    chamou = []
    monkeypatch.setattr(bot, "_atualizar_sem_atropelar", lambda: chamou.append(1))
    duble = _Bot()
    asyncio.run(bot.cmd_atualizar(_Update(111), _Ctx(duble)))
    assert chamou == []
    assert "Nao autorizado" in duble.enviadas[0][1]


def test_ocupado_responde_e_nao_reinicia(monkeypatch, tmp_path):
    saiu: list = []
    enviadas = _rodar(monkeypatch, None, saiu=saiu)
    assert saiu == [], "nao pode reiniciar sem ter atualizado"
    assert "meio de uma operacao" in enviadas[-1][1]


def test_sem_novidade_nao_reinicia(monkeypatch):
    saiu: list = []
    enviadas = _rodar(monkeypatch, (False, "Ja estava na versao mais nova (abc)."), saiu=saiu)
    assert saiu == []
    assert "Ja estava" in enviadas[-1][1]


def test_atualizou_reinicia_e_deixa_recado(monkeypatch, tmp_path):
    monkeypatch.setattr(bot, "ARQUIVO_REINICIO", tmp_path / "reinicio.json")
    saiu: list = []
    enviadas = _rodar(monkeypatch, (True, "Atualizado: a → b."), saiu=saiu)
    assert saiu == [0], "tem de sair para o lancador subir a versao nova"
    assert "Reiniciando" in enviadas[-1][1]
    assert core._ler_json(tmp_path / "reinicio.json")["chat_id"] == CHAT


def test_sem_lancador_automatico_nao_sai_do_ar(monkeypatch, tmp_path):
    """Bot aberto na mao: sair o deixaria morto. Atualiza e avisa."""
    monkeypatch.setattr(bot, "ARQUIVO_REINICIO", tmp_path / "reinicio.json")
    saiu: list = []
    enviadas = _rodar(monkeypatch, (True, "Atualizado: a → b."), sem_pausa=None, saiu=saiu)
    assert saiu == [], "nao pode sair sem quem o reinicie"
    assert bot.RECEITA_REINICIO in enviadas[-1][1]
    assert not (tmp_path / "reinicio.json").exists()


# ------------------------------------------------------- aviso na volta
class _App:
    def __init__(self):
        self.bot = _Bot()


def test_avisa_na_volta_e_apaga_o_recado(monkeypatch, tmp_path):
    arq = tmp_path / "reinicio.json"
    core._gravar_json(arq, {"chat_id": CHAT})
    monkeypatch.setattr(bot, "ARQUIVO_REINICIO", arq)
    app = _App()
    asyncio.run(bot._avisar_reinicio(app))
    assert "Voltei" in app.bot.enviadas[0][1]
    assert not arq.exists(), "o recado tem de sumir — senao avisa a cada reinicio"


def test_sem_recado_nao_avisa_nada(monkeypatch, tmp_path):
    monkeypatch.setattr(bot, "ARQUIVO_REINICIO", tmp_path / "nao_existe.json")
    app = _App()
    asyncio.run(bot._avisar_reinicio(app))
    assert app.bot.enviadas == []


def test_falha_ao_avisar_nao_impede_o_bot_de_subir(monkeypatch, tmp_path):
    arq = tmp_path / "reinicio.json"
    core._gravar_json(arq, {"chat_id": CHAT})
    monkeypatch.setattr(bot, "ARQUIVO_REINICIO", arq)

    class _Ruim:
        bot = type("B", (), {"send_message": staticmethod(
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("rede")))})()

    asyncio.run(bot._avisar_reinicio(_Ruim()))          # nao levanta


# ---------------------------------------------------------------- menu
def test_atualizar_esta_no_menu_e_no_handler():
    nomes = {c for c, _ in bot.COMANDOS_MENU}
    assert "atualizar" in nomes


# ------------------------------------------------- receita de reinicio manual
def test_receita_de_reinicio_nao_volta_ao_par_schtasks():
    """Regressao (2026-08-04): a receita antiga era `schtasks /end` + `/run`, e
    ela NAO reiniciava o bot. O lancador subia o .bat sem `-Wait`, entao a
    tarefa era dada por terminada no primeiro segundo e o bot ficava ORFAO: o
    `/end` nao tinha o que matar e o `/run` subia um SEGUNDO bot por cima do
    primeiro. Os dois brigavam pelo getUpdates (409) e o ANTIGO seguia
    respondendo — o sintoma era "reiniciei e o /versao insiste na versao velha".
    Voltar a ensinar isso reintroduz o bug para quem seguir a mensagem."""
    from pathlib import Path

    assert "schtasks" not in bot.RECEITA_REINICIO
    assert "Reiniciar Bot.bat" in bot.RECEITA_REINICIO

    raiz = Path(bot.__file__).resolve().parent
    script = raiz / "atalhos" / "reiniciar-bot.ps1"
    assert script.exists(), "a receita aponta para um script que precisa existir"
    assert (raiz / "atalhos" / "Reiniciar Bot.bat").exists()

    # o lancador precisa do -Wait: sem ele a tarefa "termina" e o bot fica orfao
    lancador = (raiz / "atalhos" / "rodar-bot-oculto.ps1").read_text(encoding="utf-8")
    start = [ln for ln in lancador.splitlines()
             if ln.strip().startswith("Start-Process")]
    assert start and all("-Wait" in ln for ln in start), \
        "Start-Process sem -Wait deixa o bot orfao da tarefa do Agendador"

    # e nenhuma instrucao viva (fora de comentario) pode ensinar o par antigo
    for arq in (Path(bot.__file__), raiz / "Atualizar programa.bat"):
        vivas = [ln for ln in arq.read_text(encoding="utf-8").splitlines()
                 if "schtasks /end" in ln
                 and not ln.strip().startswith(("#", "REM", "//"))]
        assert not vivas, f"{arq.name} ainda ensina o par schtasks: {vivas}"
