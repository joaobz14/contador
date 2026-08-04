"""
registro.py
Log operacional simples do Separador (separador.log) + redacao de segredos.

Modulo-folha DE PROPOSITO (nao importa tkinter nem o nucleo): assim pode ser
importado e testado sem display, e reutilizado por qualquer parte do app.

Filosofia do projeto (igual a _log_tempos): o log NUNCA atrapalha a operacao —
se o arquivo nao puder ser aberto, segue sem log. E NUNCA registra segredos:
loja, conta, dia de despacho, contagens e falhas — jamais tokens.
"""
import logging
import re
import sys
from pathlib import Path

# logs/ ao lado do codigo (ver PASTA_LOGS no nucleo). O caminho e montado aqui
# SEM importar o nucleo de proposito: este modulo e folha (ver docstring) — o
# preco e repetir "logs", o ganho e poder ser importado/testado sozinho.
ARQUIVO_LOG = Path(__file__).resolve().parent / "logs" / "separador.log"

log = logging.getLogger("separador")
if not log.handlers:
    log.setLevel(logging.INFO)
    log.propagate = False
    try:
        # delay=True nao cria a pasta na abertura do handler, so na 1a escrita —
        # entao garantimos a pasta aqui (o nucleo tambem cria, mas registro pode
        # ser importado sozinho).
        ARQUIVO_LOG.parent.mkdir(parents=True, exist_ok=True)
        _fh = logging.FileHandler(ARQUIVO_LOG, encoding="utf-8", delay=True)
        _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                                           datefmt="%Y-%m-%d %H:%M:%S"))
        log.addHandler(_fh)
    except OSError:
        pass                       # sem permissao de escrita: segue sem arquivo
    if getattr(sys, "stderr", None) is not None:   # console do lancador de diagnostico
        _sh = logging.StreamHandler()
        _sh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        log.addHandler(_sh)
    log.addHandler(logging.NullHandler())          # garante >=1 handler (idempotencia)


# Redacao de segredos: a Shopee assina URLs com access_token/sign na query, e o
# OAuth carrega code/refresh_token. Um erro de rede (raise_for_status) propaga a
# URL inteira ate o log — entao todo texto de excecao passa por aqui antes, para
# o token NUNCA cair no separador.log.
_CHAVES = (r"access_token|refresh_token|new_refresh_token|"
           r"client_secret|partner_key|app_secret|sign|code")
# Forma query-string:  chave=valor  (URL assinada da Shopee, redirect do OAuth).
_QUERY_RE = re.compile(rf"({_CHAVES})=[^&\s\"']+", re.I)
# Segredo NO CAMINHO da URL, nao na query — a regex acima nao alcanca.
#   Telegram: https://api.telegram.org/bot<ID>:<TOKEN>/getUpdates
# O httpx ja e silenciado no bot (ver bot_telegram), mas isso e a rede de baixo:
# qualquer texto de excecao/diagnostico que carregue essa URL sai redigido.
_PATH_RE = re.compile(r"(/bot)\d+:[\w-]+", re.I)
# Cabecalho Authorization: o token do ML viaja em "Bearer <token>" (nao na
# query). Nenhum caminho de hoje loga headers, mas um repr de request futuro
# passaria batido pelas duas regexes acima.
_BEARER_RE = re.compile(r"(Bearer\s+)[\w.\-]+", re.I)
# Webhook do n8n (/perguntas): a URL INTEIRA e a credencial — o endpoint nao
# pede token nem cabecalho, entao quem tem o link dispara o fluxo. O caminho
# depois de /webhook/ leva um sufixo aleatorio justamente por isso. O
# `_disparar_perguntas` ja constroi erro limpo (a URL nao entra na mensagem);
# isto cobre o resto (um diagnostico futuro que imprima a config, por exemplo).
_WEBHOOK_RE = re.compile(r"(/webhook(?:-test)?/)[\w-]+", re.I)
# Credencial embutida na URL: https://usuario:token@github.com/... — forma que
# o git usa quando o remoto foi clonado com token. Entrou junto com o
# /atualizar, que manda saida do git para o chat do Telegram. Redige o par
# inteiro (usuario tambem identifica).
_USERINFO_RE = re.compile(r"(://)[^/\s:@]+:[^/\s@]+(@)")
# Forma JSON / repr de dict:  "chave": "valor"  ou  'chave': 'valor'  (defesa em
# profundidade — um caminho de erro futuro que serialize o corpo/credencial de um
# request, ex.: f"Falha: {dados}", passaria batido pela regex de query). Valor sem
# aspas (ex.: "code": 200) NAO e redigido — so credenciais/tokens vao entre aspas.
_JSON_RE = re.compile(rf'(["\'](?:{_CHAVES})["\']\s*:\s*)(["\'])[^"\']*\2', re.I)


def sem_segredos(texto) -> str:
    """Substitui o valor de parametros sensiveis por *** (mantendo a chave, util
    para diagnostico). Cobre seis formas: query (chave=valor), JSON
    ("chave": "valor"), segredo NO CAMINHO da URL (token do Telegram), o
    cabecalho Bearer, o caminho do webhook do n8n e a credencial embutida na URL
    (`://usuario:token@`). Tolera qualquer entrada (converte para str)."""
    t = _QUERY_RE.sub(r"\1=***", str(texto))
    t = _JSON_RE.sub(r"\1\2***\2", t)
    t = _PATH_RE.sub(r"\1***", t)
    t = _WEBHOOK_RE.sub(r"\1***", t)
    t = _USERINFO_RE.sub(r"\1***\2", t)
    return _BEARER_RE.sub(r"\1***", t)
