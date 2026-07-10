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

ARQUIVO_LOG = Path(__file__).resolve().parent / "separador.log"

log = logging.getLogger("separador")
if not log.handlers:
    log.setLevel(logging.INFO)
    log.propagate = False
    try:
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
_SEGREDO_RE = re.compile(
    r"(access_token|refresh_token|new_refresh_token|sign|code)=[^&\s\"']+", re.I)


def sem_segredos(texto) -> str:
    """Substitui o valor de parametros sensiveis por *** (mantendo a chave, util
    para diagnostico). Tolera qualquer entrada (converte para str)."""
    return _SEGREDO_RE.sub(r"\1=***", str(texto))
