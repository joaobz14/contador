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
