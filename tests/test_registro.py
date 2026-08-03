"""Log operacional: a redacao de segredos (registro.sem_segredos) NUNCA pode
deixar token/code cair no separador.log. Modulo-folha, testavel sem display."""
import registro


def test_redige_access_token_da_url_assinada_shopee():
    url = ("https://partner.shopeemobile.com/api/v2/logistics/ship_order"
           "?partner_id=123&timestamp=1700000000&access_token=SEGREDO_ABC123&shop_id=99&sign=DEADBEEF")
    out = registro.sem_segredos(url)
    assert "SEGREDO_ABC123" not in out
    assert "DEADBEEF" not in out
    assert "access_token=***" in out
    assert "sign=***" in out
    # o que nao e segredo permanece (util para diagnostico)
    assert "partner_id=123" in out
    assert "shop_id=99" in out


def test_redige_code_e_refresh_token_do_oauth():
    txt = "callback?code=AUTH_CODE_XYZ&refresh_token=RT_9876&new_refresh_token=RT_NEW"
    out = registro.sem_segredos(txt)
    for segredo in ("AUTH_CODE_XYZ", "RT_9876", "RT_NEW"):
        assert segredo not in out
    assert out.count("=***") == 3


def test_redige_forma_json_e_repr_de_dict():
    """Defesa em profundidade (5.11): um corpo/credencial serializado como JSON
    ou repr de dict tambem e redigido — a regex de query sozinha nao pegaria."""
    j = '{"refresh_token": "RT_JSON_123", "client_secret": "CS_9", "partner_key": "PK_7"}'
    out = registro.sem_segredos(j)
    for segredo in ("RT_JSON_123", "CS_9", "PK_7"):
        assert segredo not in out
    assert out.count('"***"') == 3
    # repr de dict (aspas simples), como num f-string de debug
    d = "Falha: {'access_token': 'AT_ABC', 'shop_id': 99}"
    red = registro.sem_segredos(d)
    assert "AT_ABC" not in red and "'***'" in red
    assert "'shop_id': 99" in red                      # nao-segredo intacto


def test_valor_json_numerico_nao_e_redigido():
    """"code": 200 (sem aspas) e status, nao segredo — nao redige."""
    assert registro.sem_segredos('{"code": 200}') == '{"code": 200}'


def test_texto_sem_segredo_fica_intacto():
    msg = "Shopee /api/v2/order/get: error_auth - invalid token"
    assert registro.sem_segredos(msg) == msg


def test_tolera_entrada_nao_string():
    assert registro.sem_segredos(RuntimeError("access_token=ABC caiu")) == \
        "access_token=*** caiu"


def test_logger_tem_handler_e_nao_propaga():
    # setup idempotente do modulo: ao menos 1 handler e sem propagar pro root.
    assert registro.log.handlers
    assert registro.log.propagate is False


# ── Formas de segredo que a query/JSON NAO alcancam (varredura 2026-08-03) ───
#
# `registro.py` e a ULTIMA linha de defesa contra vazamento em log. As
# auditorias anteriores entraram sempre pelo nucleo e nunca olharam este modulo
# de 64 linhas — e havia duas brechas, uma delas aberta no MESMO dia.

def test_app_secret_do_tiktok_e_redigido():
    """`pegar_token_tiktok.py` manda app_key + app_secret na QUERY. Um erro de
    transporte carrega a URL inteira, e o script imprime traceback no console.
    `app_secret` nao estava na lista de chaves — brecha aberta hoje mesmo."""
    txt = ("ConnectionError: https://auth.tiktok-shops.com/api/v2/token/get"
           "?app_key=6kq&app_secret=SUPERSEGREDO&auth_code=AC1")
    out = registro.sem_segredos(txt)
    assert "SUPERSEGREDO" not in out
    assert "app_key=6kq" in out, "o que NAO e segredo fica, para diagnosticar"


def test_token_do_telegram_no_CAMINHO_da_url():
    """A API do Telegram poe o token no PATH (/bot<ID>:<TOKEN>/), nao na query —
    a regex de chave=valor nao alcanca. O httpx ja e silenciado no bot, mas isto
    e a rede de baixo: qualquer texto de excecao com essa URL sai redigido."""
    out = registro.sem_segredos("httpx: https://api.telegram.org/bot8123456:AAH-SEGREDO/getUpdates")
    assert "AAH-SEGREDO" not in out and "8123456" not in out
    assert "getUpdates" in out


def test_bearer_do_ml_e_redigido():
    """O token do ML viaja em 'Authorization: Bearer ...' (nao na query).
    Nenhum caminho de hoje loga headers — defesa em profundidade para um repr
    de request futuro."""
    out = registro.sem_segredos("headers={'Authorization': 'Bearer APP_USR-SEGREDO-123'}")
    assert "APP_USR-SEGREDO-123" not in out
    assert "Authorization" in out
